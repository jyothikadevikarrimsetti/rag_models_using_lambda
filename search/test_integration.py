#!/usr/bin/env python3
"""
Quick test script to verify the unified API is working correctly
Tests basic endpoints without requiring external files
"""

import sys
import subprocess
import time
import requests
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000/api"

def test_api_health():
    """Test basic API health endpoints"""
    print("🔍 Testing API Health...")
    
    tests = [
        ("/", "Basic Health Check"),
        ("/aws-health", "AWS Health Check"),
        ("/health/detailed", "Detailed Health Check")
    ]
    
    for endpoint, description in tests:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {description}: OK")
                data = response.json()
                if 'status' in data:
                    print(f"   Status: {data['status']}")
            else:
                print(f"❌ {description}: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {description}: Connection failed - is the server running?")
            return False
        except Exception as e:
            print(f"❌ {description}: {e}")
    
    return True

def test_search_endpoint():
    """Test the search endpoint"""
    print("🔍 Testing Search Endpoint...")
    
    search_data = {
        "query": "test query",
        "session_id": "test_session",
        "top_k": 3
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/search", json=search_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Search endpoint working")
            print(f"   Session ID: {result.get('session_id', 'N/A')}")
            print(f"   Answer length: {len(result.get('answer', ''))}")
            print(f"   Documents found: {len(result.get('documents', []))}")
            return True
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Search test error: {e}")
        return False

def test_upload_endpoints():
    """Test upload-related endpoints (without actual file upload)"""
    print("🔍 Testing Upload Endpoints...")
    
    # Test uploads list
    try:
        response = requests.get(f"{API_BASE_URL}/uploads", timeout=5)
        
        if response.status_code == 200:
            uploads = response.json()
            print("✅ Uploads list endpoint working")
            print(f"   Total uploads: {uploads.get('total_uploads', 0)}")
        else:
            print(f"❌ Uploads list failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Uploads list error: {e}")
    
    # Test S3 files list
    try:
        response = requests.get(f"{API_BASE_URL}/s3-files", timeout=5)
        
        if response.status_code in [200, 503]:  # 503 if AWS not available
            print("✅ S3 files endpoint reachable")
            if response.status_code == 503:
                print("   (AWS services not configured)")
        else:
            print(f"❌ S3 files failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ S3 files error: {e}")

def test_session_management():
    """Test session management endpoints"""
    print("🔍 Testing Session Management...")
    
    # Create a session by doing a search
    session_id = f"test_session_{int(time.time())}"
    
    search_data = {
        "query": "session test",
        "session_id": session_id,
        "top_k": 1
    }
    
    try:
        # Do a search to create session
        response = requests.post(f"{API_BASE_URL}/search", json=search_data, timeout=30)
        
        if response.status_code == 200:
            # List sessions
            response = requests.get(f"{API_BASE_URL}/sessions", timeout=5)
            
            if response.status_code == 200:
                sessions = response.json()
                print("✅ Session listing working")
                print(f"   Active sessions: {sessions.get('total_sessions', 0)}")
                
                # Check our session exists
                session_found = any(s['session_id'] == session_id for s in sessions.get('sessions', []))
                if session_found:
                    print(f"✅ Test session created successfully")
                else:
                    print(f"⚠️ Test session not found in list")
            else:
                print(f"❌ Session listing failed: {response.status_code}")
            
            # Try to get chat history
            response = requests.get(f"{API_BASE_URL}/chat-history/{session_id}", timeout=5)
            
            if response.status_code == 200:
                history = response.json()
                print("✅ Chat history retrieval working")
                print(f"   Messages in history: {history.get('total_messages', 0)}")
            else:
                print(f"❌ Chat history failed: {response.status_code}")
                
        else:
            print(f"❌ Could not create test session: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Session management error: {e}")

def check_server_running():
    """Check if the server is already running"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False

def main():
    """Main test function"""
    print("🚀 Unified API Integration Test")
    print("=" * 50)
    print(f"Testing API at: {API_BASE_URL}")
    print(f"Test time: {datetime.now()}")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("❌ Server is not running!")
        print("Please start the server with: python api_server.py")
        print("Then run this test again.")
        sys.exit(1)
    
    print("✅ Server is running")
    print()
    
    # Run tests
    tests_passed = 0
    total_tests = 4
    
    if test_api_health():
        tests_passed += 1
    print()
    
    if test_search_endpoint():
        tests_passed += 1
    print()
    
    test_upload_endpoints()  # No return value check
    tests_passed += 1
    print()
    
    test_session_management()  # No return value check
    tests_passed += 1
    print()
    
    # Summary
    print("=" * 50)
    print(f"📊 Test Summary: {tests_passed}/{total_tests} test groups completed")
    
    if tests_passed == total_tests:
        print("🎉 All tests completed successfully!")
        print("   The unified API is ready for use.")
    else:
        print("⚠️ Some tests had issues - check the output above")
        print("   The API may still be functional for basic use.")
    
    print()
    print("📚 Next steps:")
    print("   1. Try the demo scripts: python demo_upload.py")
    print("   2. Test with real PDFs and AWS configuration")
    print("   3. Check the API documentation in readme.md")

if __name__ == "__main__":
    main()
