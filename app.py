"""Nexo 2.1: API con búsquedas en segundo plano para alojamientos pequeños."""
import math
import os
import re
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from buscador import analizar_accion, buscar_acciones, buscar_empresas, buscar_productos

app = Flask(__name__)
app.json.ensure_ascii = False
VERSION = '2.1.0'

# Usar un solo proceso Gunicorn: el almacenamiento temporal vive en memoria.
# Un trabajo simultáneo limita consumo de CPU y RAM en Render Free.
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='nexo-busqueda')
_lock = threading.Lock()
_jobs = {}
_clients = {}
_CACHE_SECONDS = 600
_JOB_SECONDS = 900
_MAX_QUEUED = 4


def _safe_json(obj):
    """Convierte escalares de pandas/numpy y evita JSON con NaN o Infinity."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {str(k): _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_json(v) for v in obj]
    if hasattr(obj, 'item'):
        try:
            return _safe_json(obj.item())
        except (ValueError, TypeError):
            pass
    return str(obj)


def _cleanup(now):
    for key, job in list(_jobs.items()):
        if now - job['creado'] > _JOB_SECONDS:
            del _jobs[key]
    for key, stamps in list(_clients.items()):
        valid = [stamp for stamp in stamps if now - stamp < 60]
        if valid:
            _clients[key] = valid
        else:
            del _clients[key]


def _worker(job_id, categoria, consulta, zona, modo, limite):
    try:
        if categoria == 'productos':
            tasa = float(os.getenv('USD_A_PEN', '3.7'))
            datos = buscar_productos(consulta, zona, limite, tasa)
        elif categoria == 'empresas':
            datos = buscar_empresas(consulta, zona, limite)
        else:
            datos = buscar_acciones(modo, consulta)
        respuesta = {
            'resultados': _safe_json(datos),
            'total': len(datos),
            'aviso': 'Los enlaces dependen de buscadores externos. Los datos pueden estar incompletos o desactualizados.',
        }
        with _lock:
            if job_id in _jobs:
                _jobs[job_id].update(estado='terminado', respuesta=respuesta)
    except Exception:
        app.logger.exception('Búsqueda fallida (%s)', categoria)
        with _lock:
            if job_id in _jobs:
                _jobs[job_id].update(
                    estado='error',
                    mensaje='El proveedor externo no respondió correctamente. Intenta nuevamente con menos resultados.',
                )


@app.after_request
def sin_cache_api(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/')
def inicio():
    return render_template('index.html')


@app.get('/api/health')
def health():
    return jsonify(status='ok', version=VERSION)


@app.get('/api/accion/<simbolo>')
def detalle_accion(simbolo):
    if not re.fullmatch(r'[A-Za-z0-9.\-^=]{1,15}', simbolo):
        return jsonify(error='Símbolo no válido.'), 400
    try:
        resultado = analizar_accion(simbolo.upper())
        if resultado is None:
            return jsonify(error='No hay datos suficientes para esta acción.'), 404
        return jsonify(_safe_json(resultado))
    except Exception:
        app.logger.exception('Error al consultar acción')
        return jsonify(error='No se pudo consultar el detalle de la acción.'), 502


@app.post('/api/buscar')
def buscar():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error='Solicitud inválida: se esperaba un objeto JSON.'), 400
    categoria = str(payload.get('categoria', 'productos'))
    consulta = str(payload.get('consulta', '')).strip()[:120]
    zona = 'Arequipa' if payload.get('zona') == 'Arequipa' else 'Todo Perú'
    modo = 'Una empresa' if payload.get('modo') == 'Una empresa' else 'Ranking global'
    try:
        limite = max(10, min(100, int(payload.get('limite', 20))))
    except (ValueError, TypeError, OverflowError):
        limite = 20
    if categoria not in ('productos', 'empresas', 'acciones'):
        return jsonify(error='Categoría no válida.'), 400
    if not consulta and not (categoria == 'acciones' and modo == 'Ranking global'):
        return jsonify(error='Escribe lo que deseas buscar.'), 400
    if categoria == 'acciones' and modo == 'Ranking global' and consulta and not re.fullmatch(r'[A-Za-z0-9.,;\s^=\-]+', consulta):
        return jsonify(error='En el ranking usa símbolos como AAPL, NVDA, MSFT.'), 400

    now = time.monotonic()
    ip = request.remote_addr or 'unknown'
    with _lock:
        _cleanup(now)
        stamps = _clients.setdefault(ip, [])
        if len(stamps) >= 8:
            return jsonify(error='Has realizado muchas consultas. Espera un minuto y vuelve a intentarlo.'), 429
        pending = sum(j['estado'] == 'procesando' for j in _jobs.values())
        if pending >= _MAX_QUEUED:
            return jsonify(error='Hay varias búsquedas en curso. Inténtalo en unos segundos.'), 503
        stamps.append(now)
        job_id = secrets.token_urlsafe(18)
        _jobs[job_id] = {'creado': now, 'estado': 'procesando', 'respuesta': None}

    try:
        _pool.submit(_worker, job_id, categoria, consulta, zona, modo, limite)
    except RuntimeError:
        with _lock:
            _jobs.pop(job_id, None)
        return jsonify(error='No se pudo iniciar la búsqueda. Vuelve a intentarlo.'), 503
    return jsonify(trabajo=job_id, estado='procesando'), 202


@app.get('/api/trabajo/<job_id>')
def estado_trabajo(job_id):
    if not re.fullmatch(r'[A-Za-z0-9_\-]{15,40}', job_id):
        return jsonify(error='Identificador de búsqueda no válido.'), 400
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return jsonify(error='La búsqueda ya no está disponible. Si el servidor se reinició, vuelve a buscar.'), 404
        if job['estado'] == 'terminado':
            return jsonify(estado='terminado', **job['respuesta'])
        if job['estado'] == 'error':
            return jsonify(estado='error', error=job['mensaje']), 502
    return jsonify(estado='procesando'), 202


@app.errorhandler(HTTPException)
def error_http(err):
    if request.path.startswith('/api/'):
        return jsonify(error=err.description, status=err.code), err.code
    return err


@app.errorhandler(Exception)
def error_inesperado(err):
    app.logger.exception('Error inesperado en %s', request.path)
    if request.path.startswith('/api/'):
        return jsonify(error='Error interno del servidor. Revisa los Logs en Render.'), 500
    return 'Error interno', 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False, threaded=True)
