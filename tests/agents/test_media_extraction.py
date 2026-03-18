"""
Unit tests for Media Extraction Agent
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import io

from backend.agents.media_extraction import (
    MediaExtractionAgent,
    MediaExtractionInput,
    ImageUtils,
)
from backend.models.schemas import (
    ParsedDocument,
    Page,
    DocumentMetadata,
    ExtractedImage,
    MediaCollection,
)
from backend.models.enums import FileType


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def agent(temp_dir):
    """Create media extraction agent"""
    output_dir = os.path.join(temp_dir, "media")
    return MediaExtractionAgent(
        enable_deduplication=True,
        output_dir=output_dir
    )


@pytest.fixture
def sample_image(temp_dir):
    """Create a sample test image"""
    img_path = os.path.join(temp_dir, "test_image.jpg")
    
    # Create simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path, 'JPEG')
    
    return img_path


@pytest.fixture
def sample_pdf_with_images(temp_dir, sample_image):
    """Create a mock parsed PDF document"""
    # Note: We can't easily create a real PDF with embedded images in tests
    # So we create a mock ParsedDocument that simulates one
    return ParsedDocument(
        doc_id="test_pdf_001",
        source_file=sample_image,  # Using image as placeholder
        file_type=FileType.PDF,
        pages=[
            Page(
                number=1,
                text="Test document with images",
                tables=[],
                images=[
                    {
                        'xref': 5,
                        'width': 100,
                        'height': 100,
                        'bbox': (0, 0, 100, 100)
                    }
                ],
                metadata={}
            )
        ],
        total_pages=1,
        metadata=DocumentMetadata(page_count=1, file_size=1024),
        parsing_errors=[]
    )


@pytest.fixture
def sample_docx_with_images(temp_dir, sample_image):
    """Create a mock parsed DOCX document"""
    return ParsedDocument(
        doc_id="test_docx_001",
        source_file=sample_image,  # Using image as placeholder
        file_type=FileType.DOCX,
        pages=[
            Page(
                number=1,
                text="Test DOCX with images",
                tables=[],
                images=[],
                metadata={}
            )
        ],
        total_pages=1,
        metadata=DocumentMetadata(page_count=1, file_size=1024),
        parsing_errors=[]
    )


class TestMediaExtractionAgent:
    """Test suite for MediaExtractionAgent"""
    
    def test_extract_from_standalone_files(self, agent, sample_image):
        """Test extraction from standalone image files"""
        input_data = MediaExtractionInput(
            parsed_documents=[],
            standalone_files=[sample_image],
            job_id="test_job_standalone"
        )
        
        output = agent.extract_all(input_data)
        
        assert output.success is True
        assert output.total_images == 1
        assert len(output.media.images) == 1
        
        image = output.media.images[0]
        assert image.width == 100
        assert image.height == 100
        assert image.mime_type == "image/jpg"
        assert image.extraction_method == "standalone"
        assert image.is_embedded is False
    
    def test_extract_empty_input(self, agent):
        """Test extraction with empty input"""
        input_data = MediaExtractionInput(
            parsed_documents=[],
            standalone_files=[],
            job_id="test_job_empty"
        )
        
        output = agent.extract_all(input_data)
        
        assert output.success is False
        assert output.total_images == 0
        assert len(output.media.images) == 0
    
    def test_deduplication(self, agent, sample_image, temp_dir):
        """Test image deduplication"""
        # Create duplicate image
        duplicate_path = os.path.join(temp_dir, "duplicate.jpg")
        img = Image.new('RGB', (100, 100), color='red')
        img.save(duplicate_path, 'JPEG')
        
        input_data = MediaExtractionInput(
            parsed_documents=[],
            standalone_files=[sample_image, duplicate_path],
            job_id="test_job_dedup"
        )
        
        output = agent.extract_all(input_data)
        
        # Should have removed duplicate
        assert output.total_images == 1
        assert output.duplicates_removed == 1
    
    def test_processing_time_recorded(self, agent, sample_image):
        """Test that processing time is recorded"""
        input_data = MediaExtractionInput(
            parsed_documents=[],
            standalone_files=[sample_image],
            job_id="test_job_time"
        )
        
        output = agent.extract_all(input_data)
        
        assert output.processing_time > 0
        assert output.processing_time < 60  # Should be fast
    
    def test_image_metadata(self, agent, sample_image):
        """Test image metadata extraction"""
        input_data = MediaExtractionInput(
            parsed_documents=[],
            standalone_files=[sample_image],
            job_id="test_job_metadata"
        )
        
        output = agent.extract_all(input_data)
        
        assert len(output.media.images) == 1
        image = output.media.images[0]
        
        assert image.image_id is not None
        assert image.file_path is not None
        assert image.width > 0
        assert image.height > 0
        assert image.file_size > 0
        assert image.image_hash is not None
    
    def test_quality_assessment(self, agent, sample_image):
        """Test image quality assessment"""
        input_data = MediaExtractionInput(
            parsed_documents=[],
            standalone_files=[sample_image],
            job_id="test_job_quality"
        )
        
        output = agent.extract_all(input_data)
        
        assert len(output.media.images) == 1
        image = output.media.images[0]
        
        # Quality score should be in metadata
        assert 'quality_score' in image.metadata
        assert image.metadata['quality_score'] >= 0.0
        assert image.metadata['quality_score'] <= 1.0


class TestImageUtils:
    """Test suite for ImageUtils"""
    
    def test_calculate_hash(self, sample_image):
        """Test perceptual hash calculation"""
        utils = ImageUtils()
        
        with open(sample_image, 'rb') as f:
            image_bytes = f.read()
        
        img_hash = utils.calculate_hash(image_bytes)
        
        assert img_hash is not None
        assert len(img_hash) > 0
        
        # Same image should produce same hash
        hash2 = utils.calculate_hash(image_bytes)
        assert img_hash == hash2
    
    def test_assess_quality_high_res(self, temp_dir):
        """Test quality assessment for high resolution image"""
        utils = ImageUtils()
        
        # Create high-res image (1920x1080)
        img_path = os.path.join(temp_dir, "high_res.jpg")
        img = Image.new('RGB', (1920, 1080), color='blue')
        img.save(img_path, 'JPEG')
        
        quality = utils.assess_quality(img_path)
        
        assert quality['resolution'] == 'high'
        assert quality['score'] >= 0.9
        assert quality['width'] == 1920
        assert quality['height'] == 1080
    
    def test_assess_quality_low_res(self, temp_dir):
        """Test quality assessment for low resolution image"""
        utils = ImageUtils()
        
        # Create low-res image (100x100)
        img_path = os.path.join(temp_dir, "low_res.jpg")
        img = Image.new('RGB', (100, 100), color='green')
        img.save(img_path, 'JPEG')
        
        quality = utils.assess_quality(img_path)
        
        assert quality['resolution'] in ['low', 'very_low']
        assert quality['score'] <= 0.5
    
    def test_assess_quality_aspect_ratio(self, temp_dir):
        """Test aspect ratio detection"""
        utils = ImageUtils()
        
        # Create 16:9 image
        img_path = os.path.join(temp_dir, "wide.jpg")
        img = Image.new('RGB', (1920, 1080), color='yellow')
        img.save(img_path, 'JPEG')
        
        quality = utils.assess_quality(img_path)
        
        assert quality.get('standard_aspect_ratio', False) is True
    
    def test_calculate_hash_different_images(self, temp_dir):
        """Test that different images produce different hashes"""
        utils = ImageUtils()
        
        # Create two DIFFERENT images with patterns (not solid colors)
        img1_path = os.path.join(temp_dir, "img1.jpg")
        img2_path = os.path.join(temp_dir, "img2.jpg")
        
        # Create image with gradient/pattern
        img1 = Image.new('RGB', (100, 100))
        for x in range(100):
            for y in range(100):
                img1.putpixel((x, y), (x * 2, y * 2, (x + y) % 256))
        img1.save(img1_path, 'JPEG')
        
        # Create different image with different pattern
        img2 = Image.new('RGB', (100, 100))
        for x in range(100):
            for y in range(100):
                img2.putpixel((x, y), (255 - x * 2, 128, y * 2))
        img2.save(img2_path, 'JPEG')
        
        with open(img1_path, 'rb') as f:
            hash1 = utils.calculate_hash(f.read())
        
        with open(img2_path, 'rb') as f:
            hash2 = utils.calculate_hash(f.read())
        
        # Different images should have different hashes
        assert hash1 != hash2


class TestExtractedImageSchema:
    """Test suite for ExtractedImage schema"""
    
    def test_create_extracted_image(self):
        """Test creating ExtractedImage object"""
        image = ExtractedImage(
            image_id="test_001",
            file_path="/path/to/image.jpg",
            source_doc="/path/to/doc.pdf",
            source_page=1,
            width=800,
            height=600,
            file_size=102400,
            mime_type="image/jpeg",
            extraction_method="embedded_pdf",
            is_embedded=True,
            image_hash="abc123",
            metadata={'test': 'value'}
        )
        
        assert image.image_id == "test_001"
        assert image.width == 800
        assert image.height == 600
        assert image.is_embedded is True
        assert image.extraction_method == "embedded_pdf"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
