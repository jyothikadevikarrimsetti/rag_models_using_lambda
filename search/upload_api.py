"""
S3 Upload and Lambda Trigger API
Provides endpoints to upload PDFs to S3 and monitor Lambda execution
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import boto3
import json
import uuid
import time
from datetime import datetime, timedelta
import logging
import asyncio
from botocore.exceptions import ClientError, NoCredentialsError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../injestion/config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "s3-practice-ss")
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "injestion")

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

# FastAPI app
app = FastAPI(
    title="PDF Upload & Processing API",
    description="Upload PDFs to S3 and monitor Lambda processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
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

class HealthResponse(BaseModel):
    status: str
    aws_connected: bool
    s3_accessible: bool
    lambda_accessible: bool
    timestamp: datetime

# In-memory storage for tracking uploads (use Redis in production)
upload_tracking: Dict[str, ProcessingStatus] = {}

# Helper functions
def generate_s3_key(filename: str) -> str:
    """Generate a unique S3 key for the uploaded file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    clean_filename = filename.replace(" ", "_").replace("(", "").replace(")", "")
    return f"uploads/{timestamp}_{unique_id}_{clean_filename}"

def upload_to_s3(file_content: bytes, s3_key: str, content_type: str = "application/pdf") -> bool:
    """Upload file to S3"""
    try:
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
        logger.info(f"Successfully uploaded {s3_key} to S3")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {s3_key} to S3: {e}")
        return False

def trigger_lambda_function(s3_key: str) -> LambdaResponse:
    """Trigger Lambda function with S3 event"""
    try:
        # Create S3 event payload
        event_payload = {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {
                            "name": S3_BUCKET_NAME
                        },
                        "object": {
                            "key": s3_key
                        }
                    }
                }
            ]
        }
        
        start_time = time.time()
        
        # Invoke Lambda function
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',  # Synchronous execution
            Payload=json.dumps(event_payload)
        )
        
        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)
        
        # Parse response
        payload = json.loads(response['Payload'].read())
        
        execution_id = str(uuid.uuid4())[:12]
        
        if response['StatusCode'] == 200:
            return LambdaResponse(
                execution_id=execution_id,
                status="success",
                response_payload=payload,
                execution_time_ms=execution_time_ms,
                logs_available=True
            )
        else:
            return LambdaResponse(
                execution_id=execution_id,
                status="error",
                error_message=f"Lambda returned status {response['StatusCode']}",
                execution_time_ms=execution_time_ms
            )
            
    except Exception as e:
        logger.error(f"Failed to trigger Lambda function: {e}")
        return LambdaResponse(
            execution_id=str(uuid.uuid4())[:12],
            status="error",
            error_message=str(e)
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
        lambda_response = trigger_lambda_function(s3_key)
        
        # Update tracking with results
        if request_id in upload_tracking:
            upload_tracking[request_id].lambda_execution = lambda_response
            
            if lambda_response.status == "success":
                upload_tracking[request_id].status = "completed"
                upload_tracking[request_id].processing_results = lambda_response.response_payload
            else:
                upload_tracking[request_id].status = "failed"
        
        logger.info(f"Background processing completed for {request_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for {request_id}: {e}")
        if request_id in upload_tracking:
            upload_tracking[request_id].status = "failed"

# API Endpoints

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
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
    
    return HealthResponse(
        status="healthy" if aws_connected else "degraded",
        aws_connected=aws_connected,
        s3_accessible=s3_accessible,
        lambda_accessible=lambda_accessible,
        timestamp=datetime.now()
    )

@app.post("/upload", response_model=UploadResponse)
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

@app.post("/trigger-lambda/{request_id}")
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
        lambda_response = trigger_lambda_function(tracking.s3_key)
        
        # Update tracking
        tracking.lambda_execution = lambda_response
        
        if lambda_response.status == "success":
            tracking.status = "completed"
            tracking.processing_results = lambda_response.response_payload
        else:
            tracking.status = "failed"
        
        return lambda_response
        
    except Exception as e:
        tracking.status = "failed"
        logger.error(f"Lambda trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Lambda trigger failed: {str(e)}")

@app.get("/status/{request_id}", response_model=ProcessingStatus)
async def get_processing_status(request_id: str):
    """Get processing status for a specific upload"""
    
    if request_id not in upload_tracking:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    return upload_tracking[request_id]

@app.get("/uploads")
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

@app.get("/lambda-logs/{execution_id}")
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

@app.delete("/cleanup")
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

@app.get("/s3-files")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "upload_api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
