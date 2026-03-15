# Business Digitization Agent

🤖 An AI-powered multi-agent system that transforms unstructured business documents into structured digital business profiles.

## Overview

This system accepts a ZIP file containing business documents (PDFs, images, spreadsheets) and automatically:

1. **Discovers and classifies** all files
2. **Parses documents** extracting text and structure
3. **Extracts tables** with type classification
4. **Extracts images** from PDFs using PyMuPDF
5. **Detects objects** in images using YOLO
6. **Analyzes images** using Qwen 3.5 vision model
7. **Maps data** to a structured business profile schema
8. **Validates** the profile for completeness

## Features

### Multi-Agent Architecture
- **File Discovery Agent**: Extracts and classifies files from ZIP
- **Document Parsing Agent**: Parses PDF, DOCX, XLSX files
- **Table Extraction Agent**: Identifies and structures tables
- **Media Extraction Agent**: Extracts embedded and standalone media
- **Vision Agent**: Analyzes images with Qwen 3.5 0.8B
- **Schema Mapping Agent**: Maps data to business profile schema
- **Validation Agent**: Validates and scores the profile

### AI-Powered Processing
- **YOLO v8 Nano**: Object detection in extracted images
- **Qwen 3.5 0.8B**: Vision analysis for image descriptions
- **GPT-OSS-120B**: Schema mapping and reasoning (via Groq)

### Streamlit UI
- 📤 Upload & Process interface
- 🔄 Real-time pipeline visualization
- 📊 Profile viewer with tabs
- 📋 Processing logs

## Quick Start

### Prerequisites

- Python 3.10+
- Ollama with Qwen 3.5 0.8B model
- Groq API key (optional, for GPT-OSS-120B)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd business-digitization-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Pull Ollama model**:
   ```bash
   ollama pull qwen3.5:0.8b
   ```

5. **Start Ollama** (if not running):
   ```bash
   ollama serve
   ```

### Running the Application

#### 1. Start the Backend API

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

#### 2. Start the Streamlit UI

```bash
streamlit run streamlit_app/app.py
```

The UI will open at `http://localhost:8501`

### API Endpoints

- `POST /api/upload-and-process`: Upload ZIP and start pipeline
- `GET /api/status/{job_id}`: Get job status
- `GET /api/job-data/{job_id}`: Get complete job data
- `GET /api/profile/{job_id}`: Get business profile
- `GET /api/health`: Health check

## Project Structure

```
business-digitization-agent/
├── backend/
│   ├── agents/           # Multi-agent implementations
│   │   ├── file_discovery.py
│   │   ├── media_extraction.py
│   │   ├── schema_mapping.py
│   │   ├── table_extraction.py
│   │   └── vision_agent.py
│   ├── parsers/          # Document parsers
│   ├── indexing/         # PageIndex adapter
│   ├── validation/       # Schema validation
│   ├── models/           # Pydantic schemas
│   ├── utils/            # Utilities (LLM, storage, logging)
│   ├── config.py         # Configuration
│   ├── pipeline.py       # Main pipeline orchestrator
│   └── main.py           # FastAPI application
├── streamlit_app/        # Streamlit UI
│   ├── app.py           # Main Streamlit app
│   └── README.md
├── storage/             # Generated storage directory
│   ├── uploads/
│   ├── extracted/
│   ├── profiles/
│   ├── index/
│   └── media/
├── logs/                # Application logs
├── .env                 # Environment configuration
├── .env.example         # Example environment file
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Configuration

Edit `.env` to configure:

```env
# Groq API (for GPT-OSS-120B)
GROQ_API_KEY=your_groq_api_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=openai/gpt-oss-120b

# Ollama (for Qwen 3.5 0.8B)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_VISION_MODEL=qwen3.5:0.8b
OLLAMA_API_KEY=

# Storage paths
UPLOAD_DIR=storage/uploads
EXTRACTED_DIR=storage/extracted
PROFILES_DIR=storage/profiles
INDEX_DIR=storage/index
MEDIA_DIR=storage/media

# Processing settings
MAX_ZIP_SIZE_MB=500
MAX_CONCURRENT_PARSERS=4
LOG_LEVEL=INFO
```

## Usage Example

1. **Prepare a ZIP file** containing:
   - Business registration documents (PDF)
   - Product/service catalogs (PDF, DOCX)
   - Price lists (PDF, XLSX, CSV)
   - Business images (JPG, PNG)

2. **Upload via Streamlit UI**:
   - Go to "Upload & Process" page
   - Drag and drop the ZIP file
   - Click "Start Processing"

3. **Monitor progress**:
   - Navigate to "Pipeline View"
   - See real-time progress through 8 stages
   - Expand stages to see agent inputs/outputs

4. **View results**:
   - Go to "Profile Viewer"
   - Browse Business Info, Products, Services
   - View Media Gallery with YOLO detections
   - Check Extracted Tables

## Data Schema

### Business Profile

```json
{
  "business_info": {
    "description": "...",
    "working_hours": "...",
    "location": {...},
    "contact": {...},
    "payment_methods": [...],
    "tags": [...]
  },
  "business_type": "service|product|mixed",
  "products": [...],
  "services": [{
    "name": "...",
    "description": "...",
    "category": "...",
    "pricing": {...},
    "itinerary": [...],
    "inclusions": [...],
    "exclusions": [...]
  }],
  "media": [...]
}
```

## Logging

The system provides comprehensive logging:

- **Console logs**: Real-time output in terminal
- **File logs**: Saved to `logs/app.log`
- **UI logs**: Visible in Streamlit "Logs" page

All major operations are logged with timestamps and context.

## Troubleshooting

### Qwen 3.5 Model Not Found

```bash
# Pull the model
ollama pull qwen3.5:0.8b

# Verify it's available
ollama list

# Restart Ollama if needed
ollama serve
```

### YOLO Model Loading Issues

The YOLO model downloads automatically on first use. Ensure you have internet connection.

### Backend Connection Errors

1. Check if backend is running: `curl http://localhost:8000/api/health`
2. Verify port 8000 is not in use
3. Check logs for errors

### API Key Issues

- Groq API key is optional (for GPT-OSS-120B)
- Ollama is local by default (no API key needed)
- Update `.env` with correct API keys

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

The project follows Python type hints and Pydantic models for data validation.

### Adding New Agents

1. Create agent class in `backend/agents/`
2. Add to pipeline in `backend/pipeline.py`
3. Update progress tracking

## Architecture Documentation

See the following documents for detailed architecture:

- `SYSTEM_ARCHITECTURE.md`: Complete system architecture
- `AGENT_PIPELINE.md`: Agent workflow details
- `DATA_SCHEMA.md`: Data model specifications
- `MULTIMODAL_PROCESSING.md`: Image/video processing

## License

MIT License

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.

## Support

For issues and questions:
- Check existing documentation
- Review logs for errors
- Open an issue on GitHub
