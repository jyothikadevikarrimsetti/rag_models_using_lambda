"""
Response validation module for RAG system.
Provides various methods to validate the correctness and quality of generated responses.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../injestion/config/.env")

class ResponseValidator:
    def __init__(self):
        """Initialize the response validator with necessary models and clients."""
        # Load sentence transformer for semantic similarity
        try:
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except:
            self.sentence_model = None
            print("Warning: SentenceTransformer not available. Some validation features disabled.")
        
        # Initialize Azure OpenAI client for validation
        try:
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            )
            self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        except:
            self.client = None
            print("Warning: OpenAI client not available. Some validation features disabled.")

    def validate_response_grounding(self, response: str, source_documents: List[Dict], threshold: float = 0.7) -> Dict[str, Any]:
        """
        Validate if the response is grounded in the source documents.
        
        Args:
            response: Generated response text
            source_documents: List of retrieved documents
            threshold: Minimum similarity threshold for grounding validation
        
        Returns:
            Dictionary with grounding validation results
        """
        if not self.sentence_model or not source_documents:
            return {
                "is_grounded": False,
                "confidence": 0.0,
                "error": "Validation model not available or no source documents"
            }
        
        try:
            # Split response into sentences
            response_sentences = re.split(r'[.!?]+', response)
            response_sentences = [s.strip() for s in response_sentences if s.strip()]
            
            # Combine all source document content
            source_content = []
            for doc in source_documents:
                if 'chunk_text' in doc:
                    source_content.append(doc['chunk_text'])
                elif 'content' in doc:
                    source_content.append(doc['content'])
                elif 'summary' in doc:
                    source_content.append(doc['summary'])
            
            if not source_content:
                return {
                    "is_grounded": False,
                    "confidence": 0.0,
                    "error": "No content found in source documents"
                }
            
            # Calculate semantic similarity between response sentences and source content
            source_embeddings = self.sentence_model.encode(source_content)
            response_embeddings = self.sentence_model.encode(response_sentences)
            
            # Find maximum similarity for each response sentence
            grounded_sentences = 0
            similarity_scores = []
            
            for resp_emb in response_embeddings:
                max_similarity = 0
                for src_emb in source_embeddings:
                    similarity = np.dot(resp_emb, src_emb) / (np.linalg.norm(resp_emb) * np.linalg.norm(src_emb))
                    max_similarity = max(max_similarity, similarity)
                
                similarity_scores.append(max_similarity)
                if max_similarity >= threshold:
                    grounded_sentences += 1
            
            grounding_ratio = grounded_sentences / len(response_sentences) if response_sentences else 0
            avg_similarity = np.mean(similarity_scores) if similarity_scores else 0
            
            return {
                "is_grounded": grounding_ratio >= 0.6,  # At least 60% of sentences should be grounded
                "confidence": float(avg_similarity),
                "grounding_ratio": float(grounding_ratio),
                "grounded_sentences": grounded_sentences,
                "total_sentences": len(response_sentences),
                "similarity_scores": [float(s) for s in similarity_scores]
            }
            
        except Exception as e:
            return {
                "is_grounded": False,
                "confidence": 0.0,
                "error": f"Validation error: {str(e)}"
            }

    def validate_factual_consistency(self, response: str, source_documents: List[Dict]) -> Dict[str, Any]:
        """
        Use LLM to validate factual consistency between response and source documents.
        """
        if not self.client:
            return {
                "is_consistent": False,
                "confidence": 0.0,
                "error": "OpenAI client not available"
            }
        
        try:
            # Prepare source context
            source_context = "\n\n".join([
                doc.get('chunk_text', doc.get('content', doc.get('summary', '')))
                for doc in source_documents[:3]  # Use top 3 documents
            ])
            
            validation_prompt = f"""
You are a fact-checking expert. Compare the given response with the source documents and determine if the response is factually consistent.

SOURCE DOCUMENTS:
{source_context}

RESPONSE TO VALIDATE:
{response}

Analyze if the response contains any facts that contradict or are not supported by the source documents.

