#!/usr/bin/env python3
"""
Startup script for the unified Search & Upload API
Handles environment setup and starts the server
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if environment is properly configured"""
    env_file = Path("../injestion/config/.env")
    
    if not env_file.exists():
        print("❌ Environment file not found!")
        print(f"   Expected: {env_file.absolute()}")
        print("   Please create the .env file with required configuration.")
        return False
    
    print(f"✅ Environment file found: {env_file}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'redis',
        'pymongo',
        'openai',
        'boto3',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print()
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def start_server():
    """Start the API server"""
    print("🚀 Starting Unified Search & Upload API...")
    print("   Server will be available at: http://localhost:8000")
    print("   API documentation: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop the server")
    print()
    
    try:
        import uvicorn
        uvicorn.run(
            "api_server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")

def main():
    """Main startup function"""
    print("🔧 Unified API Startup")
    print("=" * 30)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()
