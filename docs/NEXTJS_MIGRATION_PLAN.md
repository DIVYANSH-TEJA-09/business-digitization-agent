# Digi-Biz Next.js Migration - Issues & Requirements

**Date:** March 18, 2026  
**Project:** Agentic Business Digitization Framework  
**Migration:** Streamlit → Next.js  
**Priority:** CRITICAL  

---

## 🎯 **NEW UX FLOW REQUIREMENT**

### **Current Flow (Streamlit):**
```
Upload Tab → Processing Tab → Results Tab → Vision Tab → Index Tab → Profile Tab
(All tabs visible from start, confusing navigation)
```

### **Required Flow (Next.js):**
```
1. Landing Page (Upload ZIP)
        ↓
2. Processing Page (Real-time progress)
        ↓
3. Generated Landing Page (Business Profile)
        ↓
4. Edit Options (Modal/Separate Page)
```

---

## 📊 **CURRENT ISSUES WITH STREAMLIT APP**

### **1. Navigation Issues** ❌

**Problem:**
- All 6 tabs visible from the beginning
- Users can access Results/Profile before processing
- Confusing user flow
- No clear progression

**Current Tabs:**
```
📤 Upload | ⚙️ Processing | 📊 Results | 🖼️ Vision | 🌳 Index | 📄 Profile
```

**User Confusion:**
- "Can I view results before uploading?"
- "Which tab should I click first?"
- "Where do I edit the profile?"

---

### **2. State Management Issues** ❌

**Problem:**
- Streamlit session_state is fragile
- State lost on page refresh
- No persistence between sessions
- Cannot share profile URLs

**Current State Storage:**
```python
st.session_state.processing_complete = False
st.session_state.business_profile = None
st.session_state.page_index_dict = None
```

**Issues:**
- ❌ No database storage
- ❌ No job persistence
- ❌ No URL sharing
- ❌ No resume capability

---

### **3. Processing UX Issues** ❌

**Problem:**
- Processing happens in same page
- No dedicated processing screen
- User can navigate away during processing
- No progress persistence

**Current Flow:**
```
User uploads ZIP → Clicks "Process" → Watches progress bar → Done
(All in same tab, can accidentally navigate away)
```

**Required Flow:**
```
User uploads ZIP → Redirects to /processing/[job_id] → Auto-redirects to /profile/[job_id]
(Dedicated pages, cannot navigate away)
```

---

### **4. Profile Display Issues** ❌

**Problem:**
- Profile shown in tab format
- Not a proper landing page
- Doesn't look like a business website
- No customization options

**Current Display:**
```
Tab with sections:
- Business Information
- Services (expandable)
- Validation Results
```

**Required Display:**
```
Proper Landing Page:
- Hero section with business name
- Services grid with cards
- Image gallery
- Contact information
- Edit button (floating/fixed)
```

---

### **5. Edit Functionality Issues** ❌

**Problem:**
- No edit UI currently
- Cannot modify extracted data
- Cannot add missing services
- Cannot upload additional images

**Current State:**
```
Profile is read-only
No edit buttons
No forms for modification
```

**Required:**
```
"Edit Profile" button → Opens edit modal/page
- Edit business info
- Edit services (add/remove/modify)
- Upload more images
- Save changes
```

---

### **6. Backend Integration Issues** ❌

**Problem:**
- Streamlit app is monolithic
- No REST API
- Cannot be consumed by Next.js frontend
- All processing happens in browser session

**Current Architecture:**
```
Streamlit Frontend + Python Backend (tightly coupled)
```

**Required Architecture:**
```
Next.js Frontend ←REST API→ FastAPI Backend
                     ↓
                Python Agents
```

---

## 🏗️ **REQUIRED NEXT.JS ARCHITECTURE**

### **Frontend Structure:**

