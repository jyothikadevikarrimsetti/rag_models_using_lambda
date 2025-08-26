from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Document(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    filename: str
    filepath: str
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_date: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeObject(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    document_id: str
    summary: str
    keywords: List[str] = Field(default_factory=list)
    intent: Optional[str] = Field(default="")
    entities: List[str] = Field(default_factory=list)
    language: str = "en"
    topic: Optional[str] = Field(default="")
    model_name: str
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_date: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingInfo(BaseModel):
    config_id: str
    vector: List[float]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    meta: dict = {}


class Chunk(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    document_id: str
    chunk_text: str
    chunk_index: int
    start_pos: int
    end_pos: int
    embeddings: List[EmbeddingInfo] = []


class EmbeddingConfig(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    model_name: str
    embedding_size: int
    distance_metric: str = "cosine"
    is_active: bool = True
    retraining_start: bool = False
    retraining_end: bool = False
    retraining_success: bool = False
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_date: datetime = Field(default_factory=datetime.utcnow)


class Module(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    module_name: str
    module_type: str
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_date: datetime = Field(default_factory=datetime.utcnow)


# Legacy model for backward compatibility
class VectorDocument(BaseModel):
    id: str = Field(..., alias="_id")
    path: str
    href: str
    title: str
    summary: str
    text: str
    embedding: List[float]
