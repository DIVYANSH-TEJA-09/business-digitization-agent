"""
Table Extraction Agent

Detects, extracts, and classifies tables from parsed documents.
Implements rule-based classification with LLM fallback for ambiguous cases.
"""
import os
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from backend.models.schemas import (
    TableExtractionInput,
    TableExtractionOutput,
    StructuredTable,
    TableMetadata,
    ParsedDocument,
    Page,
)
from backend.models.enums import TableType
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class TableExtractionError(Exception):
    """Base exception for table extraction errors"""
    pass


class TableExtractionAgent:
    """
    Extracts and classifies tables from parsed documents
    
    Features:
    - Rule-based table type classification
    - Table cleaning and normalization
    - Complex table handling
    - Confidence scoring
    """
    
    def __init__(self):
        """Initialize Table Extraction Agent"""
        self.table_utils = TableUtils()
    
    def extract(self, input: TableExtractionInput) -> TableExtractionOutput:
        """
        Extract tables from all parsed documents
        
        Args:
            input: Table extraction input
            
        Returns:
            Table extraction output
        """
        start_time = time.time()
        errors: List[str] = []
        all_tables: List[StructuredTable] = []
        
        logger.info(f"Starting table extraction for job {input.job_id}")
        logger.info(f"Documents to process: {len(input.parsed_documents)}")
        
        try:
            # Extract tables from each document
            for doc in input.parsed_documents:
                try:
                    doc_tables = self._extract_from_document(doc)
                    all_tables.extend(doc_tables)
                    logger.info(f"Extracted {len(doc_tables)} tables from {doc.source_file}")
                except Exception as e:
                    error_msg = f"Failed to extract tables from {doc.source_file}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Calculate statistics
            tables_by_type = self._count_by_type(all_tables)
            processing_time = time.time() - start_time
            
            output = TableExtractionOutput(
                job_id=input.job_id,
                success=len(all_tables) > 0,
                tables=all_tables,
                total_tables=len(all_tables),
                tables_by_type=tables_by_type,
                processing_time=processing_time,
                errors=errors
            )
            
            logger.info(
                f"Table extraction completed: {len(all_tables)} tables "
                f"in {processing_time:.2f}s"
            )
            
            return output
            
        except Exception as e:
            logger.exception(f"Unexpected error in table extraction: {e}")
            return TableExtractionOutput(
                job_id=input.job_id,
                success=False,
                tables=[],
                total_tables=0,
                tables_by_type={},
                processing_time=time.time() - start_time,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    def _extract_from_document(self, doc: ParsedDocument) -> List[StructuredTable]:
        """
        Extract tables from a single document
        
        Args:
            doc: ParsedDocument object
            
        Returns:
            List of StructuredTable objects
        """
        tables = []
        
        for page in doc.pages:
            if page.tables:
                page_tables = self._extract_from_page(page, doc)
                tables.extend(page_tables)
        
        return tables
    
    def _extract_from_page(self, page: Page, doc: ParsedDocument) -> List[StructuredTable]:
        """
        Extract tables from a single page
        
        Args:
            page: Page object
            doc: ParsedDocument object
            
        Returns:
            List of StructuredTable objects
        """
        tables = []
        
        for i, raw_table in enumerate(page.tables):
            try:
                # Clean and validate table
                cleaned = self.table_utils.clean_table(raw_table)
                
                if self.table_utils.is_valid_table(cleaned):
                    # Classify table type
                    table_type = self.classify_table(cleaned, page.text)
                    
                    # Create structured table
                    structured = StructuredTable(
                        table_id=f"tbl_{doc.doc_id}_p{page.number}_{i}",
                        source_doc=doc.source_file,
                        source_page=page.number,
                        headers=self._extract_headers(cleaned),
                        rows=cleaned[1:] if len(cleaned) > 1 else [],
                        table_type=table_type,
                        context=self._extract_context(page.text, i),
                        confidence=self._calculate_confidence(cleaned, table_type),
                        metadata=TableMetadata(
                            surrounding_text=page.text[:500] if page.text else "",
                            confidence_score=self._calculate_confidence(cleaned, table_type),
                            detection_method="rule-based",
                            column_count=len(cleaned[0]) if cleaned else 0,
                            row_count=len(cleaned)
                        )
                    )
                    
                    tables.append(structured)
                    
            except Exception as e:
                logger.warning(f"Failed to extract table {i} from page {page.number}: {e}")
        
        return tables
    
    def classify_table(self, table: List[List[str]], context: str = "") -> TableType:
        """
        Classify table by type using rule-based detection
        
        Args:
            table: Cleaned table data
            context: Surrounding text context
            
        Returns:
            TableType enum value
        """
        # Strategy 1: Check headers
        headers = table[0] if table else []
        headers_lower = [h.lower() for h in headers]
        header_text = ' '.join(headers_lower)
        
        # Strategy 2: Check content patterns
        content_text = ' '.join(' '.join(row) for row in table[1:3] if len(table) > 1)
        content_lower = content_text.lower()
        
        # Pricing table detection
        if self._is_pricing_table(headers_lower, content_lower):
            return TableType.PRICING
        
        # Itinerary/Schedule table detection
        if self._is_itinerary_table(headers_lower, content_lower):
            return TableType.ITINERARY
        
        # Specifications table detection
        if self._is_specification_table(headers_lower, content_lower):
            return TableType.SPECIFICATIONS
        
        # Menu table detection
        if self._is_menu_table(headers_lower, content_lower):
            return TableType.MENU
        
        # Inventory table detection
        if self._is_inventory_table(headers_lower, content_lower):
            return TableType.INVENTORY
        
        # Default to general
        return TableType.GENERAL
    
    def _is_pricing_table(self, headers: List[str], content: str) -> bool:
        """
        Detect pricing tables
        
        Args:
            headers: Table headers (lowercase)
            content: Table content (lowercase)
            
        Returns:
            True if pricing table
        """
        price_keywords = ['price', 'cost', 'rate', 'amount', 'fee', 'charge', 'total', 'subtotal']
        currency_patterns = [r'\$\d+', r'€\d+', r'₹\d+', r'\d+\.\d{2}', r'\d{3,}']
        
        # Check headers for price-related terms
        has_price_header = any(
            any(keyword in header for keyword in price_keywords)
            for header in headers
        )
        
        # Check content for currency patterns
        import re
        has_currency = bool(re.search(r'[\$€₹]\s*\d+[\d,.]*', content))
        
        return has_price_header or has_currency
    
    def _is_itinerary_table(self, headers: List[str], content: str) -> bool:
        """
        Detect itinerary/schedule tables
        
        Args:
            headers: Table headers (lowercase)
            content: Table content (lowercase)
            
        Returns:
            True if itinerary table
        """
        time_keywords = ['day', 'time', 'date', 'schedule', 'itinerary', 'duration', 'when']
        
        has_time_header = any(
            any(keyword in header for keyword in time_keywords)
            for header in headers
        )
        
        # Check for time patterns (Day 1, 9:00 AM, etc.)
        has_time_data = bool(re.search(r'(day\s*\d+|\d{1,2}:\d{2}\s*[ap]m)', content))
        
        return has_time_header or has_time_data
    
    def _is_specification_table(self, headers: List[str], content: str) -> bool:
        """
        Detect specification tables
        
        Args:
            headers: Table headers (lowercase)
            content: Table content (lowercase)
            
        Returns:
            True if specification table
        """
        spec_keywords = ['spec', 'specification', 'feature', 'dimension', 'weight', 
                        'size', 'material', 'color', 'model', 'type', 'description']
        
        has_spec_header = any(
            any(keyword in header for keyword in spec_keywords)
            for header in headers
        )
        
        return has_spec_header
    
    def _is_menu_table(self, headers: List[str], content: str) -> bool:
        """
        Detect menu tables
        
        Args:
            headers: Table headers (lowercase)
            content: Table content (lowercase)
            
        Returns:
            True if menu table
        """
        menu_keywords = ['dish', 'item', 'food', 'meal', 'course', 'appetizer', 
                        'main', 'dessert', 'beverage', 'menu']
        
        has_menu_header = any(
            any(keyword in header for keyword in menu_keywords)
            for header in headers
        )
        
        return has_menu_header
    
    def _is_inventory_table(self, headers: List[str], content: str) -> bool:
        """
        Detect inventory tables
        
        Args:
            headers: Table headers (lowercase)
            content: Table content (lowercase)
            
        Returns:
            True if inventory table
        """
        inventory_keywords = ['stock', 'quantity', 'available', 'inventory', 
                             'count', 'units', 'remaining']
        
        has_inventory_header = any(
            any(keyword in header for keyword in inventory_keywords)
            for header in headers
        )
        
        return has_inventory_header
    
    def _extract_headers(self, table: List[List[str]]) -> List[str]:
        """
        Extract headers from table
        
        Args:
            table: Cleaned table data
            
        Returns:
            List of header strings
        """
        if not table:
            return []
        
        return table[0] if table else []
    
    def _extract_context(self, page_text: str, table_index: int) -> str:
        """
        Extract surrounding text context for table
        
        Args:
            page_text: Full page text
            table_index: Index of table on page
            
        Returns:
            Context string
        """
        if not page_text:
            return ""
        
        # Return first 500 chars as context (simplified)
        return page_text[:500]
    
    def _calculate_confidence(self, table: List[List[str]], table_type: TableType) -> float:
        """
        Calculate confidence score for table extraction
        
        Args:
            table: Cleaned table data
            table_type: Classified table type
            
        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.5  # Base confidence
        
        # Increase for well-structured tables
        if len(table) > 2 and len(table[0]) > 1:
            confidence += 0.2
        
        # Increase for specific types (not GENERAL)
        if table_type != TableType.GENERAL:
            confidence += 0.2
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _count_by_type(self, tables: List[StructuredTable]) -> Dict[str, int]:
        """
        Count tables by type
        
        Args:
            tables: List of tables
            
        Returns:
            Dictionary of type counts
        """
        counts = {}
        for table in tables:
            type_name = table.table_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts


class TableUtils:
    """
    Utility functions for table processing
    """
    
    def clean_table(self, table: List) -> List[List[str]]:
        """
        Clean and normalize table data
        
        Args:
            table: Raw table data
            
        Returns:
            Cleaned table
        """
        if not table:
            return []
        
        cleaned = []
        
        for row in table:
            if row is None:
                continue
                
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
            
            # Only add non-empty rows
            if any(cleaned_row):
                cleaned.append(cleaned_row)
        
        return cleaned
    
    def is_valid_table(self, table: List[List[str]]) -> bool:
        """
        Validate table structure
        
        Args:
            table: Cleaned table data
            
        Returns:
            True if valid
        """
        if not table or len(table) < 2:
            return False
        
        # Check minimum dimensions
        if len(table[0]) < 1:
            return False
        
        # Check for meaningful content
        non_empty_cells = sum(
            1 for row in table 
            for cell in row 
            if cell and cell.strip()
        )
        
        total_cells = sum(len(row) for row in table)
        
        if total_cells == 0:
            return False
        
        # At least 30% cells should have content
        return (non_empty_cells / total_cells) >= 0.3
