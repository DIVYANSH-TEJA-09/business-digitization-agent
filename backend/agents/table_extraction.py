"""
Module: table_extraction.py
Purpose: Table Extraction Agent — detects, classifies, and structures tables.

Takes parsed documents and extracts structured table data with
type classification (pricing, itinerary, specs, etc.).
"""

import re
from typing import List, Optional

from backend.models.schemas import (
    ParsedDocument,
    StructuredTable,
    TableMetadata,
    TableType,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Keywords for table type classification
PRICING_KEYWORDS = {
    "price", "cost", "rate", "fee", "amount", "total", "subtotal",
    "discount", "charge", "rs", "inr", "usd", "$", "₹", "mrp",
    "per person", "per night", "per unit",
}

ITINERARY_KEYWORDS = {
    "day", "date", "time", "schedule", "itinerary", "departure",
    "arrival", "morning", "afternoon", "evening", "night",
    "activity", "meal", "breakfast", "lunch", "dinner",
}

SPEC_KEYWORDS = {
    "specification", "dimension", "weight", "size", "material",
    "color", "model", "capacity", "power", "voltage", "features",
}

MENU_KEYWORDS = {
    "item", "dish", "cuisine", "ingredient", "veg", "non-veg",
    "starter", "main course", "dessert", "beverage",
}

INVENTORY_KEYWORDS = {
    "stock", "quantity", "available", "sku", "inventory",
    "in stock", "out of stock", "units",
}


class TableExtractionAgent:
    """
    Agent for extracting and classifying tables from parsed documents.

    Workflow:
        1. Collect raw tables from parsed document pages
        2. Clean and validate each table
        3. Classify table type using header/content analysis
        4. Return structured table objects with metadata
    """

    def extract(self, parsed_doc: ParsedDocument) -> List[StructuredTable]:
        """
        Extract all tables from a parsed document.

        Args:
            parsed_doc: Document with raw tables in pages

        Returns:
            List of structured, classified tables
        """
        tables: List[StructuredTable] = []

        for page in parsed_doc.pages:
            for raw_table in page.tables:
                structured = self._structure_table(
                    raw_table=raw_table,
                    source_doc=parsed_doc.source_file,
                    source_page=page.number,
                    surrounding_text=page.text[:500],
                )

                if structured:
                    tables.append(structured)

        logger.info(
            f"Extracted {len(tables)} tables from "
            f"{parsed_doc.source_file}"
        )

        return tables

    def extract_from_multiple(
        self, parsed_docs: List[ParsedDocument]
    ) -> List[StructuredTable]:
        """Extract tables from multiple documents."""
        all_tables = []
        for doc in parsed_docs:
            all_tables.extend(self.extract(doc))
        return all_tables

    def _structure_table(
        self,
        raw_table: List[List[str]],
        source_doc: str,
        source_page: int,
        surrounding_text: str = "",
    ) -> Optional[StructuredTable]:
        """
        Convert a raw table into a structured table.

        Returns None if table is invalid or too small.
        """
        if not raw_table or len(raw_table) < 2:
            return None

        # Clean the table
        cleaned = self._clean_table(raw_table)
        if not cleaned or len(cleaned) < 2:
            return None

        # Extract headers (first row)
        headers = cleaned[0]
        rows = cleaned[1:]

        # Skip if headers are all empty
        if not any(h.strip() for h in headers):
            # Try second row as headers
            if len(cleaned) > 2:
                headers = cleaned[1]
                rows = cleaned[2:]
            else:
                return None

        # Classify table type
        table_type = self._classify_table(headers, rows, surrounding_text)

        # Calculate confidence
        confidence = self._calculate_confidence(headers, rows, table_type)

        return StructuredTable(
            source_doc=source_doc,
            source_page=source_page,
            headers=headers,
            rows=rows,
            table_type=table_type,
            context=surrounding_text[:200],
            confidence=confidence,
            metadata=TableMetadata(
                surrounding_text=surrounding_text[:500],
                confidence_score=confidence,
                column_count=len(headers),
                row_count=len(rows),
            ),
        )

    def _clean_table(self, raw_table: List[List[str]]) -> List[List[str]]:
        """
        Clean a raw table.

        - Strip whitespace from all cells
        - Remove completely empty rows
        - Remove completely empty columns
        - Normalize cell content
        """
        if not raw_table:
            return []

        # Strip cells
        cleaned = []
        for row in raw_table:
            clean_row = [
                str(cell).strip() if cell else ""
                for cell in row
            ]
            cleaned.append(clean_row)

        # Remove completely empty rows
        cleaned = [row for row in cleaned if any(cell for cell in row)]

        if not cleaned:
            return []

        # Find non-empty columns
        max_cols = max(len(row) for row in cleaned)
        non_empty_cols = set()
        for row in cleaned:
            for i, cell in enumerate(row):
                if cell:
                    non_empty_cols.add(i)

        # Remove empty columns
        if non_empty_cols and len(non_empty_cols) < max_cols:
            cleaned = [
                [row[i] if i < len(row) else "" for i in sorted(non_empty_cols)]
                for row in cleaned
            ]

        return cleaned

    def _classify_table(
        self,
        headers: List[str],
        rows: List[List[str]],
        context: str,
    ) -> TableType:
        """
        Classify table type based on headers, content, and context.

        Uses keyword matching on headers and cell values
        to determine the most likely table type.
        """
        # Combine headers and first few rows for analysis
        all_text = " ".join(headers).lower()
        for row in rows[:5]:
            all_text += " " + " ".join(row).lower()
        all_text += " " + context.lower()

        # Score each type
        scores = {
            TableType.PRICING: self._keyword_score(all_text, PRICING_KEYWORDS),
            TableType.ITINERARY: self._keyword_score(all_text, ITINERARY_KEYWORDS),
            TableType.SPECIFICATIONS: self._keyword_score(all_text, SPEC_KEYWORDS),
            TableType.MENU: self._keyword_score(all_text, MENU_KEYWORDS),
            TableType.INVENTORY: self._keyword_score(all_text, INVENTORY_KEYWORDS),
        }

        # Check for numeric patterns (pricing indicator)
        numeric_count = sum(
            1 for row in rows
            for cell in row
            if re.match(r"^[₹$]?\s*\d+[\d,]*\.?\d*$", cell.strip())
        )
        if numeric_count > len(rows) * 0.3:
            scores[TableType.PRICING] += 2

        # Find best match
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score >= 2:
            return best_type

        return TableType.GENERAL

    def _keyword_score(self, text: str, keywords: set) -> int:
        """Count how many keywords appear in text."""
        return sum(1 for kw in keywords if kw in text)

    def _calculate_confidence(
        self,
        headers: List[str],
        rows: List[List[str]],
        table_type: TableType,
    ) -> float:
        """Calculate confidence score for the extraction."""
        score = 0.5  # Base score

        # Has meaningful headers
        if any(len(h) > 2 for h in headers):
            score += 0.1

        # Consistent column count
        if rows:
            col_counts = [len(row) for row in rows]
            if len(set(col_counts)) == 1:
                score += 0.1

        # Multiple rows of data
        if len(rows) >= 3:
            score += 0.1

        # Classified to a specific type
        if table_type != TableType.GENERAL:
            score += 0.1

        # Cell fill rate
        total_cells = sum(len(row) for row in rows)
        filled_cells = sum(
            1 for row in rows for cell in row if cell.strip()
        )
        if total_cells > 0:
            fill_rate = filled_cells / total_cells
            score += fill_rate * 0.1

        return min(score, 1.0)
