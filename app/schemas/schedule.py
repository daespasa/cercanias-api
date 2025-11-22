from pydantic import BaseModel
from typing import Optional


class ScheduleEntry(BaseModel):
    trip_id: str
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    stop_id: Optional[str] = None
    stop_sequence: Optional[int] = None
    route_id: Optional[str] = None
    route_short_name: Optional[str] = None
    service_date: Optional[str] = None
