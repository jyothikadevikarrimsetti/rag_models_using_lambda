"""
Test script to demonstrate chat history integration in vector search.
Shows how conversation context enhances search results.
"""

import json
import urllib.request
import urllib.parse
import time

class ContextDemoClient:
    """Client to demonstrate context-aware search"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request"""
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
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def search(self, query, top_k=3):
        """Perform search with session management"""
        payload = {
            "query": query,
            "top_k": top_k,
            "use_new_structure": True
        }
        
        if self.session_id:
            payload["session_id"] = self.session_id
        
        result = self._make_request("POST", "/search", data=payload)
        
        if result and not self.session_id:
            self.session_id = result.get("session_id")
        
        return result
    
    def get_chat_history(self):
        """Get current chat history"""
        if not self.session_id:
            return None
        return self._make_request("GET", f"/chat-history/{self.session_id}")


def demonstrate_context_integration():
    """Demonstrate how chat history enhances search context"""
    
    print("🧠 Chat History Context Integration Demo")
    print("=" * 60)
    print("This demo shows how conversation history enhances search results")
    print()
    
    client = ContextDemoClient()
    
    # Test conversation that builds context
    conversation_flow = [
        {
            "query": "What is the education background in the documents?",
            "description": "Initial query about education",
            "context_type": "No previous context"
        },
        {
            "query": "What specific degree was obtained?",
            "description": "Follow-up asking for details",
            "context_type": "Previous: education background"
        },
        {
            "query": "What about work experience?", 
            "description": "Topic change to work experience",
            "context_type": "Previous: education + degree details"
        },
        {
            "query": "How many years of experience in total?",
            "description": "Follow-up for specific work details",
            "context_type": "Previous: education, degree, work experience"
        },
        {
            "query": "What programming languages are mentioned?",
            "description": "Topic change to technical skills",
            "context_type": "Previous: education, work, asking for tech skills"
        },
        {
            "query": "Are these languages used in the work projects?",
            "description": "Connecting programming languages to work experience",
            "context_type": "Previous: all above topics + programming languages"
        }
    ]
    
    print("🗣️ Starting contextual conversation...")
    print()
    
    for i, step in enumerate(conversation_flow, 1):
        print(f"--- Step {i}: {step['description']} ---")
        print(f"Context Available: {step['context_type']}")
        print(f"User Query: \"{step['query']}\"")
        print()
        
        # Perform search
        start_time = time.time()
        result = client.search(step['query'], top_k=2)
        end_time = time.time()
        
        if result:
            print(f"🤖 Assistant Response:")
            answer = result.get('answer', 'No answer')
            
            # Display answer with indication of context usage
            print(f"   {answer}")
            print()
            print(f"📊 Search Details:")
            print(f"   • Results found: {result.get('count', 0)}")
            print(f"   • Response time: {int((end_time - start_time) * 1000)}ms")
            print(f"   • Session ID: {result.get('session_id', 'Unknown')[:12]}...")
            
            # Show if context was likely used (by checking answer patterns)
            if i > 1:  # After first query
                context_indicators = [
                    "previous", "mentioned earlier", "as discussed", "building on",
                    "in addition to", "furthermore", "also", "moreover"
                ]
                
                has_context_reference = any(indicator in answer.lower() for indicator in context_indicators)
                
                print(f"   • Context integration: {'✅ Detected' if has_context_reference else '❓ Possible'}")
            
        else:
            print("❌ Search failed")
        
        print()
        
        # Show chat history growth
        if i % 2 == 0:  # Every 2nd step
            history = client.get_chat_history()
            if history:
                print(f"📚 Conversation Status: {history.get('total_messages', 0)} messages in history")
                print()
        
        # Brief pause between queries
        time.sleep(1)
    
    # Final conversation summary
    print("=" * 60)
    print("📋 Final Conversation Analysis")
    print("=" * 60)
    
    history = client.get_chat_history()
    if history:
        messages = history.get('messages', [])
        print(f"Total conversation length: {len(messages)} messages")
        print(f"Session duration: Full conversation")
        print()
        
        # Show how context evolved
        print("🔄 Context Evolution:")
        user_queries = [msg for msg in messages if msg.get('role') == 'user']
        
        for i, query in enumerate(user_queries, 1):
            print(f"   {i}. {query.get('content', '')}")
        
        print()
        
        # Demonstrate the context that would be available for the next query
        print("🧠 Available Context for Next Query:")
        recent_exchanges = []
        
        for i in range(len(messages) - 4, len(messages), 2):
            if i >= 0 and i + 1 < len(messages):
                user_msg = messages[i]
                assistant_msg = messages[i + 1]
                
                if user_msg.get('role') == 'user' and assistant_msg.get('role') == 'assistant':
                    recent_exchanges.append({
                        'question': user_msg.get('content', ''),
                        'answer': assistant_msg.get('content', '')[:100] + '...'
                    })
        
        for i, exchange in enumerate(recent_exchanges[-2:], 1):  # Last 2 exchanges
            print(f"   Context {i}:")
            print(f"     Q: {exchange['question']}")
            print(f"     A: {exchange['answer']}")
        
    else:
        print("❌ Could not retrieve conversation history")


