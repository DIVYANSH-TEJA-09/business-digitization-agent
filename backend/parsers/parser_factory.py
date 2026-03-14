"""
Module: parser_factory.py
Purpose: Factory pattern for selecting the appropriate document parser.

Maps file types to their respective parsers and provides a single
entry point for parsing any supported document format.
"""

from pathlib import Path
from typing import Dict, Optional

from backend.models.exceptions import UnsupportedFileTypeError
from backend.models.schemas import FileType, ParsedDocument
from backend.parsers.docx_parser import DOCXParser
from backend.parsers.excel_parser import ExcelParser
from backend.parsers.pdf_parser import PDFParser
from backend.utils.file_classifier import classify_file
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ParserFactory:
    """
    Factory for creating and selecting document parsers.

    Supports:
        - PDF (via pdfplumber + PyPDF2 fallback)
        - DOCX (via python-docx)
        - XLSX/XLS/CSV (via openpyxl + pandas)

    Usage:
        factory = ParserFactory()
        doc = factory.parse("path/to/document.pdf")
    """

    def __init__(self):
        self._pdf_parser = PDFParser()
        self._docx_parser = DOCXParser()
        self._excel_parser = ExcelParser()

        # Map FileType to parser
        self._parser_map: Dict[FileType, object] = {
            FileType.PDF: self._pdf_parser,
            FileType.DOCX: self._docx_parser,
            FileType.DOC: self._docx_parser,  # Try DOCX parser for DOC
            FileType.XLSX: self._excel_parser,
            FileType.XLS: self._excel_parser,
            FileType.CSV: self._excel_parser,
        }

    def parse(self, file_path: str, file_type: Optional[FileType] = None) -> ParsedDocument:
        """
        Parse a document file using the appropriate parser.

        Args:
            file_path: Path to the document file
            file_type: Optional FileType override. If not provided,
                      auto-detected from file extension.

        Returns:
            ParsedDocument with extracted content

        Raises:
            UnsupportedFileTypeError: If no parser available
            FileNotFoundError: If file doesn't exist
        """
        if file_type is None:
            file_type, _ = classify_file(file_path)

        parser = self._parser_map.get(file_type)

        if parser is None:
            raise UnsupportedFileTypeError(
                file_type=file_type.value,
                file_path=file_path,
            )

        logger.info(
            f"Parsing '{Path(file_path).name}' "
            f"with {type(parser).__name__}"
        )

        return parser.parse(file_path)

    def can_parse(self, file_type: FileType) -> bool:
        """Check if a file type has an available parser."""
        return file_type in self._parser_map

    @property
    def supported_types(self) -> list:
        """List of all supported file types."""
        return list(self._parser_map.keys())


# Singleton instance
parser_factory = ParserFactory()
