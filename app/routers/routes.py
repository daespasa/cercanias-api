from fastapi import APIRouter, HTTPException
from typing import List
from app.services.gtfs_service import get_routes, get_route
from app.services.gtfs_service import get_route_stops
from app.schemas.route import Route
from app.schemas.response import Envelope
from app.utils.response import success_response

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get(
	"/",
	summary="Listar rutas",
    response_model=Envelope[List[Route]],
    description=(
        "Listado de rutas definidas en el feed GTFS. Cada entrada incluye metadatos "
        "comunes (identificador, nombre corto, nombre largo y tipo).\n\n"
        "Ejemplo:\n``GET /routes/``\n\n"
        "Campos clave: `route_id`, `route_short_name`, `route_long_name`, `route_type`."
    ),
)
def list_routes():
	data = get_routes()
	return success_response(data)


@router.get(
	"/{route_id}",
	summary="Obtener ruta por ID",
    response_model=Envelope[Route],
    description=(
        "Recupera los metadatos de una ruta concreta identificada por `route_id`. "
        "Útil para obtener información detallada o para enlazar con `trips`.\n\n"
        "Parámetros:\n- `route_id` (string): identificador de la ruta en el feed GTFS.\n\n"
        "Ejemplo:\n``GET /routes/40T0001C1``\n\n"
        "Respuestas de error:\n- `404 Not Found`: ruta no encontrada (Problem Details)."
    ),
    responses={404: {"description": "Route not found"}},
)

def read_route(route_id: str):
    r = get_route(route_id)
    if not r:
        raise HTTPException(status_code=404, detail="Route not found")
    return success_response(r)


@router.get(
    "/{route_id}/stops",
    summary="Obtener paradas de una ruta",
    response_model=Envelope[List[dict]],
    description=(
        "Devuelve las paradas asociadas a una ruta, ordenadas por `stop_sequence` y agrupadas "
        "por `direction_id`. Útil para desplegar el recorrido de ida y vuelta."
    ),
)
def route_stops(route_id: str):
    data = get_route_stops(route_id)
    return success_response(data)
