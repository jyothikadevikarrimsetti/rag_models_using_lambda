import os
import json
from typing import List
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from models.datamodel_pdantic import VectorDocument, Document, KnowledgeObject, Chunk, EmbeddingConfig, Module

# -------------------------------
# MongoDB Setup
# -------------------------------
load_dotenv("config/.env")
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient("mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
db = client[os.getenv("MONGO_DB_NAME", "rag_db")]

# Collections
documents_collection = db["documents"]
knowledge_objects_collection = db["knowledge_objects"]
chunks_collection = db["chunks"]
embedding_configs_collection = db["embedding_configs"]
modules_collection = db["modules"]
collection = db[os.getenv("MONGO_COLLECTION_NAME", "dmodel")]  # Legacy collection


def insert_document(doc: Document):
    """Insert a new document into the documents collection."""
    try:
        result = documents_collection.insert_one(doc.model_dump(by_alias=True, exclude_none=True))
        print(f"✅ Inserted document: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Document insert failed: {e}")
        return None


def insert_knowledge_object(knowledge_obj: KnowledgeObject):
    """Insert a knowledge object into the knowledge_objects collection."""
    try:
        result = knowledge_objects_collection.update_one(
            {"document_id": knowledge_obj.document_id},
            {"$set": knowledge_obj.model_dump(by_alias=True, exclude_none=True)},
            upsert=True
        )
        print(f"✅ Upserted knowledge object for document: {knowledge_obj.document_id}")
        return result
    except Exception as e:
        print(f"❌ Knowledge object upsert failed: {e}")
        return None


def insert_chunk(chunk: Chunk):
    """Insert a chunk into the chunks collection."""
    try:
        chunk_data = chunk.model_dump(by_alias=True, exclude_none=True)
        
        # Debug logging
        import logging
        logging.info(f"Inserting chunk with {len(chunk.embeddings)} embeddings")
        if chunk.embeddings:
            logging.info(f"First embedding vector length: {len(chunk.embeddings[0].vector) if chunk.embeddings[0].vector else 0}")
        
        result = chunks_collection.insert_one(chunk_data)
        print(f"✅ Inserted chunk: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Chunk insert failed: {e}")
        import logging
        logging.error(f"Chunk insert failed: {e}")
        logging.error(f"Chunk data: {chunk.model_dump(by_alias=True, exclude_none=True)}")
        return None


def get_or_create_embedding_config(model_name: str, embedding_size: int, distance_metric: str = "cosine"):
    """Get or create an embedding configuration."""
    config = embedding_configs_collection.find_one({
        "model_name": model_name,
        "embedding_size": embedding_size,
        "is_active": True
    })
    
    if config:
        return str(config["_id"])
    
    # Create new config
    new_config = EmbeddingConfig(
        model_name=model_name,
        embedding_size=embedding_size,
        distance_metric=distance_metric
    )
    
    try:
        result = embedding_configs_collection.insert_one(new_config.model_dump(by_alias=True, exclude_none=True))
        print(f"✅ Created new embedding config: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Embedding config creation failed: {e}")
        return None


def upsert_vector_document(doc: VectorDocument):
    """Upsert a VectorDocument into MongoDB Atlas (legacy function)."""
    try:
        result = collection.update_one(
            {"_id": doc.id},
            {"$set": doc.model_dump(by_alias=True)},
            upsert=True
        )
        print(f"✅ Upserted: {doc.id}")
        return result
    except Exception as e:
        print(f"❌ Upsert failed for {doc.id}: {e}")
        return None
    