```
app/
├── page.tsx                    # Landing page (upload ZIP)
├── processing/
│   └── [job_id]/
│       └── page.tsx            # Processing page with progress
├── profile/
│   └── [job_id]/
│       ├── page.tsx            # Generated landing page
│       └── edit/
│           └── page.tsx        # Edit profile page
├── api/
│   ├── upload/
│   │   └── route.ts            # Handle file upload
│   ├── status/
│   │   └── [job_id]/
│   │       └── route.ts        # Get processing status
│   └── profile/
│       └── [job_id]/
│           └── route.ts        # Get profile data
└── components/
    ├── UploadZone.tsx          # Drag-drop upload
    ├── ProcessingProgress.tsx  # Progress bars
    ├── BusinessProfile.tsx     # Profile display
    ├── ServiceCard.tsx         # Service display
    ├── EditModal.tsx           # Edit forms
    └── ImageGallery.tsx        # Image gallery
```

---

### **Backend API Structure:**

```
backend/
├── api/
│   ├── main.py                 # FastAPI app
│   ├── routes/
│   │   ├── upload.py           # POST /api/upload
│   │   ├── status.py           # GET /api/status/{job_id}
│   │   └── profile.py          # GET /api/profile/{job_id}
│   └── middleware/
│       └── cors.py             # CORS configuration
├── agents/                     # Existing agents (unchanged)
│   ├── file_discovery.py
│   ├── document_parsing.py
│   ├── ...
├── storage/
│   ├── database.py             # SQLite/PostgreSQL
│   └── models.py               # DB models
└── utils/
    ├── storage_manager.py
    └── logger.py
```

---

## 🔧 **BACKEND CHANGES REQUIRED**

### **1. Create FastAPI Server**

**File:** `backend/api/main.py`

```python
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

app = FastAPI()

# CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job storage (replace with database)
jobs = {}

@app.post("/api/upload")
async def upload_zip(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    
    # Save file
    file_path = f"./storage/uploads/{job_id}_{file.filename}"
    
    # Start processing in background
    asyncio.create_task(process_job(job_id, file_path))
    
    return {"job_id": job_id, "status": "processing"}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "current_phase": job["current_phase"]
    }

@app.get("/api/profile/{job_id}")
async def get_profile(job_id: str):
    # Return complete business profile
    return jobs.get(job_id, {}).get("profile")
```

---

### **2. Database Integration**

**File:** `backend/storage/database.py`

```python
import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('digi_biz.db')
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                progress REAL,
                current_phase TEXT,
                created_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                profile_id TEXT PRIMARY KEY,
                job_id TEXT,
                business_type TEXT,
                business_info JSON,
                services JSON,
                created_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def create_job(self, job_id: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?)',
            (job_id, 'processing', 0.0, 'upload', datetime.now(), None)
        )
        self.conn.commit()
    
    def update_job_status(self, job_id: str, status: str, progress: float, phase: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE jobs SET status=?, progress=?, current_phase=? WHERE job_id=?',
            (status, progress, phase, job_id)
        )
        self.conn.commit()
    
    def save_profile(self, profile_id: str, job_id: str, profile: dict):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO profiles VALUES (?, ?, ?, ?, ?, ?)',
            (profile_id, job_id, profile['business_type'], 
             json.dumps(profile['business_info']), json.dumps(profile['services']),
             datetime.now())
        )
        self.conn.commit()
```

---

### **3. Background Processing**

**File:** `backend/api/processing.py`

