"""
Module: schemas.py
Purpose: All Pydantic data models for the business digitization pipeline.

Defines schemas for file classification, document parsing, table extraction,
media handling, indexing, business profiles, products, services, and validation.
All fields are optional by default unless business-critical.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class FileType(str, Enum):
    """Supported file types for processing."""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    UNKNOWN = "unknown"


class TableType(str, Enum):
    """Types of tables detected in documents."""
    PRICING = "pricing"
    ITINERARY = "itinerary"
    SPECIFICATIONS = "specifications"
    INVENTORY = "inventory"
    SCHEDULE = "schedule"
    MENU = "menu"
    GENERAL = "general"
    UNKNOWN = "unknown"


class ImageCategory(str, Enum):
    """Image categorization from vision analysis."""
    PRODUCT = "product"
    SERVICE = "service"
    FOOD = "food"
    DESTINATION = "destination"
    PERSON = "person"
    DOCUMENT = "document"
    LOGO = "logo"
    OTHER = "other"


class BusinessType(str, Enum):
    """Type of business detected."""
    PRODUCT = "product"
    SERVICE = "service"
    MIXED = "mixed"
    UNKNOWN = "unknown"


# =============================================================================
# FILE CLASSIFICATION SCHEMAS
# =============================================================================

def _generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())[:12]


class DocumentFile(BaseModel):
    """Metadata for a discovered document file."""
    file_id: str = Field(default_factory=_generate_id)
    file_path: str
    file_type: FileType
    file_size: int = Field(ge=0)
    original_name: str
    mime_type: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.now)


class ImageFile(BaseModel):
    """Metadata for a discovered image file."""
    file_id: str = Field(default_factory=_generate_id)
    file_path: str
    file_type: FileType
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: int = Field(ge=0)
    mime_type: str = ""
    original_name: str


class FileCollection(BaseModel):
    """Collection of all classified files from a ZIP extraction."""
    job_id: str
    documents: List[DocumentFile] = []
    spreadsheets: List[DocumentFile] = []
    images: List[ImageFile] = []
    videos: List[DocumentFile] = []
    unknown: List[DocumentFile] = []
    total_files: int = 0
    directory_structure: Dict[str, Any] = {}
    discovery_metadata: Dict[str, Any] = {}


# =============================================================================
# DOCUMENT PARSING SCHEMAS
# =============================================================================

class Page(BaseModel):
    """Single page extracted from a document."""
    number: int = Field(ge=1)
    text: str = ""
    tables: List[List[List[str]]] = []  # Raw table data: rows of cells
    images: List[Dict[str, Any]] = []   # Embedded image metadata
    width: Optional[float] = None
    height: Optional[float] = None
    metadata: Dict[str, Any] = {}


class DocumentMetadata(BaseModel):
    """Document-level metadata."""
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    page_count: int = 0
    file_size: int = 0
    language: Optional[str] = None


class ParsedDocument(BaseModel):
    """Complete parsed document with all extracted content."""
    doc_id: str = Field(default_factory=_generate_id)
    source_file: str
    file_type: FileType
    pages: List[Page] = []
    total_pages: int = 0
    full_text: str = ""  # Combined text from all pages
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    parsing_errors: List[str] = []
    parsed_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# TABLE SCHEMAS
# =============================================================================

class TableMetadata(BaseModel):
    """Context and metadata for an extracted table."""
    surrounding_text: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    detection_method: str = "rule-based"
    column_count: int = 0
    row_count: int = 0


class StructuredTable(BaseModel):
    """Extracted and structured table data."""
    table_id: str = Field(default_factory=_generate_id)
    source_doc: str = ""
    source_page: int = 0
    headers: List[str] = []
    rows: List[List[str]] = []
    table_type: TableType = TableType.UNKNOWN
    context: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: TableMetadata = Field(default_factory=TableMetadata)


# =============================================================================
# MEDIA SCHEMAS
# =============================================================================

class ExtractedImage(BaseModel):
    """An extracted or standalone image."""
    image_id: str = Field(default_factory=_generate_id)
    file_path: str
    source_doc: Optional[str] = None
    source_page: Optional[int] = None
    width: int = 0
    height: int = 0
    file_size: int = 0
    mime_type: str = ""
    extraction_method: str = "standalone"  # "embedded" | "standalone"
    is_embedded: bool = False
    image_hash: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ImageAnalysis(BaseModel):
    """Vision model analysis results for an image."""
    image_id: str
    description: str = ""
    category: ImageCategory = ImageCategory.OTHER
    tags: List[str] = []
    is_product: bool = False
    is_service_related: bool = False
    suggested_associations: List[str] = []
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    analyzed_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}


class MediaCollection(BaseModel):
    """All extracted media from a job."""
    images: List[ExtractedImage] = []
    videos: List[DocumentFile] = []
    total_count: int = 0
    extraction_summary: Dict[str, Any] = {}


# =============================================================================
# INDEXING SCHEMAS (PageIndex-compatible)
# =============================================================================

class PageReference(BaseModel):
    """Reference to a page in the index."""
    doc_id: str
    page_number: int
    snippet: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class TableReference(BaseModel):
    """Reference to a table in the index."""
    table_id: str
    doc_id: str
    page_number: int
    table_type: TableType = TableType.UNKNOWN
    snippet: str = ""


class MediaReference(BaseModel):
    """Reference to media in the index."""
    media_id: str
    media_type: str = "image"
    category: Optional[ImageCategory] = None
    description: str = ""


class PageIndexNode(BaseModel):
    """A node in the PageIndex tree structure."""
    title: str
    node_id: str
    start_index: int  # Start page number
    end_index: int    # End page number
    summary: str = ""
    nodes: List[PageIndexNode] = []  # Child nodes


# Self-referencing model needs update_forward_refs
PageIndexNode.model_rebuild()


class DocumentIndex(BaseModel):
    """PageIndex tree for a single document."""
    doc_id: str
    source_file: str
    tree: Optional[PageIndexNode] = None
    description: str = ""
    total_pages: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# BUSINESS PROFILE SCHEMAS
# =============================================================================

class Location(BaseModel):
    """Business location details."""
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    landmark: Optional[str] = None


class ContactInfo(BaseModel):
    """Business contact information."""
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    social_media: Dict[str, str] = {}

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class WorkingHours(BaseModel):
    """Business operating hours."""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    special_hours: Dict[str, str] = {}


class BusinessInfo(BaseModel):
    """Core business profile information."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[Location] = None
    contact: Optional[ContactInfo] = None
    working_hours: Optional[WorkingHours] = None
    payment_methods: List[str] = []
    fulfillment_info: Optional[str] = None
    reviews_summary: Optional[str] = None
    average_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    tags: List[str] = []
    media: List[str] = []  # Image IDs


