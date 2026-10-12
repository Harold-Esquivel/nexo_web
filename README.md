# Nexo Web 2.1 — Corrección de búsquedas en Render

Esta versión conserva los paneles de detalle de productos, empresas y acciones de Nexo 2.0 y corrige la gestión de peticiones lentas que podían mostrar: `Failed to execute 'json' on 'Response': Unexpected end of JSON input`.

## Cambios

- El navegador inicia una **búsqueda en segundo plano** (`POST /api/buscar`) y obtiene su estado con `GET /api/trabajo/<identificador>`.
- Los endpoints devuelven **JSON**, también cuando ocurre un error gestionado.
- Si Render devuelve HTML, una respuesta vacía o 502/503/504, la interfaz muestra un mensaje entendible en lugar de la excepción de `response.json()`.
- Gunicorn utiliza **1 proceso y 4 hilos** para reducir consumo de memoria en el plan gratuito de Render.
- Se limitan las fichas examinadas automáticamente a **12 por búsqueda**; los resultados restantes siguen mostrando nombre, resumen y enlace original si el buscador los devuelve. Puedes configurar `NEXO_MAX_DETALLES=8` para servidores con menos recursos.
- La selección de `20/50/100` indica **resultados solicitados**, no páginas garantizadas.
- Las búsquedas dependen de proveedores externos. Facebook, G2A, Eneba o Mercado Libre pueden bloquear el acceso a determinados datos y no se puede garantizar encontrar todas sus páginas.

## Actualizar GitHub y Render (IMPORTANTE)

1. Descarga y descomprime el archivo ZIP. **Sube el contenido interior de `nexo_web/` a la raíz de tu repositorio GitHub** (no subas el ZIP sin descomprimir).
2. Reemplaza los archivos antiguos `app.py`, `buscador.py`, `render.yaml`, `Procfile`, `templates/index.html`, `static/app.js` y los demás que aparecen en la carpeta. Confirma con **Commit changes**.
3. En **Render → tu Web Service → Settings** revisa que el **Start Command** sea exactamente:

   ```bash
   gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 90 app:app
   ```

   Atención: editar `render.yaml` en GitHub no siempre modifica la configuración de un servicio creado manualmente; actualiza el comando en el panel también.
4. El **Build Command** debe ser:

   ```bash
   pip install -r requirements.txt
   ```

5. En Render usa **Manual Deploy → Deploy latest commit** si el despliegue automático está desactivado. Espera a que indique **Live**.
6. Abre en tu navegador `https://TU-SERVICIO.onrender.com/api/health`. Debes obtener algo como:

   ```json
   {"status":"ok","version":"2.1.0"}
   ```

7. Recarga la página de Nexo y prueba primero con **20 resultados**. Las búsquedas grandes pueden tardar más y no garantizan 50 o 100 resultados reales.

## Si sigue fallando

Entra a **Render → tu servicio → Logs** y busca mensajes como `WORKER TIMEOUT`, `SIGKILL`, `Out of memory`, `Error de búsqueda` o `503`. Copia esas líneas si necesitas un diagnóstico exacto. Un reinicio del plan gratis puede borrar las búsquedas en curso porque esta versión almacena trabajos temporalmente en la memoria del proceso. Para trabajos persistentes haría falta Redis/una cola externa.

## Ejecutar localmente

Requiere Python 3.12 (recomendado), internet y las bibliotecas de `requirements.txt`.

```bash
pip install -r requirements.txt
python app.py
```

Abre `http://localhost:5000/api/health` y luego `http://localhost:5000`.

## Seguridad y limitaciones

- No almacenes claves privadas ni cuentas bancarias en el repositorio.
- El servidor no compra ni vende valores; solo muestra enlaces externos. Las señales de bolsa son orientativas, no pronósticos certificados.
- No se inventan precios, reseñas, números de contacto ni disponibilidad cuando los sitios no entregan esos datos.
