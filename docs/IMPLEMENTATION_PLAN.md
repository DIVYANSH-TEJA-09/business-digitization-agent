# Digi-Biz Next.js Implementation Plan

**Date:** March 18, 2026  
**Based on:** User Requirements (Answers to 10 Questions)  
**Status:** Ready to Implement  

---

## 🎯 **USER REQUIREMENTS SUMMARY**

| # | Feature | Choice | Implementation |
|---|---------|--------|----------------|
| 1 | User Flow | **Option C** | Hybrid (Upload → Auto-redirect to Profile) |
| 2 | Processing | **Option A** | Progress bar with agent status |
| 3 | Profile Design | **Option A** | Business website + More details |
| 4 | Edit Interface | **Option B** | Separate edit page with forms |
| 5 | Data Storage | **Demo Mode** | No DB, Export functionality |
| 6 | Image Storage | **Option A** | Local file system |
| 7 | Service Details | **Option B** | Tabs (Overview | Itinerary | Info | FAQ) |
| 8 | Multiple Profiles | **Option B** | Dashboard to select profiles |
| 9 | API Endpoints | **Full CRUD** | All REST endpoints |
| 10 | Design System | **A + B** | Tailwind CSS + shadcn/ui |

---

## 🏗️ **ARCHITECTURE OVERVIEW**

### **User Flow:**
```
┌─────────────────┐
│  Landing Page   │
│  (Upload ZIP)   │
└────────┬────────┘
         │
         ↓ Upload Complete
┌─────────────────┐
│  Processing     │
│  (Real-time     │
│   Progress)     │
└────────┬────────┘
         │
         ↓ Processing Complete
┌─────────────────┐
│  Profile        │
│  Dashboard      │
│  (All Profiles) │
└────────┬────────┘
         │
         ↓ Select Profile
┌─────────────────┐
│  Profile View   │
│  (Landing Page) │
└────────┬────────┘
         │
         ↓ Click Edit
┌─────────────────┐
│  Edit Page      │
│  (Forms)        │
└─────────────────┘
```

---

## 📁 **FILE STRUCTURE**

```
digi-biz/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI server
│   │   ├── routes/
│   │   │   ├── upload.py        # POST /api/upload
│   │   │   ├── status.py        # GET /api/status/{job_id}
│   │   │   ├── profile.py       # GET/PUT/DELETE /api/profile/{job_id}
│   │   │   └── export.py        # POST /api/profile/{job_id}/export
│   │   └── middleware/
│   │       └── cors.py
│   ├── agents/                  # Existing agents (unchanged)
│   └── storage/
│       └── profiles/            # Store profiles as JSON files
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Landing page (upload)
│   │   │   ├── processing/
│   │   │   │   └── [job_id]/
│   │   │   │       └── page.tsx # Processing page
│   │   │   ├── profiles/
│   │   │   │   ├── page.tsx     # Profile dashboard
│   │   │   │   └── [job_id]/
│   │   │   │       ├── page.tsx # Profile view (landing page)
│   │   │   │       └── edit/
│   │   │   │           └── page.tsx # Edit page
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── progress.tsx
│   │   │   │   ├── tabs.tsx
│   │   │   │   └── ...
│   │   │   ├── UploadZone.tsx
│   │   │   ├── ProcessingProgress.tsx
│   │   │   ├── ProfileDashboard.tsx
│   │   │   ├── BusinessProfile.tsx
│   │   │   ├── ServiceCard.tsx
│   │   │   ├── ServiceDetails.tsx
│   │   │   ├── EditForms.tsx
│   │   │   └── ImageGallery.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   ├── utils.ts
│   │   │   └── types.ts
│   │   └── data/
│   │       └── mockData.json
│   ├── package.json
│   └── tailwind.config.ts
│
└── api.py                       # Update existing FastAPI
```

---

## 🔧 **BACKEND CHANGES**

