"""
Unit tests for Vision Agent

Note: These tests require Ollama with Qwen3.5:0.8b model installed.
Tests will skip if Ollama is not available.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
from datetime import datetime

from backend.agents.vision_agent import (
    VisionAgent,
    VisionAnalysisInput,
    OllamaConnectionError,
)
from backend.models.schemas import ExtractedImage, ImageAnalysis, VisionAnalysisInput, VisionAnalysisOutput
from backend.models.enums import ImageCategory


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_image(temp_dir):
    """Create a sample test image with patterns (not solid color)"""
    img_path = os.path.join(temp_dir, "test_image.jpg")
    
    # Create image with gradient/pattern for better vision analysis
    img = Image.new('RGB', (200, 200))
    for x in range(200):
        for y in range(200):
            # Create a colorful gradient pattern
            img.putpixel((x, y), (x, y, (x + y) % 256))
    
    img.save(img_path, 'JPEG')
    return img_path


@pytest.fixture
def extracted_image(sample_image):
    """Create ExtractedImage object for testing"""
    return ExtractedImage(
        image_id="test_img_001",
        file_path=sample_image,
        source_doc=None,
        source_page=None,
        width=200,
        height=200,
        file_size=os.path.getsize(sample_image),
        mime_type="image/jpeg",
        extraction_method="standalone",
        is_embedded=False,
        image_hash="test_hash_123",
        metadata={}
    )


@pytest.fixture
def agent():
    """Create Vision Agent instance"""
    try:
        return VisionAgent(timeout=30)
    except OllamaConnectionError:
        pytest.skip("Ollama not available - skipping vision agent tests")


def is_ollama_available() -> bool:
    """Check if Ollama is running and accessible"""
    try:
        from ollama import Client
        client = Client(host='http://localhost:11434', timeout=5)
        # Try to list models
        client.list()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not is_ollama_available(), reason="Ollama not available")
class TestVisionAgentWithOllama:
    """Test suite for Vision Agent with real Ollama connection"""
    
    def test_analyze_single_image(self, agent, extracted_image):
        """Test analyzing a single image"""
        input_data = VisionAnalysisInput(
            image=extracted_image,
            context="Test image for business digitization",
            job_id="test_job_001"
        )
        
        analysis = agent.analyze(input_data)
        
        assert analysis is not None
        assert analysis.image_id == extracted_image.image_id
        assert analysis.description is not None
        assert len(analysis.description) > 0
        assert analysis.category is not None
        assert isinstance(analysis.tags, list)
        assert analysis.confidence >= 0.0
        assert analysis.confidence <= 1.0
    
    def test_analyze_with_context(self, agent, extracted_image):
        """Test analysis with document context"""
        context = """
        Restaurant Menu
        - Burger with fries: $12
        - Pizza Margherita: $15
        - Caesar Salad: $10
        
        Our restaurant serves authentic Italian and American cuisine.
        """
        
        input_data = VisionAnalysisInput(
            image=extracted_image,
            context=context,
            job_id="test_job_002"
        )
        
        analysis = agent.analyze(input_data)
        
        assert analysis is not None
        # Context should influence the analysis
        assert 'model' in analysis.metadata
    
    def test_analyze_batch(self, agent, temp_dir):
        """Test batch image analysis"""
        # Create multiple test images
        images = []
        for i in range(3):
            img_path = os.path.join(temp_dir, f"batch_img_{i}.jpg")
            img = Image.new('RGB', (100, 100), color=(i*50, 100, 150))
            img.save(img_path, 'JPEG')
            
            extracted = ExtractedImage(
                image_id=f"batch_img_{i}",
                file_path=img_path,
                width=100,
                height=100,
                file_size=os.path.getsize(img_path),
                mime_type="image/jpeg",
                extraction_method="standalone",
                is_embedded=False,
                metadata={}
            )
            images.append(extracted)
        
        # Analyze batch
        results = agent.analyze_batch(images, context="Batch test")
        
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert result.image_id.startswith("batch_img_")
    
    def test_fallback_on_error(self, agent, temp_dir):
        """Test fallback analysis when model fails"""
        # Create invalid image path
        invalid_image = ExtractedImage(
            image_id="invalid_img",
            file_path="/nonexistent/path/image.jpg",
            width=100,
            height=100,
            file_size=0,
            mime_type="image/jpeg",
            extraction_method="standalone",
            is_embedded=False,
            metadata={}
        )
        
        input_data = VisionAnalysisInput(
            image=invalid_image,
            context="",
            job_id="test_job_error"
        )
        
        # Should return fallback analysis, not raise exception
        analysis = agent.analyze(input_data)
        
        assert analysis is not None
        assert analysis.image_id == "invalid_img"
        assert analysis.confidence == 0.0
        assert 'error' in analysis.metadata


class TestVisionAgentUnit:
    """Unit tests for Vision Agent (no Ollama required)"""
    
    def test_agent_initialization_without_ollama(self):
        """Test agent handles missing Ollama gracefully"""
        if is_ollama_available():
            pytest.skip("Ollama is available - testing with real connection instead")
        
        # Should raise OllamaConnectionError
        with pytest.raises(OllamaConnectionError):
            VisionAgent(timeout=5)
    
    def test_parse_valid_json_response(self, agent):
        """Test parsing valid JSON response"""
        valid_response = """
        {
            "description": "A delicious burger with lettuce and tomato",
            "category": "food",
            "tags": ["burger", "food", "restaurant"],
            "is_product": true,
            "is_service_related": false,
            "associations": ["menu item", "lunch special"],
            "confidence": 0.95
        }
        """
        
        parsed = agent._parse_response(valid_response)
        
        assert parsed['description'] == "A delicious burger with lettuce and tomato"
        assert parsed['category'] == "food"
        assert len(parsed['tags']) == 3
        assert parsed['is_product'] is True
        assert parsed['confidence'] == 0.95
    
    def test_parse_json_with_extra_text(self, agent):
        """Test parsing JSON with surrounding text"""
        response_with_text = """
        Here's my analysis:
        
        {
            "description": "Test description",
            "category": "product",
            "tags": ["test"],
            "is_product": true,
            "is_service_related": false,
            "associations": [],
            "confidence": 0.8
        }
        
        Hope this helps!
        """
        
        parsed = agent._parse_response(response_with_text)
        
        assert parsed['description'] == "Test description"
        assert parsed['category'] == "product"
    
    def test_parse_invalid_json_fallback(self, agent):
        """Test fallback for invalid JSON"""
        invalid_response = "This is not JSON at all"
        
        parsed = agent._parse_response(invalid_response)
        
        # Should return structured fallback
        assert 'description' in parsed
        assert parsed['category'] == 'other'
        assert parsed['confidence'] == 0.5
    
    def test_category_mapping(self, agent):
        """Test category string to enum mapping"""
        assert agent._map_category("product") == ImageCategory.PRODUCT
        assert agent._map_category("food") == ImageCategory.FOOD
        assert agent._map_category("service") == ImageCategory.SERVICE
        assert agent._map_category("destination") == ImageCategory.DESTINATION
        assert agent._map_category("person") == ImageCategory.PERSON
        assert agent._map_category("document") == ImageCategory.DOCUMENT
        assert agent._map_category("logo") == ImageCategory.LOGO
        assert agent._map_category("unknown") == ImageCategory.OTHER
        assert agent._map_category("other") == ImageCategory.OTHER
    
    def test_build_prompt_with_context(self, agent):
        """Test prompt building with context"""
        context = "Restaurant menu with burgers and pizzas"
        prompt = agent._build_prompt(context, "embedded_pdf")
        
        assert "Restaurant menu" in prompt
        assert "business digitization" in prompt
        assert "embedded in a business document" in prompt
    
    def test_build_prompt_without_context(self, agent):
        """Test prompt building without context"""
        prompt = agent._build_prompt("", "standalone")
        
        assert "business digitization" in prompt
        assert "JSON" in prompt
        assert "embedded" not in prompt
    
    def test_create_fallback_analysis(self, agent, extracted_image):
        """Test fallback analysis creation"""
        error_msg = "Test error message"
        
        fallback = agent._create_fallback_analysis(extracted_image, error_msg)
        
        assert fallback is not None
        assert fallback.image_id == extracted_image.image_id
        assert fallback.category == ImageCategory.OTHER
        assert fallback.confidence == 0.0
        assert error_msg in fallback.description
        assert fallback.metadata['error'] == error_msg
        assert fallback.metadata['fallback'] is True


class TestImageAnalysisSchema:
    """Test suite for ImageAnalysis schema"""
    
    def test_create_image_analysis(self):
        """Test creating ImageAnalysis object"""
        analysis = ImageAnalysis(
            image_id="test_001",
            description="A test image",
            category=ImageCategory.PRODUCT,
            tags=["test", "sample"],
            is_product=True,
            is_service_related=False,
            suggested_associations=["product A"],
            confidence=0.9,
            metadata={'model': 'qwen3.5:0.8b'}
        )
        
        assert analysis.image_id == "test_001"
        assert analysis.category == ImageCategory.PRODUCT
        assert len(analysis.tags) == 2
        assert analysis.is_product is True
        assert analysis.confidence == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
