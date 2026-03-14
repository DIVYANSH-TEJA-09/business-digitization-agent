"""
Module: file_discovery.py
Purpose: File Discovery Agent — extracts ZIP files and classifies contents.

This agent is the first stage of the pipeline. It:
1. Validates and extracts ZIP files securely
2. Walks the extracted directory tree
3. Classifies each file by type (document, image, spreadsheet, etc.)
4. Returns a FileCollection with organized file metadata

Security: Protects against zip bombs and path traversal attacks.
"""

import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image as PILImage

from backend.config import settings
from backend.models.exceptions import (
    CorruptedFileError,
    FileTooLargeError,
    ZipBombError,
    ZipExtractionError,
)
from backend.models.schemas import (
    DocumentFile,
    FileCollection,
    FileType,
    ImageFile,
)
from backend.utils.file_classifier import (
    classify_file,
    get_file_category,
    is_image,
    should_skip,
)
from backend.utils.logger import get_logger
from backend.utils.storage_manager import storage_manager

logger = get_logger(__name__)

# Safety limits
MAX_COMPRESSION_RATIO = 100  # Max decompressed/compressed size ratio
MAX_TOTAL_FILES = 5000       # Max files in a single ZIP
MAX_SINGLE_FILE_SIZE = 200 * 1024 * 1024  # 200MB per extracted file