# =============================================================================
# PRODUCT SCHEMA
# =============================================================================

class Pricing(BaseModel):
    """Product/service pricing information."""
    base_price: Optional[float] = Field(default=None, ge=0.0)
    currency: str = "INR"
    discount_price: Optional[float] = Field(default=None, ge=0.0)
    price_range: Optional[str] = None
    price_type: Optional[str] = None

    @field_validator("discount_price")
    @classmethod
    def validate_discount(cls, v: Optional[float], info) -> Optional[float]:
        base = info.data.get("base_price")
        if v is not None and base is not None and v > base:
            raise ValueError("Discount price cannot exceed base price")
        return v


class Specifications(BaseModel):
    """Product specifications."""
    dimensions: Optional[str] = None
    weight: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    custom_specs: Dict[str, str] = {}


class InventoryInfo(BaseModel):
    """Product inventory status."""
    in_stock: Optional[bool] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    availability: Optional[str] = None
    restock_date: Optional[str] = None


class Product(BaseModel):
    """A single product in the inventory."""
    product_id: str = Field(default_factory=_generate_id)
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    media: List[str] = []
    pricing: Optional[Pricing] = None
    specifications: Optional[Specifications] = None
    inventory: Optional[InventoryInfo] = None
    warranty: Optional[str] = None
    cancellation_policy: Optional[str] = None
    refund_policy: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


