"""
Unit tests for File Discovery Agent
"""
import os
import zipfile
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from backend.agents.file_discovery import (
    FileDiscoveryAgent,
    FileDiscoveryInput,
    InvalidZIPError,
    FileSizeExceededError,
    FileCountExceededError,
)
from backend.models.enums import FileType
from backend.utils.storage_manager import StorageManager


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def storage_manager(temp_dir):
    """Create storage manager with temp directory"""
    return StorageManager(storage_base=temp_dir)


@pytest.fixture
def agent(storage_manager):
    """Create file discovery agent"""
    return FileDiscoveryAgent(
        storage_manager=storage_manager,
        max_file_size=524288000,  # 500MB
        max_files=100
    )


@pytest.fixture
def sample_zip(temp_dir):
    """Create sample ZIP file with mixed content"""
    zip_path = os.path.join(temp_dir, "sample.zip")
    
    # Create temporary files to add to ZIP
    files_dir = os.path.join(temp_dir, "files_to_zip")
    os.makedirs(files_dir)
    
    # Create test files
    test_files = {
        "document.pdf": b"%PDF-1.4 test content",
        "report.docx": b"PK test docx content",
        "data.xlsx": b"PK test xlsx content",
        "image.jpg": b"\xff\xd8\xff\xe0 image content",
        "photo.png": b"\x89PNG\r\n\x1a\n image content",
        "notes.txt": b"Plain text file",
    }
    
    for filename, content in test_files.items():
        file_path = os.path.join(files_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
    
    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename in test_files.keys():
            file_path = os.path.join(files_dir, filename)
            zip_file.write(file_path, filename)
    
    return zip_path


@pytest.fixture
def nested_zip(temp_dir):
    """Create ZIP with nested folder structure"""
    zip_path = os.path.join(temp_dir, "nested.zip")
    
    # Create nested directory structure
    base_dir = os.path.join(temp_dir, "nested_files")
    os.makedirs(os.path.join(base_dir, "documents", "2024"))
    os.makedirs(os.path.join(base_dir, "images", "products"))
    
    # Create test files in nested structure
    test_files = {
        "documents/report.pdf": b"%PDF report",
        "documents/2024/annual.docx": b"PK annual report",
        "images/logo.png": b"\x89PNG logo",
        "images/products/product1.jpg": b"\xff\xd8\xff product",
    }
    
    for rel_path, content in test_files.items():
        file_path = os.path.join(base_dir, rel_path)
        with open(file_path, 'wb') as f:
            f.write(content)
    
    # Create ZIP preserving structure
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_dir)
                zip_file.write(file_path, arcname)
    
    return zip_path


