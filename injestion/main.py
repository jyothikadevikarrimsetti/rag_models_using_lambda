import json
from scripts.pdf_from_s3 import extract_text_from_s3_pdf
from scripts.mongo_docs import extract_metadata
from scripts.mongo_utils import upsert_vector_document, collection
from models.datamodel_pdantic import VectorDocument
from scripts.extract import chunk_text

BUCKET_NAME = 's3-practice-ss'


def process_and_store_single_pdf(bucket_name, pdf_key, chunk_size=300, overlap=50):
	text = extract_text_from_s3_pdf(bucket_name, pdf_key)
	if not text or len(text.strip()) < 20:
		return {"pdf": pdf_key, "status": "no valid text"}
	import concurrent.futures
	chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
	chunk_results = []

	def process_chunk(i_chunk):
		i, chunk = i_chunk
		chunk_id = f"{pdf_key}_chunk_{i+1}"
		# Check if chunk already exists in MongoDB
		if collection.find_one({"_id": chunk_id}):
			return {"chunk_id": chunk_id, "upserted": False, "status": "already exists"}
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
		return {"chunk_id": chunk_id, "upserted": upsert_result is not None, "status": "upserted"}

	with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
		chunk_results = list(executor.map(process_chunk, enumerate(chunks)))

	return {"pdf": pdf_key, "chunks": chunk_results}


def lambda_handler(event, context):
	# Support multiple PDF uploads in a single event
	results = []
	for record in event.get('Records', []):
		pdf_key = record['s3']['object']['key']
		result = process_and_store_single_pdf(BUCKET_NAME, pdf_key)
		results.append(result)
	return {
		"statusCode": 200,
		"headers": {"Content-Type": "application/json"},
		"body": json.dumps(results)
	}
