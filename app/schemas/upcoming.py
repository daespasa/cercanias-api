"""Schemas para próximos trenes."""
from pydantic import BaseModel
from typing import Optional


class UpcomingTrain(BaseModel):
    """Información de un tren próximo a salir o llegar."""
    trip_id: str
    route_short_name: Optional[str] = None
    route_long_name: Optional[str] = None
    trip_headsign: Optional[str] = None
    direction_id: Optional[int] = None
    scheduled_time: str  # HH:MM:SS format
    minutes_until: int  # Minutes until departure/arrival (negative if already passed)
    stop_sequence: int


class UpcomingTrains(BaseModel):
    """Trenes próximos a salir y llegar en una estación."""
    stop_id: str
    stop_name: Optional[str] = None
    current_time: str  # HH:MM:SS format of query time
    departures: list[UpcomingTrain] = []  # Trenes que salen
    arrivals: list[UpcomingTrain] = []  # Trenes que llegan