# =============================================================================
# SERVICE SCHEMA
# =============================================================================

class Itinerary(BaseModel):
    """Service itinerary entry (e.g., for tours)."""
    day: int = Field(ge=1)
    title: Optional[str] = None
    activities: List[str] = []
    meals: List[str] = []
    accommodation: Optional[str] = None
    notes: Optional[str] = None


class ServiceDetails(BaseModel):
    """Additional service-specific details."""
    duration: Optional[str] = None
    group_size: Optional[str] = None
    best_time: Optional[str] = None
    difficulty_level: Optional[str] = None
    age_requirement: Optional[str] = None


class TravelInfo(BaseModel):
    """Travel-specific information for service businesses."""
    nearby_landmarks: List[str] = []
    festivals: List[str] = []
    local_food: List[str] = []
    what_to_carry: List[str] = []
    languages_spoken: List[str] = []
    risk_and_safety: Optional[str] = None


class FAQ(BaseModel):
    """Frequently asked question."""
    question: str
    answer: str


class Service(BaseModel):
    """A single service in the inventory."""
    service_id: str = Field(default_factory=_generate_id)
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    media: List[str] = []
    pricing: Optional[Pricing] = None
    details: Optional[ServiceDetails] = None
    itinerary: List[Itinerary] = []
    travel_info: Optional[TravelInfo] = None
    faqs: List[FAQ] = []
    cancellation_policy: Optional[str] = None
    payment_policy: Optional[str] = None
    inclusions: List[str] = []
    exclusions: List[str] = []
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


# =============================================================================
# BUSINESS PROFILE (TOP-LEVEL OUTPUT)
# =============================================================================

class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""
    extraction_date: datetime = Field(default_factory=datetime.now)
    processing_time_seconds: Optional[float] = None
    source_files_count: int = 0
    llm_calls_made: int = 0
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_method: str = "agentic"
    version: str = "1.0"


class DataProvenance(BaseModel):
    """Track source of extracted data for traceability."""
    field_name: str
    source_doc: Optional[str] = None
    source_page: Optional[int] = None
    extraction_method: str = "llm"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class BusinessProfile(BaseModel):
    """Complete business digitization output."""
    profile_id: str = Field(default_factory=_generate_id)
    business_type: BusinessType = BusinessType.UNKNOWN
    business_info: BusinessInfo = Field(default_factory=BusinessInfo)
    products: Optional[List[Product]] = None
    services: Optional[List[Service]] = None
    extraction_metadata: ExtractionMetadata = Field(
        default_factory=ExtractionMetadata
    )
    data_provenance: List[DataProvenance] = []


# =============================================================================
# VALIDATION SCHEMAS
# =============================================================================

class ValidationError(BaseModel):
    """A single validation error or warning."""
    field: str
    error_type: str
    message: str
    severity: str = "warning"  # "error" | "warning"


class FieldScore(BaseModel):
    """Completeness score for a field category."""
    category: str
    total_fields: int
    populated_fields: int
    score: float = Field(default=0.0, ge=0.0, le=1.0)


class ValidationResult(BaseModel):
    """Validation output with completeness scoring."""
    is_valid: bool = True
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    field_scores: Dict[str, FieldScore] = {}
    validated_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# API SCHEMAS
# =============================================================================

class JobStatus(BaseModel):
    """Pipeline job status."""
    job_id: str
    status: str = "queued"  # queued | processing | completed | failed
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    current_phase: Optional[str] = None
    message: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
