# Digi-Biz - Clean Project Structure

## ✅ CLEANED UP!

All documentation moved to `docs/`, unused files removed.

---

## 📁 Final Structure

```
digi-biz/
├── 📄 Core Files
│   ├── app.py                      # Streamlit app (MAIN)
│   ├── api.py                      # FastAPI backend (alternative)
│   ├── requirements.txt            # Python dependencies
│   ├── .env                        # Environment variables
│   └── .env.example                # Example env file
│
├── 🤖 Backend (Python)
│   ├── backend/
│   │   ├── api/main.py            # FastAPI server
│   │   ├── agents/                # 8 AI agents
│   │   │   ├── file_discovery.py
│   │   │   ├── document_parsing.py
│   │   │   ├── table_extraction.py
│   │   │   ├── media_extraction.py
│   │   │   ├── vision_agent.py
│   │   │   ├── indexing.py
│   │   │   ├── schema_mapping_v2.py  # NEW - Generic extraction
│   │   │   └── validation_agent.py
│   │   ├── models/
│   │   │   ├── schemas.py         # Data models
│   │   │   └── enums.py
│   │   ├── parsers/               # Document parsers
│   │   └── utils/                 # Utilities
│
├── 🌐 Frontend (Next.js - Optional)
│   ├── frontend/
│   │   ├── src/app/              # Next.js pages
│   │   ├── src/lib/api.ts        # API client
│   │   └── package.json
│
├── 📚 Documentation
│   ├── docs/                     # ALL .md files moved here
│   │   ├── README.md             # Project overview
│   │   ├── HACKATHON_QUICKSTART.md
│   │   ├── CURRENT_STATUS.md
│   │   └── [20+ more docs]
│   └── README.md                 # Main README (root)
│
├── 💾 Storage
│   └── storage/
│       ├── profiles/             # Generated profiles (JSON)
│       └── extracted/            # Extracted media
│
└── 🧪 Tests
    └── tests/
        └── agents/               # Agent tests
```

---

## 🎯 What's Kept

### **Essential Files:**
- ✅ `app.py` - Streamlit app (primary interface)
- ✅ `backend/` - All Python backend code
- ✅ `requirements.txt` - Dependencies
- ✅ `.env` - Configuration

### **Documentation:**
- ✅ All `.md` files → `docs/` folder
- ✅ `README.md` - Clean, hackathon-ready

### **Optional:**
- ⚠️ `frontend/` - Next.js (can be removed if not using)
- ⚠️ `tests/` - Unit tests (keep for development)

---

## 🗑️ What Was Removed

- ❌ `test_*.py` files (root level)
- ❌ `debug_*.py` files
- ❌ `resume.py`
- ❌ Old agent versions (`schema_mapping.py`, `schema_mapping_simple.py`)
- ❌ Duplicate/unused files

---

## 🚀 Quick Start (Clean)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your Groq API key

# 3. Run
streamlit run app.py
```

---

## 📊 File Count

| Category | Count |
|----------|-------|
| **Core Files** | 5 |
| **Backend Agents** | 8 |
| **Backend Utils** | 6 |
| **Documentation** | 26 (in docs/) |
| **Tests** | 5 |
| **Total Python Files** | ~30 |

---

**Clean, organized, and hackathon-ready!** 🎉
