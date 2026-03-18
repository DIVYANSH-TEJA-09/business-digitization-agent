# Digi-Biz Documentation

## Agentic Business Digitization Framework

**Version:** 1.0.0  
**Last Updated:** March 17, 2026

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Agents](#agents)
4. [Installation](#installation)
5. [Usage](#usage)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)

---

## Overview

**Digi-Biz** is an AI-powered agentic framework that automatically converts unstructured business documents into structured digital business profiles.

### What It Does

- Accepts ZIP files containing mixed business documents (PDF, DOCX, Excel, images, videos)
- Intelligently extracts and structures information using multi-agent workflows
- Generates comprehensive digital business profiles with product/service inventories
- Provides dynamic UI for viewing and editing results

### Key Features

✅ **Multi-Agent Pipeline** - 5 specialized agents working together  
✅ **Vectorless RAG** - Fast document retrieval without embeddings  
✅ **Groq Vision** - Image analysis with Llama-4-Scout (17B)  
✅ **Production-Ready** - Error handling, validation, logging  
✅ **Streamlit UI** - Interactive web interface  

---

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface (Streamlit)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ZIP Upload   │  │ Results View │  │ Vision Tab   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Agent Pipeline                              │
│  1. File Discovery → 2. Document Parsing → 3. Table Extract │
│  4. Media Extraction → 5. Vision (Groq) → 6. Indexing (RAG) │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  File Storage (FileSystem) • Index (In-Memory) • Profiles   │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.10+ |
| **Document Parsing** | pdfplumber, python-docx, openpyxl |
| **Image Processing** | Pillow, pdf2image |
| **Vision AI** | Groq API (Llama-4-Scout-17B) |
| **LLM (Text)** | Groq API (gpt-oss-120b) |
| **Validation** | Pydantic |
| **Frontend** | Streamlit |
| **Storage** | Local Filesystem |

---

## Agents

### 1. File Discovery Agent

**Purpose:** Extract ZIP files and classify all contained files

**Input:**
```python
FileDiscoveryInput(
    zip_file_path="/path/to/upload.zip",
    job_id="job_123",
    max_file_size=524288000,  # 500MB
    max_files=100
)
```

**Output:**
```python
FileDiscoveryOutput(
    job_id="job_123",
    success=True,
    documents=[...],      # PDFs, DOCX
    spreadsheets=[...],   # XLSX, CSV
    images=[...],         # JPG, PNG
    videos=[...],         # MP4, AVI
    total_files=10,
    extraction_dir="/storage/extracted/job_123"
)
```

**Features:**
- ZIP bomb detection (1000:1 ratio limit)
- Path traversal prevention
- File type classification (3-strategy approach)
- Directory structure preservation

**File:** `backend/agents/file_discovery.py`

---

### 2. Document Parsing Agent

**Purpose:** Extract text and structure from PDF/DOCX files

**Input:**
```python
DocumentParsingInput(
    documents=[...],  # From File Discovery
    job_id="job_123",
    enable_ocr=True
)
```

**Output:**
```python
DocumentParsingOutput(
    job_id="job_123",
    success=True,
    parsed_documents=[...],
    total_pages=56,
    processing_time=2.5
)
```

**Features:**
- PDF parsing (pdfplumber primary, PyPDF2 fallback, OCR final)
- DOCX parsing with structure preservation
- Table extraction
- Embedded image extraction

**File:** `backend/agents/document_parsing.py`

---

### 3. Table Extraction Agent

**Purpose:** Detect and classify tables from parsed documents

**Input:**
```python
TableExtractionInput(
    parsed_documents=[...],
    job_id="job_123"
)
```

**Output:**
```python
TableExtractionOutput(
    job_id="job_123",
    success=True,
    tables=[...],
    total_tables=42,
    tables_by_type={
        "itinerary": 33,
        "pricing": 6,
        "general": 3
    }
)
```

**Table Types:**
| Type | Detection Criteria |
|------|-------------------|
| **PRICING** | Headers: price/cost/rate; Currency: $, €, ₹ |
| **ITINERARY** | Headers: day/time/date; Patterns: "Day 1", "9:00 AM" |
| **SPECIFICATIONS** | Headers: spec/feature/dimension/weight |
| **MENU** | Headers: menu/dish/food/meal |
| **INVENTORY** | Headers: stock/quantity/available |
| **GENERAL** | Fallback |

**File:** `backend/agents/table_extraction.py`

---

### 4. Media Extraction Agent

**Purpose:** Extract embedded and standalone media

**Input:**
```python
MediaExtractionInput(
    parsed_documents=[...],
    standalone_files=[...],
    job_id="job_123"
)
```

**Output:**
```python
MediaExtractionOutput(
    job_id="job_123",
    success=True,
    media=MediaCollection(
        images=[...],
        total_count=15,
        extraction_summary={...}
    ),
    duplicates_removed=3
)
```

**Features:**
- PDF embedded image extraction (xref method)
- DOCX embedded image extraction (ZIP method)
- Perceptual hashing for deduplication
- Quality assessment

**File:** `backend/agents/media_extraction.py`

---

### 5. Vision Agent (Groq)

**Purpose:** Analyze images using Groq Vision API

**Input:**
```python
VisionAnalysisInput(
    image=ExtractedImage(...),
    context="Restaurant menu with burgers",
    job_id="job_123"
)
```

**Output:**
```python
ImageAnalysis(
    image_id="img_001",
    description="A delicious burger with lettuce...",
    category=ImageCategory.FOOD,
    tags=["burger", "food", "restaurant"],
    is_product=False,
    is_service_related=True,
    confidence=0.92,
    metadata={
        'provider': 'groq',
        'model': 'llama-4-scout-17b',
        'processing_time': 1.85
    }
)
```

**Features:**
- Groq API integration (Llama-4-Scout-17B)
- Ollama fallback
- Context-aware prompts
- JSON response parsing
- Batch processing
- Automatic image resizing (<4MB)

**File:** `backend/agents/vision_agent.py`

---

### 6. Indexing Agent (Vectorless RAG)

**Purpose:** Build inverted index for fast document retrieval

**Input:**
```python
IndexingInput(
    parsed_documents=[...],
    tables=[...],
    images=[...],
    job_id="job_123"
)
```

**Output:**
```python
IndexingOutput(
    job_id="job_123",
    success=True,
    page_index=PageIndex(
        documents={...},
        page_index={
            "burger": [PageReference(...)],
            "price": [PageReference(...)]
        },
        table_index={...},
        media_index={...}
    ),
    total_keywords=1250
)
```

**Features:**
- Keyword extraction (tokenization, N-grams, entities)
- Inverted index creation
- Query expansion with synonyms
- Context-aware retrieval
- Relevance scoring

**File:** `backend/agents/indexing.py`

---

## Installation

### Prerequisites

- Python 3.10+
- Git (for cloning)
- Groq API account (free at https://console.groq.com)

### Step 1: Clone Repository

```bash
cd D:\Viswam_Projects\digi-biz
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

Create `.env` file:

```bash
# Groq API (required for vision and text LLM)
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=gpt-oss-120b
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct

# Optional: Ollama for local fallback
OLLAMA_HOST=http://localhost:11434
OLLAMA_VISION_MODEL=qwen3.5:0.8b

# Application settings
APP_ENV=development
LOG_LEVEL=INFO
MAX_FILE_SIZE=524288000    # 500MB
MAX_FILES_PER_ZIP=100

# Storage
STORAGE_BASE=./storage
```

### Step 4: Get Groq API Key

1. Visit https://console.groq.com
2. Sign up / Log in
3. Go to "API Keys"
4. Create new key
5. Copy to `.env` file

### Step 5: Verify Installation

```bash
# Test Groq connection
python test_groq_vision.py

# Run tests
pytest tests/ -v

# Start Streamlit app
streamlit run app.py
```

---

## Usage

### Quick Start

1. **Start the app:**
   ```bash
   streamlit run app.py
   ```

2. **Open browser:** http://localhost:8501

3. **Upload ZIP** containing:
   - Business documents (PDF, DOCX)
   - Spreadsheets (XLSX, CSV)
   - Images (JPG, PNG)
   - Videos (MP4, AVI)

4. **Click "Start Processing"**

5. **View results** in tabs:
   - Results (documents, tables)
   - Vision Analysis (image descriptions)

### Command Line Usage

```python
from backend.agents.file_discovery import FileDiscoveryAgent, FileDiscoveryInput

# Initialize agent
agent = FileDiscoveryAgent()

# Create input
input_data = FileDiscoveryInput(
    zip_file_path="business_docs.zip",
    job_id="job_001"
)

# Run discovery
output = agent.discover(input_data)

print(f"Discovered {output.total_files} files")
```

### Batch Processing

```python
from backend.agents.vision_agent import VisionAgent

# Initialize with Groq
agent = VisionAgent(provider="groq")

# Analyze multiple images
analyses = agent.analyze_batch(images, context="Product catalog")

for analysis in analyses:
    print(f"{analysis.category.value}: {analysis.description}")
```

---

## API Reference

### File Discovery Agent

```python
class FileDiscoveryAgent:
    def discover(self, input: FileDiscoveryInput) -> FileDiscoveryOutput:
        """Extract ZIP and classify files"""
        pass
```

### Document Parsing Agent

```python
class DocumentParsingAgent:
    def parse(self, input: DocumentParsingInput) -> DocumentParsingOutput:
        """Parse documents and extract text/tables/images"""
        pass
```

### Vision Agent

```python
class VisionAgent:
    def analyze(self, input: VisionAnalysisInput) -> ImageAnalysis:
        """Analyze single image"""
        pass
    
    def analyze_batch(self, images: List[ExtractedImage], context: str) -> List[ImageAnalysis]:
        """Analyze multiple images"""
        pass
```

### Indexing Agent

```python
class IndexingAgent:
    def build_index(self, input: IndexingInput) -> PageIndex:
        """Build inverted index"""
        pass
    
    def retrieve_context(self, query: str, page_index: PageIndex, max_pages: int) -> Dict:
        """Retrieve relevant context"""
        pass
```

---

## Troubleshooting

### Groq API Issues

**Error:** `Groq API Key Missing`

**Solution:**
```bash
# Check .env file
cat .env | grep GROQ_API_KEY

# Should show your actual key, not placeholder
GROQ_API_KEY=gsk_xxxxx
```

**Error:** `Request Entity Too Large (413)`

**Solution:** Images are automatically resized. If still failing, compress images before uploading.

---

### Ollama Issues

**Error:** `Cannot connect to Ollama`

**Solution:**
```bash
# Start Ollama server
ollama serve

# Verify running
ollama list
```

---

### Memory Issues

**Error:** `Out of memory`

**Solution:**
```bash
# Reduce concurrent processing
# In .env:
MAX_CONCURRENT_PARSING=3
MAX_CONCURRENT_VISION=2
```

---

### Performance Issues

**Slow processing:**

1. Check internet connection (Groq API requires internet)
2. Reduce image sizes before upload
3. Process fewer files at once
4. Check Groq API status: https://status.groq.com

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Agent Tests

```bash
# File Discovery
pytest tests/agents/test_file_discovery.py -v

# Document Parsing
pytest tests/agents/test_document_parsing.py -v

# Vision Agent
pytest tests/agents/test_vision_agent.py -v

# Indexing Agent
pytest tests/agents/test_indexing.py -v  # (to be created)
```

### Test Coverage

```bash
pytest tests/ --cov=backend --cov-report=html
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS/Linux
```

---

## Project Structure

```
digi-biz/
├── backend/
│   ├── agents/
│   │   ├── file_discovery.py      ✅ Complete
│   │   ├── document_parsing.py    ✅ Complete
│   │   ├── table_extraction.py    ✅ Complete
│   │   ├── media_extraction.py    ✅ Complete
│   │   ├── vision_agent.py        ✅ Complete
│   │   └── indexing.py            ✅ Complete
│   ├── models/
│   │   ├── schemas.py             ✅ Complete
│   │   └── enums.py               ✅ Complete
│   └── utils/
│       ├── storage_manager.py
│       ├── file_classifier.py
│       ├── logger.py
│       └── groq_vision_client.py
├── tests/
│   └── agents/
│       ├── test_file_discovery.py
│       ├── test_document_parsing.py
│       ├── test_table_extraction.py
│       ├── test_media_extraction.py
│       └── test_vision_agent.py
├── app.py                         ✅ Streamlit App
├── requirements.txt
├── .env.example
└── docs/
    └── DOCUMENTATION.md           ✅ This file
```

---

## Performance Benchmarks

| Agent | Processing Time | Test Data |
|-------|----------------|-----------|
| File Discovery | ~1-2s | 10 files ZIP |
| Document Parsing | ~50ms/doc | PDF 10 pages |
| Table Extraction | ~100ms/doc | 5 tables |
| Media Extraction | ~200ms/image | 5 images |
| Vision Analysis | ~2s/image | Groq API |
| Indexing | ~500ms | 50 pages |

**End-to-End:** <2 minutes for typical business folder (10 documents, 5 images)

---

## License

MIT License - See LICENSE file for details

---

## Support

- **GitHub Issues:** Report bugs and feature requests
- **Documentation:** This file + inline code comments
- **Email:** [Your contact here]

---

**Last Updated:** March 17, 2026  
**Version:** 1.0.0  
**Status:** Production Ready ✅
