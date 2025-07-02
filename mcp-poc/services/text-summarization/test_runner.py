#!/usr/bin/env python3
"""
Simple test runner to validate pipeline implementation without external dependencies.
"""

import os
import sys
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work correctly with mocking"""
    print("Testing imports...")
    
    # Mock all external dependencies
    mock_modules = {
        'sentence_transformers': Mock(),
        'openai': Mock(),
        'transformers': Mock(),
        'torch': Mock(),
        'httpx': Mock(),
        'numpy': Mock()
    }
    
    with patch.dict('sys.modules', mock_modules):
        try:
            # Import models first (no external deps)
            from models import SummarizationRequest, SummarizationResponse
            print("✓ Models imported successfully")
            
            # Import config (has pydantic_settings dependency)
            try:
                from config import settings
                print("✓ Config imported successfully")
            except ImportError as e:
                print(f"⚠ Config import failed (expected): {e}")
            
            # Import pipeline with mocked dependencies
            from pipeline import SummarizationPipeline, ModelError, SemanticThresholdError
            print("✓ Pipeline imports successful")
            
            return True
            
        except Exception as e:
            print(f"✗ Import failed: {e}")
            return False

def test_model_validation():
    """Test the Pydantic model validation"""
    print("\nTesting model validation...")
    
    try:
        from models import SummarizationRequest
        
        # Test valid request
        request = SummarizationRequest(
            text_blob="This is a test text that meets the minimum requirements for summarization. " * 5,
            semantic_threshold=0.8,
            ai_model="openai"
        )
        
        assert request.text_blob is not None
        assert request.semantic_threshold == 0.8
        assert request.ai_model == "openai"
        assert request.retry_attempts == 3  # default value
        print("✓ Valid request created successfully")
        
        # Test invalid model type
        try:
            SummarizationRequest(
                text_blob="Valid text for testing purposes here with sufficient length.",
                ai_model="invalid_model"
            )
            print("✗ Should have failed with invalid model")
            return False
        except ValueError:
            print("✓ Invalid model validation works")
        
        return True
        
    except Exception as e:
        print(f"✗ Model validation failed: {e}")
        return False

async def test_pipeline_basic_structure():
    """Test pipeline class structure without external dependencies"""
    print("\nTesting pipeline structure...")
    
    # Mock all external dependencies at module level
    mock_modules = {
        'sentence_transformers': Mock(),
        'openai': Mock(), 
        'transformers': Mock(),
        'torch': Mock(),
        'httpx': Mock(),
        'numpy': Mock()
    }
    
    with patch.dict('sys.modules', mock_modules):
        try:
            from pipeline import SummarizationPipeline, ModelError
            
            # Mock the initialization to avoid loading real models
            with patch.object(SummarizationPipeline, '_initialize_models'):
                pipeline = SummarizationPipeline()
                
                # Check that required methods exist
                assert hasattr(pipeline, 'generate_summary'), "Missing generate_summary method"
                assert hasattr(pipeline, '_generate_with_model'), "Missing _generate_with_model method"
                assert hasattr(pipeline, '_generate_openai'), "Missing _generate_openai method"
                assert hasattr(pipeline, '_generate_huggingface'), "Missing _generate_huggingface method"
                assert hasattr(pipeline, '_generate_local'), "Missing _generate_local method"
                assert hasattr(pipeline, '_calculate_semantic_similarity'), "Missing _calculate_semantic_similarity method"
                
                print("✓ Pipeline has all required methods")
                
                # Test method signatures by inspecting them
                import inspect
                
                # Check generate_summary signature
                sig = inspect.signature(pipeline.generate_summary)
                assert 'request' in sig.parameters, "generate_summary missing request parameter"
                print("✓ generate_summary has correct signature")
                
                return True
                
        except Exception as e:
            print(f"✗ Pipeline structure test failed: {e}")
            return False

def test_error_classes():
    """Test custom error classes"""
    print("\nTesting error classes...")
    
    mock_modules = {
        'sentence_transformers': Mock(),
        'openai': Mock(),
        'transformers': Mock(), 
        'torch': Mock(),
        'httpx': Mock(),
        'numpy': Mock()
    }
    
    with patch.dict('sys.modules', mock_modules):
        try:
            from pipeline import ModelError, SemanticThresholdError
            
            # Test that errors can be raised and caught
            try:
                raise ModelError("Test error")
            except ModelError as e:
                assert str(e) == "Test error"
                print("✓ ModelError works correctly")
            
            try:
                raise SemanticThresholdError("Threshold error")
            except SemanticThresholdError as e:
                assert str(e) == "Threshold error"
                print("✓ SemanticThresholdError works correctly")
                
            return True
            
        except Exception as e:
            print(f"✗ Error class test failed: {e}")
            return False

async def test_pipeline_with_mocks():
    """Test pipeline functionality with fully mocked dependencies"""
    print("\nTesting pipeline with mocks...")
    
    mock_modules = {
        'sentence_transformers': Mock(),
        'openai': Mock(),
        'transformers': Mock(),
        'torch': Mock(), 
        'httpx': Mock(),
        'numpy': Mock()
    }
    
    with patch.dict('sys.modules', mock_modules):
        try:
            from pipeline import SummarizationPipeline, generate_summary
            from models import SummarizationRequest
            
            # Create mock pipeline
            with patch.object(SummarizationPipeline, '_initialize_models'):
                pipeline = SummarizationPipeline()
                
                # Mock the sentence transformer
                mock_st = Mock()
                mock_st.encode.return_value = Mock()  # Mock numpy array
                pipeline.sentence_transformer = mock_st
                
                # Mock similarity calculation to return high score
                with patch.object(pipeline, '_calculate_semantic_similarity', return_value=0.9):
                    # Mock model generation
                    with patch.object(pipeline, '_generate_openai', return_value="Test summary"):
                        
                        # Create test request
                        request = SummarizationRequest(
                            text_blob="This is a test text for summarization that meets length requirements. " * 3,
                            semantic_threshold=0.8
                        )
                        
                        # Test summary generation
                        response = await pipeline.generate_summary(request)
                        
                        assert response.refined_text == "Test summary"
                        assert response.semantic_score == 0.9
                        assert response.model_used == "openai"
                        
                        print("✓ Pipeline generates response correctly")
                        return True
                        
        except Exception as e:
            print(f"✗ Pipeline mock test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run all tests"""
    print("Running pipeline validation tests...\n")
    
    tests = [
        test_imports(),
        test_model_validation(),
        asyncio.run(test_pipeline_basic_structure()),
        test_error_classes(),
        asyncio.run(test_pipeline_with_mocks())
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Pipeline implementation is ready.")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
