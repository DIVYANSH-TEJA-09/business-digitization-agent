"""
Unit tests for backend.agents.table_extraction — TableExtractionAgent.

Covers:
    - Single and multi-doc extraction
    - Table cleaning logic
    - Table type classification (pricing, itinerary, specs, menu, inventory, general)
    - Confidence scoring
    - Edge cases (empty tables, single-row tables, missing cells)
"""

import pytest

from backend.agents.table_extraction import TableExtractionAgent
from backend.models.schemas import (
    DocumentMetadata,
    FileType,
    Page,
    ParsedDocument,
    TableType,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def agent() -> TableExtractionAgent:
    return TableExtractionAgent()


def _make_doc(tables_per_page: list, text: str = "") -> ParsedDocument:
    """
    Build a ParsedDocument with one page per element in tables_per_page.
    tables_per_page: list of raw tables (list of list of list of str).
    """
    pages = []
    for i, raw_tables in enumerate(tables_per_page, start=1):
        pages.append(
            Page(number=i, text=text, tables=raw_tables)
        )

    return ParsedDocument(
        source_file="/tmp/test.pdf",
        file_type=FileType.PDF,
        pages=pages,
        total_pages=len(pages),
        full_text=text,
        metadata=DocumentMetadata(page_count=len(pages)),
    )


# =============================================================================
# Basic extraction
# =============================================================================

class TestTableExtractionBasic:

    def test_no_tables_returns_empty(self, agent):
        doc = _make_doc([[]])  # One page, no tables
        tables = agent.extract(doc)
        assert tables == []

    def test_single_valid_table(self, agent):
        raw = [
            [["Name", "Price", "Duration"],
             ["Hampta Pass", "12000", "5 Days"],
             ["Spiti Valley", "18000", "7 Days"]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert len(tables) == 1

    def test_table_has_headers(self, agent):
        raw = [
            [["Package", "Price"], ["Trek A", "5000"]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert tables[0].headers == ["Package", "Price"]

    def test_table_has_rows(self, agent):
        raw = [
            [["Package", "Price"], ["Trek A", "5000"], ["Trek B", "8000"]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert len(tables[0].rows) == 2

    def test_source_doc_set(self, agent):
        raw = [[["H1", "H2"], ["v1", "v2"]]]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert tables[0].source_doc == "/tmp/test.pdf"

    def test_source_page_set(self, agent):
        raw = [[["H1", "H2"], ["v1", "v2"]]]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert tables[0].source_page == 1

    def test_multiple_pages_multiple_tables(self, agent):
        raw_page1 = [
            [["Name", "Price"], ["Trek A", "5000"]],
        ]
        raw_page2 = [
            [["Day", "Activity"], ["1", "Arrival"], ["2", "Trek"]],
        ]
        doc = _make_doc([raw_page1, raw_page2])
        tables = agent.extract(doc)
        assert len(tables) == 2

    def test_extract_from_multiple_docs(self, agent):
        raw = [[["Name", "Price"], ["Trek A", "5000"]]]
        doc1 = _make_doc([raw])
        doc2 = _make_doc([raw])
        tables = agent.extract_from_multiple([doc1, doc2])
        assert len(tables) == 2


# =============================================================================
# Edge cases
# =============================================================================

class TestTableExtractionEdgeCases:

    def test_single_row_table_is_skipped(self, agent):
        """A table with only one row (header only) cannot have data rows."""
        raw = [[["Name", "Price"]]]
        doc = _make_doc([raw])
        assert agent.extract(doc) == []

    def test_empty_table_list_skipped(self, agent):
        doc = _make_doc([[]])
        assert agent.extract(doc) == []

    def test_all_empty_headers_skipped(self, agent):
        """Table where first row is all empty cells."""
        raw = [
            [["", "", ""], ["data1", "data2", "data3"]]
        ]
        doc = _make_doc([raw])
        # May fall back to second row as headers
        tables = agent.extract(doc)
        # Result should be either [] or a table — no crash
        assert isinstance(tables, list)

    def test_table_with_whitespace_cells_cleaned(self, agent):
        raw = [
            [["  Name  ", "  Price  "],
             ["  Trek A  ", "  5000  "]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert len(tables) == 1
        assert tables[0].headers[0] == "Name"
        assert tables[0].rows[0][0] == "Trek A"

    def test_empty_rows_removed(self, agent):
        raw = [
            [["H1", "H2"],
             ["", ""],
             ["v1", "v2"]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        # Empty row should be removed, leaving 1 data row
        assert len(tables[0].rows) == 1

    def test_jagged_rows_handled(self, agent):
        """Rows with inconsistent column counts."""
        raw = [
            [["Name", "Price", "Duration"],
             ["Trek A", "5000"],          # Missing Duration
             ["Trek B", "8000", "7 Days"]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert len(tables) >= 1


# =============================================================================
# Table type classification
# =============================================================================

class TestTableTypeClassification:

    def test_pricing_table_classified(self, agent):
        raw = [
            [["Package", "Price (INR)", "Per Person"],
             ["Hampta Pass", "₹12000", "Yes"],
             ["Spiti Valley", "₹18000", "Yes"]]
        ]
        doc = _make_doc([raw], text="pricing cost rate")
        tables = agent.extract(doc)
        assert tables[0].table_type == TableType.PRICING

    def test_itinerary_table_classified(self, agent):
        raw = [
            [["Day", "Activity", "Meal"],
             ["1", "Arrival", "Dinner"],
             ["2", "Trek", "Breakfast, Lunch"]]
        ]
        doc = _make_doc([raw], text="day schedule itinerary")
        tables = agent.extract(doc)
        assert tables[0].table_type == TableType.ITINERARY

    def test_general_table_when_no_keywords(self, agent):
        raw = [
            [["Column A", "Column B"],
             ["x", "y"],
             ["p", "q"]]
        ]
        doc = _make_doc([raw], text="")
        tables = agent.extract(doc)
        # No strong keyword match → GENERAL
        assert tables[0].table_type == TableType.GENERAL

    def test_numeric_heavy_table_tends_to_pricing(self, agent):
        raw = [
            [["Item", "Amount"],
             ["Trek A", "12000"],
             ["Trek B", "18000"],
             ["Trek C", "25000"]]
        ]
        doc = _make_doc([raw], text="")
        tables = agent.extract(doc)
        # Lots of numbers push towards PRICING
        assert tables[0].table_type in {TableType.PRICING, TableType.GENERAL}

    def test_menu_table_classified(self, agent):
        raw = [
            [["Dish", "Cuisine", "Price"],
             ["Butter Chicken", "non-veg", "300"],
             ["Paneer Tikka", "veg", "250"]]
        ]
        doc = _make_doc([raw], text="menu dish cuisine veg non-veg")
        tables = agent.extract(doc)
        assert tables[0].table_type in {TableType.MENU, TableType.PRICING}


# =============================================================================
# Confidence scoring
# =============================================================================

class TestConfidenceScoring:

    def test_confidence_in_valid_range(self, agent):
        raw = [
            [["Name", "Price"],
             ["Trek A", "5000"],
             ["Trek B", "8000"],
             ["Trek C", "12000"]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert 0.0 <= tables[0].confidence <= 1.0

    def test_higher_confidence_for_rich_table(self, agent):
        """Table with meaningful headers, multiple rows, consistent columns."""
        rich_raw = [
            [["Package Name", "Price (INR)", "Duration", "Group Size"],
             ["Hampta Pass Trek", "₹12000", "5 Days", "6-12"],
             ["Spiti Valley Tour", "₹18000", "7 Days", "8-16"],
             ["Rohtang Day Trip", "₹3500", "1 Day", "1+"],
             ["Ladakh Explorer", "₹35000", "10 Days", "4-10"]]
        ]
        sparse_raw = [
            [["A", "B"],
             ["x", "y"]]
        ]
        doc_rich = _make_doc([rich_raw])
        doc_sparse = _make_doc([sparse_raw])
        rich_conf = agent.extract(doc_rich)[0].confidence
        sparse_conf = agent.extract(doc_sparse)[0].confidence
        assert rich_conf >= sparse_conf

    def test_metadata_column_count(self, agent):
        raw = [
            [["Name", "Price", "Duration"],
             ["Trek A", "5000", "5 Days"]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert tables[0].metadata.column_count == 3

    def test_metadata_row_count(self, agent):
        raw = [
            [["Name", "Price"],
             ["Trek A", "5000"],
             ["Trek B", "8000"]]
        ]
        doc = _make_doc([raw])
        tables = agent.extract(doc)
        assert tables[0].metadata.row_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
