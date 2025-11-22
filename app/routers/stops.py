from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.gtfs_service import get_stops, get_stop
from app.schemas.stop import Stop
from app.utils.response import success_response

router = APIRouter(prefix="/stops", tags=["Stops"])


@router.get(
	"/",
	summary="Listar paradas",
	description=(
		"Devuelve una lista de paradas disponibles.\n\n"
		"Parámetros:\n"
		"- `limit` (int, opcional): limita el número de resultados devueltos (por defecto 200).\n\n"
		"Ejemplo de petición:\n"
		"``GET /stops/?limit=10``\n\n"
		"Ejemplo de respuesta (200):\n"
		"``{\n  \"status\": \"ok\",\n  \"data\": [ { \"stop_id\": \"S1\", \"stop_name\": \"Estación 1\" } ]\n}``"
	),
)
def list_stops(limit: Optional[int] = 200):
	"""Lista paradas. Opcional `limit` para limitar resultados."""
	data = get_stops(limit=limit)
	return success_response(data)


@router.get(
	"/{stop_id}",
	summary="Obtener parada por ID",
	description=(
		"Devuelve la parada identificada por `stop_id`.\n\n"
		"Parámetros:\n- `stop_id` (string): identificador de la parada.\n\n"
		"Ejemplo de petición:\n``GET /stops/S1``\n\n"
		"Ejemplo de respuesta (200):\n``{ \"status\": \"ok\", \"data\": { \"stop_id\": \"S1\", \"stop_name\": \"Estación 1\" } }``\n\n"
		"Errores:\n- 404: retornado si la parada no existe (Problem Details con `title`, `status`, `detail`)."
	),
)
def read_stop(stop_id: str):
	s = get_stop(stop_id)
	if not s:
		raise HTTPException(status_code=404, detail="Stop not found")
	return success_response(s)
