from fastapi import APIRouter, HTTPException
from typing import List
from app.services.gtfs_service import get_routes, get_route
from app.schemas.route import Route
from app.utils.response import success_response

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get(
	"/",
	summary="Listar rutas",
	description=(
		"Devuelve una lista de rutas.\n\n"
		"Ejemplo de petición:\n``GET /routes/``\n\n"
		"Ejemplo de respuesta (200):\n``{\n  \"status\": \"ok\",\n  \"data\": [ { \"route_id\": \"R1\", \"route_short_name\": \"L1\" } ]\n}``\n\n"
		"Campos principales:\n- `route_id`, `route_short_name`, `route_long_name`, `route_type`."
	),
)
def list_routes():
	data = get_routes()
	return success_response(data)


@router.get(
	"/{route_id}",
	summary="Obtener ruta por ID",
	description=(
		"Devuelve los datos de la ruta indicada por `route_id`.\n\n"
		"Parámetros:\n- `route_id` (string): identificador de la ruta.\n\n"
		"Ejemplo de petición:\n``GET /routes/R1``\n\n"
		"Ejemplo de respuesta (200):\n``{ \"status\": \"ok\", \"data\": { \"route_id\": \"R1\", \"route_short_name\": \"L1\" } }``\n\n"
		"Errores:\n- 404: retornado si la ruta no existe (Problem Details)."
	),
)
def read_route(route_id: str):
	r = get_route(route_id)
	if not r:
		raise HTTPException(status_code=404, detail="Route not found")
	return success_response(r)
