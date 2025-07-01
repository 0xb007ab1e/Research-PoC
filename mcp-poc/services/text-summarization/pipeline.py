"""
Core summarization pipeline for the MCP Text Summarization Service.

Orchestrates model selection, retry loops with semantic validation,
semantic similarity scoring, and fallback mechanisms.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import openai
from transformers import pipeline as hf_pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from opentelemetry import trace

from models import SummarizationRequest, SummarizationResponse, ErrorResponse

# Handle missing config gracefully for testing
try:
    from config import settings
except ImportError:
    # Create a mock settings object for testing
    class MockSettings:
        class AIModels:
            sentence_transformer_model = "all-MiniLM-L6-v2"
            hf_model_name = "facebook/bart-large-cnn"
            openai_api_key = None
            openai_model = "gpt-3.5-turbo"
            openai_max_tokens = 1000
            hf_api_token = None
        
        ai_models = AIModels()
    
    settings = MockSettings()

logger = logging.getLogger(__name__)


class ModelError(Exception):
    """Custom exception for model-related errors"""
    pass


class SemanticThresholdError(Exception):
    """Exception raised when semantic threshold cannot be met"""
    pass


class SummarizationPipeline:
    """
    Core summarization pipeline that orchestrates model selection,
    retry logic, semantic validation, and fallback mechanisms.
    """
    
    def __init__(self):
        self.sentence_transformer = None
        self.local_model = None
        self.local_tokenizer = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize sentence transformer and local models"""
        try:
            # Initialize sentence transformer for semantic scoring
            model_name = settings.ai_models.sentence_transformer_model
            logger.info(f"Loading sentence transformer: {model_name}")
            self.sentence_transformer = SentenceTransformer(model_name)
            
            # Initialize local model as fallback
            self._initialize_local_model()
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise ModelError(f"Model initialization failed: {e}")
    
    def _initialize_local_model(self):
        """Initialize local Hugging Face model for fallback"""
        try:
            model_name = settings.ai_models.hf_model_name
            logger.info(f"Loading local model: {model_name}")
            
            # Use CPU if CUDA is not available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self.local_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.local_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self.local_model.to(device)
            
            logger.info(f"Local model loaded on device: {device}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize local model: {e}")
            # Continue without local model - will raise error if needed
    
    async def generate_summary(self, request: SummarizationRequest) -> SummarizationResponse:
        """
        Main entry point for text summarization.
        
        Args:
            request: SummarizationRequest containing text and parameters
            
        Returns:
            SummarizationResponse with summarized text and metadata
            
        Raises:
            SemanticThresholdError: If semantic threshold cannot be met
            ModelError: If all models fail
        """
        # Create OpenTelemetry span for the summarization
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("summarization.generate") as span:
            span.set_attribute("mcp.request_id", request.request_id or "unknown")
            span.set_attribute("mcp.model", request.ai_model)
            span.set_attribute("mcp.text_length", len(request.text_blob))
            span.set_attribute("mcp.semantic_threshold", request.semantic_threshold)
            
            start_time = time.time()
            original_length = len(request.text_blob)
            
            logger.info(
                f"Starting summarization for request {request.request_id}, "
                f"text length: {original_length}, model: {request.ai_model}"
            )
            
            # Track attempts and best result
            attempts = 0
            best_summary = ""
            best_score = 0.0
            model_used = request.ai_model
            warnings = []
            
            try:
                # Main retry loop
                while attempts < request.retry_attempts:
                    attempts += 1
                    
                    try:
                        # Generate summary using specified model
                        summary = await self._generate_with_model(
                            request.text_blob, 
                            request.ai_model,
                            request.api_token,
                            request.max_summary_length,
                            request.summary_ratio
                        )
                        
                        # Calculate semantic similarity
                        semantic_score = self._calculate_semantic_similarity(
                            request.text_blob, 
                            summary
                        )
                        
                        logger.info(
                            f"Attempt {attempts}: semantic score {semantic_score:.3f}, "
                            f"threshold {request.semantic_threshold}"
                        )
                        
                        # Track best result
                        if semantic_score > best_score:
                            best_summary = summary
                            best_score = semantic_score
                        
                        # Check if threshold is met
                        if semantic_score >= request.semantic_threshold:
                            break
                        
                        # If not met and we have more attempts, adjust parameters
                        if attempts < request.retry_attempts:
                            warnings.append(
                                f"Attempt {attempts}: semantic score {semantic_score:.3f} "
                                f"below threshold {request.semantic_threshold}"
                            )
                    
                    except ModelError as e:
                        logger.warning(f"Attempt {attempts} failed with model {request.ai_model}: {e}")
                    
                    # Try fallback to local model if external model failed
                    if request.ai_model != "local" and attempts == 1:
                        logger.info("Attempting fallback to local model")
                        try:
                            summary = await self._generate_with_model(
                                request.text_blob,
                                "local",
                                None,
                                request.max_summary_length,
                                request.summary_ratio
                            )
                            
                            semantic_score = self._calculate_semantic_similarity(
                                request.text_blob,
                                summary
                            )
                            
                            model_used = "local"
                            warnings.append(f"Fallback to local model due to {request.ai_model} failure")
                            
                            if semantic_score > best_score:
                                best_summary = summary
                                best_score = semantic_score
                            
                            if semantic_score >= request.semantic_threshold:
                                break
                                
                        except Exception as fallback_error:
                            logger.error(f"Fallback to local model failed: {fallback_error}")
                            warnings.append("Local model fallback failed")
                    
                    # If we're on the last attempt, re-raise
                    if attempts >= request.retry_attempts:
                        raise
            
                # Check final result
                if best_score < request.semantic_threshold:
                    error_msg = (
                        f"Failed to meet semantic threshold {request.semantic_threshold} "
                        f"after {attempts} attempts. Best score: {best_score:.3f}"
                    )
                    logger.error(error_msg)
                    span.set_attribute("mcp.error", "semantic_threshold_not_met")
                    raise SemanticThresholdError(error_msg)
                
                # Calculate response metrics
                processing_time_ms = int((time.time() - start_time) * 1000)
                summary_length = len(best_summary)
                compression_ratio = summary_length / original_length if original_length > 0 else 0
                
                # Set final span attributes
                span.set_attribute("mcp.final_score", best_score)
                span.set_attribute("mcp.attempts", attempts)
                span.set_attribute("mcp.model_used", model_used)
                span.set_attribute("mcp.processing_time_ms", processing_time_ms)
                span.set_attribute("mcp.compression_ratio", compression_ratio)
                
                # Build response
                response = SummarizationResponse(
                    refined_text=best_summary,
                    semantic_score=best_score,
                    request_id=request.request_id,
                    original_length=original_length,
                    summary_length=summary_length,
                    compression_ratio=compression_ratio,
                    processing_time_ms=processing_time_ms,
                    model_used=model_used,
                    retry_count=attempts - 1,
                    quality_metrics={
                        "semantic_similarity": best_score,
                        "compression_ratio": compression_ratio
                    },
                    status="success" if not warnings else "partial_success",
                    warnings=warnings
                )
                
                logger.info(
                    f"Summarization completed for request {request.request_id}: "
                    f"score {best_score:.3f}, attempts {attempts}"
                )
                
                return response
                
            except Exception as e:
                span.set_attribute("mcp.error", str(e))
                span.set_attribute("mcp.error_type", type(e).__name__)
                logger.error(f"Summarization failed for request {request.request_id}: {e}")
                raise
    
    async def _generate_with_model(
        self, 
        text: str, 
        model_type: str, 
        api_token: Optional[str],
        max_length: int,
        summary_ratio: float
    ) -> str:
        """Generate summary using specified model"""
        
        if model_type == "openai":
            return await self._generate_openai(text, api_token, max_length)
        elif model_type == "huggingface":
            return await self._generate_huggingface(text, api_token, max_length, summary_ratio)
        elif model_type == "local":
            return await self._generate_local(text, max_length, summary_ratio)
        else:
            raise ModelError(f"Unknown model type: {model_type}")
    
    async def _generate_openai(self, text: str, api_token: Optional[str], max_length: int) -> str:
        """Generate summary using OpenAI API"""
        try:
            # Use provided token or fall back to config
            api_key = api_token or settings.ai_models.openai_api_key
            if not api_key:
                raise ModelError("OpenAI API key not provided")
            
            client = openai.AsyncOpenAI(api_key=api_key)
            
            prompt = (
                f"Please provide a concise summary of the following text. "
                f"The summary should be no more than {max_length} characters and "
                f"should preserve the key information and meaning of the original text.\n\n"
                f"Text: {text}\n\nSummary:"
            )
            
            response = await client.chat.completions.create(
                model=settings.ai_models.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.ai_models.openai_max_tokens,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Truncate if necessary
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"OpenAI summarization failed: {e}")
            raise ModelError(f"OpenAI API error: {e}")
    
    async def _generate_huggingface(
        self, 
        text: str, 
        api_token: Optional[str], 
        max_length: int,
        summary_ratio: float
    ) -> str:
        """Generate summary using Hugging Face API"""
        try:
            import httpx
            
            api_url = f"https://api-inference.huggingface.co/models/{settings.ai_models.hf_model_name}"
            headers = {
                "Authorization": f"Bearer {api_token or settings.ai_models.hf_api_token}"
            }
            
            # Calculate target length
            target_length = min(int(len(text) * summary_ratio), max_length)
            
            payload = {
                "inputs": text,
                "parameters": {
                    "max_length": target_length,
                    "min_length": max(30, target_length // 4),
                    "do_sample": False
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    summary = result[0].get("summary_text", "")
                else:
                    raise ModelError("Invalid response format from Hugging Face API")
            
            if not summary:
                raise ModelError("Empty summary returned from Hugging Face API")
            
            # Truncate if necessary
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Hugging Face summarization failed: {e}")
            raise ModelError(f"Hugging Face API error: {e}")
    
    async def _generate_local(self, text: str, max_length: int, summary_ratio: float) -> str:
        """Generate summary using local model"""
        try:
            if not self.local_model or not self.local_tokenizer:
                raise ModelError("Local model not initialized")
            
            # Calculate target length
            target_length = min(int(len(text) * summary_ratio), max_length)
            
            # Tokenize input
            inputs = self.local_tokenizer.encode(
                text, 
                return_tensors="pt", 
                max_length=1024, 
                truncation=True
            )
            
            # Move to same device as model
            device = next(self.local_model.parameters()).device
            inputs = inputs.to(device)
            
            # Generate summary
            with torch.no_grad():
                summary_ids = self.local_model.generate(
                    inputs,
                    max_length=min(target_length // 4, 512),  # Token-based length
                    min_length=30,
                    num_beams=4,
                    length_penalty=2.0,
                    early_stopping=True
                )
            
            # Decode summary
            summary = self.local_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            
            # Truncate if necessary
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Local model summarization failed: {e}")
            raise ModelError(f"Local model error: {e}")
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts using sentence transformers"""
        try:
            if not self.sentence_transformer:
                raise ModelError("Sentence transformer not initialized")
            
            # Encode both texts
            embeddings = self.sentence_transformer.encode([text1, text2])
            
            # Calculate cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            
            # Ensure result is in [0, 1] range
            similarity = max(0.0, min(1.0, float(similarity)))
            
            return similarity
            
        except Exception as e:
            logger.error(f"Semantic similarity calculation failed: {e}")
            # Return a default score to avoid complete failure
            return 0.5


# Global pipeline instance
_pipeline_instance = None


def get_pipeline() -> SummarizationPipeline:
    """Get or create the global pipeline instance"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = SummarizationPipeline()
    return _pipeline_instance


async def generate_summary(request: SummarizationRequest) -> SummarizationResponse:
    """
    Main entry point for text summarization.
    
    Args:
        request: SummarizationRequest containing text and parameters
        
    Returns:
        SummarizationResponse with summarized text and metadata
    """
    pipeline = get_pipeline()
    return await pipeline.generate_summary(request)
