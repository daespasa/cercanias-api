# Cercanías API

API sencilla en FastAPI para consultar datos GTFS de Renfe Cercanías.

## Requisitos

- Python 3.9+
- (Opcional) crear y activar un entorno virtual

````markdown
# Cercanías API

API sencilla en FastAPI para consultar datos GTFS de Renfe Cercanías.

## Requisitos

- Python 3.9+
- (Opcional) crear y activar un entorno virtual

## Instalación

1. Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

2. Coloca el archivo GTFS ZIP en el directorio `data/gtfs/` (por defecto) con el nombre por defecto `fomento_transit.zip`, o define la ruta/ubicación en `.env` con las variables `GTFS_DATA_DIR` y/o `GTFS_PATH`.

3. (Opcional) configura la API key en `.env`:

```text
API_KEY=tu_api_key_aqui
```

Si `API_KEY` está presente, la API exigirá el header `X-API-Key` en las peticiones.

## Ejecutar la API

Recomendado (script incluido):

```powershell
python run.py
```

Opciones de entorno:

- `HOST` — host a escuchar (por defecto `0.0.0.0`)
- `PORT` — puerto (por defecto `8000`)
- `UVICORN_RELOAD` — `true`/`false` para habilitar recarga automática en desarrollo

Ejemplo con recarga (PowerShell):

```powershell
#$env:UVICORN_RELOAD = "true"; python run.py
```

Alternativa directa usando uvicorn:

```powershell
python -m uvicorn app:app --reload
```

La API estará disponible en `http://127.0.0.1:8000` por defecto.

> Nota: `run.py` crea el directorio `GTFS_DATA_DIR` si no existe antes de arrancar.

## Variables y carpeta de datos GTFS

- `GTFS_DATA_DIR` (por defecto `data/gtfs`) — carpeta donde se almacenan el ZIP GTFS y el fichero `.meta` con metadatos.
- `GTFS_PATH` — nombre del fichero ZIP dentro de `GTFS_DATA_DIR` (por defecto `fomento_transit.zip`).

El downloader (si está configurado) usa ETag / If-Modified-Since y guarda metadatos JSON junto al ZIP.

## Endpoints principales

- `GET /stops/` — lista de paradas. Parámetro opcional `limit`.
- `GET /stops/{stop_id}` — detalles de una parada.
- `GET /routes/` — lista de rutas.
- `GET /routes/{route_id}` — detalle de una ruta.
- `GET /schedule/?stop_id=...&route_id=...&date=YYYY-MM-DD` — entradas de horario filtradas. `date` intenta filtrar usando `calendar.txt` y `calendar_dates.txt`.

Ejemplo con `curl` (sin API key configurada):

```powershell
curl http://127.0.0.1:8000/stops/
curl "http://127.0.0.1:8000/schedule/?stop_id=S1&date=2025-06-01"
```

Si has configurado `API_KEY`, añade el header `X-API-Key`:

```powershell
curl -H "X-API-Key: tu_api_key" http://127.0.0.1:8000/stops/
```

## Endpoints administrativos

- `GET /admin/gtfs/meta` — devuelve metadatos persistidos del ZIP en disco y metadatos actuales del `GTFSManager` (timestamps, etag, hash, size, status).

Si quieres forzar recargas o añadir endpoints de administración, puedes extender el router `app/routers/admin.py`.

## Convenciones y seguridad

- Los errores HTTP se devuelven en estilo Problem Details (`type`, `title`, `status`, `detail`).
- Validación simple de seguridad por `X-API-Key` si `API_KEY` está presente en la configuración.

## Tests

Para ejecutar los tests unitarios:

```powershell
python -m pip install -r requirements.txt
pytest -q
```

Los tests residen en `tests/` y usan directorios temporales y `monkeypatch` para aislar la dependencia de `GTFS_DATA_DIR`.

## Siguientes pasos recomendados

- Añadir más validaciones y paginación para listados grandes.
- Mejorar performance (indexar/serializar) para GTFS grandes.
- Añadir endpoints de búsqueda por nombre y proximidad geográfica.
````
