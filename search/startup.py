"""
Startup script for Vector Search API with Redis chat history.
Provides easy commands to run the API locally or with Docker.
"""

import os
import sys
import subprocess
import time
import argparse

def check_redis_connection():
    """Check if Redis is available"""
    try:
        import redis
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        
        r = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=5)
        r.ping()
        print(f"✅ Redis is running at {redis_host}:{redis_port}")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ["fastapi", "uvicorn", "redis", "pymongo", "openai"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install -r requirements.api.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def setup_environment():
    """Setup environment variables"""
    env_file = ".env"
    if not os.path.exists(env_file):
        if os.path.exists(".env.example"):
            print("📋 Creating .env file from .env.example")
            subprocess.run(["cp", ".env.example", ".env"], shell=True)
        else:
            print("⚠️ No .env file found. Please create one based on .env.example")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

def run_local():
    """Run the API locally"""
    print("🚀 Starting Vector Search API locally...")
    
    if not check_dependencies():
        return False
    
    setup_environment()
    
    # Check Redis
    if not check_redis_connection():
        print("💡 To start Redis locally:")
        print("   - Docker: docker run -d -p 6379:6379 redis:7-alpine")
        print("   - Local: redis-server")
        print("   - Or use Docker Compose: docker-compose up redis")
    
    # Start the API
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "api_server:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ]
        
        print("📡 API will be available at: http://localhost:8000")
        print("📚 API docs will be available at: http://localhost:8000/docs")
        print("🔍 Health check: http://localhost:8000/")
        print("\nPress Ctrl+C to stop the server")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 API server stopped")
    except Exception as e:
        print(f"❌ Failed to start API: {e}")
        return False
    
    return True

def run_docker():
    """Run with Docker Compose"""
    print("🐳 Starting with Docker Compose...")
    
    if not os.path.exists("docker-compose.yml"):
        print("❌ docker-compose.yml not found")
        return False
    
    try:
        # Build and start services
        print("📦 Building and starting services...")
        subprocess.run(["docker-compose", "up", "--build", "-d"], check=True)
        
        print("⏳ Waiting for services to start...")
        time.sleep(10)
        
        # Check service status
        result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True)
        print("📋 Service Status:")
        print(result.stdout)
        
        print("📡 API should be available at: http://localhost:8000")
        print("📚 API docs: http://localhost:8000/docs")
        print("\nTo stop services: docker-compose down")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker Compose failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def run_tests():
    """Run API tests"""
    print("🧪 Running API tests...")
    
    try:
        # Check if API is running
        import requests
        try:
            response = requests.get("http://localhost:8000/", timeout=5)
            if response.status_code == 200:
                print("✅ API is running, starting tests...")
            else:
                print("⚠️ API returned non-200 status, proceeding with tests...")
        except:
            print("⚠️ API may not be running, tests might fail...")
        
        # Run tests
        cmd = [sys.executable, "test_api.py", "--url", "http://localhost:8000"]
        subprocess.run(cmd)
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.api.txt"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Vector Search API Startup Script")
    parser.add_argument("command", choices=["local", "docker", "test", "install", "check"], 
                       help="Command to run")
    
    args = parser.parse_args()
    
    print("🔍 Vector Search API with Chat History")
    print("=" * 40)
    
    if args.command == "local":
        run_local()
    elif args.command == "docker":
        run_docker()
    elif args.command == "test":
        run_tests()
    elif args.command == "install":
        install_dependencies()
    elif args.command == "check":
        print("🔍 Checking system dependencies...")
        deps_ok = check_dependencies()
        redis_ok = check_redis_connection()
        
        if deps_ok and redis_ok:
            print("\n✅ System is ready to run the API")
        else:
            print("\n❌ System needs setup before running the API")

if __name__ == "__main__":
    main()
