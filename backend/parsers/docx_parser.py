"""
Module: docx_parser.py
Purpose: Extract text, tables, and metadata from DOCX documents.

Uses python-docx to parse Word documents, extracting paragraphs,
tables, and basic metadata while preserving document structure.
"""

from pathlib import Path
from typing import Any, Dict, List
from zipfile import BadZipFile

from docx import Document
from docx.table import Table as DocxTable

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


class DOCXParser:
    """
    DOCX document parser using python-docx.

    Extracts:
        - Paragraphs with style information
        - Tables with structure
        - Document metadata (title, author)
        - Embedded image references

    Note: DOCX doesn't have natural "pages" like PDF.
    We treat the entire document as a single page and use
    paragraph styles to maintain structure.
    """

    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse a DOCX file and extract all content.

        Args:
            file_path: Path to the DOCX file

        Returns:
            ParsedDocument with content and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            CorruptedFileError: If DOCX is corrupted
            DocumentParsingError: For other parsing errors
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"DOCX file not found: {file_path}")

        logger.info(f"Parsing DOCX: {path.name}")

        try:
            doc = Document(file_path)
        except BadZipFile:
            raise CorruptedFileError(
                f"Corrupted DOCX file (invalid ZIP structure): {file_path}"
            )
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to open DOCX: {e}"
            ) from e

        try:
            return self._extract_content(doc, file_path)
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to parse DOCX content: {e}"
            ) from e

    def _extract_content(
        self, doc: Document, file_path: str
    ) -> ParsedDocument:
        """Extract all content from a DOCX document."""
        # Extract text from paragraphs
        text_parts: List[str] = []
        elements: List[Dict[str, Any]] = []

        for para in doc.paragraphs:
            if not para.text.strip():
                text_parts.append("")
                continue

            text = clean_text(para.text)
            style_name = para.style.name if para.style else "Normal"

            text_parts.append(text)
            elements.append({
                "type": "paragraph",
                "text": text,
                "style": style_name,
                "is_heading": style_name.startswith("Heading"),
                "heading_level": self._get_heading_level(style_name),
            })

        # Extract tables
        tables = self._extract_tables(doc)

        # Extract image references
        image_refs = self._get_image_references(doc)

        # Extract metadata
        metadata = self._extract_metadata(doc, file_path)

        # Combine all text
        full_text = "\n".join(text_parts)
        full_text = clean_text(full_text)

        # For table text, add it to the full text as well
        table_text_parts = []
        for table_data in tables:
            for row in table_data:
                table_text_parts.append(" | ".join(
                    str(cell) for cell in row
                ))

        if table_text_parts:
            full_text += "\n\n" + "\n".join(table_text_parts)

        # Create a single "page" (DOCX doesn't have real pages)
        page = Page(
            number=1,
            text=full_text,
            tables=tables,
            images=image_refs,
            metadata={
                "elements": elements,
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(tables),
                "image_count": len(image_refs),
            },
        )

        doc_result = ParsedDocument(
            source_file=file_path,
            file_type=FileType.DOCX,
            pages=[page],
            total_pages=1,
            full_text=full_text,
            metadata=metadata,
        )

        logger.info(
            f"DOCX parsed: {Path(file_path).name} — "
            f"{len(doc.paragraphs)} paragraphs, "
            f"{len(tables)} tables, "
            f"{len(image_refs)} images"
        )

        return doc_result

    def _extract_tables(self, doc: Document) -> List[List[List[str]]]:
        """Extract all tables from the document."""
        tables = []

        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = []
                for cell in row.cells:
                    cell_text = clean_text(cell.text)
                    row_data.append(cell_text)
                table_data.append(row_data)

            # Skip empty tables
            if any(any(cell for cell in row) for row in table_data):
                tables.append(table_data)

        return tables

    def _get_image_references(self, doc: Document) -> List[Dict[str, Any]]:
        """
        Get references to embedded images in the DOCX.

        DOCX stores images in the ZIP's word/media/ folder.
        We extract metadata here; actual images are extracted
        by the MediaExtractionAgent later.
        """
        images = []
        try:
            for idx, rel in enumerate(doc.part.rels.values()):
                if "image" in rel.reltype:
                    images.append({
                        "index": idx,
                        "rel_id": rel.rId,
                        "target": rel.target_ref,
                        "type": "embedded",
                    })
        except Exception as e:
            logger.debug(f"Could not extract image references: {e}")

        return images

    def _extract_metadata(
        self, doc: Document, file_path: str
    ) -> DocumentMetadata:
        """Extract document metadata from DOCX core properties."""
        props = doc.core_properties

        return DocumentMetadata(
            title=props.title or None,
            author=props.author or None,
            creation_date=str(props.created) if props.created else None,
            modification_date=str(props.modified) if props.modified else None,
            page_count=1,  # DOCX doesn't track pages reliably
            file_size=Path(file_path).stat().st_size,
        )

    def _get_heading_level(self, style_name: str) -> int:
        """
        Extract heading level from style name.

        'Heading 1' -> 1, 'Heading 2' -> 2, etc.
        Returns 0 for non-heading styles.
        """
        if not style_name.startswith("Heading"):
            return 0
        try:
            return int(style_name.split()[-1])
        except (ValueError, IndexError):
            return 0
