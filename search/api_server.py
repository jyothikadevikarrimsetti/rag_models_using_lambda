"""
FastAPI server for vector search with chat history using Redis.
Provides REST API endpoints for searching with conversation context.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uvicorn
import redis
import json
import uuid
import time
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager

# Import our existing search functions
from search_pipeline import (
    mongodb_vector_search_new_structure,
    mongodb_vector_search,
    get_openai_embedding
)
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../injestion/config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB = int(os.getenv("REDIS_DB", 0))
CHAT_HISTORY_TTL = int(os.getenv("CHAT_HISTORY_TTL", 3600))  # 1 hour default

# Global Redis client
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    global redis_client
    
    # Startup
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        # Test connection
        redis_client.ping()
        logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        # Create a mock client for development
        redis_client = MockRedisClient()
    
    yield
    
    # Shutdown
    if hasattr(redis_client, 'close'):
        redis_client.close()

# Initialize FastAPI app
app = FastAPI(
    title="Vector Search API with Chat History",
    description="API for semantic search with conversation context using Redis",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=3, ge=1, le=20, description="Number of results to return")
    session_id: Optional[str] = Field(default=None, description="Chat session ID for context")
    use_new_structure: bool = Field(default=True, description="Use new data structure")

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)

class SearchResponse(BaseModel):
    answer: str
    results: List[Dict[str, Any]]
    count: int
    search_method: str
    session_id: str
    query_id: str
    response_time_ms: int

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]
    total_messages: int

class HealthResponse(BaseModel):
    status: str
    redis_connected: bool
    timestamp: datetime

# Mock Redis client for development/fallback
class MockRedisClient:
    """Mock Redis client when Redis is not available"""
    def __init__(self):
        self.data = {}
    
    def ping(self):
        return True
    
    def get(self, key):
        return self.data.get(key)
    
    def setex(self, key, time, value):
        self.data[key] = value
    
    def delete(self, key):
        return self.data.pop(key, None) is not None
    
    def keys(self, pattern):
        import fnmatch
        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]
    
    def close(self):
        pass

# Dependency to get Redis client
def get_redis_client():
    return redis_client

# Chat history management functions
def generate_session_id() -> str:
    """Generate a unique session ID"""
    return f"session_{uuid.uuid4().hex[:12]}_{int(time.time())}"

def get_chat_history(session_id: str, redis_client) -> List[ChatMessage]:
    """Retrieve chat history from Redis"""
    try:
        history_key = f"chat_history:{session_id}"
        history_json = redis_client.get(history_key)
        
        if history_json:
            history_data = json.loads(history_json)
            return [ChatMessage(**msg) for msg in history_data]
        return []
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return []

def save_chat_history(session_id: str, messages: List[ChatMessage], redis_client):
    """Save chat history to Redis"""
    try:
        history_key = f"chat_history:{session_id}"
        history_data = [msg.model_dump(mode='json') for msg in messages]
        
        redis_client.setex(
            history_key,
            CHAT_HISTORY_TTL,
            json.dumps(history_data, default=str)
        )
    except Exception as e:
        logger.error(f"Error saving chat history: {e}")

def add_message_to_history(session_id: str, message: ChatMessage, redis_client) -> List[ChatMessage]:
    """Add a message to chat history"""
    history = get_chat_history(session_id, redis_client)
    history.append(message)
    
    # Keep only last 50 messages to prevent memory issues
    if len(history) > 50:
        history = history[-50:]
    
    save_chat_history(session_id, history, redis_client)
    return history

def build_context_from_history(history: List[ChatMessage], current_query: str) -> str:
    """Build contextual query from chat history"""
    if not history:
        return current_query
    
    # Get last few messages for context
    recent_messages = history[-6:]  # Last 3 exchanges
    
    context_parts = []
    for msg in recent_messages:
        if msg.role == "user":
            context_parts.append(f"Previous question: {msg.content}")
        elif msg.role == "assistant":
            # Include just a summary of the assistant's response
            summary = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            context_parts.append(f"Previous answer: {summary}")
    
    if context_parts:
        context = " | ".join(context_parts)
        return f"Context: {context} | Current question: {current_query}"
    
    return current_query

# API Endpoints

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    redis_connected = True
    try:
        redis_client.ping()
    except:
        redis_connected = False
    
    return HealthResponse(
        status="healthy",
        redis_connected=redis_connected,
        timestamp=datetime.now()
    )

@app.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    redis_client=Depends(get_redis_client)
):
    """
    Search documents with optional chat history context
    """
    start_time = time.time()
    
    try:
        # Generate session ID if not provided
        session_id = request.session_id or generate_session_id()
        query_id = f"query_{uuid.uuid4().hex[:8]}"
        
        # Get chat history for context
        chat_history = get_chat_history(session_id, redis_client)
        
        # Convert chat history to the format expected by search functions
        chat_messages = []
        if chat_history:
            for msg in chat_history:
                chat_messages.append({
                    'role': msg.role,
                    'content': msg.content
                })
        
        # Build contextual query
        contextual_query = build_context_from_history(chat_history, request.query)
        
        logger.info(f"Session: {session_id}, Query: {request.query}")
        logger.info(f"Contextual query: {contextual_query}")
        logger.info(f"Chat history messages: {len(chat_messages)}")
        
        # Add user message to history
        user_message = ChatMessage(role="user", content=request.query)
        add_message_to_history(session_id, user_message, redis_client)
        
        # Perform search with chat history context
        if request.use_new_structure:
            result = mongodb_vector_search_new_structure(contextual_query, request.top_k, chat_messages)
        else:
            result = mongodb_vector_search(contextual_query, request.top_k, chat_messages)
        
        # Add assistant response to history
        assistant_message = ChatMessage(role="assistant", content=result["answer"])
        add_message_to_history(session_id, assistant_message, redis_client)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return SearchResponse(
            answer=result["answer"],
            results=result["results"],
            count=result["count"],
            search_method=result["search_method"],
            session_id=session_id,
            query_id=query_id,
            response_time_ms=response_time_ms
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat-history/{session_id}", response_model=ChatHistoryResponse)
async def get_session_history(
    session_id: str,
    redis_client=Depends(get_redis_client)
):
    """Get chat history for a specific session"""
    try:
        history = get_chat_history(session_id, redis_client)
        
        return ChatHistoryResponse(
            session_id=session_id,
            messages=history,
            total_messages=len(history)
        )
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat-history/{session_id}")
async def clear_session_history(
    session_id: str,
    redis_client=Depends(get_redis_client)
):
    """Clear chat history for a specific session"""
    try:
        history_key = f"chat_history:{session_id}"
        deleted = redis_client.delete(history_key)
        
        return {
            "session_id": session_id,
            "cleared": bool(deleted),
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
async def list_active_sessions(
    redis_client=Depends(get_redis_client)
):
    """List all active chat sessions"""
    try:
        pattern = "chat_history:*"
        session_keys = redis_client.keys(pattern)
        
        sessions = []
        for key in session_keys:
            session_id = key.replace("chat_history:", "")
            history = get_chat_history(session_id, redis_client)
            
            if history:
                sessions.append({
                    "session_id": session_id,
                    "message_count": len(history),
                    "last_activity": history[-1].timestamp if history else None
                })
        
        return {
            "active_sessions": len(sessions),
            "sessions": sessions
        }
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/similarity")
async def calculate_similarity(
    query1: str,
    query2: str
):
    """Calculate semantic similarity between two queries"""
    try:
        import numpy as np
        
        # Get embeddings for both queries
        embedding1 = get_openai_embedding(query1)
        embedding2 = get_openai_embedding(query2)
        
        # Calculate cosine similarity
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        cosine_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        return {
            "query1": query1,
            "query2": query2,
            "cosine_similarity": float(cosine_sim),
            "similarity_percentage": f"{cosine_sim * 100:.2f}%"
        }
        
    except Exception as e:
        logger.error(f"Similarity calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health/detailed")
async def detailed_health_check(
    redis_client=Depends(get_redis_client)
):
    """Detailed health check including all system components"""
    health_status = {
        "timestamp": datetime.now(),
        "api_status": "healthy",
        "components": {}
    }
    
    # Check Redis
    try:
        redis_client.ping()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "host": REDIS_HOST,
            "port": REDIS_PORT
        }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check MongoDB (via search function)
    try:
        # Test with a simple search
        test_result = mongodb_vector_search_new_structure("test", 1)
        health_status["components"]["mongodb"] = {
            "status": "healthy",
            "search_method": test_result.get("search_method", "unknown")
        }
    except Exception as e:
        health_status["components"]["mongodb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check OpenAI
    try:
        test_embedding = get_openai_embedding("test")
        health_status["components"]["openai"] = {
            "status": "healthy",
            "embedding_dimensions": len(test_embedding)
        }
    except Exception as e:
        health_status["components"]["openai"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return health_status

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
