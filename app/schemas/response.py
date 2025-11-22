from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    status: str
    data: Optional[T] = None


class ListEnvelope(BaseModel):
    status: str
    data: List[dict]


class ItemEnvelope(BaseModel):
    status: str
    data: Optional[dict]
