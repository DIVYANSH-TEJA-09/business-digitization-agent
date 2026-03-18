import os
import tempfile
import time
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv(".env")

# Agents
from backend.agents.file_discovery import FileDiscoveryAgent, FileDiscoveryInput
from backend.agents.document_parsing import DocumentParsingAgent, DocumentParsingInput
from backend.agents.table_extraction import TableExtractionAgent, TableExtractionInput
from backend.agents.media_extraction import MediaExtractionAgent, MediaExtractionInput
from backend.agents.indexing import IndexingAgent, IndexingInput
from backend.agents.schema_mapping_simple import SchemaMappingAgent
from backend.models.schemas import SchemaMappingInput
from backend.agents.validation_agent import ValidationAgent
from backend.models.schemas import ValidationInput as ValidationInputSchema
from backend.utils.storage_manager import StorageManager
from backend.models.schemas import PageIndex

app = FastAPI(title="Digi-Biz API")

# Allow CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_job_id() -> str:
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

@app.post("/upload")
async def process_zip(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Must be a ZIP file")
        
    job_id = generate_job_id()
    temp_dir = Path(tempfile.gettempdir()) / "digi_biz" / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    zip_path = temp_dir / file.filename
    with open(zip_path, "wb") as f:
        f.write(await file.read())
        
    storage_manager = StorageManager(storage_base=str(temp_dir))
    
    print("Step 1: File Discovery")
    discovery_agent = FileDiscoveryAgent(storage_manager=storage_manager)
    discovery_output = discovery_agent.discover(
        FileDiscoveryInput(zip_file_path=str(zip_path), job_id=job_id)
    )
    if not discovery_output.success:
        raise HTTPException(status_code=500, detail="File discovery failed")
        
    print("Step 2: Document Parsing")
    parsing_agent = DocumentParsingAgent(enable_ocr=False)
    parsing_output = parsing_agent.parse(
        DocumentParsingInput(documents=discovery_output.documents, job_id=job_id, enable_ocr=False)
    )
    
    print("Step 3: Table Extraction")
    table_agent = TableExtractionAgent()
    tables_output = table_agent.extract(
        TableExtractionInput(parsed_documents=parsing_output.parsed_documents, job_id=job_id)
    )
    
    print("Step 4: Media Extraction")
    media_agent = MediaExtractionAgent(enable_deduplication=False)
    media_output = media_agent.extract_all(
        MediaExtractionInput(
            parsed_documents=parsing_output.parsed_documents,
            standalone_files=[img.file_path for img in discovery_output.images],
            job_id=job_id
        )
    )
    
    print("Step 5: Indexing")
    indexing_agent = IndexingAgent()
    page_index = indexing_agent.build_index(
        IndexingInput(
            parsed_documents=parsing_output.parsed_documents,
            tables=tables_output.tables,
            images=media_output.media.images if media_output.success else [],
            job_id=job_id
        )
    )
    
    print("Step 6: Schema Mapping")
    schema_agent = SchemaMappingAgent()
    mapping_output = schema_agent.map_to_schema(
        SchemaMappingInput(page_index=page_index, job_id=job_id)
    )
    if not mapping_output.success:
        raise HTTPException(status_code=500, detail=f"Schema mapping failed: {mapping_output.errors}")
        
    print("Step 7: Validation")
    val_agent = ValidationAgent()
    val_out = val_agent.validate(
        ValidationInputSchema(profile=mapping_output.profile, job_id=job_id)
    )
    
    return val_out.model_dump(mode="json")
