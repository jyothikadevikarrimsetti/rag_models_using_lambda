#!/usr/bin/env python3
"""
Fix MongoDB index for chunk_id field name change.
This script will:
1. Drop the old index on chunk_id_id
2. Create a new index on chunk_id
3. Clean up any documents with null chunk_id values
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_mongodb_index():
    """Fix the MongoDB index after field name change."""
    
    print("🔧 FIXING MONGODB INDEX FOR CHUNK_ID FIELD")
    print("=" * 50)
    
    # Get MongoDB connection

    
    try:
        client = MongoClient("mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
        db = client['rag_with_lambda']
        chunks_collection = db['chunks']
        
        print("\n📊 CURRENT INDEX STATUS")
        print("-" * 30)
        
        # List current indexes
        indexes = list(chunks_collection.list_indexes())
        print("Current indexes:")
        for idx in indexes:
            print(f"   • {idx['name']}: {idx.get('key', {})}")
        
        print("\n🗑️ DROPPING OLD INDEX")
        print("-" * 28)
        
        # Check if old index exists and drop it
        try:
            chunks_collection.drop_index("document_id_1_chunk_id_id_1")
            print("✅ Successfully dropped old index: document_id_1_chunk_id_id_1")
        except Exception as e:
            if "index not found" in str(e).lower():
                print("ℹ️ Old index already removed or doesn't exist")
            else:
                print(f"⚠️ Warning dropping old index: {e}")
        
        print("\n🏗️ CREATING NEW INDEX")
        print("-" * 27)
        
        # Create new compound index on document_id and chunk_id
        try:
            result = chunks_collection.create_index([
                ("document_id", 1),
                ("chunk_id", 1)
            ], unique=True, name="document_id_1_chunk_id_1")
            print(f"✅ Successfully created new index: {result}")
        except Exception as e:
            print(f"❌ Error creating new index: {e}")
            return False
        
        print("\n🧹 CLEANING UP NULL VALUES")
        print("-" * 32)
        
        # Find documents with null chunk_id
        null_chunks = list(chunks_collection.find({"chunk_id": None}))
        print(f"Found {len(null_chunks)} documents with null chunk_id")
        
        if null_chunks:
            print("Documents with null chunk_id:")
            for chunk in null_chunks:
                print(f"   • Document ID: {chunk.get('document_id')}, _id: {chunk.get('_id')}")
            
            # Option 1: Delete these documents (recommended for clean start)
            print("\n🗑️ Removing documents with null chunk_id...")
            delete_result = chunks_collection.delete_many({"chunk_id": None})
            print(f"✅ Deleted {delete_result.deleted_count} documents with null chunk_id")
        
        print("\n📋 UPDATED INDEX STATUS")
        print("-" * 29)
        
        # List indexes after changes
        indexes = list(chunks_collection.list_indexes())
        print("Updated indexes:")
        for idx in indexes:
            print(f"   • {idx['name']}: {idx.get('key', {})}")
        
        print("\n✅ INDEX FIX COMPLETE!")
        print("The chunks collection now has the correct index structure.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def verify_index_fix():
    """Verify the index fix by checking the current state."""
    
    print("\n🔍 VERIFICATION")
    print("-" * 18)
    
 
    
    try:
        client = MongoClient("mongodb+srv://jyothika:Jyothika%40123@cluster.ollkbh1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
        db = client['rag_with_lambda']
        chunks_collection = db['chunks']
        
        # Check document count
        total_chunks = chunks_collection.count_documents({})
        null_chunk_ids = chunks_collection.count_documents({"chunk_id": None})
        valid_chunk_ids = chunks_collection.count_documents({"chunk_id": {"$ne": None}})
        
        print(f"📊 Collection Statistics:")
        print(f"   • Total chunks: {total_chunks}")
        print(f"   • Valid chunk_id: {valid_chunk_ids}")
        print(f"   • Null chunk_id: {null_chunk_ids}")
        
        # Test inserting a sample document
        sample_doc = {
            "document_id": "test_doc_123",
            "chunk_id": 1,
            "chunk_start": 0,
            "chunk_end": 100,
            "chunk_text": "Test chunk text",
            "embedding": [0.1] * 1536,
            "embedding_meta": {
                "model_name": "test-model",
                "model_version": "1.0",
                "dimensionality": 1536,
                "embedding_method": "test",
                "tokenizer": "test",
                "embedding_date": "2025-08-27T00:00:00",
                "source_field": "chunk_text",
                "embedding_quality_score": 0.95,
                "reembedding_required": False
            }
        }
        
        try:
            test_result = chunks_collection.insert_one(sample_doc)
            print(f"✅ Test insert successful: {test_result.inserted_id}")
            
            # Clean up test document
            chunks_collection.delete_one({"_id": test_result.inserted_id})
            print("🧹 Test document cleaned up")
            
        except Exception as e:
            print(f"❌ Test insert failed: {e}")
            return False
        
        print("\n🎉 INDEX FIX VERIFIED!")
        print("The collection is ready for new chunk inserts.")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    print("Starting MongoDB index fix for chunk_id field...")
    
    if fix_mongodb_index():
        verify_index_fix()
        print("\n🚀 NEXT STEPS:")
        print("1. The index has been fixed")
        print("2. You can now re-run your ingestion pipeline")
        print("3. New chunks will use the correct 'chunk_id' field")
    else:
        print("\n❌ Index fix failed. Please check the error messages above.")
        sys.exit(1)
