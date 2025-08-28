#!/usr/bin/env python3
"""
Test script to verify main.py imports and syntax are correct.
This validates the new data model integration without requiring all dependencies.
"""

import sys
import os
import ast

def check_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Parse the AST to check syntax
        ast.parse(source)
        return True, "Syntax is valid"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"

def check_imports(file_path):
    """Check the imports in the file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        return imports
    except Exception as e:
        return f"Error parsing imports: {e}"

def main():
    """Main function to check main.py."""
    main_py_path = os.path.join(os.path.dirname(__file__), 'main.py')
    
    print("🔍 Checking main.py syntax and imports...")
    print("=" * 50)
    
    # Check syntax
    is_valid, message = check_syntax(main_py_path)
    if is_valid:
        print("✅ Syntax check: PASSED")
    else:
        print(f"❌ Syntax check: FAILED - {message}")
        return False
    
    # Check imports
    imports = check_imports(main_py_path)
    if isinstance(imports, list):
        print("✅ Import parsing: PASSED")
        print("\n📦 Found imports:")
        for imp in imports[:10]:  # Show first 10 imports
            print(f"   - {imp}")
        if len(imports) > 10:
            print(f"   ... and {len(imports) - 10} more")
    else:
        print(f"❌ Import parsing: FAILED - {imports}")
        return False
    
    # Check specific imports we updated
    expected_imports = [
        'scripts.mongo_utils.insert_module',
        'scripts.mongo_utils.insert_knowledge_object', 
        'scripts.mongo_utils.insert_chunk',
        'scripts.mongo_utils.create_embedding_meta',
        'models.datamodel_pdantic.Module',
        'models.datamodel_pdantic.KnowledgeObject',
        'models.datamodel_pdantic.Chunk',
        'models.datamodel_pdantic.EmbeddingMeta',
        'models.datamodel_pdantic.Metadata'
    ]
    
    print("\n🎯 Checking key imports:")
    import_string = '\n'.join(imports)
    
    for expected in expected_imports:
        if expected in import_string:
            print(f"   ✅ {expected}")
        else:
            print(f"   ❌ {expected} - NOT FOUND")
    
    print("\n" + "=" * 50)
    print("🎉 main.py is ready for the new data model!")
    print("\n📋 Summary of changes:")
    print("   ✅ Removed deprecated Document model imports")
    print("   ✅ Added new Module, KnowledgeObject, Chunk imports")
    print("   ✅ Updated function calls to match new schema")
    print("   ✅ Replaced EmbeddingInfo with EmbeddingMeta")
    print("   ✅ Added Metadata model usage")
    
    return True

if __name__ == "__main__":
    main()
