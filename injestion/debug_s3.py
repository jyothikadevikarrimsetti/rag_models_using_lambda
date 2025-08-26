"""
Debug utility to help troubleshoot S3 and Lambda issues.
"""

import json
import boto3
import logging
from scripts.pdf_from_s3 import list_pdfs_in_s3

# Configure logging
logging.basicConfig(level=logging.INFO)

BUCKET_NAME = 's3-practice-ss'


def test_s3_connection():
    """Test S3 connection and list available PDFs."""
    try:
        s3 = boto3.client('s3')
        
        # Test bucket access
        logging.info(f"Testing access to bucket: {BUCKET_NAME}")
        response = s3.head_bucket(Bucket=BUCKET_NAME)
        logging.info(f"✅ Bucket access successful")
        
        # List all PDFs
        pdf_files = list_pdfs_in_s3(BUCKET_NAME)
        logging.info(f"📄 Found {len(pdf_files)} PDF files:")
        for pdf in pdf_files:
            logging.info(f"   - {pdf}")
            
        return pdf_files
        
    except Exception as e:
        logging.error(f"❌ S3 connection failed: {str(e)}")
        return []


def test_lambda_event_structure():
    """Show expected Lambda event structure for S3 triggers."""
    sample_event = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {
                        "name": BUCKET_NAME
                    },
                    "object": {
                        "key": "sample-document.pdf"
                    }
                }
            }
        ]
    }
    
    logging.info("📝 Expected Lambda event structure:")
    logging.info(json.dumps(sample_event, indent=2))
    return sample_event


def validate_pdf_key(pdf_key):
    """Validate that a PDF key exists in S3."""
    try:
        s3 = boto3.client('s3')
        s3.head_object(Bucket=BUCKET_NAME, Key=pdf_key)
        logging.info(f"✅ PDF exists: s3://{BUCKET_NAME}/{pdf_key}")
        return True
    except s3.exceptions.NoSuchKey:
        logging.error(f"❌ PDF not found: s3://{BUCKET_NAME}/{pdf_key}")
        return False
    except Exception as e:
        logging.error(f"❌ Error checking PDF: {str(e)}")
        return False


if __name__ == "__main__":
    print("🔍 S3 Debug Utility")
    print("=" * 50)
    
    # Test S3 connection
    pdfs = test_s3_connection()
    
    # Show event structure
    test_lambda_event_structure()
    
    # Test specific PDF if available
    if pdfs:
        test_pdf = pdfs[0]
        print(f"\n🧪 Testing PDF: {test_pdf}")
        validate_pdf_key(test_pdf)
