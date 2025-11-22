from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.gtfs_service import get_stops, get_stop
from app.schemas.stop import Stop
from app.schemas.response import Envelope
from app.utils.response import success_response
from app.services.gtfs_service import search_stops, list_stop_names

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
