"""
Pydantic schemas for data validation and serialization
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .enums import FileType, TableType, ImageCategory, BusinessType, JobStatus


# =============================================================================
# File Discovery Schemas
# =============================================================================

class DocumentFile(BaseModel):
    """
    Document file metadata (PDF, DOCX, DOC)
    """
    file_id: str = Field(..., description="Unique file identifier")
    file_path: str = Field(..., description="Absolute path to extracted file")
    file_type: FileType = Field(..., description="Detected file type")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    original_name: str = Field(..., description="Original filename from ZIP")
    mime_type: Optional[str] = Field(None, description="MIME type")
    relative_path: str = Field(..., description="Path relative to extraction root")
    discovered_at: datetime = Field(default_factory=datetime.now)


class DocumentParsingInput(BaseModel):
    """
    Input to Document Parsing Agent
    """
    documents: List[DocumentFile] = Field(default_factory=list)
    job_id: str = Field(..., description="Unique job identifier")
    enable_ocr: bool = Field(default=True, description="Enable OCR fallback")


class SpreadsheetFile(BaseModel):
    """
    Spreadsheet file metadata (XLSX, XLS, CSV)
    """
    file_id: str
    file_path: str
    file_type: FileType
    file_size: int = Field(..., gt=0)
    original_name: str
    mime_type: Optional[str]
    relative_path: str
    discovered_at: datetime = Field(default_factory=datetime.now)


class ImageFile(BaseModel):
    """
    Image file metadata
    """
    file_id: str
    file_path: str
    file_type: FileType
    file_size: int = Field(..., gt=0)
    original_name: str
    mime_type: str
    relative_path: str
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    discovered_at: datetime = Field(default_factory=datetime.now)


class VideoFile(BaseModel):
    """
    Video file metadata
    """
    file_id: str
    file_path: str
    file_type: FileType
    file_size: int = Field(..., gt=0)
    original_name: str
    mime_type: str
    relative_path: str
    duration: Optional[float] = Field(None, description="Duration in seconds")
    discovered_at: datetime = Field(default_factory=datetime.now)


class UnknownFile(BaseModel):
    """
    Unknown/unsupported file type
    """
    file_id: str
    file_path: str
    file_type: FileType = FileType.UNKNOWN
    file_size: int = Field(..., gt=0)
    original_name: str
    mime_type: Optional[str]
    relative_path: str
    discovered_at: datetime = Field(default_factory=datetime.now)


class DirectoryNode(BaseModel):
    """
    Directory tree node
    """
    name: str
    path: str
    is_file: bool = False
    children: List['DirectoryNode'] = Field(default_factory=list)
    
    model_config = {
        'extra': 'allow'
    }


# Fix recursive reference
DirectoryNode.model_rebuild()


class DiscoveryMetadata(BaseModel):
    """
    Metadata about the discovery process
    """
    zip_file_path: str
    job_id: str
    extraction_started_at: datetime = Field(default_factory=datetime.now)
    extraction_completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    total_files: int = 0
    total_size_bytes: int = 0
    compression_ratio: Optional[float] = None


class FileDiscoveryInput(BaseModel):
    """
    Input to File Discovery Agent
    """
    zip_file_path: str = Field(..., description="Absolute path to uploaded ZIP")
    job_id: str = Field(..., description="Unique job identifier")
    max_file_size: int = Field(default=524288000, description="Max file size in bytes (500MB)")
    max_files: int = Field(default=100, description="Max files per ZIP")


class FileDiscoveryOutput(BaseModel):
    """
    Output from File Discovery Agent
    """
    job_id: str
    success: bool
    
    # Classified files
    documents: List[DocumentFile] = Field(default_factory=list)
    spreadsheets: List[SpreadsheetFile] = Field(default_factory=list)
    images: List[ImageFile] = Field(default_factory=list)
    videos: List[VideoFile] = Field(default_factory=list)
    unknown: List[UnknownFile] = Field(default_factory=list)
    
    # Structure
    directory_tree: Optional[DirectoryNode] = None
    
    # Metadata
    total_files: int = 0
    extraction_dir: Optional[str] = None
    processing_time: float = 0.0
    errors: List[str] = Field(default_factory=list)
    
    # Summary for logging
    summary: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Document Parsing Schemas (Preview)
# =============================================================================

class Page(BaseModel):
    """
    Single page from a document
    """
    number: int = Field(..., ge=1)
    text: str = ""
    tables: List[List[List[str]]] = Field(default_factory=list)
    images: List[dict] = Field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentMetadata(BaseModel):
    """
    Document-level metadata
    """
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    page_count: int = 0
    file_size: int = 0
    language: Optional[str] = None


class ParsedDocument(BaseModel):
    """
    Complete parsed document
    """
    doc_id: str
    source_file: str
    file_type: FileType
    pages: List[Page]
    total_pages: int
    metadata: DocumentMetadata
    parsing_errors: List[str] = Field(default_factory=list)
    parsed_at: datetime = Field(default_factory=datetime.now)


class DocumentParsingOutput(BaseModel):
    """
    Output from Document Parsing Agent
    """
    job_id: str
    success: bool
    parsed_documents: List[ParsedDocument] = Field(default_factory=list)
    total_pages: int = 0
    total_tables: int = 0
    total_images: int = 0
    processing_time: float = 0.0
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# Table Schemas
# =============================================================================

class TableMetadata(BaseModel):
    """
    Table context and metadata
    """
    surrounding_text: str = ""
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    detection_method: str = "rule-based"
    column_count: int = 0
    row_count: int = 0


class StructuredTable(BaseModel):
    """
    Extracted and structured table
    """
    table_id: str
    source_doc: str
    source_page: int
    headers: List[str]
    rows: List[List[str]]
    table_type: TableType
    context: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    metadata: TableMetadata


class TableExtractionInput(BaseModel):
    """
    Input to Table Extraction Agent
    """
    parsed_documents: List[ParsedDocument] = Field(default_factory=list)
    job_id: str = Field(..., description="Unique job identifier")


class TableExtractionOutput(BaseModel):
    """
    Output from Table Extraction Agent
    """
    job_id: str
    success: bool
    tables: List[StructuredTable] = Field(default_factory=list)
    total_tables: int = 0
    tables_by_type: Dict[str, int] = Field(default_factory=dict)
    processing_time: float = 0.0
    errors: List[str] = Field(default_factory=list)


class MediaExtractionInput(BaseModel):
    """
    Input to Media Extraction Agent
    """
    parsed_documents: List[ParsedDocument] = Field(default_factory=list)
    standalone_files: List[str] = Field(default_factory=list)
    job_id: str = Field(..., description="Unique job identifier")


class ExtractedImage(BaseModel):
    """
    Extracted or standalone image
    """
    image_id: str
    file_path: str
    source_doc: Optional[str] = None
    source_page: Optional[int] = None
    width: int
    height: int
    file_size: int
    mime_type: str
    extraction_method: str  # "embedded_pdf" | "embedded_docx" | "standalone"
    is_embedded: bool
    image_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MediaCollection(BaseModel):
    """
    All extracted media
    """
    images: List[ExtractedImage] = Field(default_factory=list)
    videos: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    extraction_summary: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        'arbitrary_types_allowed': True
    }


class MediaExtractionOutput(BaseModel):
    """
    Output from Media Extraction Agent
    """
    job_id: str
    success: bool
    media: MediaCollection
    total_images: int = 0
    duplicates_removed: int = 0
    processing_time: float = 0.0
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# Indexing Schemas (Preview)
# =============================================================================

class ImageAnalysis(BaseModel):
    """
    Vision model analysis results
    """
    image_id: str
    description: str
    category: ImageCategory  # Use enum type
    tags: List[str] = Field(default_factory=list)
    is_product: bool = False
    is_service_related: bool = False
    suggested_associations: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VisionAnalysisInput(BaseModel):
    """
    Input to Vision Agent
    """
    image: ExtractedImage
    context: str = ""
    job_id: str = ""


class VisionAnalysisOutput(BaseModel):
    """
    Output from Vision Agent
    """
    job_id: str
    success: bool
    analyses: List[ImageAnalysis] = Field(default_factory=list)
    total_images: int = 0
    processing_time: float = 0.0
    errors: List[str] = Field(default_factory=list)


class PageReference(BaseModel):
    """
    Reference to a page in the index
    """
    doc_id: str
    page_number: int
    snippet: str = ""
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)


class TreeNode(BaseModel):
    """
    Tree node for hierarchical indexing (PageIndex-style)
    """
    title: str
    node_id: str
    start_page: int = 0
    end_page: int = 0
    summary: str = ""
    keywords: List[str] = Field(default_factory=list)
    children: List['TreeNode'] = Field(default_factory=list)
    doc_id: str = ""
    content_snippet: str = ""
    
    model_config = {
        'extra': 'allow',
        'json_schema_extra': {
            'recursive': True
        }
    }


class PageIndex(BaseModel):
    """
    Vectorless hierarchical index (PageIndex-style tree structure)
    """
    documents: Dict[str, ParsedDocument] = Field(default_factory=dict)
    tree_root: Optional[TreeNode] = None  # Hierarchical tree
    page_index: Dict[str, List[PageReference]] = Field(default_factory=dict)  # Flat keyword index
    table_index: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    media_index: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IndexingInput(BaseModel):
    """
    Input to Indexing Agent
    """
    parsed_documents: List[ParsedDocument] = Field(default_factory=list)
    tables: List[StructuredTable] = Field(default_factory=list)
    images: List[ExtractedImage] = Field(default_factory=list)
    job_id: str = Field(..., description="Unique job identifier")


class IndexingOutput(BaseModel):
    """
    Output from Indexing Agent
    """
    job_id: str
    success: bool
    page_index: PageIndex
    total_keywords: int = 0
    processing_time: float = 0.0
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# Business Profile Schemas
# =============================================================================

class Location(BaseModel):
    """
    Business location details
    """
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    landmark: Optional[str] = None


class ContactInfo(BaseModel):
    """
    Contact information
    """
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    social_media: Dict[str, str] = Field(default_factory=dict)


class WorkingHours(BaseModel):
    """
    Business operating hours
    """
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    special_hours: Dict[str, str] = Field(default_factory=dict)


class BusinessInfo(BaseModel):
    """
    Core business profile information
    """
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[Location] = None
    contact: Optional[ContactInfo] = None
    working_hours: Optional[WorkingHours] = None
    payment_methods: List[str] = Field(default_factory=list)
    fulfillment_info: Optional[str] = None
    reviews_summary: Optional[str] = None
    average_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    tags: List[str] = Field(default_factory=list)
    media: List[str] = Field(default_factory=list)


class ExtractionMetadata(BaseModel):
    """
    Metadata about the extraction process
    """
    extraction_date: datetime = Field(default_factory=datetime.now)
    processing_time: Optional[float] = None
    source_files_count: int = 0
    llm_calls_made: int = 0
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    extraction_method: str = "agentic"
    version: str = "1.0"


class BusinessProfile(BaseModel):
    """
    Complete business digitization output
    """
    profile_id: str
    business_type: BusinessType
    business_info: BusinessInfo
    products: Optional[List[Dict[str, Any]]] = None
    services: Optional[List[Dict[str, Any]]] = None
    extraction_metadata: ExtractionMetadata
    data_provenance: List[Dict[str, Any]] = Field(default_factory=list)


class Pricing(BaseModel):
    """
    Product/service pricing
    """
    base_price: Optional[float] = Field(None, ge=0.0)
    currency: str = "USD"
    discount_price: Optional[float] = Field(None, ge=0.0)
    price_range: Optional[str] = None
    price_type: Optional[str] = None


class Product(BaseModel):
    """
    Product inventory item
    """
    product_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    pricing: Optional[Pricing] = None
    specifications: Optional[Dict[str, Any]] = None
    inventory: Optional[Dict[str, Any]] = None
    warranty: Optional[str] = None
    cancellation_policy: Optional[str] = None
    refund_policy: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class Service(BaseModel):
    """
    Service inventory item
    """
    service_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    pricing: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None
    itinerary: List[Dict[str, Any]] = Field(default_factory=list)
    travel_info: Optional[Dict[str, Any]] = None
    faqs: List[Dict[str, Any]] = Field(default_factory=list)
    cancellation_policy: Optional[str] = None
    payment_policy: Optional[str] = None
    inclusions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


# =============================================================================
# Schema Mapping Agent Schemas
# =============================================================================

class SchemaMappingInput(BaseModel):
    """
    Input to Schema Mapping Agent
    """
    page_index: PageIndex
    job_id: str = Field(..., description="Unique job identifier")


class SchemaMappingOutput(BaseModel):
    """
    Output from Schema Mapping Agent
    """
    job_id: str
    success: bool
    profile: Optional[BusinessProfile] = None
    processing_time: float = 0.0
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# Validation Schemas
# =============================================================================

class ValidationError(BaseModel):
    """
    Single validation error
    """
    field: str
    error_type: str
    message: str
    severity: str  # "error" | "warning"


class ValidationInput(BaseModel):
    """
    Input to Validation Agent
    """
    profile: Optional[BusinessProfile] = None
    job_id: str = Field(..., description="Unique job identifier")


class ValidationOutput(BaseModel):
    """
    Output from Validation Agent
    """
    job_id: str
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)
    completeness_score: float = Field(0.0, ge=0.0, le=1.0)
    field_scores: Dict[str, float] = Field(default_factory=dict)
    validated_profile: Optional[BusinessProfile] = None
    validated_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Validation Schemas (Preview)
# =============================================================================

class ValidationError(BaseModel):
    """
    Single validation error
    """
    field: str
    error_type: str
    message: str
    severity: str


class ValidationResult(BaseModel):
    """
    Validation output
    """
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)
    completeness_score: float = Field(0.0, ge=0.0, le=1.0)
    field_scores: Dict[str, float] = Field(default_factory=dict)
    validated_at: datetime = Field(default_factory=datetime.now)
    validated_profile: BusinessProfile


# =============================================================================
# Job Management Schemas
# =============================================================================

class JobStatusModel(BaseModel):
    """
    Job status tracking
    """
    job_id: str
    status: JobStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    current_phase: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
