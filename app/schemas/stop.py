from pydantic import BaseModel
from typing import Optional


class Stop(BaseModel):
    stop_id: str
    stop_name: Optional[str] = None
    stop_lat: Optional[float] = None
    stop_lon: Optional[float] = None
