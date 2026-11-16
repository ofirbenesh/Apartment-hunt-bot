from dataclasses import dataclass
from typing import Optional


@dataclass
class Listing:
    post_id: str
    post_url: str
    raw_text: str
    author: str = ""
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    rooms: Optional[float] = None
    price: Optional[int] = None
    floor: Optional[int] = None
    has_broker: bool = False
    balcony: bool = False
    parking: bool = False
    shelter: bool = False
