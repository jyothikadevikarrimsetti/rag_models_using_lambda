from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Metadata(BaseModel):
    path: str
    repo_url: str
    intent_category: str
    version: str
    modified_time: datetime
    csp: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmbeddingMeta(BaseModel):
    model_name: str
    model_version: str
    dimensionality: int
    embedding_method: str
    tokenizer: str
    embedding_date: datetime
    source_field: str
    embedding_quality_score: float
    reembedding_required: bool
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Module(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    module_id: str = Field(..., alias="module_id")
    module_tag: List[str] = Field(default_factory=list, alias="module_tag")
    module_link: List[str] = Field(default_factory=list, alias="module_link")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class KnowledgeObject(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    title: str
    named_entity: str
    summary: str
    content: str
    keywords: str
    texts: str
    is_terraform: bool
    metadata: Metadata
    module_id: str
    chunk_ids: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Chunk(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    document_id: str
    chunk_id: int
    chunk_start: int
    chunk_end: int
    chunk_text: str
    embedding: List[float] = Field(default_factory=list)
    embedding_meta: EmbeddingMeta
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Legacy model for backward compatibility
class VectorDocument(BaseModel):
    id: str = Field(..., alias="_id")
    path: str
    href: str
    title: str
    summary: str
    text: str
    embedding: List[float]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
