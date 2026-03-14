# Data Schema: Agentic Business Digitization Framework

## Schema Overview

This document defines all data structures used throughout the system, from input files to final business profiles. Schemas are defined using Pydantic for validation and type safety.

## Core Principles

1. **Required vs Optional**: Fields are optional by default unless explicitly business-critical
2. **No Fabrication**: Empty fields when data unavailable
3. **Data Provenance**: Track source of every extracted field
4. **Validation**: Type checking, format validation, business rules
5. **Extensibility**: Easy to add new fields without breaking existing data

## Input Schemas

### ZIP Upload Schema

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class ZIPUploadRequest(BaseModel):
    """
    Initial user upload request
    """
    file_path: str = Field(..., description="Path to uploaded ZIP file")
    original_filename: str = Field(..., description="Original ZIP filename")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    upload_timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None
    job_id: str = Field(..., description="Unique job identifier")
    
    @validator('file_size')
    def validate_size(cls, v):
        max_size = 500 * 1024 * 1024  # 500MB
        if v > max_size:
            raise ValueError(f"File size exceeds maximum of {max_size} bytes")
        return v
```

### File Classification Schemas

```python
from enum import Enum

class FileType(str, Enum):
    """
    Supported file types
    """
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
    UNKNOWN = "unknown"

class DocumentFile(BaseModel):
    """
    Document file metadata
    """
    file_id: str
    file_path: str
    file_type: FileType
    file_size: int
    original_name: str
    mime_type: Optional[str]
    discovered_at: datetime = Field(default_factory=datetime.now)

class ImageFile(BaseModel):
    """
    Image file metadata
    """
    file_id: str
    file_path: str
    file_type: FileType
    width: Optional[int]
    height: Optional[int]
    file_size: int
    mime_type: str
    original_name: str

class FileCollection(BaseModel):
    """
    Collection of classified files
    """
    documents: List[DocumentFile] = []
    spreadsheets: List[DocumentFile] = []
    images: List[ImageFile] = []
    videos: List[DocumentFile] = []
    unknown: List[DocumentFile] = []
    total_files: int
    discovery_metadata: dict = {}
```

## Document Parsing Schemas

### Parsed Document Schema

```python
class Page(BaseModel):
    """
    Single page from a document
    """
    number: int = Field(..., ge=1)
    text: str = ""
    tables: List[List[List[str]]] = []  # Raw table data
    images: List[dict] = []  # Embedded images
    width: Optional[float] = None
    height: Optional[float] = None
    metadata: dict = {}

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
    parsing_errors: List[str] = []
    parsed_at: datetime = Field(default_factory=datetime.now)
    
    @validator('total_pages')
    def validate_page_count(cls, v, values):
        if 'pages' in values and len(values['pages']) != v:
            raise ValueError("Page count mismatch")
        return v
```

### Table Schemas

```python
class TableType(str, Enum):
    """
    Types of tables detected
    """
    PRICING = "pricing"
    ITINERARY = "itinerary"
    SPECIFICATIONS = "specifications"
    INVENTORY = "inventory"
    SCHEDULE = "schedule"
    MENU = "menu"
    GENERAL = "general"
    UNKNOWN = "unknown"

class TableMetadata(BaseModel):
    """
    Table context and metadata
    """
    surrounding_text: str = ""
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    detection_method: str = "rule-based"
    column_count: int
    row_count: int

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
    
    @validator('headers')
    def validate_headers(cls, v):
        if not v:
            raise ValueError("Table must have at least one header")
        return v
```

### Media Schemas

```python
class ImageCategory(str, Enum):
    """
    Image categorization
    """
    PRODUCT = "product"
    SERVICE = "service"
    FOOD = "food"
    DESTINATION = "destination"
    PERSON = "person"
    DOCUMENT = "document"
    LOGO = "logo"
    OTHER = "other"

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
    extraction_method: str  # "embedded" | "standalone"
    is_embedded: bool
    image_hash: Optional[str] = None  # For deduplication

class ImageAnalysis(BaseModel):
    """
    Vision model analysis results
    """
    image_id: str
    description: str
    category: ImageCategory
    tags: List[str] = []
    is_product: bool = False
    is_service_related: bool = False
    suggested_associations: List[str] = []
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    analyzed_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = {}

class MediaCollection(BaseModel):
    """
    All extracted media
    """
    images: List[ExtractedImage] = []
    videos: List[DocumentFile] = []
    total_count: int
    extraction_summary: dict = {}
```

## Indexing Schemas

```python
class PageReference(BaseModel):
    """
    Reference to a page in the index
    """
    doc_id: str
    page_number: int
    snippet: str = ""  # Context snippet
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)

class TableReference(BaseModel):
    """
    Reference to a table in the index
    """
    table_id: str
    doc_id: str
    page_number: int
    table_type: TableType
    snippet: str = ""

