from fastapi import APIRouter, Query
from typing import Optional
from app.core.gtfs_manager import gtfs_manager
from app.utils.response import success_response

router = APIRouter(prefix="/realtime", tags=["Realtime"])


@router.get(
    "/alerts",
    summary="Alertas en tiempo real",
    description=(
        "Recupera alertas e incidencias en tiempo real extraídas del feed RT. "
        "Las alertas se normalizan en un formato serializable para permitir su "
        "consumo por integraciones externas."
    ),
)
def get_alerts():
    alerts = gtfs_manager.get_rt_alerts()
    # The alerts are protobuf Alert objects; return as dicts where possible
    result = []
    for a in alerts:
        try:
            result.append({
                "informed_entity": [e.SerializeToString().hex() for e in a.informed_entity] if hasattr(a, "informed_entity") else None,
                "header_text": a.header_text.translation[0].text if a.header_text.translation else None,
                "description_text": a.description_text.translation[0].text if a.description_text.translation else None,
            })
        except Exception:
            result.append(str(a))
    return success_response(result)


@router.get(
    "/vehicles",
    summary="Posiciones de vehículos en tiempo real",
    description=(
        "Proporciona la posición y estado actual de vehículos en operación. "
        "Soporta filtros por `route_id` y `trip_id`. Los datos devueltos son "
        "ligeros (lat/lon, bearing, velocidad y estado)."
    ),
)
def get_vehicles(route_id: Optional[str] = Query(None), trip_id: Optional[str] = Query(None)):
    vehicles = gtfs_manager.get_rt_vehicles(route_id=route_id, trip_id=trip_id)
    out = []
    for v in vehicles:
        try:
            pos = v.position
            out.append({
                "trip_id": getattr(v.trip, "trip_id", None),
                "route_id": getattr(v.trip, "route_id", None),
                "latitude": pos.latitude if pos is not None else None,
                "longitude": pos.longitude if pos is not None else None,
                "bearing": pos.bearing if pos is not None else None,
                "speed": pos.speed if pos is not None else None,
                "current_status": v.current_status if hasattr(v, "current_status") else None,
            })
        except Exception:
            out.append(str(v))
    return success_response(out)


@router.get(
    "/trip_updates",
    summary="Trip updates en tiempo real",
    description=(
        "Actualizaciones en tiempo real sobre viajes: variaciones de horario, "
        "cancelaciones y reprogramaciones. Se puede filtrar por `trip_id` o "
        "`route_id`."
    ),
)
def get_trip_updates(trip_id: Optional[str] = Query(None), route_id: Optional[str] = Query(None)):
    updates = gtfs_manager.get_rt_trip_updates(trip_id=trip_id, route_id=route_id)
    out = []
    for u in updates:
        try:
            out.append({
                "trip_id": getattr(u.trip, "trip_id", None),
                "route_id": getattr(u.trip, "route_id", None),
                "stop_time_updates": [st.SerializeToString().hex() for st in u.stop_time_update] if hasattr(u, "stop_time_update") else None,
            })
        except Exception:
            out.append(str(u))
    return success_response(out)
