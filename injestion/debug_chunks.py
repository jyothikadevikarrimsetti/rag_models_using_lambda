"""
Debug utility to inspect the chunks collection structure.
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

# Load environment variables
load_dotenv("config/.env")

def inspect_chunks_collection():
    """Inspect the structure of documents in the chunks collection."""
    
    mongo_client = MongoClient("mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
    db = mongo_client["rag_db"]
    chunks_collection = db["chunks"]
    
    # Get total count
    total_chunks = chunks_collection.count_documents({})
    print(f"📊 Total chunks in collection: {total_chunks}")
    
    if total_chunks == 0:
        print("❌ No chunks found in collection!")
        return
    
    # Get a sample chunk to inspect structure
    sample_chunk = chunks_collection.find_one({})
    
    if sample_chunk:
        print("\n📋 Sample chunk structure:")
        print("=" * 50)
        
        # Pretty print the structure
        def print_structure(obj, indent=0):
            for key, value in obj.items():
                if key == "_id":
                    print("  " * indent + f"{key}: {str(value)}")
                elif key == "embeddings" and isinstance(value, list):
                    print("  " * indent + f"{key}: [")
                    if value:
                        for i, embedding in enumerate(value):
                            print("  " * (indent + 1) + f"[{i}]: {{")
                            for k, v in embedding.items():
                                if k == "vector":
                                    if isinstance(v, list):
                                        print("  " * (indent + 2) + f"{k}: [array of {len(v)} numbers]")
                                    else:
                                        print("  " * (indent + 2) + f"{k}: {type(v)} {v}")
                                else:
                                    print("  " * (indent + 2) + f"{k}: {v}")
                            print("  " * (indent + 1) + "}")
                    print("  " * indent + "]")
                elif isinstance(value, str) and len(value) > 100:
                    print("  " * indent + f"{key}: '{value[:100]}...' (truncated)")
                else:
                    print("  " * indent + f"{key}: {value}")
        
        print_structure(sample_chunk)
    
    # Check if embeddings exist and their structure
    chunks_with_embeddings = chunks_collection.count_documents({"embeddings": {"$exists": True, "$ne": []}})
    print(f"\n📊 Chunks with embeddings: {chunks_with_embeddings}/{total_chunks}")
    
    if chunks_with_embeddings > 0:
        # Check embedding vector lengths
        pipeline = [
            {"$match": {"embeddings": {"$exists": True, "$ne": []}}},
            {"$project": {
                "embedding_count": {"$size": "$embeddings"},
                "first_embedding_vector_length": {"$size": {"$arrayElemAt": ["$embeddings.vector", 0]}}
            }},
            {"$limit": 5}
        ]
        
        print("\n📏 Embedding vector information:")
        for doc in chunks_collection.aggregate(pipeline):
            print(f"  - Chunk {doc['_id']}: {doc['embedding_count']} embeddings, vector length: {doc.get('first_embedding_vector_length', 'N/A')}")


def check_vector_search_compatibility():
    """Check if the chunks collection is compatible with vector search."""
    
    mongo_client = MongoClient("mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
    db = mongo_client["rag_db"]
    chunks_collection = db["chunks"]
    
    print("\n🔍 Vector Search Compatibility Check:")
    print("=" * 50)
    
    # Check for required fields
    sample = chunks_collection.find_one({"embeddings.vector": {"$exists": True}})
    
    if sample:
        print("✅ Found chunks with embeddings.vector field")
        
        # Check vector structure
        if sample.get("embeddings") and len(sample["embeddings"]) > 0:
            vector = sample["embeddings"][0].get("vector")
            if isinstance(vector, list) and len(vector) > 0:
                print(f"✅ Vector is a list with {len(vector)} dimensions")
                print(f"✅ Sample vector values: {vector[:5]}... (showing first 5)")
            else:
                print(f"❌ Vector is not a proper list: {type(vector)}")
        else:
            print("❌ No embeddings found in sample")
    else:
        print("❌ No chunks found with embeddings.vector field")
    
    # Suggest vector search index configuration
    print(f"\n📝 Suggested Atlas Vector Search Index:")
    index_config = {
        "fields": [
            {
                "type": "vector",
                "path": "embeddings.vector",
                "numDimensions": 1536,
                "similarity": "cosine"
            }
        ]
    }
    print(json.dumps(index_config, indent=2))


if __name__ == "__main__":
    print("🔍 Chunks Collection Inspector")
    print("=" * 50)
    
    inspect_chunks_collection()
    check_vector_search_compatibility()
