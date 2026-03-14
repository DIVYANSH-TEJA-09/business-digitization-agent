"""
Shared pytest fixtures for the business-digitization-agent test suite.

Available fixtures:
    sample_zip_path       — creates a realistic in-memory ZIP and returns its path
    empty_zip_path        — a valid but empty ZIP
    corrupted_zip_path    — a file that looks like a ZIP but is not
    tmp_storage_dir       — temporary directory used as storage root
    business_profile      — a fully populated BusinessProfile
    empty_profile         — a minimal (empty) BusinessProfile
    parsed_doc            — a minimal ParsedDocument with one page
    structured_tables     — a list of StructuredTable objects
"""

import zipfile
from pathlib import Path
from typing import List

import pytest

from backend.models.schemas import (
    BusinessInfo,
    BusinessProfile,
    BusinessType,
    ContactInfo,
    DocumentMetadata,
    ExtractionMetadata,
    InventoryInfo,
    Itinerary,
    Location,
    Page,
    ParsedDocument,
    Pricing,
    Product,
    Service,
    ServiceDetails,
    Specifications,
    StructuredTable,
    TableMetadata,
    TableType,
    FileType,
    WorkingHours,
)


# ---------------------------------------------------------------------------
# ZIP fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_zip_path(tmp_path_factory) -> str:
    """Create a realistic sample ZIP with mixed file types."""
    tmp = tmp_path_factory.mktemp("zips")
    zip_path = tmp / "sample_business.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("brochure.pdf", b"%PDF-1.4 fake pdf content for testing " * 20)
        zf.writestr("menu.docx", b"PK fake docx content " * 10)
        zf.writestr("prices.xlsx", b"PK fake xlsx content " * 10)
        zf.writestr("photos/logo.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
        zf.writestr("photos/product1.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 200)
        zf.writestr("videos/promo.mp4", b"Fake video content " * 5)
        zf.writestr("notes.txt", b"Some plain text notes")
        # Junk that must be filtered
        zf.writestr("__MACOSX/._brochure.pdf", b"Mac metadata")
        zf.writestr(".DS_Store", b"Mac stuff")

    return str(zip_path)


@pytest.fixture(scope="session")
def empty_zip_path(tmp_path_factory) -> str:
    """A valid ZIP with no contents."""
    tmp = tmp_path_factory.mktemp("zips")
    zip_path = tmp / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        pass
    return str(zip_path)


@pytest.fixture(scope="session")
def corrupted_zip_path(tmp_path_factory) -> str:
    """A file that is not a valid ZIP."""
    tmp = tmp_path_factory.mktemp("zips")
    bad = tmp / "not_a_zip.zip"
    bad.write_bytes(b"This is definitely not a zip file at all!")
    return str(bad)


# ---------------------------------------------------------------------------
# Business profile fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def business_profile() -> BusinessProfile:
    """A fully populated BusinessProfile for validation / schema tests."""
    return BusinessProfile(
        business_type=BusinessType.MIXED,
        business_info=BusinessInfo(
            name="TrekoTrip Adventures",
            description="Trekking and adventure travel company based in India.",
            category="Travel & Tourism",
            location=Location(
                address="123, MG Road",
                city="Bangalore",
                state="Karnataka",
                country="India",
                postal_code="560001",
            ),
            contact=ContactInfo(
                phone="+91-9876543210",
                email="info@trekotrip.in",
                website="https://www.trekotrip.in",
            ),
            working_hours=WorkingHours(
                monday="9:00 AM - 6:00 PM",
                tuesday="9:00 AM - 6:00 PM",
                saturday="10:00 AM - 4:00 PM",
                sunday="Closed",
            ),
            payment_methods=["UPI", "Credit Card", "Bank Transfer"],
            tags=["trekking", "adventure", "travel", "india"],
        ),
        products=[
            Product(
                name="Trekking Pole",
                description="Lightweight aluminium trekking pole",
                category="Gear",
                pricing=Pricing(base_price=1200.0, currency="INR", discount_price=999.0),
                specifications=Specifications(
                    material="Aluminium",
                    weight="400g",
                    color="Black",
                ),
                inventory=InventoryInfo(in_stock=True, quantity=50),
                tags=["gear", "trekking", "pole"],
            )
        ],
        services=[
            Service(
                name="Hampta Pass Trek",
                description="5-day snow crossing from Manali to Lahaul.",
                category="High Altitude Trek",
                pricing=Pricing(base_price=12000.0, currency="INR"),
                details=ServiceDetails(
                    duration="5 days / 4 nights",
                    group_size="6-12 people",
                    best_time="June to September",
                    difficulty_level="Moderate",
                ),
                itinerary=[
                    Itinerary(
                        day=1,
                        title="Manali to Jobra",
                        activities=["Drive to Jobra", "Camp setup"],
                        meals=["Dinner"],
                        accommodation="Tent",
                    )
                ],
                inclusions=["Transport", "Guide", "Tent", "Meals"],
                exclusions=["Personal gear", "Insurance"],
                cancellation_policy="Full refund if cancelled 15 days before.",
            )
        ],
        extraction_metadata=ExtractionMetadata(
            source_files_count=3,
            llm_calls_made=4,
            confidence_score=0.85,
        ),
    )


@pytest.fixture()
def empty_profile() -> BusinessProfile:
    """A completely empty BusinessProfile (no fields filled)."""
    return BusinessProfile()


# ---------------------------------------------------------------------------
# Document / table fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def parsed_doc() -> ParsedDocument:
    """A single-page ParsedDocument with sample text and a raw table."""
    return ParsedDocument(
        source_file="/tmp/test_doc.pdf",
        file_type=FileType.PDF,
        pages=[
            Page(
                number=1,
                text=(
                    "TrekoTrip Adventures\n\n"
                    "PRICING\n"
                    "Hampta Pass Trek — ₹12,000 per person\n"
                    "Spiti Valley Tour — ₹18,000 per person\n\n"
                    "CONTACT\n"
                    "Email: info@trekotrip.in\n"
                    "Phone: +91-9876543210"
                ),
                tables=[
                    [
                        ["Package", "Duration", "Price (INR)", "Group Size"],
                        ["Hampta Pass", "5 Days", "12000", "6-12"],
                        ["Spiti Valley", "7 Days", "18000", "8-16"],
                        ["Rohtang Day", "1 Day", "3500", "1+"],
                    ]
                ],
            )
        ],
        total_pages=1,
        full_text=(
            "TrekoTrip Adventures\n"
            "PRICING\n"
            "Hampta Pass Trek — ₹12,000 per person\n"
            "Spiti Valley Tour — ₹18,000 per person\n"
            "CONTACT\n"
            "Email: info@trekotrip.in\n"
            "Phone: +91-9876543210"
        ),
        metadata=DocumentMetadata(title="TrekoTrip Brochure", page_count=1),
    )


@pytest.fixture()
def structured_tables() -> List[StructuredTable]:
    """A list of pre-built StructuredTable objects covering multiple types."""
    pricing_table = StructuredTable(
        source_doc="brochure.pdf",
        source_page=1,
        headers=["Package", "Price (INR)", "Duration"],
        rows=[
            ["Hampta Pass", "12000", "5 Days"],
            ["Spiti Valley", "18000", "7 Days"],
        ],
        table_type=TableType.PRICING,
        confidence=0.85,
        metadata=TableMetadata(
            column_count=3,
            row_count=2,
            confidence_score=0.85,
        ),
    )

    itinerary_table = StructuredTable(
        source_doc="itinerary.pdf",
        source_page=2,
        headers=["Day", "Activity", "Meal", "Accommodation"],
        rows=[
            ["1", "Arrival, Manali", "Dinner", "Hotel"],
            ["2", "Drive to Jobra", "Lunch, Dinner", "Tent"],
            ["3", "Hampta Pass crossing", "All meals", "Tent"],
        ],
        table_type=TableType.ITINERARY,
        confidence=0.80,
        metadata=TableMetadata(
            column_count=4,
            row_count=3,
        ),
    )

    general_table = StructuredTable(
        source_doc="misc.pdf",
        source_page=1,
        headers=["Item", "Details"],
        rows=[
            ["Cancellation", "Full refund if 15 days prior"],
            ["Payment", "50% advance"],
        ],
        table_type=TableType.GENERAL,
        confidence=0.60,
        metadata=TableMetadata(column_count=2, row_count=2),
    )

    return [pricing_table, itinerary_table, general_table]
