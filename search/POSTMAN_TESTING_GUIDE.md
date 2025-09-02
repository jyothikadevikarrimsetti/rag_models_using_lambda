# Postman Testing Guide for Unified Search & Upload API

This guide provides step-by-step instructions for testing the unified API using Postman.

## 🚀 Getting Started

### 1. Base URL Configuration
- **Base URL**: `http://localhost:8000`
- Create a Postman Environment with this variable for easy switching

### 2. Server Status Check
First, ensure your server is running by testing the health endpoint.

## 📋 Postman Collection Setup

### Environment Variables
Create a Postman environment with these variables:
```
BASE_URL = http://localhost:8000
SESSION_ID = test_session_{{$timestamp}}
REQUEST_ID = (will be set from upload response)
```

## 🔍 Testing Search & Chat Endpoints

### 1. Basic Health Check
**GET** `{{BASE_URL}}/`

**Expected Response:**
```json
{
    "status": "healthy",
    "redis_connected": true,
    "timestamp": "2025-09-02T12:00:00"
}
```

### 2. Detailed Health Check
**GET** `{{BASE_URL}}/health/detailed`

**Expected Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-09-02T12:00:00",
    "components": {
        "redis": {"status": "healthy"},
        "mongodb": {"status": "healthy"},
        "openai": {"status": "healthy"}
    }
}
```

### 3. Vector Search (Basic)
**POST** `{{BASE_URL}}/search`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
    "query": "What is machine learning?",
    "top_k": 5
}
```

**Expected Response:**
```json
{
    "answer": "Machine learning is a method of data analysis...",
    "documents": [
        {
            "content": "Document content...",
            "metadata": {},
            "score": 0.95
        }
    ],
    "session_id": "auto_generated_id",
    "chat_context": [],
    "search_metadata": {
        "search_method": "vector_search",
        "query_embedding_time_ms": 150,
        "total_documents_found": 5
    }
}
```

### 4. Search with Chat History
**POST** `{{BASE_URL}}/search`

**Body (JSON):**
```json
{
    "query": "What is machine learning?",
    "session_id": "{{SESSION_ID}}",
    "top_k": 3,
    "use_chat_history": true
}
```

**Follow-up Search:**
```json
{
    "query": "How is it different from deep learning?",
    "session_id": "{{SESSION_ID}}",
    "top_k": 3,
    "use_chat_history": true
}
```

### 5. Get Chat History
**GET** `{{BASE_URL}}/chat-history/{{SESSION_ID}}`

**Expected Response:**
```json
{
    "session_id": "test_session_123",
    "messages": [
        {
            "role": "user",
            "content": "What is machine learning?",
            "timestamp": "2025-09-02T12:00:00"
        },
        {
            "role": "assistant",
            "content": "Machine learning is...",
            "timestamp": "2025-09-02T12:00:01"
        }
    ],
    "total_messages": 2
}
```

### 6. List All Sessions
**GET** `{{BASE_URL}}/sessions`

### 7. Clear Session History
**DELETE** `{{BASE_URL}}/clear-history/{{SESSION_ID}}`

## 📤 Testing Upload & AWS Endpoints

### 1. AWS Health Check
**GET** `{{BASE_URL}}/aws-health`

**Expected Response:**
```json
{
    "status": "healthy",
    "aws_connected": true,
    "s3_accessible": true,
    "lambda_accessible": true,
    "timestamp": "2025-09-02T12:00:00"
}
```

### 2. Upload PDF File
**POST** `{{BASE_URL}}/upload?process_immediately=true`

**Headers:**
```
Content-Type: multipart/form-data
```

**Body (form-data):**
- Key: `file`
- Type: File
- Value: Select a PDF file

