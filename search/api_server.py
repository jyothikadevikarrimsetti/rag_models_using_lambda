"""
FastAPI server for vector search with chat history using Redis.
Provides REST API endpoints for searching with conversation context and PDF upload processing.
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
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
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

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

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "s3-practice-ss")
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "injfunc")

# Global clients
redis_client = None
s3_client = None
lambda_client = None
logs_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    global redis_client, s3_client, lambda_client, logs_client
    
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
    
    # Initialize AWS clients
    try:
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        s3_client = session.client('s3')
        lambda_client = session.client('lambda')
        logs_client = session.client('logs')
        
        logger.info(f"AWS clients initialized for region: {AWS_REGION}")
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        s3_client = None
        lambda_client = None
        logs_client = None
    except Exception as e:
        logger.error(f"Failed to initialize AWS clients: {e}")
        s3_client = None
        lambda_client = None
        logs_client = None
    
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

# Create API router with prefix
from fastapi import APIRouter
api_router = APIRouter()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add a root redirect to /api/
@app.get("/")
async def redirect_to_api():
    """Redirect root to API health endpoint"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/")

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

# Upload API Models
class UploadResponse(BaseModel):
    success: bool
    s3_key: str
    s3_url: str
    file_size: int
    upload_time: datetime
    lambda_triggered: bool
    request_id: Optional[str] = None

class LambdaResponse(BaseModel):
    execution_id: str
    status: str
    response_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    logs_available: bool = False

class ProcessingStatus(BaseModel):
    request_id: str
    status: str  # "uploaded", "processing", "completed", "failed"
    s3_key: str
    upload_time: datetime
    lambda_execution: Optional[LambdaResponse] = None
    processing_results: Optional[Dict[str, Any]] = None

class AWSHealthResponse(BaseModel):
    status: str
    aws_connected: bool
    s3_accessible: bool
    lambda_accessible: bool
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

# Upload tracking storage (use Redis in production)
upload_tracking: Dict[str, ProcessingStatus] = {}

