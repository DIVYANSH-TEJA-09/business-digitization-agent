"""
Digi-Biz: Agentic Business Digitization Framework
Streamlit Demo Application

This app demonstrates the complete workflow:
1. Upload ZIP with business documents
2. File Discovery Agent extracts and classifies files
3. Document Parsing Agent extracts text and tables
4. Media Extraction Agent extracts images
5. Vision Agent (Groq Llama-4-Scout) analyzes images
6. View results
"""
import streamlit as st
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json
import io
from PIL import Image
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Import Groq to verify it's available
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Import agents
from backend.agents.file_discovery import FileDiscoveryAgent, FileDiscoveryInput
from backend.agents.document_parsing import DocumentParsingAgent, DocumentParsingInput
from backend.agents.table_extraction import TableExtractionAgent, TableExtractionInput
from backend.agents.media_extraction import MediaExtractionAgent, MediaExtractionInput
from backend.agents.vision_agent import VisionAgent, VisionAnalysisInput
from backend.agents.indexing import IndexingAgent, IndexingInput
from backend.utils.storage_manager import StorageManager


# =============================================================================
# Streamlit Configuration
# =============================================================================
st.set_page_config(
    page_title="Digi-Biz - Business Digitization",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
    .agent-card {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f5f5f5;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Session State Initialization
# =============================================================================
if 'job_id' not in st.session_state:
    st.session_state.job_id = ""
if 'discovery_output' not in st.session_state:
    st.session_state.discovery_output = None
if 'parsing_output' not in st.session_state:
    st.session_state.parsing_output = None
if 'tables_output' not in st.session_state:
    st.session_state.tables_output = None
if 'media_output' not in st.session_state:
    st.session_state.media_output = None
if 'vision_output' not in st.session_state:
    st.session_state.vision_output = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False


# =============================================================================
# Helper Functions
# =============================================================================
def generate_job_id():
    """Generate unique job ID"""
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def cleanup_temp_dirs():
    """Clean up temporary directories"""
    temp_base = Path(tempfile.gettempdir()) / "digi_biz"
    if temp_base.exists():
        shutil.rmtree(temp_base)


def get_model_status():
    """Check if Ollama and Qwen model are available"""
    try:
        from ollama import Client
        client = Client(host='http://localhost:11434', timeout=5)
        response = client.list()
        
        if isinstance(response, dict) and 'models' in response:
            models = [m['name'] for m in response['models']]
        elif hasattr(response, 'models'):
            models = [m.name if hasattr(m, 'name') else m['name'] for m in response.models]
        else:
            models = []
        
        ollama_ok = True
        qwen_available = any('qwen3.5' in m for m in models)
        
        # Test actual vision capability
        vision_working = False
        if qwen_available:
            try:
                # Quick vision test
                test_client = Client(host='http://localhost:11434', timeout=30)
                test_img = Image.new('RGB', (50, 50), color='red')
                test_bytes = io.BytesIO()
                test_img.save(test_bytes, format='PNG')
                
                test_response = test_client.chat(
                    model='qwen3.5:0.8b',
                    messages=[{
                        'role': 'user',
                        'content': 'What color?',
                        'images': [test_bytes.getvalue()]
                    }],
                    options={'timeout': 20000}
                )
                
                vision_working = len(test_response['message']['content'].strip()) > 10
            except Exception:
                vision_working = False
        
        return ollama_ok, qwen_available, vision_working, models
        
    except Exception:
        return False, False, False, []


# =============================================================================
# Main App
# =============================================================================

# Header
st.markdown('<h1 class="main-header">📄 Digi-Biz</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Agentic Business Digitization Framework</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🔧 Configuration")
    
    # Model status
    st.subheader("Model Status")
    
    # Check Groq API
    groq_ok = False
    groq_model = "N/A"
    groq_error = ""
    
    try:
        api_key = os.getenv("GROQ_API_KEY")
        
        if not api_key:
            groq_error = "GROQ_API_KEY not set in .env"
        elif api_key == "gsk_YOUR_API_KEY_HERE":
            groq_error = "Using placeholder key"
        else:
            # Try to create client
            client = Groq(api_key=api_key, timeout=5)
            models = client.models.list()
            groq_ok = True
            groq_model = "llama-4-scout-17b"
    except ImportError:
        groq_error = "groq package not installed"
    except Exception as e:
        groq_error = str(e)[:100]
    
    if groq_ok:
        st.success(f"✓ Groq API: {groq_model}")
    else:
        st.error("✗ Groq API Not Available")
        st.code(groq_error, language=None)
        st.info("Fix: Get key from https://console.groq.com and add to .env file")
    
    # Check Ollama (fallback)
    ollama_ok = False
    try:
        from ollama import Client
        client = Client(host='http://localhost:11434', timeout=5)
        client.list()
        ollama_ok = True
    except Exception:
        pass
    
    if ollama_ok:
        st.success("✓ Ollama: Fallback Ready")
    else:
        st.warning("⚠ Ollama: Not Running (optional)")
    
    st.divider()
    
    # Agent status
    st.subheader("Agents")
    st.markdown("""
    <div class="agent-card">
    <b>1. File Discovery</b><br>
    <small>Extracts & classifies files from ZIP</small>
    </div>
    
    <div class="agent-card">
    <b>2. Document Parsing</b><br>
    <small>Extracts text from PDF/DOCX</small>
    </div>
    
    <div class="agent-card">
    <b>3. Table Extraction</b><br>
    <small>Detects & classifies tables</small>
    </div>
    
    <div class="agent-card">
    <b>4. Media Extraction</b><br>
    <small>Extracts embedded images</small>
    </div>
    
    <div class="agent-card">
    <b>5. Vision Agent</b><br>
    <small>Analyzes images with Groq</small>
    </div>
    
    <div class="agent-card">
    <b>6. Indexing Agent</b><br>
    <small>Builds RAG search index</small>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Reset button
    if st.button("🔄 Reset All", use_container_width=True):
        cleanup_temp_dirs()
        for key in list(st.session_state.keys()):
            st.session_state[key] = None
        st.session_state.processing_complete = False
        st.rerun()

# Main content area
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📤 Upload", "⚙️ Processing", "📊 Results", "🖼️ Vision Analysis", "🌳 Index Tree", "📄 Business Profile"])

with tab1:
    st.header("Upload Business Documents")
    
    st.markdown("""
    **Supported Formats:**
    - 📄 Documents: PDF, DOCX, DOC
    - 📊 Spreadsheets: XLSX, XLS, CSV
    - 🖼️ Images: JPG, PNG, GIF, WEBP
    - 🎥 Videos: MP4, AVI, MOV
    
    **Instructions:**
    1. Create a ZIP file with your business documents
    2. Upload using the file uploader below
    3. Click "Start Processing"
    """)
    
    uploaded_file = st.file_uploader(
        "Upload ZIP file",
        type=['zip'],
        help="Select a ZIP file containing business documents"
    )
    
    if uploaded_file:
        st.success(f"✓ Uploaded: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
        
        # Save to temp location
        temp_dir = Path(tempfile.gettempdir()) / "digi_biz" / generate_job_id()
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = temp_dir / uploaded_file.name
        with open(zip_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        st.session_state.zip_path = str(zip_path)
        st.session_state.job_id = temp_dir.name
        
        st.info(f"Job ID: `{st.session_state.job_id}`")
        
        # Start processing button
        if st.button("🚀 Start Processing", type="primary", use_container_width=True):
            st.session_state.processing_started = True
            st.rerun()

with tab2:
    st.header("Processing Pipeline")
    
    if not hasattr(st.session_state, 'processing_started') or not st.session_state.processing_started:
        st.info("👆 Upload a ZIP file and click 'Start Processing'")
        st.stop()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Step 1: File Discovery
    status_text.text("Step 1/5: File Discovery Agent...")
    try:
        storage_manager = StorageManager(storage_base=str(Path(tempfile.gettempdir()) / "digi_biz" / st.session_state.job_id))
        
        discovery_agent = FileDiscoveryAgent(storage_manager=storage_manager)
        discovery_input = FileDiscoveryInput(
            zip_file_path=st.session_state.zip_path,
            job_id=st.session_state.job_id
        )
        st.session_state.discovery_output = discovery_agent.discover(discovery_input)
        
        progress_bar.progress(20)
        
        if st.session_state.discovery_output.success:
            st.success(f"✓ File Discovery Complete: {st.session_state.discovery_output.total_files} files")
            st.markdown(f"""
            <div class="success-box">
            <b>Summary:</b><br>
            • Documents: {st.session_state.discovery_output.summary.get('documents_count', 0)}<br>
            • Spreadsheets: {st.session_state.discovery_output.summary.get('spreadsheets_count', 0)}<br>
            • Images: {st.session_state.discovery_output.summary.get('images_count', 0)}<br>
            • Videos: {st.session_state.discovery_output.summary.get('videos_count', 0)}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"✗ File Discovery Failed: {st.session_state.discovery_output.errors}")
            st.stop()
            
    except Exception as e:
        st.error(f"File Discovery Error: {str(e)}")
        st.stop()
    
    # Step 2: Document Parsing
    status_text.text("Step 2/5: Document Parsing Agent...")
    try:
        parsing_agent = DocumentParsingAgent(enable_ocr=False)
        parsing_input = DocumentParsingInput(
            documents=st.session_state.discovery_output.documents,
            job_id=st.session_state.job_id,
            enable_ocr=False
        )
        st.session_state.parsing_output = parsing_agent.parse(parsing_input)
        
        progress_bar.progress(40)
        
        if st.session_state.parsing_output.success:
            st.success(f"✓ Document Parsing Complete: {st.session_state.parsing_output.total_pages} pages")
        else:
            st.warning("⚠ Document Parsing: No documents to parse")
            
    except Exception as e:
        st.warning(f"Document Parsing: {str(e)}")
    
    # Step 3: Table Extraction
    status_text.text("Step 3/5: Table Extraction Agent...")
    try:
        table_agent = TableExtractionAgent()
        table_input = TableExtractionInput(
            parsed_documents=st.session_state.parsing_output.parsed_documents if st.session_state.parsing_output else [],
            job_id=st.session_state.job_id
        )
        st.session_state.tables_output = table_agent.extract(table_input)
        
        progress_bar.progress(60)
        
        if st.session_state.tables_output.success:
            st.success(f"✓ Table Extraction Complete: {st.session_state.tables_output.total_tables} tables")
            if st.session_state.tables_output.tables_by_type:
                types_str = ", ".join([f"{k}: {v}" for k, v in st.session_state.tables_output.tables_by_type.items()])
                st.info(f"Types: {types_str}")
        else:
            st.warning("⚠ Table Extraction: No tables found")
            
    except Exception as e:
        st.warning(f"Table Extraction: {str(e)}")
    
    # Step 4: Media Extraction
    status_text.text("Step 4/5: Media Extraction Agent...")
    try:
        media_agent = MediaExtractionAgent(enable_deduplication=True)
        media_input = MediaExtractionInput(
            parsed_documents=st.session_state.parsing_output.parsed_documents if st.session_state.parsing_output else [],
            standalone_files=[img.file_path for img in st.session_state.discovery_output.images] if st.session_state.discovery_output else [],
            job_id=st.session_state.job_id
        )
        st.session_state.media_output = media_agent.extract_all(media_input)
        
        progress_bar.progress(80)
        
        if st.session_state.media_output.success:
            st.success(f"✓ Media Extraction Complete: {st.session_state.media_output.total_images} images")
            if st.session_state.media_output.duplicates_removed > 0:
                st.info(f"Removed {st.session_state.media_output.duplicates_removed} duplicates")
        else:
            st.warning("⚠ Media Extraction: No images found")
            
    except Exception as e:
        st.warning(f"Media Extraction: {str(e)}")
    
    # Step 5: Vision Analysis
    status_text.text("Step 5/5: Vision Agent (Groq Llama-4-Scout)...")
    try:
        # Initialize Vision Agent with Groq provider
        from backend.agents.vision_agent import VisionAgent
        
        vision_agent = VisionAgent(provider="groq", timeout=120)
        
        # Check if we have images to analyze
        images_to_analyze = []
        if st.session_state.media_output and st.session_state.media_output.success:
            images_to_analyze = st.session_state.media_output.media.images[:5]  # Analyze first 5 images

        if images_to_analyze:
            st.info(f"Analyzing {len(images_to_analyze)} images with Groq Vision (Llama-4-Scout)...")
            progress_vision = st.progress(0)

            try:
                # Analyze images
                analyses = vision_agent.analyze_batch(images_to_analyze)
                st.session_state.vision_output = analyses

                progress_vision.progress(100)
                st.success(f"✓ Vision Analysis Complete: {len(analyses)} images analyzed")

                # Show quick summary
                if analyses:
                    categories = {}
                    for a in analyses:
                        cat = a.category.value
                        categories[cat] = categories.get(cat, 0) + 1

                    st.markdown("**Categories Detected:**")
                    cat_text = ", ".join([f"{k}: {v}" for k, v in categories.items()])
                    st.info(cat_text)

            except Exception as ve:
                st.warning(f"Vision analysis failed: {str(ve)}")
                st.info("Falling back to Ollama...")

                # Try Ollama fallback
                try:
                    vision_agent_ollama = VisionAgent(provider="ollama", timeout=120)
                    analyses = vision_agent_ollama.analyze_batch(images_to_analyze)
                    st.session_state.vision_output = analyses
                    st.success(f"✓ Vision Analysis Complete (via Ollama): {len(analyses)} images")
                except Exception as e2:
                    st.session_state.vision_output = None
                    st.error(f"All vision providers failed: {e2}")
        else:
            st.session_state.vision_output = None
            st.warning("⚠ Vision Analysis: No images to analyze")

        # Step 6: Indexing (RAG)
        status_text.text("Step 6/6: Building Search Index (RAG)...")
        try:
            indexing_agent = IndexingAgent()

            # Prepare indexing input
            all_images = []
            if st.session_state.media_output and st.session_state.media_output.success:
                all_images = st.session_state.media_output.media.images

            indexing_input = IndexingInput(
                parsed_documents=st.session_state.parsing_output.parsed_documents if st.session_state.parsing_output else [],
                tables=st.session_state.tables_output.tables if st.session_state.tables_output else [],
                images=all_images,
                job_id=st.session_state.job_id
            )

            # Build index
            page_index = indexing_agent.build_index(indexing_input)
            
            # Store in session state (convert Pydantic model to dict for serialization)
            st.session_state.page_index_dict = page_index.model_dump(mode='json')
            st.session_state.page_index_has_data = True

            st.success(f"✓ Index Built: {page_index.metadata.get('total_keywords', 0)} keywords")

        except Exception as e:
            st.warning(f"Indexing failed: {str(e)}")
            st.session_state.page_index_dict = None
            st.session_state.page_index_has_data = False

        progress_bar.progress(100)
        status_text.text("✓ Processing Complete!")

        st.session_state.processing_complete = True

    except Exception as e:
        st.warning(f"Processing error: {str(e)}")
        st.session_state.processing_complete = False

# Step 7: Schema Mapping (optional - for future)
# TODO: Add schema mapping button in Results tab

with tab3:
    st.header("Processing Results")
    
    if not st.session_state.processing_complete:
        st.info("⏳ Processing not complete yet. Go to 'Processing' tab.")
        st.stop()
    
    # Generate Business Profile Button
    st.subheader("🎯 Generate Business Profile")
    st.markdown("Use AI to create a structured business profile from extracted data")
    
    if st.button("🚀 Generate Business Profile with AI", type="primary", use_container_width=True):
        with st.spinner("Generating business profile with Groq AI... Processing each document individually (1-2 minutes)"):
            try:
                from backend.agents.schema_mapping_simple import SchemaMappingAgent
                from backend.models.schemas import SchemaMappingInput
                from backend.agents.validation_agent import ValidationAgent
                from backend.models.schemas import ValidationInput as ValidationInputSchema
                
                # Get page index
                if not st.session_state.get('page_index_dict'):
                    st.error("No index available. Please run processing first.")
                else:
                    from backend.models.schemas import PageIndex
                    page_index = PageIndex.model_validate(st.session_state.page_index_dict)
                    
                    # Step 1: Schema Mapping
                    with st.status("Running Schema Mapping Agent...", expanded=True) as status:
                        agent = SchemaMappingAgent()
                        input_data = SchemaMappingInput(
                            page_index=page_index,
                            job_id=st.session_state.job_id
                        )
                        mapping_output = agent.map_to_schema(input_data)
                        
                        if mapping_output.success and mapping_output.profile:
                            st.success("✅ Schema mapping complete!")
                            status.update(label="Schema Mapping Complete", state="complete")
                        else:
                            st.warning(f"⚠️ Schema mapping had issues: {mapping_output.errors}")
                            status.update(label="Schema Mapping Complete (with warnings)", state="complete")
                    
                    # Step 2: Validation
                    with st.status("Running Validation Agent...", expanded=True) as status:
                        validation_agent = ValidationAgent()
                        validation_input = ValidationInputSchema(
                            profile=mapping_output.profile,
                            job_id=st.session_state.job_id
                        )
                        validation_output = validation_agent.validate(validation_input)
                        
                        st.session_state.validation_result = validation_output.model_dump(mode='json')
                        
                        if validation_output.is_valid:
                            st.success(f"✅ Validation passed! Completeness: {validation_output.completeness_score:.0%}")
                            status.update(label="Validation Complete", state="complete")
                        else:
                            st.warning(f"⚠️ Validation found {len(validation_output.errors)} errors")
                            status.update(label="Validation Complete (errors found)", state="complete")
                    
                    # Store profile
                    if mapping_output.profile:
                        st.session_state.business_profile = mapping_output.profile.model_dump(mode='json')
                        st.success("✅ Business Profile Generated Successfully!")
                        st.info("Go to 'Business Profile' tab to view results")
                    else:
                        st.error("Failed to generate profile")
                        
            except Exception as e:
                st.error(f"Error generating profile: {str(e)}")
                logger.error(f"Schema mapping failed: {e}")
    
    st.divider()
    
    # File Discovery Results
    st.subheader("📁 File Discovery")
    if st.session_state.discovery_output:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Documents", st.session_state.discovery_output.summary.get('documents_count', 0))
        with col2:
            st.metric("Spreadsheets", st.session_state.discovery_output.summary.get('spreadsheets_count', 0))
        with col3:
            st.metric("Images", st.session_state.discovery_output.summary.get('images_count', 0))
        with col4:
            st.metric("Videos", st.session_state.discovery_output.summary.get('videos_count', 0))
        
        # File list
        with st.expander("📋 View File List"):
            if st.session_state.discovery_output.documents:
                st.write("**Documents:**")
                for doc in st.session_state.discovery_output.documents:
                    st.write(f"- {doc.original_name} ({doc.file_type.value})")
    
    # Document Parsing Results
    st.subheader("📄 Document Parsing")
    if st.session_state.parsing_output and st.session_state.parsing_output.success:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pages", st.session_state.parsing_output.total_pages)
        with col2:
            st.metric("Processing Time", f"{st.session_state.parsing_output.processing_time:.1f}s")
        
        # Show extracted text from first document
        with st.expander("📝 View Extracted Text"):
            if st.session_state.parsing_output.parsed_documents:
                doc = st.session_state.parsing_output.parsed_documents[0]
                st.write(f"**Source:** {doc.source_file}")
                st.write(f"**Pages:** {doc.total_pages}")
                if doc.pages and doc.pages[0].text:
                    st.text_area("Text content", doc.pages[0].text[:1000], height=300)
    
    # Table Extraction Results
    st.subheader("📊 Table Extraction")
    if st.session_state.tables_output and st.session_state.tables_output.success:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tables Found", st.session_state.tables_output.total_tables)
        with col2:
            st.metric("By Type", str(st.session_state.tables_output.tables_by_type))
        
        # Show tables
        with st.expander("📋 View Tables"):
            for i, table in enumerate(st.session_state.tables_output.tables):
                st.write(f"**Table {i+1}:** {table.table_type.value}")
                st.write(f"Source: {table.source_doc}, Page: {table.source_page}")
                if table.headers:
                    st.write(f"Headers: {', '.join(table.headers)}")

with tab4:
    st.header("🖼️ Vision Analysis (Groq Llama-4-Scout)")

    if not st.session_state.processing_complete:
        st.info("⏳ Processing not complete yet.")
        st.stop()

    if not st.session_state.vision_output:
        st.warning("⚠ No vision analysis available. Either no images were found or analysis failed.")
        st.stop()

    # Show analyzed images
    for i, analysis in enumerate(st.session_state.vision_output):
        st.divider()

        col1, col2 = st.columns([1, 2])

        with col1:
            # Find corresponding image
            if st.session_state.media_output:
                for img in st.session_state.media_output.media.images:
                    if img.image_id == analysis.image_id:
                        try:
                            st.image(img.file_path, caption=analysis.image_id, use_container_width=True)
                        except Exception:
                            st.write(f"Image: {analysis.image_id}")
                        break

        with col2:
            st.subheader(f"Analysis {i+1}")

            # Category badge - handle both str and enum
            category_value = analysis.category
            if hasattr(analysis.category, 'value'):
                category_value = analysis.category.value
            elif isinstance(analysis.category, str):
                category_value = analysis.category.lower()

            category_colors = {
                'product': '🔵',
                'service': '🟢',
                'food': '🟠',
                'destination': '🟣',
                'person': '🔴',
                'document': '⚪',
                'logo': '🟡',
                'other': '⚫'
            }

            category_emoji = category_colors.get(category_value, '⚪')
            st.markdown(f"**Category:** {category_emoji} {category_value}")
            
            # Show provider and confidence
            provider = analysis.metadata.get('provider', 'unknown')
            provider_icon = "🚀" if provider == 'groq' else "🦙"
            st.markdown(f"**Provider:** {provider_icon} {provider.upper()}")
            st.markdown(f"**Confidence:** {analysis.confidence:.0%}")

            # Description
            if analysis.description:
                st.markdown(f"**Description:** {analysis.description}")

            # Tags
            if analysis.tags:
                st.markdown(f"**Tags:** {', '.join(analysis.tags)}")

            # Product/Service flags
            col_a, col_b = st.columns(2)
            with col_a:
                if analysis.is_product:
                    st.success("✓ Product")
            with col_b:
                if analysis.is_service_related:
                    st.info("✓ Service-related")

            # Associations
            if analysis.suggested_associations:
                st.markdown(f"**Associations:** {', '.join(analysis.suggested_associations)}")
            
            # Processing time
            proc_time = analysis.metadata.get('processing_time', 0)
            st.caption(f"Processed in {proc_time:.2f}s")

with tab5:
    st.header("🌳 PageIndex Tree Structure")
    
    if not st.session_state.processing_complete:
        st.info("⏳ Processing not complete yet.")
        st.stop()
    
    if not st.session_state.get('page_index_has_data') or not st.session_state.get('page_index_dict'):
        st.warning("⚠ No index available. Run processing first.")
        st.stop()
    
    # Reconstruct PageIndex from dict
    from backend.models.schemas import PageIndex
    page_index = PageIndex.model_validate(st.session_state.page_index_dict)
    
    # Index Statistics
    st.subheader("📊 Index Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Keywords", page_index.metadata.get('total_keywords', 0))
    with col2:
        # Count tree nodes from documents if tree_root is None
        tree_node_count = 0
        if page_index.tree_root:
            tree_node_count = page_index.metadata.get('total_tree_nodes', 0)
        elif page_index.documents:
            tree_node_count = len(page_index.documents)
        st.metric("Tree Nodes", tree_node_count)
    with col3:
        st.metric("Build Time", f"{page_index.metadata.get('build_time_seconds', 0):.2f}s")
    
    st.divider()
    
    # Tree Visualization - Show documents if tree_root is None
    st.subheader("🌲 Document Tree")
    
    if page_index.tree_root and page_index.tree_root.children:
        # Display tree structure
        def display_tree_node(node, level=0):
            """Recursively display tree node"""
            indent = "  " * level
            
            # Display node
            if level == 0:
                st.markdown(f"{indent}**📁 {node.title}**")
            else:
                st.markdown(f"{indent}📄 {node.title}")
            
            # Show details
            if node.keywords:
                keywords_str = ", ".join(node.keywords[:10])  # Show first 10
                if len(node.keywords) > 10:
                    keywords_str += f" ... and {len(node.keywords) - 10} more"
                st.markdown(f"{indent}**Keywords:** {keywords_str}")
            
            if node.start_page and node.end_page:
                st.markdown(f"{indent}**Pages:** {node.start_page}-{node.end_page}")
            
            # Display children
            if node.children:
                for child in node.children:
                    display_tree_node(child, level + 1)
        
        display_tree_node(page_index.tree_root)
    elif page_index.documents:
        # Fallback: Display documents directly
        st.info(f"📄 Displaying {len(page_index.documents)} documents")
        
        for doc_id, doc in page_index.documents.items():
            st.markdown(f"**📄 {os.path.basename(doc.source_file)}**")
            st.markdown(f"  - **Pages:** {doc.total_pages}")
            st.markdown(f"  - **Type:** {doc.file_type.value}")
            st.divider()
    else:
        st.warning("⚠ No documents in index")
    
    # Keyword Search
    st.subheader("🔍 Keyword Search")
    
    search_query = st.text_input("Search keywords:", placeholder="e.g., burger, price, menu")
    
    if search_query and page_index.page_index:
        if search_query.lower() in page_index.page_index:
            refs = page_index.page_index[search_query.lower()]
            st.markdown(f"**Found '{search_query}' in {len(refs)} location(s):**")
            
            for ref in refs[:5]:  # Show first 5
                st.markdown(f"- 📄 Document: `{ref.doc_id}`, Page {ref.page_number}")
                if ref.snippet:
                    st.markdown(f"  > {ref.snippet[:200]}")
        else:
            st.info(f"Keyword '{search_query}' not found in index")

    # Raw Index Data (collapsible)
    with st.expander("📋 View Raw Index Data"):
        st.json({
            'total_keywords': page_index.metadata.get('total_keywords', 0),
            'total_tree_nodes': page_index.metadata.get('total_tree_nodes', 0),
            'sample_keywords': list(page_index.page_index.keys())[:50] if page_index.page_index else []
        })

with tab6:
    st.header("📄 Business Profile")
    
    if not st.session_state.get('business_profile'):
        st.info("👆 Click 'Generate Business Profile with AI' in the Results tab to create a business profile")
        
        st.markdown("""
        ### What is a Business Profile?
        
        A structured digital profile containing:
        
        - **Business Information**: Name, description, location, contact, hours
        - **Product Inventory**: Products with pricing, specifications, inventory
        - **Service Inventory**: Services with pricing, itineraries, FAQs
        - **Data Provenance**: Track where each field came from
        
        ### How It Works:
        
        1. Upload business documents (PDFs, DOCX, images)
        2. Run processing pipeline (6 agents)
        3. Click "Generate Business Profile with AI"
        4. Groq AI extracts and structures the information
        5. View results here!
        """)
    else:
        profile = st.session_state.business_profile
        
        # Business Type Badge
        business_type = profile.get('business_type', 'unknown')
        type_emoji = "🏪" if business_type == 'product' else "💼" if business_type == 'service' else "🏢"
        st.markdown(f"### {type_emoji} Business Type: **{business_type.upper()}**")
        
        # Download JSON button
        profile_json = json.dumps(
            {k: v for k, v in profile.items() if not str(k).startswith('_')},
            indent=2, ensure_ascii=False, default=str
        )
        st.download_button(
            label="📥 Download Profile JSON",
            data=profile_json,
            file_name=f"business_profile_{st.session_state.job_id}.json",
            mime="application/json"
        )
        
        st.divider()
        
        # Business Info
        st.subheader("📊 Business Information")
        business_info = profile.get('business_info', {})
        
        col1, col2 = st.columns(2)
        with col1:
            if business_info.get('name'):
                st.markdown(f"**Name:** {business_info['name']}")
            if business_info.get('description'):
                st.markdown(f"**Description:** {business_info['description']}")
            if business_info.get('category'):
                st.markdown(f"**Category:** {business_info['category']}")
        
        with col2:
            location = business_info.get('location', {})
            if location:
                st.markdown("**Location:**")
                if location.get('address'):
                    st.markdown(f"  - Address: {location['address']}")
                if location.get('city'):
                    st.markdown(f"  - City: {location['city']}")
                if location.get('state'):
                    st.markdown(f"  - State: {location['state']}")
        
        # Contact Info
        contact = business_info.get('contact', {})
        if contact:
            st.markdown("**Contact:**")
            col_a, col_b = st.columns(2)
            with col_a:
                if contact.get('phone'):
                    st.markdown(f"  📞 Phone: {contact['phone']}")
                if contact.get('email'):
                    st.markdown(f"  📧 Email: {contact['email']}")
            with col_b:
                if contact.get('website'):
                    st.markdown(f"  🌐 Website: {contact['website']}")
        
        st.divider()
        
        # Products
        products = profile.get('products', [])
        if products:
            st.subheader(f"📦 Products ({len(products)})")
            for i, product in enumerate(products, 1):
                with st.expander(f"**{i}. {product.get('name', 'Product')}**"):
                    st.write(f"**Description:** {product.get('description', 'N/A')}")
                    if product.get('pricing'):
                        pricing = product['pricing']
                        st.write(f"**Price:** {pricing.get('base_price', 'N/A')} {pricing.get('currency', 'USD')}")
                    if product.get('specifications'):
                        st.write("**Specifications:**")
                        for key, value in product['specifications'].items():
                            if value:
                                st.write(f"  - {key}: {value}")
        
        st.divider()
        
        # ============== SERVICES (COMPREHENSIVE DISPLAY) ==============
        services = profile.get('services', [])
        if services:
            st.subheader(f"💼 Services ({len(services)})")
            
            # Service completeness overview
            st.markdown("**Service Completeness:**")
            for i, service in enumerate(services):
                filled = 0
                total = 13
                for field in ['name', 'description', 'category', 'pricing', 'details',
                              'itinerary', 'inclusions', 'exclusions', 'cancellation_policy',
                              'payment_policy', 'travel_info', 'faqs', 'tags']:
                    val = service.get(field)
                    if val and (not isinstance(val, (list, dict)) or len(val) > 0):
                        filled += 1
                pct = int(filled / total * 100)
                st.progress(pct / 100, text=f"{service.get('name', f'Service {i+1}')}: {pct}% ({filled}/{total} fields)")
            
            st.divider()
            
            # Render each service in detail
            for i, service in enumerate(services, 1):
                svc_name = service.get('name', f'Service {i}')
                with st.expander(f"🏔️ **{i}. {svc_name}**", expanded=(i == 1)):
                    
                    # --- Basic Info ---
                    st.markdown("#### 📋 Basic Information")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Name:** {svc_name}")
                        st.markdown(f"**Category:** {service.get('category', 'N/A')}")
                    with col2:
                        if service.get('description'):
                            st.markdown(f"**Description:** {service['description']}")
                    
                    # --- Pricing ---
                    pricing = service.get('pricing')
                    if pricing and isinstance(pricing, dict):
                        st.markdown("#### 💰 Pricing")
                        pcol1, pcol2, pcol3 = st.columns(3)
                        with pcol1:
                            bp = pricing.get('base_price')
                            curr = pricing.get('currency', 'INR')
                            st.metric("Base Price", f"{curr} {bp}" if bp else "N/A")
                        with pcol2:
                            st.markdown(f"**Price Type:** {pricing.get('price_type', 'N/A')}")
                        with pcol3:
                            dp = pricing.get('discount_price')
                            if dp:
                                st.metric("Discount Price", f"{curr} {dp}")
                    
                    # --- Trek Details ---
                    details = service.get('details')
                    if details and isinstance(details, dict):
                        st.markdown("#### 🏔️ Trek Details")
                        dcol1, dcol2, dcol3 = st.columns(3)
                        with dcol1:
                            if details.get('duration'):
                                st.markdown(f"⏱️ **Duration:** {details['duration']}")
                            if details.get('difficulty_level'):
                                diff = details['difficulty_level']
                                diff_emoji = "🟢" if 'easy' in diff.lower() else "🟡" if 'moderate' in diff.lower() else "🔴"
                                st.markdown(f"{diff_emoji} **Difficulty:** {diff}")
                        with dcol2:
                            if details.get('max_altitude'):
                                st.markdown(f"🏔️ **Max Altitude:** {details['max_altitude']}")
                            if details.get('total_distance'):
                                st.markdown(f"📏 **Distance:** {details['total_distance']}")
                        with dcol3:
                            if details.get('starting_point'):
                                st.markdown(f"📍 **Start:** {details['starting_point']}")
                            if details.get('ending_point'):
                                st.markdown(f"📍 **End:** {details['ending_point']}")
                        
                        if details.get('group_size'):
                            st.markdown(f"👥 **Group Size:** {details['group_size']}")
                        if details.get('best_time'):
                            st.markdown(f"📅 **Best Time:** {details['best_time']}")
                    
                    # --- Itinerary ---
                    itinerary = service.get('itinerary', [])
                    if itinerary and isinstance(itinerary, list) and len(itinerary) > 0:
                        st.markdown(f"#### 🗓️ Day-by-Day Itinerary ({len(itinerary)} days)")
                        
                        for day_data in itinerary:
                            if isinstance(day_data, dict):
                                day_num = day_data.get('day', '?')
                                day_title = day_data.get('title', day_data.get('description', 'N/A'))
                                day_desc = day_data.get('description', '')
                                day_alt = day_data.get('altitude', '')
                                day_dist = day_data.get('distance', '')
                                
                                header = f"**Day {day_num}: {day_title}**"
                                if day_alt:
                                    header += f" | 🏔️ {day_alt}"
                                if day_dist:
                                    header += f" | 📏 {day_dist}"
                                
                                st.markdown(header)
                                if day_desc and day_desc != day_title:
                                    st.caption(day_desc)
                                
                                # Show activities if present
                                activities = day_data.get('activities', [])
                                if activities and isinstance(activities, list):
                                    st.markdown("  " + " → ".join(activities))
                                
                                # Show meals if present
                                meals = day_data.get('meals', [])
                                if meals and isinstance(meals, list):
                                    st.markdown(f"  🍽️ Meals: {', '.join(meals)}")
                                
                                # Show accommodation if present
                                accommodation = day_data.get('accommodation')
                                if accommodation:
                                    st.markdown(f"  🏠 Stay: {accommodation}")
                    else:
                        st.markdown("#### 🗓️ Itinerary")
                        st.caption("No itinerary data extracted")
                    
                    # --- Inclusions & Exclusions ---
                    incl = service.get('inclusions', [])
                    excl = service.get('exclusions', [])
                    if incl or excl:
                        st.markdown("#### ✅ Inclusions & ❌ Exclusions")
                        icol1, icol2 = st.columns(2)
                        with icol1:
                            if incl and isinstance(incl, list):
                                st.markdown("**✅ Included:**")
                                for item in incl:
                                    st.markdown(f"  ✓ {item}")
                            else:
                                st.caption("No inclusions data")
                        with icol2:
                            if excl and isinstance(excl, list):
                                st.markdown("**❌ Excluded:**")
                                for item in excl:
                                    st.markdown(f"  ✗ {item}")
                            else:
                                st.caption("No exclusions data")
                    
                    # --- Policies ---
                    cancel_policy = service.get('cancellation_policy')
                    pay_policy = service.get('payment_policy')
                    if cancel_policy or pay_policy:
                        st.markdown("#### 📜 Policies")
                        if cancel_policy:
                            st.markdown(f"**Cancellation Policy:** {cancel_policy}")
                        if pay_policy:
                            st.markdown(f"**Payment Policy:** {pay_policy}")
                    
                    # --- Travel Info ---
                    travel = service.get('travel_info')
                    if travel and isinstance(travel, dict) and any(travel.values()):
                        st.markdown("#### 🚂 Travel Information")
                        if travel.get('how_to_reach'):
                            st.markdown(f"**How to Reach:** {travel['how_to_reach']}")
                        tcol1, tcol2 = st.columns(2)
                        with tcol1:
                            if travel.get('nearest_railway'):
                                st.markdown(f"🚆 **Railway:** {travel['nearest_railway']}")
                        with tcol2:
                            if travel.get('nearest_airport'):
                                st.markdown(f"✈️ **Airport:** {travel['nearest_airport']}")
                        landmarks = travel.get('nearby_landmarks', [])
                        if landmarks and isinstance(landmarks, list):
                            st.markdown(f"📍 **Landmarks:** {', '.join(landmarks)}")
                    
                    # --- FAQs ---
                    faqs = service.get('faqs', [])
                    if faqs and isinstance(faqs, list) and len(faqs) > 0:
                        st.markdown(f"#### ❓ FAQs ({len(faqs)})")
                        for faq in faqs:
                            if isinstance(faq, dict):
                                st.markdown(f"**Q: {faq.get('question', 'N/A')}**")
                                st.markdown(f"A: {faq.get('answer', 'N/A')}")
                    
                    # --- What to Carry ---
                    carry = service.get('what_to_carry', [])
                    if carry and isinstance(carry, list) and len(carry) > 0:
                        st.markdown("#### 🎒 What to Carry")
                        ccol1, ccol2 = st.columns(2)
                        half = len(carry) // 2 + 1
                        with ccol1:
                            for item in carry[:half]:
                                st.markdown(f"  • {item}")
                        with ccol2:
                            for item in carry[half:]:
                                st.markdown(f"  • {item}")
                    
                    # --- Risk & Safety ---
                    risk = service.get('risk_and_safety')
                    if risk:
                        st.markdown("#### ⚠️ Risk & Safety")
                        st.warning(risk)
                    
                    # --- Tags ---
                    tags = service.get('tags', [])
                    if tags and isinstance(tags, list):
                        st.markdown("#### 🏷️ Tags")
                        st.markdown(" ".join([f"`{tag}`" for tag in tags]))
        else:
            st.info("No services extracted")
        
        st.divider()
        
        # Metadata
        st.subheader("📋 Extraction Metadata")
        metadata = profile.get('extraction_metadata', {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Processing Time", f"{metadata.get('processing_time', 0):.2f}s")
        with col2:
            st.metric("Source Files", metadata.get('source_files_count', 0))
        with col3:
            st.metric("Confidence", f"{metadata.get('confidence_score', 0):.0%}")
        with col4:
            st.metric("LLM Calls", metadata.get('llm_calls_made', 0))
        
        st.markdown(f"**Method:** {metadata.get('extraction_method', 'unknown')}")
        st.markdown(f"**Version:** {metadata.get('version', '1.0')}")
        
        # Raw JSON viewer
        with st.expander("🔍 View Raw Profile JSON"):
            st.json(profile)

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <b>Digi-Biz</b> - Agentic Business Digitization Framework<br>
    Powered by Groq Vision (Llama-4-Scout) • Ollama Fallback • Multi-Agent Pipeline
</div>
""", unsafe_allow_html=True)
