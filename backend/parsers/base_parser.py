"""
Base Parser Interface

All document parsers inherit from this base class.
"""
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path

from backend.models.schemas import ParsedDocument


class BaseParser(ABC):
    """
    Abstract base class for document parsers
    
    All parsers must implement:
    - parse(): Main parsing method
    - _extract_text(): Text extraction
    - _extract_metadata(): Document metadata
    """
    
    def __init__(self):
        self.supported_extensions = []
    
    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse document and extract content
        
        Args:
            file_path: Path to document file
            
        Returns:
            ParsedDocument object
        """
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """
        Validate file exists and is readable
        
        Args:
            file_path: Path to file
            
        Returns:
            True if valid
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        if not path.stat().st_size > 0:
            raise ValueError(f"File is empty: {file_path}")
        
        return True
    
    def generate_doc_id(self, file_path: str) -> str:
        """
        Generate unique document ID from file path
        
        Args:
            file_path: Path to file
            
        Returns:
            Document ID string
        """
        import hashlib
        import time
        
        # Create unique ID from file path and timestamp
        content = f"{file_path}_{time.time()}"
        return f"doc_{hashlib.md5(content.encode()).hexdigest()[:12]}"
