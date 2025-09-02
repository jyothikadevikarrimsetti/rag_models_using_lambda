#!/usr/bin/env python3
"""
Demo script for the unified API with PDF upload functionality
Demonstrates uploading PDFs and monitoring processing status
"""

import requests
import time
import json
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8000"
DEMO_PDF_PATH = "demo.pdf"  # Update this to a valid PDF path

def create_demo_pdf():
    """Create a simple demo PDF if none exists"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(DEMO_PDF_PATH, pagesize=letter)
        c.drawString(100, 750, "Demo PDF for Upload Testing")
        c.drawString(100, 730, "This is a test document created for API testing.")
        c.drawString(100, 710, f"Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        c.save()
        
        print(f"✅ Created demo PDF: {DEMO_PDF_PATH}")
        return True
    except ImportError:
        print("❌ reportlab not installed. Please provide a PDF file manually.")
        return False

def check_health():
    """Check API health status"""
    print("🔍 Checking API health...")
    
    try:
        # Check main health
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            print("✅ Main API is healthy")
        
        # Check AWS health
        response = requests.get(f"{API_BASE_URL}/aws-health")
        if response.status_code == 200:
            aws_health = response.json()
            print(f"✅ AWS Status: {aws_health['status']}")
            print(f"   S3 Accessible: {aws_health['s3_accessible']}")
            print(f"   Lambda Accessible: {aws_health['lambda_accessible']}")
        else:
            print("⚠️ AWS services may not be available")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure it's running on port 8000.")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    return True

def upload_pdf(pdf_path, process_immediately=True):
    """Upload a PDF file"""
    if not Path(pdf_path).exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return None
    
    print(f"📤 Uploading PDF: {pdf_path}")
    
    try:
        with open(pdf_path, 'rb') as file:
            files = {'file': file}
            params = {'process_immediately': process_immediately}
            
            response = requests.post(
                f"{API_BASE_URL}/upload", 
                files=files, 
                params=params
            )
        
        if response.status_code == 200:
            upload_result = response.json()
            print("✅ Upload successful!")
            print(f"   Request ID: {upload_result['request_id']}")
            print(f"   S3 Key: {upload_result['s3_key']}")
            print(f"   File Size: {upload_result['file_size']} bytes")
            print(f"   Lambda Triggered: {upload_result['lambda_triggered']}")
            return upload_result
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def check_processing_status(request_id, max_wait=30):
    """Check processing status with polling"""
    print(f"⏳ Monitoring processing status for {request_id}...")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE_URL}/status/{request_id}")
            
            if response.status_code == 200:
                status = response.json()
                print(f"   Status: {status['status']}")
                
                if status['status'] in ['completed', 'failed']:
                    if status['lambda_execution']:
                        print(f"   Lambda Status: {status['lambda_execution']['status']}")
                        if status['lambda_execution'].get('execution_time_ms'):
                            print(f"   Execution Time: {status['lambda_execution']['execution_time_ms']}ms")
                    
                    if status.get('processing_results'):
                        print("   ✅ Processing Results Available")
                        print(f"   Results: {json.dumps(status['processing_results'], indent=2)}")
                    
                    return status
                
                time.sleep(2)
            else:
                print(f"❌ Status check failed: {response.status_code}")
                break
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
            break
    
    print("⏰ Timeout waiting for processing to complete")
    return None

def list_uploads():
    """List recent uploads"""
    print("📋 Listing recent uploads...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/uploads")
        
        if response.status_code == 200:
            uploads = response.json()
            print(f"   Total uploads: {uploads['total_uploads']}")
            
            for upload in uploads['uploads']:
                print(f"   📄 {upload['s3_key']}")
                print(f"      Status: {upload['status']}")
                print(f"      Time: {upload['upload_time']}")
                print(f"      Has Results: {upload['has_results']}")
                print()
        else:
            print(f"❌ Failed to list uploads: {response.status_code}")
            
    except Exception as e:
        print(f"❌ List uploads error: {e}")

def get_lambda_logs(execution_id):
    """Get Lambda execution logs"""
    print(f"📋 Getting Lambda logs for {execution_id}...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/lambda-logs/{execution_id}")
        
        if response.status_code == 200:
            logs = response.json()
            
            if 'logs' in logs and logs['logs']:
                print(f"   Log Stream: {logs.get('log_stream', 'unknown')}")
                print(f"   Total Events: {logs.get('total_events', 0)}")
                print("   Recent Logs:")
                
                for log_entry in logs['logs'][-10:]:  # Show last 10 entries
                    print(f"     {log_entry['timestamp']}: {log_entry['message']}")
            else:
                print("   No logs available or error occurred")
                if 'error' in logs:
                    print(f"   Error: {logs['error']}")
        else:
            print(f"❌ Failed to get logs: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Get logs error: {e}")

def list_s3_files():
    """List files in S3 bucket"""
    print("🗂️ Listing S3 files...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/s3-files")
        
        if response.status_code == 200:
            s3_files = response.json()
            print(f"   Bucket: {s3_files['bucket']}")
            print(f"   Total files: {s3_files['total']}")
            
            for file_info in s3_files['files']:
                print(f"   📄 {file_info['key']}")
                print(f"      Size: {file_info['size']} bytes")
                print(f"      Modified: {file_info['last_modified']}")
                print()
        else:
            print(f"❌ Failed to list S3 files: {response.status_code}")
            
    except Exception as e:
        print(f"❌ List S3 files error: {e}")

def demo_search_with_context():
    """Demo the enhanced search with chat history"""
    print("🔍 Testing search with chat history...")
    
    session_id = f"demo_session_{int(time.time())}"
    
    # First search
    search_data = {
        "query": "What is machine learning?",
        "session_id": session_id,
        "top_k": 3
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/search", json=search_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Search completed")
            print(f"   Answer: {result['answer'][:200]}...")
            print(f"   Documents: {len(result['documents'])}")
            print(f"   Session ID: {result['session_id']}")
            
            # Follow-up search
            follow_up_data = {
                "query": "Can you explain more about neural networks?",
                "session_id": session_id,
                "top_k": 3
            }
            
            response2 = requests.post(f"{API_BASE_URL}/search", json=follow_up_data)
            
            if response2.status_code == 200:
                result2 = response2.json()
                print(f"✅ Follow-up search completed")
                print(f"   Answer: {result2['answer'][:200]}...")
                print(f"   Used Chat History: {len(result2['chat_context'])} messages")
        else:
            print(f"❌ Search failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Search error: {e}")

def main():
    """Main demo function"""
    print("🚀 Unified API Demo - Upload & Search")
    print("=" * 50)
    
    # Health check
    if not check_health():
        return
    
    print()
    
    # Create demo PDF if needed
    if not Path(DEMO_PDF_PATH).exists():
        if not create_demo_pdf():
            print("Please provide a PDF file for testing and update DEMO_PDF_PATH")
            return
    
    print()
    
    # Upload PDF
    upload_result = upload_pdf(DEMO_PDF_PATH)
    
    if upload_result:
        print()
        
        # Monitor processing
        status = check_processing_status(upload_result['request_id'])
        
        if status and status.get('lambda_execution'):
            print()
            
            # Get logs if available
            execution_id = status['lambda_execution']['execution_id']
            get_lambda_logs(execution_id)
    
    print()
    
    # List uploads
    list_uploads()
    
    print()
    
    # List S3 files
    list_s3_files()
    
    print()
    
    # Demo search functionality
    demo_search_with_context()
    
    print()
    print("✅ Demo completed!")

if __name__ == "__main__":
    main()
