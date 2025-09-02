# Unified Search & Upload API

A comprehensive FastAPI server that provides vector search with chat history using Redis and PDF upload functionality with AWS Lambda processing.

## Features

### 🔍 Vector Search with Chat History
- **MongoDB Vector Search**: Advanced vector search using MongoDB Atlas
- **Chat History**: Persistent conversation context using Redis
- **Context-Aware Responses**: LLM responses use both retrieved documents and chat history
- **Session Management**: Track and manage multiple chat sessions

### 📤 PDF Upload & Processing
- **S3 Upload**: Direct PDF upload to AWS S3
- **Lambda Integration**: Automatic triggering of AWS Lambda for PDF processing
- **Status Monitoring**: Real-time tracking of upload and processing status
- **Log Access**: View Lambda execution logs
- **File Management**: List and manage uploaded files

## Quick Start

### 1. Environment Setup

Create a `.env` file in the `config/` directory:

```env
# MongoDB Atlas
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database
MONGODB_DATABASE=your_database
MONGODB_COLLECTION=your_collection

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_ENDPOINT=https://your-azure-openai.openai.azure.com/
OPENAI_API_VERSION=2024-02-15-preview
OPENAI_DEPLOYMENT_NAME=your_deployment

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-s3-bucket
LAMBDA_FUNCTION_NAME=your-lambda-function
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Server

```bash
python api_server.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Search & Chat Endpoints

#### POST `/search`
Perform vector search with chat history context.

**Request:**
```json
{
    "query": "What is machine learning?",
    "session_id": "optional_session_id",
    "top_k": 5,
    "use_chat_history": true
}
```

**Response:**
```json
{
    "answer": "Machine learning is...",
    "documents": [...],
    "session_id": "session_123",
    "chat_context": [...],
    "search_metadata": {...}
}
```

#### GET `/chat-history/{session_id}`
Retrieve chat history for a session.

#### GET `/sessions`
List all active sessions.

#### DELETE `/clear-history/{session_id}`
Clear chat history for a session.

### Upload & Processing Endpoints

#### POST `/upload`
Upload a PDF file to S3 and optionally trigger Lambda processing.

**Parameters:**
- `file`: PDF file (multipart/form-data)
- `process_immediately`: Boolean (default: true)

**Response:**
```json
{
    "success": true,
    "s3_key": "uploads/20240101_123456_document.pdf",
    "s3_url": "https://bucket.s3.region.amazonaws.com/...",
    "file_size": 1048576,
    "upload_time": "2024-01-01T12:34:56",
    "lambda_triggered": true,
    "request_id": "uuid-here"
}
```

#### GET `/status/{request_id}`
Get processing status for an uploaded file.

**Response:**
```json
{
    "request_id": "uuid-here",
    "status": "completed",
    "s3_key": "uploads/...",
    "upload_time": "2024-01-01T12:34:56",
    "lambda_execution": {
        "execution_id": "exec_123",
        "status": "success",
        "response_payload": {...},
        "execution_time_ms": 5000
    },
    "processing_results": {...}
}
```

#### POST `/trigger-lambda/{request_id}`
Manually trigger Lambda processing for an uploaded file.

#### GET `/uploads`
List recent uploads with their status.

#### GET `/lambda-logs/{execution_id}`
Get Lambda execution logs.

#### GET `/s3-files`
List files in the S3 bucket.

#### DELETE `/cleanup`
Clean up old upload tracking data.

### Health & Monitoring

#### GET `/`
Basic health check.

#### GET `/aws-health`
AWS services health check.

#### GET `/health/detailed`
Comprehensive health check including all services.

## Usage Examples

### Search with Chat History

```python
import requests

# Start a conversation
response = requests.post("http://localhost:8000/search", json={
    "query": "What is artificial intelligence?",
    "session_id": "my_session"
})

# Continue the conversation
response = requests.post("http://localhost:8000/search", json={
    "query": "How is it different from machine learning?",
    "session_id": "my_session"  # Same session for context
})
```

### Upload and Process PDF

```python
import requests

# Upload PDF
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": f},
        params={"process_immediately": True}
    )

upload_result = response.json()
request_id = upload_result["request_id"]

# Check processing status
status_response = requests.get(f"http://localhost:8000/status/{request_id}")
status = status_response.json()

print(f"Status: {status['status']}")
```

## Docker Deployment

Build and run with Docker:

```bash
# Build the image
docker build -t search-upload-api .

# Run the container
docker run -p 8000:8000 --env-file config/.env search-upload-api
```

## Demo Scripts

### `demo_upload.py`
Comprehensive demo showing upload functionality:
```bash
python demo_upload.py
```

### `demo_simple.py`
Basic search functionality demo:
```bash
python demo_simple.py
```

### `client_example.py`
Interactive client for testing search with chat history:
```bash
python client_example.py
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│   Redis Cache   │────│  MongoDB Atlas  │
│                 │    │  (Chat History) │    │ (Vector Search) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ├─────────────────────────────────────────────────────────┐
         │                                                         │
         v                                                         v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AWS S3        │────│  AWS Lambda     │────│   CloudWatch    │
│ (PDF Storage)   │    │ (Processing)    │    │    (Logs)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Features in Detail

### Context-Aware Search
The search pipeline combines:
1. **Vector Search Results**: Retrieved documents from MongoDB
2. **Chat History**: Previous conversation context from Redis
3. **LLM Processing**: Azure OpenAI generates contextual responses

### Upload Processing Pipeline
1. **File Validation**: PDF format and size checks
2. **S3 Upload**: Secure upload with metadata
3. **Lambda Trigger**: Automatic or manual processing trigger
4. **Status Tracking**: Real-time processing status updates
5. **Result Storage**: Processing results stored and retrievable

### Error Handling
- Graceful fallbacks for service unavailability
- Comprehensive error messages
- Health check endpoints for monitoring
- Automatic retry mechanisms

## Monitoring

### Health Checks
- `/`: Basic API health
- `/aws-health`: AWS services connectivity
- `/health/detailed`: Comprehensive service health

### Logging
- Structured logging with timestamps
- Service-specific log levels
- Lambda execution logs accessible via API

## Security

- File type validation (PDF only)
- File size limits (50MB)
- AWS IAM-based access control
- Environment variable configuration
- CORS protection

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check Redis server status
   - Verify connection parameters
   - API falls back to mock client

2. **AWS Services Unavailable**
   - Verify AWS credentials
   - Check IAM permissions
   - Confirm S3 bucket exists

3. **MongoDB Connection Issues**
   - Verify MongoDB URI
   - Check network connectivity
   - Confirm collection exists

4. **Lambda Processing Fails**
   - Check Lambda function exists
   - Verify IAM permissions
   - Review Lambda logs

### Debug Mode

Run with debug logging:
```bash
export LOG_LEVEL=DEBUG
python api_server.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.