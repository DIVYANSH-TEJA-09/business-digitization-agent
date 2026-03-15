# Streamlit App for Business Digitization Agent

A comprehensive web UI for the business digitization pipeline built with Streamlit.

## Features

### 📤 Upload & Process
- Drag-and-drop ZIP file upload
- Real-time file classification summary
- One-click pipeline initiation

### 🔄 Pipeline Visualization
- Real-time progress tracking
- Visual representation of all 8 pipeline stages:
  1. File Discovery
  2. Document Parsing
  3. PageIndex Generation
  4. Table Extraction
  5. Media Extraction
  6. Vision Analysis (Qwen 3.5)
  7. Schema Mapping
  8. Validation
- Input/output inspection for each agent
- Auto-refresh during processing

### 📊 Profile Viewer
- **Business Info Tab**: Complete business details, contact, location, payment methods
- **Products Tab**: Product catalog with specifications and pricing
- **Services & Itineraries Tab**: Service details with multi-step itinerary cards
- **Media Gallery Tab**: 
  - PDF-organized images with page-level metadata
  - YOLO object detection results
  - Qwen vision analysis descriptions
- **Extracted Data Tab**: 
  - All extracted tables in DataFrame format
  - Parsed document text previews

### 📋 Logs
- Real-time processing logs
- Filter by log level (INFO, WARNING, ERROR, DEBUG)
- Clear logs functionality

## Prerequisites

1. **Backend API running** on `http://localhost:8000`
2. **Streamlit installed**: `pip install streamlit==1.31.0`
3. **Python 3.10+**

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install Streamlit separately
pip install streamlit==1.31.0
```

## Running the App

```bash
# Navigate to the project root
cd /path/to/business-digitization-agent

# Run Streamlit app
streamlit run streamlit_app/app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage Workflow

1. **Start the Backend** (in a separate terminal):
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the Streamlit App**:
   ```bash
   streamlit run streamlit_app/app.py
   ```

3. **Upload a ZIP File**:
   - Go to "Upload & Process" page
   - Drag and drop or select a ZIP file
   - Click "Start Processing"

4. **Monitor Progress**:
   - Navigate to "Pipeline View" to see real-time progress
   - Expand each stage to see agent inputs/outputs
   - Wait for completion (auto-refreshes)

5. **View Results**:
   - Go to "Profile Viewer" to see the generated business profile
   - Browse through tabs: Business Info, Products, Services, Media, Extracted Data
   - View YOLO detections and vision analysis for each image

6. **Check Logs**:
   - Go to "Logs" page to see all processing logs
   - Filter by log level as needed

## Architecture

```
┌─────────────────┐         ┌─────────────────┐
│  Streamlit App  │◄───────►│  FastAPI Backend│
│   (Port 8501)   │  HTTP   │   (Port 8000)   │
└─────────────────┘         └─────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │  Pipeline &     │
                            │  Agents         │
                            └─────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │   Groq    │   │  Ollama   │   │   YOLO    │
            │ (GPT-OSS) │   │ (Qwen 3.5)│   │  (v8n)    │
            └───────────┘   └───────────┘   └───────────┘
```

## Key Components

### `app.py`
Main Streamlit application with:
- Multi-page layout using tabs
- Session state management
- API integration
- Real-time status polling
- Log tracking

### Pages
1. **Upload & Process**: File upload and initial processing
2. **Pipeline View**: Real-time pipeline visualization
3. **Profile Viewer**: Business profile display with 5 tabs
4. **Logs**: Processing logs viewer

## API Endpoints Used

- `POST /api/upload-and-process`: Upload ZIP and start pipeline
- `GET /api/status/{job_id}`: Get job status
- `GET /api/job-data/{job_id}`: Get complete job data
- `GET /api/health`: Health check

## Configuration

Edit `.env` file to configure:
- Ollama URL (default: `http://localhost:11434/v1`)
- Ollama model (default: `qwen3.5:0.8b`)
- Groq API key and model
- Storage paths

## Troubleshooting

### Backend Not Connected
- Ensure backend is running: `uvicorn backend.main:app --reload`
- Check API health in sidebar

### Model Not Found
- Pull the Qwen model: `ollama pull qwen3.5:0.8b`
- Start Ollama: `ollama serve`

### Images Not Displaying
- Check file paths in job data
- Ensure images were extracted successfully
- Verify YOLO and vision processing completed

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Export profile as PDF/JSON
- [ ] Edit profile functionality
- [ ] Batch processing
- [ ] User authentication
- [ ] Job history persistence
