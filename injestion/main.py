import json
from scripts.pdf_from_s3 import extract_text_from_s3_pdf
from scripts.mongo_docs import extract_metadata
from scripts.mongo_utils import (
    insert_document, insert_knowledge_object, insert_chunk, 
    get_or_create_embedding_config, upsert_vector_document
)
from models.datamodel_pdantic import Document, KnowledgeObject, Chunk, EmbeddingInfo, VectorDocument
from scripts.extract import chunk_text
import os
from datetime import datetime

BUCKET_NAME = 's3-practice-ss'


def process_and_store_single_pdf_new_structure(bucket_name, pdf_key, chunk_size=300, overlap=50):
    """Process PDF using the new data structure with separate collections."""
    text = extract_text_from_s3_pdf(bucket_name, pdf_key)
    if not text or len(text.strip()) < 20:
        return {"pdf": pdf_key, "status": "no valid text"}
    
    # 1. Insert document
    doc = Document(
        filename=os.path.basename(pdf_key),
        filepath=f's3://{bucket_name}/{pdf_key}'
    )
    document_id = insert_document(doc)
    if not document_id:
        return {"pdf": pdf_key, "status": "failed to insert document"}
    
    # 2. Extract and store knowledge object (document-level metadata)
    metadata = extract_metadata(text[:2000])  # Use first 2000 chars for document summary
    knowledge_obj = KnowledgeObject(
        document_id=document_id,
        summary=metadata['summary'],
        keywords=metadata.get('keywords', []),
        intent=metadata.get('intent', ""),
        entities=metadata.get('entities', []),
        topic=metadata.get('topic', ""),
        model_name=metadata.get('model_name', 'gpt-4o')
    )
    insert_knowledge_object(knowledge_obj)
    
    # 3. Get or create embedding config
    embedding_config_id = get_or_create_embedding_config(
        model_name="text-embedding-3-small",
        embedding_size=1536,
        distance_metric="cosine"
    )
    
    # 4. Process and store chunks
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    chunk_results = []
    
    import concurrent.futures
    
    def process_chunk(i_chunk):
        i, chunk_text_content = i_chunk
        chunk_metadata = extract_metadata(chunk_text_content)
        
        # Create embedding info
        embedding_info = EmbeddingInfo(
            config_id=embedding_config_id,
            vector=chunk_metadata['embedding']
        )
        
        # Create chunk
        chunk = Chunk(
            document_id=document_id,
            chunk_text=chunk_text_content,
            chunk_index=i,
            start_pos=i * (chunk_size - overlap),
            end_pos=min((i * (chunk_size - overlap)) + len(chunk_text_content), len(text)),
            embeddings=[embedding_info]
        )
        
        chunk_id = insert_chunk(chunk)
        return {"chunk_index": i, "chunk_id": chunk_id, "status": "inserted" if chunk_id else "failed"}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        chunk_results = list(executor.map(process_chunk, enumerate(chunks)))
    
    return {
        "pdf": pdf_key,
        "document_id": document_id,
        "chunks_processed": len(chunk_results),
        "chunks": chunk_results
    }


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
		from scripts.mongo_utils import collection
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
	import logging
	logging.basicConfig(level=logging.INFO)
	
	results = []
	use_new_structure = os.getenv("USE_NEW_DATA_STRUCTURE", "false").lower() == "true"
	
	# Log the configuration
	logging.info(f"USE_NEW_DATA_STRUCTURE: {use_new_structure}")
	logging.info(f"Received event: {json.dumps(event, default=str)}")
	
	try:
		for record in event.get('Records', []):
			try:
				pdf_key = record['s3']['object']['key']
				logging.info(f"Processing PDF: {pdf_key}")
				
				# Validate that the key looks like a PDF
				if not pdf_key.lower().endswith('.pdf'):
					logging.warning(f"Skipping non-PDF file: {pdf_key}")
					results.append({
						"pdf": pdf_key, 
						"status": "skipped", 
						"reason": "not a PDF file"
					})
					continue
				
				if use_new_structure:
					logging.info("Using NEW data structure")
					result = process_and_store_single_pdf_new_structure(BUCKET_NAME, pdf_key)
				else:
					logging.info("Using LEGACY data structure")
					result = process_and_store_single_pdf(BUCKET_NAME, pdf_key)
				results.append(result)
				
			except KeyError as e:
				error_msg = f"Missing required field in event record: {str(e)}"
				logging.error(error_msg)
				results.append({
					"status": "error",
					"error": error_msg
				})
			except FileNotFoundError as e:
				error_msg = f"File not found: {str(e)}"
				logging.error(error_msg)
				results.append({
					"pdf": pdf_key if 'pdf_key' in locals() else "unknown",
					"status": "error",
					"error": error_msg
				})
			except Exception as e:
				error_msg = f"Error processing record: {str(e)}"
				logging.error(error_msg)
				results.append({
					"pdf": pdf_key if 'pdf_key' in locals() else "unknown",
					"status": "error", 
					"error": error_msg
				})
				
	except Exception as e:
		logging.error(f"Critical error in lambda_handler: {str(e)}")
		return {
			"statusCode": 500,
			"headers": {"Content-Type": "application/json"},
			"body": json.dumps({"error": f"Critical error: {str(e)}"})
		}
	
	return {
		"statusCode": 200,
		"headers": {"Content-Type": "application/json"},
		"body": json.dumps(results)
	}
