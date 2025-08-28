import os
import json
from typing import List
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from models.datamodel_pdantic import VectorDocument, KnowledgeObject, Chunk, Module, Metadata, EmbeddingMeta

# -------------------------------
# MongoDB Setup
# -------------------------------
load_dotenv("config/.env")
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient("mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
db = client[os.getenv("MONGO_DB_NAME", "rag_with_lambda")]

# Collections based on new schema
modules_collection = db["modules"]
knowledge_objects_collection = db["knowledge_objects"]
chunks_collection = db["chunks"]
collection = db[os.getenv("MONGO_COLLECTION_NAME", "dmodel")]  # Legacy collection


def insert_module(module: Module):
    """Insert a new module into the modules collection."""
    try:
        result = modules_collection.insert_one(module.model_dump(by_alias=True, exclude_none=True))
        print(f"✅ Inserted module: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Module insert failed: {e}")
        return None


def insert_knowledge_object(knowledge_obj: KnowledgeObject):
    """Insert a knowledge object into the knowledge_objects collection."""
    try:
        result = knowledge_objects_collection.update_one(
            {"module_id": knowledge_obj.module_id, "title": knowledge_obj.title},
            {"$set": knowledge_obj.model_dump(by_alias=True, exclude_none=True)},
            upsert=True
        )
        print(f"✅ Upserted knowledge object for module: {knowledge_obj.module_id}")
        return result
    except Exception as e:
        print(f"❌ Knowledge object upsert failed: {e}")
        return None


def insert_chunk(chunk: Chunk):
    """Insert a chunk into the chunks collection."""
    try:
        # Convert to dict with proper serialization
        chunk_data = chunk.model_dump(by_alias=True, exclude_none=True)
        
        # Debug logging
        import logging
        logging.info(f"Inserting chunk with embedding length: {len(chunk.embedding)}")
        if chunk.embedding:
            logging.info(f"Embedding vector length: {len(chunk.embedding)}")
            
            # Ensure vector is a list of floats
            if not isinstance(chunk.embedding, list):
                logging.error(f"Embedding is not a list: {type(chunk.embedding)}")
            elif not all(isinstance(x, (int, float)) for x in chunk.embedding):
                logging.error("Embedding contains non-numeric values")
            else:
                logging.info(f"Embedding is valid list with {len(chunk.embedding)} floats")
        
        result = chunks_collection.insert_one(chunk_data)
        print(f"✅ Inserted chunk: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Chunk insert failed: {e}")
        import logging
        logging.error(f"Chunk insert failed: {e}")
        logging.error(f"Chunk data keys: {chunk_data.keys() if 'chunk_data' in locals() else 'chunk_data not created'}")
        return None


def create_embedding_meta(model_name: str, dimensionality: int, embedding_method: str = "azure_openai"):
    """Create embedding metadata for a chunk."""
    from datetime import datetime
    return EmbeddingMeta(
        model_name=model_name,
        model_version="1.0",
        dimensionality=dimensionality,
        embedding_method=embedding_method,
        tokenizer="cl100k_base",
        embedding_date=datetime.utcnow(),
        source_field="chunk_text",
        embedding_quality_score=1.0,
        reembedding_required=False
    )


def update_knowledge_object_chunk_ids(module_id: str, title: str, chunk_ids: list):
    """Update a knowledge object with chunk IDs."""
    try:
        result = knowledge_objects_collection.update_one(
            {"module_id": module_id, "title": title},
            {"$set": {"chunk_ids": chunk_ids}}
        )
        if result.modified_count > 0:
            print(f"✅ Updated knowledge object with {len(chunk_ids)} chunk IDs")
            return True
        else:
            print(f"⚠️ No knowledge object found to update for module_id: {module_id}")
            return False
    except Exception as e:
        print(f"❌ Failed to update knowledge object chunk IDs: {e}")
        return False


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
    