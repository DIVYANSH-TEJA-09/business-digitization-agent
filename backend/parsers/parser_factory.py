"""
Parser Factory

Provides appropriate parser based on file type.
"""
from typing import Optional, Dict, Type
from backend.models.enums import FileType
from backend.parsers.pdf_parser import PDFParser
from backend.parsers.docx_parser import DOCXParser
from backend.parsers.base_parser import BaseParser


class ParserFactory:
    """
    Factory for creating document parsers
    
    Usage:
        factory = ParserFactory()
        parser = factory.get_parser(FileType.PDF)
        parsed_doc = parser.parse("document.pdf")
    """
    
    def __init__(self, enable_ocr: bool = True):
        """
        Initialize parser factory
        
        Args:
            enable_ocr: Enable OCR fallback for scanned PDFs
        """
        self.enable_ocr = enable_ocr
        self._parsers: Dict[FileType, Type[BaseParser]] = {
            FileType.PDF: PDFParser,
            FileType.DOCX: DOCXParser,
            FileType.DOC: DOCXParser,  # Use DOCX parser for old DOC (best effort)
        }
    
    def get_parser(self, file_type: FileType) -> Optional[BaseParser]:
        """
        Get parser instance for file type
        
        Args:
            file_type: File type to get parser for
            
        Returns:
            Parser instance or None if not supported
        """
        parser_class = self._parsers.get(file_type)
        
        if not parser_class:
            return None
        
        # Instantiate with configuration
        if file_type == FileType.PDF:
            return parser_class(enable_ocr=self.enable_ocr)
        else:
            return parser_class()
    
    def get_supported_types(self) -> list:
        """
        Get list of supported file types
        
        Returns:
            List of supported FileType enums
        """
        return list(self._parsers.keys())
    
    def is_supported(self, file_type: FileType) -> bool:
        """
        Check if file type is supported
        
        Args:
            file_type: File type to check
            
        Returns:
            True if supported
        """
        return file_type in self._parsers
