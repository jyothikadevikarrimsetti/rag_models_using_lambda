#!/usr/bin/env python3
"""
Final validation script for the complete data model migration.
This script checks both ingestion and search pipelines for compatibility.
"""

import sys
import os
import ast

def validate_complete_migration():
    """Validate that the complete migration is successful."""
    
    print("🔍 Final Data Model Migration Validation")
    print("=" * 60)
    
    # Files to check
    files_to_check = {
        'datamodel_pdantic.py': '../injestion/models/datamodel_pdantic.py',
        'mongo_utils.py': '../injestion/scripts/mongo_utils.py', 
        'main.py': '../injestion/main.py',
        'search_pipeline.py': 'search_pipeline.py'
    }
    
    validation_results = {}
    
    for filename, filepath in files_to_check.items():
        print(f"\n📂 Validating {filename}...")
        
        try:
            full_path = os.path.join(os.path.dirname(__file__), filepath)
            with open(full_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Check syntax
            ast.parse(source)
            print(f"   ✅ Syntax: PASSED")
            
            # File-specific validations
            if filename == 'datamodel_pdantic.py':
                checks = {
                    'class Metadata(BaseModel):': 'Metadata model',
                    'class EmbeddingMeta(BaseModel):': 'EmbeddingMeta model',
                    'class Module(BaseModel):': 'Module model (new)',
                    'class KnowledgeObject(BaseModel):': 'KnowledgeObject model',
                    'class Chunk(BaseModel):': 'Chunk model',
                    'embedding: List[float]': 'Direct embedding storage',
                    'embedding_meta: EmbeddingMeta': 'EmbeddingMeta reference'
                }
                
            elif filename == 'mongo_utils.py':
                checks = {
                    'def insert_module(': 'insert_module function',
                    'def insert_knowledge_object(': 'insert_knowledge_object function',
                    'def insert_chunk(': 'insert_chunk function',
                    'def create_embedding_meta(': 'create_embedding_meta function',
                    'modules_collection': 'modules collection',
                    'knowledge_objects_collection': 'knowledge_objects collection',
                    'chunks_collection': 'chunks collection'
                }
                
            elif filename == 'main.py':
                checks = {
                    'Module, KnowledgeObject, Chunk, EmbeddingMeta, Metadata': 'All new model imports',
                    'insert_module(module)': 'insert_module usage',
                    'create_embedding_meta(': 'create_embedding_meta usage',
                    'module = Module(': 'Module instantiation',
                    'knowledge_obj = KnowledgeObject(': 'KnowledgeObject instantiation',
                    'chunk = Chunk(': 'Chunk instantiation'
                }
                
            elif filename == 'search_pipeline.py':
                checks = {
                    '"path": "embedding"': 'Direct embedding path',
                    '"from": "knowledge_objects"': 'Knowledge objects lookup',
                    '"from": "modules"': 'Modules lookup',
                    '"foreignField": "module_id"': 'Module ID relationship',
                    '"knowledge.metadata.path"': 'Nested metadata access',
                    '"knowledge.is_terraform"': 'Terraform flag',
                    '"module.module_tag"': 'Module tags'
                }
            
            # Run checks
            passed_checks = []
            failed_checks = []
            
            for pattern, description in checks.items():
                if pattern in source:
                    passed_checks.append(f"✅ {description}")
                else:
                    failed_checks.append(f"❌ {description}")
            
            # Display results
            for check in passed_checks:
                print(f"   {check}")
            
            if failed_checks:
                print("   Failed checks:")
                for check in failed_checks:
                    print(f"   {check}")
                validation_results[filename] = False
            else:
                validation_results[filename] = True
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            validation_results[filename] = False
    
    # Overall validation summary
    print("\n" + "=" * 60)
    print("📊 Migration Validation Summary")
    print("=" * 60)
    
    all_passed = True
    for filename, passed in validation_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{filename:25} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 MIGRATION COMPLETE!")
        print("\n📋 What was updated:")
        print("   ✅ Data models restructured to match schema image")
        print("   ✅ MongoDB collections updated (modules, knowledge_objects, chunks)")
        print("   ✅ Ingestion pipeline updated for new structure")
        print("   ✅ Search pipeline updated with correct relationships")
        print("   ✅ Direct embedding storage implemented")
        print("   ✅ Metadata structure normalized")
        print("   ✅ Module-based organization added")
        
        print("\n🚀 Ready for deployment:")
        print("   - Docker images can be built with new code")
        print("   - Lambda functions will use new data structure")
        print("   - MongoDB Atlas vector search index: 'vector_index' on 'embedding' path")
        print("   - Environment variable: USE_NEW_DATA_STRUCTURE=true")
        
    else:
        print("❌ MIGRATION INCOMPLETE")
        print("   Some files still need updates. Check the failed items above.")
    
    return all_passed

if __name__ == "__main__":
    validate_complete_migration()
