"""
Script to initialize database collections with default configurations.
Run this once to set up embedding configs and modules.
"""

from scripts.mongo_utils import embedding_configs_collection, modules_collection
from models.datamodel_pdantic import EmbeddingConfig, Module


def initialize_embedding_configs():
    """Initialize default embedding configurations."""
    configs = [
        EmbeddingConfig(
            model_name="text-embedding-3-small",
            embedding_size=1536,
            distance_metric="cosine",
            is_active=True
        ),
        EmbeddingConfig(
            model_name="text-embedding-ada-002",
            embedding_size=1536,
            distance_metric="cosine",
            is_active=False
        )
    ]
    
    for config in configs:
        existing = embedding_configs_collection.find_one({
            "model_name": config.model_name,
            "embedding_size": config.embedding_size
        })
        
        if not existing:
            result = embedding_configs_collection.insert_one(
                config.model_dump(by_alias=True, exclude_none=True)
            )
            print(f"✅ Created embedding config: {config.model_name} ({result.inserted_id})")
        else:
            print(f"⚠️ Embedding config already exists: {config.model_name}")


def initialize_modules():
    """Initialize default processing modules."""
    modules = [
        Module(module_name="summarizer", module_type="nlp_processor"),
        Module(module_name="text_embedder", module_type="embedding_processor"),
        Module(module_name="pdf_text_extractor", module_type="document_processor"),
        Module(module_name="text_chunker", module_type="document_processor")
    ]
    
    for module in modules:
        existing = modules_collection.find_one({
            "module_name": module.module_name,
            "module_type": module.module_type
        })
        
        if not existing:
            result = modules_collection.insert_one(
                module.model_dump(by_alias=True, exclude_none=True)
            )
            print(f"✅ Created module: {module.module_name} ({result.inserted_id})")
        else:
            print(f"⚠️ Module already exists: {module.module_name}")


def create_indexes():
    """Create necessary indexes for the collections."""
    try:
        # Create unique index on knowledge_objects.document_id
        from scripts.mongo_utils import knowledge_objects_collection, chunks_collection
        
        knowledge_objects_collection.create_index("document_id", unique=True)
        print("✅ Created unique index on knowledge_objects.document_id")
        
        # Create compound index on chunks for efficient retrieval
        chunks_collection.create_index([("document_id", 1), ("chunk_index", 1)])
        print("✅ Created compound index on chunks (document_id, chunk_index)")
        
    except Exception as e:
        print(f"❌ Index creation error: {e}")


if __name__ == "__main__":
    print("🚀 Initializing database collections...")
    
    print("\n📋 Setting up embedding configurations...")
    initialize_embedding_configs()
    
    print("\n🔧 Setting up processing modules...")
    initialize_modules()
    
    print("\n📚 Creating database indexes...")
    create_indexes()
    
    print("\n✅ Database initialization complete!")
