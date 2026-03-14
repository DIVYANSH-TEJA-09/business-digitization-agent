"""
Module: media_extraction.py
Purpose: Media Extraction Agent — extracts images from documents and organizes media.

Handles:
    - Embedded image extraction from PDFs (using pdfplumber)
    - Embedded image extraction from DOCX (from ZIP internals)
    - Standalone image/video file organization
    - Image deduplication using hashing
"""

import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set

from PIL import Image as PILImage

from backend.models.schemas import (
    DocumentFile,
    ExtractedImage,
    FileType,
    ImageFile,
    MediaCollection,
    ParsedDocument,
)
from backend.utils.file_classifier import is_image, is_video
from backend.utils.logger import get_logger
from backend.utils.storage_manager import storage_manager

logger = get_logger(__name__)


class MediaExtractionAgent:
    """
    Agent for extracting and organizing media files.

    Workflow:
        1. Extract embedded images from parsed PDFs and DOCX
        2. Process standalone image/video files
        3. Deduplicate images using perceptual hashing
        4. Organize all media into the job's media directory
        5. Return a MediaCollection with metadata
    """

    def __init__(self):
        self.storage = storage_manager

    def extract_all(
        self,
        parsed_docs: List[ParsedDocument],
        image_files: List[ImageFile],
        video_files: List[DocumentFile],
        job_id: str,
    ) -> MediaCollection:
        """
        Extract and organize all media for a job.

        Args:
            parsed_docs: Parsed documents (may contain embedded images)
            image_files: Standalone image files from file discovery
            video_files: Video files from file discovery
            job_id: Job identifier for storage

        Returns:
            MediaCollection with all organized media
        """
        logger.info(f"[{job_id}] Starting media extraction")

        all_images: List[ExtractedImage] = []
        seen_hashes: Set[str] = set()

        media_dir = self.storage.get_job_subdir(job_id, "media")

        # Step 1: Extract embedded images from documents
        for doc in parsed_docs:
            embedded = self._extract_embedded_images(doc, media_dir)
            for img in embedded:
                if img.image_hash and img.image_hash in seen_hashes:
                    logger.debug(f"Skipping duplicate: {img.file_path}")
                    continue
                if img.image_hash:
                    seen_hashes.add(img.image_hash)
                all_images.append(img)

        # Step 2: Process standalone image files
        for img_file in image_files:
            extracted = self._process_standalone_image(
                img_file, media_dir, seen_hashes
            )
            if extracted:
                all_images.append(extracted)

        # Step 3: Process video files (just copy references)
        video_docs = []
        for vid in video_files:
            video_docs.append(vid)

        collection = MediaCollection(
            images=all_images,
            videos=video_docs,
            total_count=len(all_images) + len(video_docs),
            extraction_summary={
                "embedded_images": sum(
                    1 for img in all_images if img.is_embedded
                ),
                "standalone_images": sum(
                    1 for img in all_images if not img.is_embedded
                ),
                "videos": len(video_docs),
                "duplicates_skipped": len(seen_hashes) - len(all_images),
            },
        )

        logger.info(
            f"[{job_id}] Media extraction complete: "
            f"{len(all_images)} images, {len(video_docs)} videos"
        )

        return collection

    def _extract_embedded_images(
        self,
        doc: ParsedDocument,
        media_dir: Path,
    ) -> List[ExtractedImage]:
        """Extract embedded images from a parsed document."""
        if doc.file_type == FileType.PDF:
            return self._extract_from_pdf(doc, media_dir)
        elif doc.file_type == FileType.DOCX:
            return self._extract_from_docx(doc, media_dir)
        return []

    def _extract_from_pdf(
        self,
        doc: ParsedDocument,
        media_dir: Path,
    ) -> List[ExtractedImage]:
        """Extract embedded images from a PDF document."""
        import pdfplumber

        images: List[ExtractedImage] = []
        source_name = Path(doc.source_file).stem

        try:
            with pdfplumber.open(doc.source_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_images = page.images or []

                    for img_idx, img_data in enumerate(page_images):
                        try:
                            # pdfplumber gives image bounds, not pixel data
                            # We use the page.to_image() approach for actual extraction
                            # For now, record metadata
                            img_id = f"{source_name}_p{page_num}_img{img_idx}"

                            images.append(ExtractedImage(
                                image_id=img_id,
                                file_path="",  # Will be populated if we can extract pixel data
                                source_doc=doc.source_file,
                                source_page=page_num,
                                width=int(img_data.get("width", 0)),
                                height=int(img_data.get("height", 0)),
                                file_size=0,
                                mime_type="image/png",
                                extraction_method="embedded",
                                is_embedded=True,
                            ))
                        except Exception as e:
                            logger.debug(
                                f"Could not extract image {img_idx} "
                                f"from page {page_num}: {e}"
                            )
        except Exception as e:
            logger.warning(f"PDF image extraction failed: {e}")

        return images

    def _extract_from_docx(
        self,
        doc: ParsedDocument,
        media_dir: Path,
    ) -> List[ExtractedImage]:
        """
        Extract embedded images from a DOCX document.

        DOCX is a ZIP file containing images in word/media/.
        """
        import zipfile

        images: List[ExtractedImage] = []
        source_name = Path(doc.source_file).stem

        try:
            with zipfile.ZipFile(doc.source_file, "r") as zf:
                media_files = [
                    f for f in zf.namelist()
                    if f.startswith("word/media/")
                ]

                for idx, media_path in enumerate(media_files):
                    try:
                        # Extract the image
                        img_filename = f"{source_name}_embedded_{idx}{Path(media_path).suffix}"
                        output_path = media_dir / img_filename

                        with zf.open(media_path) as src, open(output_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)

                        # Get image info
                        width, height, file_size = 0, 0, 0
                        mime_type = "image/png"

                        try:
                            with PILImage.open(output_path) as img:
                                width, height = img.size
                            file_size = output_path.stat().st_size
                            suffix = output_path.suffix.lower()
                            mime_map = {
                                ".jpg": "image/jpeg",
                                ".jpeg": "image/jpeg",
                                ".png": "image/png",
                                ".gif": "image/gif",
                                ".emf": "image/emf",
                                ".wmf": "image/wmf",
                            }
                            mime_type = mime_map.get(suffix, "image/png")
                        except Exception:
                            pass

                        # Hash for deduplication
                        img_hash = self._hash_file(str(output_path))

                        images.append(ExtractedImage(
                            image_id=f"{source_name}_emb_{idx}",
                            file_path=str(output_path),
                            source_doc=doc.source_file,
                            source_page=1,
                            width=width,
                            height=height,
                            file_size=file_size,
                            mime_type=mime_type,
                            extraction_method="embedded",
                            is_embedded=True,
                            image_hash=img_hash,
                        ))

                    except Exception as e:
                        logger.debug(
                            f"Could not extract DOCX image {media_path}: {e}"
                        )
        except Exception as e:
            logger.warning(f"DOCX image extraction failed: {e}")

        return images

    def _process_standalone_image(
        self,
        img_file: ImageFile,
        media_dir: Path,
        seen_hashes: Set[str],
    ) -> Optional[ExtractedImage]:
        """Process a standalone image file."""
        try:
            # Hash for deduplication
            img_hash = self._hash_file(img_file.file_path)
            if img_hash in seen_hashes:
                logger.debug(f"Skipping duplicate standalone: {img_file.original_name}")
                return None
            seen_hashes.add(img_hash)

            # Copy to media directory
            dest_path = media_dir / img_file.original_name
            if not dest_path.exists():
                shutil.copy2(img_file.file_path, dest_path)

            return ExtractedImage(
                file_path=str(dest_path),
                source_doc=None,
                source_page=None,
                width=img_file.width or 0,
                height=img_file.height or 0,
                file_size=img_file.file_size,
                mime_type=img_file.mime_type,
                extraction_method="standalone",
                is_embedded=False,
                image_hash=img_hash,
            )
        except Exception as e:
            logger.warning(
                f"Could not process standalone image "
                f"{img_file.original_name}: {e}"
            )
            return None

    def _hash_file(self, file_path: str) -> str:
        """Generate MD5 hash of a file for deduplication."""
        try:
            hasher = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
