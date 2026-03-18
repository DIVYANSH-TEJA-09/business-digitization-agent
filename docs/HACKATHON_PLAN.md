# Digi-Biz Hackathon Implementation

**Date:** March 18, 2026  
**Scope:** Hackathon MVP (Minimum Viable Product)  
**Target:** Any business owner/vendor (not just treks)  

---

## 🎯 **SCOPE (Hackathon MVP)**

### **What We'll Build:**
✅ Single-page upload → Processing → Profile flow  
✅ Progress tracking during processing  
✅ Profile display (works for ANY business type)  
✅ Edit functionality (simple forms)  
✅ Export to JSON  
✅ Local storage (JSON files, no database)  
✅ Works for: Restaurants, Shops, Services, Treks, ANY business  

### **What We'll Skip:**
❌ User authentication  
❌ Multiple profiles dashboard  
❌ Complex image galleries  
❌ Service detail tabs (keep it simple)  
❌ Delete functionality  

---

## 🎨 **DESIGN UPDATES**

### **Color Scheme:**
- **Background:** Cream (`#FDFBF7` or `bg-stone-50`)
- **Primary:** Warm brown/terracotta (`#C4795D` or similar)
- **Accent:** Sage green (`#8FA895`)
- **Text:** Dark brown (`#3D2B1F`)

### **Universal Design:**
- NO trek-specific imagery
- Generic business icons
- Works for:
  - 🍽️ Restaurants (menu, location, hours)
  - 🏪 Retail shops (products, pricing)
  - 💼 Services (consulting, repairs, etc.)
  - 🥾 Adventure companies (treks, tours)
  - 🏨 Hotels/B&Bs
  - ANY small business!

---

## 📁 **FILES TO UPDATE**

### **Backend (api.py):**
- ✅ Already has all endpoints
- Just need to verify it works
- Store profiles as JSON files

### **Frontend:**
1. **`app/page.tsx`** - Upload page (update colors)
2. **`app/processing/[job_id]/page.tsx`** - Processing page
3. **`app/profile/[job_id]/page.tsx`** - Profile display (GENERIC)
4. **`app/profile/[job_id]/edit/page.tsx`** - Edit page
5. **Components** - Simple, reusable

---

## 🚀 **IMPLEMENTATION**

Let me start building now! I'll:

1. **Update backend** (verify endpoints work)
2. **Create frontend pages** (upload, processing, profile, edit)
3. **Style with cream/brown theme**
4. **Make it generic** (works for any business)
5. **Test end-to-end**

**ETA:** 2-3 hours for working MVP

---

**Starting now! I'll create the files and let you know when ready to test.** 🚀
