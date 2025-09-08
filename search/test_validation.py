"""
Test script for response validation functionality.
Run this to validate your RAG responses and test the validation endpoints.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000/api"

def test_search_with_validation():
    """Test the search endpoint and see validation results."""
    print("🔍 Testing search with validation...")
    
    search_request = {
        "query": "What is Terraform used for?",
        "top_k": 3,
        "use_new_structure": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/search", json=search_request)
        result = response.json()
        
        print(f"✅ Search Status: {response.status_code}")
        print(f"📝 Answer: {result['answer'][:200]}...")
        print(f"📊 Retrieved {result['count']} documents")
        
        # Check if validation results are included
        if 'validation' in result:
            validation = result['validation']
            print("\n🔬 Validation Results:")
            print(f"   Overall Quality Score: {validation.get('overall_quality', {}).get('score', 'N/A'):.2f}")
            print(f"   Is High Quality: {validation.get('overall_quality', {}).get('is_high_quality', 'N/A')}")
            print(f"   Recommendation: {validation.get('overall_quality', {}).get('recommendation', 'N/A')}")
            
            if 'grounding' in validation:
                grounding = validation['grounding']
                print(f"   Grounding Score: {grounding.get('confidence', 'N/A'):.2f}")
                print(f"   Is Grounded: {grounding.get('is_grounded', 'N/A')}")
        else:
            print("⚠️  No validation results found in response")
            
        return result
        
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return None

def test_validation_endpoint():
    """Test the dedicated validation endpoint."""
    print("\n🧪 Testing validation endpoint...")
    
    validation_request = {
        "query": "What is Terraform?",
        "response": "Terraform is an Infrastructure as Code (IaC) tool developed by HashiCorp that allows you to define and provision data center infrastructure using a declarative configuration language."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/validate", json=validation_request)
        result = response.json()
        
        print(f"✅ Validation Status: {response.status_code}")
        print(f"🆔 Validation ID: {result['validation_id']}")
        print(f"✓ Is Valid: {result['is_valid']}")
        print(f"📊 Quality Score: {result['quality_score']:.2f}")
        
        return result['validation_id']
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return None

def test_feedback_endpoint(validation_id=None):
    """Test the feedback submission endpoint."""
    print("\n📝 Testing feedback endpoint...")
    
    feedback_request = {
        "validation_id": validation_id,
        "query": "What is Terraform?",
        "response": "Terraform is an Infrastructure as Code tool...",
        "user_rating": 4,
        "feedback_text": "Good response but could include more examples"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/feedback", json=feedback_request)
        result = response.json()
        
        print(f"✅ Feedback Status: {response.status_code}")
        print(f"🆔 Feedback ID: {result['feedback_id']}")
        print(f"💬 Message: {result['message']}")
        
        return result['feedback_id']
        
    except Exception as e:
        print(f"❌ Feedback test failed: {e}")
        return None

def test_validation_stats():
    """Test the validation statistics endpoint."""
    print("\n📈 Testing validation stats endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/validation-stats")
        result = response.json()
        
        print(f"✅ Stats Status: {response.status_code}")
        print(f"📊 Total Validations: {result['total_validations']}")
        print(f"🎯 High Quality Rate: {result['high_quality_rate']:.2%}")
        print(f"⭐ Average Quality Score: {result['average_quality_score']:.2f}")
        print(f"💬 Total Feedback: {result['total_feedback']}")
        print(f"⭐ Average User Rating: {result['average_user_rating']:.1f}/5")
        
        return result
        
    except Exception as e:
        print(f"❌ Stats test failed: {e}")
        return None

def main():
    """Run all validation tests."""
    print("🚀 Starting Response Validation Tests")
    print("=" * 50)
    
    # Test 1: Search with validation
    search_result = test_search_with_validation()
    
    # Test 2: Validation endpoint
    validation_id = test_validation_endpoint()
    
    # Test 3: Feedback endpoint
    feedback_id = test_feedback_endpoint(validation_id)
    
    # Wait a moment for data to be stored
    time.sleep(1)
    
    # Test 4: Validation stats
    stats_result = test_validation_stats()
    
    print("\n" + "=" * 50)
    print("🎉 Validation tests completed!")
    
    if search_result and validation_id and feedback_id and stats_result:
        print("✅ All tests passed successfully")
    else:
        print("⚠️  Some tests failed - check the output above")

if __name__ == "__main__":
    main()