### **1. Update api.py - Add All Endpoints**

**File:** `backend/api/main.py`

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import json
from pathlib import Path
from datetime import datetime
import uuid

app = FastAPI(title="Digi-Biz API")

# CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
PROFILES_DIR = Path("./storage/profiles")
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job status (replace with DB in production)
jobs = {}

@app.post("/api/upload")
async def upload_zip(file: UploadFile = File(...)):
    """Upload ZIP and start processing"""
    job_id = str(uuid.uuid4())
    
    # Save file
    upload_path = PROFILES_DIR / f"{job_id}_{file.filename}"
    with open(upload_path, "wb") as f:
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
    asyncio.create_task(process_job(job_id, str(upload_path)))
    
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
                    "name": profile.get("business_info", {}).get("name"),
                    "created_at": profile.get("created_at"),
                    "service_count": len(profile.get("services", []))
                })
    return {"profiles": profiles}

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
    
    # Add updated timestamp
    profile["updated_at"] = datetime.now().isoformat()
    
    # Save
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

# Background processing function
async def process_job(job_id: str, file_path: str):
    """Process job in background with progress updates"""
    from backend.agents.file_discovery import FileDiscoveryAgent, FileDiscoveryInput
    from backend.agents.document_parsing import DocumentParsingAgent, DocumentParsingInput
    from backend.agents.table_extraction import TableExtractionAgent, TableExtractionInput
    from backend.agents.media_extraction import MediaExtractionAgent, MediaExtractionInput
    from backend.agents.indexing import IndexingAgent, IndexingInput
    from backend.agents.schema_mapping_simple import SchemaMappingAgent
    from backend.models.schemas import SchemaMappingInput
    from backend.utils.storage_manager import StorageManager
    
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
        
        # Add metadata
        profile = mapping_output.profile.model_dump(mode='json')
        profile["job_id"] = job_id
        profile["created_at"] = datetime.now().isoformat()
        
        # Save profile
        profile_path = PROFILES_DIR / f"profile_{job_id}.json"
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        
        jobs[job_id]["profile_path"] = str(profile_path)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100.0
        jobs[job_id]["current_phase"] = "done"
        
        print(f"✅ Job {job_id} completed successfully")
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"❌ Job {job_id} failed: {e}")
```

---

## 🎨 **FRONTEND IMPLEMENTATION**

### **Page 1: Landing Page (Upload)**

**File:** `frontend/src/app/page.tsx`

**Features:**
- Hero section with Digi-Biz branding
- Drag-drop upload zone
- Recent profiles list
- Clean, minimal design

---

### **Page 2: Processing Page**

**File:** `frontend/src/app/processing/[job_id]/page.tsx`

**Features:**
- Progress bar (0-100%)
- Current phase display:
  - 📁 File Discovery (10%)
  - 📄 Document Parsing (30%)
  - 📊 Table Extraction (50%)
  - 🖼️ Media Extraction (70%)
  - 🔍 Indexing (85%)
  - 🤖 Schema Mapping (95%)
  - ✅ Complete (100%)
- Auto-redirect to profile on completion
- Cannot navigate away (modal-like)

---

### **Page 3: Profile Dashboard**

**File:** `frontend/src/app/profiles/page.tsx`

**Features:**
- Grid of all profiles
- Each card shows:
  - Business name
  - Service count
  - Created date
  - Preview image
- "Create New" button
- Search/filter

---

### **Page 4: Profile View (Landing Page)**

**File:** `frontend/src/app/profiles/[job_id]/page.tsx`

**Features:**
- **Hero Section:**
  - Business name
  - Category badge
  - Description
  - Contact info (phone, email, website)
  - Location
  - Hero image (if available)

- **Services Grid:**
  - Service cards with image, name, price, duration
  - Click to view details

- **Service Details Modal/Page:**
  - **Tabs:**
    - Overview (description, category)
    - Itinerary (day-by-day)
    - Info (inclusions, exclusions, what to carry)
    - FAQ (questions & answers)
    - Policy (cancellation, payment)

- **Image Gallery:**
  - Grid of all images
  - Lightbox view

- **Actions:**
  - Edit Profile button
  - Export JSON button
  - Delete Profile button

---

### **Page 5: Edit Page**

**File:** `frontend/src/app/profiles/[job_id]/edit/page.tsx`

**Features:**
- **Business Info Form:**
  - Name, description, category
  - Contact (phone, email, website)
  - Location
  - Hero image upload

- **Services Editor:**
  - List of all services
  - Add/Remove services
  - Edit each service:
    - Name, description, category
    - Pricing (base price, currency, price type)
    - Details (duration, difficulty, best time)
    - Itinerary (add/remove days)
    - Inclusions/Exclusions (tag input)
    - FAQs (Q&A pairs)
    - Images upload

- **Actions:**
  - Save button
  - Cancel button (back to profile)
  - Auto-save draft (optional)

---

## 🎯 **COMPONENTS NEEDED**

### **shadcn/ui Components:**
```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add progress
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add form
npx shadcn-ui@latest add input
npx shadcn-ui@latest add textarea
npx shadcn-ui@latest add label
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add avatar
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add toast
```

### **Custom Components:**
1. `UploadZone.tsx` - Drag-drop upload
2. `ProcessingProgress.tsx` - Progress bar with phases
3. `ProfileDashboard.tsx` - Profile grid
4. `BusinessProfile.tsx` - Profile display
5. `ServiceCard.tsx` - Service card
6. `ServiceDetails.tsx` - Service details with tabs
7. `EditForms.tsx` - Edit forms
8. `ImageGallery.tsx` - Image gallery
9. `ItineraryBuilder.tsx` - Itinerary editor
10. `TagInput.tsx` - For inclusions/exclusions

---

## 📋 **IMPLEMENTATION CHECKLIST**

### **Phase 1: Backend API (8-10 hours)**
- [ ] Update api.py with all endpoints
- [ ] Add profile storage (JSON files)
- [ ] Add background processing
- [ ] Add progress tracking
- [ ] Test all endpoints with Postman
- [ ] Add error handling
- [ ] Add CORS for localhost:3000

### **Phase 2: Frontend Setup (4-6 hours)**
- [ ] Install shadcn/ui components
- [ ] Setup Tailwind config
- [ ] Create API client (lib/api.ts)
- [ ] Create types (lib/types.ts)
- [ ] Setup routing

### **Phase 3: Core Pages (10-12 hours)**
- [ ] Landing page (upload)
- [ ] Processing page
- [ ] Profile dashboard
- [ ] Profile view page
- [ ] Edit page
- [ ] All components

### **Phase 4: Integration (6-8 hours)**
- [ ] Connect upload to API
- [ ] Connect processing status polling
- [ ] Connect profile loading
- [ ] Connect edit forms
- [ ] Connect export
- [ ] Connect delete
- [ ] Error handling
- [ ] Loading states

### **Phase 5: Polish (4-6 hours)**
- [ ] Responsive design
- [ ] Animations
- [ ] Toast notifications
- [ ] Better error messages
- [ ] Performance optimization
- [ ] Test with real data

**Total: 32-42 hours**

---

## 🚀 **NEXT STEPS**

1. **Confirm this plan** matches your vision
2. **I'll start implementing** Phase 1 (Backend API)
3. **Test backend** with Postman
4. **Build frontend** incrementally
5. **Test together**

---

## ❓ **FINAL QUESTIONS BEFORE I START:**

1. **Should I proceed with this exact plan?**
2. **Any specific design preferences?** (colors, layout, etc.)
3. **Should I keep the existing mockData.json** as fallback?
4. **Any specific trek companies** to reference for design?

---

**Ready to start building! Just say "GO" and I'll begin with Phase 1!** 🚀
