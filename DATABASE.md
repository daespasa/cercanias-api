# Base de Datos GTFS - Documentación

Esta API utiliza una base de datos SQLite completa y optimizada con todos los datos GTFS de Renfe Cercanías.

## Estructura de la Base de Datos

### Tablas Principales

#### 1. **agency** (1 registro)
Información sobre la agencia de transporte (Renfe).
- `agency_id` - Identificador único de la agencia
- `agency_name` - Nombre de la agencia
- `agency_url` - Sitio web
- `agency_timezone` - Zona horaria
- `agency_lang` - Idioma
- `agency_phone` - Teléfono de contacto

#### 2. **routes** (514 registros)
Rutas/líneas de cercanías disponibles.
- `route_id` - Identificador único de la ruta
- `route_short_name` - Nombre corto (ej: "C1", "C2")
- `route_long_name` - Nombre descriptivo completo
- `route_type` - Tipo de transporte (tren)
- `route_color` - Color hexadecimal de la línea
- `route_text_color` - Color del texto

**Índices:**
- `ix_routes_route_id` - Búsqueda por ID
- `ix_routes_route_type` - Filtrado por tipo

#### 3. **stops** (1,133 registros)
Estaciones y paradas del sistema.
- `stop_id` - Identificador único (STRING, preserva ceros iniciales: "04040")
- `stop_name` - Nombre de la estación
- `stop_lat` - Latitud
- `stop_lon` - Longitud
- `wheelchair_boarding` - Accesibilidad

**Índices:**
- `ix_stops_stop_id` - Búsqueda por ID (crítico para rendimiento)
- `ix_stops_location` - Búsqueda espacial por lat/lon

#### 4. **calendar** (360 registros)
Calendarios de servicio que definen qué días opera cada servicio.
- `service_id` - Identificador del calendario
- `monday`, `tuesday`, ..., `sunday` - Días de operación (0/1)
- `start_date` - Fecha de inicio (YYYYMMDD)
- `end_date` - Fecha de fin (YYYYMMDD)

**Índices:**
- `ix_calendar_service_id` - Búsqueda por servicio
- `ix_calendar_dates` - Búsqueda por rango de fechas

#### 5. **trips** (124,504 registros)
Viajes individuales de cada ruta.
- `route_id` - Ruta a la que pertenece
- `service_id` - Calendario de servicio
- `trip_id` - Identificador único del viaje
- `trip_headsign` - Destino mostrado
- `trip_short_name` - Nombre corto del viaje
- `shape_id` - Geometría del recorrido

**Índices:**
- `ix_trips_trip_id` - Búsqueda por ID
- `ix_trips_route_id` - Filtrado por ruta
- `ix_trips_service_id` - Filtrado por servicio
- `ix_trips_shape_id` - Acceso a geometría

#### 6. **stop_times** (1,797,944 registros) 
**LA TABLA MÁS CRÍTICA** - Horarios de llegada/salida en cada parada.
- `trip_id` - Viaje al que pertenece
- `arrival_time` - Hora de llegada (HH:MM:SS)
- `departure_time` - Hora de salida (HH:MM:SS)
- `stop_id` - Parada
- `stop_sequence` - Orden de la parada en el viaje
- `pickup_type` - Tipo de subida
- `drop_off_type` - Tipo de bajada

**Índices (altamente optimizados):**
- `ix_stop_times_trip_id` - Por viaje
- `ix_stop_times_stop_id` - Por parada
- `ix_stop_times_sequence` - Por secuencia
- `ix_stop_times_stop_trip` - Búsquedas combinadas parada+viaje
- `ix_stop_times_trip_sequence` - Búsquedas combinadas viaje+secuencia
- `ix_stop_times_arrival` - Búsqueda por hora de llegada
- `ix_stop_times_departure` - Búsqueda por hora de salida

#### 7. **shapes** (57,406 registros)
Geometría de las rutas (trazado en el mapa).
- `shape_id` - Identificador de la forma
- `shape_pt_lat` - Latitud del punto
- `shape_pt_lon` - Longitud del punto
- `shape_pt_sequence` - Orden del punto

**Índices:**
- `ix_shapes_shape_id` - Por ID de forma
- `ix_shapes_sequence` - Por forma+secuencia (trazado ordenado)

#### 8. **transfers** (19 registros)
Transbordos recomendados entre líneas.
- `from_stop_id` - Parada de origen
- `to_stop_id` - Parada de destino
- `from_route_id` - Ruta de origen
- `to_route_id` - Ruta de destino
- `from_trip_id` - Viaje de origen (opcional)
- `to_trip_id` - Viaje de destino (opcional)
- `transfer_type` - Tipo de transbordo (0=recomendado, 2=requiere tiempo mínimo)
- `min_transfer_time` - Tiempo mínimo en segundos

