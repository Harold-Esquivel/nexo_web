#!/usr/bin/env python3
"""Buscador visual estilo macOS: productos, empresas y acciones.
Instalar: pip install customtkinter ddgs requests beautifulsoup4 yfinance pandas
Ejecutar: python buscador_app_mejorado.py
"""
import json
import math
import queue
import re
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
import yfinance as yf

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"}
AREQUIPA = (-16.3989, -71.5350)
ACCIONES = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "NFLX", "AVGO", "TSM", "ASML", "SAP", "BABA", "TM", "NVO", "JPM", "V", "KO", "DIS", "XOM", "SHEL", "BHP", "FCX", "SCCO", "BVN", "INTC", "PYPL", "NKE", "BA"]
BG = "#F5F5F7"
WHITE = "#FFFFFF"
INK = "#1D1D1F"
GREY = "#86868B"
BLUE = "#007AFF"
BLUE_LIGHT = "#EAF3FF"
BORDER = "#E5E5EA"
GREEN = "#248A48"
RED = "#D92D20"


def numero(obj, default=None):
    try:
        ans = float(obj)
        return ans if math.isfinite(ans) else default
    except (TypeError, ValueError, OverflowError):
        return default


def parse_precio(valor):
    s = re.sub(r"[^\d.,]", "", str(valor or ""))
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.rsplit(",", 1)[-1]) <= 2 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def distancia(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(math.radians(b[1]-a[1])/2)**2
    return 12742 * math.asin(min(1, math.sqrt(h)))


def descargar(url):
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=9)
        if r.ok and "html" in r.headers.get("content-type", "").lower():
            return r.text[:1_500_000]
    except requests.RequestException:
        pass
    return None


def objetos_jsonld(soup):
    salida = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            cola = [json.loads(script.string or script.get_text() or "")]
        except (ValueError, TypeError):
            continue
        while cola:
            item = cola.pop()
            if isinstance(item, list):
                cola.extend(item)
            elif isinstance(item, dict):
                salida.append(item)
                cola.extend(v for v in item.values() if isinstance(v, (dict, list)))
    return salida


def resultados_web(texto, limite):
    """DDGS devuelve hasta un máximo solicitado, sujeto a su motor y bloqueos."""
    with DDGS() as ddg:
        encontrados = list(ddg.text(texto, region="pe-es", max_results=limite) or [])
    usados, lista = set(), []
    for r in encontrados:
        url = r.get("href") or r.get("url")
        if not url or url in usados:
            continue
        usados.add(url)
        lista.append({"titulo": r.get("title") or url, "link": url, "resumen": r.get("body", "")})
    return lista


def analizar_producto(item, tasa):
    base = dict(item)
    base.update(precio=None, precio_pen=None, moneda="", calificacion=None, resenas=None)
    html = descargar(item["link"])
    if not html:
        return base
    soup = BeautifulSoup(html, "html.parser")
    for obj in objetos_jsonld(soup):
        if "Product" not in str(obj.get("@type", "")):
            continue
        ofertas = obj.get("offers") or []
        if isinstance(ofertas, dict):
            ofertas = [ofertas]
        for oferta in ofertas:
            if isinstance(oferta, dict):
                p = parse_precio(oferta.get("price") or oferta.get("lowPrice"))
                if p is not None and p > 0:
                    base["precio"] = p
                    base["moneda"] = oferta.get("priceCurrency") or ""
                    break
        nota = obj.get("aggregateRating")
        if isinstance(nota, dict):
            base["calificacion"] = numero(nota.get("ratingValue"))
            base["resenas"] = nota.get("reviewCount") or nota.get("ratingCount")
        break
    if base["precio"] is None:
        match = re.search(r"(S/\.?|US\$|USD|\$)\s*(\d[\d.,]*)", soup.get_text(" ", strip=True)[:50000], re.I)
        if match:
            base["precio"] = parse_precio(match.group(2))
            base["moneda"] = "PEN" if match.group(1).startswith("S") else "USD"
    if base["precio"] is not None:
        if base["moneda"] == "PEN":
            base["precio_pen"] = base["precio"]
        elif base["moneda"] in ("USD", "US$", "$", ""):
            # Sin moneda confirmada no convertir a PEN.
            if base["moneda"]:
                base["precio_pen"] = base["precio"] * tasa
    return base


def buscar_productos(entrada, alcance, limite, tasa):
    zona = "Arequipa" if alcance == "Arequipa" else "Perú"
    items = resultados_web(f"{entrada} comprar precio {zona}", limite)
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(lambda x: analizar_producto(x, tasa), items))


def datos_empresa(item):
    base = dict(item)
    base.update(direccion="", telefono="", correos=[], encargado="", calificacion=None, km=None)
    html = descargar(item["link"])
    if not html:
        return base
    soup = BeautifulSoup(html, "html.parser")
    emails = set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", html))
    base["correos"] = sorted(x for x in emails if not re.search(r"\.(?:png|jpg|webp|gif|svg)$", x, re.I))[:3]
    for obj in objetos_jsonld(soup):
        if isinstance(obj.get("address"), dict):
            ad = obj["address"]
            base["direccion"] = ", ".join(str(ad.get(k)) for k in ("streetAddress", "addressLocality", "addressRegion") if ad.get(k))
        if obj.get("telephone"):
            base["telefono"] = str(obj["telephone"])
        ar = obj.get("aggregateRating")
        if isinstance(ar, dict):
            base["calificacion"] = numero(ar.get("ratingValue"))
        fundador = obj.get("founder")
        if isinstance(fundador, dict):
            base["encargado"] = fundador.get("name", "")
    return base


