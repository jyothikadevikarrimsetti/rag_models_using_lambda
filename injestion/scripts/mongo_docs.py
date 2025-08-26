from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import tiktoken
import concurrent.futures
import logging

load_dotenv("config/.env")
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Helper functions for embeddings and similarity
def get_openai_embedding(text, timeout=15):
    """Get embeddings using Azure OpenAI's text-embedding model with context window truncation and timeout."""
    # Truncate text to fit within model context window (e.g., 8000 tokens for text-embedding-3-small)
    max_tokens = 8000
    encoding = tiktoken.encoding_for_model("text-embedding-3-small")
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        text = encoding.decode(tokens)
    def call():
        return client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        ).data[0].embedding
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(call)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logging.error(f"OpenAI embedding call timed out for text: {text[:50]}")
            raise TimeoutError("OpenAI embedding call timed out.")

def summarize_text(text):
    # Truncate text to fit within LLM context window (e.g., 8000 tokens for GPT-4o)
    max_tokens = 8000
    encoding = tiktoken.encoding_for_model("gpt-4o")
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        text = encoding.decode(tokens)
    summary_prompt = (
        "Summarize the following text in 1-2 sentences. "
        "Be extremely concise and do not include bullets or extra details. "
        "Text: {text}"
    )
    summary = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": summary_prompt.format(text=text)}],
        max_tokens=256,
        temperature=0.2
    )
    return summary.choices[0].message.content.strip()

def extract_keywords_and_entities(text):
    """Extract keywords and entities using Azure OpenAI - simplified version."""
    # Return empty defaults since no NLP/NER models are being used
    return {
        "keywords": [],
        "entities": [],
        "intent": "",
        "topic": ""
    }


def build_document(summary, doc_emb, text, document_name=None):
    document = {
        "summary": summary,
        "embedding": doc_emb,
        "text": text
    }
    if document_name:
        document["document_name"] = document_name
    return document


def extract_metadata(text, document_name=None):
    doc_emb = get_openai_embedding(text)
    summary = summarize_text(text)
    extraction_data = extract_keywords_and_entities(text)
    
    metadata = build_document(summary, doc_emb, text, document_name)
    metadata.update({
        "keywords": extraction_data.get("keywords", []),
        "entities": extraction_data.get("entities", []),
        "intent": extraction_data.get("intent", ""),
        "topic": extraction_data.get("topic", ""),
        "model_name": "gpt-4o"
    })
    
    return metadata
