"""
Simple demo script for Vector Search API with chat history.
Uses only standard library modules for immediate testing.
"""

import json
import urllib.request
import urllib.parse
import time
import sys

class SimpleAPIClient:
    """Simple API client using only standard library"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request using urllib"""
        url = f"{self.base_url}{endpoint}"
        
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        headers = {"Content-Type": "application/json"}
        
        if data:
            data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode('utf-8')
            print(f"HTTP Error {e.code}: {error_msg}")
            return None
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def health_check(self):
        """Check API health"""
        return self._make_request("GET", "/")
    
    def search(self, query, top_k=3, use_new_structure=True):
        """Perform search"""
        payload = {
            "query": query,
            "top_k": top_k,
            "use_new_structure": use_new_structure
        }
        
        if self.session_id:
            payload["session_id"] = self.session_id
        
        result = self._make_request("POST", "/search", data=payload)
        
        if result and not self.session_id:
            self.session_id = result.get("session_id")
        
        return result
    
    def get_chat_history(self):
        """Get chat history"""
        if not self.session_id:
            return None
        
        return self._make_request("GET", f"/chat-history/{self.session_id}")
    
    def calculate_similarity(self, query1, query2):
        """Calculate similarity"""
        params = {"query1": query1, "query2": query2}
        return self._make_request("POST", "/search/similarity", params=params)
    
    def list_sessions(self):
        """List active sessions"""
        return self._make_request("GET", "/sessions")


def print_header(title):
    """Print section header"""
    print(f"\n{'='*50}")
    print(f"🔍 {title}")
    print(f"{'='*50}")


def print_result(title, result, show_details=True):
    """Print result with formatting"""
    if result:
        print(f"✅ {title}: SUCCESS")
        if show_details:
            # Print key information
            if "answer" in result:
                print(f"   Answer: {result['answer'][:100]}...")
            if "session_id" in result:
                print(f"   Session: {result['session_id']}")
            if "count" in result:
                print(f"   Results: {result['count']}")
            if "response_time_ms" in result:
                print(f"   Time: {result['response_time_ms']}ms")
            if "status" in result:
                print(f"   Status: {result['status']}")
            if "total_messages" in result:
                print(f"   Messages: {result['total_messages']}")
    else:
        print(f"❌ {title}: FAILED")


def demo_basic_functionality():
    """Demo basic API functionality"""
    print_header("Basic Functionality Demo")
    
    client = SimpleAPIClient()
    
    # Health check
    print("🏥 Testing health check...")
    health = client.health_check()
    print_result("Health Check", health)
    
    if not health:
        print("❌ API is not responding. Make sure it's running at http://localhost:8000")
        return False
    
    # Basic search
    print("\n🔍 Testing basic search...")
    search_result = client.search("What is the education background?")
    print_result("Basic Search", search_result)
    
    if search_result:
        # Follow-up search with context
        print("\n🔄 Testing search with context...")
        context_result = client.search("What about work experience?")
        print_result("Context Search", context_result)
        
        # Get chat history
        print("\n📚 Testing chat history...")
        history = client.get_chat_history()
        print_result("Chat History", history)
        
        if history:
            print(f"   Conversation has {len(history.get('messages', []))} messages")
    
    return True


