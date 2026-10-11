"""Nexo web: interfaz móvil y API de búsqueda."""
import os
import re
import time
import threading
from flask import Flask, render_template, request, jsonify
from buscador import buscar_productos, buscar_empresas, buscar_acciones

app = Flask(__name__)
app.json.ensure_ascii = False
_gate = threading.Lock()
_clients = {}

@app.get('/')
def inicio():
    return render_template('index.html')

@app.get('/api/health')
def health():
    return jsonify(status='ok')

@app.post('/api/buscar')
def buscar():
    payload = request.get_json(silent=True) or {}
    cat = str(payload.get('categoria', 'productos'))
    query = str(payload.get('consulta', '')).strip()[:120]
    zona = 'Arequipa' if payload.get('zona') == 'Arequipa' else 'Todo Perú'
    modo = 'Una empresa' if payload.get('modo') == 'Una empresa' else 'Ranking global'
    limite = min(max(int(payload.get('limite', 20)) if str(payload.get('limite', '')).isdigit() else 20, 10), 100)
    if not query and not (cat == 'acciones' and modo == 'Ranking global'):
        return jsonify(error='Escribe lo que deseas buscar.'), 400
    if cat not in ('productos', 'empresas', 'acciones'):
        return jsonify(error='Categoría no válida.'), 400
    # Límite básico de peticiones por IP para evitar abuso de proveedores gratuitos.
    ip = request.headers.get('X-Real-IP') or request.remote_addr or 'unknown'
    now = time.monotonic()
    with _gate:
        recientes = [t for t in _clients.get(ip, []) if now-t < 60]
        if len(recientes) >= 8:
            return jsonify(error='Demasiadas consultas. Intenta nuevamente en un minuto.'), 429
        recientes.append(now)
        _clients[ip] = recientes
        if len(_clients) > 3000:
            _clients.clear()
    try:
        if cat == 'productos':
            tasa = float(os.getenv('USD_A_PEN', '3.7'))
            datos = buscar_productos(query, zona, limite, tasa)
        elif cat == 'empresas':
            datos = buscar_empresas(query, zona, limite)
        else:
            if modo == 'Ranking global' and query and not re.fullmatch(r'[A-Za-z0-9.,;\s^=\-]+', query):
                return jsonify(error='En el ranking usa símbolos como AAPL, NVDA, MSFT.'), 400
            datos = buscar_acciones(modo, query)
        return jsonify(resultados=datos, total=len(datos), aviso='Los resultados dependen de fuentes externas y pueden estar incompletos o desactualizados.')
    except Exception as err:
        app.logger.exception('Error de búsqueda')
        return jsonify(error='No se pudo completar la consulta. El proveedor externo podría estar limitando el acceso. Vuelve a intentarlo.'), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False)
