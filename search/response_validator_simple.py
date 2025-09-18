"""
Simplified response validation module for RAG system.
Uses basic text matching and OpenAI for validation without external ML libraries.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv("../injestion/config/.env")

class SimpleResponseValidator:
    def __init__(self):
        """Initialize the response validator with OpenAI client only."""
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

    def validate_response_grounding_simple(self, response: str, source_documents: List[Dict], threshold: float = 0.3) -> Dict[str, Any]:
        """
        Simple text-based grounding validation using keyword overlap.
        
        Args:
            response: Generated response text
            source_documents: List of retrieved documents
            threshold: Minimum overlap threshold for grounding validation
        
        Returns:
            Dictionary with grounding validation results
        """
        if not source_documents:
            return {
                "is_grounded": False,
                "confidence": 0.0,
                "error": "No source documents"
            }
        
        try:
            # Extract key terms from response (simple tokenization)
            response_words = set(re.findall(r'\b\w{3,}\b', response.lower()))
            response_words = {word for word in response_words if len(word) > 3}
            
            # Extract content from source documents
            source_content = []
            for doc in source_documents:
                if 'chunk_text' in doc:
                    source_content.append(doc['chunk_text'].lower())
                elif 'content' in doc:
                    source_content.append(doc['content'].lower())
                elif 'summary' in doc:
                    source_content.append(doc['summary'].lower())
            
            if not source_content:
                return {
                    "is_grounded": False,
                    "confidence": 0.0,
                    "error": "No content found in source documents"
                }
            
            # Combine all source content
            combined_source = " ".join(source_content)
            source_words = set(re.findall(r'\b\w{3,}\b', combined_source))
            
            # Calculate overlap with improved analysis
            if not response_words:
                overlap_ratio = 0.0
                overlapping_words = set()
                non_overlapping = set()
            else:
                overlapping_words = response_words.intersection(source_words)
                non_overlapping = response_words - source_words
                overlap_ratio = len(overlapping_words) / len(response_words)
            
            is_grounded = overlap_ratio >= threshold
            
            # Provide improvement suggestions
            suggestions = []
            if overlap_ratio < 0.5:
                suggestions.append("Response contains many terms not found in source documents")
                suggestions.append("Consider using more direct quotes from the source material")
            if len(non_overlapping) > 10:
                suggestions.append("Too many new terms introduced - stick closer to source content")
            
            return {
                "is_grounded": is_grounded,
                "confidence": float(overlap_ratio),
                "grounding_ratio": float(overlap_ratio),
                "overlapping_terms": len(overlapping_words),
                "non_overlapping_terms": len(non_overlapping),
                "improvement_suggestions": suggestions,
                "total_response_terms": len(response_words),
                "method": "simple_text_overlap"
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
                "is_consistent": True,  # Default to true if we can't validate
                "confidence": 0.5,
                "error": "OpenAI client not available",
                "method": "fallback"
            }
        
        try:
            # Prepare source context (limit to avoid token limits)
            source_context = "\n\n".join([
                doc.get('chunk_text', doc.get('content', doc.get('summary', '')))[:500]  # Limit each doc to 500 chars
                for doc in source_documents[:3]  # Use top 3 documents
            ])
            
            if len(source_context) > 2000:  # Further limit total context
                source_context = source_context[:2000] + "..."
            
            validation_prompt = f"""
You are a fact-checking expert. Compare the response with the source documents and determine if the response is factually consistent.

SOURCE DOCUMENTS:
{source_context}

RESPONSE TO VALIDATE:
{response}

Analyze if the response contains facts that contradict the source documents or makes claims not supported by them.

