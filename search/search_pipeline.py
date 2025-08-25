
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
load_dotenv("config/.env")
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

def mongodb_vector_search(query_text: str, top_k: int = 3) -> dict:
    """Search MongoDB Atlas for top-k documents using vector similarity."""
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    import logging

    # Load environment variables
    load_dotenv("config/.env")
    MONGO_URI = os.getenv("MONGO_URI")
    mongo_client = MongoClient(MONGO_URI)
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
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
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
    "count": len(docs)
}
    