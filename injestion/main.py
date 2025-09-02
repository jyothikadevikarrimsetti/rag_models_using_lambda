import json
from scripts.pdf_from_s3 import extract_text_from_s3_pdf
from scripts.mongo_docs import extract_metadata
from scripts.mongo_utils import (
    insert_module, insert_knowledge_object, insert_chunk, 
    create_embedding_meta, update_knowledge_object_chunk_ids, upsert_vector_document
)
from models.datamodel_pdantic import Module, KnowledgeObject, Chunk, EmbeddingMeta, Metadata, VectorDocument
from scripts.extract import chunk_text
import os
from datetime import datetime

BUCKET_NAME = 's3-practice-ss'


def process_and_store_single_pdf_new_structure(bucket_name, pdf_key, chunk_size=300, overlap=50):
    """Process PDF using the new data structure with separate collections."""
    text = extract_text_from_s3_pdf(bucket_name, pdf_key)
    if not text or len(text.strip()) < 20:
        return {"pdf": pdf_key, "status": "no valid text"}
    
    # 1. Create or get module for this document
    module = Module(
        module_id=f"mod_{os.path.basename(pdf_key).replace('.pdf', '')}",
        module_tag=["document", "pdf"],
        module_link=[]
    )
    module_id = insert_module(module)
    if not module_id:
        return {"pdf": pdf_key, "status": "failed to insert module"}
    
    # 2. Create metadata for the document
    from datetime import datetime
    metadata = Metadata(
        path=f's3://{bucket_name}/{pdf_key}',
        repo_url="",
        intent_category="document",
        version="1.0",
        modified_time=datetime.utcnow(),
        csp="aws"
    )
    
    # 3. Extract and store knowledge object (document-level metadata)
    from scripts.mongo_docs import summarize_text, extract_keywords_and_entities
    import logging
    
    # Get simple summary for document-level metadata
    document_summary = summarize_text(text[:2000])  # Use first 2000 chars for document summary
    
    # Check if metadata extraction is enabled
    enable_metadata = os.getenv("ENABLE_METADATA_EXTRACTION", "false").lower() == "true"
    
    if enable_metadata:
        logging.info("Metadata extraction enabled - extracting keywords and entities")
        metadata_extraction = extract_keywords_and_entities(text[:2000])
        keywords = ", ".join(metadata_extraction.get('keywords', []))
        logging.info(f"Extracted {len(metadata_extraction.get('keywords', []))} keywords")
    else:
        logging.info("Metadata extraction disabled - using empty keywords")
        keywords = ""
    
    knowledge_obj = KnowledgeObject(
        title=os.path.basename(pdf_key).replace('.pdf', ''),
        named_entity=f"entity_{os.path.basename(pdf_key).replace('.pdf', '')}",
        summary=document_summary,
        content=text[:1000] if len(text) > 1000 else text,  # Store first 1000 chars as content preview
        keywords=keywords,  # Now populated based on env variable
        texts=text,   # Full text
        is_terraform=False,  # Assume false unless detected
        metadata=metadata,
        module_id=module_id,
        chunk_ids=[]  # Will be populated after chunk creation
    )
    
    # Insert knowledge object first to get its ID
    knowledge_result = insert_knowledge_object(knowledge_obj)
    
    # 4. Process and store chunks
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    chunk_results = []
    chunk_ids = []
    
    import concurrent.futures
    
    def process_chunk(i_chunk):
        i, chunk_text_content = i_chunk
        
        # Import the embedding function directly
        from scripts.mongo_docs import get_openai_embedding
        
        # Get embedding directly
        try:
            chunk_embedding = get_openai_embedding(chunk_text_content)
            import logging
            logging.info(f"Chunk {i}: Generated embedding with {len(chunk_embedding)} dimensions")
        except Exception as e:
            import logging
            logging.error(f"Chunk {i}: Failed to generate embedding: {e}")
            return {"chunk_index": i, "chunk_id": None, "status": "embedding_failed", "error": str(e)}
        
        # Create embedding metadata
        embedding_meta = create_embedding_meta(
            model_name="text-embedding-3-small",
            dimensionality=len(chunk_embedding)
        )
        
        # Create chunk with new structure
        chunk = Chunk(
            document_id=module_id,  # Use module_id as document reference
            chunk_id=i + 1,  # Sequential ID starting from 1
            chunk_start=i * (chunk_size - overlap),
            chunk_end=min((i * (chunk_size - overlap)) + len(chunk_text_content), len(text)),
            chunk_text=chunk_text_content,
            embedding=chunk_embedding,
            embedding_meta=embedding_meta
        )
        
        # Debug the chunk
        import logging
        logging.info(f"Chunk {i}: Chunk embedding length = {len(chunk.embedding)}")
        
        chunk_id = insert_chunk(chunk)
        return {"chunk_index": i, "chunk_id": chunk_id, "status": "inserted" if chunk_id else "failed"}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        chunk_results = list(executor.map(process_chunk, enumerate(chunks)))
    
    # 5. Update knowledge object with chunk IDs
    chunk_ids = [result["chunk_id"] for result in chunk_results if result["chunk_id"]]
    
    # Update the knowledge object with the actual chunk IDs
    if chunk_ids:
        update_success = update_knowledge_object_chunk_ids(
            module_id=module_id,
            title=knowledge_obj.title,
            chunk_ids=chunk_ids
        )
        if not update_success:
            print(f"⚠️ Warning: Could not update knowledge object with chunk IDs")
    
    return {
        "pdf": pdf_key,
        "module_id": module_id,
        "chunks_processed": len(chunk_results),
        "chunks": chunk_results,
        "chunk_ids": chunk_ids
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
				import urllib.parse
				pdf_key = record['s3']['object']['key']
				# URL decode the PDF key to handle encoded characters like %2B (plus sign)
				pdf_key = urllib.parse.unquote(pdf_key)
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
