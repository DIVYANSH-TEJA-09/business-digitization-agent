"""
Module: file_classifier.py
Purpose: Classify files by type using MIME detection and extension mapping.

Uses a two-tier approach:
1. Extension-based detection (fast, reliable for known extensions)
2. MIME type detection as validation/fallback
"""

import mimetypes
from pathlib import Path
from typing import Tuple

from backend.models.schemas import FileType
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Extension to FileType mapping (primary detection method)
EXTENSION_MAP: dict[str, FileType] = {
    # Documents
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".doc": FileType.DOC,
    # Spreadsheets
    ".xlsx": FileType.XLSX,
    ".xls": FileType.XLS,
    ".csv": FileType.CSV,
    # Images
    ".jpg": FileType.JPG,
    ".jpeg": FileType.JPEG,
    ".png": FileType.PNG,
    ".gif": FileType.GIF,
    ".webp": FileType.WEBP,
    # Videos
    ".mp4": FileType.MP4,
    ".avi": FileType.AVI,
    ".mov": FileType.MOV,
    ".mkv": FileType.MKV,
}

# File type groupings
DOCUMENT_TYPES = {FileType.PDF, FileType.DOCX, FileType.DOC}
SPREADSHEET_TYPES = {FileType.XLSX, FileType.XLS, FileType.CSV}
IMAGE_TYPES = {FileType.JPG, FileType.JPEG, FileType.PNG, FileType.GIF, FileType.WEBP}
VIDEO_TYPES = {FileType.MP4, FileType.AVI, FileType.MOV, FileType.MKV}

# Files/folders to skip during discovery
SKIP_PATTERNS = {
    "__MACOSX",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".git",
    "__pycache__",
}


def classify_file(file_path: str) -> Tuple[FileType, str]:
    """
    Determine the FileType and MIME type of a file.

    Uses extension-based detection (fast, reliable) with MIME
    type as secondary validation.

    Args:
        file_path: Path to the file to classify

    Returns:
        Tuple of (FileType enum, MIME type string)
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    # Extension-based detection (primary)
    file_type = EXTENSION_MAP.get(extension, FileType.UNKNOWN)

    # MIME type detection
    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "application/octet-stream"

    if file_type == FileType.UNKNOWN:
        logger.debug(
            f"Unknown file type for '{path.name}' "
            f"(ext='{extension}', mime='{mime_type}')"
        )

    return file_type, mime_type


def is_document(file_type: FileType) -> bool:
    """Check if FileType is a document type."""
    return file_type in DOCUMENT_TYPES


def is_spreadsheet(file_type: FileType) -> bool:
    """Check if FileType is a spreadsheet type."""
    return file_type in SPREADSHEET_TYPES


def is_image(file_type: FileType) -> bool:
    """Check if FileType is an image type."""
    return file_type in IMAGE_TYPES


def is_video(file_type: FileType) -> bool:
    """Check if FileType is a video type."""
    return file_type in VIDEO_TYPES


def should_skip(file_path: str) -> bool:
    """
    Check if a file or directory should be skipped during discovery.

    Skips OS metadata files, hidden directories, and other non-content files.

    Args:
        file_path: Path string to check

    Returns:
        True if the file should be skipped
    """
    path = Path(file_path)

    # Skip hidden files (starting with .)
    if path.name.startswith("."):
        return True

    # Skip known junk patterns
    for pattern in SKIP_PATTERNS:
        if pattern in path.parts or path.name == pattern:
            return True

    # Skip empty files
    if path.is_file() and path.stat().st_size == 0:
        return True

    return False


def get_file_category(file_type: FileType) -> str:
    """
    Get the broad category for a file type.

    Returns:
        One of: "document", "spreadsheet", "image", "video", "unknown"
    """
    if is_document(file_type):
        return "document"
    elif is_spreadsheet(file_type):
        return "spreadsheet"
    elif is_image(file_type):
        return "image"
    elif is_video(file_type):
        return "video"
    return "unknown"
