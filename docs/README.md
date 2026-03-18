# Digi-Biz 📄

**Agentic Business Digitization Framework**

Transform unstructured business documents into structured digital profiles using AI agents.

[![Tests](https://img.shields.io/badge/tests-66%20passed-green)]()
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Groq API

Get your free API key at https://console.groq.com

Create `.env` file:
```bash
GROQ_API_KEY=gsk_your_key_here
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

### 3. Run the App

```bash
streamlit run app.py
```

Open http://localhost:8501

---

## ✨ Features

✅ **Multi-Agent Pipeline** - 6 specialized agents  
✅ **Groq Vision** - Image analysis with Llama-4-Scout (17B)  
✅ **Vectorless RAG** - Fast document retrieval  
✅ **Production-Ready** - Error handling, validation, logging  
✅ **Interactive UI** - Streamlit web interface  

---

## 📊 What It Does

1. **Upload ZIP** with business documents
2. **AI Agents Process**:
   - File Discovery → Classify files
   - Document Parsing → Extract text/tables
   - Table Extraction → Detect & classify
   - Media Extraction → Extract images
   - Vision Analysis → Describe images (Groq)
   - Indexing → Build search index (RAG)
3. **View Results** in interactive UI

---

## 🎯 Example Use Cases

### Restaurant Digitization
- Upload: Menu PDFs, food photos, price lists
- Output: Digital menu with prices, food descriptions, categories

### Travel Agency
- Upload: Tour brochures, itinerary PDFs, destination photos
- Output: Tour packages with itineraries, pricing, descriptions

### Retail Store
- Upload: Product catalogs, inventory spreadsheets, product photos
- Output: Product inventory with descriptions, prices, categories

---

## 📁 Project Structure

```
digi-biz/
├── backend/agents/        # 6 AI agents
├── backend/models/        # Data schemas
├── backend/utils/         # Utilities
├── tests/agents/          # Test suites
├── app.py                 # Streamlit app
├── requirements.txt       # Dependencies
└── docs/                  # Documentation
```

---

## 🧪 Testing

All agents are thoroughly tested:

```bash
# Run all tests
pytest tests/ -v

# Test coverage
pytest tests/ --cov=backend
```

**Test Results:** 66/66 tests passing ✅

---

## 📖 Documentation

- **[Full Documentation](docs/DOCUMENTATION.md)** - Complete guide
- **[Agent Details](docs/AGENT_PIPELINE.md)** - Agent specifications
- **[Streamlit App](docs/STREAMLIT_APP.md)** - App usage guide

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Groq API (required)
GROQ_API_KEY=gsk_xxxxx
GROQ_MODEL=gpt-oss-120b
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct

# Optional: Ollama fallback
OLLAMA_HOST=http://localhost:11434

# Processing limits
MAX_FILE_SIZE=524288000    # 500MB
MAX_FILES_PER_ZIP=100
```

---

## 🎓 Agents

| # | Agent | Purpose | Status |
|---|-------|---------|--------|
| 1 | File Discovery | Extract & classify ZIP files | ✅ |
| 2 | Document Parsing | Parse PDF/DOCX | ✅ |
| 3 | Table Extraction | Detect & classify tables | ✅ |
| 4 | Media Extraction | Extract images/videos | ✅ |
| 5 | Vision Agent | Analyze images (Groq) | ✅ |
| 6 | Indexing Agent | Build RAG index | ✅ |

---

## 📊 Performance

| Task | Time |
|------|------|
| File Discovery (10 files) | ~1-2s |
| Document Parsing (10 pages) | ~0.5s |
| Table Extraction (5 tables) | ~0.5s |
| Vision Analysis (1 image) | ~2s |
| **Total (typical folder)** | **<2 min** |

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Pydantic, asyncio
- **Document Parsing:** pdfplumber, python-docx, openpyxl
- **Vision AI:** Groq API (Llama-4-Scout-17B)
- **Frontend:** Streamlit
- **Testing:** pytest

---

## 📝 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Add tests
4. Submit PR

---

## 📞 Support

- **Issues:** GitHub Issues
- **Docs:** [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)

---

**Made with ❤️ using AI Agents**
