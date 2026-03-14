"""
Module: pdf_parser.py
Purpose: Extract text, tables, and metadata from PDF documents.

Uses pdfplumber as primary parser with PyPDF2 as fallback.
Extracts page-level text, tables, and embedded image metadata.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pdfplumber
from PyPDF2 import PdfReader

from backend.models.exceptions import CorruptedFileError, DocumentParsingError
from backend.models.schemas import (
    DocumentMetadata,
    FileType,
    Page,
    ParsedDocument,
)
from backend.utils.logger import get_logger
from backend.utils.text_utils import clean_text

logger = get_logger(__name__)


class PDFParser:
    """
    PDF document parser using pdfplumber with PyPDF2 fallback.

    Extracts:
        - Page-level text content
        - Tables (as lists of rows)
        - Embedded image metadata (count, dimensions)
        - Document metadata (title, author, dates)
    """

    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse a PDF file and extract all content.

        Args:
            file_path: Path to the PDF file

        Returns:
            ParsedDocument with pages, text, and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            CorruptedFileError: If PDF is corrupted/unreadable
            DocumentParsingError: For other parsing errors
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"Parsing PDF: {path.name}")

        try:
            return self._parse_with_pdfplumber(file_path)
        except CorruptedFileError:
            raise
        except Exception as e:
            logger.warning(
                f"pdfplumber failed for {path.name}: {e}. "
                f"Trying PyPDF2 fallback..."
            )
            try:
                return self._parse_with_pypdf2(file_path)
            except Exception as e2:
                raise DocumentParsingError(
                    f"Failed to parse PDF with both parsers: {e2}"
                ) from e2

    def _parse_with_pdfplumber(self, file_path: str) -> ParsedDocument:
        """Parse PDF using pdfplumber (primary parser)."""
        pages: List[Page] = []
        all_text_parts: List[str] = []
        parsing_errors: List[str] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                metadata = self._extract_metadata_pdfplumber(pdf, file_path)

                for i, page in enumerate(pdf.pages):
                    page_num = i + 1

                    try:
                        # Extract text
                        text = page.extract_text() or ""
                        text = clean_text(text)

                        # Extract tables
                        raw_tables = page.extract_tables() or []
                        tables = self._clean_tables(raw_tables)

                        # Count embedded images
                        images = self._get_image_metadata(page, page_num)

                        pages.append(Page(
                            number=page_num,
                            text=text,
                            tables=tables,
                            images=images,
                            width=page.width,
                            height=page.height,
                            metadata={
                                "char_count": len(text),
                                "table_count": len(tables),
                                "image_count": len(images),
                            },
                        ))

                        if text:
                            all_text_parts.append(
                                f"--- Page {page_num} ---\n{text}"
                            )

                    except Exception as e:
                        error_msg = f"Page {page_num}: {str(e)}"
                        parsing_errors.append(error_msg)
                        logger.warning(f"Error on page {page_num}: {e}")

                        # Add empty page to maintain page numbering
                        pages.append(Page(
                            number=page_num,
                            text="",
                            metadata={"error": str(e)},
                        ))

        except Exception as e:
            if "password" in str(e).lower() or "encrypt" in str(e).lower():
                raise CorruptedFileError(
                    f"PDF is password-protected: {file_path}"
                ) from e
            raise

        full_text = "\n\n".join(all_text_parts)

        doc = ParsedDocument(
            source_file=file_path,
            file_type=FileType.PDF,
            pages=pages,
            total_pages=len(pages),
            full_text=full_text,
            metadata=metadata,
            parsing_errors=parsing_errors,
        )

        logger.info(
            f"PDF parsed: {Path(file_path).name} — "
            f"{len(pages)} pages, {len(full_text)} chars, "
            f"{sum(len(p.tables) for p in pages)} tables"
        )

        return doc

    def _parse_with_pypdf2(self, file_path: str) -> ParsedDocument:
        """Parse PDF using PyPDF2 (fallback parser — text only)."""
        pages: List[Page] = []
        all_text_parts: List[str] = []
        parsing_errors: List[str] = []

        try:
            reader = PdfReader(file_path)
            metadata = self._extract_metadata_pypdf2(reader, file_path)

            for i, page in enumerate(reader.pages):
                page_num = i + 1
                try:
                    text = page.extract_text() or ""
                    text = clean_text(text)

                    pages.append(Page(
                        number=page_num,
                        text=text,
                        metadata={"parser": "pypdf2"},
                    ))

                    if text:
                        all_text_parts.append(
                            f"--- Page {page_num} ---\n{text}"
                        )
                except Exception as e:
                    parsing_errors.append(f"Page {page_num}: {str(e)}")
                    pages.append(Page(number=page_num, text=""))

        except Exception as e:
            raise CorruptedFileError(
                f"Cannot read PDF: {e}"
            ) from e

        return ParsedDocument(
            source_file=file_path,
            file_type=FileType.PDF,
            pages=pages,
            total_pages=len(pages),
            full_text="\n\n".join(all_text_parts),
            metadata=metadata,
            parsing_errors=parsing_errors,
        )

    def _extract_metadata_pdfplumber(
        self, pdf: Any, file_path: str
    ) -> DocumentMetadata:
        """Extract metadata using pdfplumber."""
        info = pdf.metadata or {}
        return DocumentMetadata(
            title=info.get("Title"),
            author=info.get("Author"),
            creation_date=str(info.get("CreationDate", "")),
            modification_date=str(info.get("ModDate", "")),
            page_count=len(pdf.pages),
            file_size=Path(file_path).stat().st_size,
        )

    def _extract_metadata_pypdf2(
        self, reader: PdfReader, file_path: str
    ) -> DocumentMetadata:
        """Extract metadata using PyPDF2."""
        info = reader.metadata or {}
        return DocumentMetadata(
            title=getattr(info, "title", None),
            author=getattr(info, "author", None),
            creation_date=str(getattr(info, "creation_date", "")),
            modification_date=str(getattr(info, "modification_date", "")),
            page_count=len(reader.pages),
            file_size=Path(file_path).stat().st_size,
        )

    def _clean_tables(
        self, raw_tables: List[List[List[Optional[str]]]]
    ) -> List[List[List[str]]]:
        """Clean raw tables — replace None with empty string, strip cells."""
        cleaned = []
        for table in raw_tables:
            if not table:
                continue
            clean_table = []
            for row in table:
                clean_row = [
                    str(cell).strip() if cell is not None else ""
                    for cell in row
                ]
                clean_table.append(clean_row)

            # Skip tables with only empty cells
            if any(any(cell for cell in row) for row in clean_table):
                cleaned.append(clean_table)

        return cleaned

    def _get_image_metadata(
        self, page: Any, page_num: int
    ) -> List[Dict[str, Any]]:
        """Get metadata about images on a page (not the image data itself)."""
        images = []
        try:
            page_images = page.images or []
            for idx, img in enumerate(page_images):
                images.append({
                    "index": idx,
                    "page": page_num,
                    "x0": img.get("x0", 0),
                    "y0": img.get("top", 0),
                    "x1": img.get("x1", 0),
                    "y1": img.get("bottom", 0),
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                })
        except Exception:
            pass  # Image metadata extraction is best-effort
        return images