```python
import asyncio
from backend.agents.file_discovery import FileDiscoveryAgent
from backend.agents.document_parsing import DocumentParsingAgent
# ... import all agents

async def process_job(job_id: str, file_path: str):
    """Process job in background with progress updates"""
    
    db = Database()
    db.update_job_status(job_id, 'processing', 0.0, 'upload')
    
    try:
        # Step 1: File Discovery (10%)
        discovery_agent = FileDiscoveryAgent()
        discovery_output = await asyncio.to_thread(
            discovery_agent.discover,
            FileDiscoveryInput(zip_file_path=file_path, job_id=job_id)
        )
        db.update_job_status(job_id, 'processing', 10.0, 'discovery')
        
        # Step 2: Document Parsing (30%)
        parsing_agent = DocumentParsingAgent()
        parsing_output = await asyncio.to_thread(
            parsing_agent.parse,
            DocumentParsingInput(documents=discovery_output.documents, job_id=job_id)
        )
        db.update_job_status(job_id, 'processing', 30.0, 'parsing')
        
        # Step 3: Table Extraction (50%)
        # ... continue for all agents
        
        # Step 7: Save Profile (100%)
        db.update_job_status(job_id, 'completed', 100.0, 'done')
        db.save_profile(profile_id, job_id, profile)
        
    except Exception as e:
        db.update_job_status(job_id, 'failed', 0.0, 'error')
        logger.error(f"Job {job_id} failed: {e}")
```

---

## 🎨 **FRONTEND PAGES**

### **1. Landing Page (Upload)**

**File:** `app/page.tsx`

```tsx
'use client'

import { useState } from 'react'
import { UploadZone } from '@/components/UploadZone'
import { useRouter } from 'next/navigation'

export default function HomePage() {
  const router = useRouter()
  const [uploading, setUploading] = useState(false)
  
  const handleUpload = async (file: File) => {
    setUploading(true)
    
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    })
    
    const { job_id } = await response.json()
    
    // Redirect to processing page
    router.push(`/processing/${job_id}`)
  }
  
  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <h1 className="text-5xl font-bold text-center mb-4">
          📄 Digi-Biz
        </h1>
        <p className="text-xl text-center text-gray-600 mb-12">
          Agentic Business Digitization Framework
        </p>
        
        <UploadZone onUpload={handleUpload} disabled={uploading} />
        
        {uploading && (
          <div className="text-center mt-8">
            <p className="text-lg">Uploading...</p>
          </div>
        )}
      </div>
    </main>
  )
}
```

---

### **2. Processing Page**

**File:** `app/processing/[job_id]/page.tsx`

```tsx
'use client'

import { useEffect, useState } from 'react'
import { ProcessingProgress } from '@/components/ProcessingProgress'
import { useRouter, useParams } from 'next/navigation'

export default function ProcessingPage() {
  const router = useRouter()
  const params = useParams()
  const [status, setStatus] = useState({
    status: 'processing',
    progress: 0,
    current_phase: 'upload'
  })
  
  useEffect(() => {
    const pollStatus = async () => {
      const response = await fetch(`/api/status/${params.job_id}`)
      const data = await response.json()
      
      setStatus(data)
      
      if (data.status === 'completed') {
        // Redirect to profile page
        router.push(`/profile/${params.job_id}`)
      } else if (data.status === 'failed') {
        // Show error
        router.push(`/error?job_id=${params.job_id}`)
      }
    }
    
    // Poll every 2 seconds
    const interval = setInterval(pollStatus, 2000)
    return () => clearInterval(interval)
  }, [params.job_id, router])
  
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-16">
        <h1 className="text-3xl font-bold mb-8">Processing Your Documents</h1>
        
        <ProcessingProgress 
          status={status.status}
          progress={status.progress}
          currentPhase={status.current_phase}
        />
        
        <div className="mt-8 text-center">
          <p className="text-gray-600">
            This may take 2-3 minutes. Please don't close this page.
          </p>
        </div>
      </div>
    </main>
  )
}
```

---

### **3. Profile Page (Generated Landing Page)**

**File:** `app/profile/[job_id]/page.tsx`

```tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { BusinessProfile } from '@/components/BusinessProfile'
import { EditButton } from '@/components/EditButton'

export default function ProfilePage() {
  const params = useParams()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchProfile = async () => {
      const response = await fetch(`/api/profile/${params.job_id}`)
      const data = await response.json()
      setProfile(data)
      setLoading(false)
    }
    
    fetchProfile()
  }, [params.job_id])
  
  if (loading) {
    return <div>Loading...</div>
  }
  
  return (
    <main className="min-h-screen bg-white">
      {/* Floating Edit Button */}
      <EditButton jobId={params.job_id} />
      
      {/* Business Profile Display */}
      <BusinessProfile profile={profile} />
    </main>
  )
}
```

---

### **4. Edit Page**

**File:** `app/profile/[job_id]/edit/page.tsx`

```tsx
'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { BusinessInfoForm } from '@/components/BusinessInfoForm'
import { ServiceEditor } from '@/components/ServiceEditor'

export default function EditProfilePage() {
  const params = useParams()
  const router = useRouter()
  const [profile, setProfile] = useState(null)
  const [saving, setSaving] = useState(false)
  
  const handleSave = async (updatedProfile) => {
    setSaving(true)
    
    await fetch(`/api/profile/${params.job_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedProfile)
    })
    
    setSaving(false)
    router.push(`/profile/${params.job_id}`)
  }
  
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Edit Business Profile</h1>
        
        <BusinessInfoForm 
          initialData={profile?.business_info}
          onSave={handleSave}
        />
        
        <ServiceEditor
          services={profile?.services}
          onSave={handleSave}
        />
        
        {saving && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <p className="text-white text-xl">Saving...</p>
          </div>
        )}
      </div>
    </main>
  )
}
```

---

## 📋 **MIGRATION CHECKLIST**

### **Phase 1: Backend API** ⏳
- [ ] Create FastAPI server
- [ ] Add CORS middleware
- [ ] Create upload endpoint
- [ ] Create status endpoint
- [ ] Create profile endpoint
- [ ] Add database integration
- [ ] Add background processing
- [ ] Test all endpoints

### **Phase 2: Frontend Pages** ⏳
- [ ] Create Next.js project
- [ ] Create landing page (upload)
- [ ] Create processing page
- [ ] Create profile page
- [ ] Create edit page
- [ ] Add all components
- [ ] Add styling (Tailwind)

### **Phase 3: Integration** ⏳
- [ ] Connect frontend to backend
- [ ] Test upload flow
- [ ] Test processing flow
- [ ] Test profile display
- [ ] Test edit functionality
- [ ] Add error handling
- [ ] Add loading states

### **Phase 4: Polish** ⏳
- [ ] Add animations
- [ ] Add responsive design
- [ ] Add SEO meta tags
- [ ] Add favicon
- [ ] Test on mobile
- [ ] Performance optimization
- [ ] Deploy

---

## 🎯 **PRIORITY ORDER**

1. **Backend API** (FastAPI) - Foundation
2. **Landing Page** (Upload) - User entry point
3. **Processing Page** - Real-time progress
4. **Profile Page** - Final output
5. **Edit Page** - Manual corrections
6. **Database** - Persistence
7. **Polish** - UI/UX improvements

---

## ⏱️ **ESTIMATED TIME**

| Phase | Tasks | Time |
|-------|-------|------|
| Backend API | 7 tasks | 8-10 hours |
| Frontend Pages | 5 tasks | 10-12 hours |
| Integration | 7 tasks | 6-8 hours |
| Polish | 7 tasks | 4-6 hours |
| **Total** | **26 tasks** | **28-36 hours** |

---

## 🚀 **NEXT STEPS**

1. **Read this document** thoroughly
2. **Decide on approach:**
   - Build from scratch?
   - Use existing template?
3. **Start with Backend API** (FastAPI)
4. **Then build Frontend** (Next.js)
5. **Test incrementally**

---

**Status:** 📝 **PLANNING COMPLETE**  
**Next Action:** Start Backend API implementation  
**ETA:** 28-36 hours for complete migration  

---

**Made with ❤️ - Let's build this!** 🚀
