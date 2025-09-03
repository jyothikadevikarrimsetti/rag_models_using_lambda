
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

# Initialize OpenAI client with error handling
try:
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION") or os.getenv("OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("OPENAI_ENDPOINT")
    )
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("OPENAI_DEPLOYMENT_NAME")
except Exception as e:
    print(f"Warning: Failed to initialize OpenAI client: {e}")
    client = None
    deployment = None

# Helper functions for embeddings and similarity
def get_openai_embedding(text, timeout=15):
    """Get embeddings using Azure OpenAI's text-embedding model with context window truncation and timeout."""
    if client is None:
        raise Exception("OpenAI client not initialized. Check your API credentials.")
    
    # Truncate text to fit within model context window (e.g., 8000 tokens for text-embedding-3-small)
    max_tokens = 8000
    try:
        encoding = tiktoken.get_encoding("cl100k_base")  # Use explicit encoding for text-embedding-3-small
    except Exception:
        # Fallback to a simple character-based truncation if tiktoken fails
        if len(text) > max_tokens * 4:  # Rough approximation: 4 chars per token
            text = text[:max_tokens * 4]
    else:
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

def mongodb_vector_search_new_structure(query_text: str, top_k: int = 3, chat_history: Optional[List[Dict]] = None) -> dict:
    """Search MongoDB Atlas using the new data structure with separate collections."""
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    import logging

    # Check if OpenAI client is initialized
    if client is None:
        return {
            "answer": "OpenAI client not initialized. Please check your API credentials.",
            "results": [],
            "count": 0,
            "search_method": "new_structure"
        }

    # Load environment variables - use correct database name
    load_dotenv("../injestion/config/.env")
    MONGO_URI = "mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
    DB_NAME = os.getenv("MONGO_DB_NAME", "rag_with_lambda")
    
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    chunks_collection = db["chunks"]
    knowledge_objects_collection = db["knowledge_objects"]
    modules_collection = db["modules"]

    logging.info(f"Searching in database: {DB_NAME}")

    # Check if chunks collection has any data
    chunk_count = chunks_collection.count_documents({})
    logging.info(f"Found {chunk_count} documents in chunks collection")
    
    if chunk_count == 0:
        logging.warning("No chunks found in collection, falling back to legacy search")
        return mongodb_vector_search(query_text, top_k)

    query_vector = get_openai_embedding(query_text)
    logging.info(f"Generated query embedding with {len(query_vector)} dimensions")
    
    # Check collection structure - new schema uses direct embedding in chunks
    sample_chunk = chunks_collection.find_one({})
    if sample_chunk:
        logging.info(f"Sample chunk structure verified")
        embedding = sample_chunk.get('embedding', [])
        if embedding and len(embedding) > 0:
            vector_length = len(embedding)
            logging.info(f"Sample embedding vector length: {vector_length}")
    
    # Search in chunks collection using vector search - updated for new schema
    pipeline = [
        {
            "$vectorSearch": {
                "queryVector": query_vector,
                "path": "embedding",  # Direct embedding path in new schema
                "numCandidates": 100,
                "index": "vector_index",
                "limit": top_k
            }
        },
        {
            "$lookup": {
                "from": "knowledge_objects",
                "localField": "document_id",
                "foreignField": "module_id",  # Both are strings
                "as": "knowledge"
            }
        },
        {
            "$addFields": {
                "document_object_id": {"$toObjectId": "$document_id"}
            }
        },
        {
            "$lookup": {
                "from": "modules",
                "localField": "document_object_id", 
                "foreignField": "_id",  # modules._id is ObjectId
                "as": "module"
            }
        },
        {
            "$project": {
                "_id": 1,
                "chunk_text": 1,
                "chunk_id": 1,
                "chunk_start": 1,
                "chunk_end": 1,
                "document_id": 1,
                "module.module_id": 1,
                "module.module_tag": 1,
                "knowledge.title": 1,
                "knowledge.summary": 1,
                "knowledge.keywords": 1,
                "knowledge.content": 1,
                "knowledge.metadata.path": 1,
                "knowledge.metadata.intent_category": 1,
                "knowledge.is_terraform": 1,
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
            # Get knowledge object info - convert string ID to ObjectId
            from bson import ObjectId
            try:
                document_oid = ObjectId(chunk["document_id"])
                knowledge = knowledge_objects_collection.find_one({"module_id": str(document_oid)})
                module = modules_collection.find_one({"_id": document_oid})
            except:
                knowledge = None
                module = None
            
            results.append({
                "_id": chunk["_id"],
                "chunk_text": chunk["chunk_text"],
                "chunk_id": chunk.get("chunk_id", 0),
                "chunk_start": chunk.get("chunk_start", 0),
                "chunk_end": chunk.get("chunk_end", 0),
                "document_id": chunk["document_id"],
                "module": [module] if module else [],
                "knowledge": [knowledge] if knowledge else [],
                "score": 0.5  # Default score for text search
            })
    
    docs = []
    
    for doc in results:
        module_info = doc.get("module", [{}])[0] if doc.get("module") else {}
        knowledge_info = doc.get("knowledge", [{}])[0] if doc.get("knowledge") else {}
        metadata = knowledge_info.get("metadata", {}) if knowledge_info else {}
        
        docs.append({
            "_id": str(doc.get("_id", "")),
            "chunk_text": doc.get("chunk_text", ""),
            "chunk_id": doc.get("chunk_id", 0),  # Fixed: use chunk_id from data model
            "chunk_start": doc.get("chunk_start", 0),
            "chunk_end": doc.get("chunk_end", 0),
            "filename": knowledge_info.get("title", "Unknown"),
            "filepath": metadata.get("path", ""),
            "summary": knowledge_info.get("summary", ""),
            "keywords": knowledge_info.get("keywords", ""),
            "content": knowledge_info.get("content", ""),
            "intent_category": metadata.get("intent_category", ""),
            "is_terraform": knowledge_info.get("is_terraform", False),
            "module_id": module_info.get("module_id", ""),
            "module_tags": module_info.get("module_tag", []),
            "score": doc.get("score", 0)
        })

    # Prepare context for LLM answer
    if docs:
        # Build document context
        document_context = "\n\n".join([
            f"Document: {doc['filename']}\n"
            f"Summary: {doc['summary']}\n"
            f"Content: {doc['chunk_text'][:300]}..." 
            for doc in docs[:3]  # Use top 3 results
        ])
        
        # Build chat history context if available
        chat_context = ""
        if chat_history and len(chat_history) > 0:
            # Get recent conversation context (last 5 exchanges)
            recent_messages = chat_history[-10:]  # Last 5 user-assistant pairs
            chat_exchanges = []
            
            for i in range(0, len(recent_messages), 2):
                if i + 1 < len(recent_messages):
                    user_msg = recent_messages[i]
                    assistant_msg = recent_messages[i + 1]
                    
                    if user_msg.get('role') == 'user' and assistant_msg.get('role') == 'assistant':
                        chat_exchanges.append(
                            f"Previous Q: {user_msg.get('content', '')}\n"
                            f"Previous A: {assistant_msg.get('content', '')[:150]}..."
                        )
            
            if chat_exchanges:
                chat_context = f"\n\nConversation History:\n" + "\n\n".join(chat_exchanges)  # Show all available exchanges
        
        # Combine contexts
        full_context = f"Relevant Documents:\n{document_context}"
        if chat_context:
            full_context += chat_context
        
        prompt = f"""You are an expert assistant. Use the following context to answer the user's question. 
Consider both the relevant documents and the conversation history to provide a comprehensive answer.

{full_context}

Current Question: {query_text}

Answer in detail based on the provided context. If this question relates to previous conversation, reference that context appropriately:"""
        
        # Check if OpenAI client is initialized
        if client is None:
            answer = "OpenAI client not initialized. Please check your API credentials."
        else:
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


def mongodb_vector_search(query_text: str, top_k: int = 3, chat_history: Optional[List[Dict]] = None) -> dict:
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
        # Build document context
        document_context = "\n\n".join([doc["summary"] for doc in docs[:min(3, len(docs))]])
        
        # Build chat history context if available
        chat_context = ""
        if chat_history and len(chat_history) > 0:
            recent_messages = chat_history[-10:]  # Last 5 user-assistant pairs
            chat_exchanges = []
            
            for i in range(0, len(recent_messages), 2):
                if i + 1 < len(recent_messages):
                    user_msg = recent_messages[i]
                    assistant_msg = recent_messages[i + 1]
                    
                    if user_msg.get('role') == 'user' and assistant_msg.get('role') == 'assistant':
                        chat_exchanges.append(
                            f"Previous Q: {user_msg.get('content', '')}\n"
                            f"Previous A: {assistant_msg.get('content', '')[:150]}..."
                        )
            
            if chat_exchanges:
                chat_context = f"\n\nConversation History:\n" + "\n\n".join(chat_exchanges)  # Show all available exchanges
        
        # Combine contexts
        full_context = f"Relevant Documents:\n{document_context}"
        if chat_context:
            full_context += chat_context
            
        prompt = f"You are an expert assistant. Use the following context to answer the user's question. Consider both the relevant documents and the conversation history.\n\n{full_context}\n\nCurrent Question: {query_text}\n\nAnswer in detail:"
        
        # Check if OpenAI client is initialized
        if client is None:
            answer = "OpenAI client not initialized. Please check your API credentials."
        else:
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
    chat_history = body.get('chat_history', None)  # Optional chat history
    use_new_structure = os.getenv("USE_NEW_DATA_STRUCTURE", "false").lower() == "true"

    
    logging.info(f"Query: {query_text}")
    logging.info(f"Top K: {top_k}")
    logging.info(f"Chat history messages: {len(chat_history) if chat_history else 0}")
    logging.info(f"Use new structure: {use_new_structure}")
    
    if not query_text:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'query_text' in event"})
        }
    try:
        if use_new_structure:
            logging.info("Using NEW structure for search")
            result = mongodb_vector_search_new_structure(query_text, top_k, chat_history)
        else:
            logging.info("Using LEGACY structure for search")
            result = mongodb_vector_search(query_text, top_k, chat_history)
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