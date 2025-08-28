#!/usr/bin/env python3
"""
Visual code flow analysis showing exactly how the search executes.
This traces through the actual function calls and data transformations.
"""

def trace_search_execution():
    """Trace the actual execution flow through the search pipeline code."""
    
    print("🔍 SEARCH EXECUTION TRACE")
    print("=" * 50)
    
    print("\n📞 LAMBDA HANDLER ENTRY POINT")
    print("-" * 35)
    print("Function: lambda_handler(event, context)")
    print("Code location: search_pipeline.py line ~320")
    print("Input processing:")
    print("  ┌─ Parse event body (JSON)")
    print("  ├─ Extract query_text")
    print("  ├─ Extract top_k (default: 3)")
    print("  ├─ Check USE_NEW_DATA_STRUCTURE env var")
    print("  └─ Route to appropriate search function")
    
    print("\n🆕 NEW STRUCTURE SEARCH FUNCTION")
    print("-" * 35)
    print("Function: mongodb_vector_search_new_structure()")
    print("Code location: search_pipeline.py line ~40")
    
    print("\nStep 1: Environment & Connection Setup")
    print("  ┌─ load_dotenv('../injestion/config/.env')")
    print("  ├─ MONGO_URI = os.getenv('MONGO_URI').strip('\"')")
    print("  ├─ DB_NAME = os.getenv('MONGO_DB_NAME', 'rag_with_lambda')")
    print("  ├─ mongo_client = MongoClient(MONGO_URI)")
    print("  ├─ db = mongo_client[DB_NAME]")
    print("  ├─ chunks_collection = db['chunks']")
    print("  ├─ knowledge_objects_collection = db['knowledge_objects']")
    print("  └─ modules_collection = db['modules']")
    
    print("\nStep 2: Data Validation")
    print("  ┌─ chunk_count = chunks_collection.count_documents({})")
    print("  ├─ if chunk_count == 0:")
    print("  │   └─ return mongodb_vector_search(query_text, top_k)  # Fallback")
    print("  └─ logging.info(f'Found {chunk_count} documents')")
    
    print("\nStep 3: Query Embedding Generation")
    print("  ┌─ query_vector = get_openai_embedding(query_text)")
    print("  │   ├─ Truncate to 8000 tokens if needed")
    print("  │   ├─ client.embeddings.create(model='text-embedding-3-small')")
    print("  │   └─ Return 1536-dimensional vector")
    print("  └─ logging.info(f'Generated {len(query_vector)} dimensions')")
    
    print("\nStep 4: Sample Data Inspection")
    print("  ┌─ sample_chunk = chunks_collection.find_one({})")
    print("  ├─ embedding = sample_chunk.get('embedding', [])")
    print("  └─ logging.info(f'Sample embedding length: {len(embedding)}')")
    
    print("\n🔧 AGGREGATION PIPELINE CONSTRUCTION")
    print("-" * 40)
    
    pipeline_code = '''
pipeline = [
    {
        "$vectorSearch": {
            "queryVector": query_vector,     # 1536-dim array
            "path": "embedding",             # Direct field path
            "numCandidates": 100,
            "index": "vector_index",
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
            "from": "knowledge_objects",
            "localField": "document_object_id",
            "foreignField": "module_id",
            "as": "knowledge"
        }
    },
    {
        "$lookup": {
            "from": "modules",
            "localField": "document_object_id",
            "foreignField": "_id",
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
]'''
    
    print("Pipeline construction (search_pipeline.py line ~70-120):")
    print(pipeline_code)
    
    print("\n⚡ PIPELINE EXECUTION")
    print("-" * 25)
    print("Execution:")
    print("  ┌─ try:")
    print("  │   ├─ results = list(chunks_collection.aggregate(pipeline))")
    print("  │   ├─ logging.info(f'Vector search returned {len(results)} results')")
    print("  │   └─ for result in results: log score")
    print("  └─ except Exception as e:")
    print("      ├─ logging.error(f'Vector search failed: {e}')")
    print("      ├─ Fall back to text search:")
    print("      └─ chunks_collection.find({'chunk_text': {'$regex': query}})")
    
    print("\n📊 RESULT PROCESSING")
    print("-" * 25)
    print("Function: Result formatting loop (line ~180-220)")
    
    processing_code = '''
docs = []
for doc in results:
    module_info = doc.get("module", [{}])[0] if doc.get("module") else {}
    knowledge_info = doc.get("knowledge", [{}])[0] if doc.get("knowledge") else {}
    metadata = knowledge_info.get("metadata", {}) if knowledge_info else {}
    
    docs.append({
        "_id": str(doc.get("_id", "")),
        "chunk_text": doc.get("chunk_text", ""),
        "chunk_id": doc.get("chunk_id", 0),
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
    })'''
    
    print("Processing code:")
    print(processing_code)
    
    print("\n🤖 LLM CONTEXT PREPARATION")
    print("-" * 30)
    print("Function: Context building (line ~240-260)")
    
    context_code = '''
if docs:
    context = "\\n\\n".join([
        f"Document: {doc['filename']}\\n"
        f"Summary: {doc['summary']}\\n"
        f"Content: {doc['chunk_text'][:300]}..." 
        for doc in docs[:3]  # Use top 3 results
    ])
    
    prompt = f"""You are an expert assistant. Use the following context to answer the user's question.

Context:
{context}

Question: {query_text}

Answer in detail based on the provided context:"""'''
    
    print("Context preparation:")
    print(context_code)
    
    print("\n🎯 AZURE OPENAI COMPLETION")
    print("-" * 30)
    print("Function: LLM answer generation (line ~270-285)")
    
    completion_code = '''
try:
    answer = client.chat.completions.create(
        model=deployment,                    # GPT model
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,                     # Focused answers
        max_tokens=512,                      # Response limit
        timeout=30                           # API timeout
    ).choices[0].message.content.strip()
except Exception as e:
    logging.error(f"OpenAI completion error: {e}")
    answer = "Error generating answer from LLM."'''
    
    print("Completion code:")
    print(completion_code)
    
    print("\n📤 FINAL RESPONSE")
    print("-" * 20)
    print("Function: Response formatting (line ~290-300)")
    
    response_code = '''
return {
    "answer": answer,                        # LLM-generated response
    "results": docs,                         # Processed search results
    "count": len(docs),                      # Number of results
    "search_method": "new_structure"         # Method identifier
}'''
    
    print("Response structure:")
    print(response_code)
    
    print("\n🔄 DATA FLOW SUMMARY")
    print("-" * 25)
    
    flow_steps = [
        "1. User Query → Lambda Handler",
        "2. Query Text → Embedding Vector (1536-dim)",
        "3. Vector → MongoDB Atlas Search",
        "4. Search Results → Aggregation Pipeline", 
        "5. Pipeline → Enriched Results (with joins)",
        "6. Raw Results → Formatted Objects",
        "7. Top Results → LLM Context",
        "8. Context + Query → GPT Answer",
        "9. Answer + Results → JSON Response"
    ]
    
    for step in flow_steps:
        print(f"   {step}")
    
    print("\n🏗️ KEY ARCHITECTURAL DECISIONS")
    print("-" * 35)
    
    decisions = [
        "✅ Direct embedding storage (not nested)",
        "✅ MongoDB aggregation for joins",
        "✅ ObjectId conversion for relationships",
        "✅ Fallback error handling",
        "✅ Separate collections for normalization",
        "✅ Vector index on 'embedding' field",
        "✅ Connection reuse and pooling",
        "✅ Timeout handling for external APIs"
    ]
    
    for decision in decisions:
        print(f"   {decision}")
    
    print("\n" + "=" * 50)
    print("🎉 SEARCH EXECUTION TRACE COMPLETE!")
    
    print("\nCritical Code Paths:")
    print("• Vector search: chunks_collection.aggregate(pipeline)")
    print("• Embedding: client.embeddings.create()")
    print("• Completion: client.chat.completions.create()")
    print("• Joins: MongoDB $lookup operations")
    print("• Error handling: try/except with fallbacks")

if __name__ == "__main__":
    trace_search_execution()
