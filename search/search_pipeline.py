
from dotenv import load_dotenv
import os
import time
import numpy as np
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
import logging
import concurrent.futures
import tiktoken
import json

import os

# Load environment variables
load_dotenv("../injestion/config/.env")
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Helper functions for embeddings and similarity
def get_openai_embedding(text, timeout=15):
    """Get embeddings using Azure OpenAI's text-embedding model with context window truncation and timeout."""
    # Truncate text to fit within model context window (e.g., 8000 tokens for text-embedding-3-small)
    max_tokens = 8000
    encoding = tiktoken.encoding_for_model("text-embedding-3-small")
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        text = encoding.decode(tokens)
    def call():
        return client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        ).data[0].embedding
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(call)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logging.error(f"OpenAI embedding call timed out for text: {text[:50]}")
            raise TimeoutError("OpenAI embedding call timed out.")

def mongodb_vector_search_new_structure(query_text: str, top_k: int = 3) -> dict:
    """Search MongoDB Atlas using the new data structure with separate collections."""
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    import logging

    # Load environment variables - use correct database name
    load_dotenv("../injestion/config/.env")
    MONGO_URI = os.getenv("MONGO_URI").strip('"')
    DB_NAME = os.getenv("MONGO_DB_NAME", "rag_with_lambda")
    
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    chunks_collection = db["chunks"]

    logging.info(f"Searching in database: {DB_NAME}")

    # Check if chunks collection has any data
    chunk_count = chunks_collection.count_documents({})
    logging.info(f"Found {chunk_count} documents in chunks collection")
    
    if chunk_count == 0:
        logging.warning("No chunks found in collection, falling back to legacy search")
        return mongodb_vector_search(query_text, top_k)

    query_vector = get_openai_embedding(query_text)
    logging.info(f"Generated query embedding with {len(query_vector)} dimensions")
    
    # Check collection structure
    sample_chunk = chunks_collection.find_one({})
    if sample_chunk:
        logging.info(f"Sample chunk structure verified")
        embeddings = sample_chunk.get('embeddings', [])
        if embeddings and len(embeddings) > 0:
            vector_length = len(embeddings[0].get('vector', []))
            logging.info(f"Sample embedding vector length: {vector_length}")
    
    # Search in chunks collection using vector search with ObjectId conversion
    pipeline = [
        {
            "$vectorSearch": {
                "queryVector": query_vector,
                "path": "embeddings.vector",
                "numCandidates": 100,
                "index": "vector_index",  # Fixed index name
                "limit": top_k
            }
        },
        {
            "$addFields": {
                "document_object_id": {"$toObjectId": "$document_id"}
            }
        },
        {
            "$lookup": {
                "from": "documents",
                "localField": "document_object_id",
                "foreignField": "_id",
                "as": "document"
            }
        },
        {
            "$lookup": {
                "from": "knowledge_objects",
                "localField": "document_object_id", 
                "foreignField": "document_id",
                "as": "knowledge"
            }
        },
        {
            "$project": {
                "_id": 1,
                "chunk_text": 1,
                "chunk_index": 1,
                "start_pos": 1,
                "end_pos": 1,
                "document.filename": 1,
                "document.filepath": 1,
                "knowledge.summary": 1,
                "knowledge.keywords": 1,
                "knowledge.topic": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    try:
        results = list(chunks_collection.aggregate(pipeline))
        logging.info(f"Vector search returned {len(results)} results")
        
        for i, result in enumerate(results):
            score = result.get('score', 0)
            logging.info(f"Result {i+1}: score={score:.4f}")
            
    except Exception as e:
        logging.error(f"Vector search failed: {e}")
        
        # Fallback: simple text search if vector search fails
        logging.info("Falling back to text search")
        text_results = chunks_collection.find({
            "chunk_text": {"$regex": query_text, "$options": "i"}
        }).limit(top_k)
        
        results = []
        for chunk in text_results:
            # Get document info - convert string ID to ObjectId
            from bson import ObjectId
            try:
                document_oid = ObjectId(chunk["document_id"])
                document = db["documents"].find_one({"_id": document_oid})
                knowledge = db["knowledge_objects"].find_one({"document_id": document_oid})
            except:
                document = None
                knowledge = None
            
            results.append({
                "_id": chunk["_id"],
                "chunk_text": chunk["chunk_text"],
                "chunk_index": chunk["chunk_index"],
                "document": [document] if document else [],
                "knowledge": [knowledge] if knowledge else [],
                "score": 0.5  # Default score for text search
            })
    
    docs = []
    
    for doc in results:
        document_info = doc.get("document", [{}])[0] if doc.get("document") else {}
        knowledge_info = doc.get("knowledge", [{}])[0] if doc.get("knowledge") else {}
        
        docs.append({
            "_id": str(doc.get("_id", "")),
            "chunk_text": doc.get("chunk_text", ""),
            "chunk_index": doc.get("chunk_index", 0),
            "filename": document_info.get("filename", "Unknown"),
            "filepath": document_info.get("filepath", ""),
            "summary": knowledge_info.get("summary", ""),
            "keywords": knowledge_info.get("keywords", []),
            "topic": knowledge_info.get("topic", ""),
            "score": doc.get("score", 0)
        })

    # Prepare context for LLM answer
    if docs:
        context = "\n\n".join([
            f"Document: {doc['filename']}\n"
            f"Summary: {doc['summary']}\n"
            f"Content: {doc['chunk_text'][:300]}..." 
            for doc in docs[:3]  # Use top 3 results
        ])
        
        prompt = f"""You are an expert assistant. Use the following context to answer the user's question.

Context:
{context}

Question: {query_text}

Answer in detail based on the provided context:"""
        
        try:          
            answer = client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
                timeout=30
            ).choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"OpenAI completion error: {e}")
            answer = "Error generating answer from LLM."
    else:
        answer = "No relevant documents found for your query."
    
    return {
        "answer": answer,
        "results": docs,
        "count": len(docs),
        "search_method": "new_structure"
    }


def mongodb_vector_search(query_text: str, top_k: int = 3) -> dict:
    """Search MongoDB Atlas for top-k documents using vector similarity (legacy structure)."""
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    import logging

    # Load environment variables
    load_dotenv("../injestion/config/.env")
    MONGO_URI = os.getenv("MONGO_URI")
    mongo_client = MongoClient("mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
    db = mongo_client["rag_db"]
    collection = db["dmodel"]

    query_vector = get_openai_embedding(query_text)
    
    pipeline = [
        {
            "$vectorSearch": {
                "queryVector": query_vector,
                "path": "embedding",
                "numCandidates": 100,
                "index": "vector_index",  # Make sure this matches your Atlas Search index name
                "limit": top_k
            }
        }
    ]

    results = list(collection.aggregate(pipeline))
    docs = []
    for doc in results:
        docs.append({
            "_id": doc.get("_id", None),
            "href": doc.get("href", ""),
            "path": doc.get("path", ""),
            "title": doc.get("title",None),
            "summary": doc.get("summary", ""),
        })
        
    # Prepare context for LLM answer
    if docs:
        context = "\n\n".join([doc["summary"] for doc in docs[:min(3, len(docs))]])
        prompt = f"You are an expert assistant. Use the following context to answer the user's question.\n\nContext:\n{context}\n\nQuestion: {query_text}\n\nAnswer in detail:"
        try:          
            answer = client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=256,
                timeout=20
            ).choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"OpenAI completion error: {e}")
            answer = "LLM completion error."
    else:
        answer = "No relevant document found."
    return {
        "answer": answer,
        "results": docs,
        "count": len(docs),
        "search_method": "legacy_structure"
    }

# ...existing code...

def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    Expects event['query_text'] and optionally event['top_k'].
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    
    if 'body' in event and event['body']:
        body = json.loads(event['body'])
    else:
        body = event
    query_text = body.get('query_text')
    top_k = body.get('top_k', 3)
    use_new_structure = os.getenv("USE_NEW_DATA_STRUCTURE", "false").lower() == "true"

    
    logging.info(f"Query: {query_text}")
    logging.info(f"Top K: {top_k}")
    logging.info(f"Use new structure: {use_new_structure}")
    
    if not query_text:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'query_text' in event"})
        }
    try:
        if use_new_structure:
            logging.info("Using NEW structure for search")
            result = mongodb_vector_search_new_structure(query_text, top_k)
        else:
            logging.info("Using LEGACY structure for search")
            result = mongodb_vector_search(query_text, top_k)
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
    except Exception as e:
        logging.error(f"Error in lambda_handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }