# Data Model Migration

This update introduces a new, normalized data structure for better organization and scalability.

## New Collections Structure

### 1. `documents`
- Stores basic document metadata
- Fields: `_id`, `filename`, `filepath`, `created_date`, `modified_date`

### 2. `knowledge_objects`
- Stores extracted metadata for each document (1:1 relationship)
- Fields: `_id`, `document_id`, `summary`, `keywords`, `intent`, `entities`, `language`, `topic`, `model_name`, `created_date`, `modified_date`

### 3. `chunks`
- Stores text chunks with embeddings (1:N relationship)
- Fields: `_id`, `document_id`, `chunk_text`, `chunk_index`, `start_pos`, `end_pos`, `embeddings[]`

### 4. `embedding_configs`
- Stores embedding model configurations
- Fields: `_id`, `model_name`, `embedding_size`, `distance_metric`, `is_active`, etc.

### 5. `modules`
- Registry of processing modules
- Fields: `_id`, `module_name`, `module_type`, `created_date`, `modified_date`

## Migration Instructions

### 1. Initialize New Collections
Run the initialization script to set up default configurations:
```bash
python scripts/init_db_collections.py
```

### 2. Configure Environment
Set `USE_NEW_DATA_STRUCTURE=true` in your `.env` file to enable the new structure.

### 3. Create Vector Search Indexes
In MongoDB Atlas, create a new vector search index on the `chunks` collection:
- Collection: `chunks`
- Field: `embeddings.vector`
- Index name: `chunks_vector_index`
- Dimensions: 1536 (for text-embedding-3-small)
- Similarity: cosine

### 4. Update Search Queries
When calling the search API, add `"use_new_structure": true` to use the new data structure:
```json
{
    "query_text": "your search query",
    "top_k": 3,
    "use_new_structure": true
}
```

## Benefits of New Structure

1. **Better Organization**: Separate collections for different data types
2. **Improved Queries**: More efficient lookups with proper indexing
3. **Scalability**: Better support for multiple embedding models
4. **Metadata Rich**: Enhanced document-level and chunk-level metadata
5. **Flexibility**: Support for multiple processing modules

## Backward Compatibility

The legacy structure (`dmodel` collection) is still supported. The system automatically chooses between old and new structures based on configuration.

## Required Atlas Indexes

```javascript
// knowledge_objects collection
db.knowledge_objects.createIndex({"document_id": 1}, {unique: true})

// chunks collection
db.chunks.createIndex({"document_id": 1, "chunk_index": 1})

// Vector Search Index (via Atlas UI)
// Collection: chunks
// Field: embeddings.vector
// Dimensions: 1536
// Similarity: cosine
```
