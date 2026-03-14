"""
Module: pipeline.py
Purpose: Main Pipeline Orchestrator for the business digitization workflow.

Coordinates all agents in sequence:
    1. File Discovery → 2. Document Parsing → 2.5. PageIndex Tree Generation →
    3. Table Extraction → 4. Media Extraction → 5. Vision Analysis →
    6. Schema Mapping → 7. Validation → 8. Profile Output

Provides progress tracking and error handling at each phase.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from backend.agents.file_discovery import FileDiscoveryAgent
from backend.agents.media_extraction import MediaExtractionAgent
from backend.agents.schema_mapping import SchemaMappingAgent
from backend.agents.table_extraction import TableExtractionAgent
from backend.agents.vision_agent import VisionAgent
from backend.indexing.pageindex_adapter import PageIndexAdapter
from backend.models.schemas import (
    BusinessProfile,
    DocumentIndex,
    FileCollection,
    ImageAnalysis,
    JobStatus,
    MediaCollection,
    ParsedDocument,
    StructuredTable,
    ValidationResult,
)
from backend.parsers.parser_factory import parser_factory
from backend.utils.logger import get_logger
from backend.utils.storage_manager import storage_manager
from backend.validation.schema_validator import SchemaValidator

logger = get_logger(__name__)


class BusinessDigitizationPipeline:
    """
    Main orchestrator for the agentic digitization workflow.

    Coordinates multiple specialized agents to transform
    unstructured business documents into structured profiles.

    Usage:
        pipeline = BusinessDigitizationPipeline()
        profile, validation = await pipeline.process("path/to/upload.zip")
    """

    def __init__(self):
        self.file_discovery = FileDiscoveryAgent()
        self.table_extraction = TableExtractionAgent()
        self.media_extraction = MediaExtractionAgent()
        self.vision_agent = VisionAgent()
        self.pageindex = PageIndexAdapter()
        self.schema_mapping = SchemaMappingAgent()
        self.validator = SchemaValidator()

        # Progress tracking
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable) -> None:
        """Set a callback function for progress updates."""
        self._progress_callback = callback

    def _update_progress(
        self, phase: str, progress: float, message: str
    ) -> None:
        """Report progress to the callback."""
        logger.info(f"[{phase}] {progress:.0f}% — {message}")
        if self._progress_callback:
            self._progress_callback(phase, progress, message)

    async def process(
        self,
        zip_path: str,
        job_id: Optional[str] = None,
    ) -> tuple[BusinessProfile, ValidationResult]:
        """
        Run the full digitization pipeline on a ZIP file.

        Args:
            zip_path: Path to the uploaded ZIP file
            job_id: Optional job identifier

        Returns:
            Tuple of (BusinessProfile, ValidationResult)
        """
        start_time = time.time()
        job_id = job_id or Path(zip_path).stem[:12]

        logger.info(f"{'='*60}")
        logger.info(f"Pipeline started — Job: {job_id}")
        logger.info(f"{'='*60}")

        try:
            # ─── Phase 1: File Discovery ─────────────────────────
            self._update_progress(
                "file_discovery", 5, "Extracting and classifying files..."
            )
            collection = self.file_discovery.discover(zip_path, job_id)

            if collection.total_files == 0:
                raise ValueError("ZIP file contains no processable files.")

            # ─── Phase 2: Document Parsing ────────────────────────
            self._update_progress(
                "parsing", 15, f"Parsing {len(collection.documents) + len(collection.spreadsheets)} documents..."
            )
            parsed_docs = self._parse_documents(collection)

            # ─── Phase 2.5: PageIndex Tree Generation ─────────────
            self._update_progress(
                "pageindex", 25,
                f"Building PageIndex trees for {len(parsed_docs)} documents..."
            )
            doc_indexes = self.pageindex.build_indexes(parsed_docs, job_id)

            # ─── Phase 3: Table Extraction ────────────────────────
            self._update_progress(
                "table_extraction", 35, "Extracting tables..."
            )
            tables = self.table_extraction.extract_from_multiple(parsed_docs)

            # ─── Phase 4: Media Extraction ────────────────────────
            self._update_progress(
                "media_extraction", 45,
                f"Extracting media ({len(collection.images)} images)..."
            )
            media = self.media_extraction.extract_all(
                parsed_docs=parsed_docs,
                image_files=collection.images,
                video_files=collection.videos,
                job_id=job_id,
            )

            # ─── Phase 5: Vision Analysis ─────────────────────────
            self._update_progress(
                "vision_analysis", 55,
                f"Analyzing {len(media.images)} images with AI..."
            )
            image_analyses = self.vision_agent.analyze_batch(media.images)

            # ─── Phase 6: Schema Mapping ──────────────────────────
            self._update_progress(
                "schema_mapping", 70,
                "Mapping data to business profile schema..."
            )
            profile = await self.schema_mapping.map_to_schema(
                parsed_docs=parsed_docs,
                tables=tables,
                image_analyses=image_analyses,
            )

            # ─── Phase 7: Validation ──────────────────────────────
            self._update_progress(
                "validation", 90, "Validating profile..."
            )
            validation = self.validator.validate(profile)

            # ─── Phase 8: Save Profile ────────────────────────────
            self._update_progress(
                "saving", 95, "Saving profile..."
            )
            profile_json = profile.model_dump_json(indent=2)
            storage_manager.save_profile(job_id, profile_json)

            # Save validation results alongside
            validation_json = json.dumps(validation.model_dump(), indent=2, default=str)
            val_path = storage_manager.get_job_subdir(job_id, "index") / "validation.json"
            val_path.write_text(validation_json, encoding="utf-8")

            elapsed = time.time() - start_time
            self._update_progress(
                "complete", 100,
                f"Done! {elapsed:.1f}s — "
                f"Completeness: {validation.completeness_score:.0%}"
            )

            logger.info(f"{'='*60}")
            logger.info(
                f"Pipeline complete — Job: {job_id} — "
                f"{elapsed:.1f}s — "
                f"Type: {profile.business_type.value} — "
                f"Products: {len(profile.products or [])} — "
                f"Services: {len(profile.services or [])} — "
                f"Completeness: {validation.completeness_score:.0%}"
            )
            logger.info(f"{'='*60}")

            return profile, validation

        except Exception as e:
            logger.exception(f"Pipeline failed for job {job_id}: {e}")
            self._update_progress("error", 0, f"Error: {str(e)}")
            raise

    def _parse_documents(
        self, collection: FileCollection
    ) -> List[ParsedDocument]:
        """Parse all discovered documents and spreadsheets."""
        parsed_docs = []

        # Parse documents (PDF, DOCX)
        for doc_file in collection.documents:
            try:
                parsed = parser_factory.parse(
                    doc_file.file_path,
                    doc_file.file_type,
                )
                parsed_docs.append(parsed)
            except Exception as e:
                logger.warning(
                    f"Failed to parse {doc_file.original_name}: {e}"
                )

        # Parse spreadsheets (XLSX, CSV)
        for sheet_file in collection.spreadsheets:
            try:
                parsed = parser_factory.parse(
                    sheet_file.file_path,
                    sheet_file.file_type,
                )
                parsed_docs.append(parsed)
            except Exception as e:
                logger.warning(
                    f"Failed to parse {sheet_file.original_name}: {e}"
                )

        logger.info(f"Parsed {len(parsed_docs)} documents successfully")
        return parsed_docs


# Convenience function to run the pipeline
async def run_pipeline(
    zip_path: str,
    job_id: Optional[str] = None,
) -> tuple[BusinessProfile, ValidationResult]:
    """
    Convenience function to run the full pipeline.

    Usage:
        profile, validation = await run_pipeline("path/to/upload.zip")
    """
    pipeline = BusinessDigitizationPipeline()
    return await pipeline.process(zip_path, job_id)
