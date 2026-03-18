import os
import tempfile
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv(".env")

# Agents
from backend.agents.file_discovery import FileDiscoveryAgent, FileDiscoveryInput
from backend.agents.document_parsing import DocumentParsingAgent, DocumentParsingInput
from backend.agents.table_extraction import TableExtractionAgent, TableExtractionInput
from backend.agents.media_extraction import MediaExtractionAgent, MediaExtractionInput
from backend.agents.indexing import IndexingAgent, IndexingInput
from backend.agents.schema_mapping_v2 import SchemaMappingAgent
from backend.models.schemas import SchemaMappingInput
from backend.agents.validation_agent import ValidationAgent
from backend.models.schemas import ValidationInput as ValidationInputSchema
from backend.utils.storage_manager import StorageManager

app = FastAPI(title="Digi-Biz API")

# Allow CORS for Next.js
origins = [
    "http://localhost:3000",
]
if os.getenv("FRONTEND_URL"):
    origins.append(os.getenv("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
PROFILES_DIR = Path("./storage/profiles")
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job status
jobs: Dict[str, Dict[str, Any]] = {}

def generate_job_id() -> str:
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

@app.post("/api/upload")
async def upload_zip(file: UploadFile = File(...)):
    """Upload ZIP and start processing"""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Must be a ZIP file")

    job_id = generate_job_id()
    temp_dir = Path(tempfile.gettempdir()) / "digi_biz" / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    zip_path = temp_dir / file.filename
    with open(zip_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Initialize job status
    jobs[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "progress": 0.0,
        "current_phase": "upload",
        "created_at": datetime.now().isoformat(),
        "profile_path": None
    }

    # Start background processing
    import asyncio
    asyncio.create_task(process_job(job_id, str(zip_path)))

    return {"job_id": job_id, "status": "processing"}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get processing status"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@app.get("/api/profiles")
async def list_profiles():
    """List all profiles"""
    profiles = []
    for profile_file in PROFILES_DIR.glob("*.json"):
        if profile_file.name.startswith("profile_"):
            with open(profile_file) as f:
                profile = json.load(f)
                profiles.append({
                    "job_id": profile.get("job_id"),
                    "name": profile.get("business_info", {}).get("name", "Unknown"),
                    "created_at": profile.get("created_at"),
                    "service_count": len(profile.get("services", [])),
                    "business_type": profile.get("business_type", "unknown")
                })
    return {"profiles": sorted(profiles, key=lambda x: x.get('created_at', ''), reverse=True)}

@app.get("/api/profile/{job_id}")
async def get_profile(job_id: str):
    """Get complete profile"""
    profile_path = PROFILES_DIR / f"profile_{job_id}.json"
    
    if not profile_path.exists():
        raise HTTPException(404, "Profile not found")
    
    with open(profile_path) as f:
        profile = json.load(f)
    
    return profile

@app.put("/api/profile/{job_id}")
async def update_profile(job_id: str, profile: dict):
    """Update profile (edit)"""
    profile_path = PROFILES_DIR / f"profile_{job_id}.json"
    
    if not profile_path.exists():
        raise HTTPException(404, "Profile not found")
    
    profile["updated_at"] = datetime.now().isoformat()
    
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)
    
    return {"success": True, "message": "Profile updated"}

@app.delete("/api/profile/{job_id}")
async def delete_profile(job_id: str):
    """Delete profile"""
    profile_path = PROFILES_DIR / f"profile_{job_id}.json"
    
    if not profile_path.exists():
        raise HTTPException(404, "Profile not found")
    
    profile_path.unlink()
    
    return {"success": True, "message": "Profile deleted"}

@app.post("/api/profile/{job_id}/export")
async def export_profile(job_id: str):
    """Export profile as JSON"""
    profile_path = PROFILES_DIR / f"profile_{job_id}.json"
    
    if not profile_path.exists():
        raise HTTPException(404, "Profile not found")
    
    with open(profile_path) as f:
        profile = json.load(f)
    
    return JSONResponse(
        content=profile,
        headers={"Content-Disposition": f"attachment; filename=profile_{job_id}.json"}
    )

async def process_job(job_id: str, file_path: str):
    """Process job in background with progress updates"""
    try:
        # Update status
        jobs[job_id]["current_phase"] = "file_discovery"
        jobs[job_id]["progress"] = 10.0
        
        # Step 1: File Discovery
        storage_manager = StorageManager(storage_base=str(PROFILES_DIR))
        discovery_agent = FileDiscoveryAgent(storage_manager=storage_manager)
        discovery_output = discovery_agent.discover(
            FileDiscoveryInput(zip_file_path=file_path, job_id=job_id)
        )
        
        if not discovery_output.success:
            raise Exception(f"File discovery failed: {discovery_output.errors}")
        
        # Step 2: Document Parsing (30%)
        jobs[job_id]["current_phase"] = "document_parsing"
        jobs[job_id]["progress"] = 30.0
        parsing_agent = DocumentParsingAgent(enable_ocr=False)
        parsing_output = parsing_agent.parse(
            DocumentParsingInput(documents=discovery_output.documents, job_id=job_id)
        )
        
        # Step 3: Table Extraction (50%)
        jobs[job_id]["current_phase"] = "table_extraction"
        jobs[job_id]["progress"] = 50.0
        table_agent = TableExtractionAgent()
        tables_output = table_agent.extract(
            TableExtractionInput(parsed_documents=parsing_output.parsed_documents, job_id=job_id)
        )
        
        # Step 4: Media Extraction (70%)
        jobs[job_id]["current_phase"] = "media_extraction"
        jobs[job_id]["progress"] = 70.0
        media_agent = MediaExtractionAgent(enable_deduplication=False)
        media_output = media_agent.extract_all(
            MediaExtractionInput(
                parsed_documents=parsing_output.parsed_documents,
                standalone_files=[img.file_path for img in discovery_output.images],
                job_id=job_id
            )
        )
        
        # Step 5: Indexing (85%)
        jobs[job_id]["current_phase"] = "indexing"
        jobs[job_id]["progress"] = 85.0
        indexing_agent = IndexingAgent()
        page_index = indexing_agent.build_index(
            IndexingInput(
                parsed_documents=parsing_output.parsed_documents,
                tables=tables_output.tables,
                images=media_output.media.images if media_output.success else [],
                job_id=job_id
            )
        )
        
        # Step 6: Schema Mapping (95%)
        jobs[job_id]["current_phase"] = "schema_mapping"
        jobs[job_id]["progress"] = 95.0
        schema_agent = SchemaMappingAgent()
        mapping_output = schema_agent.map_to_schema(
            SchemaMappingInput(page_index=page_index, job_id=job_id)
        )
        
        if not mapping_output.success:
            raise Exception(f"Schema mapping failed: {mapping_output.errors}")
        
        # Validate
        validation_agent = ValidationAgent()
        validation_output = validation_agent.validate(
            ValidationInputSchema(profile=mapping_output.profile, job_id=job_id)
        )
        
        # Add metadata
        profile = mapping_output.profile.model_dump(mode='json')
        profile["job_id"] = job_id
        profile["created_at"] = datetime.now().isoformat()
        profile["validation"] = {
            "completeness_score": validation_output.completeness_score,
            "field_scores": validation_output.field_scores
        }
        
        # Save profile
        profile_path = PROFILES_DIR / f"profile_{job_id}.json"
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        
        jobs[job_id]["profile_path"] = str(profile_path)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100.0
        jobs[job_id]["current_phase"] = "done"
        
        print(f"[SUCCESS] Job {job_id} completed successfully")
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"[ERROR] Job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
