"""
Integration test: exercises File Discovery → Parsing → Table Extraction
→ Validation using the real sample ZIP (trekotrip - Activities-Business.zip).

Does NOT require LLM services (Groq/Ollama) — tests only the deterministic
pipeline stages to verify parsers and agents work with real business data.

Run with:  python -m pytest tests/integration/test_pipeline_offline.py -v
"""

import os
from pathlib import Path

import pytest

from backend.agents.file_discovery import FileDiscoveryAgent
from backend.agents.table_extraction import TableExtractionAgent
from backend.models.schemas import BusinessProfile, BusinessType, FileType
from backend.parsers.parser_factory import parser_factory
from backend.utils.text_utils import text_to_markdown, tables_to_markdown
from backend.validation.schema_validator import SchemaValidator


# Path to the sample ZIP
SAMPLE_ZIP = str(
    Path(__file__).resolve().parents[2]
    / "test_data"
    / "trekotrip - Activities-Business.zip"
)


@pytest.fixture(scope="module")
def file_collection():
    """Run file discovery on the sample ZIP (once per module)."""
    if not os.path.exists(SAMPLE_ZIP):
        pytest.skip(f"Sample ZIP not found: {SAMPLE_ZIP}")
    agent = FileDiscoveryAgent()
    return agent.discover(SAMPLE_ZIP, job_id="integration-test")


class TestFileDiscoveryIntegration:
    """Test file discovery on the real sample ZIP."""

    def test_has_files(self, file_collection):
        assert file_collection.total_files > 0, "ZIP should contain files"

    def test_has_documents_or_spreadsheets(self, file_collection):
        total_parsable = (
            len(file_collection.documents)
            + len(file_collection.spreadsheets)
        )
        assert total_parsable > 0, "Should find at least one parsable doc"

    def test_file_types_classified(self, file_collection):
        """All discovered files should have a valid FileType."""
        for doc in file_collection.documents:
            assert doc.file_type != FileType.UNKNOWN

    def test_directory_structure(self, file_collection):
        assert file_collection.directory_structure is not None

    def test_no_junk_files(self, file_collection):
        """Junk files should not appear in any category."""
        junk_names = {"__MACOSX", ".DS_Store", "Thumbs.db"}
        for doc in file_collection.documents:
            assert not any(
                junk in doc.original_name for junk in junk_names
            )


class TestDocumentParsing:
    """Test parsing documents from the sample ZIP."""

    @pytest.fixture(scope="class")
    def parsed_docs(self, file_collection):
        """Parse all discovered documents and spreadsheets."""
        docs = []
        for doc_file in file_collection.documents:
            try:
                parsed = parser_factory.parse(
                    doc_file.file_path, doc_file.file_type
                )
                docs.append(parsed)
            except Exception as e:
                print(f"WARNING: Parse failed for {doc_file.original_name}: {e}")
        for sheet_file in file_collection.spreadsheets:
            try:
                parsed = parser_factory.parse(
                    sheet_file.file_path, sheet_file.file_type
                )
                docs.append(parsed)
            except Exception as e:
                print(f"WARNING: Parse failed for {sheet_file.original_name}: {e}")
        return docs

    def test_has_parsed_docs(self, parsed_docs):
        assert len(parsed_docs) > 0, "At least one doc should parse"

    def test_has_text(self, parsed_docs):
        texts = [doc.full_text for doc in parsed_docs if doc.full_text]
        assert len(texts) > 0, "Should extract text from at least one doc"

    def test_text_not_empty(self, parsed_docs):
        for doc in parsed_docs:
            if doc.full_text:
                assert len(doc.full_text) > 10, (
                    f"Text too short for {doc.source_file}"
                )


class TestTableExtraction:
    """Test table extraction from parsed docs."""

    @pytest.fixture(scope="class")
    def tables(self, parsed_docs):
        agent = TableExtractionAgent()
        return agent.extract_from_multiple(parsed_docs)

    @pytest.fixture(scope="class")
    def parsed_docs(self, file_collection):
        docs = []
        for doc_file in file_collection.documents:
            try:
                docs.append(
                    parser_factory.parse(doc_file.file_path, doc_file.file_type)
                )
            except Exception:
                pass
        for sheet_file in file_collection.spreadsheets:
            try:
                docs.append(
                    parser_factory.parse(sheet_file.file_path, sheet_file.file_type)
                )
            except Exception:
                pass
        return docs

    def test_table_extraction(self, tables):
        """Should extract tables from business documents."""
        # Travel business docs often have pricing/itinerary tables
        print(f"Extracted {len(tables)} tables")
        for t in tables:
            print(f"  - {t.table_type.value}: {t.headers[:3]}... ({len(t.rows)} rows)")

    def test_tables_have_headers(self, tables):
        for t in tables:
            assert len(t.headers) > 0, "Table should have headers"

    def test_tables_have_type(self, tables):
        for t in tables:
            assert t.table_type is not None


class TestMarkdownConversion:
    """Test Markdown generation for PageIndex consumption."""

    @pytest.fixture(scope="class")
    def parsed_docs(self, file_collection):
        docs = []
        for doc_file in file_collection.documents:
            try:
                docs.append(
                    parser_factory.parse(doc_file.file_path, doc_file.file_type)
                )
            except Exception:
                pass
        return docs

    def test_text_to_markdown(self, parsed_docs):
        for doc in parsed_docs:
            if doc.full_text:
                md = text_to_markdown(doc.full_text, source_file=doc.source_file)
                assert len(md) > 0, "Markdown should not be empty"
                assert md.startswith("#"), "Markdown should start with heading"

    def test_tables_to_markdown(self, parsed_docs):
        for doc in parsed_docs:
            for page in doc.pages:
                if page.tables:
                    md = tables_to_markdown(page.tables)
                    assert "|" in md, "Markdown table should contain pipes"


class TestValidation:
    """Test validation on a mock profile."""

    def test_empty_profile_validation(self):
        validator = SchemaValidator()
        profile = BusinessProfile()
        result = validator.validate(profile)
        assert result is not None
        assert 0 <= result.completeness_score <= 1.0

    def test_populated_profile_validation(self):
        from backend.models.schemas import BusinessInfo, Product, Pricing

        validator = SchemaValidator()
        profile = BusinessProfile(
            business_type=BusinessType.PRODUCT,
            business_info=BusinessInfo(
                name="TrekoTrip Adventures",
                description="Travel and activities company",
                category="Travel & Tourism",
            ),
            products=[
                Product(
                    name="Mountain Trek",
                    description="3-day mountain trekking adventure",
                    pricing=Pricing(base_price=5000, currency="INR"),
                )
            ],
        )
        result = validator.validate(profile)
        assert result.is_valid is True
        assert result.completeness_score > 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