Respond in JSON format:
{{
    "is_consistent": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list", "of", "potential", "issues"],
    "explanation": "brief explanation of the assessment"
}}
"""
            
            result = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": validation_prompt}],
                temperature=0.1,
                max_tokens=500,
                timeout=30
            )
            
            # Parse JSON response
            import json
            validation_result = json.loads(result.choices[0].message.content.strip())
            return validation_result
            
        except Exception as e:
            return {
                "is_consistent": False,
                "confidence": 0.0,
                "error": f"Factual validation error: {str(e)}"
            }

    def calculate_retrieval_quality(self, query: str, retrieved_documents: List[Dict], top_k: int = 3) -> Dict[str, Any]:
        """
        Calculate quality metrics for the retrieval phase.
        """
        if not retrieved_documents:
            return {
                "retrieval_quality": 0.0,
                "coverage": 0.0,
                "relevance_scores": [],
                "error": "No documents retrieved"
            }
        
        try:
            # Calculate average retrieval score if available
            scores = []
            for doc in retrieved_documents:
                if 'score' in doc:
                    scores.append(doc['score'])
            
            avg_score = np.mean(scores) if scores else 0.0
            
            # Calculate coverage (how many of top_k positions are filled)
            coverage = len(retrieved_documents) / top_k if top_k > 0 else 0.0
            
            # Use semantic similarity if sentence transformer is available
            semantic_scores = []
            if self.sentence_model:
                query_embedding = self.sentence_model.encode([query])
                for doc in retrieved_documents:
                    doc_text = doc.get('chunk_text', doc.get('content', doc.get('summary', '')))
                    if doc_text:
                        doc_embedding = self.sentence_model.encode([doc_text])
                        similarity = np.dot(query_embedding[0], doc_embedding[0]) / (
                            np.linalg.norm(query_embedding[0]) * np.linalg.norm(doc_embedding[0])
                        )
                        semantic_scores.append(float(similarity))
            
            return {
                "retrieval_quality": float(avg_score),
                "coverage": float(coverage),
                "relevance_scores": scores,
                "semantic_scores": semantic_scores,
                "num_documents": len(retrieved_documents)
            }
            
        except Exception as e:
            return {
                "retrieval_quality": 0.0,
                "coverage": 0.0,
                "error": f"Retrieval quality calculation error: {str(e)}"
            }

    def comprehensive_validation(self, query: str, response: str, source_documents: List[Dict]) -> Dict[str, Any]:
        """
        Perform comprehensive validation combining multiple methods.
        """
        results = {
            "query": query,
            "response_length": len(response),
            "num_source_documents": len(source_documents),
            "timestamp": str(np.datetime64('now'))
        }
        
        # Grounding validation
        grounding_result = self.validate_response_grounding(response, source_documents)
        results["grounding"] = grounding_result
        
        # Factual consistency validation
        factual_result = self.validate_factual_consistency(response, source_documents)
        results["factual_consistency"] = factual_result
        
        # Retrieval quality
        retrieval_result = self.calculate_retrieval_quality(query, source_documents)
        results["retrieval_quality"] = retrieval_result
        
        # Overall quality score
        grounding_score = grounding_result.get("confidence", 0.0)
        factual_score = factual_result.get("confidence", 0.0) if factual_result.get("is_consistent", False) else 0.0
        retrieval_score = retrieval_result.get("retrieval_quality", 0.0)
        
        overall_score = (grounding_score * 0.4 + factual_score * 0.4 + retrieval_score * 0.2)
        
        results["overall_quality"] = {
            "score": float(overall_score),
            "is_high_quality": overall_score >= 0.7,
            "recommendation": "approve" if overall_score >= 0.7 else "review" if overall_score >= 0.5 else "reject"
        }
        
        return results

# Global validator instance
validator = ResponseValidator()

def validate_response(query: str, response: str, source_documents: List[Dict]) -> Dict[str, Any]:
    """
    Convenience function for response validation.
    """
    return validator.comprehensive_validation(query, response, source_documents)
