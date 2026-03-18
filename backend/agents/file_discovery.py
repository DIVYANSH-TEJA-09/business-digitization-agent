"""
File Discovery Agent

Extracts ZIP files and classifies all contained files by type.
Implements security checks for path traversal, zip bombs, and corrupted files.
"""
import os
import zipfile
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from backend.models.schemas import (
    FileDiscoveryInput,
    FileDiscoveryOutput,
    DocumentFile,
    SpreadsheetFile,
    ImageFile,
    VideoFile,
    UnknownFile,
    DirectoryNode,
    DiscoveryMetadata,
)
from backend.models.enums import FileType
from backend.utils.file_classifier import FileClassifier
from backend.utils.storage_manager import StorageManager
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class FileDiscoveryError(Exception):
    """Base exception for file discovery errors"""
    pass


class InvalidZIPError(FileDiscoveryError):
    """Raised when ZIP file is invalid or corrupted"""
    pass


class FileSizeExceededError(FileDiscoveryError):
    """Raised when file exceeds maximum allowed size"""
    pass


class FileCountExceededError(FileDiscoveryError):
    """Raised when ZIP contains too many files"""
    pass


class PathTraversalError(FileDiscoveryError):
    """Raised when path traversal attack is detected"""
    pass


class FileDiscoveryAgent:
    """
    Discovers and classifies files from uploaded ZIP
    
    Security features:
    - ZIP bomb detection (compression ratio check)
    - Path traversal prevention
    - File size limits
    - File count limits
    - Corrupted file handling
    """
    
    # Maximum compression ratio (1000:1)
    MAX_COMPRESSION_RATIO = 1000
    
    def __init__(
        self,
        storage_manager: Optional[StorageManager] = None,
        max_file_size: int = 524288000,  # 500MB
        max_files: int = 100
    ):
        """
        Initialize File Discovery Agent
        
        Args:
            storage_manager: Storage manager instance
            max_file_size: Maximum allowed file size in bytes
            max_files: Maximum number of files per ZIP
        """
        self.storage_manager = storage_manager or StorageManager()
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.classifier = FileClassifier()
    
    def discover(self, input: FileDiscoveryInput) -> FileDiscoveryOutput:
        """
        Extract ZIP and classify all files
        
        Args:
            input: File discovery input
            
        Returns:
            File discovery output with classified files
        """
        start_time = time.time()
        errors: List[str] = []
        
        logger.info(f"Starting file discovery for job {input.job_id}")
        logger.info(f"ZIP file: {input.zip_file_path}")
        
        try:
            # Step 1: Validate ZIP file
            self._validate_zip_file(
                input.zip_file_path,
                input.max_file_size,
                input.max_files
            )
            
            # Step 2: Create extraction directory
            extraction_dir = self.storage_manager.create_job_directory(input.job_id)
            logger.info(f"Created extraction directory: {extraction_dir}")
            
            # Step 3: Extract files safely
            extracted_files = self._safe_extract(
                input.zip_file_path,
                extraction_dir,
                errors
            )
            
            # Step 4: Classify each file
            documents, spreadsheets, images, videos, unknown = self._classify_files(
                extracted_files,
                input.job_id,
                errors
            )
            
            # Step 5: Build directory tree
            directory_tree = self._build_directory_tree(extracted_files, extraction_dir)
            
            # Step 6: Generate output
            processing_time = time.time() - start_time
            
            all_files = documents + spreadsheets + images + videos + unknown
            
            output = FileDiscoveryOutput(
                job_id=input.job_id,
                success=True,
                documents=documents,
                spreadsheets=spreadsheets,
                images=images,
                videos=videos,
                unknown=unknown,
                directory_tree=directory_tree,
                total_files=len(all_files),
                extraction_dir=str(extraction_dir),
                processing_time=processing_time,
                errors=errors,
                summary=self._generate_summary(
                    documents, spreadsheets, images, videos, unknown
                )
            )
            
            # Save metadata
            self.storage_manager.save_discovery_output(output, input.job_id)
            
            logger.info(
                f"File discovery completed: {len(all_files)} files "
                f"in {processing_time:.2f}s"
            )
            
            return output
            
        except FileDiscoveryError as e:
            logger.error(f"File discovery failed: {e}")
            return FileDiscoveryOutput(
                job_id=input.job_id,
                success=False,
                total_files=0,
                processing_time=time.time() - start_time,
                errors=[str(e)],
                summary={"error": str(e)}
            )
        except Exception as e:
            logger.exception(f"Unexpected error in file discovery: {e}")
            return FileDiscoveryOutput(
                job_id=input.job_id,
                success=False,
                total_files=0,
                processing_time=time.time() - start_time,
                errors=[f"Unexpected error: {str(e)}"],
                summary={"error": str(e)}
            )
    
    def _validate_zip_file(
        self,
        zip_path: str,
        max_file_size: int,
        max_files: int
    ):
        """
        Validate ZIP file before extraction
        
        Args:
            zip_path: Path to ZIP file
            max_file_size: Maximum allowed file size
            max_files: Maximum number of files
            
        Raises:
            InvalidZIPError: If ZIP is invalid
            FileSizeExceededError: If file too large
            FileCountExceededError: If too many files
        """
        # Check file exists
        if not os.path.exists(zip_path):
            raise InvalidZIPError(f"ZIP file not found: {zip_path}")
        
        # Check file size
        file_size = os.path.getsize(zip_path)
        if file_size > max_file_size:
            raise FileSizeExceededError(
                f"File size {file_size} exceeds maximum {max_file_size}"
            )
        
        # Check ZIP validity
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # Check for bad file (corrupted ZIP)
                bad_file = zip_file.testzip()
                if bad_file:
                    logger.warning(f"Corrupted file in ZIP: {bad_file}")
                
                # Check file count
                file_count = len(zip_file.namelist())
                if file_count > max_files:
                    raise FileCountExceededError(
                        f"ZIP contains {file_count} files, maximum is {max_files}"
                    )
                
                # Check compression ratio (zip bomb detection)
                compressed_size = file_size
                uncompressed_size = sum(
                    info.file_size for info in zip_file.infolist()
                )
                
                if compressed_size > 0:
                    compression_ratio = uncompressed_size / compressed_size
                    if compression_ratio > self.MAX_COMPRESSION_RATIO:
                        raise InvalidZIPError(
                            f"Suspicious compression ratio: {compression_ratio:.0f}:1 "
                            f"(max: {self.MAX_COMPRESSION_RATIO}:1)"
                        )
                
                logger.info(
                    f"ZIP validation passed: {file_count} files, "
                    f"ratio: {compression_ratio:.1f}:1"
                )
                
        except zipfile.BadZipFile as e:
            raise InvalidZIPError(f"Invalid or corrupted ZIP file: {e}")
    
    def _safe_extract(
        self,
        zip_path: str,
        extraction_dir: Path,
        errors: List[str]
    ) -> List[Path]:
        """
        Safely extract ZIP file with path traversal prevention
        
        Args:
            zip_path: Path to ZIP file
            extraction_dir: Directory to extract to
            errors: List to append errors to
            
        Returns:
            List of extracted file paths
        """
        extracted_files = []
        
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            for member in zip_file.namelist():
                try:
                    # Sanitize path
                    safe_path = self._sanitize_path(member)
                    
                    if not safe_path:
                        errors.append(f"Skipped dangerous path: {member}")
                        logger.warning(f"Skipped dangerous path: {member}")
                        continue
                    
                    # Full extraction path
                    full_path = extraction_dir / safe_path
                    
                    # Check for path traversal after joining
                    try:
                        full_path.resolve().relative_to(extraction_dir.resolve())
                    except ValueError:
                        errors.append(f"Path traversal attempt blocked: {member}")
                        logger.warning(f"Path traversal attempt blocked: {member}")
                        continue
                    
                    # Create directories
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Check if directory
                    if member.endswith('/'):
                        full_path.mkdir(parents=True, exist_ok=True)
                        continue
                    
                    # Extract file
                    zip_file.extract(member, extraction_dir)
                    
                    # Rename to safe name (zipfile.extract uses original name)
                    extracted_path = extraction_dir / member
                    if extracted_path != full_path:
                        extracted_path.rename(full_path)
                    
                    extracted_files.append(full_path)
                    
                except Exception as e:
                    errors.append(f"Failed to extract {member}: {e}")
                    logger.error(f"Failed to extract {member}: {e}")
        
        logger.info(f"Extracted {len(extracted_files)} files")
        return extracted_files
    
    def _sanitize_path(self, path: str) -> Optional[str]:
        """
        Sanitize file path to prevent path traversal
        
        Args:
            path: Original path from ZIP
            
        Returns:
            Sanitized path or None if dangerous
        """
        # Remove leading slashes/backslashes
        path = path.lstrip('/\\')
        
        # Check for path traversal (.. anywhere in path)
        if '..' in path:
            return None
        
        # Check for absolute paths (starting with / or drive letters like C:)
        if path.startswith('/') or (len(path) > 1 and path[1] == ':'):
            return None
        
        # Normalize path separators to forward slashes
        path = path.replace('\\', '/')
        
        # Remove any double slashes
        while '//' in path:
            path = path.replace('//', '/')
        
        # Ensure path is not empty
        if not path or path == '.':
            return None
        
        return path
    
    def _classify_files(
        self,
        extracted_files: List[Path],
        job_id: str,
        errors: List[str]
    ) -> tuple:
        """
        Classify extracted files by type
        
        Args:
            extracted_files: List of extracted file paths
            job_id: Unique job identifier
            errors: List to append errors to
            
        Returns:
            Tuple of (documents, spreadsheets, images, videos, unknown)
        """
        documents: List[DocumentFile] = []
        spreadsheets: List[SpreadsheetFile] = []
        images: List[ImageFile] = []
        videos: List[VideoFile] = []
        unknown: List[UnknownFile] = []
        
        for file_path in extracted_files:
            try:
                # Classify file
                file_type, mime_type = self.classifier.classify_file(str(file_path))
                
                # Get relative path
                relative_path = str(file_path.relative_to(
                    self.storage_manager.get_job_directory(job_id)
                ))
                
                # Create file metadata
                file_metadata = {
                    'file_id': self._generate_file_id(),
                    'file_path': str(file_path),
                    'file_type': file_type,
                    'file_size': file_path.stat().st_size,
                    'original_name': file_path.name,
                    'mime_type': mime_type,
                    'relative_path': relative_path,
                }
                
                # Categorize by type
                if file_type in [FileType.PDF, FileType.DOC, FileType.DOCX]:
                    documents.append(DocumentFile(**file_metadata))
                elif file_type in [FileType.XLS, FileType.XLSX, FileType.CSV]:
                    spreadsheets.append(SpreadsheetFile(**file_metadata))
                elif file_type in [FileType.JPG, FileType.JPEG, FileType.PNG, FileType.GIF, FileType.WEBP]:
                    # Get image dimensions
                    try:
                        from PIL import Image
                        with Image.open(file_path) as img:
                            file_metadata['width'] = img.width
                            file_metadata['height'] = img.height
                    except Exception:
                        pass
                    images.append(ImageFile(**file_metadata))
                elif file_type in [FileType.MP4, FileType.AVI, FileType.MOV, FileType.MKV]:
                    videos.append(VideoFile(**file_metadata))
                else:
                    unknown.append(UnknownFile(**file_metadata))
                
            except Exception as e:
                errors.append(f"Failed to classify {file_path.name}: {e}")
                logger.error(f"Failed to classify {file_path.name}: {e}")
        
        logger.info(
            f"Classified files: {len(documents)} docs, "
            f"{len(spreadsheets)} spreadsheets, {len(images)} images, "
            f"{len(videos)} videos, {len(unknown)} unknown"
        )
        
        return documents, spreadsheets, images, videos, unknown
    
    def _build_directory_tree(
        self,
        extracted_files: List[Path],
        extraction_dir: Path
    ) -> DirectoryNode:
        """
        Build directory tree structure
        
        Args:
            extracted_files: List of extracted file paths
            extraction_dir: Base extraction directory
            
        Returns:
            Directory tree root node
        """
        root = DirectoryNode(
            name="root",
            path="",
            is_file=False,
            children=[]
        )
        
        for file_path in extracted_files:
            try:
                relative_path = file_path.relative_to(extraction_dir)
                parts = relative_path.parts
                
                # Navigate/create nodes
                current = root
                for i, part in enumerate(parts):
                    # Find or create child node
                    existing = next(
                        (c for c in current.children if c.name == part),
                        None
                    )
                    
                    if existing:
                        current = existing
                    else:
                        is_file = (i == len(parts) - 1)
                        new_node = DirectoryNode(
                            name=part,
                            path=str(relative_path),
                            is_file=is_file,
                            children=[]
                        )
                        current.children.append(new_node)
                        current = new_node
                        
            except Exception as e:
                logger.error(f"Failed to build tree for {file_path}: {e}")
        
        return root
    
    def _generate_summary(
        self,
        documents: List[DocumentFile],
        spreadsheets: List[SpreadsheetFile],
        images: List[ImageFile],
        videos: List[VideoFile],
        unknown: List[UnknownFile]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics
        
        Args:
            documents: List of document files
            spreadsheets: List of spreadsheet files
            images: List of image files
            videos: List of video files
            unknown: List of unknown files
            
        Returns:
            Summary dictionary
        """
        all_files = documents + spreadsheets + images + videos + unknown
        
        total_size = sum(f.file_size for f in all_files)
        
        return {
            "documents_count": len(documents),
            "spreadsheets_count": len(spreadsheets),
            "images_count": len(images),
            "videos_count": len(videos),
            "unknown_count": len(unknown),
            "total_files": len(all_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
    
    def _generate_file_id(self) -> str:
        """
        Generate unique file identifier
        
        Returns:
            Unique file ID
        """
        return f"file_{uuid.uuid4().hex[:12]}"