class MediaReference(BaseModel):
    """
    Reference to media in the index
    """
    media_id: str
    media_type: str  # "image" | "video"
    category: Optional[ImageCategory] = None
    description: str = ""

class PageIndex(BaseModel):
    """
    Vectorless inverted index
    """
    documents: dict = {}  # doc_id -> ParsedDocument
    page_index: dict = {}  # keyword -> List[PageReference]
    table_index: dict = {}  # keyword -> List[TableReference]
    media_index: dict = {}  # keyword -> List[MediaReference]
    metadata: dict = {}
    
    def get_relevant_context(self, query_terms: List[str]) -> str:
        """
        Retrieve context for given search terms
        """
        # Implementation in indexing logic
        pass
```

## Business Profile Schemas

### Business Information Schema

```python
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
    social_media: dict = {}  # platform -> handle
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError("Invalid email format")
        return v

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
    special_hours: dict = {}  # For holidays, etc.

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
    payment_methods: List[str] = []
    fulfillment_info: Optional[str] = None
    reviews_summary: Optional[str] = None
    average_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    tags: List[str] = []
    media: List[str] = []  # References to image IDs
```

### Product Schema

```python
class Pricing(BaseModel):
    """
    Product/service pricing
    """
    base_price: Optional[float] = Field(None, ge=0.0)
    currency: str = "USD"
    discount_price: Optional[float] = Field(None, ge=0.0)
    price_range: Optional[str] = None  # "$10-$50"
    price_type: Optional[str] = None  # "per unit", "per hour", etc.
    
    @validator('discount_price')
    def validate_discount(cls, v, values):
        if v and 'base_price' in values and values['base_price']:
            if v > values['base_price']:
                raise ValueError("Discount price cannot exceed base price")
        return v

class Specifications(BaseModel):
    """
    Product specifications
    """
    dimensions: Optional[str] = None
    weight: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    custom_specs: dict = {}  # Additional specifications

class InventoryInfo(BaseModel):
    """
    Inventory status
    """
    in_stock: Optional[bool] = None
    quantity: Optional[int] = Field(None, ge=0)
    availability: Optional[str] = None
    restock_date: Optional[datetime] = None

class Product(BaseModel):
    """
    Product inventory item
    """
    product_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    media: List[str] = []  # Image IDs
    pricing: Optional[Pricing] = None
    specifications: Optional[Specifications] = None
    inventory: Optional[InventoryInfo] = None
    warranty: Optional[str] = None
    cancellation_policy: Optional[str] = None
    refund_policy: Optional[str] = None
    tags: List[str] = []
    metadata: dict = {}
```

### Service Schema

```python
class Itinerary(BaseModel):
    """
    Service itinerary (e.g., for tours)
    """
    day: int = Field(..., ge=1)
    title: Optional[str] = None
    activities: List[str] = []
    meals: List[str] = []
    accommodation: Optional[str] = None
    notes: Optional[str] = None

class ServiceDetails(BaseModel):
    """
    Additional service-specific details
    """
    duration: Optional[str] = None
    group_size: Optional[str] = None
    best_time: Optional[str] = None
    difficulty_level: Optional[str] = None
    age_requirement: Optional[str] = None

class TravelInfo(BaseModel):
    """
    Travel-specific information
    """
    nearby_landmarks: List[str] = []
    festivals: List[str] = []
    local_food: List[str] = []
    what_to_carry: List[str] = []
    languages_spoken: List[str] = []
    risk_and_safety: Optional[str] = None

class FAQ(BaseModel):
    """
    Frequently asked question
    """
    question: str
    answer: str

class Service(BaseModel):
    """
    Service inventory item
    """
    service_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    media: List[str] = []  # Image IDs
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
    metadata: dict = {}
```

### Business Profile Schema

```python
class BusinessType(str, Enum):
    """
    Type of business
    """
    PRODUCT = "product"
    SERVICE = "service"
    MIXED = "mixed"
    UNKNOWN = "unknown"

class ExtractionMetadata(BaseModel):
    """
    Metadata about the extraction process
    """
    extraction_date: datetime = Field(default_factory=datetime.now)
    processing_time: Optional[float] = None  # seconds
    source_files_count: int = 0
    llm_calls_made: int = 0
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    extraction_method: str = "agentic"
    version: str = "1.0"

class DataProvenance(BaseModel):
    """
    Track source of extracted data
    """
    field_name: str
    source_doc: Optional[str] = None
    source_page: Optional[int] = None
    extraction_method: str
    confidence: float = Field(0.0, ge=0.0, le=1.0)

