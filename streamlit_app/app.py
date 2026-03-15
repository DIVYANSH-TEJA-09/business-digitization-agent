"""
Streamlit App: Business Digitization Agent UI

A comprehensive UI for the business digitization pipeline that shows:
- File upload and processing
- Real-time pipeline visualization with agent inputs/outputs
- Profile viewer with itinerary cards and images
- Extracted tables and all PDF data
"""

import streamlit as st
import requests
import time
import json
from pathlib import Path
from datetime import datetime

# =============================================================================
# Page Configuration
# =============================================================================
st.set_page_config(
    page_title="Business Digitization Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# API Configuration
# =============================================================================
API_BASE_URL = "http://localhost:8000"

# =============================================================================
# Session State Initialization
# =============================================================================
if "current_job_id" not in st.session_state:
    st.session_state.current_job_id = None
if "job_data" not in st.session_state:
    st.session_state.job_data = None
if "processing_status" not in st.session_state:
    st.session_state.processing_status = None
if "logs" not in st.session_state:
    st.session_state.logs = []

# =============================================================================
# Helper Functions
# =============================================================================


def add_log(message: str, level: str = "INFO"):
    """Add a log entry to the session state."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.logs.append({
        "timestamp": timestamp,
        "level": level,
        "message": message
    })


def clear_logs():
    """Clear all logs."""
    st.session_state.logs = []


def upload_file(file) -> dict:
    """Upload a ZIP file to the API."""
    try:
        files = {"file": (file.name, file, "application/zip")}
        # Increased timeout to 5 minutes for large files
        response = requests.post(
            f"{API_BASE_URL}/api/upload-and-process",
            files=files,
            timeout=300
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Upload failed")}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to API. Is the backend running?"}
    except requests.exceptions.ReadTimeout:
        return {"error": "Upload timed out. The file may be too large or backend is slow. Try again or check backend logs."}
    except Exception as e:
        return {"error": str(e)}


def get_job_status(job_id: str) -> dict:
    """Get job status from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/status/{job_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"error": "Status not available"}
    except Exception as e:
        return {"error": str(e)}


def get_job_data(job_id: str) -> dict:
    """Get complete job data from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/job-data/{job_id}", timeout=30)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        add_log(f"Failed to get job data: {e}", "ERROR")
        return {}


def check_api_health() -> dict:
    """Check API health."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "unhealthy"}
    except Exception:
        return {"status": "unhealthy", "error": "Cannot connect to API"}


# =============================================================================
# Sidebar
# =============================================================================
with st.sidebar:
    st.title("🤖 Business Digitization")
    st.markdown("---")
    
    # API Health Check
    st.subheader("System Status")
    health = check_api_health()
    if health.get("status") == "ok":
        st.success("✅ Backend Connected")
    else:
        st.error("❌ Backend Disconnected")
        st.info("Start backend: `uvicorn backend.main:app --reload`")
    
    st.markdown("---")
    
    # Navigation
    st.subheader("Navigation")
    page = st.radio(
        "Go to",
        ["📤 Upload & Process", "🔄 Pipeline View", "📊 Profile Viewer", "📋 Logs"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Job Info
    if st.session_state.current_job_id:
        st.info(f"**Current Job:** `{st.session_state.current_job_id}`")
        
        if st.button("Clear Current Job"):
            st.session_state.current_job_id = None
            st.session_state.job_data = None
            st.session_state.processing_status = None
            st.rerun()
    
    # Log viewer in sidebar (mini)
    with st.expander(f"📝 Recent Logs ({len(st.session_state.logs[-5:])})"):
        for log in st.session_state.logs[-5:]:
            st.caption(f"{log['timestamp']} - {log['message']}")

# =============================================================================
# Page: Upload & Process
# =============================================================================
if page == "📤 Upload & Process":
    st.title("📤 Upload & Process Business Documents")
    st.markdown("""
    Upload a ZIP file containing business documents (PDFs, images, spreadsheets).
    The system will automatically:
    - Extract and classify files
    - Parse documents and extract tables
    - Extract images with YOLO object detection
    - Analyze images with Qwen 3.5 vision
    - Generate a structured business profile
    """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a ZIP file",
        type=["zip"],
        help="Upload a ZIP file containing business documents"
    )
    
    if uploaded_file:
        st.info(f"📦 Selected: **{uploaded_file.name}** ({uploaded_file.size / 1024 / 1024:.2f} MB)")

        col1, col2 = st.columns([1, 4])
        with col1:
            upload_btn = st.button("🚀 Start Processing", type="primary", use_container_width=True)

        if upload_btn:
            add_log(f"Starting upload: {uploaded_file.name}")

            # Show progress bar during upload
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("⏳ Uploading and starting pipeline..."):
                status_text.text("⏳ Connecting to backend...")
                progress_bar.progress(10)
                
                result = upload_file(uploaded_file)
                
                progress_bar.progress(50)
                status_text.text("⏳ Processing response...")

                if "error" in result:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"❌ Upload failed: {result['error']}")
                    add_log(f"Upload failed: {result['error']}", "ERROR")
                    
                    # Show troubleshooting tips
                    with st.expander("🔧 Troubleshooting Tips"):
                        st.markdown("""
                        **Check if backend is running:**
                        ```bash
                        curl http://localhost:8000/api/health
                        ```
                        
                        **Start backend:**
                        ```bash
                        cd /path/to/business-digitization-agent
                        export OLLAMA_BASE_URL=http://localhost:11434/v1
                        export GROQ_API_KEY="your_api_key"
                        uvicorn backend.main:app --reload --port 8000
                        ```
                        
                        **Check backend logs for errors.**
                        """)
                else:
                    progress_bar.progress(100)
                    status_text.text("✅ Upload complete!")
                    
                    st.session_state.current_job_id = result["job_id"]
                    st.session_state.processing_status = result
                    add_log(f"Upload successful! Job ID: {result['job_id']}")

                    st.success(f"✅ Upload successful! Job ID: `{result['job_id']}`")
                    st.info(result.get("message", "Processing started"))

                    # Show initial file discovery results
                    if "file_collection" in result:
                        fc = result["file_collection"]
                        st.markdown("### 📁 Discovered Files")
                        cols = st.columns(4)
                        cols[0].metric("Documents", fc.get("total_documents", 0))
                        cols[1].metric("Spreadsheets", fc.get("total_spreadsheets", 0))
                        cols[2].metric("Images", fc.get("total_images", 0))
                        cols[3].metric("Videos", fc.get("total_videos", 0))

                    st.markdown("---")
                    st.markdown("### ⏳ Processing Status")
                    st.write("The pipeline is now running in the background. Go to **Pipeline View** to see real-time progress.")

                    if st.button("Go to Pipeline View →", type="primary"):
                        st.rerun()
    
    # Instructions
    with st.expander("📖 What should the ZIP contain?"):
        st.markdown("""
        **Recommended contents:**
        - Business registration documents (PDF)
        - Product/service catalogs (PDF, DOCX)
        - Price lists (PDF, XLSX, CSV)
        - Business images (JPG, PNG)
        - Any other relevant business documents
        
        **The system will extract:**
        - Business information (name, description, hours, location)
        - Products or services with details
        - Pricing information
        - Images with AI-powered descriptions
        - Tables and structured data
        """)

# =============================================================================
# Page: Pipeline View
# =============================================================================
elif page == "🔄 Pipeline View":
    st.title("🔄 Pipeline Visualization")
    st.markdown("Real-time view of the digitization pipeline showing agent inputs, outputs, and data flow.")
    
    if not st.session_state.current_job_id:
        st.warning("⚠️ No active job. Upload a file first.")
        if st.button("Go to Upload →"):
            st.rerun()
    else:
        job_id = st.session_state.current_job_id
        
        # Refresh button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Refresh Status", use_container_width=True):
                st.rerun()
        
        # Get current status
        status = get_job_status(job_id)
        st.session_state.processing_status = status
        
        # Progress bar
        progress = status.get("progress", 0)
        st.progress(progress / 100)
        
        # Status indicators
        cols = st.columns(3)
        cols[0].metric("Status", status.get("status", "unknown"))
        cols[1].metric("Phase", status.get("current_phase", "unknown"))
        cols[2].metric("Progress", f"{progress:.0f}%")
        
        if status.get("message"):
            st.info(f"💬 {status['message']}")
        
        # Pipeline stages visualization
        st.markdown("---")
        st.subheader("🏗️ Pipeline Stages")
        
        stages = [
            ("📂 File Discovery", "file_discovery", "Extracts and classifies files from ZIP"),
            ("📄 Document Parsing", "parsing", "Parses PDF, DOCX, XLSX files"),
            ("🌳 PageIndex Generation", "pageindex", "Builds searchable page indexes"),
            ("📊 Table Extraction", "table_extraction", "Extracts tables from documents"),
            ("🖼️ Media Extraction", "media_extraction", "Extracts images from documents"),
            ("👁️ Vision Analysis", "vision_analysis", "Analyzes images with Qwen 3.5"),
            ("🗺️ Schema Mapping", "schema_mapping", "Maps data to business profile schema"),
            ("✅ Validation", "validation", "Validates and scores the profile"),
        ]
        
        current_phase = status.get("current_phase", "")
        
        for i, (name, phase_key, description) in enumerate(stages):
            is_completed = progress > (i + 1) * (100 / len(stages))
            is_current = phase_key in current_phase.lower()
            
            with st.container():
                col1, col2, col3 = st.columns([0.5, 2, 4])
                
                with col1:
                    if is_completed:
                        st.success("✅")
                    elif is_current:
                        st.warning("⏳")
                    else:
                        st.write("⚪")
                
                with col2:
                    st.markdown(f"**{name}**")
                
                with col3:
                    st.caption(description)
                
                # Show input/output for current or completed stages
                if is_completed or is_current:
                    with st.expander(f"  📥 Input → 📤 Output for {name}"):
                        if st.session_state.job_data:
                            jd = st.session_state.job_data
                            if phase_key == "file_discovery" and "file_collection" in jd:
                                st.json(jd["file_collection"])
                            elif phase_key == "parsing" and "parsed_documents" in jd:
                                st.write(f"**{len(jd['parsed_documents'])} documents parsed**")
                                for doc in jd["parsed_documents"][:2]:
                                    st.json(doc)
                            elif phase_key == "table_extraction" and "extracted_tables" in jd:
                                st.write(f"**{len(jd['extracted_tables'])} tables extracted**")
                                for table in jd["extracted_tables"][:2]:
                                    st.json(table)
                            elif phase_key == "media_extraction" and "media_collection" in jd:
                                mc = jd["media_collection"]
                                st.write(f"**{mc.get('total_count', 0)} media files**")
                                st.write(f"- Images: {len(mc.get('images', []))}")
                                st.write(f"- Videos: {len(mc.get('videos', []))}")
                            elif phase_key == "vision_analysis" and "image_analyses" in jd:
                                st.write(f"**{len(jd['image_analyses'])} images analyzed**")
                                for analysis in jd["image_analyses"][:2]:
                                    st.json(analysis)
                        else:
                            st.info("Job data not yet available")
        
        # Auto-refresh if processing
        if status.get("status") == "processing" and progress < 100:
            st.info("⏱️ Auto-refreshing in 5 seconds...")
            time.sleep(5)
            st.rerun()
        
        # Show complete data when done
        if status.get("status") == "completed" or progress >= 100:
            st.success("🎉 Pipeline Complete!")
            
            if not st.session_state.job_data:
                with st.spinner("Loading job data..."):
                    st.session_state.job_data = get_job_data(job_id)
                    add_log(f"Job data loaded for {job_id}")
            
            if st.session_state.job_data:
                jd = st.session_state.job_data
                
                st.markdown("---")
                st.subheader("📊 Processing Summary")
                
                summary_cols = st.columns(4)
                
                fc = jd.get("file_collection", {})
                summary_cols[0].metric("Total Files", fc.get("total_files", 0))
                
                pd = jd.get("parsed_documents", [])
                summary_cols[1].metric("Documents Parsed", len(pd))
                
                tables = jd.get("extracted_tables", [])
                summary_cols[2].metric("Tables Extracted", len(tables))
                
                mc = jd.get("media_collection", {})
                summary_cols[3].metric("Images Extracted", len(mc.get("images", [])))
                
                # Validation results
                validation = jd.get("validation", {})
                if validation:
                    st.markdown("### ✅ Validation Results")
                    val_cols = st.columns(3)
                    val_cols[0].metric("Valid", "✅" if validation.get("is_valid") else "❌")
                    val_cols[1].metric("Completeness", f"{validation.get('completeness_score', 0):.0%}")
                    val_cols[2].metric("Errors", len(validation.get("errors", [])))
                    
                    if validation.get("warnings"):
                        with st.expander(f"⚠️ {len(validation['warnings'])} Warnings"):
                            for w in validation["warnings"]:
                                st.warning(w)
                    
                    if validation.get("errors"):
                        with st.expander(f"❌ {len(validation['errors'])} Errors"):
                            for e in validation["errors"]:
                                st.error(e)
                
                # Business profile preview
                if "business_profile" in jd:
                    st.markdown("### 🏢 Business Profile Preview")
                    bp = jd["business_profile"]
                    bi = bp.get("business_info", {})
                    
                    st.write(f"**Business Type:** {bp.get('business_type', 'unknown')}")
                    st.write(f"**Description:** {bi.get('description', 'N/A')[:200]}...")
                    
                    if bp.get("products"):
                        st.write(f"**Products:** {len(bp['products'])} items")
                    if bp.get("services"):
                        st.write(f"**Services:** {len(bp['services'])} items")
                    
                    if st.button("View Full Profile →", type="primary"):
                        st.rerun()

# =============================================================================
# Page: Profile Viewer
# =============================================================================
elif page == "📊 Profile Viewer":
    st.title("📊 Business Profile Viewer")
    
    if not st.session_state.job_data:
        if st.session_state.current_job_id:
            with st.spinner("Loading job data..."):
                st.session_state.job_data = get_job_data(st.session_state.current_job_id)
        else:
            st.warning("⚠️ No job data available. Process a file first.")
            if st.button("Go to Upload →"):
                st.rerun()
    
    if st.session_state.job_data:
        jd = st.session_state.job_data
        profile = jd.get("business_profile", {})
        
        # Tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏢 Business Info",
            "🛍️ Products",
            "🎯 Services & Itineraries",
            "🖼️ Media Gallery",
            "📊 Extracted Data"
        ])
        
        # Tab 1: Business Info
        with tab1:
            st.subheader("Business Information")
            bi = profile.get("business_info", {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📝 Details")
                st.write(f"**Description:** {bi.get('description', 'N/A')}")
                st.write(f"**Working Hours:** {bi.get('working_hours', 'N/A')}")
                
                contact = bi.get("contact", {})
                if contact:
                    st.markdown("### 📞 Contact")
                    st.write(f"Email: {contact.get('email', 'N/A')}")
                    st.write(f"Phone: {contact.get('phone', 'N/A')}")
                    st.write(f"Website: {contact.get('website', 'N/A')}")
            
            with col2:
                location = bi.get("location", {})
                if location:
                    st.markdown("### 📍 Location")
                    st.write(f"Address: {location.get('address', 'N/A')}")
                    st.write(f"City: {location.get('city', 'N/A')}")
                    st.write(f"State: {location.get('state', 'N/A')}")
                    st.write(f"ZIP: {location.get('zip_code', 'N/A')}")
                
                payment = bi.get("payment_methods", [])
                if payment:
                    st.markdown("### 💳 Payment Methods")
                    for p in payment:
                        st.write(f"- {p}")
                
                tags = bi.get("tags", [])
                if tags:
                    st.markdown("### 🏷️ Tags")
                    st.write(", ".join(tags))
        
        # Tab 2: Products
        with tab2:
            st.subheader("Products")
            products = profile.get("products", [])
            
            if not products:
                st.info("No products found in this business profile.")
            else:
                st.write(f"**{len(products)} products found**")
                
                for i, product in enumerate(products):
                    with st.expander(f"📦 {product.get('name', f'Product {i+1}')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Description:** {product.get('description', 'N/A')}")
                            st.write(f"**Category:** {product.get('category', 'N/A')}")
                            st.write(f"**SKU:** {product.get('sku', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Price:** ${product.get('price', 0):.2f}")
                            st.write(f"**Stock:** {product.get('stock_level', 'N/A')}")
                        
                        if product.get("specifications"):
                            st.markdown("#### Specifications")
                            st.json(product["specifications"])
        
        # Tab 3: Services & Itineraries
        with tab3:
            st.subheader("Services & Itineraries")
            services = profile.get("services", [])
            
            if not services:
                st.info("No services found in this business profile.")
            else:
                st.write(f"**{len(services)} services found**")
                
                for i, service in enumerate(services):
                    st.markdown(f"### 🎯 {service.get('name', f'Service {i+1}')}")
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Description:** {service.get('description', 'N/A')}")
                        st.write(f"**Category:** {service.get('category', 'N/A')}")
                    
                    with col2:
                        price = service.get("pricing", {})
                        if price:
                            st.write(f"**Price:** ${price.get('amount', 0):.2f}")
                            st.write(f"**Type:** {price.get('type', 'fixed')}")
                    
                    # Itinerary display
                    itinerary = service.get("itinerary", [])
                    if itinerary:
                        st.markdown("#### 📋 Itinerary")
                        
                        # Create cards for each itinerary item
                        for j, item in enumerate(itinerary):
                            with st.container():
                                st.markdown(f"**Step {j+1}:** {item.get('step', 'N/A')}")
                                st.write(f"- **Activity:** {item.get('activity', 'N/A')}")
                                st.write(f"- **Duration:** {item.get('duration', 'N/A')}")
                                st.write(f"- **Description:** {item.get('description', 'N/A')}")
                                st.divider()
                    
                    if service.get("inclusions"):
                        st.markdown("#### ✅ Inclusions")
                        for inc in service["inclusions"]:
                            st.write(f"- {inc}")
                    
                    if service.get("exclusions"):
                        st.markdown("#### ❌ Exclusions")
                        for exc in service["exclusions"]:
                            st.write(f"- {exc}")
                    
                    st.divider()
        
        # Tab 4: Media Gallery
        with tab4:
            st.subheader("Media Gallery")
            
            # Get PDF-wise data
            pdf_data = jd.get("pdf_wise_data", {})
            media_collection = jd.get("media_collection", {})
            image_analyses = jd.get("image_analyses", [])
            
            # Create analysis lookup
            analysis_lookup = {a["image_id"]: a for a in image_analyses}
            
            if pdf_data and "pdfs" in pdf_data:
                st.markdown("### 📄 Images by PDF")
                
                for pdf_id, pdf_info in pdf_data["pdfs"].items():
                    with st.expander(f"📄 {pdf_info.get('pdf_name', pdf_id)} ({pdf_info.get('total_images', 0)} images)"):
                        st.write(f"**Source:** {pdf_info.get('source_file', 'N/A')}")
                        st.write(f"**Total Pages:** {pdf_info.get('total_pages', 0)}")
                        
                        pages = pdf_info.get("pages", {})
                        for page_num, page_data in pages.items():
                            st.markdown(f"#### Page {page_num}")
                            
                            images = page_data.get("images", [])
                            if not images:
                                st.caption("No images on this page")
                                continue
                            
                            cols = st.columns(min(3, len(images)))
                            for idx, img in enumerate(images):
                                with cols[idx % 3]:
                                    img_path = img.get("file_path", "")
                                    if img_path and Path(img_path).exists():
                                        st.image(str(img_path), caption=img.get("image_id", ""), use_container_width=True)
                                    else:
                                        st.info("Image not available")
                                    
                                    # Show YOLO detections
                                    yolo_dets = img.get("yolo_detections", [])
                                    if yolo_dets:
                                        with st.expander(f"🔍 YOLO ({len(yolo_dets)})"):
                                            for det in yolo_dets:
                                                st.write(f"- {det.get('class', 'unknown')} ({det.get('confidence', 0):.2f})")
                                    
                                    # Show vision description
                                    vision_desc = img.get("vision_description", {})
                                    if vision_desc:
                                        with st.expander("👁️ Vision Analysis"):
                                            st.write(f"**Description:** {vision_desc.get('description', 'N/A')}")
                                            st.write(f"**Category:** {vision_desc.get('category', 'N/A')}")
                                            st.write(f"**Tags:** {', '.join(vision_desc.get('tags', []))}")
                                            st.write(f"**Business Related:** {vision_desc.get('is_business_related', False)}")
            
            elif media_collection:
                st.markdown("### 🖼️ All Images")
                images = media_collection.get("images", [])
                
                if not images:
                    st.info("No images found")
                else:
                    cols = st.columns(3)
                    for idx, img in enumerate(images):
                        with cols[idx % 3]:
                            img_path = img.get("file_path", "")
                            if img_path and Path(img_path).exists():
                                st.image(str(img_path), use_container_width=True)
                                st.caption(img.get("image_id", "")[:30])
        
        # Tab 5: Extracted Data
        with tab5:
            st.subheader("Extracted Tables")
            
            tables = jd.get("extracted_tables", [])
            
            if not tables:
                st.info("No tables extracted")
            else:
                st.write(f"**{len(tables)} tables found**")
                
                for i, table in enumerate(tables):
                    with st.expander(f"📊 Table {i+1}: {table.get('type', 'Unknown')} (Page {table.get('source_page', 'N/A')})"):
                        data = table.get("data", [])
                        if data:
                            # Convert to DataFrame for nice display
                            import pandas as pd
                            df = pd.DataFrame(data)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.json(table)
            
            st.markdown("---")
            st.subheader("Parsed Documents")
            
            parsed_docs = jd.get("parsed_documents", [])
            
            if not parsed_docs:
                st.info("No parsed documents")
            else:
                for doc in parsed_docs:
                    with st.expander(f"📄 {Path(doc.get('source_file', '')).name}"):
                        st.write(f"**Type:** {doc.get('file_type', 'unknown')}")
                        st.write(f"**Pages:** {doc.get('total_pages', 0)}")
                        
                        # Show first page text preview
                        pages = doc.get("pages", [])
                        if pages:
                            first_page = pages[0]
                            text = first_page.get("text", "")
                            if text:
                                st.markdown("#### Text Preview (First Page)")
                                st.text(text[:1000] + "..." if len(text) > 1000 else text)

# =============================================================================
# Page: Logs
# =============================================================================
elif page == "📋 Logs":
    st.title("📋 Processing Logs")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ Clear Logs", use_container_width=True):
            clear_logs()
            st.rerun()
    
    if not st.session_state.logs:
        st.info("No logs yet. Start by uploading a file.")
    else:
        # Filter options
        log_levels = st.multiselect(
            "Filter by level",
            ["INFO", "WARNING", "ERROR", "DEBUG"],
            default=["INFO", "WARNING", "ERROR"]
        )
        
        filtered_logs = [log for log in st.session_state.logs if log["level"] in log_levels]
        
        # Display logs
        for log in reversed(filtered_logs):
            level_color = {
                "INFO": "blue",
                "WARNING": "orange",
                "ERROR": "red",
                "DEBUG": "gray"
            }
            
            with st.container():
                cols = st.columns([0.8, 0.5, 6])
                cols[0].caption(log["timestamp"])
                cols[1].markdown(f":{level_color.get(log['level'], 'gray')}[{log['level']}]")
                cols[2].write(log["message"])
                st.divider()

# =============================================================================
# Footer
# =============================================================================
st.markdown("---")
st.caption("""
Business Digitization Agent v1.0 | 
Powered by Qwen 3.5 Vision, YOLO, and GPT-OSS-120B |
Built with Streamlit
""")
