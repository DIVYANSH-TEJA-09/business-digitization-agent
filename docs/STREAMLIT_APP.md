# 📄 Digi-Biz Streamlit App

## Quick Start

### 1. Install Dependencies

```bash
pip install streamlit
```

### 2. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## Features

### 📤 Upload Tab
- Upload ZIP files containing business documents
- Supports PDF, DOCX, XLSX, images, videos
- Shows file size and job ID

### ⚙️ Processing Tab
- **Real-time progress** through 5 agents:
  1. File Discovery Agent
  2. Document Parsing Agent
  3. Table Extraction Agent
  4. Media Extraction Agent
  5. Vision Agent (Qwen3.5:0.8B)
- Live status updates
- Error handling with graceful degradation

### 📊 Results Tab
- File discovery summary (documents, images, videos)
- Document parsing results (pages, text preview)
- Table extraction results (count, types)
- Expandable details for each section

### 🖼️ Vision Analysis Tab
- Image gallery with analysis results
- Category classification (product, service, food, etc.)
- Confidence scores
- Tags and descriptions
- Product/service detection
- Association suggestions

---

## Sidebar Features

- **Model Status**: Shows Ollama server and Qwen model availability
- **Agent Cards**: Quick reference for all 5 agents
- **Reset Button**: Clear all session data and start fresh

---

## Requirements

### System Requirements
- Python 3.10+
- Ollama installed and running
- Qwen3.5:0.8b model pulled

### Python Packages
```bash
pip install -r requirements.txt
```

---

## Usage Example

1. **Prepare ZIP file** with business documents:
   - Restaurant menu PDFs
   - Product catalogs
   - Service brochures
   - Business cards
   - Product photos

2. **Upload** the ZIP file in the "Upload" tab

3. **Click "Start Processing"** - watch real-time progress

4. **View Results** in "Results" and "Vision Analysis" tabs

---

## Troubleshooting

### Ollama Not Running
```
Error: Ollama Server Not Running
```
**Solution:** Start Ollama server
```bash
ollama serve
```

### Qwen Model Not Found
```
Error: Qwen3.5:0.8B Not Available
```
**Solution:** Pull the model
```bash
ollama pull qwen3.5:0.8b
```

### Processing Timeout
If processing takes too long:
- Reduce number of images in ZIP
- Vision analysis processes first 3 images by default
- Increase timeout in `vision_agent.py`

---

## Screenshots

The app provides:
- ✅ Clean, modern UI with custom styling
- ✅ Progress bars and status indicators
- ✅ Interactive expandable sections
- ✅ Image gallery with analysis overlays
- ✅ Real-time agent status updates

---

## Development

### Run in Development Mode

```bash
streamlit run app.py --server.headless=true --server.port=8501
```

### Enable Debug Logging

Add to `app.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Streamlit Frontend              │
│  - Upload component                     │
│  - Progress tracking                    │
│  - Results display                      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Agent Pipeline                  │
│  1. File Discovery Agent                │
│  2. Document Parsing Agent              │
│  3. Table Extraction Agent              │
│  4. Media Extraction Agent              │
│  5. Vision Agent (Qwen3.5:0.8B)         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Ollama (Qwen Vision)            │
│  - Image analysis                       │
│  - Category classification              │
│  - Tag generation                       │
└─────────────────────────────────────────┘
```

---

## Next Steps

After the demo:
1. Review extracted data
2. Export results (JSON export coming soon)
3. Edit/refine results (editing UI in development)
4. Integrate with downstream systems

---

**Enjoy using Digi-Biz!** 🚀
