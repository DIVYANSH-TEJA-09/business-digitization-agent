"""
Document Parsing Agent

Parses PDF, DOCX, and Excel files to extract text, tables, and embedded images.
Implements multi-strategy parsing with OCR fallback for scanned documents.
"""
import os
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.models.schemas import (
    DocumentParsingInput,
    DocumentParsingOutput,
    ParsedDocument,
    Page,
    DocumentMetadata,
    DocumentFile,
    SpreadsheetFile,
)
from backend.models.enums import FileType
from backend.parsers.parser_factory import ParserFactory
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class DocumentParsingError(Exception):
    """Base exception for document parsing errors"""
    pass


class UnsupportedFileTypeError(DocumentParsingError):
    """Raised when file type cannot be parsed"""
    pass


class CorruptedFileError(DocumentParsingError):
    """Raised when file is corrupted or unreadable"""
    pass


class DocumentParsingAgent:
    """
    Parses documents and extracts text, tables, and images
    
    Features:
    - Multi-format support (PDF, DOCX, XLSX, CSV)
    - Table extraction
    - Embedded image extraction
    - OCR fallback for scanned PDFs
    - Parallel processing
    """
    
    def __init__(
        self,
        enable_ocr: bool = True,
        max_concurrent: int = 5,
        timeout_per_doc: int = 300  # 5 minutes
    ):
        """
        Initialize Document Parsing Agent
        
        Args:
            enable_ocr: Enable OCR fallback for scanned PDFs
            max_concurrent: Maximum concurrent parsing tasks
            timeout_per_doc: Timeout per document in seconds
        """
        self.enable_ocr = enable_ocr
        self.max_concurrent = max_concurrent
        self.timeout_per_doc = timeout_per_doc
        self.parser_factory = ParserFactory(enable_ocr=enable_ocr)
    
    def parse(self, input: DocumentParsingInput) -> DocumentParsingOutput:
        """
        Parse all documents
        
        Args:
            input: Document parsing input
            
        Returns:
            Document parsing output
        """
        start_time = time.time()
        errors: List[str] = []
        parsed_documents: List[ParsedDocument] = []
        
        logger.info(f"Starting document parsing for job {input.job_id}")
        logger.info(f"Documents to parse: {len(input.documents)}")
        
        try:
            # Parse documents
            parsed_documents, parse_errors = self._parse_all_documents(
                input.documents,
                input.job_id
            )
            errors.extend(parse_errors)
            
            # Calculate statistics
            total_pages = sum(doc.total_pages for doc in parsed_documents)
            total_tables = sum(
                len(page.tables) 
                for doc in parsed_documents 
                for page in doc.pages
            )
            total_images = sum(
                len(page.images) 
                for doc in parsed_documents 
                for page in doc.pages
            )
            
            processing_time = time.time() - start_time
            
            output = DocumentParsingOutput(
                job_id=input.job_id,
                success=len(parsed_documents) > 0,
                parsed_documents=parsed_documents,
                total_pages=total_pages,
                total_tables=total_tables,
                total_images=total_images,
                processing_time=processing_time,
                errors=errors
            )
            
            logger.info(
                f"Document parsing completed: {len(parsed_documents)} docs, "
                f"{total_pages} pages, {total_tables} tables, {total_images} images "
                f"in {processing_time:.2f}s"
            )
            
            return output
            
        except Exception as e:
            logger.exception(f"Unexpected error in document parsing: {e}")
            return DocumentParsingOutput(
                job_id=input.job_id,
                success=False,
                parsed_documents=[],
                total_pages=0,
                total_tables=0,
                total_images=0,
                processing_time=time.time() - start_time,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    def _parse_all_documents(
        self,
        documents: List[DocumentFile],
        job_id: str
    ) -> tuple:
        """
        Parse all documents with concurrency control
        
        Args:
            documents: List of document files
            job_id: Unique job identifier
            
        Returns:
            Tuple of (parsed_documents, errors)
        """
        parsed_documents = []
        errors = []
        
        # Filter to only parseable types
        parseable_docs = [
            doc for doc in documents
            if doc.file_type in [FileType.PDF, FileType.DOCX, FileType.DOC]
        ]
        
        if not parseable_docs:
            logger.info("No parseable documents found")
            return parsed_documents, errors
        
        logger.info(f"Parsing {len(parseable_docs)} documents")
        
        # Parse sequentially (can be made async for production)
        for i, doc_file in enumerate(parseable_docs):
            try:
                logger.info(f"Parsing document {i+1}/{len(parseable_docs)}: {doc_file.original_name}")
                
                # Get appropriate parser
                parser = self.parser_factory.get_parser(doc_file.file_type)
                
                if not parser:
                    errors.append(f"No parser available for {doc_file.file_type.value}")
                    continue
                
                # Parse with timeout
                parsed = self._parse_with_timeout(doc_file, parser)
                
                if parsed:
                    parsed_documents.append(parsed)
                    logger.info(
                        f"Successfully parsed {doc_file.original_name}: "
                        f"{parsed.total_pages} pages"
                    )
                    
            except asyncio.TimeoutError:
                error_msg = f"Timeout parsing {doc_file.original_name} ({self.timeout_per_doc}s)"
                errors.append(error_msg)
                logger.error(error_msg)
                
            except Exception as e:
                error_msg = f"Failed to parse {doc_file.original_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return parsed_documents, errors
    
    def _parse_with_timeout(self, doc_file: DocumentFile, parser) -> Optional[ParsedDocument]:
        """
        Parse document with timeout
        
        Args:
            doc_file: Document file to parse
            parser: Parser instance
            
        Returns:
            Parsed document or None
        """
        try:
            # For now, parse synchronously
            # In production, use asyncio.wait_for()
            return parser.parse(doc_file.file_path)
            
        except asyncio.TimeoutError:
            raise
            
        except Exception as e:
            raise
    
    def parse_single(self, file_path: str, file_type: FileType) -> ParsedDocument:
        """
        Parse a single document
        
        Args:
            file_path: Path to document
            file_type: File type
            
        Returns:
            Parsed document
        """
        parser = self.parser_factory.get_parser(file_type)
        
        if not parser:
            raise UnsupportedFileTypeError(f"No parser for {file_type.value}")
        
        return parser.parse(file_path)