**Expected Response:**
```json
{
    "success": true,
    "s3_key": "uploads/20250902_120000_abcd1234_document.pdf",
    "s3_url": "https://your-bucket.s3.ap-south-1.amazonaws.com/uploads/...",
    "file_size": 1048576,
    "upload_time": "2025-09-02T12:00:00",
    "lambda_triggered": true,
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Post-response Script** (to save request_id):
```javascript
if (pm.response.json() && pm.response.json().request_id) {
    pm.environment.set("REQUEST_ID", pm.response.json().request_id);
}
```

### 3. Check Upload Status
**GET** `{{BASE_URL}}/status/{{REQUEST_ID}}`

**Expected Response:**
```json
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "s3_key": "uploads/20250902_120000_abcd1234_document.pdf",
    "upload_time": "2025-09-02T12:00:00",
    "lambda_execution": {
        "execution_id": "exec_12345",
        "status": "success",
        "response_payload": {
            "message": "Processing completed successfully"
        },
        "execution_time_ms": 5000,
        "logs_available": true
    },
    "processing_results": {
        "documents_processed": 10,
        "pages_extracted": 25
    }
}
```

### 4. Manually Trigger Lambda
**POST** `{{BASE_URL}}/trigger-lambda/{{REQUEST_ID}}`

### 5. Get Lambda Logs
**GET** `{{BASE_URL}}/lambda-logs/exec_12345?lines=50`

### 6. List Recent Uploads
**GET** `{{BASE_URL}}/uploads?limit=10`

**Expected Response:**
```json
{
    "total_uploads": 3,
    "uploads": [
        {
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "s3_key": "uploads/20250902_120000_abcd1234_document.pdf",
            "status": "completed",
            "upload_time": "2025-09-02T12:00:00",
            "has_results": true
        }
    ]
}
```

### 7. List S3 Files
**GET** `{{BASE_URL}}/s3-files?prefix=uploads/&limit=20`

### 8. Cleanup Old Data
**DELETE** `{{BASE_URL}}/cleanup?days=7`

## 🧪 Test Scenarios

### Scenario 1: Complete Search Conversation
1. **POST** `/search` - Ask initial question
2. **POST** `/search` - Ask follow-up question (same session_id)
3. **GET** `/chat-history/{session_id}` - View conversation
4. **GET** `/sessions` - See all sessions

### Scenario 2: File Upload & Processing
1. **GET** `/aws-health` - Check AWS connectivity
2. **POST** `/upload` - Upload a PDF
3. **GET** `/status/{request_id}` - Check processing status
4. **GET** `/uploads` - List all uploads

### Scenario 3: Error Handling
1. **POST** `/upload` with non-PDF file (should fail)
2. **GET** `/status/invalid-id` (should return 404)
3. **POST** `/search` with empty query (should handle gracefully)

## 📁 Sample Postman Collection JSON

Here's a basic collection you can import:

```json
{
    "info": {
        "name": "Unified Search & Upload API",
        "description": "Test collection for the unified API"
    },
    "item": [
        {
            "name": "Health Checks",
            "item": [
                {
                    "name": "Basic Health",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{BASE_URL}}/",
                            "host": ["{{BASE_URL}}"],
                            "path": [""]
                        }
                    }
                },
                {
                    "name": "AWS Health",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{BASE_URL}}/aws-health",
                            "host": ["{{BASE_URL}}"],
                            "path": ["aws-health"]
                        }
                    }
                }
            ]
        },
        {
            "name": "Search & Chat",
            "item": [
                {
                    "name": "Vector Search",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n    \"query\": \"What is machine learning?\",\n    \"session_id\": \"{{SESSION_ID}}\",\n    \"top_k\": 5\n}"
                        },
                        "url": {
                            "raw": "{{BASE_URL}}/search",
                            "host": ["{{BASE_URL}}"],
                            "path": ["search"]
                        }
                    }
                }
            ]
        },
        {
            "name": "Upload & Processing",
            "item": [
                {
                    "name": "Upload PDF",
                    "request": {
                        "method": "POST",
                        "header": [],
                        "body": {
                            "mode": "formdata",
                            "formdata": [
                                {
                                    "key": "file",
                                    "type": "file",
                                    "src": []
                                }
                            ]
                        },
                        "url": {
                            "raw": "{{BASE_URL}}/upload?process_immediately=true",
                            "host": ["{{BASE_URL}}"],
                            "path": ["upload"],
                            "query": [
                                {
                                    "key": "process_immediately",
                                    "value": "true"
                                }
                            ]
                        }
                    }
                }
            ]
        }
    ]
}
```

## 🔧 Troubleshooting

### Common Issues:

1. **Connection Refused**: Server not running
   - Check if `uvicorn api_server:app --host 0.0.0.0 --port 8000` is running

2. **500 Internal Server Error**: Check server logs for specific errors

3. **Redis Connection Failed**: Redis mock client will be used automatically

4. **AWS Services Unavailable**: Upload endpoints will return 503 status

5. **MongoDB Connection Issues**: Search will return error messages

### Debug Tips:

1. **Check Server Logs**: Look at the terminal running uvicorn
2. **Test Health Endpoints**: Start with `/` and `/health/detailed`
3. **Use Small Files**: For upload testing, use small PDF files first
4. **Check Environment**: Ensure `.env` file is properly configured

## 🎯 Quick Start Checklist

- [ ] Server is running on port 8000
- [ ] Postman environment created with BASE_URL
- [ ] Basic health check passes
- [ ] Search endpoint responds (even if with errors)
- [ ] AWS health check shows service status
- [ ] Upload endpoint accepts files (if AWS configured)

Happy testing! 🚀
