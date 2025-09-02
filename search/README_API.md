# Vector Search API with Chat History

A FastAPI-based REST API for semantic document search with conversation context using Redis for chat history management.

## Features

- 🔍 **Vector Search**: Semantic search using Azure OpenAI embeddings
- 💬 **Chat History**: Conversation context maintained in Redis
- 🔄 **Session Management**: Multiple concurrent chat sessions
- 📊 **Similarity Analysis**: Calculate semantic similarity between queries
- 🏥 **Health Monitoring**: Comprehensive health checks for all components
- 🐳 **Docker Support**: Ready-to-deploy containerized setup
- 🧪 **Testing Suite**: Comprehensive API testing framework

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │      Redis      │    │    MongoDB      │
│                 │    │                 │    │                 │
│ • Search API    │◄──►│ • Chat History  │    │ • Vector Store  │
│ • Session Mgmt  │    │ • Session Cache │    │ • Documents     │
│ • Health Check  │    │ • TTL Support   │    │ • Embeddings    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Azure OpenAI   │
                    │                 │
                    │ • Embeddings    │
                    │ • Completions   │
                    │ • Chat Context  │
                    └─────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Install API dependencies
pip install -r requirements.api.txt

# Or use the startup script
python startup.py install
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# - Redis connection details
# - Azure OpenAI credentials (inherited from ../injestion/config/.env)
# - MongoDB connection (inherited from ../injestion/config/.env)
```

### 3. Start Redis

```bash
# Option 1: Docker
docker run -d -p 6379:6379 redis:7-alpine

# Option 2: Local installation
redis-server

# Option 3: Docker Compose (includes API)
docker-compose up redis
```

### 4. Run the API

```bash
# Option 1: Local development
python startup.py local

# Option 2: Docker Compose (full stack)
python startup.py docker

# Option 3: Direct uvicorn
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Test the API

```bash
# Run comprehensive tests
python startup.py test

# Or test specific functionality
python test_api.py
```

## API Endpoints

### Search Endpoints

#### `POST /search`
Perform semantic search with optional chat history context.

**Request:**
```json
{
  "query": "What is the education background?",
  "top_k": 3,
  "session_id": "session_abc123_1234567890",
  "use_new_structure": true
}
```

**Response:**
```json
{
  "answer": "Based on the documents, the education background includes...",
  "results": [
    {
      "chunk_text": "Education content...",
      "filename": "document.pdf",
      "score": 0.85,
      "chunk_id": 1
    }
  ],
  "count": 3,
  "search_method": "new_structure",
  "session_id": "session_abc123_1234567890",
  "query_id": "query_def456",
  "response_time_ms": 1250
}
```

#### `POST /search/similarity`
Calculate semantic similarity between two queries.

**Parameters:**
- `query1`: First query text
- `query2`: Second query text

**Response:**
```json
{
  "query1": "What is education background?",
  "query2": "Tell me about educational qualifications",
  "cosine_similarity": 0.8234,
  "similarity_percentage": "82.34%"
}
```

### Chat History Endpoints

#### `GET /chat-history/{session_id}`
Retrieve chat history for a session.

**Response:**
```json
{
  "session_id": "session_abc123_1234567890",
  "messages": [
    {
      "role": "user",
      "content": "What is the education background?",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "role": "assistant", 
      "content": "The education background includes...",
      "timestamp": "2024-01-15T10:30:02Z"
    }
  ],
  "total_messages": 2
}
```

#### `DELETE /chat-history/{session_id}`
Clear chat history for a session.

**Response:**
```json
{
  "session_id": "session_abc123_1234567890",
  "cleared": true,
  "timestamp": "2024-01-15T10:35:00Z"
}
```

### Session Management

#### `GET /sessions`
List all active chat sessions.

**Response:**
```json
{
  "active_sessions": 3,
  "sessions": [
    {
      "session_id": "session_abc123_1234567890",
      "message_count": 6,
      "last_activity": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Health Check Endpoints

#### `GET /`
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "redis_connected": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### `GET /health/detailed`
Detailed health check of all components.

**Response:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "api_status": "healthy",
  "components": {
    "redis": {
      "status": "healthy",
      "host": "localhost",
      "port": 6379
    },
    "mongodb": {
      "status": "healthy",
      "search_method": "new_structure"
    },
    "openai": {
      "status": "healthy",
      "embedding_dimensions": 1536
    }
  }
}
```

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
CHAT_HISTORY_TTL=3600

# Search Configuration
USE_NEW_DATA_STRUCTURE=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=info

# Session Configuration
MAX_CHAT_HISTORY_MESSAGES=50
DEFAULT_TOP_K=3
MAX_TOP_K=20
```

### Chat History TTL

Chat history is automatically expired after `CHAT_HISTORY_TTL` seconds (default: 1 hour).
Adjust this value based on your requirements:

- **Short sessions**: 600 (10 minutes)
- **Standard sessions**: 3600 (1 hour)
- **Long sessions**: 86400 (24 hours)

## Usage Examples

### Python Client

```python
from api_client import VectorSearchClient