def demonstrate_context_benefits():
    """Show specific benefits of context integration"""
    
    print("\n🎯 Context Integration Benefits Demo")
    print("=" * 50)
    
    # Test queries that benefit from context
    context_scenarios = [
        {
            "setup_query": "What programming languages are mentioned in the documents?",
            "followup_query": "Which of these are used for web development?",
            "benefit": "Refers to previously mentioned languages without re-listing them"
        },
        {
            "setup_query": "What is the person's educational background?",
            "followup_query": "Is this education relevant to their current work?",
            "benefit": "Connects education context with work experience"
        },
        {
            "setup_query": "How many years of experience does the person have?",
            "followup_query": "What was their first job?",
            "benefit": "Uses experience timeline context to answer career questions"
        }
    ]
    
    for i, scenario in enumerate(context_scenarios, 1):
        print(f"--- Scenario {i}: {scenario['benefit']} ---")
        
        # Fresh client for each scenario
        client = ContextDemoClient()
        
        # Setup context
        print(f"Setup: \"{scenario['setup_query']}\"")
        setup_result = client.search(scenario['setup_query'])
        
        if setup_result:
            print(f"✅ Context established")
            
            # Follow-up with context
            print(f"Follow-up: \"{scenario['followup_query']}\"")
            followup_result = client.search(scenario['followup_query'])
            
            if followup_result:
                answer = followup_result.get('answer', '')
                print(f"🤖 Contextual Answer: {answer[:200]}...")
                
                # Check for context integration
                if any(word in answer.lower() for word in ['these', 'mentioned', 'discussed', 'above']):
                    print("✅ Context successfully integrated into response")
                else:
                    print("❓ Context integration unclear")
            else:
                print("❌ Follow-up failed")
        else:
            print("❌ Setup failed")
        
        print()


def main():
    """Main demo function"""
    print("🔍 Enhanced Vector Search with Chat History Context")
    print("Testing integration between vector search results and conversation history")
    print()
    
    # Check if API is available
    try:
        response = urllib.request.urlopen("http://localhost:8000/", timeout=5)
        if response.status == 200:
            print("✅ API is running")
        else:
            print("⚠️ API returned unexpected status")
    except:
        print("❌ API is not accessible at http://localhost:8000")
        print("Please start the API first: python startup.py local")
        return
    
    print()
    
    try:
        # Run main demonstration
        demonstrate_context_integration()
        
        # Show specific benefits
        demonstrate_context_benefits()
        
        print("🎉 Context Integration Demo Complete!")
        print()
        print("💡 Key Improvements:")
        print("   • Vector search results are enhanced with conversation context")
        print("   • LLM receives both document content AND chat history")
        print("   • Follow-up questions can reference previous answers")
        print("   • More natural conversation flow")
        print()
        print("📚 The search pipeline now uses:")
        print("   1. Vector similarity search (for relevant documents)")
        print("   2. Chat history context (for conversation continuity)")
        print("   3. Combined context (for comprehensive answers)")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    main()
