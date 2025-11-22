# Endpoint: Próximos Trenes

## Descripción

El nuevo endpoint `/stops/{stop_id}/upcoming` permite consultar los próximos trenes que **salen** y **llegan** a una estación específica, mostrando el **tiempo restante en minutos** hasta la salida o llegada.

## Características

✅ **Tiempo en minutos** - Calcula automáticamente los minutos restantes hasta cada tren  
✅ **Hora actual automática** - Si no se especifica, usa la hora del sistema  
✅ **Separación salidas/llegadas** - Distingue entre trenes que salen vs. llegan  
✅ **Información completa** - Incluye línea, destino, hora programada  
✅ **Servicios activos** - Solo muestra trenes que operan hoy según el calendario  

## Uso

### Endpoint
```
GET /stops/{stop_id}/upcoming
```

### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `stop_id` | string | ✅ Sí | ID de la estación (ej: "04040") |
| `current_time` | string | ❌ No | Hora en formato HH:MM:SS (default: hora actual) |
| `limit` | integer | ❌ No | Número máximo de trenes por categoría (default: 10) |

### Ejemplos

#### 1. Consultar próximos trenes con hora actual
```bash
GET /stops/04040/upcoming
```

**Respuesta:**
```json
{
  "status": "success",
  "data": {
    "stop_id": "04040",
    "stop_name": "Zaragoza Delicias",
    "current_time": "14:23:45",
    "departures": [
      {
        "trip_id": "40T0010C1_210_23B",
        "route_short_name": "C1",
        "route_long_name": null,
        "trip_headsign": null,
        "direction_id": null,
        "scheduled_time": "14:35:00",
        "minutes_until": 11,
        "stop_sequence": 3
      },
      {
        "trip_id": "40T0010C1_211_23B",
        "route_short_name": "C1",
        "route_long_name": null,
        "trip_headsign": null,
        "direction_id": null,
        "scheduled_time": "15:05:00",
        "minutes_until": 41,
        "stop_sequence": 3
      }
    ],
    "arrivals": [
      {
        "trip_id": "40T0010C1_208_23B",
        "route_short_name": "C1",
        "route_long_name": null,
        "trip_headsign": null,
        "direction_id": null,
        "scheduled_time": "14:30:00",
        "minutes_until": 6,
        "stop_sequence": 8
      }
    ]
  }
}
```

#### 2. Consultar con hora específica
```bash
GET /stops/04040/upcoming?current_time=10:00:00&limit=3
```

**Respuesta:**
```json
{
  "status": "success",
  "data": {
    "stop_id": "04040",
    "stop_name": "Zaragoza Delicias",
    "current_time": "10:00:00",
    "departures": [
      {
        "route_short_name": "C1",
        "scheduled_time": "10:23:00",
        "minutes_until": 23
      },
      {
        "route_short_name": "C1",
        "scheduled_time": "10:57:00",
        "minutes_until": 57
      },
      {
        "route_short_name": "C1",
        "scheduled_time": "11:21:00",
        "minutes_until": 81
      }
    ],
    "arrivals": [
      {
        "route_short_name": "C1",
        "scheduled_time": "10:22:00",
        "minutes_until": 22
      }
    ]
  }
}
```

#### 3. Parada no encontrada
```bash
GET /stops/99999/upcoming
```

**Respuesta:**
```json
{
  "detail": "Stop not found"
}
```
**Status:** `404 Not Found`

## Campos de Respuesta

### Nivel superior
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `stop_id` | string | ID de la estación consultada |
| `stop_name` | string | Nombre de la estación |
| `current_time` | string | Hora de consulta (HH:MM:SS) |
| `departures` | array | Lista de trenes que **salen** |
| `arrivals` | array | Lista de trenes que **llegan** |

### Cada tren (departure/arrival)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `trip_id` | string | Identificador único del viaje |
| `route_short_name` | string | Nombre corto de la línea (ej: "C1") |
| `route_long_name` | string | Nombre largo de la línea |
| `trip_headsign` | string | Destino del tren |
| `direction_id` | integer | Dirección del viaje (0 o 1) |
| `scheduled_time` | string | Hora programada (HH:MM:SS) |
| `minutes_until` | integer | **⏱️ Minutos restantes** |
| `stop_sequence` | integer | Posición de la parada en el recorrido |

## Casos de Uso

### 🚉 Paneles de información en estaciones
Mostrar en tiempo real los próximos trenes con cuenta regresiva:
```
SALIDAS PRÓXIMAS
C1 → en 5 minutos (10:35)
C2 → en 12 minutos (10:42)
```

### 📱 Aplicaciones móviles
Notificar a usuarios cuándo llega su tren:
```javascript
if (minutes_until <= 5) {
  notify("¡Tu tren sale en " + minutes_until + " minutos!");
}
```

### 🗺️ Planificadores de rutas
Calcular tiempos de espera y conexiones:
```javascript
const waitTime = departure.minutes_until;
const totalTime = travelTime + waitTime;
```

### 📊 Análisis de frecuencias
Estudiar intervalos entre trenes:
```sql
SELECT route_short_name, 
       AVG(minutes_between_trains) as avg_frequency
FROM upcoming_analysis
GROUP BY route_short_name;
```

## Notas Técnicas

### ⚡ Rendimiento
- Usa índices optimizados en `stop_times`, `trips`, y `routes`
- Consulta solo servicios activos según calendario
- Tiempo de respuesta: < 100ms típicamente

### 📅 Servicios Activos
- Consulta automática del calendario GTFS
- Considera día de la semana actual
- Respeta fechas de inicio/fin de servicio
- Soporta excepciones vía `calendar_dates` (si están disponibles)

### 🕐 Cálculo de Minutos
- Compara hora actual vs. hora programada
- Maneja correctamente horarios después de medianoche (ej: 25:30:00)
- Minutos negativos indican trenes pasados (no se devuelven)

### 🔄 Actualización de Datos
- Los horarios se actualizan automáticamente cada 24 horas
- La BD se reconstruye desde el ZIP de Renfe
- Descarga automática configurada en `AUTO_DOWNLOAD_GTFS=true`

## Limitaciones Conocidas

1. **No incluye retrasos en tiempo real** - Solo horarios programados
2. **direction_id puede ser null** - Algunos datos GTFS no lo incluyen
3. **trip_headsign puede estar vacío** - Depende de la calidad de datos GTFS
4. **Solo servicios del día actual** - No consulta múltiples días

## Próximas Mejoras

- [ ] Integración con datos de tiempo real (GTFS-RT)
- [ ] Notificaciones de retrasos/cancelaciones
- [ ] Filtrado por línea específica
- [ ] Búsqueda de trenes entre dos estaciones
- [ ] Histórico de puntualidad

## Testing

El endpoint incluye 5 tests automatizados:
- ✅ Consulta con hora específica
- ✅ Consulta con hora actual del sistema
- ✅ Manejo de paradas inexistentes (404)
- ✅ Horarios de madrugada
- ✅ Validación completa de estructura de respuesta

```bash
pytest tests/test_upcoming_trains.py -v
```

## Documentación Interactiva

Visita `/docs` en el servidor para probar el endpoint con Swagger UI.

---

**Endpoint implementado:** ✅ 2025-11-22  
**Tests:** 5/5 pasando  
**Estado:** Producción
