#!/usr/bin/env python3
"""
Test URL decoding for PDF filenames with special characters
"""

import urllib.parse

def test_url_decoding():
    """Test URL decoding for problematic PDF filenames."""
    
    print("🔍 TESTING URL DECODING FOR PDF FILENAMES")
    print("=" * 50)
    
    # Test cases based on the error
    test_cases = [
        {
            "original": "Jimson_Ratnam_JavaFullStackDeveloper_2%2Byears.pdf",
            "expected": "Jimson_Ratnam_JavaFullStackDeveloper_2+years.pdf",
            "description": "Plus sign encoded as %2B"
        },
        {
            "original": "John%20Doe%20Resume.pdf",
            "expected": "John Doe Resume.pdf", 
            "description": "Space encoded as %20"
        },
        {
            "original": "Software%26Engineer.pdf",
            "expected": "Software&Engineer.pdf",
            "description": "Ampersand encoded as %26"
        },
        {
            "original": "Resume%2B%2B.pdf",
            "expected": "Resume++.pdf",
            "description": "Multiple plus signs"
        },
        {
            "original": "normal_filename.pdf",
            "expected": "normal_filename.pdf",
            "description": "No encoding needed"
        }
    ]
    
    print("\n📋 TEST CASES")
    print("-" * 15)
    
    all_passed = True
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['description']}")
        print(f"   Original:  {case['original']}")
        print(f"   Expected:  {case['expected']}")
        
        # Perform URL decoding
        decoded = urllib.parse.unquote(case['original'])
        print(f"   Decoded:   {decoded}")
        
        # Check if it matches expected
        if decoded == case['expected']:
            print(f"   Result:    ✅ PASS")
        else:
            print(f"   Result:    ❌ FAIL")
            all_passed = False
    
    print(f"\n{'=' * 50}")
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("URL decoding will handle encoded filenames correctly.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("URL decoding may not work as expected.")
    
    print("\n🔧 IMPLEMENTATION")
    print("-" * 20)
    print("Added to main.py:")
    print("```python")
    print("import urllib.parse")
    print("pdf_key = record['s3']['object']['key']")
    print("pdf_key = urllib.parse.unquote(pdf_key)  # Decode URL encoding")
    print("```")
    
    print("\n🎯 SPECIFIC FIX FOR YOUR ERROR")
    print("-" * 35)
    problem_filename = "Jimson_Ratnam_JavaFullStackDeveloper_2%2Byears.pdf"
    fixed_filename = urllib.parse.unquote(problem_filename)
    
    print(f"Problem file: {problem_filename}")
    print(f"Fixed file:   {fixed_filename}")
    print(f"Result:       ✅ The '+' character is now properly decoded")
    
    print("\n🚀 NEXT STEPS")
    print("-" * 15)
    print("1. ✅ Updated main.py to decode PDF keys")
    print("2. ✅ Updated pdf_from_s3.py with fallback logic")
    print("3. 🔄 Rebuild and redeploy Docker image")
    print("4. 🔄 Test with the problematic PDF file")
    print("5. 🔄 The 404 error should be resolved")

if __name__ == "__main__":
    test_url_decoding()
