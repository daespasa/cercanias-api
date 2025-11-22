from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.gtfs_service import get_stops, get_stop
from app.schemas.stop import Stop
from app.schemas.response import Envelope
from app.utils.response import success_response
from app.services.gtfs_service import search_stops, list_stop_names, get_upcoming_trains
from app.schemas.upcoming import UpcomingTrains

router = APIRouter(prefix="/stops", tags=["Stops"])


@router.get(
	"/",
	summary="Listar paradas",
	response_model=Envelope[List[Stop]],
	description=(
		"Devuelve un listado de paradas disponibles en el feed GTFS. "
		"Se admite paginación simple mediante el parámetro `limit`.\n\n"
		"Parámetros:\n- `limit` (int, opcional): límite máximo de resultados a devolver (por defecto 200).\n\n"
		"Ejemplo:\n``GET /stops/?limit=10``"
	),
)
def list_stops(limit: Optional[int] = 200):
	"""Lista paradas. Opcional `limit` para limitar resultados."""
	data = get_stops(limit=limit)
	return success_response(data)


@router.get(
	"/search",
	summary="Buscar paradas por nombre",
	response_model=Envelope[List[Stop]],
	description=(
		"Busca paradas cuyo nombre contenga la cadena proporcionada (no distingue mayúsculas/minúsculas).\n\n"
		"Parámetros:\n- `q` (string): término de búsqueda en el nombre de la parada.\n- `limit` (int, opcional): número máximo de resultados (por defecto 100).\n\n"
		"Ejemplo:\n``GET /stops/search?q=estaci%C3%B3n&limit=10``"
	),
)
def search_stops_endpoint(q: str, limit: Optional[int] = 100):
	results = search_stops(name_query=q, limit=limit)
	return success_response(results)


@router.get(
	"/names",
	summary="Listar nombres de paradas",
	response_model=Envelope[List[dict]],
	description=(
		"Devuelve una lista de pares `stop_id`/`stop_name` disponibles en el feed. "
		"Útil para autocompletar o navegación en UIs.\n\n"
		"Parámetros:\n- `limit` (int, opcional): máximo de entradas a devolver (por defecto 1000)."
	),
)
def list_names(limit: Optional[int] = 1000):
	data = list_stop_names(limit=limit)
	return success_response(data)


@router.get(
	"/{stop_id}",
	summary="Obtener parada por ID",
	response_model=Envelope[Stop],
	description=(
		"Recupera la información de una parada concreta identificada por su `stop_id`. "
		"El `stop_id` se expresa como un entero y corresponde al identificador del feed GTFS.\n\n"
		"Parámetros:\n- `stop_id` (int): identificador numérico de la parada.\n\n"
		"Ejemplo:\n``GET /stops/65000``\n\n"
		"Respuestas de error:\n- `404 Not Found`: la parada no existe (detalle en formato Problem Details)."
	),
	responses={404: {"description": "Stop not found"}},
)
def read_stop(stop_id: str):
	s = get_stop(stop_id)
	if not s:
		raise HTTPException(status_code=404, detail="Stop not found")
	return success_response(s)


@router.get(
	"/{stop_id}/upcoming",
	summary="Próximos trenes en una estación",
	response_model=Envelope[UpcomingTrains],
	description=(
		"Devuelve los próximos trenes que salen y llegan a una estación específica, "
		"con el tiempo restante en minutos hasta la salida/llegada.\n\n"
		"Parámetros:\n"
		"- `stop_id` (string): identificador de la parada.\n"
		"- `current_time` (string, opcional): hora actual en formato HH:MM:SS (por defecto: hora actual del sistema).\n"
		"- `limit` (int, opcional): número máximo de trenes a devolver por categoría (salidas/llegadas, por defecto 10).\n\n"
		"Respuesta:\n"
		"- `stop_id`: ID de la parada\n"
		"- `stop_name`: Nombre de la estación\n"
		"- `current_time`: Hora de consulta\n"
		"- `departures`: Lista de trenes que salen (con minutos hasta salida)\n"
		"- `arrivals`: Lista de trenes que llegan (con minutos hasta llegada)\n\n"
		"Cada tren incluye:\n"
		"- `route_short_name`: Línea (ej: 'C1', 'C2')\n"
		"- `trip_headsign`: Destino del tren\n"
		"- `scheduled_time`: Hora programada (HH:MM:SS)\n"
		"- `minutes_until`: Minutos restantes hasta salida/llegada\n\n"
		"Ejemplo:\n``GET /stops/04040/upcoming`` o ``GET /stops/04040/upcoming?current_time=14:30:00&limit=5``"
	),
	responses={404: {"description": "Stop not found"}},
)
def get_upcoming_trains_endpoint(stop_id: str, current_time: Optional[str] = None, limit: Optional[int] = 10):
	"""Obtiene los próximos trenes que salen y llegan a una estación con minutos restantes."""
	data = get_upcoming_trains(stop_id=stop_id, current_time=current_time, limit=limit)
	if not data.get('stop_name'):
		raise HTTPException(status_code=404, detail="Stop not found")
	return success_response(data)
