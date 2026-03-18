"""
File type classification using multiple strategies
"""
import os
import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum

from backend.models.enums import FileType


class FileClassifier:
    """
    Multi-strategy file type classifier
    
    Strategies (in order):
    1. MIME type detection (python-magic if available)
    2. Extension-based classification
    3. Magic number validation (for images)
    """
    
    # Extension to FileType mapping
    EXTENSION_MAP = {
        # Documents
        '.pdf': FileType.PDF,
        '.doc': FileType.DOC,
        '.docx': FileType.DOCX,
        
        # Spreadsheets
        '.xls': FileType.XLS,
        '.xlsx': FileType.XLSX,
        '.csv': FileType.CSV,
        
        # Images
        '.jpg': FileType.JPG,
        '.jpeg': FileType.JPEG,
        '.png': FileType.PNG,
        '.gif': FileType.GIF,
        '.webp': FileType.WEBP,
        
        # Videos
        '.mp4': FileType.MP4,
        '.avi': FileType.AVI,
        '.mov': FileType.MOV,
        '.mkv': FileType.MKV,
    }
    
    # MIME type to FileType mapping
    MIME_MAP = {
        # Documents
        'application/pdf': FileType.PDF,
        'application/msword': FileType.DOC,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileType.DOCX,
        
        # Spreadsheets
        'application/vnd.ms-excel': FileType.XLS,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileType.XLSX,
        'text/csv': FileType.CSV,
        'text/comma-separated-values': FileType.CSV,
        
        # Images
        'image/jpeg': FileType.JPG,
        'image/png': FileType.PNG,
        'image/gif': FileType.GIF,
        'image/webp': FileType.WEBP,
        
        # Videos
        'video/mp4': FileType.MP4,
        'video/x-msvideo': FileType.AVI,
        'video/quicktime': FileType.MOV,
        'video/x-matroska': FileType.MKV,
    }
    
    # Magic numbers for common file types (first few bytes)
    MAGIC_NUMBERS = {
        b'%PDF': FileType.PDF,
        b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': FileType.DOC,  # OLE compound (old DOC)
        b'PK\x03\x04': None,  # ZIP-based (DOCX, XLSX - need further check)
        b'\xff\xd8\xff': FileType.JPG,
        b'\x89PNG\r\n\x1a\n': FileType.PNG,
        b'GIF87a': FileType.GIF,
        b'GIF89a': FileType.GIF,
        b'RIFF': None,  # Could be AVI or WEBP
    }
    
    def __init__(self):
        # Initialize mimetypes
        mimetypes.init()
        
        # Try to import python-magic (optional)
        self.magic_available = False
        try:
            import magic
            self.magic = magic
            self.magic_available = True
        except ImportError:
            pass
    
    def classify_file(self, file_path: str) -> Tuple[FileType, Optional[str]]:
        """
        Classify file using multiple strategies
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (FileType, mime_type)
        """
        path = Path(file_path)
        
        if not path.exists():
            return FileType.UNKNOWN, None
        
        # Strategy 1: MIME type detection (python-magic)
        if self.magic_available:
            try:
                mime_type = self._detect_mime_with_magic(file_path)
                if mime_type:
                    file_type = self.MIME_MAP.get(mime_type)
                    if file_type:
                        return file_type, mime_type
            except Exception:
                pass  # Fall through to next strategy
        
        # Strategy 2: Extension-based classification
        file_type, mime_type = self._classify_by_extension(path)
        if file_type != FileType.UNKNOWN:
            return file_type, mime_type
        
        # Strategy 3: Magic number detection
        file_type = self._classify_by_magic_number(file_path)
        if file_type:
            # Get mime type from system for magic-based detection
            mime_type, _ = mimetypes.guess_type(str(path))
            return file_type, mime_type
        
        # Strategy 4: mimetypes library fallback
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type:
            file_type = self.MIME_MAP.get(mime_type)
            if file_type:
                return file_type, mime_type
        
        # All strategies failed
        return FileType.UNKNOWN, None
    
    def _detect_mime_with_magic(self, file_path: str) -> Optional[str]:
        """
        Detect MIME type using python-magic
        """
        if not self.magic_available:
            return None
        
        try:
            mime = self.magic.Magic(mime=True)
            return mime.from_file(file_path)
        except Exception:
            return None
    
    def _classify_by_extension(self, path: Path) -> Tuple[FileType, Optional[str]]:
        """
        Classify file by extension
        """
        extension = path.suffix.lower()
        
        if extension in self.EXTENSION_MAP:
            file_type = self.EXTENSION_MAP[extension]
            mime_type, _ = mimetypes.guess_type(str(path))
            return file_type, mime_type
        
        return FileType.UNKNOWN, None
    
    def _classify_by_magic_number(self, file_path: str) -> Optional[FileType]:
        """
        Classify file by reading magic numbers
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # Read first 16 bytes
                
                # Check for exact matches
                for magic_bytes, file_type in self.MAGIC_NUMBERS.items():
                    if header.startswith(magic_bytes):
                        if file_type is not None:
                            return file_type
                        
                        # Special handling for ZIP-based formats
                        if magic_bytes == b'PK\x03\x04':
                            return self._identify_zip_based_file(file_path)
                        
                        # Special handling for RIFF (AVI or WEBP)
                        if magic_bytes == b'RIFF':
                            if len(header) > 12 and header[8:12] == b'AVI ':
                                return FileType.AVI
                            elif len(header) > 12 and header[8:12] == b'WEBP':
                                return FileType.WEBP
                
                return None
                
        except (IOError, OSError):
            return None
    
    def _identify_zip_based_file(self, file_path: str) -> Optional[FileType]:
        """
        Identify ZIP-based file types (DOCX, XLSX, etc.)
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Use extension as hint for ZIP-based formats
        if extension in self.EXTENSION_MAP:
            return self.EXTENSION_MAP[extension]
        
        # Try to inspect ZIP contents
        try:
            import zipfile
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                names = zip_file.namelist()
                
                # Check for Word document markers
                if any('word/' in name for name in names):
                    return FileType.DOCX
                
                # Check for Excel workbook markers
                if any('xl/' in name for name in names):
                    return FileType.XLSX
                    
        except (zipfile.BadZipFile, Exception):
            pass
        
        return None
    
    def is_supported_type(self, file_type: FileType) -> bool:
        """
        Check if file type is supported for processing
        """
        return file_type != FileType.UNKNOWN
    
    def get_category(self, file_type: FileType) -> str:
        """
        Get category for file type
        """
        if file_type in [FileType.PDF, FileType.DOC, FileType.DOCX]:
            return "document"
        elif file_type in [FileType.XLS, FileType.XLSX, FileType.CSV]:
            return "spreadsheet"
        elif file_type in [FileType.JPG, FileType.JPEG, FileType.PNG, FileType.GIF, FileType.WEBP]:
            return "image"
        elif file_type in [FileType.MP4, FileType.AVI, FileType.MOV, FileType.MKV]:
            return "video"
        else:
            return "unknown"
