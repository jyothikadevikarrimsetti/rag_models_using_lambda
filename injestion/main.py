import json
from scripts.pdf_from_s3 import list_pdfs_in_s3, extract_text_from_s3_pdf
from scripts.mongo_docs import extract_metadata
from scripts.mongo_utils import upsert_vector_document
from models.datamodel_pdantic import VectorDocument
from scripts.extract import chunk_text

BUCKET_NAME = 's3-practice-ss'

def process_and_store_all_pdfs(bucket_name, chunk_size=300, overlap=50):
	pdf_keys = list_pdfs_in_s3(bucket_name)
	results = []
	for pdf_key in pdf_keys:
		text = extract_text_from_s3_pdf(bucket_name, pdf_key)
		if not text or len(text.strip()) < 20:
			results.append({"pdf": pdf_key, "status": "no valid text"})
			continue
		chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
		chunk_results = []
		for i, chunk in enumerate(chunks):
			chunk_id = f"{pdf_key}_chunk_{i+1}"
			metadata = extract_metadata(chunk, document_name=chunk_id)
			doc = VectorDocument(
				_id=chunk_id,
				path=pdf_key,
				href=f's3://{bucket_name}/{pdf_key}',
				title=f"{pdf_key} [chunk {i+1}]",
				summary=metadata['summary'],
				text=metadata['text'],
				embedding=metadata['embedding']
			)
			upsert_result = upsert_vector_document(doc)
			chunk_results.append({"chunk_id": chunk_id, "upserted": upsert_result is not None})
		results.append({"pdf": pdf_key, "chunks": chunk_results})
	return results

def lambda_handler(event, context):
	# You can customize event parsing as needed
	result = process_and_store_all_pdfs(BUCKET_NAME)
	return {
		"statusCode": 200,
		"headers": {"Content-Type": "application/json"},
		"body": json.dumps(result)
	}