**Índices:**
- `ix_transfers_from_stop` - Por parada origen
- `ix_transfers_to_stop` - Por parada destino
- `ix_transfers_type` - Por tipo de transbordo

---

### Vistas Precomputadas

Para optimizar consultas comunes, la base de datos incluye vistas:

#### **active_services_today**
Servicios activos para la fecha actual, considerando el día de la semana.
```sql
SELECT DISTINCT service_id FROM active_services_today;
```

#### **stops_with_parents**
Paradas con información de sus estaciones padre (para estaciones con múltiples andenes).
```sql
SELECT * FROM stops_with_parents WHERE stop_id = '04040';
```

#### **routes_with_agency**
Rutas con información completa de la agencia.
```sql
SELECT * FROM routes_with_agency WHERE route_short_name = 'C1';
```

#### **trips_detailed**
Viajes con detalles de la ruta (nombre, tipo, color).
```sql
SELECT * FROM trips_detailed WHERE route_id = '...';
```

---

## Optimizaciones de Rendimiento

### 1. Pragmas Configurados
- `PRAGMA foreign_keys=ON` - Integridad referencial
- `PRAGMA journal_mode=WAL` - Modo Write-Ahead Log para concurrencia
- `PRAGMA cache_size=-64000` - Caché de 64MB en memoria
- `PRAGMA mmap_size=268435456` - 256MB de memoria mapeada
- `PRAGMA synchronous=NORMAL` - Balance entre seguridad y velocidad

### 2. Índices Compuestos
Se crearon índices compuestos para consultas típicas:
- `(stop_id, trip_id)` - Búsqueda de horarios de una parada en un viaje
- `(trip_id, stop_sequence)` - Recorrido ordenado de paradas de un viaje
- `(stop_lat, stop_lon)` - Búsquedas espaciales

### 3. Estadísticas del Optimizador
Se ejecutó `ANALYZE` para que el optimizador de consultas de SQLite pueda elegir los mejores planes de ejecución.

---

## Tamaño y Estadísticas

- **Tamaño total:** 321 MB
- **Total de registros:** ~2 millones
- **Tiempo de construcción:** ~24 segundos
- **Tablas principales:** 9
- **Vistas:** 4
- **Índices:** 25+

---

## Consultas de Ejemplo

### Obtener horarios de una parada
```sql
SELECT 
    st.arrival_time,
    st.departure_time,
    t.trip_headsign,
    r.route_short_name
FROM stop_times st
JOIN trips t ON st.trip_id = t.trip_id
JOIN routes r ON t.route_id = r.route_id
WHERE st.stop_id = '04040'
AND t.service_id IN (SELECT service_id FROM active_services_today)
ORDER BY st.arrival_time
LIMIT 10;
```

### Buscar paradas cercanas
```sql
SELECT 
    stop_id,
    stop_name,
    stop_lat,
    stop_lon
FROM stops
WHERE stop_lat BETWEEN 40.4 AND 40.5
AND stop_lon BETWEEN -3.8 AND -3.7
ORDER BY stop_lat, stop_lon;
```

### Ver recorrido completo de un viaje
```sql
SELECT 
    st.stop_sequence,
    s.stop_name,
    st.arrival_time,
    st.departure_time
FROM stop_times st
JOIN stops s ON st.stop_id = s.stop_id
WHERE st.trip_id = 'TRIP_ID'
ORDER BY st.stop_sequence;
```

### Obtener geometría de una ruta
```sql
SELECT 
    shape_pt_lat,
    shape_pt_lon,
    shape_pt_sequence
FROM shapes
WHERE shape_id = 'SHAPE_ID'
ORDER BY shape_pt_sequence;
```

### Consultar transbordos disponibles desde una parada
```sql
SELECT 
    t.*,
    r1.route_short_name as from_route,
    r2.route_short_name as to_route
FROM transfers t
JOIN routes r1 ON t.from_route_id = r1.route_id
JOIN routes r2 ON t.to_route_id = r2.route_id
WHERE t.from_stop_id = '65000';
```

---

## Próximos Pasos

Con esta base de datos completa, se pueden crear nuevos endpoints para:

1. **Búsqueda de rutas** - Encontrar la mejor ruta entre dos paradas
2. **Búsqueda geográfica** - Paradas cercanas a una ubicación
3. **Visualización de mapas** - Trazar rutas con shapes
4. **Transbordos** - Sugerir transbordos óptimos
5. **Servicios activos** - Filtrar por calendario y excepciones
6. **Estadísticas** - Análisis de frecuencias, tiempos de viaje, etc.

La estructura está optimizada para consultas rápidas incluso con casi 2 millones de registros de horarios.
