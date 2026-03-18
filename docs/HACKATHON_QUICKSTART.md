# Digi-Biz Hackathon MVP - Quick Start Guide

**Date:** March 18, 2026  
**Status:** Ready to Test  

---

## 🚀 **QUICK START**

### **1. Install Dependencies**

```bash
# Backend
cd D:\Viswam_Projects\digi-biz
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### **2. Start Backend API**

```bash
# In digi-biz directory (NOT frontend)
python backend/api/main.py
```

API will run at: **http://127.0.0.1:8000**

### **3. Start Frontend**

```bash
# In frontend directory
npm run dev
```

Frontend will run at: **http://localhost:3000**

---

## 📋 **TESTING FLOW**

### **Step 1: Upload ZIP**
1. Open http://localhost:3000
2. Click "Upload Your Business ZIP" or drag-drop
3. Select your ZIP file (must contain business documents)

### **Step 2: Watch Processing**
- Automatically redirects to `/processing/[job_id]`
- Shows real-time progress (0-100%)
- 6 phases: File Discovery → Document Parsing → Tables → Media → Indexing → Schema Mapping

### **Step 3: View Profile**
- Auto-redirects to `/profile/[job_id]` when complete
- Shows business information
- Shows services/products grid

### **Step 4: Edit (Optional)**
- Click "Edit" button
- Modify business info
- Click "Save"

### **Step 5: Export**
- Click "Export" to download JSON
- Or use Delete button to remove

---

## 🎨 **FEATURES**

### **Working:**
✅ Upload ZIP file  
✅ Real-time processing progress  
✅ Profile display (works for ANY business)  
✅ Edit business information  
✅ Export to JSON  
✅ Delete profile  
✅ Cream/brown theme  
✅ Responsive design  

### **Simplified for Hackathon:**
⚠️ Service editing (basic - via JSON only)  
⚠️ No image upload in edit (shows placeholder)  
⚠️ No multiple profiles dashboard  
⚠️ No user authentication  

---

## 🎯 **TEST DATA**

### **Use Your Trek ZIP:**
- Contains: Bali Pass, Bhrigu Lake, etc.
- Should extract: 6-7 treks with prices

### **Or Test With Other Business:**
- **Restaurant:** Menu PDFs, food photos
- **Retail:** Product lists, price lists
- **Services:** Service descriptions, pricing

---

## 🐛 **TROUBLESHOOTING**

### **Backend won't start:**
```bash
# Check if port 8000 is free
netstat -ano | findstr :8000

# Kill process if needed
taskkill /F /PID <PID>
```

### **Frontend errors:**
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### **Upload fails:**
- Make sure file is .zip
- Check backend is running
- Check CORS in browser console

### **Processing stuck:**
- Check backend terminal for errors
- May take 2-3 minutes for large ZIPs
- Refresh page and try again

---

## 📊 **API ENDPOINTS**

```
POST   /api/upload              # Upload ZIP
GET    /api/status/{job_id}     # Get processing status
GET    /api/profiles            # List all profiles
GET    /api/profile/{job_id}    # Get profile
PUT    /api/profile/{job_id}    # Update profile
DELETE /api/profile/{job_id}    # Delete profile
POST   /api/profile/{job_id}/export  # Export JSON
```

---

## 🎨 **COLOR SCHEME**

- **Background:** Cream (#FDFBF7)
- **Primary:** Terracotta (#C4795D)
- **Secondary:** Sage Green (#8FA895)
- **Text:** Dark Brown (#3D2B1F)

Works for ANY business type!

---

## ✅ **CHECKLIST**

Before presenting:
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Test ZIP file ready
- [ ] Test full flow: Upload → Processing → Profile → Edit → Export
- [ ] Check responsive design (mobile view)
- [ ] Prepare demo script

---

## 🎤 **DEMO SCRIPT**

1. **Show Landing Page** (5 sec)
   - "Welcome to Digi-Biz"
   - "Upload your business documents"

2. **Upload ZIP** (10 sec)
   - "Select ZIP with business docs"
   - "AI will process automatically"

3. **Show Processing** (15 sec)
   - "Real-time progress tracking"
   - "6 AI agents working"

4. **Show Profile** (30 sec)
   - "Beautiful digital profile"
   - "Works for any business"
   - "Services, contact info, everything"

5. **Show Edit** (20 sec)
   - "Easy to edit"
   - "Update business info"

6. **Show Export** (10 sec)
   - "Export as JSON"
   - "Use anywhere"

**Total: 90 seconds**

---

## 🏆 **HACKATHON SELLING POINTS**

1. **Universal** - Works for ANY business (not just treks)
2. **Fast** - 2-3 minutes from ZIP to profile
3. **Beautiful** - Cream/brown theme, professional design
4. **Easy** - Upload, wait, done
5. **AI-Powered** - 8 AI agents working together
6. **Exportable** - JSON format, use anywhere

---

**Ready to build and test!** 🚀
