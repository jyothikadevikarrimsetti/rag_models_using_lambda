"""
Test script for Vector Search API with chat history.
Tests all endpoints and chat history functionality.
"""

import asyncio
import aiohttp
import json
import time
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class APITester:
    """Comprehensive API testing class"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
        self.test_results = []
    
    async def test_health_check(self, session: aiohttp.ClientSession):
        """Test basic health check endpoint"""
        print("🔍 Testing health check...")
        
        try:
            async with session.get(f"{self.base_url}/") as response:
                data = await response.json()
                assert response.status == 200
                assert data["status"] == "healthy"
                
                self.log_success("Health check", data)
                return True
                
        except Exception as e:
            self.log_error("Health check", str(e))
            return False
    
    async def test_detailed_health_check(self, session: aiohttp.ClientSession):
        """Test detailed health check endpoint"""
        print("🔍 Testing detailed health check...")
        
        try:
            async with session.get(f"{self.base_url}/health/detailed") as response:
                data = await response.json()
                assert response.status == 200
                assert "components" in data
                
                self.log_success("Detailed health check", data)
                return True
                
        except Exception as e:
            self.log_error("Detailed health check", str(e))
            return False
    
    async def test_search_without_history(self, session: aiohttp.ClientSession):
        """Test search without existing chat history"""
        print("🔍 Testing search without history...")
        
        payload = {
            "query": "What is the education background?",
            "top_k": 3,
            "use_new_structure": True
        }
        
        try:
            async with session.post(f"{self.base_url}/search", json=payload) as response:
                data = await response.json()
                assert response.status == 200
                assert "answer" in data
                assert "session_id" in data
                
                # Store session ID for future tests
                self.session_id = data["session_id"]
                
                self.log_success("Search without history", {
                    "session_id": data["session_id"],
                    "answer_length": len(data["answer"]),
                    "results_count": data["count"],
                    "response_time": data["response_time_ms"]
                })
                return True
                
        except Exception as e:
            self.log_error("Search without history", str(e))
            return False
    
    async def test_search_with_history(self, session: aiohttp.ClientSession):
        """Test search with existing chat history"""
        print("🔍 Testing search with history...")
        
        if not self.session_id:
            print("❌ No session ID available, skipping test")
            return False
        
        payload = {
            "query": "What about work experience?",
            "top_k": 3,
            "session_id": self.session_id,
            "use_new_structure": True
        }
        
        try:
            async with session.post(f"{self.base_url}/search", json=payload) as response:
                data = await response.json()
                assert response.status == 200
                assert data["session_id"] == self.session_id
                
                self.log_success("Search with history", {
                    "session_id": data["session_id"],
                    "answer_length": len(data["answer"]),
                    "results_count": data["count"]
                })
                return True
                
        except Exception as e:
            self.log_error("Search with history", str(e))
            return False
    
    async def test_get_chat_history(self, session: aiohttp.ClientSession):
        """Test retrieving chat history"""
        print("🔍 Testing get chat history...")
        
        if not self.session_id:
            print("❌ No session ID available, skipping test")
            return False
        
        try:
            url = f"{self.base_url}/chat-history/{self.session_id}"
            async with session.get(url) as response:
                data = await response.json()
                assert response.status == 200
                assert "messages" in data
                assert data["session_id"] == self.session_id
                
                self.log_success("Get chat history", {
                    "session_id": data["session_id"],
                    "total_messages": data["total_messages"],
                    "messages": len(data["messages"])
                })
                return True
                
        except Exception as e:
            self.log_error("Get chat history", str(e))
            return False
    
    async def test_list_sessions(self, session: aiohttp.ClientSession):
        """Test listing active sessions"""
        print("🔍 Testing list sessions...")
        
        try:
            async with session.get(f"{self.base_url}/sessions") as response:
                data = await response.json()
                assert response.status == 200
                assert "active_sessions" in data
                
                self.log_success("List sessions", {
                    "active_sessions": data["active_sessions"]
                })
                return True
                
        except Exception as e:
            self.log_error("List sessions", str(e))
            return False
    
    async def test_similarity_calculation(self, session: aiohttp.ClientSession):
        """Test similarity calculation endpoint"""
        print("🔍 Testing similarity calculation...")
        
        params = {
            "query1": "What is the education background?",
            "query2": "Tell me about educational qualifications"
        }
        
        try:
            async with session.post(f"{self.base_url}/search/similarity", params=params) as response:
                data = await response.json()
                assert response.status == 200
                assert "cosine_similarity" in data
                assert "similarity_percentage" in data
                
                self.log_success("Similarity calculation", {
                    "cosine_similarity": data["cosine_similarity"],
                    "similarity_percentage": data["similarity_percentage"]
                })
                return True
                
        except Exception as e:
            self.log_error("Similarity calculation", str(e))
            return False
    
    async def test_conversation_flow(self, session: aiohttp.ClientSession):
        """Test a complete conversation flow"""
        print("🔍 Testing conversation flow...")
        
        conversation = [
            "What technical skills are mentioned?",
            "How many years of experience?", 
            "What programming languages are used?"
        ]
        
        conversation_session_id = None
        
        try:
            for i, query in enumerate(conversation):
                payload = {
                    "query": query,
                    "top_k": 2,
                    "use_new_structure": True
                }
                
                if conversation_session_id:
                    payload["session_id"] = conversation_session_id
                
                async with session.post(f"{self.base_url}/search", json=payload) as response:
                    data = await response.json()
                    assert response.status == 200
                    
                    if not conversation_session_id:
                        conversation_session_id = data["session_id"]
                    else:
                        assert data["session_id"] == conversation_session_id
            
            # Verify conversation history
            url = f"{self.base_url}/chat-history/{conversation_session_id}"
            async with session.get(url) as response:
                data = await response.json()
                assert response.status == 200
                assert data["total_messages"] >= len(conversation) * 2  # User + assistant messages
            
            self.log_success("Conversation flow", {
                "session_id": conversation_session_id,
                "queries_processed": len(conversation),
                "total_messages": data["total_messages"]
            })
            return True
            
        except Exception as e:
            self.log_error("Conversation flow", str(e))
            return False
    
    async def test_clear_chat_history(self, session: aiohttp.ClientSession):
        """Test clearing chat history"""
        print("🔍 Testing clear chat history...")
        
        if not self.session_id:
            print("❌ No session ID available, skipping test")
            return False
        
        try:
            url = f"{self.base_url}/chat-history/{self.session_id}"
            async with session.delete(url) as response:
                data = await response.json()
                assert response.status == 200
                assert "cleared" in data
                
                self.log_success("Clear chat history", {
                    "session_id": data["session_id"],
                    "cleared": data["cleared"]
                })
                return True
                
        except Exception as e:
            self.log_error("Clear chat history", str(e))
            return False
    
    async def test_error_handling(self, session: aiohttp.ClientSession):
        """Test error handling"""
        print("🔍 Testing error handling...")
        
        test_cases = [
            {
                "name": "Empty query",
                "payload": {"query": "", "top_k": 3},
                "expected_status": 422  # Validation error
            },
            {
                "name": "Invalid top_k",
                "payload": {"query": "test", "top_k": 100},
                "expected_status": 422  # Validation error
            },
            {
                "name": "Invalid session ID in history",
                "url": f"{self.base_url}/chat-history/invalid_session_id",
                "method": "get",
                "expected_status": 200  # Should return empty history
            }
        ]
        
        error_tests_passed = 0
        
        for test_case in test_cases:
            try:
                if test_case.get("method") == "get":
                    async with session.get(test_case["url"]) as response:
                        status_ok = response.status == test_case["expected_status"]
                else:
                    async with session.post(f"{self.base_url}/search", json=test_case["payload"]) as response:
                        status_ok = response.status == test_case["expected_status"]
                
                if status_ok:
                    error_tests_passed += 1
                    print(f"  ✅ {test_case['name']}: Expected status {test_case['expected_status']}")
                else:
                    print(f"  ❌ {test_case['name']}: Got status {response.status}, expected {test_case['expected_status']}")
                    
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Exception {str(e)}")
        
        success = error_tests_passed == len(test_cases)
        
        self.log_success("Error handling", {
            "tests_passed": error_tests_passed,
            "total_tests": len(test_cases),
            "success_rate": f"{(error_tests_passed/len(test_cases)*100):.1f}%"
        }) if success else self.log_error("Error handling", f"Only {error_tests_passed}/{len(test_cases)} tests passed")
        
        return success
    
    def log_success(self, test_name: str, data: Dict[str, Any]):
        """Log successful test result"""
        result = {"test": test_name, "status": "PASS", "data": data}
        self.test_results.append(result)
        print(f"  ✅ {test_name}: PASSED")
        if isinstance(data, dict) and len(data) <= 3:
            for key, value in data.items():
                print(f"     {key}: {value}")
    
    def log_error(self, test_name: str, error: str):
        """Log failed test result"""
        result = {"test": test_name, "status": "FAIL", "error": error}
        self.test_results.append(result)
        print(f"  ❌ {test_name}: FAILED - {error}")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting API Tests")
        print("=" * 50)
        
        async with aiohttp.ClientSession() as session:
            # Basic functionality tests
            await self.test_health_check(session)
            await self.test_detailed_health_check(session)
            
            # Search functionality tests
            await self.test_search_without_history(session)
            await self.test_search_with_history(session)
            
            # Chat history tests
            await self.test_get_chat_history(session)
            await self.test_list_sessions(session)
            
            # Additional functionality tests
            await self.test_similarity_calculation(session)
            await self.test_conversation_flow(session)
            
            # Cleanup and error handling tests
            await self.test_clear_chat_history(session)
            await self.test_error_handling(session)
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['error']}")
        
        print(f"\n{'🎉 ALL TESTS PASSED!' if failed == 0 else '⚠️ SOME TESTS FAILED'}")


async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Vector Search API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--wait", type=int, default=0, help="Wait time before starting tests")
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds for API to start...")
        await asyncio.sleep(args.wait)
    
    tester = APITester(args.url)
    
    try:
        await tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
    finally:
        tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
