#!/usr/bin/env python3
"""
Comprehensive explanation of how the search pipeline works with the new data model.
This script explains the search flow, data transformations, and result processing.
"""

def explain_search_pipeline():
    """Explain the complete search pipeline workflow."""
    
    print("🔍 HOW SEARCH WORKS IN THE NEW DATA MODEL")
    print("=" * 60)
    
    print("\n🎯 OVERVIEW")
    print("-" * 30)
    print("The search pipeline uses MongoDB Atlas Vector Search to find relevant")
    print("document chunks based on semantic similarity, then enriches results")
    print("with metadata from related collections.")
    
    print("\n📊 DATA MODEL STRUCTURE")
    print("-" * 30)
    print("Collections:")
    print("  📁 chunks          - Text chunks with embeddings")
    print("  📁 knowledge_objects - Document metadata & summaries")
    print("  📁 modules         - Module organization & tags")
    print("")
    print("Relationships:")
    print("  chunks.document_id → modules._id")
    print("  knowledge_objects.module_id → modules._id")
    
    print("\n🚀 SEARCH FLOW STEP-BY-STEP")
    print("-" * 40)
    
    print("\n1️⃣  QUERY PROCESSING")
    print("   Input: User query text (e.g., 'How to configure AWS VPC?')")
    print("   Process:")
    print("   ┌─ Truncate to 8000 tokens (text-embedding-3-small limit)")
    print("   ├─ Send to Azure OpenAI embedding API")
    print("   └─ Receive 1536-dimensional vector")
    print("   Output: [0.1, -0.3, 0.8, ..., 0.2] (1536 numbers)")
    
    print("\n2️⃣  VECTOR SEARCH")
    print("   Input: Query embedding vector")
    print("   Process:")
    print("   ┌─ MongoDB Atlas vector search on 'chunks' collection")
    print("   ├─ Index: 'vector_index' on field 'embedding'")
    print("   ├─ Similarity: Cosine similarity")
    print("   ├─ Candidates: 100 (for accuracy)")
    print("   └─ Limit: top_k results (default 3)")
    print("   Output: Ranked chunks with similarity scores")
    
    print("\n3️⃣  DATA ENRICHMENT")
    print("   Input: Chunk results with scores")
    print("   Process:")
    print("   ┌─ Convert chunk.document_id (string) → ObjectId")
    print("   ├─ JOIN knowledge_objects ON module_id")
    print("   ├─ JOIN modules ON _id")
    print("   └─ PROJECT relevant fields")
    print("   Output: Enriched results with metadata")
    
    print("\n4️⃣  RESULT FORMATTING")
    print("   Input: Raw MongoDB aggregation results")
    print("   Process:")
    print("   ┌─ Extract fields from nested objects")
    print("   ├─ Handle missing/optional fields")
    print("   ├─ Format for consistent structure")
    print("   └─ Include similarity scores")
    print("   Output: Standardized result objects")
    
    print("\n5️⃣  CONTEXT PREPARATION")
    print("   Input: Top 3 search results")
    print("   Process:")
    print("   ┌─ Extract key information per result:")
    print("   ├─   • Document title/filename")
    print("   ├─   • Summary")
    print("   ├─   • Chunk content (first 300 chars)")
    print("   └─ Combine into LLM context")
    print("   Output: Formatted context string")
    
    print("\n6️⃣  LLM ANSWER GENERATION")
    print("   Input: Context + user query")
    print("   Process:")
    print("   ┌─ Create prompt with context and question")
    print("   ├─ Send to Azure OpenAI (GPT model)")
    print("   ├─ Temperature: 0.2 (focused answers)")
    print("   └─ Max tokens: 512")
    print("   Output: Natural language answer")
    
    print("\n🔧 AGGREGATION PIPELINE DETAILS")
    print("-" * 40)
    
    pipeline_stages = [
        {
            "stage": "1. $vectorSearch",
            "purpose": "Find similar chunks",
            "details": [
                "• queryVector: User's embedded query",
                "• path: 'embedding' (direct field)",
                "• index: 'vector_index'",
                "• numCandidates: 100",
                "• limit: top_k"
            ]
        },
        {
            "stage": "2. $addFields",
            "purpose": "Convert IDs for joins",
            "details": [
                "• document_object_id = ObjectId(document_id)",
                "• Enables proper MongoDB joins"
            ]
        },
        {
            "stage": "3. $lookup (knowledge_objects)",
            "purpose": "Get document metadata",
            "details": [
                "• from: 'knowledge_objects'",
                "• localField: 'document_object_id'",
                "• foreignField: 'module_id'",
                "• as: 'knowledge'"
            ]
        },
        {
            "stage": "4. $lookup (modules)",
            "purpose": "Get module information",
            "details": [
                "• from: 'modules'",
                "• localField: 'document_object_id'", 
                "• foreignField: '_id'",
                "• as: 'module'"
            ]
        },
        {
            "stage": "5. $project",
            "purpose": "Select relevant fields",
            "details": [
                "• Chunk: _id, text, positions",
                "• Knowledge: title, summary, metadata",
                "• Module: id, tags",
                "• Score: vectorSearchScore"
            ]
        }
    ]
    
    for stage_info in pipeline_stages:
        print(f"\n{stage_info['stage']}")
        print(f"Purpose: {stage_info['purpose']}")
        for detail in stage_info['details']:
            print(f"   {detail}")
    
    print("\n📋 RESULT STRUCTURE")
    print("-" * 25)
    
    sample_result = {
        "_id": "ObjectId('...')",
        "chunk_text": "AWS VPC configuration requires...",
        "chunk_id": 1,
        "chunk_start": 0,
        "chunk_end": 300,
        "filename": "aws-vpc-guide",
        "filepath": "s3://bucket/docs/aws-vpc-guide.pdf",
        "summary": "Comprehensive AWS VPC setup guide",
        "keywords": "aws, vpc, networking, terraform",
        "content": "This document explains...",
        "intent_category": "infrastructure",
        "is_terraform": True,
        "module_id": "mod_aws_vpc",
        "module_tags": ["aws", "infrastructure", "terraform"],
        "score": 0.87
    }
    
    print("Sample search result:")
    for key, value in sample_result.items():
        if isinstance(value, str) and len(value) > 50:
            value = value[:47] + "..."
        print(f"   {key}: {value}")
    
    print("\n⚡ PERFORMANCE OPTIMIZATIONS")
    print("-" * 35)
    
    optimizations = [
        "🔸 Direct embedding storage (no nested arrays)",
        "🔸 Vector index on 'embedding' field",
        "🔸 Efficient ObjectId conversion",
        "🔸 Projection limits returned fields",
        "🔸 Connection pooling for MongoDB",
        "🔸 Concurrent embedding generation",
        "🔸 Timeout handling for API calls",
        "🔸 Fallback to text search if vector fails"
    ]
    
    for opt in optimizations:
        print(f"   {opt}")
    
    print("\n🔄 ERROR HANDLING & FALLBACKS")
    print("-" * 35)
    
    error_scenarios = [
        {
            "scenario": "Vector search fails",
            "action": "Fall back to regex text search",
            "impact": "Returns results but with default scores"
        },
        {
            "scenario": "No chunks found",
            "action": "Fall back to legacy search",
            "impact": "Uses old data structure if available"
        },
        {
            "scenario": "OpenAI API timeout",
            "action": "Return embedding/completion error",
            "impact": "User gets error message"
        },
        {
            "scenario": "Missing metadata",
            "action": "Use default values",
            "impact": "Results may have 'Unknown' fields"
        }
    ]
    
    for scenario in error_scenarios:
        print(f"\n   Scenario: {scenario['scenario']}")
        print(f"   Action:   {scenario['action']}")
        print(f"   Impact:   {scenario['impact']}")
    
    print("\n🎯 SCORING & RANKING")
    print("-" * 25)
    
    print("Vector similarity scores:")
    print("   • Range: 0.0 to 1.0")
    print("   • 1.0 = Perfect match")
    print("   • 0.8+ = Highly relevant")
    print("   • 0.6+ = Moderately relevant")
    print("   • 0.4+ = Somewhat relevant")
    print("   • <0.4 = Low relevance")
    print("")
    print("Scoring factors:")
    print("   • Semantic similarity (primary)")
    print("   • Keyword overlap")
    print("   • Context understanding")
    print("   • Document structure")
    
    print("\n📈 SEARCH QUALITY FACTORS")
    print("-" * 30)
    
    quality_factors = [
        "✅ Embedding model quality (text-embedding-3-small)",
        "✅ Chunk size optimization (300 chars default)",
        "✅ Document preprocessing quality",
        "✅ Metadata completeness",
        "✅ Vector index configuration",
        "✅ Query preprocessing",
        "✅ Result ranking accuracy",
        "✅ Context window utilization"
    ]
    
    for factor in quality_factors:
        print(f"   {factor}")
    
    print("\n" + "=" * 60)
    print("🎉 SEARCH PIPELINE EXPLANATION COMPLETE!")
    print("\nKey Takeaways:")
    print("• Uses semantic search with 1536-dim embeddings")
    print("• Joins 3 collections for comprehensive results")
    print("• Provides relevance scores for result ranking")
    print("• Includes robust error handling and fallbacks")
    print("• Optimized for performance and accuracy")

if __name__ == "__main__":
    explain_search_pipeline()
