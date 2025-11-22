from fastapi import APIRouter
from typing import List, Optional
from app.services.gtfs_service import get_schedule
from app.schemas.schedule import ScheduleEntry
from app.schemas.response import Envelope
from app.utils.response import success_response

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get(
	"/",
	summary="Obtener horarios / schedule",
	response_model=Envelope[List[ScheduleEntry]],
	description=(
		"Consulta los horarios combinando `stop_times`, `trips` y `routes`. "
		"Soporta filtros por parada, por ruta y por fecha de servicio. Las fechas "
		"deben proporcionarse en formato `YYYY-MM-DD`.\n\n"
		"Parámetros opcionales:\n- `stop_id` (int): filtra por identificador de parada.\n- `route_id` (string): filtra por identificador de ruta.\n- `date` (string): fecha en formato `YYYY-MM-DD` para limitar a servicios activos.\n- `limit` (int): límite de resultados (por defecto 200).\n\n"
		"Ejemplo:\n``GET /schedule/?stop_id=65000&date=2025-06-02``"
	),
)
def list_schedule(stop_id: Optional[int] = None, route_id: Optional[str] = None, date: Optional[str] = None, limit: int = 200):
	"""Devuelve las entradas de horario filtradas por parámetros opcionales.

	El parámetro `date` aplica la lógica de `calendar` y `calendar_dates` del feed.
	"""
	data = get_schedule(stop_id=stop_id, route_id=route_id, date=date, limit=limit)
	return success_response(data)
