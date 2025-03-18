from pydantic import BaseModel
from typing import Union

class Order(BaseModel):
    type: str
    price: Union[int, None] = None
    volume: int
    timestamp: float