class TestFileDiscoveryAgent:
    """Test suite for FileDiscoveryAgent"""
    
    def test_discover_valid_zip(self, agent, sample_zip):
        """Test discovery with valid ZIP file"""
        input_data = FileDiscoveryInput(
            zip_file_path=sample_zip,
            job_id="test_job_001"
        )
        
        output = agent.discover(input_data)
        
        assert output.success is True
        assert output.total_files == 6
        assert len(output.documents) == 2  # PDF, DOCX
        assert len(output.spreadsheets) == 1  # XLSX
        assert len(output.images) == 2  # JPG, PNG
        assert len(output.unknown) == 1  # TXT
        assert output.errors == []
        assert output.processing_time > 0
    
    def test_discover_nested_zip(self, agent, nested_zip):
        """Test discovery with nested folder structure"""
        input_data = FileDiscoveryInput(
            zip_file_path=nested_zip,
            job_id="test_job_002"
        )
        
        output = agent.discover(input_data)
        
        assert output.success is True
        assert output.total_files == 4
        assert output.directory_tree is not None
        assert len(output.directory_tree.children) > 0
    
    def test_discover_nonexistent_zip(self, agent, temp_dir):
        """Test discovery with non-existent ZIP file"""
        input_data = FileDiscoveryInput(
            zip_file_path=os.path.join(temp_dir, "nonexistent.zip"),
            job_id="test_job_003"
        )
        
        output = agent.discover(input_data)
        
        assert output.success is False
        assert len(output.errors) > 0
        assert "not found" in output.errors[0].lower()
    
    def test_file_size_exceeded(self, agent, temp_dir):
        """Test discovery with file exceeding size limit"""
        # Create a file larger than limit
        large_file_path = os.path.join(temp_dir, "large.zip")
        with open(large_file_path, 'wb') as f:
            f.write(b'0' * (524288001))  # 500MB + 1 byte
        
        input_data = FileDiscoveryInput(
            zip_file_path=large_file_path,
            job_id="test_job_004",
            max_file_size=524288000
        )
        
        output = agent.discover(input_data)
        
        assert output.success is False
        assert any("size" in err.lower() for err in output.errors)
    
    def test_file_count_exceeded(self, agent, temp_dir):
        """Test discovery with too many files"""
        # Create ZIP with many files
        zip_path = os.path.join(temp_dir, "many_files.zip")
        files_dir = os.path.join(temp_dir, "many_files_dir")
        os.makedirs(files_dir)
        
        # Create 101 files
        for i in range(101):
            file_path = os.path.join(files_dir, f"file_{i}.txt")
            with open(file_path, 'wb') as f:
                f.write(b"test")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i in range(101):
                file_path = os.path.join(files_dir, f"file_{i}.txt")
                zip_file.write(file_path, f"file_{i}.txt")
        
        input_data = FileDiscoveryInput(
            zip_file_path=zip_path,
            job_id="test_job_005",
            max_files=100
        )
        
        output = agent.discover(input_data)
        
        assert output.success is False
        assert any("files" in err.lower() for err in output.errors)
    
    def test_path_traversal_blocked(self, agent, temp_dir):
        """Test that path traversal attempts are blocked"""
        # Create ZIP with path traversal attempt
        zip_path = os.path.join(temp_dir, "traversal.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add file with path traversal
            zip_file.writestr("../../../etc/passwd", "malicious content")
            # Add normal file
            zip_file.writestr("safe_file.txt", "safe content")
        
        input_data = FileDiscoveryInput(
            zip_file_path=zip_path,
            job_id="test_job_006"
        )
        
        output = agent.discover(input_data)
        
        # Should still process safe files
        assert output.total_files >= 1
        # Should have warning about blocked path
        assert any("traversal" in err.lower() or "dangerous" in err.lower() 
                   for err in output.errors)
    
    def test_corrupted_zip(self, agent, temp_dir):
        """Test discovery with corrupted ZIP file"""
        # Create invalid ZIP
        corrupt_zip_path = os.path.join(temp_dir, "corrupt.zip")
        with open(corrupt_zip_path, 'wb') as f:
            f.write(b"This is not a valid ZIP file")
        
        input_data = FileDiscoveryInput(
            zip_file_path=corrupt_zip_path,
            job_id="test_job_007"
        )
        
        output = agent.discover(input_data)
        
        assert output.success is False
        assert any("invalid" in err.lower() or "corrupt" in err.lower() 
                   for err in output.errors)
    
    def test_extraction_directory_created(self, agent, sample_zip):
        """Test that extraction directory is created correctly"""
        input_data = FileDiscoveryInput(
            zip_file_path=sample_zip,
            job_id="test_job_008"
        )
        
        output = agent.discover(input_data)
        
        assert output.extraction_dir is not None
        assert os.path.exists(output.extraction_dir)
        assert output.job_id in output.extraction_dir
    
    def test_file_classification(self, agent, sample_zip):
        """Test file type classification"""
        input_data = FileDiscoveryInput(
            zip_file_path=sample_zip,
            job_id="test_job_009"
        )
        
        output = agent.discover(input_data)
        
        # Check PDF classified correctly
        pdf_files = [f for f in output.documents if f.file_type == FileType.PDF]
        assert len(pdf_files) == 1
        
        # Check DOCX classified correctly
        docx_files = [f for f in output.documents if f.file_type == FileType.DOCX]
        assert len(docx_files) == 1
        
        # Check XLSX classified correctly
        xlsx_files = [f for f in output.spreadsheets if f.file_type == FileType.XLSX]
        assert len(xlsx_files) == 1
        
        # Check JPG classified correctly
        jpg_files = [f for f in output.images if f.file_type == FileType.JPG]
        assert len(jpg_files) == 1
        
        # Check PNG classified correctly
        png_files = [f for f in output.images if f.file_type == FileType.PNG]
        assert len(png_files) == 1
    
    def test_directory_tree_built(self, agent, nested_zip):
        """Test directory tree structure"""
        input_data = FileDiscoveryInput(
            zip_file_path=nested_zip,
            job_id="test_job_010"
        )
        
        output = agent.discover(input_data)
        
        assert output.directory_tree is not None
        assert output.directory_tree.name == "root"
        assert len(output.directory_tree.children) > 0
        
        # Check nested structure preserved
        def find_node(node, name):
            if node.name == name:
                return node
            for child in node.children:
                result = find_node(child, name)
                if result:
                    return result
            return None
        
        # Should find nested directories
        documents_node = find_node(output.directory_tree, "documents")
        assert documents_node is not None
    
    def test_processing_time_recorded(self, agent, sample_zip):
        """Test that processing time is recorded"""
        input_data = FileDiscoveryInput(
            zip_file_path=sample_zip,
            job_id="test_job_011"
        )
        
        output = agent.discover(input_data)
        
        assert output.processing_time > 0
        assert output.processing_time < 60  # Should complete in under 60s
    
    def test_summary_generated(self, agent, sample_zip):
        """Test summary statistics"""
        input_data = FileDiscoveryInput(
            zip_file_path=sample_zip,
            job_id="test_job_012"
        )
        
        output = agent.discover(input_data)
        
        assert output.summary is not None
        assert "total_files" in output.summary
        assert "total_size_bytes" in output.summary
        assert output.summary["total_files"] == 6
    
    def test_metadata_saved(self, agent, sample_zip):
        """Test that discovery metadata is saved"""
        input_data = FileDiscoveryInput(
            zip_file_path=sample_zip,
            job_id="test_job_013"
        )
        
        output = agent.discover(input_data)
        
        # Check metadata file exists
        metadata_path = os.path.join(
            output.extraction_dir,
            "discovery_metadata.json"
        )
        assert os.path.exists(metadata_path)


class TestFileClassifier:
    """Test suite for FileClassifier"""
    
    def test_classify_pdf(self, agent, temp_dir):
        """Test PDF classification"""
        pdf_path = os.path.join(temp_dir, "test.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(b"%PDF-1.4 test")
        
        file_type, mime_type = agent.classifier.classify_file(pdf_path)
        assert file_type == FileType.PDF
    
    def test_classify_jpg(self, agent, temp_dir):
        """Test JPG classification"""
        jpg_path = os.path.join(temp_dir, "test.jpg")
        with open(jpg_path, 'wb') as f:
            f.write(b"\xff\xd8\xff\xe0 test")
        
        file_type, mime_type = agent.classifier.classify_file(jpg_path)
        assert file_type == FileType.JPG
    
    def test_classify_unknown(self, agent, temp_dir):
        """Test unknown file classification"""
        unknown_path = os.path.join(temp_dir, "test.xyz")
        with open(unknown_path, 'wb') as f:
            f.write(b"unknown content")
        
        file_type, mime_type = agent.classifier.classify_file(unknown_path)
        assert file_type == FileType.UNKNOWN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
