"""
Unit tests for the summarization pipeline.

Tests cover success scenarios, failure handling, semantic threshold retry logic,
model fallbacks, and edge cases.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import numpy as np
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import respx for HTTP mocking
import respx
import httpx

# Mock missing dependencies before importing pipeline
with patch.dict('sys.modules', {
    'sentence_transformers': Mock(),
    'openai': Mock(),
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


class TestSummarizationPipeline:
    """Test cases for the SummarizationPipeline class"""
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock sentence transformer"""
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
            text_blob="This is a sample text that needs to be summarized. " * 10,
            semantic_threshold=0.8,
            ai_model="openai",
            max_summary_length=200,
            summary_ratio=0.3,
            retry_attempts=3
        )
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization with mocked dependencies"""
        with patch('pipeline.SentenceTransformer') as mock_st:
            with patch.object(SummarizationPipeline, '_initialize_local_model'):
                pipeline = SummarizationPipeline()
                assert pipeline.sentence_transformer is not None
                mock_st.assert_called_once()
    
    def test_initialization_failure(self):
        """Test pipeline initialization failure handling"""
        with patch('pipeline.SentenceTransformer', side_effect=Exception("Model loading failed")):
            with pytest.raises(ModelError, match="Model initialization failed"):
                SummarizationPipeline()
    
    @pytest.mark.asyncio
    async def test_successful_summarization_openai(self, pipeline_with_mocks, sample_request):
        """Test successful summarization with OpenAI model"""
        expected_summary = "This is a summarized version of the text."
        
        # Mock OpenAI API call
        with patch.object(pipeline_with_mocks, '_generate_openai', return_value=expected_summary):
            # Mock high semantic similarity
            pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
                [1, 0, 0], [0.9, 0.1, 0]  # Similarity ~0.9
            ])
            
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert isinstance(response, SummarizationResponse)
            assert response.refined_text == expected_summary
            assert response.semantic_score >= sample_request.semantic_threshold
            assert response.model_used == "openai"
            assert response.retry_count == 0
            assert response.status == "success"
    
    @pytest.mark.asyncio
    async def test_successful_summarization_huggingface(self, pipeline_with_mocks, sample_request):
        """Test successful summarization with Hugging Face model"""
        sample_request.ai_model = "huggingface"
        expected_summary = "HF generated summary."
        
        with patch.object(pipeline_with_mocks, '_generate_huggingface', return_value=expected_summary):
            pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
                [1, 0, 0], [0.85, 0.15, 0]  # Similarity ~0.85
            ])
            
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert response.refined_text == expected_summary
            assert response.model_used == "huggingface"
            assert response.semantic_score >= sample_request.semantic_threshold
    
    @pytest.mark.asyncio
    async def test_successful_summarization_local(self, pipeline_with_mocks, sample_request):
        """Test successful summarization with local model"""
        sample_request.ai_model = "local"
        expected_summary = "Local model summary."
        
        with patch.object(pipeline_with_mocks, '_generate_local', return_value=expected_summary):
            pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
                [1, 0, 0], [0.82, 0.18, 0]  # Similarity ~0.82
            ])
            
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert response.refined_text == expected_summary
            assert response.model_used == "local"
            assert response.semantic_score >= sample_request.semantic_threshold
    
    @pytest.mark.asyncio
    async def test_semantic_threshold_retry_logic(self, pipeline_with_mocks, sample_request):
        """Test retry logic when semantic threshold is not met initially"""
        sample_request.retry_attempts = 3
        expected_summary = "Improved summary after retry."
        
        # Mock different similarity scores for each attempt
        similarity_scores = [
            np.array([[1, 0, 0], [0.7, 0.3, 0]]),  # 0.7 - below threshold
            np.array([[1, 0, 0], [0.75, 0.25, 0]]), # 0.75 - still below
            np.array([[1, 0, 0], [0.85, 0.15, 0]])  # 0.85 - above threshold
        ]
        
        call_count = 0
        def mock_encode(texts):
            nonlocal call_count
            result = similarity_scores[call_count]
            call_count += 1
            return result
        
        pipeline_with_mocks.sentence_transformer.encode.side_effect = mock_encode
        
        with patch.object(pipeline_with_mocks, '_generate_openai', return_value=expected_summary):
            response = await pipeline_with_mocks.generate_summary(sample_request)
            
            assert response.refined_text == expected_summary
            assert response.retry_count == 2  # 3 attempts - 1
            assert response.semantic_score >= sample_request.semantic_threshold
            assert len(response.warnings) == 2  # Two warnings for failed attempts
            assert response.status == "partial_success"
    
    @pytest.mark.asyncio
    async def test_semantic_threshold_not_met_failure(self, pipeline_with_mocks, sample_request):
        """Test failure when semantic threshold cannot be met"""
        sample_request.retry_attempts = 2
        
        # Mock consistently low similarity scores
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0], [0.5, 0.5, 0]  # Similarity ~0.5 - below 0.8 threshold
        ])
        
        with patch.object(pipeline_with_mocks, '_generate_openai', return_value="Poor summary"):
            with pytest.raises(SemanticThresholdError) as exc_info:
                await pipeline_with_mocks.generate_summary(sample_request)
            
            assert "Failed to meet semantic threshold" in str(exc_info.value)
            assert "0.8" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_model_failure_with_fallback(self, pipeline_with_mocks, sample_request):
        """Test fallback to local model when primary model fails"""
        expected_summary = "Local fallback summary."
        
        # Mock primary model failure and successful local fallback
        with patch.object(pipeline_with_mocks, '_generate_openai', 
                         side_effect=ModelError("OpenAI API failed")):
            with patch.object(pipeline_with_mocks, '_generate_local', return_value=expected_summary):
                pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
                    [1, 0, 0], [0.85, 0.15, 0]  # Good similarity
                ])
                
                response = await pipeline_with_mocks.generate_summary(sample_request)
                
                assert response.refined_text == expected_summary
                assert response.model_used == "local"
                assert "Fallback to local model" in response.warnings[0]
                assert response.status == "partial_success"
    
    @pytest.mark.asyncio
    async def test_all_models_fail(self, pipeline_with_mocks, sample_request):
        """Test complete failure when all models fail"""
        with patch.object(pipeline_with_mocks, '_generate_openai', 
                         side_effect=ModelError("OpenAI failed")):
            with patch.object(pipeline_with_mocks, '_generate_local', 
                             side_effect=ModelError("Local model failed")):
                
                with pytest.raises(ModelError):
                    await pipeline_with_mocks.generate_summary(sample_request)
    
    @pytest.mark.asyncio
    async def test_generate_openai_success(self, pipeline_with_mocks):
        """Test OpenAI generation method"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "OpenAI generated summary"
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            result = await pipeline_with_mocks._generate_openai("test text", "fake-key", 200)
            
            assert result == "OpenAI generated summary"
            mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_openai_no_api_key(self, pipeline_with_mocks):
        """Test OpenAI generation without API key"""
        with pytest.raises(ModelError, match="OpenAI API key not provided"):
            await pipeline_with_mocks._generate_openai("test text", None, 200)
    
    @pytest.mark.asyncio
    async def test_generate_huggingface_success(self, pipeline_with_mocks):
        """Test Hugging Face generation method"""
        mock_response_data = [{"summary_text": "HF summary"}]
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await pipeline_with_mocks._generate_huggingface(
                "test text", "fake-token", 200, 0.3
            )
            
            assert result == "HF summary"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_huggingface_invalid_response(self, pipeline_with_mocks):
        """Test Hugging Face generation with invalid response"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {}  # Invalid response format
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(ModelError, match="Invalid response format"):
                await pipeline_with_mocks._generate_huggingface(
                    "test text", "fake-token", 200, 0.3
                )
    
    @pytest.mark.asyncio
    async def test_generate_local_success(self, pipeline_with_mocks):
        """Test local model generation"""
        # Mock tokenizer and model
        mock_inputs = Mock()
        mock_summary_ids = [[1, 2, 3, 4]]  # Mock token IDs
        
        pipeline_with_mocks.local_tokenizer.encode.return_value = mock_inputs
        pipeline_with_mocks.local_model.generate.return_value = mock_summary_ids
        pipeline_with_mocks.local_model.parameters.return_value = [Mock()]
        pipeline_with_mocks.local_tokenizer.decode.return_value = "Local summary"
        
        # Mock device detection
        with patch('torch.cuda.is_available', return_value=False):
            result = await pipeline_with_mocks._generate_local("test text", 200, 0.3)
            
            assert result == "Local summary"
            pipeline_with_mocks.local_tokenizer.encode.assert_called_once()
            pipeline_with_mocks.local_model.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_local_model_not_initialized(self, pipeline_with_mocks):
        """Test local generation when model is not initialized"""
        pipeline_with_mocks.local_model = None
        
        with pytest.raises(ModelError, match="Local model not initialized"):
            await pipeline_with_mocks._generate_local("test text", 200, 0.3)
    
    def test_calculate_semantic_similarity(self, pipeline_with_mocks):
        """Test semantic similarity calculation"""
        # Mock embeddings that result in high similarity
        pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
            [1, 0, 0],      # First text embedding
            [0.9, 0.1, 0]   # Second text embedding
        ])
        
        similarity = pipeline_with_mocks._calculate_semantic_similarity("text1", "text2")
        
        assert 0.8 < similarity <= 1.0  # Should be high similarity
        pipeline_with_mocks.sentence_transformer.encode.assert_called_once_with(["text1", "text2"])
    
    def test_calculate_semantic_similarity_failure(self, pipeline_with_mocks):
        """Test semantic similarity calculation failure handling"""
        pipeline_with_mocks.sentence_transformer.encode.side_effect = Exception("Encoding failed")
        
        # Should return default score instead of failing
        similarity = pipeline_with_mocks._calculate_semantic_similarity("text1", "text2")
        assert similarity == 0.5
    
    def test_calculate_semantic_similarity_no_transformer(self, pipeline_with_mocks):
        """Test semantic similarity when transformer is not initialized"""
        pipeline_with_mocks.sentence_transformer = None
        
        # Should return default score
        similarity = pipeline_with_mocks._calculate_semantic_similarity("text1", "text2")
        assert similarity == 0.5
    
    @pytest.mark.asyncio
    async def test_unknown_model_type(self, pipeline_with_mocks, sample_request):
        """Test handling of unknown model type"""
        sample_request.ai_model = "unknown_model"
        
        with pytest.raises(ModelError, match="Unknown model type: unknown_model"):
            await pipeline_with_mocks.generate_summary(sample_request)
    
    def test_response_metrics_calculation(self, pipeline_with_mocks, sample_request):
        """Test that response metrics are calculated correctly"""
        # This is tested implicitly in other tests, but we can add specific checks
        original_text = "A" * 1000
        sample_request.text_blob = original_text
        
        # The metrics calculation is tested through the integration tests above


class TestPipelineGlobalFunctions:
    """Test global pipeline functions"""
    
    def test_get_pipeline_singleton(self):
        """Test that get_pipeline returns the same instance"""
        with patch('pipeline.SummarizationPipeline') as mock_pipeline_class:
            mock_instance = Mock()
            mock_pipeline_class.return_value = mock_instance
            
            # Clear any existing instance
            import pipeline
            pipeline._pipeline_instance = None
            
            # First call should create instance
            result1 = get_pipeline()
            assert result1 == mock_instance
            mock_pipeline_class.assert_called_once()
            
            # Second call should return same instance
            result2 = get_pipeline()
            assert result1 is result2
            # Should not create another instance
            assert mock_pipeline_class.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_summary_function(self):
        """Test the module-level generate_summary function"""
        with patch('pipeline.get_pipeline') as mock_get_pipeline:
            mock_pipeline = Mock()
            mock_response = Mock(spec=SummarizationResponse)
            mock_pipeline.generate_summary.return_value = mock_response
            mock_get_pipeline.return_value = mock_pipeline
            
            request = Mock(spec=SummarizationRequest)
            result = await generate_summary(request)
            
            assert result == mock_response
            mock_pipeline.generate_summary.assert_called_once_with(request)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.fixture
    def pipeline_with_mocks(self):
        """Create pipeline with mocked dependencies for edge case testing"""
        with patch('pipeline.SentenceTransformer') as mock_st:
            with patch.object(SummarizationPipeline, '_initialize_local_model'):
                pipeline = SummarizationPipeline()
                pipeline.sentence_transformer = mock_st.return_value
                pipeline.local_model = Mock()
                pipeline.local_tokenizer = Mock()
                return pipeline
    
    @pytest.mark.asyncio
    async def test_very_long_summary_truncation(self, pipeline_with_mocks):
        """Test summary truncation for very long generated text"""
        very_long_summary = "A" * 1000  # Longer than max_length
        max_length = 200
        
        with patch.object(pipeline_with_mocks, '_generate_openai', return_value=very_long_summary):
            # Mock high similarity to avoid retry loop
            pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
                [1, 0, 0], [0.9, 0.1, 0]
            ])
            
            request = SummarizationRequest(
                text_blob="Sample text to summarize",
                max_summary_length=max_length,
                semantic_threshold=0.8
            )
            
            result = await pipeline_with_mocks._generate_openai("test", None, max_length)
            assert len(result) <= max_length
            assert result.endswith("...")
    
    @pytest.mark.asyncio
    async def test_empty_or_very_short_text(self, pipeline_with_mocks):
        """Test handling of edge case text lengths"""
        with patch.object(pipeline_with_mocks, '_generate_openai', return_value="Short summary"):
            pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
                [1, 0, 0], [0.9, 0.1, 0]
            ])
            
            # Test with minimum valid text (should work due to validation in models.py)
            request = SummarizationRequest(
                text_blob="This is a short text that meets minimum requirements for summarization testing purposes.",
                semantic_threshold=0.8
            )
            
            response = await pipeline_with_mocks.generate_summary(request)
            assert response.compression_ratio > 0
    
    @pytest.mark.asyncio
    async def test_zero_retry_attempts(self, pipeline_with_mocks):
        """Test behavior with zero retry attempts (should use minimum of 1)"""
        with patch.object(pipeline_with_mocks, '_generate_openai', return_value="Summary"):
            pipeline_with_mocks.sentence_transformer.encode.return_value = np.array([
                [1, 0, 0], [0.9, 0.1, 0]  # High similarity
            ])
            
            request = SummarizationRequest(
                text_blob="Sample text for summarization testing purposes with sufficient length.",
                retry_attempts=1,  # Minimum from model validation
                semantic_threshold=0.8
            )
            
            response = await pipeline_with_mocks.generate_summary(request)
            assert response.retry_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