class BusinessProfile(BaseModel):
    """
    Complete business digitization output
    """
    profile_id: str
    business_type: BusinessType
    business_info: BusinessInfo
    products: Optional[List[Product]] = None
    services: Optional[List[Service]] = None
    extraction_metadata: ExtractionMetadata
    data_provenance: List[DataProvenance] = []
    
    @validator('products')
    def validate_products(cls, v, values):
        if v and 'business_type' in values:
            if values['business_type'] == BusinessType.SERVICE:
                raise ValueError("Service-only business cannot have products")
        return v
    
    @validator('services')
    def validate_services(cls, v, values):
        if v and 'business_type' in values:
            if values['business_type'] == BusinessType.PRODUCT:
                raise ValueError("Product-only business cannot have services")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile_id": "prof_123",
                "business_type": "service",
                "business_info": {
                    "name": "Mountain Adventures Travel",
                    "description": "Premium tour packages...",
                    "location": {
                        "city": "Denver",
                        "state": "CO"
                    }
                },
                "services": [
                    {
                        "service_id": "srv_001",
                        "name": "Rocky Mountain Trek",
                        "pricing": {
                            "base_price": 1299.00,
                            "currency": "USD"
                        }
                    }
                ]
            }
        }
```

## Validation Schemas

```python
class ValidationError(BaseModel):
    """
    Single validation error
    """
    field: str
    error_type: str
    message: str
    severity: str  # "error" | "warning"

class FieldScore(BaseModel):
    """
    Completeness score for a field category
    """
    category: str
    total_fields: int
    populated_fields: int
    score: float = Field(ge=0.0, le=1.0)

class ValidationResult(BaseModel):
    """
    Validation output
    """
    is_valid: bool
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    completeness_score: float = Field(ge=0.0, le=1.0)
    field_scores: dict = {}  # category -> FieldScore
    validated_at: datetime = Field(default_factory=datetime.now)
    validated_profile: BusinessProfile
```

## API Request/Response Schemas

```python
class DigitizationRequest(BaseModel):
    """
    API request to start digitization
    """
    zip_file_path: str
    user_id: Optional[str] = None
    options: dict = {}

class DigitizationResponse(BaseModel):
    """
    API response for digitization request
    """
    job_id: str
    status: str  # "queued" | "processing" | "completed" | "failed"
    message: str
    created_at: datetime = Field(default_factory=datetime.now)

class JobStatus(BaseModel):
    """
    Job status query response
    """
    job_id: str
    status: str
    progress: float = Field(ge=0.0, le=100.0)
    current_phase: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None

class ProfileResponse(BaseModel):
    """
    Final profile retrieval response
    """
    job_id: str
    profile: BusinessProfile
    validation_result: ValidationResult
    generated_at: datetime
```

## Database Schemas (SQLite)

```sql
-- Jobs tracking table
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    user_id TEXT,
    zip_file_path TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL DEFAULT 0.0,
    current_phase TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Profiles table
CREATE TABLE profiles (
    profile_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    business_type TEXT,
    profile_data JSON NOT NULL,
    validation_data JSON,
    completeness_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Documents table
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    file_type TEXT,
    page_count INTEGER,
    parsed_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Media table
CREATE TABLE media (
    media_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    media_type TEXT,
    analysis_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Index for quick lookups
CREATE INDEX idx_job_status ON jobs(status);
CREATE INDEX idx_profile_job ON profiles(job_id);
CREATE INDEX idx_docs_job ON documents(job_id);
CREATE INDEX idx_media_job ON media(job_id);
```

## Schema Evolution Strategy

### Version 1.0 (Initial)
- Core business profile fields
- Product and service schemas
- Basic validation

### Future Versions
- **v1.1**: Multi-language support fields
- **v1.2**: Advanced inventory management
- **v1.3**: Customer reviews integration
- **v1.4**: Booking/scheduling fields

### Migration Strategy
```python
class SchemaVersion(BaseModel):
    """
    Schema version tracking
    """
    version: str
    migration_required: bool
    backward_compatible: bool

def migrate_profile(
    old_profile: dict, 
    from_version: str, 
    to_version: str
) -> BusinessProfile:
    """
    Migrate profile between schema versions
    """
    migrations = {
        "1.0->1.1": migrate_1_0_to_1_1,
        "1.1->1.2": migrate_1_1_to_1_2,
    }
    
    migration_key = f"{from_version}->{to_version}"
    if migration_key in migrations:
        return migrations[migration_key](old_profile)
    
    raise ValueError(f"No migration path from {from_version} to {to_version}")
```

## JSON Schema Export

The system can export JSON Schema for all models:

```python
# Export schemas for external validation
business_profile_schema = BusinessProfile.schema_json(indent=2)
product_schema = Product.schema_json(indent=2)
service_schema = Service.schema_json(indent=2)

# Save to files
with open('schemas/business_profile.json', 'w') as f:
    f.write(business_profile_schema)
```

## Conclusion

This comprehensive schema definition ensures:
- **Type safety** through Pydantic validation
- **Clear contracts** between system components
- **Data integrity** through validators and constraints
- **Extensibility** for future enhancements
- **Documentation** via schema examples and descriptions

All agents operate on these well-defined schemas, ensuring consistent data flow throughout the system.
