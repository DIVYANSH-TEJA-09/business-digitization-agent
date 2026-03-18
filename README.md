# Digi-Biz - Agentic Business Digitization

**Transform business documents into beautiful digital profiles using AI**

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:
```bash
GROQ_API_KEY=gsk_your_key_here
```

Get your free API key at: https://console.groq.com

### 3. Run the App

```bash
streamlit run app.py
```

Open http://localhost:8501

---

## 📋 Features

✅ **Upload ZIP** - PDFs, DOCX, images, videos  
✅ **AI Processing** - 8 AI agents extract data  
✅ **Business Profile** - Beautiful digital profile  
✅ **Edit & Export** - Modify and download as JSON  

---

## 🎯 Works For Any Business

- 🍽️ **Restaurants** - Menus, dishes, prices
- 🏪 **Retail** - Products, inventory, specs
- 💼 **Services** - Packages, pricing, policies
- 🏨 **Hotels** - Rooms, amenities, rates
- 🥾 **Travel** - Tours, itineraries, inclusions
- **And more!**

---

## 📁 Project Structure

```
digi-biz/
├── app.py                      # Streamlit app
├── backend/
│   ├── api/main.py            # FastAPI backend
│   ├── agents/                # 8 AI agents
│   ├── models/schemas.py      # Data models
│   └── utils/                 # Utilities
├── frontend/                   # Next.js (optional)
├── storage/                    # Profiles storage
├── docs/                       # Documentation
├── requirements.txt
└── .env.example
```

---

## 🔧 API Endpoints

```
POST   /api/upload              # Upload ZIP
GET    /api/status/{job_id}     # Processing status
GET    /api/profiles            # List profiles
GET    /api/profile/{job_id}    # Get profile
PUT    /api/profile/{job_id}    # Update profile
DELETE /api/profile/{job_id}    # Delete profile
POST   /api/profile/{job_id}/export  # Export JSON
```

---

## 📊 Processing Pipeline

1. **File Discovery** - Extract & classify files
2. **Document Parsing** - Extract text from PDFs/DOCX
3. **Table Extraction** - Detect & classify tables
4. **Media Extraction** - Extract images
5. **Vision Analysis** - Analyze images (Groq)
6. **Indexing** - Build search index
7. **Schema Mapping** - Extract business data (LLM)
8. **Validation** - Validate & score profile

---

## 🎨 Tech Stack

- **Frontend:** Streamlit
- **Backend:** FastAPI + Python
- **AI:** Groq API (Llama-4-Scout-17B)
- **Storage:** Local JSON files

---

## 📖 Documentation

See `docs/` folder for detailed documentation:
- `HACKATHON_QUICKSTART.md` - Quick start guide
- `CURRENT_STATUS.md` - Project status
- All technical documentation

---

## 🏆 Hackathon Ready!

**90-second demo:**
1. Upload ZIP (10 sec)
2. Watch processing (60 sec)
3. Show profile (20 sec)

---

**Built with ❤️ for any business owner!**