def demo_conversation_flow():
    """Demo a conversation flow"""
    print_header("Conversation Flow Demo")
    
    client = SimpleAPIClient()
    
    conversation = [
        "What technical skills are mentioned in the documents?",
        "How many years of experience does the person have?",
        "What programming languages are used?",
        "Tell me about the educational background?",
        "What about certifications?"
    ]
    
    print(f"🗣️ Starting conversation with {len(conversation)} questions...")
    
    for i, question in enumerate(conversation, 1):
        print(f"\n--- Question {i} ---")
        print(f"❓ User: {question}")
        
        result = client.search(question, top_k=2)
        
        if result:
            answer = result.get("answer", "No answer")
            print(f"🤖 Assistant: {answer[:150]}...")
            print(f"   📊 Found {result.get('count', 0)} relevant documents")
            print(f"   ⏱️ Response time: {result.get('response_time_ms', 0)}ms")
        else:
            print("❌ Search failed")
            break
        
        # Small delay between questions
        time.sleep(1)
    
    # Show final conversation summary
    print(f"\n📋 Conversation Summary:")
    history = client.get_chat_history()
    if history:
        messages = history.get("messages", [])
        print(f"   Total messages: {len(messages)}")
        print(f"   Session ID: {history.get('session_id', 'Unknown')}")
        
        # Show last few messages
        print(f"   Last few exchanges:")
        for msg in messages[-4:]:
            role_icon = "👤" if msg["role"] == "user" else "🤖"
            content = msg["content"][:80] + "..." if len(msg["content"]) > 80 else msg["content"]
            print(f"     {role_icon} {content}")


def demo_similarity_analysis():
    """Demo similarity analysis"""
    print_header("Similarity Analysis Demo")
    
    client = SimpleAPIClient()
    
    query_pairs = [
        ("What is the education background?", "Tell me about educational qualifications"),
        ("What programming languages are used?", "Which coding languages are mentioned?"),
        ("Work experience details", "Professional background information"),
        ("Technical skills and abilities", "What is the weather today?")  # Should be low similarity
    ]
    
    print("🔍 Comparing query similarities...")
    
    for i, (query1, query2) in enumerate(query_pairs, 1):
        print(f"\n--- Pair {i} ---")
        print(f"Query 1: {query1}")
        print(f"Query 2: {query2}")
        
        similarity = client.calculate_similarity(query1, query2)
        
        if similarity:
            percentage = similarity.get("similarity_percentage", "Unknown")
            score = similarity.get("cosine_similarity", 0)
            
            print(f"Similarity: {percentage}")
            
            # Interpret similarity
            if score > 0.8:
                print("   🟢 Very similar queries")
            elif score > 0.6:
                print("   🟡 Moderately similar queries")
            elif score > 0.4:
                print("   🟠 Somewhat similar queries")
            else:
                print("   🔴 Different topics")
        else:
            print("❌ Similarity calculation failed")


def demo_session_management():
    """Demo session management"""
    print_header("Session Management Demo")
    
    # Create multiple clients to simulate different users
    clients = [SimpleAPIClient() for _ in range(3)]
    
    print("👥 Creating multiple user sessions...")
    
    for i, client in enumerate(clients, 1):
        print(f"\n--- User {i} ---")
        result = client.search(f"Test query from user {i}")
        
        if result:
            print(f"✅ User {i} session: {result.get('session_id', 'Unknown')}")
        else:
            print(f"❌ User {i} session creation failed")
    
    # List all sessions
    print(f"\n📊 Active Sessions Overview:")
    sessions = clients[0].list_sessions()  # Any client can list sessions
    
    if sessions:
        print(f"   Total active sessions: {sessions.get('active_sessions', 0)}")
        
        session_list = sessions.get('sessions', [])
        for session in session_list[-3:]:  # Show last 3
            session_id = session.get('session_id', 'Unknown')
            message_count = session.get('message_count', 0)
            print(f"   📝 {session_id}: {message_count} messages")
    else:
        print("❌ Failed to list sessions")


def main():
    """Main demo function"""
    print("🚀 Vector Search API Demo with Chat History")
    print("Using only Python standard library")
    print("Make sure the API is running at http://localhost:8000")
    
    try:
        # Run demos in sequence
        if demo_basic_functionality():
            demo_conversation_flow()
            demo_similarity_analysis()
            demo_session_management()
        
        print(f"\n{'='*50}")
        print("🎉 Demo completed!")
        print("💡 Try the interactive API docs at: http://localhost:8000/docs")
        print("📚 See README_API.md for more information")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print(f"Make sure the API server is running: python startup.py local")


if __name__ == "__main__":
    main()
