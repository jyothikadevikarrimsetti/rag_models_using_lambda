"""
Debug utility to check the legacy dmodel collection.
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

# Load environment variables
load_dotenv("config/.env")

def inspect_legacy_collection():
    """Inspect the legacy dmodel collection."""
    
    mongo_client = MongoClient("mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
    db = mongo_client["rag_db"]
    
    # Check what collections exist
    collection_names = db.list_collection_names()
    print(f"📋 Available collections: {collection_names}")
    
    # Check the legacy collection
    legacy_collection = db["dmodel"]
    total_docs = legacy_collection.count_documents({})
    print(f"\n📊 Total documents in 'dmodel' collection: {total_docs}")
    
    if total_docs == 0:
        print("❌ No documents found in legacy collection either!")
        
        # Check lambda collection too
        lambda_collection = db["lambda"]
        lambda_docs = lambda_collection.count_documents({})
        print(f"📊 Total documents in 'lambda' collection: {lambda_docs}")
        
        if lambda_docs > 0:
            print("✅ Found documents in 'lambda' collection!")
            sample = lambda_collection.find_one({})
            if sample:
                print(f"📋 Sample document keys: {list(sample.keys())}")
                if 'embedding' in sample:
                    print(f"✅ Has embedding field with {len(sample['embedding'])} dimensions")
        return
    
    # Get a sample document
    sample_doc = legacy_collection.find_one({})
    
    if sample_doc:
        print("\n📋 Sample legacy document structure:")
        print("=" * 50)
        
        for key, value in sample_doc.items():
            if key == "embedding" and isinstance(value, list):
                print(f"{key}: [array of {len(value)} numbers]")
            elif isinstance(value, str) and len(value) > 100:
                print(f"{key}: '{value[:100]}...' (truncated)")
            else:
                print(f"{key}: {value}")
    
    # Check embedding structure
    docs_with_embeddings = legacy_collection.count_documents({"embedding": {"$exists": True, "$ne": []}})
    print(f"\n📊 Documents with embeddings: {docs_with_embeddings}/{total_docs}")
    
    if docs_with_embeddings > 0:
        # Check embedding dimensions
        sample_with_embedding = legacy_collection.find_one({"embedding": {"$exists": True, "$ne": []}})
        if sample_with_embedding and sample_with_embedding.get("embedding"):
            print(f"📏 Embedding dimensions: {len(sample_with_embedding['embedding'])}")
            print(f"📏 Sample embedding values: {sample_with_embedding['embedding'][:5]}...")


def check_environment_config():
    """Check current environment configuration."""
    print("\n🔧 Environment Configuration:")
    print("=" * 50)
    
    use_new = os.getenv("USE_NEW_DATA_STRUCTURE", "false")
    mongo_collection = os.getenv("MONGO_COLLECTION_NAME", "dmodel")
    mongo_db = os.getenv("MONGO_DB_NAME", "rag_db")
    
    print(f"USE_NEW_DATA_STRUCTURE: {use_new}")
    print(f"MONGO_DB_NAME: {mongo_db}")
    print(f"MONGO_COLLECTION_NAME: {mongo_collection}")
    
    if use_new.lower() == "true":
        print("⚠️ New structure is enabled but chunks collection is empty!")
        print("💡 Either:")
        print("   1. Set USE_NEW_DATA_STRUCTURE=false to use legacy data")
        print("   2. Re-process PDFs to populate the new structure")
    else:
        print("✅ Using legacy structure - this should work with existing data")


if __name__ == "__main__":
    print("🔍 Legacy Collection Inspector")
    print("=" * 50)
    
    inspect_legacy_collection()
    check_environment_config()