# Upload helper functions
def generate_s3_key(filename: str) -> str:
    """Generate a unique S3 key for the uploaded file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    clean_filename = filename.replace(" ", "_").replace("(", "").replace(")", "")
    return f"{timestamp}_{unique_id}_{clean_filename}"

def upload_to_s3(file_content: bytes, s3_key: str, content_type: str = "application/pdf") -> bool:
    """Upload file to S3"""
    try:
        if not s3_client:
            return False
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            Metadata={
                'uploaded_at': datetime.now().isoformat(),
                'upload_source': 'api'
            }
        )
        return True
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        return False

def trigger_lambda(s3_key: str) -> Optional[LambdaResponse]:
    """Trigger Lambda function for processing"""
    try:
        if not lambda_client:
            return None
            
        payload = {
            "Records": [{
                "s3": {
                    "bucket": {"name": S3_BUCKET_NAME},
                    "object": {"key": s3_key}
                }
            }]
        }
        
        start_time = time.time()
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        execution_time = int((time.time() - start_time) * 1000)
        
        response_payload = response.get('Payload')
        if response_payload:
            payload_data = json.loads(response_payload.read())
        else:
            payload_data = None
        
        return LambdaResponse(
            execution_id=response.get('ResponseMetadata', {}).get('RequestId', str(uuid.uuid4())),
            status="success" if response.get('StatusCode') == 200 else "error",
            response_payload=payload_data,
            execution_time_ms=execution_time,
            logs_available=True
        )
    except Exception as e:
        logger.error(f"Lambda trigger failed: {e}")
        return LambdaResponse(
            execution_id=str(uuid.uuid4()),
            status="error",
            error_message=str(e),
            logs_available=False
        )

async def process_upload_background(request_id: str, file_content: bytes, s3_key: str):
    """Background task to process upload and trigger Lambda"""
    try:
        # Update status to processing
        if request_id in upload_tracking:
            upload_tracking[request_id].status = "processing"
        
        # Upload to S3
        upload_success = upload_to_s3(file_content, s3_key)
        
        if not upload_success:
            upload_tracking[request_id].status = "failed"
            return
        
        # Trigger Lambda
        lambda_response = trigger_lambda(s3_key)
        
        # Update tracking with results
        if request_id in upload_tracking:
            upload_tracking[request_id].lambda_execution = lambda_response
            
            if lambda_response and lambda_response.status == "success":
                upload_tracking[request_id].status = "completed"
                upload_tracking[request_id].processing_results = lambda_response.response_payload
            else:
                upload_tracking[request_id].status = "failed"
        
        logger.info(f"Background processing completed for {request_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for {request_id}: {e}")
        if request_id in upload_tracking:
            upload_tracking[request_id].status = "failed"

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

@api_router.get("/", response_model=HealthResponse)
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

@api_router.post("/search", response_model=SearchResponse)
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

@api_router.get("/chat-history/{session_id}", response_model=ChatHistoryResponse)
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

@api_router.delete("/chat-history/{session_id}")
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

@api_router.get("/sessions")
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

@api_router.post("/search/similarity")
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

@api_router.get("/health/detailed")
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

# === Upload API Endpoints ===

@api_router.get("/aws-health", response_model=AWSHealthResponse)
async def aws_health_check():
    """AWS services health check endpoint"""
    aws_connected = s3_client is not None and lambda_client is not None
    s3_accessible = False
    lambda_accessible = False
    
    if aws_connected:
        try:
            # Test S3 access
            s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            s3_accessible = True
        except:
            pass
        
        try:
            # Test Lambda access
            lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
            lambda_accessible = True
        except:
            pass
    
    return AWSHealthResponse(
        status="healthy" if aws_connected else "degraded",
        aws_connected=aws_connected,
        s3_accessible=s3_accessible,
        lambda_accessible=lambda_accessible,
        timestamp=datetime.now()
    )

@api_router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    process_immediately: bool = True
):
    """Upload PDF to S3 and optionally trigger Lambda processing"""
    
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not s3_client or not lambda_client:
        raise HTTPException(status_code=503, detail="AWS services not available")
    
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")
        
        # Generate S3 key and request ID
        s3_key = generate_s3_key(file.filename)
        request_id = str(uuid.uuid4())
        upload_time = datetime.now()
        
        # Create tracking entry
        upload_tracking[request_id] = ProcessingStatus(
            request_id=request_id,
            status="uploaded",
            s3_key=s3_key,
            upload_time=upload_time
        )
        
        # Upload to S3 immediately
        upload_success = upload_to_s3(file_content, s3_key)
        
        if not upload_success:
            del upload_tracking[request_id]
            raise HTTPException(status_code=500, detail="Failed to upload to S3")
        
        # Generate S3 URL
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        
        lambda_triggered = False
        
        if process_immediately:
            # Add background task to trigger Lambda
            background_tasks.add_task(
                process_upload_background,
                request_id,
                file_content,
                s3_key
            )
            lambda_triggered = True
        
        return UploadResponse(
            success=True,
            s3_key=s3_key,
            s3_url=s3_url,
            file_size=file_size,
            upload_time=upload_time,
            lambda_triggered=lambda_triggered,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@api_router.post("/trigger-lambda/{request_id}")
async def trigger_lambda_for_upload(request_id: str):
    """Manually trigger Lambda processing for an uploaded file"""
    
    if request_id not in upload_tracking:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    tracking = upload_tracking[request_id]
    
    if tracking.status != "uploaded":
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot trigger Lambda, current status: {tracking.status}"
        )
    
    try:
        # Update status
        tracking.status = "processing"
        
        # Trigger Lambda
        lambda_response = trigger_lambda(tracking.s3_key)
        
        # Update tracking
        tracking.lambda_execution = lambda_response
        
        if lambda_response and lambda_response.status == "success":
            tracking.status = "completed"
            tracking.processing_results = lambda_response.response_payload
        else:
            tracking.status = "failed"
        
        return lambda_response
        
    except Exception as e:
        tracking.status = "failed"
        logger.error(f"Lambda trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Lambda trigger failed: {str(e)}")

@api_router.get("/status/{request_id}", response_model=ProcessingStatus)
async def get_processing_status(request_id: str):
    """Get processing status for a specific upload"""
    
    if request_id not in upload_tracking:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    return upload_tracking[request_id]

@api_router.get("/uploads")
async def list_recent_uploads(limit: int = 20):
    """List recent uploads"""
    
    # Sort by upload time, most recent first
    sorted_uploads = sorted(
        upload_tracking.values(),
        key=lambda x: x.upload_time,
        reverse=True
    )
    
    return {
        "total_uploads": len(sorted_uploads),
        "uploads": [
            {
                "request_id": upload.request_id,
                "s3_key": upload.s3_key,
                "status": upload.status,
                "upload_time": upload.upload_time,
                "has_results": upload.processing_results is not None
            }
            for upload in sorted_uploads[:limit]
        ]
    }

@api_router.get("/lambda-logs/{execution_id}")
async def get_lambda_logs(execution_id: str, lines: int = 50):
    """Get Lambda execution logs (if available)"""
    
    try:
        # Find the tracking entry with this execution ID
        tracking_entry = None
        for tracking in upload_tracking.values():
            if (tracking.lambda_execution and 
                tracking.lambda_execution.execution_id == execution_id):
                tracking_entry = tracking
                break
        
        if not tracking_entry:
            raise HTTPException(status_code=404, detail="Execution ID not found")
        
        # Try to get recent logs from Lambda function
        log_group = f"/aws/lambda/{LAMBDA_FUNCTION_NAME}"
        
        try:
            # Get recent log streams
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            if not streams_response['logStreams']:
                return {"logs": [], "message": "No log streams found"}
            
            # Get logs from the most recent stream
            latest_stream = streams_response['logStreams'][0]
            
            logs_response = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=latest_stream['logStreamName'],
                limit=lines,
                startFromHead=False
            )
            
            log_events = logs_response['events']
            
            return {
                "execution_id": execution_id,
                "log_stream": latest_stream['logStreamName'],
                "logs": [
                    {
                        "timestamp": datetime.fromtimestamp(event['timestamp'] / 1000),
                        "message": event['message'].strip()
                    }
                    for event in log_events
                ],
                "total_events": len(log_events)
            }
            
        except Exception as e:
            return {
                "execution_id": execution_id,
                "error": f"Could not fetch logs: {str(e)}",
                "logs": []
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@api_router.delete("/cleanup")
async def cleanup_old_uploads(days: int = 7):
    """Clean up upload tracking data older than specified days"""
    
    cutoff_time = datetime.now() - timedelta(days=days)
    
    old_request_ids = [
        request_id for request_id, tracking in upload_tracking.items()
        if tracking.upload_time < cutoff_time
    ]
    
    for request_id in old_request_ids:
        del upload_tracking[request_id]
    
    return {
        "cleaned_up": len(old_request_ids),
        "remaining": len(upload_tracking),
        "cutoff_date": cutoff_time
    }

@api_router.get("/s3-files")
async def list_s3_files(prefix: str = "uploads/", limit: int = 20):
    """List files in S3 bucket"""
    
    if not s3_client:
        raise HTTPException(status_code=503, detail="S3 not available")
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=limit
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'],
                    "url": f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{obj['Key']}"
                })
        
        return {
            "bucket": S3_BUCKET_NAME,
            "prefix": prefix,
            "files": files,
            "total": len(files)
        }
        
    except Exception as e:
        logger.error(f"Failed to list S3 files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list S3 files: {str(e)}")

# Include the API router with /api prefix
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
