"""
Module: storage_manager.py
Purpose: Manage filesystem storage for the digitization pipeline.

Handles job directory creation, file organization, and cleanup.
Each job gets its own directory structure under storage/extracted/<job_id>.
"""

import json
import shutil
from pathlib import Path
from typing import Optional

from backend.config import settings, PROJECT_ROOT
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class StorageManager:
    """
    Manages filesystem storage for digitization jobs.

    Directory structure per job:
        storage/extracted/<job_id>/
        ├── documents/     # Extracted document files
        ├── spreadsheets/  # Extracted spreadsheet files
        ├── images/        # Extracted + embedded images
        ├── videos/        # Video files
        ├── media/         # Processed media output
        ├── index/         # PageIndex trees
        └── unknown/       # Unclassified files
    """

    def __init__(self):
        self._ensure_base_dirs()

    def _ensure_base_dirs(self) -> None:
        """Create base storage directories if they don't exist."""
        for path_fn in [
            settings.get_upload_path,
            settings.get_extracted_path,
            settings.get_profiles_path,
            settings.get_index_path,
            settings.get_media_path,
        ]:
            path_fn().mkdir(parents=True, exist_ok=True)

    def create_job_directory(self, job_id: str) -> Path:
        """
        Create the directory structure for a new job.

        Args:
            job_id: Unique job identifier

        Returns:
            Path to the job's root directory
        """
        job_dir = settings.get_extracted_path() / job_id

        subdirs = [
            "documents",
            "spreadsheets",
            "images",
            "videos",
            "media",
            "index",
            "unknown",
        ]

        for subdir in subdirs:
            (job_dir / subdir).mkdir(parents=True, exist_ok=True)

        logger.info(f"Created job directory: {job_dir}")
        return job_dir

    def get_job_directory(self, job_id: str) -> Path:
        """Get the root directory for a job."""
        return settings.get_extracted_path() / job_id

    def get_job_subdir(self, job_id: str, category: str) -> Path:
        """
        Get a specific subdirectory for a job.

        Args:
            job_id: Job identifier
            category: One of: documents, spreadsheets, images, videos, media, index, unknown

        Returns:
            Path to the subdirectory
        """
        subdir = self.get_job_directory(job_id) / category
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir

    def save_profile(self, job_id: str, profile_data: str) -> Path:
        """
        Save a generated business profile JSON.

        Args:
            job_id: Job identifier
            profile_data: JSON string of the business profile

        Returns:
            Path to the saved profile file
        """
        profile_dir = settings.get_profiles_path()
        profile_path = profile_dir / f"{job_id}.json"
        profile_path.write_text(profile_data, encoding="utf-8")
        logger.info(f"Saved profile: {profile_path}")
        return profile_path

    def load_profile(self, job_id: str) -> Optional[str]:
        """
        Load a saved business profile.

        Returns:
            JSON string of the profile, or None if not found
        """
        profile_path = settings.get_profiles_path() / f"{job_id}.json"
        if profile_path.exists():
            return profile_path.read_text(encoding="utf-8")
        return None

    def save_index(self, job_id: str, doc_id: str, index_data: str) -> Path:
        """
        Save a PageIndex tree JSON for a document.

        Args:
            job_id: Job identifier
            doc_id: Document identifier
            index_data: JSON string of the PageIndex tree

        Returns:
            Path to the saved index file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        index_path = index_dir / f"{doc_id}_tree.json"
        index_path.write_text(index_data, encoding="utf-8")
        logger.debug(f"Saved index: {index_path}")
        return index_path

    def save_file_collection(self, job_id: str, collection_data: dict) -> Path:
        """
        Save the file collection JSON for a job.

        Args:
            job_id: Job identifier
            collection_data: Dict of the file collection

        Returns:
            Path to the saved file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        file_path = index_dir / "file_collection.json"
        file_path.write_text(
            json.dumps(collection_data, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved file collection: {file_path}")
        return file_path

    def save_parsed_documents(self, job_id: str, parsed_docs: list) -> Path:
        """
        Save all parsed documents JSON for a job.

        Args:
            job_id: Job identifier
            parsed_docs: List of ParsedDocument model_dump() dicts

        Returns:
            Path to the saved file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        file_path = index_dir / "parsed_documents.json"
        file_path.write_text(
            json.dumps(parsed_docs, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved {len(parsed_docs)} parsed documents: {file_path}")
        return file_path

    def save_tables(self, job_id: str, tables: list) -> Path:
        """
        Save all extracted tables JSON for a job.

        Args:
            job_id: Job identifier
            tables: List of StructuredTable model_dump() dicts

        Returns:
            Path to the saved file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        file_path = index_dir / "extracted_tables.json"
        file_path.write_text(
            json.dumps(tables, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved {len(tables)} tables: {file_path}")
        return file_path

    def save_media_collection(self, job_id: str, media_data: dict) -> Path:
        """
        Save the media collection JSON for a job.

        Args:
            job_id: Job identifier
            media_data: Dict of the media collection

        Returns:
            Path to the saved file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        file_path = index_dir / "media_collection.json"
        file_path.write_text(
            json.dumps(media_data, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved media collection: {file_path}")
        return file_path

    def save_image_analyses(self, job_id: str, analyses: list) -> Path:
        """
        Save all image analysis results JSON for a job.

        Args:
            job_id: Job identifier
            analyses: List of ImageAnalysis model_dump() dicts

        Returns:
            Path to the saved file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        file_path = index_dir / "image_analyses.json"
        file_path.write_text(
            json.dumps(analyses, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved {len(analyses)} image analyses: {file_path}")
        return file_path

    def save_document_indexes(self, job_id: str, indexes: list) -> Path:
        """
        Save all document indexes JSON for a job.

        Args:
            job_id: Job identifier
            indexes: List of DocumentIndex model_dump() dicts

        Returns:
            Path to the saved file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        file_path = index_dir / "document_indexes.json"
        file_path.write_text(
            json.dumps(indexes, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved {len(indexes)} document indexes: {file_path}")
        return file_path

    def save_complete_job_data(self, job_id: str, job_data: dict) -> Path:
        """
        Save a complete job data export (all artifacts in one file).

        Args:
            job_id: Job identifier
            job_data: Dict containing all job artifacts

        Returns:
            Path to the saved file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        file_path = index_dir / "complete_job_data.json"
        file_path.write_text(
            json.dumps(job_data, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved complete job data: {file_path}")
        return file_path

    def save_pdf_wise_data(self, job_id: str, pdf_data: dict) -> Path:
        """
        Save PDF-wise organized data with page-level metadata.

        Args:
            job_id: Job identifier
            pdf_data: Dict with PDF-wise organized data

        Returns:
            Path to the saved file
        """
        index_dir = self.get_job_subdir(job_id, "index")
        file_path = index_dir / "pdf_wise_data.json"
        file_path.write_text(
            json.dumps(pdf_data, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved PDF-wise data: {file_path}")
        return file_path

    def cleanup_job(self, job_id: str) -> None:
        """
        Remove all files and directories for a job.

        Args:
            job_id: Job identifier to clean up
        """
        job_dir = self.get_job_directory(job_id)
        if job_dir.exists():
            shutil.rmtree(job_dir)
            logger.info(f"Cleaned up job directory: {job_dir}")

        # Also remove profile
        profile_path = settings.get_profiles_path() / f"{job_id}.json"
        if profile_path.exists():
            profile_path.unlink()
            logger.info(f"Removed profile: {profile_path}")

    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        stats = {}
        for name, path_fn in [
            ("uploads", settings.get_upload_path),
            ("extracted", settings.get_extracted_path),
            ("profiles", settings.get_profiles_path),
            ("index", settings.get_index_path),
            ("media", settings.get_media_path),
        ]:
            path = path_fn()
            if path.exists():
                total_size = sum(
                    f.stat().st_size for f in path.rglob("*") if f.is_file()
                )
                file_count = sum(1 for f in path.rglob("*") if f.is_file())
                stats[name] = {
                    "size_mb": round(total_size / (1024 * 1024), 2),
                    "file_count": file_count,
                }
            else:
                stats[name] = {"size_mb": 0, "file_count": 0}
        return stats


# Singleton instance
storage_manager = StorageManager()