def buscar_empresas(entrada, alcance, limite):
    lugar = "Arequipa" if alcance == "Arequipa" else "Perú"
    registros = []
    try:
        with DDGS() as ddg:
            registros = list(ddg.maps(entrada, place=f"{lugar}, Peru", max_results=min(limite, 100)) or [])
    except Exception:
        pass
    if registros:
        usados = set()
        datos = []
        for r in registros:
            enlace = r.get("url") or r.get("website") or ""
            clave = (r.get("title", "").casefold(), r.get("address", ""))
            if clave in usados:
                continue
            usados.add(clave)
            lat, lon = numero(r.get("latitude")), numero(r.get("longitude"))
            datos.append({"titulo": r.get("title") or "Empresa", "link": enlace, "resumen": r.get("description", ""),
                          "direccion": r.get("address") or "", "telefono": r.get("phone") or "",
                          "correos": [], "encargado": "", "calificacion": numero(r.get("rating")),
                          "km": round(distancia(AREQUIPA, (lat, lon)), 1) if lat is not None and lon is not None else None})
        return datos
    items = resultados_web(f"{entrada} empresas {lugar} telefono dirección web", limite)
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(datos_empresa, items))


def rsi_14(cierre):
    delta = cierre.diff().dropna()
    if len(delta) < 14:
        return None
    ganancias = delta.clip(lower=0).tail(14).mean()
    perdidas = (-delta.clip(upper=0)).tail(14).mean()
    if perdidas == 0:
        return 100.0 if ganancias > 0 else 50.0
    return 100 - 100 / (1 + ganancias / perdidas)


def analizar_accion(simbolo):
    """Clasificación heurística; no representa probabilidad estadística."""
    try:
        t = yf.Ticker(simbolo)
        hist = t.history(period="6mo", auto_adjust=True)
        if hist is None or hist.empty or "Close" not in hist:
            return None
        cierre = hist["Close"].dropna()
        if len(cierre) < 21:
            return None
        actual = float(cierre.iloc[-1])
        ma20 = float(cierre.tail(20).mean())
        ma50 = float(cierre.tail(50).mean()) if len(cierre) >= 50 else None
        cambio20 = (actual / float(cierre.iloc[-21]) - 1) * 100
        rsi = rsi_14(cierre)
        puntuacion = 0
        razones = []
        if actual >= ma20:
            puntuacion += 1
            razones.append("Precio por encima de la media de 20 sesiones")
        else:
            puntuacion -= 1
            razones.append("Precio por debajo de la media de 20 sesiones")
        if ma50 is not None:
            if ma20 >= ma50:
                puntuacion += 1
                razones.append("Media de 20 sesiones por encima de la de 50")
            else:
                puntuacion -= 1
                razones.append("Media de 20 sesiones por debajo de la de 50")
        if cambio20 > 2:
            puntuacion += 1
            razones.append("Momento positivo durante 20 sesiones")
        elif cambio20 < -2:
            puntuacion -= 1
            razones.append("Momento negativo durante 20 sesiones")
        if rsi is not None:
            if rsi > 70:
                puntuacion -= 1
                razones.append("RSI alto: posible sobrecompra")
            elif rsi < 30:
                puntuacion += 1
                razones.append("RSI bajo: posible rebote, con riesgo")
        info = {}
        try:
            info = t.info or {}
        except Exception:
            pass
        objetivo = numero(info.get("targetMedianPrice"))
        potencial = (objetivo / actual - 1) * 100 if objetivo and actual else None
        tendencia = "Posible subida" if puntuacion >= 2 else "Posible bajada" if puntuacion <= -2 else "Sin señal clara"
        return {"ticker": simbolo, "empresa": info.get("shortName") or simbolo,
                "moneda": info.get("currency") or "moneda del mercado", "precio": actual,
                "puntuacion": puntuacion, "tendencia": tendencia, "rsi": rsi,
                "momento": cambio20, "ma20": ma20, "ma50": ma50, "objetivo": objetivo,
                "potencial": potencial, "analistas": info.get("numberOfAnalystOpinions"), "razones": razones}
    except Exception:
        return None


def simbolo_busqueda(texto):
    texto = texto.strip()
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9.\-^=]{0,14}", texto):
        return texto.upper()
    try:
        resultado = yf.Search(texto, max_results=1)
        cotizaciones = resultado.quotes or []
        return cotizaciones[0].get("symbol") if cotizaciones else None
    except Exception:
        return None


def buscar_acciones(modo, entrada):
    if modo == "Una empresa":
        simbolo = simbolo_busqueda(entrada)
        if not simbolo:
            raise ValueError("No se encontró el símbolo de esa empresa. Intenta con un ticker, como AAPL.")
        resultado = analizar_accion(simbolo)
        return [resultado] if resultado else []
    adicionales = re.split(r"[,;\s]+", entrada.strip().upper()) if entrada else []
    todos = list(dict.fromkeys(ACCIONES + [x for x in adicionales if re.fullmatch(r"[A-Z0-9.\-^=]{1,15}", x)]))[:70]
    with ThreadPoolExecutor(max_workers=5) as pool:
        return [x for x in pool.map(analizar_accion, todos) if x]


