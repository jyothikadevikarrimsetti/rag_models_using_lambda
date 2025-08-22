def download_pdf_from_s3(bucket_name, pdf_key, save_dir="."):
	"""Download a PDF from S3 and save it to the specified directory."""
	import os
	s3 = boto3.client('s3')
	response = s3.get_object(Bucket=bucket_name, Key=pdf_key)
	pdf_bytes = response['Body'].read()
	local_path = os.path.join(save_dir, pdf_key)
	os.makedirs(os.path.dirname(local_path), exist_ok=True)
	with open(local_path, "wb") as f:
		f.write(pdf_bytes)
	print(f"Downloaded {pdf_key} to {local_path}")
	return local_path
import boto3
import tempfile
from scripts.extract import extract_text_from_pdf

def list_pdfs_in_s3(bucket_name):
	"""List all PDF files in the given S3 bucket."""
	s3 = boto3.client('s3')
	paginator = s3.get_paginator('list_objects_v2')
	pdf_keys = []
	for page in paginator.paginate(Bucket=bucket_name):
		for obj in page.get('Contents', []):
			key = obj['Key']
			if key.lower().endswith('.pdf'):
				pdf_keys.append(key)
	return pdf_keys

def extract_text_from_s3_pdf(bucket_name, pdf_key):
	"""Download a PDF from S3 and extract its text."""
	import io
	s3 = boto3.client('s3')
	response = s3.get_object(Bucket=bucket_name, Key=pdf_key)
	pdf_bytes = response['Body'].read()
	pdf_stream = io.BytesIO(pdf_bytes)
	text = extract_text_from_pdf(pdf_stream)
	return text

def process_all_pdfs_in_s3(bucket_name):
	"""Find all PDFs in S3, extract and print their text."""
	pdf_keys = list_pdfs_in_s3(bucket_name)
	print(f"Found {len(pdf_keys)} PDFs in bucket '{bucket_name}':")
	for pdf_key in pdf_keys:
		print(f"\n--- Extracting: {pdf_key} ---")
		text = extract_text_from_s3_pdf(bucket_name, pdf_key)
		print(text)


