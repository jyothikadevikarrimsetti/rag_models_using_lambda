# Vector Search API with Redis Chat History - Quick Start

## 🚀 What's Been Created

I've created a complete **FastAPI-based vector search system** with **Redis chat history** that transforms your existing search pipeline into a production-ready API with conversation context.

## 📁 Files Created

```
search/
├── 🌟 api_server.py           # Main FastAPI application with Redis chat history
├── 🔧 api_client.py           # Python client library with examples
├── 🧪 test_api.py             # Comprehensive test suite (async)
├── 🎮 demo_simple.py          # Simple demo using only stdlib
├── 🚀 startup.py              # Development utility script
├── 💻 start_api.ps1           # PowerShell script for Windows
├── 🐳 docker-compose.yml      # Full stack deployment
├── 📦 Dockerfile.api          # API container configuration
├── 📋 requirements.api.txt    # Complete dependency list
├── ⚙️ .env.example            # Environment configuration template
└── 📚 README_API.md           # Comprehensive documentation
```

## ✨ Key Features

### 🔍 **Enhanced Search**
- **Semantic Vector Search**: Uses your existing MongoDB Atlas vector search
- **Contextual Queries**: Chat history improves search relevance
- **Dual Structure Support**: Works with both new and legacy data models
- **Real-time Similarity**: Calculate semantic similarity between queries

### 💬 **Chat History with Redis**
- **Session Management**: Multiple concurrent user conversations
- **Automatic Context**: Previous messages enhance current queries
- **TTL Support**: Configurable session expiration (default: 1 hour)
- **Memory Management**: Automatic pruning of old messages

### 🌐 **Production-Ready API**
- **FastAPI**: High-performance async web framework
- **Interactive Docs**: Swagger UI at `/docs`
- **Health Monitoring**: Comprehensive system health checks
- **Error Handling**: Graceful fallbacks and informative errors
- **CORS Support**: Ready for web applications

### 🐳 **Deployment Options**
- **Local Development**: Direct Python execution
- **Docker Support**: Containerized deployment
- **Docker Compose**: Full stack with Redis
- **Environment Configuration**: Flexible env var management

## 🚦 Quick Start

### 1. **Install Dependencies**
```bash
# Option 1: Use the requirements file
pip install -r requirements.api.txt

# Option 2: Use the startup script
python startup.py install

# Option 3: Windows PowerShell
.\start_api.ps1 install
```

### 2. **Setup Environment**
```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your Redis and Azure OpenAI settings
```

### 3. **Start Redis**
```bash
# Docker (recommended)
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Or use Docker Compose
docker-compose up redis -d
```

### 4. **Run the API**
```bash
# Option 1: Python directly
python startup.py local

# Option 2: Windows PowerShell
.\start_api.ps1 local

# Option 3: Docker full stack
docker-compose up --build
```

### 5. **Test the API**
```bash
# Simple demo (no extra dependencies)
python demo_simple.py

# Comprehensive tests
python startup.py test

# Windows PowerShell
.\start_api.ps1 test
```

## 📡 API Endpoints

### Core Search
- `POST /search` - Vector search with chat history context
- `POST /search/similarity` - Calculate query similarity

### Chat Management
- `GET /chat-history/{session_id}` - Retrieve conversation history
- `DELETE /chat-history/{session_id}` - Clear session
- `GET /sessions` - List active sessions

### System Health
- `GET /` - Basic health check
- `GET /health/detailed` - Component status

## 💻 Usage Examples

### Python Client
```python
from api_client import VectorSearchClient

client = VectorSearchClient("http://localhost:8000")

# Search with automatic session management
result1 = client.search("What is the education background?")
result2 = client.search("What about work experience?")  # Uses context

print(f"Answer: {result1['answer']}")
print(f"Session: {result1['session_id']}")
```

### cURL
```bash
# Search request
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the education background?", "top_k": 3}'

# Get chat history
curl "http://localhost:8000/chat-history/session_abc123"
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8000/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'What technical skills are mentioned?',
    top_k: 3
  })
});
const result = await response.json();
console.log('Answer:', result.answer);
```

## 🔧 Configuration

### Environment Variables
```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
CHAT_HISTORY_TTL=3600

# Search
USE_NEW_DATA_STRUCTURE=true

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Chat History Features
- **Context Window**: Last 6 messages used for context
- **Message Limit**: 50 messages per session (configurable)
- **Auto-Expiration**: Sessions expire after TTL
- **Fallback Mode**: Works without Redis (in-memory only)

## 🧪 Testing

The system includes comprehensive testing:

### Automated Tests
- ✅ Health checks (basic + detailed)
- ✅ Search functionality (with/without history)
- ✅ Chat history operations
- ✅ Session management
- ✅ Conversation flows
- ✅ Error handling
- ✅ Input validation

### Manual Testing
- **Interactive Docs**: `http://localhost:8000/docs`
- **Simple Demo**: `python demo_simple.py`
- **Health Check**: `http://localhost:8000/`

## 🐳 Docker Deployment

### Development
```bash
# Full stack
docker-compose up --build

# API only
docker build -f Dockerfile.api -t vector-search-api .
docker run -p 8000:8000 vector-search-api
```

### Production
```bash
# With external Redis
docker run -d \
  -p 8000:8000 \
  -e REDIS_HOST=your-redis-host \
  -e REDIS_PASSWORD=your-password \
  vector-search-api
```

## 📊 How Chat History Works

### Context Building
```
User: "What is the education background?"
→ Search: "What is the education background?"

User: "What about work experience?"
→ Search: "Previous: education background | Current: work experience"
```

### Session Flow
1. **First Query**: Creates new session, stores user message + AI response
2. **Follow-up Queries**: Retrieves history, builds context, enhanced search
3. **Context Enhancement**: Recent messages improve search relevance
4. **Automatic Cleanup**: Sessions expire after TTL

## 🔍 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │      Redis      │    │    MongoDB      │
│                 │    │                 │    │                 │
│ • REST API      │◄──►│ • Chat History  │    │ • Vector Search │
│ • Session Mgmt  │    │ • Session Cache │    │ • Documents     │
│ • Health Check  │    │ • TTL Support   │    │ • Embeddings    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Azure OpenAI   │
                    │ • Embeddings    │
                    │ • Completions   │ 
                    │ • Chat Context  │
                    └─────────────────┘
```

## 🛠️ Development

### Adding Features
1. Add endpoint to `api_server.py`
2. Add tests to `test_api.py`
3. Update client in `api_client.py`
4. Update documentation

### Debugging
- **Logs**: Built-in logging with configurable levels
- **Health Checks**: Component-wise status monitoring
- **Error Handling**: Detailed error messages and fallbacks

## 🎯 Benefits

### For Users
- **Better Search**: Conversation context improves relevance
- **Natural Interaction**: Ask follow-up questions naturally
- **Fast Responses**: Optimized search with caching

### For Developers
- **REST API**: Standard HTTP interface
- **Documentation**: Auto-generated API docs
- **Testing**: Comprehensive test coverage
- **Deployment**: Multiple deployment options

### For Operations
- **Monitoring**: Health checks and metrics
- **Scaling**: Horizontal scaling support
- **Configuration**: Environment-based config
- **Reliability**: Graceful error handling

## 🎉 What's Next?

Your vector search system is now a **production-ready API** with **intelligent chat history**! 

🔗 **Access Points:**
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health/detailed

📖 **Learn More:**
- See `README_API.md` for detailed documentation
- Try `demo_simple.py` for a quick demonstration
- Explore `/docs` for interactive API testing

**Happy searching! 🚀**
