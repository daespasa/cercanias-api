from fastapi import APIRouter
from typing import List, Optional
from app.services.gtfs_service import get_schedule
from app.schemas.schedule import ScheduleEntry
from app.utils.response import success_response

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get(
	"/",
	summary="Obtener horarios / schedule",
	description=(
		"Devuelve entradas de horario combinando `stop_times`, `trips` y `routes`.\n\n"
		"Parámetros opcionales:\n"
		"- `stop_id`: filtra por parada (ej. `S1`)\n"
		"- `route_id`: filtra por ruta (ej. `R1`)\n"
		"- `date`: fecha en formato `YYYY-MM-DD` para filtrar servicios activos (usa `calendar.txt` y `calendar_dates.txt`)\n"
		"- `limit`: límite de resultados (por defecto 200)\n\n"
		"Ejemplo de petición:\n``GET /schedule/?stop_id=S1&date=2025-06-02&limit=50``\n\n"
		"Ejemplo de respuesta (200):\n``{\n  \"status\": \"ok\",\n  \"data\": [ { \"trip_id\": \"T1\", \"arrival_time\": \"08:00:00\", \"stop_id\": \"S1\", \"route_id\": \"R1\" } ]\n}``\n\n"
		"Notas de implementación:\n"
		"- Si `date` es provisto, la API intentará filtrar los trips cuya `service_id` está activo en ese día usando `calendar.txt` y `calendar_dates.txt`.\n"
		"- Si los archivos de calendario no están presentes, `date` puede que no tenga efecto."
	),
)
def list_schedule(stop_id: Optional[str] = None, route_id: Optional[str] = None, date: Optional[str] = None, limit: int = 200):
	"""Devuelve las próximas entradas de horario filtradas por `stop_id` o `route_id`.

	`date` filtra usando `calendar.txt` y `calendar_dates.txt` cuando esos archivos están presentes.
	"""
	data = get_schedule(stop_id=stop_id, route_id=route_id, date=date, limit=limit)
	return success_response(data)
