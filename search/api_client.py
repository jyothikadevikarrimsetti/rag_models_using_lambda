"""
Example client for the Vector Search API with chat history.
Demonstrates how to interact with the API endpoints.
"""

import requests
import json
import time
from typing import Optional

class VectorSearchClient:
    """Client for interacting with the Vector Search API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session_id: Optional[str] = None
    
    def search(self, query: str, top_k: int = 3, use_new_structure: bool = True) -> dict:
        """
        Perform a search with optional chat history context
        """
        url = f"{self.base_url}/search"
        
        payload = {
            "query": query,
            "top_k": top_k,
            "use_new_structure": use_new_structure
        }
        
        if self.session_id:
            payload["session_id"] = self.session_id
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # Store session ID for future requests
        if not self.session_id:
            self.session_id = result.get("session_id")
        
        return result
    
    def get_chat_history(self, session_id: Optional[str] = None) -> dict:
        """Get chat history for current or specified session"""
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No session ID available")
        
        url = f"{self.base_url}/chat-history/{session_id}"
        response = requests.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def clear_chat_history(self, session_id: Optional[str] = None) -> dict:
        """Clear chat history for current or specified session"""
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No session ID available")
        
        url = f"{self.base_url}/chat-history/{session_id}"
        response = requests.delete(url)
        response.raise_for_status()
        
        return response.json()
    
    def list_active_sessions(self) -> dict:
        """List all active chat sessions"""
        url = f"{self.base_url}/sessions"
        response = requests.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def calculate_similarity(self, query1: str, query2: str) -> dict:
        """Calculate semantic similarity between two queries"""
        url = f"{self.base_url}/search/similarity"
        
        params = {
            "query1": query1,
            "query2": query2
        }
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def health_check(self) -> dict:
        """Basic health check"""
        url = f"{self.base_url}/"
        response = requests.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def detailed_health_check(self) -> dict:
        """Detailed health check of all components"""
        url = f"{self.base_url}/health/detailed"
        response = requests.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def start_new_session(self):
        """Start a new chat session"""
        self.session_id = None


def demo_conversation():
    """Demonstrate a conversation with chat history"""
    
    print("🤖 Vector Search API Demo with Chat History")
    print("=" * 50)
    
    # Initialize client
    client = VectorSearchClient()
    
    # Check API health
    try:
        health = client.health_check()
        print(f"✅ API Health: {health['status']}")
        print(f"   Redis Connected: {health['redis_connected']}")
    except Exception as e:
        print(f"❌ API Health Check Failed: {e}")
        return
    
    # Demo conversation
    conversation_queries = [
        "What is the education background in the documents?",
        "What about work experience?",
        "Can you tell me more about the technical skills?",
        "What programming languages are mentioned?",
        "How many years of experience does the person have?"
    ]
    
    print(f"\n🔍 Starting conversation with {len(conversation_queries)} queries...")
    
    for i, query in enumerate(conversation_queries, 1):
        print(f"\n--- Query {i} ---")
        print(f"User: {query}")
        
        try:
            # Perform search
            start_time = time.time()
            result = client.search(query, top_k=3)
            end_time = time.time()
            
            print(f"Assistant: {result['answer']}")
            print(f"Session ID: {result['session_id']}")
            print(f"Results: {result['count']} documents")
            print(f"Search Method: {result['search_method']}")
            print(f"Response Time: {result['response_time_ms']}ms")
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
    
    # Show chat history
    print(f"\n📚 Chat History Summary:")
    try:
        history = client.get_chat_history()
        print(f"Session: {history['session_id']}")
        print(f"Total Messages: {history['total_messages']}")
        
        for msg in history['messages'][-4:]:  # Show last 4 messages
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"{role_emoji} {msg['role'].title()}: {content}")
            
    except Exception as e:
        print(f"❌ Failed to get chat history: {e}")


def demo_similarity():
    """Demonstrate similarity calculation"""
    
    print("\n🔍 Similarity Calculation Demo")
    print("=" * 40)
    
    client = VectorSearchClient()
    
    test_pairs = [
        ("What is the education background?", "Tell me about educational qualifications"),
        ("What programming languages are used?", "Which coding languages are mentioned?"),
        ("Work experience details", "Professional background information"),
        ("Technical skills", "What is the weather today?")  # Unrelated queries
    ]
    
    for query1, query2 in test_pairs:
        try:
            similarity = client.calculate_similarity(query1, query2)
            print(f"\nQuery 1: {query1}")
            print(f"Query 2: {query2}")
            print(f"Similarity: {similarity['similarity_percentage']}")
            
        except Exception as e:
            print(f"❌ Similarity calculation failed: {e}")


def demo_session_management():
    """Demonstrate session management"""
    
    print("\n📊 Session Management Demo")
    print("=" * 35)
    
    client = VectorSearchClient()
    
    # Create multiple sessions
    sessions_created = []
    
    for i in range(3):
        client.start_new_session()
        result = client.search(f"Test query {i+1}")
        sessions_created.append(result['session_id'])
        print(f"Created session {i+1}: {result['session_id']}")
    
    # List all sessions
    try:
        sessions = client.list_active_sessions()
        print(f"\nActive Sessions: {sessions['active_sessions']}")
        
        for session in sessions['sessions'][-3:]:  # Show last 3
            print(f"  Session: {session['session_id']}")
            print(f"  Messages: {session['message_count']}")
    
    except Exception as e:
        print(f"❌ Failed to list sessions: {e}")
    
    # Clear a session
    if sessions_created:
        try:
            result = client.clear_chat_history(sessions_created[0])
            print(f"\nCleared session: {sessions_created[0]}")
            print(f"Success: {result['cleared']}")
            
        except Exception as e:
            print(f"❌ Failed to clear session: {e}")


if __name__ == "__main__":
    try:
        # Run demos
        demo_conversation()
        demo_similarity()
        demo_session_management()
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
