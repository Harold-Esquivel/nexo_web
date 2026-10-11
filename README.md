# Nexo — Buscador web para celular

Web responsive con tres módulos: **Productos y juegos**, **Empresas**, **Acciones**. Mantiene la lógica principal del archivo Python proporcionado. Las búsquedas online requieren backend Python; abrir solo `index.html` no ejecuta consultas reales.

## Para probar en tu computadora

1. Instala Python 3.12 o 3.13.
2. Abre una terminal dentro de esta carpeta.
3. Ejecuta `pip install -r requirements.txt`.
4. Ejecuta `python app.py`.
5. Entra en `http://127.0.0.1:5000`.

## Para abrir desde tu celular en el mismo Wi-Fi

1. Ejecuta la web en tu PC como se indica arriba.
2. Consulta la IP local de tu PC con `ipconfig` (ejemplo: `192.168.1.12`).
3. En el navegador del celular abre `http://192.168.1.12:5000` y acepta la excepción del firewall en red privada si Windows la solicita.

## Publicar en internet con Render

1. Sube el contenido completo de esta carpeta a un repositorio de GitHub (mantén `app.py`, `buscador.py`, `templates/` y `static/`).
2. En Render crea un **Web Service** desde ese repositorio, o usa el Blueprint incluido en `render.yaml`.
3. Configura `Build Command`: `pip install -r requirements.txt`.
4. Configura `Start Command`: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 app:app`.
5. Abre la URL HTTPS de Render desde tu celular.

No funcionará en alojamiento **solo HTML** como GitHub Pages, pues requiere servidor Python. Los planes y límites del hosting pueden cambiar. Se usa un tipo de cambio **manual** (variable `USD_A_PEN`, por defecto 3.7) únicamente para estimaciones de precios en soles; edítalo antes de publicar. DDGS y yfinance son fuentes externas que pueden limitar el acceso, bloquear peticiones o devolver datos incompletos. Señales técnicas ≠ probabilidades fiables.

## Estructura

- `app.py`: servidor/API HTTP
- `buscador.py`: búsquedas y análisis originales adaptados para web
- `templates/index.html`: estructura HTML
- `static/style.css`: diseño responsive
- `static/app.js`: interacción, filtros, botones y paginación
- `render.yaml` y `Procfile`: despliegue
