# Quick Postman Testing Steps

## 🚀 Quick Start (5 minutes)

### 1. Import into Postman
1. Open Postman
2. Click **Import** button
3. Drag and drop these files:
   - `Unified_API_Postman_Collection.json`
   - `Unified_API_Environment.postman_environment.json`
4. Select the "Unified API Environment" in the top-right dropdown

### 2. Ensure Server is Running
```bash
cd "C:\New folder (5)\lambda\search"
uvicorn api_server:app --host 0.0.0.0 --port 8000
```
✅ Server should be running on http://localhost:8000
✅ API endpoints available at http://localhost:8000/api/

### 3. Test Basic Functionality (in order)

#### A. Health Checks 🔍
1. **Basic Health Check** - Should return status "healthy"
2. **AWS Health Check** - Shows AWS service availability
3. **Detailed Health Check** - Complete system status

#### B. Search & Chat 🗣️
1. **Basic Vector Search** - Try: "What is machine learning?"
2. **Search with Chat History** - Creates a session
3. **Follow-up Question** - Uses same session for context
4. **Get Chat History** - See the conversation
5. **List All Sessions** - View active sessions

#### C. Upload & Processing 📤
1. **Upload PDF (with processing)** - Upload any PDF file
2. **Check Upload Status** - See processing status
3. **List Recent Uploads** - View all uploads

## 🎯 Expected Results

### ✅ Health Check Response
```json
{
    "status": "healthy",
    "redis_connected": true,
    "timestamp": "2025-09-02T12:00:00"
}
```

### ✅ Search Response
```json
{
    "answer": "Machine learning is a method...",
    "documents": [...],
    "session_id": "auto_generated_id",
    "search_metadata": {...}
}
```

### ✅ Upload Response
```json
{
    "success": true,
    "s3_key": "uploads/20250902_120000_document.pdf",
    "request_id": "uuid-here",
    "lambda_triggered": true
}
```

## 🔧 Troubleshooting

### If Health Check Fails:
- Check if server is running on port 8000
- Look for errors in the server terminal

### If Search Fails:
- MongoDB connection might be down
- Check the detailed health endpoint

### If Upload Fails:
- AWS credentials might not be configured
- Check aws-health endpoint first

## 📋 Test Scenarios to Try

### Scenario 1: Complete Conversation
1. Ask: "What is artificial intelligence?"
2. Follow up: "How does it work?"
3. Follow up: "What are its applications?"
4. Check chat history

### Scenario 2: File Processing Workflow
1. Upload a PDF with `process_immediately=true`
2. Check status immediately
3. Check status again after 30 seconds
4. View the upload list

### Scenario 3: Error Handling
1. Try uploading a .txt file (should fail)
2. Try getting status with invalid ID (should 404)
3. Try empty search query (should handle gracefully)

## 📊 Status Codes to Expect

- **200**: Success
- **400**: Bad request (invalid file type, empty query, etc.)
- **404**: Not found (invalid request ID, session not found)
- **422**: Validation error (missing required fields)
- **500**: Server error (database issues, etc.)
- **503**: Service unavailable (AWS not configured)

## 🔍 What to Look For

### In Responses:
- ✅ Proper JSON formatting
- ✅ Expected fields present
- ✅ Reasonable response times
- ✅ Appropriate error messages

### In Server Logs:
- ✅ No error stack traces
- ✅ Successful database connections
- ✅ AWS service status messages

## 🎉 Success Indicators

If you can successfully:
1. ✅ Get healthy status from all health checks
2. ✅ Perform a search and get results
3. ✅ Create and view chat history
4. ✅ Upload a file (even if AWS fails, should handle gracefully)
5. ✅ List sessions and uploads

**Then your unified API is working perfectly! 🚀**

Happy testing!
