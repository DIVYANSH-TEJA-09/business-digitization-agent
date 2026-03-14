"""
Unit tests for Pydantic schemas in backend.models.schemas.

Covers:
    - FileType / TableType / BusinessType enums
    - DocumentFile, ImageFile, FileCollection
    - Pricing (base_price ≥ 0, discount ≤ base, currency)
    - ContactInfo (email @-check)
    - BusinessProfile construction
    - ValidationResult
    - JobStatus defaults
    - StructuredTable
    - PageIndexNode (self-referencing)
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    BusinessInfo,
    BusinessProfile,
    BusinessType,
    ContactInfo,
    DataProvenance,
    DocumentFile,
    DocumentIndex,
    ExtractionMetadata,
    FAQ,
    FieldScore,
    FileCollection,
    FileType,
    ImageFile,
    InventoryInfo,
    Itinerary,
    JobStatus,
    Location,
    MediaCollection,
    Page,
    PageIndexNode,
    PageReference,
    ParsedDocument,
    Pricing,
    Product,
    Service,
    ServiceDetails,
    Specifications,
    StructuredTable,
    TableMetadata,
    TableType,
    TravelInfo,
    ValidationError as BizValidationError,
    ValidationResult,
    WorkingHours,
)


# =============================================================================
# Enum tests
# =============================================================================

class TestEnums:

    def test_filetype_values(self):
        assert FileType.PDF == "pdf"
        assert FileType.DOCX == "docx"
        assert FileType.XLSX == "xlsx"
        assert FileType.MP4 == "mp4"
        assert FileType.UNKNOWN == "unknown"

    def test_tabletype_values(self):
        assert TableType.PRICING == "pricing"
        assert TableType.ITINERARY == "itinerary"
        assert TableType.GENERAL == "general"

    def test_businesstype_values(self):
        assert BusinessType.PRODUCT == "product"
        assert BusinessType.SERVICE == "service"
        assert BusinessType.MIXED == "mixed"
        assert BusinessType.UNKNOWN == "unknown"


# =============================================================================
# DocumentFile
# =============================================================================

class TestDocumentFile:

    def test_create_minimal(self):
        doc = DocumentFile(
            file_path="/tmp/test.pdf",
            file_type=FileType.PDF,
            file_size=1024,
            original_name="test.pdf",
        )
        assert doc.file_path == "/tmp/test.pdf"
        assert doc.file_type == FileType.PDF

    def test_file_id_auto_generated(self):
        doc = DocumentFile(
            file_path="/tmp/a.pdf",
            file_type=FileType.PDF,
            file_size=100,
            original_name="a.pdf",
        )
        assert doc.file_id is not None
        assert len(doc.file_id) > 0

    def test_negative_file_size_raises(self):
        with pytest.raises(ValidationError):
            DocumentFile(
                file_path="/tmp/a.pdf",
                file_type=FileType.PDF,
                file_size=-1,
                original_name="a.pdf",
            )

    def test_discovered_at_auto_set(self):
        doc = DocumentFile(
            file_path="/tmp/a.pdf",
            file_type=FileType.PDF,
            file_size=100,
            original_name="a.pdf",
        )
        assert isinstance(doc.discovered_at, datetime)


# =============================================================================
# ImageFile
# =============================================================================

class TestImageFile:

    def test_create_with_dimensions(self):
        img = ImageFile(
            file_path="/tmp/logo.png",
            file_type=FileType.PNG,
            width=800,
            height=600,
            file_size=50000,
            mime_type="image/png",
            original_name="logo.png",
        )
        assert img.width == 800
        assert img.height == 600

    def test_dimensions_optional(self):
        img = ImageFile(
            file_path="/tmp/logo.png",
            file_type=FileType.PNG,
            file_size=50000,
            original_name="logo.png",
        )
        assert img.width is None
        assert img.height is None


# =============================================================================
# FileCollection
# =============================================================================

class TestFileCollection:

    def test_defaults(self):
        fc = FileCollection(job_id="test-job")
        assert fc.documents == []
        assert fc.images == []
        assert fc.total_files == 0

    def test_model_dump_has_expected_keys(self):
        fc = FileCollection(job_id="test-job")
        d = fc.model_dump()
        assert "job_id" in d
        assert "documents" in d
        assert "directory_structure" in d


# =============================================================================
# Pricing
# =============================================================================

class TestPricing:

    def test_valid_pricing(self):
        p = Pricing(base_price=1000.0, currency="INR", discount_price=800.0)
        assert p.base_price == 1000.0
        assert p.discount_price == 800.0

    def test_discount_exceeds_base_raises(self):
        with pytest.raises(ValidationError):
            Pricing(base_price=1000.0, discount_price=1500.0)

    def test_negative_base_price_raises(self):
        with pytest.raises(ValidationError):
            Pricing(base_price=-100.0)

    def test_discount_equals_base_is_ok(self):
        p = Pricing(base_price=1000.0, discount_price=1000.0)
        assert p.discount_price == 1000.0

    def test_default_currency(self):
        p = Pricing(base_price=500.0)
        assert p.currency == "INR"


# =============================================================================
# ContactInfo
# =============================================================================

class TestContactInfo:

    def test_valid_email(self):
        c = ContactInfo(email="info@trekotrip.in")
        assert c.email == "info@trekotrip.in"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            ContactInfo(email="not-an-email")

    def test_none_email_is_fine(self):
        c = ContactInfo(email=None)
        assert c.email is None

    def test_social_media_default_empty(self):
        c = ContactInfo()
        assert c.social_media == {}


# =============================================================================
# Page & ParsedDocument
# =============================================================================

class TestPage:

    def test_page_number_ge_1(self):
        p = Page(number=1, text="Hello")
        assert p.number == 1

    def test_page_number_zero_raises(self):
        with pytest.raises(ValidationError):
            Page(number=0, text="Hello")

    def test_page_default_tables_empty(self):
        p = Page(number=1)
        assert p.tables == []


class TestParsedDocument:

    def test_create_parsed_doc(self):
        doc = ParsedDocument(
            source_file="/tmp/doc.pdf",
            file_type=FileType.PDF,
        )
        assert doc.source_file == "/tmp/doc.pdf"
        assert doc.pages == []
        assert doc.full_text == ""

    def test_doc_id_auto_generated(self):
        doc = ParsedDocument(
            source_file="/tmp/doc.pdf",
            file_type=FileType.PDF,
        )
        assert doc.doc_id is not None


# =============================================================================
# StructuredTable
# =============================================================================

class TestStructuredTable:

    def test_defaults(self):
        t = StructuredTable()
        assert t.headers == []
        assert t.rows == []
        assert t.table_type == TableType.UNKNOWN

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            StructuredTable(confidence=1.5)

        with pytest.raises(ValidationError):
            StructuredTable(confidence=-0.1)

    def test_valid_confidence(self):
        t = StructuredTable(confidence=0.75)
        assert t.confidence == 0.75


# =============================================================================
# BusinessProfile
# =============================================================================

class TestBusinessProfile:

    def test_default_business_type(self):
        profile = BusinessProfile()
        assert profile.business_type == BusinessType.UNKNOWN

    def test_profile_id_auto_generated(self):
        profile = BusinessProfile()
        assert profile.profile_id is not None

    def test_products_none_by_default(self):
        profile = BusinessProfile()
        assert profile.products is None

    def test_services_none_by_default(self):
        profile = BusinessProfile()
        assert profile.services is None

    def test_model_dump_json(self):
        profile = BusinessProfile()
        json_str = profile.model_dump_json()
        assert "profile_id" in json_str
        assert "business_type" in json_str


# =============================================================================
# ValidationResult
# =============================================================================

class TestValidationResult:

    def test_defaults(self):
        r = ValidationResult()
        assert r.is_valid is True
        assert r.errors == []
        assert r.warnings == []
        assert r.completeness_score == 0.0

    def test_completeness_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            ValidationResult(completeness_score=1.5)

        with pytest.raises(ValidationError):
            ValidationResult(completeness_score=-0.1)


# =============================================================================
# JobStatus
# =============================================================================

class TestJobStatus:

    def test_defaults(self):
        job = JobStatus(job_id="abc123")
        assert job.status == "queued"
        assert job.progress == 0.0
        assert job.error_message is None

    def test_progress_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            JobStatus(job_id="x", progress=101.0)
        with pytest.raises(ValidationError):
            JobStatus(job_id="x", progress=-1.0)


# =============================================================================
# PageIndexNode (self-referencing)
# =============================================================================

class TestPageIndexNode:

    def test_leaf_node(self):
        node = PageIndexNode(
            title="Chapter 1",
            node_id="n1",
            start_index=1,
            end_index=10,
        )
        assert node.nodes == []

    def test_nested_nodes(self):
        child = PageIndexNode(
            title="Sub-section",
            node_id="n2",
            start_index=1,
            end_index=5,
        )
        parent = PageIndexNode(
            title="Section",
            node_id="n1",
            start_index=1,
            end_index=20,
            nodes=[child],
        )
        assert len(parent.nodes) == 1
        assert parent.nodes[0].title == "Sub-section"


# =============================================================================
# Itinerary
# =============================================================================

class TestItinerary:

    def test_day_ge_1(self):
        it = Itinerary(day=1)
        assert it.day == 1

    def test_day_zero_raises(self):
        with pytest.raises(ValidationError):
            Itinerary(day=0)

    def test_defaults(self):
        it = Itinerary(day=1)
        assert it.activities == []
        assert it.meals == []


# =============================================================================
# InventoryInfo
# =============================================================================

class TestInventoryInfo:

    def test_negative_quantity_raises(self):
        with pytest.raises(ValidationError):
            InventoryInfo(quantity=-5)

    def test_zero_quantity_ok(self):
        inv = InventoryInfo(quantity=0)
        assert inv.quantity == 0


# =============================================================================
# BusinessInfo average_rating
# =============================================================================

class TestBusinessInfo:

    def test_valid_rating(self):
        bi = BusinessInfo(average_rating=4.5)
        assert bi.average_rating == 4.5

    def test_rating_above_5_raises(self):
        with pytest.raises(ValidationError):
            BusinessInfo(average_rating=5.1)

    def test_rating_below_0_raises(self):
        with pytest.raises(ValidationError):
            BusinessInfo(average_rating=-1.0)

    def test_none_rating_ok(self):
        bi = BusinessInfo(average_rating=None)
        assert bi.average_rating is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
