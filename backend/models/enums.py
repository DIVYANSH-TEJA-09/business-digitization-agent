"""
Enumeration types for the application
"""
from enum import Enum


class FileType(str, Enum):
    """
    Supported file types
    """
    # Documents
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    
    # Spreadsheets
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    
    # Images
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    
    # Videos
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    
    # Other
    UNKNOWN = "unknown"


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


class BusinessType(str, Enum):
    """
    Type of business
    """
    PRODUCT = "product"
    SERVICE = "service"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class JobStatus(str, Enum):
    """
    Job processing status
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentMessageType(str, Enum):
    """
    Types of inter-agent messages
    """
    FILE_DISCOVERED = "file_discovered"
    DOCUMENT_PARSED = "document_parsed"
    TABLE_EXTRACTED = "table_extracted"
    MEDIA_EXTRACTED = "media_extracted"
    IMAGE_ANALYZED = "image_analyzed"
    INDEX_BUILT = "index_built"
    PROFILE_MAPPED = "profile_mapped"
    VALIDATION_COMPLETE = "validation_complete"
    ERROR = "error"
