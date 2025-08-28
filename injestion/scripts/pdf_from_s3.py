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
	import logging
	s3 = boto3.client('s3')
	paginator = s3.get_paginator('list_objects_v2')
	pdf_keys = []
	
	try:
		for page in paginator.paginate(Bucket=bucket_name):
			for obj in page.get('Contents', []):
				key = obj['Key']
				if key.lower().endswith('.pdf'):
					pdf_keys.append(key)
					logging.info(f"Found PDF: {key}")
		
		logging.info(f"Total PDFs found in {bucket_name}: {len(pdf_keys)}")
		return pdf_keys
		
	except Exception as e:
		logging.error(f"Error listing PDFs in bucket {bucket_name}: {str(e)}")
		return []

def extract_text_from_s3_pdf(bucket_name, pdf_key):
	"""Download a PDF from S3 and extract its text."""
	import io
	import logging
	import urllib.parse
	s3 = boto3.client('s3')
	
	try:
		# URL decode the pdf_key to handle encoded characters like %2B (plus sign)
		decoded_pdf_key = urllib.parse.unquote(pdf_key)
		logging.info(f"Original key: {pdf_key}")
		logging.info(f"Decoded key: {decoded_pdf_key}")
		
		# Log the attempt
		logging.info(f"Attempting to fetch PDF: s3://{bucket_name}/{decoded_pdf_key}")
		
		# Check if object exists first
		try:
			s3.head_object(Bucket=bucket_name, Key=decoded_pdf_key)
		except s3.exceptions.NoSuchKey:
			# Try with original key if decoded key fails
			logging.info(f"Decoded key not found, trying original key: {pdf_key}")
			try:
				s3.head_object(Bucket=bucket_name, Key=pdf_key)
				decoded_pdf_key = pdf_key  # Use original key if it works
			except s3.exceptions.NoSuchKey:
				logging.error(f"PDF file not found with either key: s3://{bucket_name}/{pdf_key}")
				raise FileNotFoundError(f"PDF file not found: s3://{bucket_name}/{pdf_key}")
		except Exception as e:
			logging.error(f"Error checking if file exists: {e}")
			raise
		
		response = s3.get_object(Bucket=bucket_name, Key=decoded_pdf_key)
		pdf_bytes = response['Body'].read()
		pdf_stream = io.BytesIO(pdf_bytes)
		text = extract_text_from_pdf(pdf_stream)
		logging.info(f"Successfully extracted {len(text)} characters from {decoded_pdf_key}")
		return text
		
	except Exception as e:
		logging.error(f"Failed to extract text from {pdf_key}: {str(e)}")
		raise

def process_all_pdfs_in_s3(bucket_name):
	"""Find all PDFs in S3, extract and print their text."""
	pdf_keys = list_pdfs_in_s3(bucket_name)
	print(f"Found {len(pdf_keys)} PDFs in bucket '{bucket_name}':")
	for pdf_key in pdf_keys:
		print(f"\n--- Extracting: {pdf_key} ---")
		text = extract_text_from_s3_pdf(bucket_name, pdf_key)
		print(text)


