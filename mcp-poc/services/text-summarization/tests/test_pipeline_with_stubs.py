"""
Enhanced tests for the summarization pipeline with OpenAI API stubs using respx.

Tests cover real HTTP interactions with mocked external services.
"""

import pytest
import asyncio
import respx
import httpx
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import json
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies before importing pipeline
with patch.dict('sys.modules', {
    'sentence_transformers': Mock(),
    'transformers': Mock(),
    'torch': Mock(),
}):
    from pipeline import (
        SummarizationPipeline, 
        ModelError, 
        SemanticThresholdError,
        generate_summary,
        get_pipeline
    )
    from models import SummarizationRequest, SummarizationResponse


class TestSummarizationPipelineWithStubs:
    """Test cases using respx to mock external API calls"""
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock sentence transformer for similarity calculation"""
        mock = Mock()
        mock.encode.return_value = np.array([[1, 0, 0], [0.9, 0.1, 0]])  # High similarity
        return mock
    
    @pytest.fixture
    def pipeline_with_mocks(self, mock_sentence_transformer):
        """Create pipeline instance with mocked dependencies"""
        with patch('pipeline.SentenceTransformer', return_value=mock_sentence_transformer):
            with patch.object(SummarizationPipeline, '_initialize_local_model'):
                pipeline = SummarizationPipeline()
                pipeline.sentence_transformer = mock_sentence_transformer
                pipeline.local_model = Mock()
                pipeline.local_tokenizer = Mock()
                return pipeline
    
    @pytest.fixture
    def sample_request(self):
        """Create a sample summarization request"""
        return SummarizationRequest(
            text_blob="This is a comprehensive sample text that needs to be summarized for testing purposes. " * 10,
            semantic_threshold=0.8,
            ai_model="openai",
            api_token="sk-test-token-123",
            max_summary_length=200,
            summary_ratio=0.3,
            retry_attempts=3
        )
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_openai_api_success_with_stub(self, pipeline_with_mocks, sample_request):
        """Test successful OpenAI API call using respx stub"""
        # Mock OpenAI API response
        openai_response = {
            "choices": [
                {
                    "message": {
                        "content": "This is a comprehensive summary of the provided text, capturing the key points and main ideas."
                    }
                }
            ]
        }
        
        # Create respx route for OpenAI API
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=openai_response)
        )
        
        # Mock high semantic similarity
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0], [0.9, 0.1, 0]  # Similarity ~0.9
        ])
        
        response = await pipeline_with_mocks.generate_summary(sample_request)
        
        assert isinstance(response, SummarizationResponse)
        assert "comprehensive summary" in response.refined_text.lower()
        assert response.semantic_score >= sample_request.semantic_threshold
        assert response.model_used == "openai"
        assert response.status == "success"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_openai_api_error_with_fallback(self, pipeline_with_mocks, sample_request):
        """Test OpenAI API error handling with fallback to local model"""
        # Mock OpenAI API error
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(500, json={"error": "Internal server error"})
        )
        
        # Mock successful local model generation
        pipeline_with_mocks.local_tokenizer.encode.return_value = Mock()
        pipeline_with_mocks.local_model.generate.return_value = [[1, 2, 3, 4]]
        pipeline_with_mocks.local_model.parameters.return_value = [Mock()]
        pipeline_with_mocks.local_tokenizer.decode.return_value = "Local fallback summary"
        
        # Mock high semantic similarity for local result
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0], [0.85, 0.15, 0]  # Good similarity
        ])
        
        with patch('torch.cuda.is_available', return_value=False):
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert response.refined_text == "Local fallback summary"
            assert response.model_used == "local"
            assert response.status == "partial_success"
            assert any("fallback" in warning.lower() for warning in response.warnings)
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_huggingface_api_success_with_stub(self, pipeline_with_mocks, sample_request):
        """Test successful Hugging Face API call using respx stub"""
        sample_request.ai_model = "huggingface"
        
        # Mock Hugging Face API response
        hf_response = [
            {"summary_text": "AI-generated summary from Hugging Face model"}
        ]
        
        # Create respx route for Hugging Face API
        respx.post("https://api-inference.huggingface.co/models/facebook/bart-large-cnn").mock(
            return_value=httpx.Response(200, json=hf_response)
        )
        
        # Mock high semantic similarity
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0], [0.88, 0.12, 0]  # Similarity ~0.88
        ])
        
        response = await pipeline_with_mocks.generate_summary(sample_request)
        
        assert isinstance(response, SummarizationResponse)
        assert response.refined_text == "AI-generated summary from Hugging Face model"
        assert response.model_used == "huggingface"
        assert response.semantic_score >= sample_request.semantic_threshold
        assert response.status == "success"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_huggingface_api_rate_limit_error(self, pipeline_with_mocks, sample_request):
        """Test Hugging Face API rate limit handling"""
        sample_request.ai_model = "huggingface"
        
        # Mock rate limit response
        respx.post("https://api-inference.huggingface.co/models/facebook/bart-large-cnn").mock(
            return_value=httpx.Response(429, json={"error": "Rate limit exceeded"})
        )
        
        # Mock successful local fallback
        pipeline_with_mocks.local_tokenizer.encode.return_value = Mock()
        pipeline_with_mocks.local_model.generate.return_value = [[1, 2, 3, 4]]
        pipeline_with_mocks.local_model.parameters.return_value = [Mock()]
        pipeline_with_mocks.local_tokenizer.decode.return_value = "Rate limit fallback summary"
        
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0], [0.83, 0.17, 0]  # Good similarity
        ])
        
        with patch('torch.cuda.is_available', return_value=False):
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert response.refined_text == "Rate limit fallback summary"
            assert response.model_used == "local"
            assert response.status == "partial_success"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_semantic_threshold_retry_with_real_api(self, pipeline_with_mocks, sample_request):
        """Test retry logic with progressively better API responses"""
        sample_request.retry_attempts = 3
        
        # Mock API responses that get progressively better
        api_responses = [
            {"choices": [{"message": {"content": "Poor quality summary"}}]},
            {"choices": [{"message": {"content": "Mediocre summary of the content"}}]},
            {"choices": [{"message": {"content": "High quality comprehensive summary with excellent semantic alignment to the original text"}}]},
        ]
        
        call_count = 0
        def mock_openai_response(request):
            nonlocal call_count
            response = api_responses[call_count]
            call_count += 1
            return httpx.Response(200, json=response)
        
        respx.post("https://api.openai.com/v1/chat/completions").mock(side_effect=mock_openai_response)
        
        # Mock similarity scores that improve with better summaries
        similarity_scores = [
            np.array([[1, 0, 0], [0.7, 0.3, 0]]),    # 0.7 - below threshold
            np.array([[1, 0, 0], [0.75, 0.25, 0]]),  # 0.75 - still below
            np.array([[1, 0, 0], [0.92, 0.08, 0]])   # 0.92 - above threshold
        ]
        
        similarity_call_count = 0
        def mock_encode(texts):
            nonlocal similarity_call_count
            result = similarity_scores[similarity_call_count]
            similarity_call_count += 1
            return result
        
        pipeline_with_mocks.sentence_transformer.encode.side_effect = mock_encode
        
        response = await pipeline_with_mocks.generate_summary(sample_request)
        
        assert "comprehensive summary" in response.refined_text.lower()
        assert response.retry_count == 2  # Two retries (3 attempts - 1)
        assert response.semantic_score >= sample_request.semantic_threshold
        assert response.status == "partial_success"  # Due to retries
        assert len(response.warnings) == 2  # Two warnings for failed attempts
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_network_timeout_handling(self, pipeline_with_mocks, sample_request):
        """Test handling of network timeouts"""
        # Mock timeout error
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )
        
        # Mock successful local fallback
        pipeline_with_mocks.local_tokenizer.encode.return_value = Mock()
        pipeline_with_mocks.local_model.generate.return_value = [[1, 2, 3, 4]]
        pipeline_with_mocks.local_model.parameters.return_value = [Mock()]
        pipeline_with_mocks.local_tokenizer.decode.return_value = "Timeout fallback summary"
        
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0], [0.84, 0.16, 0]  # Good similarity
        ])
        
        with patch('torch.cuda.is_available', return_value=False):
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert response.refined_text == "Timeout fallback summary"
            assert response.model_used == "local"
            assert response.status == "partial_success"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_api_authentication_error(self, pipeline_with_mocks, sample_request):
        """Test handling of API authentication errors"""
        # Mock authentication error
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(401, json={"error": "Invalid API key"})
        )
        
        # Should fallback to local model
        pipeline_with_mocks.local_tokenizer.encode.return_value = Mock()
        pipeline_with_mocks.local_model.generate.return_value = [[1, 2, 3, 4]]
        pipeline_with_mocks.local_model.parameters.return_value = [Mock()]
        pipeline_with_mocks.local_tokenizer.decode.return_value = "Auth error fallback summary"
        
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0], [0.86, 0.14, 0]  # Good similarity
        ])
        
        with patch('torch.cuda.is_available', return_value=False):
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert response.refined_text == "Auth error fallback summary"
            assert response.model_used == "local"
            assert response.status == "partial_success"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_malformed_api_response(self, pipeline_with_mocks, sample_request):
        """Test handling of malformed API responses"""
        # Mock malformed response
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"invalid": "response"})
        )
        
        # Should fallback to local model
        pipeline_with_mocks.local_tokenizer.encode.return_value = Mock()
        pipeline_with_mocks.local_model.generate.return_value = [[1, 2, 3, 4]]
        pipeline_with_mocks.local_model.parameters.return_value = [Mock()]
        pipeline_with_mocks.local_tokenizer.decode.return_value = "Malformed response fallback"
        
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0], [0.87, 0.13, 0]  # Good similarity
        ])
        
        with patch('torch.cuda.is_available', return_value=False):
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert response.refined_text == "Malformed response fallback"
            assert response.model_used == "local"
            assert response.status == "partial_success"


class TestPipelineIntegrationWithMocks:
    """Integration tests that combine multiple components with mocked external services"""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_full_pipeline_with_multiple_models(self):
        """Test complete pipeline flow with multiple model attempts"""
        request = SummarizationRequest(
            text_blob="Integration test text that requires comprehensive summarization to validate the complete pipeline flow. " * 15,
            semantic_threshold=0.85,
            ai_model="openai",
            api_token="sk-test-token",
            max_summary_length=300,
            retry_attempts=3
        )
        
        # Mock OpenAI success
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": "Comprehensive integration test summary that meets high semantic similarity requirements"}}]
            })
        )
        
        with patch('pipeline.SentenceTransformer') as mock_st:
            mock_transformer = Mock()
            # Mock very high similarity to ensure success
            mock_transformer.encode.return_value = np.array([
                [1, 0, 0], [0.95, 0.05, 0]  # Very high similarity
            ])
            mock_st.return_value = mock_transformer
            
            with patch.object(SummarizationPipeline, '_initialize_local_model'):
                pipeline = SummarizationPipeline()
                pipeline.sentence_transformer = mock_transformer
                
                response = await pipeline.generate_summary(request)
                
                assert isinstance(response, SummarizationResponse)
                assert "integration test summary" in response.refined_text.lower()
                assert response.semantic_score >= request.semantic_threshold
                assert response.model_used == "openai"
                assert response.status == "success"
                assert response.retry_count == 0
                assert response.processing_time_ms > 0
                assert response.compression_ratio < 1.0
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_complete_failure_scenario(self):
        """Test scenario where all models fail"""
        request = SummarizationRequest(
            text_blob="Test text for complete failure scenario. " * 10,
            semantic_threshold=0.8,
            ai_model="openai",
            api_token="sk-test-token",
            retry_attempts=1
        )
        
        # Mock OpenAI failure
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )
        
        with patch('pipeline.SentenceTransformer') as mock_st:
            mock_transformer = Mock()
            mock_st.return_value = mock_transformer
            
            with patch.object(SummarizationPipeline, '_initialize_local_model'):
                pipeline = SummarizationPipeline()
                pipeline.sentence_transformer = mock_transformer
                pipeline.local_model = None  # Simulate local model failure
                
                with pytest.raises(ModelError, match="All available models failed"):
                    await pipeline.generate_summary(request)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