# Initialize client
client = VectorSearchClient("http://localhost:8000")

# Perform searches with automatic session management
result1 = client.search("What is the education background?")
result2 = client.search("What about work experience?")  # Uses same session

# Get chat history
history = client.get_chat_history()
print(f"Session has {history['total_messages']} messages")

# Calculate similarity
similarity = client.calculate_similarity(
    "education background",
    "academic qualifications"
)
print(f"Similarity: {similarity['similarity_percentage']}")
```

### cURL Examples

```bash
# Search without session
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the education background?",
    "top_k": 3
  }'

# Search with session
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What about work experience?",
    "session_id": "session_abc123_1234567890"
  }'

# Get chat history
curl "http://localhost:8000/chat-history/session_abc123_1234567890"

# Health check
curl "http://localhost:8000/"
```

### JavaScript/Fetch

```javascript
// Search with fetch
const searchResponse = await fetch('http://localhost:8000/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'What is the education background?',
    top_k: 3
  })
});

const searchResult = await searchResponse.json();
console.log('Answer:', searchResult.answer);

// Get chat history
const historyResponse = await fetch(`http://localhost:8000/chat-history/${searchResult.session_id}`);
const history = await historyResponse.json();
console.log('Messages:', history.total_messages);
```

## Docker Deployment

### Development

```bash
# Start full stack
docker-compose up --build

# Start only Redis
docker-compose up redis

# View logs
docker-compose logs -f api
```

### Production

```bash
# Build production image
docker build -f Dockerfile.api -t vector-search-api .

# Run with external Redis
docker run -d \
  -p 8000:8000 \
  -e REDIS_HOST=your-redis-host \
  -e REDIS_PASSWORD=your-redis-password \
  vector-search-api
```

## Testing

### Automated Tests

```bash
# Run all tests
python startup.py test

# Run with custom API URL
python test_api.py --url http://your-api-host:8000

# Run with delay (useful for Docker startup)
python test_api.py --wait 10
```

### Manual Testing

1. **Health Check**: Visit `http://localhost:8000/`
2. **API Docs**: Visit `http://localhost:8000/docs`
3. **Interactive Testing**: Use the Swagger UI at `/docs`

### Test Coverage

The test suite covers:
- ✅ Health checks (basic and detailed)
- ✅ Search functionality (with/without history)
- ✅ Chat history management
- ✅ Session management
- ✅ Similarity calculations
- ✅ Conversation flows
- ✅ Error handling
- ✅ Input validation

## Chat History Features

### Context Building

The API automatically builds context from previous messages:

```python
# User asks: "What is the education background?"
# Assistant responds with education details

# User asks: "What about work experience?"
# Context: "Previous question: What is the education background? | Previous answer: The education background includes... | Current question: What about work experience?"
```

### Session Management

- **Automatic Session Creation**: New sessions created automatically
- **Session Persistence**: Sessions stored in Redis with TTL
- **Multiple Sessions**: Support for concurrent user sessions
- **Session Cleanup**: Automatic expiration and manual clearing

### Message Limits

- **Per Session**: Max 50 messages (configurable)
- **Context Window**: Last 6 messages used for context
- **Automatic Pruning**: Older messages removed when limit exceeded

## Performance Considerations

### Response Times

- **Search**: 500-2000ms (depending on query complexity)
- **Chat History**: 10-50ms (Redis lookup)
- **Similarity**: 200-500ms (OpenAI embedding generation)

### Scaling

- **Horizontal**: Multiple API instances with shared Redis
- **Redis**: Use Redis Cluster for high availability
- **MongoDB**: Leverage Atlas vector search scaling
- **Caching**: Consider response caching for frequent queries

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Start Redis
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **OpenAI API Errors**
   ```bash
   # Check environment variables
   echo $AZURE_OPENAI_API_KEY
   echo $AZURE_OPENAI_ENDPOINT
   ```

3. **MongoDB Connection Issues**
   ```bash
   # Verify MongoDB connection from search pipeline
   python -c "from search_pipeline import mongodb_vector_search_new_structure; print('MongoDB OK')"
   ```

4. **Dependency Issues**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.api.txt --force-reinstall
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Use the detailed health check to diagnose issues:

```bash
curl http://localhost:8000/health/detailed
```

## Development

### Code Structure

```
search/
├── api_server.py          # Main FastAPI application
├── api_client.py          # Python client example
├── test_api.py           # Comprehensive test suite
├── startup.py            # Development utilities
├── docker-compose.yml    # Docker setup
├── Dockerfile.api        # API container
├── requirements.api.txt  # API dependencies
├── .env.example         # Environment template
└── README_API.md        # This documentation
```

### Adding New Endpoints

1. Add endpoint to `api_server.py`
2. Add corresponding tests to `test_api.py`
3. Update client examples in `api_client.py`
4. Update documentation

### Contributing

1. Follow FastAPI best practices
2. Add comprehensive tests for new features
3. Update documentation
4. Ensure Docker compatibility

## API Interactive Documentation

When the API is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These provide interactive API exploration and testing capabilities.
