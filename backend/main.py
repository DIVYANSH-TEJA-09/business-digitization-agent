"""
Module: main.py
Purpose: FastAPI application entry point.

Provides REST API endpoints for the business digitization pipeline:
    - POST /api/upload     : Upload a ZIP file and start processing
    - GET  /api/status/{id}: Check job status
    - GET  /api/profile/{id}: Get generated business profile
    - GET  /api/health     : System health check
"""

import asyncio
import json
import shutil
import uuid
from pathlib import Path
from typing import Dict

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.agents.file_discovery import FileDiscoveryAgent
from backend.config import settings
from backend.models.schemas import FileCollection, JobStatus
from backend.utils.logger import get_logger
from backend.utils.storage_manager import storage_manager

logger = get_logger(__name__)

# =============================================================================
# APP SETUP
# =============================================================================

app = FastAPI(
    title="Business Digitization Agent",
    description="AI-powered system that converts unstructured business documents "
                "into structured digital business profiles.",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking (replace with DB for production)
jobs: Dict[str, JobStatus] = {}
file_collections: Dict[str, FileCollection] = {}

# Agent instances
file_discovery_agent = FileDiscoveryAgent()


async def _run_full_pipeline(job_id: str, zip_path: str) -> None:
    """Background task: run the full digitization pipeline."""
    from backend.pipeline import BusinessDigitizationPipeline

    pipeline = BusinessDigitizationPipeline()

    def progress_callback(phase: str, progress: float, message: str):
        if job_id in jobs:
            jobs[job_id].current_phase = phase
            jobs[job_id].progress = progress
            jobs[job_id].message = message

    pipeline.set_progress_callback(progress_callback)

    try:
        profile, validation = await pipeline.process(zip_path, job_id)
        jobs[job_id].status = "completed"
        jobs[job_id].progress = 100.0
        jobs[job_id].message = (
            f"Profile generated — "
            f"Type: {profile.business_type.value}, "
            f"Products: {len(profile.products or [])}, "
            f"Services: {len(profile.services or [])}, "
            f"Completeness: {validation.completeness_score:.0%}"
        )
    except Exception as e:
        logger.exception(f"[{job_id}] Pipeline failed: {e}")
        jobs[job_id].status = "failed"
        jobs[job_id].error_message = str(e)
        jobs[job_id].message = f"Error: {str(e)}"


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/health")
async def health_check():
    """System health check — verify all services are running."""
    from backend.utils.llm_client import llm_client

    health = {
        "status": "ok",
        "storage": storage_manager.get_storage_stats(),
        "ollama": {
            "status": "checking...",
        },
        "groq": {
            "status": "checking...",
        },
    }

    # Check Ollama
    try:
        ollama_ok = llm_client.check_ollama_health()
        health["ollama"]["status"] = "ok" if ollama_ok else "model_not_found"
    except Exception as e:
        health["ollama"]["status"] = f"error: {str(e)}"

    # Check Groq
    try:
        groq_ok = llm_client.check_groq_health()
        health["groq"]["status"] = "ok" if groq_ok else "error"
    except Exception as e:
        health["groq"]["status"] = f"error: {str(e)}"

    return health


@app.post("/api/upload")
async def upload_zip(file: UploadFile = File(...)):
    """
    Upload a ZIP file to start business digitization.

    Accepts a ZIP file, saves it, and kicks off the file discovery phase.

    Returns:
        Job ID and file discovery results.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are accepted."
        )

    job_id = str(uuid.uuid4())[:12]
    logger.info(f"[{job_id}] Received upload: {file.filename}")

    # Create job status
    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="processing",
        current_phase="file_discovery",
        message="Extracting and classifying files...",
    )

    try:
        # Save uploaded file
        upload_path = settings.get_upload_path() / f"{job_id}.zip"
        with open(upload_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info(f"[{job_id}] ZIP saved: {upload_path}")

        # Run file discovery
        collection = file_discovery_agent.discover(
            str(upload_path), job_id=job_id
        )

        # Store results
        file_collections[job_id] = collection

        # Update job status
        jobs[job_id].status = "discovered"
        jobs[job_id].progress = 15.0
        jobs[job_id].current_phase = "file_discovery_complete"
        jobs[job_id].message = (
            f"Found {collection.total_files} files: "
            f"{len(collection.documents)} documents, "
            f"{len(collection.spreadsheets)} spreadsheets, "
            f"{len(collection.images)} images, "
            f"{len(collection.videos)} videos"
        )

        return {
            "job_id": job_id,
            "status": "discovered",
            "message": jobs[job_id].message,
            "file_collection": collection.model_dump(),
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Upload failed: {e}")
        jobs[job_id].status = "failed"
        jobs[job_id].error_message = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get the current status of a digitization job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id].model_dump()


@app.get("/api/profile/{job_id}")
async def get_profile(job_id: str):
    """Get the generated business profile for a completed job."""
    profile_data = storage_manager.load_profile(job_id)
    if not profile_data:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Job may still be processing."
        )
    import json
    return json.loads(profile_data)


@app.get("/api/job-data/{job_id}")
async def get_job_data(job_id: str):
    """Get all job data including parsed documents, tables, media, and profile."""
    import json
    from pathlib import Path
    
    index_dir = storage_manager.get_job_subdir(job_id, "index")
    
    # Try to load complete job data first
    complete_data_path = index_dir / "complete_job_data.json"
    if complete_data_path.exists():
        data = json.loads(complete_data_path.read_text(encoding="utf-8"))
        return data
    
    # Fallback: load individual files
    job_data = {"job_id": job_id}
    
    # Load file collection
    file_collection_path = index_dir / "file_collection.json"
    if file_collection_path.exists():
        job_data["file_collection"] = json.loads(file_collection_path.read_text(encoding="utf-8"))
    
    # Load parsed documents
    parsed_docs_path = index_dir / "parsed_documents.json"
    if parsed_docs_path.exists():
        job_data["parsed_documents"] = json.loads(parsed_docs_path.read_text(encoding="utf-8"))
    
    # Load document indexes
    doc_indexes_path = index_dir / "document_indexes.json"
    if doc_indexes_path.exists():
        job_data["document_indexes"] = json.loads(doc_indexes_path.read_text(encoding="utf-8"))
    
    # Load extracted tables
    tables_path = index_dir / "extracted_tables.json"
    if tables_path.exists():
        job_data["extracted_tables"] = json.loads(tables_path.read_text(encoding="utf-8"))
    
    # Load media collection
    media_path = index_dir / "media_collection.json"
    if media_path.exists():
        job_data["media_collection"] = json.loads(media_path.read_text(encoding="utf-8"))
    
    # Load image analyses
    analyses_path = index_dir / "image_analyses.json"
    if analyses_path.exists():
        job_data["image_analyses"] = json.loads(analyses_path.read_text(encoding="utf-8"))
    
    # Load validation
    validation_path = index_dir / "validation.json"
    if validation_path.exists():
        job_data["validation"] = json.loads(validation_path.read_text(encoding="utf-8"))
    
    # Load profile
    profile_data = storage_manager.load_profile(job_id)
    if profile_data:
        job_data["business_profile"] = json.loads(profile_data)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="No job data found")
    
    return job_data


@app.get("/api/job-data/{job_id}/parsed-documents")
async def get_parsed_documents(job_id: str):
    """Get parsed documents for a job."""
    import json
    from pathlib import Path
    
    index_dir = storage_manager.get_job_subdir(job_id, "index")
    parsed_docs_path = index_dir / "parsed_documents.json"
    
    if not parsed_docs_path.exists():
        raise HTTPException(status_code=404, detail="Parsed documents not found")
    
    return json.loads(parsed_docs_path.read_text(encoding="utf-8"))


@app.get("/api/job-data/{job_id}/tables")
async def get_tables(job_id: str):
    """Get extracted tables for a job."""
    import json
    from pathlib import Path
    
    index_dir = storage_manager.get_job_subdir(job_id, "index")
    tables_path = index_dir / "extracted_tables.json"
    
    if not tables_path.exists():
        raise HTTPException(status_code=404, detail="Tables not found")
    
    return json.loads(tables_path.read_text(encoding="utf-8"))


@app.get("/api/job-data/{job_id}/media")
async def get_media(job_id: str):
    """Get media collection and image analyses for a job."""
    import json
    from pathlib import Path
    
    index_dir = storage_manager.get_job_subdir(job_id, "index")
    
    media_data = {}
    
    media_path = index_dir / "media_collection.json"
    if media_path.exists():
        media_data["media_collection"] = json.loads(media_path.read_text(encoding="utf-8"))
    
    analyses_path = index_dir / "image_analyses.json"
    if analyses_path.exists():
        media_data["image_analyses"] = json.loads(analyses_path.read_text(encoding="utf-8"))
    
    if not media_data:
        raise HTTPException(status_code=404, detail="Media data not found")
    
    return media_data


@app.get("/api/job-data/{job_id}/pdf-wise")
async def get_pdf_wise_data(job_id: str):
    """Get PDF-wise organized data with page-level metadata and YOLO detections."""
    import json
    from pathlib import Path
    
    index_dir = storage_manager.get_job_subdir(job_id, "index")
    pdf_wise_path = index_dir / "pdf_wise_data.json"
    
    if not pdf_wise_path.exists():
        raise HTTPException(status_code=404, detail="PDF-wise data not found")
    
    return json.loads(pdf_wise_path.read_text(encoding="utf-8"))


@app.get("/api/files/{job_id}")
async def get_files(job_id: str):
    """Get the file collection for a job."""
    if job_id not in file_collections:
        raise HTTPException(status_code=404, detail="Job not found")
    return file_collections[job_id].model_dump()


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and all associated data."""
    storage_manager.cleanup_job(job_id)
    jobs.pop(job_id, None)
    file_collections.pop(job_id, None)
    return {"message": f"Job {job_id} deleted"}


@app.post("/api/process/{job_id}")
async def process_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Start the full digitization pipeline for a discovered job.

    Call this after /api/upload returns with a job_id.
    Processing runs in the background — poll /api/status/{job_id}.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if jobs[job_id].status == "processing":
        raise HTTPException(status_code=409, detail="Job already processing")

    # Find the ZIP file
    zip_path = settings.get_upload_path() / f"{job_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP file not found")

    jobs[job_id].status = "processing"
    jobs[job_id].current_phase = "pipeline_start"
    jobs[job_id].message = "Starting full pipeline..."

    # Run pipeline in background
    background_tasks.add_task(_run_full_pipeline, job_id, str(zip_path))

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Full pipeline started. Poll /api/status/{job_id} for updates.",
    }


@app.post("/api/upload-and-process")
async def upload_and_process(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a ZIP and immediately start full pipeline processing.

    Combines /api/upload + /api/process into one call.
    Returns immediately with job_id — poll /api/status for progress.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted.")

    job_id = str(uuid.uuid4())[:12]
    logger.info(f"[{job_id}] Upload+Process: {file.filename}")

    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="processing",
        current_phase="uploading",
        message="Saving and starting pipeline...",
    )

    try:
        upload_path = settings.get_upload_path() / f"{job_id}.zip"
        with open(upload_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        background_tasks.add_task(_run_full_pipeline, job_id, str(upload_path))

        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Pipeline started. Poll /api/status/{job_id} for progress.",
        }
    except Exception as e:
        jobs[job_id].status = "failed"
        jobs[job_id].error_message = str(e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STARTUP
# =============================================================================

@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("Business Digitization Agent — Starting up")
    logger.info(f"Groq Model: {settings.groq_model}")
    logger.info(f"Ollama Model: {settings.ollama_vision_model}")
    logger.info("=" * 60)


# Mount frontend static files
from backend.config import PROJECT_ROOT

frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        index_path = frontend_dir / "index.html"
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