Respond in JSON format only:
{{
    "is_consistent": true,
    "confidence": 0.8,
    "issues": [],
    "explanation": "brief explanation"
}}
"""
            
            result = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": validation_prompt}],
                temperature=0.1,
                max_tokens=300,
                timeout=20
            )
            
            # Parse JSON response
            response_text = result.choices[0].message.content.strip()
            
            # Try to extract JSON
            try:
                validation_result = json.loads(response_text)
                validation_result["method"] = "llm_validation"
                return validation_result
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                is_consistent = "true" in response_text.lower() or "consistent" in response_text.lower()
                return {
                    "is_consistent": is_consistent,
                    "confidence": 0.6 if is_consistent else 0.4,
                    "explanation": "Parsed from non-JSON response",
                    "method": "llm_validation_fallback"
                }
            
        except Exception as e:
            logging.warning(f"Factual validation error: {e}")
            return {
                "is_consistent": True,  # Default to true on error
                "confidence": 0.5,
                "error": f"Factual validation error: {str(e)}",
                "method": "error_fallback"
            }

    def calculate_retrieval_quality(self, query: str, retrieved_documents: List[Dict], top_k: int = 3) -> Dict[str, Any]:
        """
        Calculate quality metrics for the retrieval phase using simple metrics.
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
            
            avg_score = sum(scores) / len(scores) if scores else 0.5  # Default to 0.5 if no scores
            
            # Calculate coverage (how many of top_k positions are filled)
            coverage = len(retrieved_documents) / top_k if top_k > 0 else 0.0
            
            # Simple relevance check based on query terms
            query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))
            relevance_scores = []
            
            for doc in retrieved_documents:
                doc_text = doc.get('chunk_text', doc.get('content', doc.get('summary', ''))).lower()
                doc_terms = set(re.findall(r'\b\w{3,}\b', doc_text))
                
                if query_terms and doc_terms:
                    overlap = len(query_terms.intersection(doc_terms))
                    relevance = overlap / len(query_terms)
                    relevance_scores.append(relevance)
                else:
                    relevance_scores.append(0.0)
            
            return {
                "retrieval_quality": float(avg_score),
                "coverage": float(coverage),
                "relevance_scores": scores,
                "simple_relevance_scores": relevance_scores,
                "num_documents": len(retrieved_documents),
                "method": "simple_metrics"
            }
            
        except Exception as e:
            return {
                "retrieval_quality": 0.5,  # Default score
                "coverage": 0.0,
                "error": f"Retrieval quality calculation error: {str(e)}"
            }

    def comprehensive_validation(self, query: str, response: str, source_documents: List[Dict]) -> Dict[str, Any]:
        """
        Perform comprehensive validation combining multiple simple methods.
        """
        import datetime
        
        results = {
            "query": query,
            "response_length": len(response),
            "num_source_documents": len(source_documents),
            "timestamp": datetime.datetime.now().isoformat(),
            "validation_method": "simple"
        }
        
        # Grounding validation
        grounding_result = self.validate_response_grounding_simple(response, source_documents)
        results["grounding"] = grounding_result
        
        # Factual consistency validation
        factual_result = self.validate_factual_consistency(response, source_documents)
        results["factual_consistency"] = factual_result
        
        # Retrieval quality
        retrieval_result = self.calculate_retrieval_quality(query, source_documents)
        results["retrieval_quality"] = retrieval_result
        
        # Overall quality score (simplified)
        grounding_score = grounding_result.get("confidence", 0.0)
        factual_score = factual_result.get("confidence", 0.5) if factual_result.get("is_consistent", True) else 0.0
        retrieval_score = retrieval_result.get("retrieval_quality", 0.5)
        
        # Weighted average
        overall_score = (grounding_score * 0.4 + factual_score * 0.4 + retrieval_score * 0.2)
        
        results["overall_quality"] = {
            "score": float(overall_score),
            "is_high_quality": overall_score >= 0.6,  # Lowered threshold for simple validation
            "recommendation": "approve" if overall_score >= 0.6 else "review" if overall_score >= 0.4 else "reject",
            "method": "simple_weighted_average"
        }
        
        return results

# Global validator instance
validator = SimpleResponseValidator()

def validate_response(query: str, response: str, source_documents: List[Dict]) -> Dict[str, Any]:
    """
    Convenience function for response validation using simple methods.
    """
    return validator.comprehensive_validation(query, response, source_documents)