class FileDiscoveryAgent:
    """
    Agent responsible for ZIP extraction and file classification.

    Workflow:
        1. Validate ZIP file (size, format, security)
        2. Extract to job-specific directory
        3. Walk directory tree, skip junk files
        4. Classify each file by type
        5. Return organized FileCollection
    """

    def __init__(self):
        self.storage = storage_manager

    def discover(self, zip_path: str, job_id: str | None = None) -> FileCollection:
        """
        Extract a ZIP file and classify all contained files.

        Args:
            zip_path: Path to the ZIP file
            job_id: Optional job identifier (generated if not provided)

        Returns:
            FileCollection with classified files

        Raises:
            FileTooLargeError: If ZIP exceeds size limit
            ZipExtractionError: If ZIP is invalid or corrupted
            ZipBombError: If ZIP bomb is detected
        """
        job_id = job_id or str(uuid.uuid4())[:12]
        logger.info(f"[{job_id}] Starting file discovery: {zip_path}")

        # Step 1: Validate
        self._validate_zip(zip_path)

        # Step 2: Extract
        extract_dir = self._extract_zip(zip_path, job_id)

        # Step 3: Walk and classify
        collection = self._classify_files(extract_dir, job_id)

        logger.info(
            f"[{job_id}] Discovery complete: "
            f"{collection.total_files} files found "
            f"({len(collection.documents)} docs, "
            f"{len(collection.spreadsheets)} sheets, "
            f"{len(collection.images)} images, "
            f"{len(collection.videos)} videos, "
            f"{len(collection.unknown)} unknown)"
        )

        return collection

    def _validate_zip(self, zip_path: str) -> None:
        """
        Validate ZIP file before extraction.

        Checks:
            - File exists
            - File is a valid ZIP
            - File size is within limits
        """
        path = Path(zip_path)

        if not path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        if not zipfile.is_zipfile(zip_path):
            raise ZipExtractionError(
                f"Not a valid ZIP file: {zip_path}"
            )

        file_size = path.stat().st_size
        max_size = settings.max_zip_size_mb * 1024 * 1024
        if file_size > max_size:
            raise FileTooLargeError(file_size, max_size)

        logger.debug(
            f"ZIP validation passed: {path.name} "
            f"({file_size / (1024*1024):.1f}MB)"
        )

    def _extract_zip(self, zip_path: str, job_id: str) -> Path:
        """
        Securely extract ZIP contents to job directory.

        Security measures:
            - Path traversal prevention (no ../ in filenames)
            - Zip bomb detection (compression ratio check)
            - Max file count enforcement
            - Individual file size limits

        Returns:
            Path to the extraction directory
        """
        extract_dir = self.storage.create_job_directory(job_id)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Security: check total file count
                members = zf.infolist()
                if len(members) > MAX_TOTAL_FILES:
                    raise ZipBombError(
                        f"ZIP contains {len(members)} files "
                        f"(max: {MAX_TOTAL_FILES})"
                    )

                # Security: check compression ratio
                compressed_size = sum(m.compress_size for m in members)
                uncompressed_size = sum(m.file_size for m in members)

                if compressed_size > 0:
                    ratio = uncompressed_size / compressed_size
                    if ratio > MAX_COMPRESSION_RATIO:
                        raise ZipBombError(
                            f"Suspicious compression ratio: {ratio:.0f}x "
                            f"(max: {MAX_COMPRESSION_RATIO}x)"
                        )

                # Extract each file with security checks
                extracted_count = 0
                for member in members:
                    # Skip directories
                    if member.is_dir():
                        continue

                    # Security: path traversal check
                    member_path = Path(member.filename)
                    if ".." in member_path.parts:
                        logger.warning(
                            f"Skipping path traversal attempt: {member.filename}"
                        )
                        continue

                    # Security: individual file size check
                    if member.file_size > MAX_SINGLE_FILE_SIZE:
                        logger.warning(
                            f"Skipping oversized file: {member.filename} "
                            f"({member.file_size / (1024*1024):.1f}MB)"
                        )
                        continue

                    # Extract to a flat or preserved structure
                    target_path = extract_dir / member.filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                    extracted_count += 1

                logger.info(
                    f"[{job_id}] Extracted {extracted_count} files "
                    f"to {extract_dir}"
                )

        except zipfile.BadZipFile as e:
            self.storage.cleanup_job(job_id)
            raise CorruptedFileError(f"Corrupted ZIP file: {e}") from e
        except (ZipBombError, FileTooLargeError):
            self.storage.cleanup_job(job_id)
            raise
        except Exception as e:
            self.storage.cleanup_job(job_id)
            raise ZipExtractionError(f"Failed to extract ZIP: {e}") from e

        return extract_dir

    def _classify_files(self, extract_dir: Path, job_id: str) -> FileCollection:
        """
        Walk extracted directory and classify all files.

        Returns:
            FileCollection with files organized by type
        """
        documents: List[DocumentFile] = []
        spreadsheets: List[DocumentFile] = []
        images: List[ImageFile] = []
        videos: List[DocumentFile] = []
        unknown: List[DocumentFile] = []
        directory_structure: Dict[str, Any] = {}

        # Walk all files recursively
        for file_path in sorted(extract_dir.rglob("*")):
            if not file_path.is_file():
                continue

            # Skip junk/hidden files
            if should_skip(str(file_path)):
                logger.debug(f"Skipping: {file_path.name}")
                continue

            # Classify the file
            file_type, mime_type = classify_file(str(file_path))
            file_size = file_path.stat().st_size
            relative_path = file_path.relative_to(extract_dir)

            # Build directory structure map
            self._update_directory_structure(
                directory_structure, str(relative_path), file_type.value
            )

            category = get_file_category(file_type)

            if category == "document":
                documents.append(DocumentFile(
                    file_path=str(file_path),
                    file_type=file_type,
                    file_size=file_size,
                    original_name=file_path.name,
                    mime_type=mime_type,
                ))

            elif category == "spreadsheet":
                spreadsheets.append(DocumentFile(
                    file_path=str(file_path),
                    file_type=file_type,
                    file_size=file_size,
                    original_name=file_path.name,
                    mime_type=mime_type,
                ))

            elif category == "image":
                img_file = self._create_image_file(
                    file_path, file_type, file_size, mime_type
                )
                images.append(img_file)

            elif category == "video":
                videos.append(DocumentFile(
                    file_path=str(file_path),
                    file_type=file_type,
                    file_size=file_size,
                    original_name=file_path.name,
                    mime_type=mime_type,
                ))

            else:
                unknown.append(DocumentFile(
                    file_path=str(file_path),
                    file_type=file_type,
                    file_size=file_size,
                    original_name=file_path.name,
                    mime_type=mime_type,
                ))

        total = len(documents) + len(spreadsheets) + len(images) + len(videos) + len(unknown)

        return FileCollection(
            job_id=job_id,
            documents=documents,
            spreadsheets=spreadsheets,
            images=images,
            videos=videos,
            unknown=unknown,
            total_files=total,
            directory_structure=directory_structure,
            discovery_metadata={
                "source_directory": str(extract_dir),
                "file_type_counts": {
                    "documents": len(documents),
                    "spreadsheets": len(spreadsheets),
                    "images": len(images),
                    "videos": len(videos),
                    "unknown": len(unknown),
                },
            },
        )

    def _create_image_file(
        self,
        file_path: Path,
        file_type: FileType,
        file_size: int,
        mime_type: str,
    ) -> ImageFile:
        """
        Create an ImageFile with dimensions if available.

        Attempts to read image dimensions using Pillow.
        Falls back gracefully if image can't be opened.
        """
        width, height = None, None

        try:
            with PILImage.open(file_path) as img:
                width, height = img.size
        except Exception:
            logger.debug(f"Could not read dimensions: {file_path.name}")

        return ImageFile(
            file_path=str(file_path),
            file_type=file_type,
            width=width,
            height=height,
            file_size=file_size,
            mime_type=mime_type,
            original_name=file_path.name,
        )

    def _update_directory_structure(
        self,
        structure: Dict[str, Any],
        relative_path: str,
        file_type: str,
    ) -> None:
        """
        Build a nested dictionary representing the directory structure.

        Example output:
        {
            "folder1": {
                "brochure.pdf": "pdf",
                "subfolder": {
                    "prices.xlsx": "xlsx"
                }
            }
        }
        """
        parts = Path(relative_path).parts
        current = structure

        for part in parts[:-1]:  # Navigate to parent dirs
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the file entry
        current[parts[-1]] = file_type
