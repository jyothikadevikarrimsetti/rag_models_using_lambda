from pydantic import BaseModel, Field
from typing import List


class VectorDocument(BaseModel):
    id: str = Field(..., alias="_id")
    path: str
    href: str
    title: str
    summary: str
    text: str
    embedding: List[float]
