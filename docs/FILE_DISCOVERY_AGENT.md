# File Discovery Agent

**Agent 1** in the Agentic Business Digitization Pipeline

## Overview

The File Discovery Agent is responsible for securely extracting ZIP files and classifying all contained files by type. It implements comprehensive security checks to prevent path traversal attacks, zip bombs, and handles corrupted files gracefully.

## Features

- ✅ Secure ZIP extraction with safety checks
- ✅ Multi-strategy file type classification
- ✅ Path traversal prevention
- ✅ ZIP bomb detection (compression ratio check)
- ✅ File size and count limits
- ✅ Directory structure preservation
- ✅ Comprehensive error handling
- ✅ Detailed metadata generation

## Security Features

| Check | Description | Limit |
|-------|-------------|-------|
| **File Size** | Maximum ZIP file size | 500MB (configurable) |
| **File Count** | Maximum files per ZIP | 100 (configurable) |
| **Compression Ratio** | Zip bomb detection | 1000:1 max |
| **Path Traversal** | Block `..` patterns | Always blocked |
| **Magic Numbers** | Validate file content | Auto-detected |

## Usage

### Basic Usage

```python
from backend.agents.file_discovery import FileDiscoveryAgent, FileDiscoveryInput
from backend.utils.storage_manager import StorageManager

# Initialize
storage = StorageManager(storage_base="./storage")
agent = FileDiscoveryAgent(storage_manager=storage)

# Create input
input_data = FileDiscoveryInput(
    zip_file_path="/path/to/upload.zip",
    job_id="job_20240315_abc123"
)

# Run discovery
output = agent.discover(input_data)

# Check results
if output.success:
    print(f"Discovered {output.total_files} files")
    print(f"Documents: {len(output.documents)}")
    print(f"Images: {len(output.images)}")
    print(f"Extraction dir: {output.extraction_dir}")
else:
    print(f"Errors: {output.errors}")
```

### Input Schema

```python
FileDiscoveryInput(
    zip_file_path: str,        # Absolute path to ZIP file
    job_id: str,                # Unique job identifier
    max_file_size: int = 524288000,  # Optional: 500MB default
    max_files: int = 100         # Optional: 100 files default
)
```

### Output Schema

```python
FileDiscoveryOutput(
    job_id: str,
    success: bool,
    
    # Classified files
    documents: List[DocumentFile],      # PDFs, DOCX, DOC
    spreadsheets: List[SpreadsheetFile], # XLSX, XLS, CSV
    images: List[ImageFile],            # JPG, PNG, GIF, WEBP
    videos: List[VideoFile],            # MP4, AVI, MOV, MKV
    unknown: List[UnknownFile],         # Unsupported types
    
    # Structure
    directory_tree: DirectoryNode,      # Folder hierarchy
    
    # Metadata
    total_files: int,
    extraction_dir: str,
    processing_time: float,
    errors: List[str],
    
    # Summary
    summary: dict
)
```

## File Type Classification

The agent uses a **3-strategy approach**:

1. **MIME Type Detection** (python-magic if available)
2. **Extension-based** classification
3. **Magic Number** validation

### Supported Types

| Category | Extensions |
|----------|-----------|
| **Documents** | .pdf, .doc, .docx |
| **Spreadsheets** | .xls, .xlsx, .csv |
| **Images** | .jpg, .jpeg, .png, .gif, .webp |
| **Videos** | .mp4, .avi, .mov, .mkv |

## Directory Structure

After extraction, files are organized as:

```
storage/
└── extracted/
    └── {job_id}/
        ├── documents/
        ├── spreadsheets/
        ├── images/
        ├── videos/
        ├── unknown/
        └── discovery_metadata.json
```

## Error Handling

| Error Type | Behavior |
|-----------|----------|
| Invalid ZIP | `success=False`, error in list |
| Path traversal | File skipped, warning logged |
| Corrupted file | File skipped, error logged |
| Unsupported type | Added to `unknown` list |
| Size exceeded | `success=False`, processing stopped |

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest tests/agents/test_file_discovery.py -v

# Run with coverage
pytest tests/agents/test_file_discovery.py --cov=backend.agents.file_discovery

# Run specific test
pytest tests/agents/test_file_discovery.py::TestFileDiscoveryAgent::test_discover_valid_zip -v
```

### Test Coverage

- ✅ Valid ZIP with mixed files
- ✅ Nested folder structures
- ✅ Non-existent files
- ✅ File size exceeded
- ✅ File count exceeded
- ✅ Path traversal attempts
- ✅ Corrupted ZIP files
- ✅ File type classification
- ✅ Directory tree building
- ✅ Metadata persistence

## Configuration

Environment variables (see `.env.example`):

```bash
# File limits
MAX_FILE_SIZE=524288000    # 500MB
MAX_FILES_PER_ZIP=100

# Storage paths
STORAGE_BASE=./storage
EXTRACTED_DIR=extracted
```

## Performance

Typical performance for business document folders:

| Files | Total Size | Processing Time |
|-------|-----------|-----------------|
| 10 files | 5MB | ~0.5s |
| 50 files | 25MB | ~2s |
| 100 files | 50MB | ~4s |

## Next Steps

After file discovery completes successfully:

1. **Document Parsing Agent** processes PDFs and DOCX files
2. **Table Extraction Agent** finds and structures tables
3. **Media Extraction Agent** extracts embedded images
4. **Vision Agent** analyzes images with Qwen3.5:0.8B

## Files

- `backend/agents/file_discovery.py` - Main agent implementation
- `backend/utils/file_classifier.py` - File type classification
- `backend/utils/storage_manager.py` - Storage organization
- `tests/agents/test_file_discovery.py` - Unit tests
