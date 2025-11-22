# 🚆 Cercanías API — FastAPI GTFS Service

[![Build Status](https://img.shields.io/github/actions/workflow/status/daespasa/cercanias-api/ci.yml?branch=main&label=build&logo=github)](https://github.com/daespasa/cercanias-api/actions)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://github.com/daespasa/cercanias-api/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)

API moderna y optimizada construida con **FastAPI** para consultar horarios, rutas y paradas de **Renfe Cercanías** utilizando datos **GTFS** oficiales.

Incluye:

- Loader GTFS completo con validación, normalización y metadatos persistidos.
- Filtrado por fecha real usando `calendar.txt` y `calendar_dates.txt`.
- Endpoints REST con respuestas estandarizadas.
- Seguridad opcional mediante `X-API-Key`.
- Tests unitarios incluidos.
- Preparada para producción con Uvicorn y estructura profesional.

---

## 📦 Requisitos

- Python **3.9+**
- (Opcional pero recomendado) **entorno virtual** `venv`
- Archivo GTFS `fomento_transit.zip`

---

## 🛠 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/daespasa/cercanias-api.git
cd cercanias-api
```

### 2. Crear y activar entorno virtual

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Colocar los datos GTFS

Por defecto se espera:

```
data/
 └── gtfs/
      ├── fomento_transit.zip
      └── fomento_transit.meta (generado automáticamente)
```

Puedes cambiar estas rutas en el archivo `.env`:

```
GTFS_DATA_DIR=data/gtfs
GTFS_PATH=fomento_transit.zip
```

### (Opcional) API Key

Para activar seguridad:

```
API_KEY=123456
```

Después deberás enviar:

```
X-API-Key: 123456
```

---

## 🚀 Ejecutar la API

### Opción recomendada (script incluido)

```bash
python run.py
```

Con recarga automática:

```powershell
$env:UVICORN_RELOAD="true"
python run.py
```

### Opción manual:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

📍 Por defecto se ejecuta en:

➡ **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

📖 Documentación interactiva:

➡ **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
➡ **[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)**

---

## 📚 Endpoints Principales

### 🔹 **GET /stops/**

Lista todas las paradas.

```bash
curl http://127.0.0.1:8000/stops/
```

### 🔹 **GET /stops/{stop_id}**

Detalles de una parada.

### 🔹 **GET /routes/**

Lista de rutas.

### 🔹 **GET /routes/{route_id}**

Detalle de rutas + información GTFS.

### 🔹 **GET /schedule/**

Consulta de horarios combinando:

- `stop_times`
- `trips`
- `routes`
- `calendar` (días activos)
- `calendar_dates` (excepciones)

Parámetros:

- `stop_id`
- `route_id`
- `date=YYYY-MM-DD`

Ejemplo:

```bash
curl "http://127.0.0.1:8000/schedule/?stop_id=65000&date=2025-06-01"
```

### 🔹 **GET /admin/gtfs/meta**

Metadatos del GTFS:

- ETAG
- Last-Modified
- Hash
- Fecha de carga
- Conteo de registros

---

## 🛡 Seguridad

Si `API_KEY` existe en `.env`, todos los endpoints requerirán:

```
X-API-Key: <tu_api_key>
```

Errores siguen el formato **RFC 7807 Problem Details**, por ejemplo:

```json
{
  "type": "about:blank",
  "title": "Unauthorized",
  "detail": "Missing or invalid API key",
  "status": 401
}
```

---

## 🧪 Tests

```bash
pip install -r requirements.txt
pytest -q
```

Los tests incluyen:

- Mock del cargador GTFS
- Validación de endpoints
- Manejo de fechas y calendar.txt
- Metadatos

---

## 🗂 Estructura del proyecto

```
cercanias-api/
│
├── app/
│   ├── core/          # Loader GTFS + utilidades
│   ├── routers/       # Routers FastAPI
│   ├── models/        # Esquemas Pydantic
│   ├── deps/          # Dependencias inyectables (auth, manager…)
│   └── __init__.py    # Crea la app FastAPI
│
├── data/
│   └── gtfs/          # ZIP + metadatos
│
├── tests/             # Tests unitarios
├── run.py             # Lanzador de la API
├── requirements.txt
└── README.md
```

---

## 🚧 Roadmap (ideas futuras)

- Cache Redis opcional
- GTFS-RT (vehículos, alertas, retrasos)
- Endpoint de proximidad geográfica
- Históricos y agregaciones
- CLI: `cercanias-cli search --stop "Nord"`

---

## ❤️ Contribuir

Pull Requests abiertas.

Si deseas colaborar:

```
git checkout -b feature/lo-que-sea
```

---

## 📄 Licencia

MIT — Libre para uso personal y comercial.
