# Docker Run Commands for Search API

## 🐳 Quick Start

### Basic Docker Run Command
```bash
docker run -d \
  --name rag-search-api \
  -p 8000:8000 \
  eswarchivatam/ragbackend:latest
```

## 🔧 Production Docker Run with Environment Variables

### With Environment File
```bash
# Create .env file first
docker run -d \
  --name rag-search-api \
  -p 8000:8000 \
  --env-file ../injestion/config/.env \
  --restart unless-stopped \
  --health-cmd="curl -f http://localhost:8000/api/ || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  eswarchivatam/ragbackend:latest
```

### With Individual Environment Variables
```bash
docker run -d \
  --name rag-search-api \
  -p 8000:8000 \
  -e MONGODB_URI="mongodb+srv://username:password@cluster.mongodb.net/database" \
  -e MONGODB_DATABASE="rag_with_lambda" \
  -e MONGODB_COLLECTION="chunks" \
  -e OPENAI_API_KEY="your_openai_api_key" \
  -e OPENAI_ENDPOINT="https://your-azure-openai.openai.azure.com/" \
  -e OPENAI_API_VERSION="2024-02-15-preview" \
  -e OPENAI_DEPLOYMENT_NAME="your_deployment" \
  -e REDIS_HOST="redis-container" \
  -e REDIS_PORT="6379" \
  -e REDIS_PASSWORD="your_redis_password" \
  -e AWS_ACCESS_KEY_ID="your_aws_access_key" \
  -e AWS_SECRET_ACCESS_KEY="your_aws_secret_key" \
  -e AWS_REGION="ap-south-1" \
  -e S3_BUCKET_NAME="your-s3-bucket" \
  -e LAMBDA_FUNCTION_NAME="your-lambda-function" \
  --restart unless-stopped \
  eswarchivatam/ragbackend:latest
```

## 🔗 Docker Compose Setup (Recommended)

### Create docker-compose.yml
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: rag-redis
    ports:
      - "6379:6379"
    command: redis-server --requirepass yourredispassword
    volumes:
      - redis_data:/data
    restart: unless-stopped

  search-api:
    image: eswarchivatam/ragbackend:latest
    container_name: rag-search-api
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=yourredispassword
      - MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database
      - MONGODB_DATABASE=rag_with_lambda
      - MONGODB_COLLECTION=chunks
      - OPENAI_API_KEY=your_openai_api_key
      - OPENAI_ENDPOINT=https://your-azure-openai.openai.azure.com/
      - OPENAI_API_VERSION=2024-02-15-preview
      - OPENAI_DEPLOYMENT_NAME=your_deployment
      - AWS_ACCESS_KEY_ID=your_aws_access_key
      - AWS_SECRET_ACCESS_KEY=your_aws_secret_key
      - AWS_REGION=ap-south-1
      - S3_BUCKET_NAME=your-s3-bucket
      - LAMBDA_FUNCTION_NAME=your-lambda-function
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
```

### Run with Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f search-api

# Stop all services
docker-compose down
```

## 🚀 Development Mode

### With Volume Mounting (for development)
```bash
docker run -d \
  --name rag-search-api-dev \
  -p 8000:8000 \
  -v "$(pwd):/app" \
  --env-file ../injestion/config/.env \
  eswarchivatam/ragbackend:latest \
  uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

## 🔍 Debugging Commands

### Check Container Status
```bash
# List running containers
docker ps

# Check container logs
docker logs rag-search-api

# Follow logs in real-time
docker logs -f rag-search-api

# Execute commands in container
docker exec -it rag-search-api bash

# Check container health
docker inspect rag-search-api | grep -A 5 Health
```

### Test API Endpoints
```bash
# Test health endpoint
curl http://localhost:8000/api/

# Test search endpoint
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 3}'

# Test AWS health
curl http://localhost:8000/api/aws-health
```

## 🔧 Environment Variables Required

### Core Variables (Required)
```bash
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database
MONGODB_DATABASE=rag_with_lambda
MONGODB_COLLECTION=chunks
OPENAI_API_KEY=your_openai_api_key
OPENAI_ENDPOINT=https://your-azure-openai.openai.azure.com/
OPENAI_DEPLOYMENT_NAME=your_deployment
```

### Redis Variables (Optional - falls back to mock)
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
```

### AWS Variables (Optional - for upload functionality)
```bash
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-s3-bucket
LAMBDA_FUNCTION_NAME=your-lambda-function
```

## 🎯 Quick Test

After running the container, test these endpoints:

1. **Health Check**: `GET http://localhost:8000/api/`
2. **API Documentation**: `GET http://localhost:8000/docs`
3. **Search**: `POST http://localhost:8000/api/search`
4. **Upload**: `POST http://localhost:8000/api/upload`

## 📊 Container Management

### Update to Latest Version
```bash
# Pull latest image
docker pull eswarchivatam/ragbackend:latest

# Stop current container
docker stop rag-search-api

# Remove old container
docker rm rag-search-api

# Run new container
docker run -d \
  --name rag-search-api \
  -p 8000:8000 \
  --env-file ../injestion/config/.env \
  --restart unless-stopped \
  eswarchivatam/ragbackend:latest
```

### Backup and Restore
```bash
# Backup container configuration
docker inspect rag-search-api > container-config.json

# Export container as image
docker commit rag-search-api my-search-api-backup

# Save image to file
docker save eswarchivatam/ragbackend:latest > ragbackend.tar
```

Happy containerized searching! 🐳🔍
