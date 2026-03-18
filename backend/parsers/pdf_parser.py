"""
PDF Parser

Extracts text, tables, and images from PDF files using pdfplumber.
Implements OCR fallback for scanned PDFs.
"""
import io
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import pdfplumber
from PIL import Image

from backend.models.schemas import ParsedDocument, Page, DocumentMetadata
from backend.models.enums import FileType
from backend.parsers.base_parser import BaseParser


class PDFParser(BaseParser):
    """
    PDF parser with multi-strategy extraction
    
    Strategies:
    1. pdfplumber (primary) - best for structured PDFs
    2. PyPDF2 (fallback) - for corrupted PDFs
    3. OCR (final fallback) - for scanned PDFs
    """
    
    def __init__(self, enable_ocr: bool = True):
        """
        Initialize PDF parser
        
        Args:
            enable_ocr: Enable OCR fallback
        """
        super().__init__()
        self.enable_ocr = enable_ocr
        self.supported_extensions = ['.pdf']
    
    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ParsedDocument object
        """
        self.validate_file(file_path)
        
        try:
            return self._parse_with_pdfplumber(file_path)
        except Exception as e:
            # Fallback to other methods
            if self.enable_ocr:
                return self._parse_with_ocr(file_path)
            else:
                raise
    
    def _parse_with_pdfplumber(self, pdf_path: str) -> ParsedDocument:
        """
        Parse PDF using pdfplumber (primary method)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ParsedDocument object
        """
        pages = []
        errors = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    page_obj = self._parse_page(page, i + 1)
                    pages.append(page_obj)
                except Exception as e:
                    errors.append(f"Page {i+1}: {str(e)}")
                    # Add empty page as placeholder
                    pages.append(Page(number=i+1, text="", tables=[], images=[]))
        
        return ParsedDocument(
            doc_id=self.generate_doc_id(pdf_path),
            source_file=pdf_path,
            file_type=FileType.PDF,
            pages=pages,
            total_pages=len(pages),
            metadata=self._extract_metadata(pdf_path, pdf),
            parsing_errors=errors
        )
    
    def _parse_page(self, page, page_num: int) -> Page:
        """
        Parse single PDF page
        
        Args:
            page: pdfplumber page object
            page_num: Page number (1-indexed)
            
        Returns:
            Page object
        """
        # Extract text
        text = page.extract_text() or ""
        
        # Extract tables
        tables = self._extract_tables(page)
        
        # Extract images
        images = self._extract_images(page, page_num)
        
        return Page(
            number=page_num,
            text=text,
            tables=tables,
            images=images,
            width=float(page.width) if page.width else None,
            height=float(page.height) if page.height else None,
            metadata={
                'page_number': page_num,
                'width': page.width,
                'height': page.height
            }
        )
    
    def _extract_tables(self, page) -> List[List[List[str]]]:
        """
        Extract tables from page
        
        Args:
            page: pdfplumber page object
            
        Returns:
            List of tables (each table is list of rows)
        """
        tables = []
        
        try:
            pdf_tables = page.extract_tables()
            
            if pdf_tables:
                for table in pdf_tables:
                    if self._is_valid_table(table):
                        cleaned = self._clean_table(table)
                        tables.append(cleaned)
        except Exception:
            pass
        
        return tables
    
    def _is_valid_table(self, table: List) -> bool:
        """
        Validate table structure
        
        Args:
            table: Raw table data
            
        Returns:
            True if valid
        """
        if not table or len(table) < 2:
            return False
        
        # Check for minimum content
        non_empty_cells = sum(
            1 for row in table 
            for cell in row 
            if cell and str(cell).strip()
        )
        
        return non_empty_cells > 0
    
    def _clean_table(self, table: List) -> List[List[str]]:
        """
        Clean and normalize table data
        
        Args:
            table: Raw table data
            
        Returns:
            Cleaned table
        """
        cleaned = []
        
        for row in table:
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append("")
                else:
                    # Convert to string and clean
                    cell_text = str(cell).strip()
                    # Remove excessive whitespace
                    cell_text = ' '.join(cell_text.split())
                    cleaned_row.append(cell_text)
            cleaned.append(cleaned_row)
        
        return cleaned
    
    def _extract_images(self, page, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract embedded images from page
        
        Args:
            page: pdfplumber page object
            page_num: Page number
            
        Returns:
            List of image metadata
        """
        images = []
        
        try:
            if hasattr(page, 'images'):
                for i, img_info in enumerate(page.images):
                    try:
                        image_data = self._extract_image_data(page, img_info)
                        
                        if image_data:
                            images.append({
                                'image_id': f"img_p{page_num}_{i}",
                                'page_number': page_num,
                                'index': i,
                                'width': img_info.get('width', 0),
                                'height': img_info.get('height', 0),
                                'bbox': img_info.get('bbox'),
                                'data': image_data  # Base64 or bytes
                            })
                    except Exception:
                        pass
        except Exception:
            pass
        
        return images
    
    def _extract_image_data(self, page, img_info: Dict) -> Optional[bytes]:
        """
        Extract actual image bytes
        
        Args:
            page: pdfplumber page object
            img_info: Image metadata
            
        Returns:
            Image bytes or None
        """
        try:
            # Get image object reference
            xref = img_info.get('xref')
            
            if not xref:
                return None
            
            # Extract using pdfplumber's PDF object
            pdf = page.pdf
            if hasattr(pdf, 'pdf') and hasattr(pdf.pdf, 'extract_image'):
                base_image = pdf.pdf.extract_image(xref)
                if base_image:
                    return base_image.get('image')
            
            return None
            
        except Exception:
            return None
    
    def _extract_metadata(self, pdf_path: str, pdf) -> DocumentMetadata:
        """
        Extract PDF metadata
        
        Args:
            pdf_path: Path to PDF
            pdf: pdfplumber PDF object
            
        Returns:
            DocumentMetadata object
        """
        metadata = pdf.metadata or {}
        
        return DocumentMetadata(
            title=metadata.get('Title'),
            author=metadata.get('Author'),
            creation_date=self._parse_pdf_date(metadata.get('CreationDate')),
            modification_date=self._parse_pdf_date(metadata.get('ModDate')),
            page_count=len(pdf.pages),
            file_size=os.path.getsize(pdf_path)
        )
    
    def _parse_pdf_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse PDF date format
        
        Args:
            date_str: PDF date string
            
        Returns:
            datetime object or None
        """
        if not date_str:
            return None
        
        try:
            # Remove 'D:' prefix and timezone
            date_str = date_str.replace('D:', '').split('+')[0].split('-')[0]
            return datetime.strptime(date_str[:14], '%Y%m%d%H%M%S')
        except Exception:
            return None
    
    def _parse_with_ocr(self, pdf_path: str) -> ParsedDocument:
        """
        Parse PDF using OCR (fallback for scanned PDFs)
        
        Args:
            pdf_path: Path to PDF
            
        Returns:
            ParsedDocument object
        """
        try:
            import pytesseract
            from pdf2image import convert_from_path
            
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            
            pages = []
            for i, image in enumerate(images):
                # Enhance image for OCR
                enhanced = self._enhance_for_ocr(image)
                
                # Extract text
                text = pytesseract.image_to_string(enhanced, config='--psm 6')
                
                pages.append(Page(
                    number=i + 1,
                    text=text,
                    tables=[],  # OCR doesn't extract tables well
                    images=[],
                    metadata={'extraction_method': 'ocr'}
                ))
            
            return ParsedDocument(
                doc_id=self.generate_doc_id(pdf_path),
                source_file=pdf_path,
                file_type=FileType.PDF,
                pages=pages,
                total_pages=len(pages),
                metadata=self._extract_metadata(pdf_path, None),
                parsing_errors=['OCR used - tables may be missing']
            )
            
        except Exception as e:
            raise Exception(f"OCR parsing failed: {str(e)}")
    
    def _enhance_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Enhance image for better OCR accuracy
        
        Args:
            image: PIL Image object
            
        Returns:
            Enhanced image
        """
        from PIL import ImageEnhance, ImageFilter
        
        # Convert to grayscale
        gray = image.convert('L')
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(gray)
        contrasted = enhancer.enhance(2.0)
        
        # Denoise
        denoised = contrasted.filter(ImageFilter.MedianFilter(size=3))
        
        # Sharpen
        sharpened = denoised.filter(ImageFilter.SHARPEN)
        
        return sharpened
