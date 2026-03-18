# System Architecture: Agentic Business Digitization Framework

## Architecture Overview

### System Philosophy
The architecture follows a **multi-agent microservices pattern** where specialized agents collaborate to transform unstructured documents into structured business profiles. Each agent has a single responsibility and communicates through well-defined interfaces.

### Core Principles
1. **Separation of Concerns**: Each agent handles one aspect of processing
2. **Fail Gracefully**: Missing information results in empty fields, not errors
3. **Deterministic Parsing**: Scripts handle extraction, LLMs handle intelligence
4. **Data Provenance**: Track source of every extracted field
5. **Extensibility**: Easy to add new document types or agents

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ZIP Upload   │  │ Profile View │  │ Edit Interface│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Orchestration Layer                         │
│         ┌────────────────────────────────┐                  │
│         │  BusinessDigitizationPipeline  │                  │
│         │  - Workflow Coordination       │                  │
│         │  - Error Handling              │                  │
│         │  - Progress Tracking           │                  │
│         └────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│File Discovery│   │Document Parse│   │Media Extract │
│    Agent     │   │    Agent     │   │    Agent     │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│Table Extract │   │Vision/Image  │   │Schema Mapping│
│    Agent     │   │    Agent     │   │    Agent     │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Indexing & RAG Layer                      │
│         ┌────────────────────────────────┐                  │
│         │     Page Index (Vectorless)    │                  │
│         │  - Document-level indexing     │                  │
│         │  - Page-level context          │                  │
│         │  - Metadata storage            │                  │
│         └────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Validation Layer                           │
│         ┌────────────────────────────────┐                  │
│         │      Schema Validator          │                  │
│         │  - Field validation            │                  │
│         │  - Completeness scoring        │                  │
│         │  - Data quality checks         │                  │
│         └────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ File Storage │  │ Index Store  │  │ Profile Store│      │
│  │ (Filesystem) │  │ (SQLite/JSON)│  │    (JSON)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. User Interface Layer

#### 1.1 Upload Component
**Purpose**: Accept ZIP files from users

**Technology**: React with react-dropzone

**Responsibilities**:
- Drag-and-drop file upload
- ZIP validation (size, format)
- Upload progress tracking
- Error messaging

**Interface**:
```typescript
interface UploadComponentProps {
  onUploadComplete: (jobId: string) => void;
  maxFileSize: number; // in MB
  acceptedFormats: string[];
}
```

#### 1.2 Profile Viewer
**Purpose**: Display generated business profiles

**Technology**: React with dynamic rendering

**Responsibilities**:
- Conditional rendering based on business type
- Product inventory display
- Service inventory display
- Media gallery
- Metadata presentation

**Interface**:
```typescript
interface BusinessProfile {
  businessInfo: BusinessInfo;
  products?: Product[];
  services?: Service[];
  media: MediaFile[];
  metadata: ProfileMetadata;
}
```

#### 1.3 Edit Interface
**Purpose**: Allow post-digitization editing

**Technology**: React Hook Form with Zod validation

**Responsibilities**:
- Form-based editing
- Field validation
- Media upload/removal
- Save/discard changes
- Version history

### 2. Orchestration Layer

#### BusinessDigitizationPipeline
**Purpose**: Coordinate multi-agent workflow

**Technology**: Python async/await with concurrent processing

**Core Workflow**:
```python
class BusinessDigitizationPipeline:
    def __init__(self):
        self.file_discovery = FileDiscoveryAgent()
        self.parsing = DocumentParsingAgent()
        self.table_extraction = TableExtractionAgent()
        self.media_extraction = MediaExtractionAgent()
        self.vision = VisionAgent()
        self.indexing = IndexingAgent()
        self.schema_mapping = SchemaMappingAgent()
        self.validation = ValidationAgent()
    
    async def process(self, zip_path: str) -> BusinessProfile:
        try:
            # Phase 1: Discover files
            files = await self.file_discovery.discover(zip_path)
            
            # Phase 2: Parse documents (parallel)
            parsed_docs = await asyncio.gather(*[
                self.parsing.parse(f) for f in files.documents
            ])
            
            # Phase 3: Extract tables (parallel)
            tables = await asyncio.gather(*[
                self.table_extraction.extract(doc) for doc in parsed_docs
            ])
            
            # Phase 4: Extract media
            media = await self.media_extraction.extract_all(
                parsed_docs, files.media_files
            )
            
            # Phase 5: Vision processing for images
            image_metadata = await asyncio.gather(*[
                self.vision.analyze(img) for img in media.images
            ])
            
            # Phase 6: Build page index
            page_index = await self.indexing.build_index(
                parsed_docs, tables, media
            )
            
            # Phase 7: LLM-assisted schema mapping
            profile = await self.schema_mapping.map_to_schema(
                page_index, image_metadata
            )
            
            # Phase 8: Validation
            validated_profile = await self.validation.validate(profile)
            
            return validated_profile
            
        except Exception as e:
            self.handle_error(e)
            raise
```

**Error Handling Strategy**:
- Graceful degradation per agent
- Detailed error logging
- Partial results on failure
- User-friendly error messages

### 3. Agent Layer

#### 3.1 File Discovery Agent
**Purpose**: Extract and classify files from ZIP

**Input**: ZIP file path

**Output**: Classified file collection

**Implementation**:
```python
class FileDiscoveryAgent:
    def discover(self, zip_path: str) -> FileCollection:
        """
        Extract ZIP and classify files by type
        """
        extracted_files = self.extract_zip(zip_path)
        
        return FileCollection(
            documents=self.classify_documents(extracted_files),
            media_files=self.classify_media(extracted_files),
            spreadsheets=self.classify_spreadsheets(extracted_files),
            directory_structure=self.map_structure(extracted_files)
        )
    
    def classify_file(self, file_path: str) -> FileType:
        """
        Determine file type using mimetypes and extension
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return self.mime_to_file_type(mime_type)
```

**Supported File Types**:
- Documents: PDF, DOC, DOCX
- Spreadsheets: XLS, XLSX, CSV
- Images: JPG, PNG, GIF, WEBP
- Videos: MP4, AVI, MOV

#### 3.2 Document Parsing Agent
**Purpose**: Extract text and structure from documents

**Input**: Document file path

**Output**: Parsed document with metadata

**Implementation**:
```python
class DocumentParsingAgent:
    def __init__(self):
        self.parsers = {
            FileType.PDF: PDFParser(),
            FileType.DOCX: DOCXParser(),
            FileType.DOC: DOCParser()
        }
    
    def parse(self, file_path: str) -> ParsedDocument:
        """
        Factory pattern to select appropriate parser
        """
        file_type = self.detect_type(file_path)
        parser = self.parsers.get(file_type)
        
        if not parser:
            raise UnsupportedFileTypeError(file_type)
        
        return parser.parse(file_path)
```

**PDF Parser**:
```python
class PDFParser:
    def parse(self, pdf_path: str) -> ParsedDocument:
        """
        Extract text, preserve structure, identify sections
        """
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for i, page in enumerate(pdf.pages):
                pages.append(Page(
                    number=i + 1,
                    text=page.extract_text(),
                    tables=page.extract_tables(),
                    images=self.extract_images(page),
                    metadata=self.extract_page_metadata(page)
                ))
            
            return ParsedDocument(
                source=pdf_path,
                pages=pages,
                total_pages=len(pages),
                metadata=self.extract_doc_metadata(pdf)
            )
```

**DOCX Parser**:
```python
class DOCXParser:
    def parse(self, docx_path: str) -> ParsedDocument:
        """
        Extract paragraphs, tables, images with structure
        """
        doc = Document(docx_path)
        
        elements = []
        for elem in iter_block_items(doc):
            if isinstance(elem, Paragraph):
                elements.append(TextElement(
                    text=elem.text,
                    style=elem.style.name,
                    formatting=self.extract_formatting(elem)
                ))
            elif isinstance(elem, Table):
                elements.append(TableElement(
                    data=self.parse_table(elem),
                    style=elem.style.name
                ))
        
        return ParsedDocument(
            source=docx_path,
            elements=elements,
            images=self.extract_images(doc),
            metadata=self.extract_metadata(doc)
        )
```

#### 3.3 Table Extraction Agent
**Purpose**: Identify and structure table data

**Input**: Parsed document

**Output**: Structured table data

**Implementation**:
```python
class TableExtractionAgent:
    def extract(self, parsed_doc: ParsedDocument) -> List[StructuredTable]:
        """
        Convert raw tables to structured format
        """
        tables = []
        for page in parsed_doc.pages:
            for raw_table in page.tables:
                structured = self.structure_table(raw_table)
                if self.is_valid_table(structured):
                    tables.append(StructuredTable(
                        data=structured,
                        context=self.extract_context(page, raw_table),
                        type=self.classify_table(structured),
                        source_page=page.number
                    ))
        return tables
    
    def classify_table(self, table: List[List[str]]) -> TableType:
        """
        Identify table purpose (pricing, itinerary, specs, etc.)
        """
        headers = table[0] if table else []
        
        if self.has_price_columns(headers):
            return TableType.PRICING
        elif self.has_time_columns(headers):
            return TableType.ITINERARY
        elif self.has_spec_columns(headers):
            return TableType.SPECIFICATIONS
        else:
            return TableType.GENERAL
```

**Table Types**:
- Pricing tables (product/service pricing)
- Itinerary tables (schedules, timelines)
- Specification tables (product specs)
- Inventory tables (stock levels)
- General tables (miscellaneous data)

#### 3.4 Media Extraction Agent
**Purpose**: Extract and organize media files

**Input**: Parsed documents + standalone media files

**Output**: Organized media collection

**Implementation**:
```python
class MediaExtractionAgent:
    def extract_all(
        self, 
        parsed_docs: List[ParsedDocument],
        media_files: List[str]
    ) -> MediaCollection:
        """
        Extract embedded + standalone media
        """
        embedded_images = []
        for doc in parsed_docs:
            embedded_images.extend(self.extract_embedded(doc))
        
        standalone_media = self.process_standalone(media_files)
        
        return MediaCollection(
            images=embedded_images + standalone_media.images,
            videos=standalone_media.videos,
            metadata=self.generate_metadata_all()
        )
    
    def extract_embedded(self, doc: ParsedDocument) -> List[Image]:
        """
        Extract images from PDFs and DOCX
        """
        if doc.source.endswith('.pdf'):
            return self.extract_from_pdf(doc)
        elif doc.source.endswith('.docx'):
            return self.extract_from_docx(doc)
        return []
```

#### 3.5 Vision Agent
**Purpose**: Analyze images using vision-language models

**Input**: Image files

**Output**: Descriptive metadata

**Implementation**:
```python
class VisionAgent:
    def __init__(self):
        from ollama import Client
        self.ollama_client = Client(host='http://localhost:11434')
        self.model = "qwen3.5:0.8b"

    async def analyze(self, image: Image) -> ImageMetadata:
        """
        Generate descriptive metadata using Qwen3.5:0.8B vision (via Ollama)
        """
        # Call Qwen via Ollama with image
        response = self.ollama_client.chat(
            model=self.model,
            messages=[{
                "role": "user",
                "content": self.get_vision_prompt(),
                "images": [image.path]
            }]
        )

        return ImageMetadata(
            description=response['message']['content'],
            suggested_category=self.extract_category(response),
            tags=self.extract_tags(response),
            is_product_image=self.is_product(response),
            confidence=0.85
        )

    def get_vision_prompt(self) -> str:
        return """
        Analyze this image and provide:
        1. A brief description (2-3 sentences)
        2. Category (product, service, food, destination, other)
        3. Relevant tags (comma-separated)
        4. Is this a product image? (yes/no)

        Format your response as JSON.
        """
```

#### 3.6 Schema Mapping Agent
**Purpose**: Map extracted data to business profile schema

**Input**: Page index, parsed data, media metadata

**Output**: Structured business profile

**Implementation**:
```python
class SchemaMappingAgent:
    def __init__(self):
        from openai import OpenAI
        # Groq API endpoint
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.model = "gpt-oss-120b"

    async def map_to_schema(
        self,
        page_index: PageIndex,
        image_metadata: List[ImageMetadata]
    ) -> BusinessProfile:
        """
        Use Groq (gpt-oss-120b) to intelligently map data to schema fields
        """
        # Step 1: Classify business type
        business_type = await self.classify_business_type(page_index)

        # Step 2: Extract business info
        business_info = await self.extract_business_info(page_index)

        # Step 3: Extract products or services
        if business_type in [BusinessType.PRODUCT, BusinessType.MIXED]:
            products = await self.extract_products(page_index, image_metadata)
        else:
            products = None

        if business_type in [BusinessType.SERVICE, BusinessType.MIXED]:
            services = await self.extract_services(page_index, image_metadata)
        else:
            services = None

        return BusinessProfile(
            business_info=business_info,
            products=products,
            services=services,
            business_type=business_type,
            extraction_metadata=self.generate_metadata()
        )

    async def extract_business_info(self, page_index: PageIndex) -> BusinessInfo:
        """
        Extract core business information using Groq
        """
        context = page_index.get_relevant_context([
            "business name",
            "description",
            "hours",
            "location",
            "contact"
        ])

        prompt = self.build_extraction_prompt(context, "business_info")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        extracted_data = json.loads(response.choices[0].message.content)

        return BusinessInfo(
            description=extracted_data.get("description", ""),
            working_hours=extracted_data.get("working_hours", ""),
            location=extracted_data.get("location", {}),
            contact=extracted_data.get("contact", {}),
            payment_methods=extracted_data.get("payment_methods", []),
            tags=extracted_data.get("tags", [])
        )
```

### 4. Indexing & RAG Layer

#### Page Index (Vectorless RAG)
**Purpose**: Enable efficient context retrieval without embeddings

**Architecture**:
```python
class PageIndex:
    """
    Vectorless retrieval using inverted index on pages
    """
    def __init__(self):
        self.documents: Dict[str, ParsedDocument] = {}
        self.page_index: Dict[str, List[PageReference]] = {}
        self.table_index: Dict[str, List[TableReference]] = {}
        self.media_index: Dict[str, List[MediaReference]] = {}
    
    def build_index(self, parsed_docs: List[ParsedDocument]) -> None:
        """
        Create inverted index for fast lookup
        """
        for doc in parsed_docs:
            self.documents[doc.id] = doc
            
            for page in doc.pages:
                # Index by keywords
                keywords = self.extract_keywords(page.text)
                for keyword in keywords:
                    if keyword not in self.page_index:
                        self.page_index[keyword] = []
                    
                    self.page_index[keyword].append(PageReference(
                        doc_id=doc.id,
                        page_number=page.number,
                        context=self.extract_snippet(page.text, keyword)
                    ))
    
    def get_relevant_context(self, query_terms: List[str]) -> str:
        """
        Retrieve relevant pages/context for given terms
        """
        relevant_pages = set()
        
        for term in query_terms:
            if term.lower() in self.page_index:
                relevant_pages.update(self.page_index[term.lower()])
        
        # Rank by relevance
        ranked = self.rank_pages(relevant_pages, query_terms)
        
        # Build context from top pages
        return self.build_context(ranked[:5])
```

**Advantages**:
- No embedding generation overhead
- Fast exact keyword matching
- Easy to debug and understand
- Low memory footprint
- Deterministic results

### 5. Validation Layer

#### Schema Validator
**Purpose**: Ensure data quality and completeness

**Implementation**:
```python
class SchemaValidator:
    def validate(self, profile: BusinessProfile) -> ValidationResult:
        """
        Validate business profile against schema rules
        """
        errors = []
        warnings = []
        
        # Validate business info
        if not profile.business_info.description:
            warnings.append("Missing business description")
        
        if profile.business_info.contact:
            if not self.is_valid_email(profile.business_info.contact.email):
                errors.append("Invalid email format")
        
        # Validate products
        if profile.products:
            for i, product in enumerate(profile.products):
                product_errors = self.validate_product(product)
                if product_errors:
                    errors.extend([f"Product {i+1}: {e}" for e in product_errors])
        
        # Calculate completeness score
        completeness = self.calculate_completeness(profile)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            completeness_score=completeness,
            profile=profile
        )
    
    def calculate_completeness(self, profile: BusinessProfile) -> float:
        """
        Score based on populated vs empty fields
        """
        total_fields = self.count_schema_fields()
        populated_fields = self.count_populated_fields(profile)
        
        return populated_fields / total_fields
```

## Data Flow

### End-to-End Processing Flow
```
User uploads ZIP
    ↓
FileDiscoveryAgent extracts and classifies files
    ↓
DocumentParsingAgent parses each document (parallel)
    ↓
TableExtractionAgent extracts tables from parsed docs
    ↓
MediaExtractionAgent extracts embedded + standalone media
    ↓
VisionAgent analyzes images (parallel)
    ↓
IndexingAgent builds page index
    ↓
SchemaMappingAgent uses Groq + page index to map fields
    ↓
ValidationAgent validates and scores profile
    ↓
BusinessProfile saved as JSON
    ↓
UI renders profile dynamically
```

## Technology Stack

### Backend
- **Language**: Python 3.10+
- **Async Framework**: asyncio
- **Document Parsing**: pdfplumber, python-docx, openpyxl
- **Image Processing**: Pillow, pdf2image
- **LLM Integration**: Groq API (gpt-oss-120b), Ollama (Qwen3.5:0.8B for vision)
- **Validation**: Pydantic
- **Testing**: pytest, pytest-asyncio

### Frontend
- **Framework**: React 18 with TypeScript
- **State Management**: Zustand
- **UI Components**: shadcn/ui
- **Forms**: React Hook Form + Zod
- **File Upload**: react-dropzone
- **Build Tool**: Vite

### Storage
- **Documents**: Filesystem with organized structure
- **Index**: SQLite or JSON-based lightweight store
- **Profiles**: JSON files with schema validation

## Deployment Architecture

### Development Environment
```
/project
├── backend/
│   ├── agents/
│   ├── parsers/
│   ├── indexing/
│   ├── validation/
│   └── main.py
├── frontend/
│   ├── src/
│   ├── components/
│   └── pages/
├── storage/
│   ├── uploads/
│   ├── extracted/
│   ├── profiles/
│   └── index/
└── tests/
```

### Production Considerations
- Docker containerization for consistent deployment
- Environment variable management for API keys
- Logging and monitoring integration
- Error tracking (Sentry)
- Performance monitoring

## Security Considerations

1. **File Upload Security**
   - Virus scanning on uploaded ZIPs
   - Size limits (500MB max)
   - Type validation
   - Sandboxed extraction

2. **API Key Management**
   - Environment variables only
   - Never commit keys
   - Rotate periodically

3. **Data Privacy**
   - No data sent to third parties except Groq API
   - Vision processing is fully local (Ollama)
   - User data isolated by session
   - Option to delete processed files

## Performance Optimization

1. **Parallel Processing**
   - Parse documents concurrently
   - Process images in parallel
   - Async LLM calls

2. **Caching**
   - Cache parsed documents
   - Reuse vision analysis results
   - Index caching

3. **Resource Management**
   - Stream large files
   - Cleanup temporary files
   - Memory limits for document processing

## Monitoring & Observability

### Metrics to Track
- Processing time per phase
- Success/failure rates
- LLM token usage
- Extraction accuracy (sampled)
- User satisfaction scores

### Logging Strategy
- Structured JSON logging
- Log levels: DEBUG, INFO, WARN, ERROR
- Contextual information (job_id, file_name)
- Performance timings

## Conclusion

This architecture provides a robust, scalable foundation for the agentic business digitization system. The multi-agent approach allows for:
- Independent development and testing of each component
- Graceful handling of failures
- Easy extension with new capabilities
- Clear data provenance and debugging

The vectorless RAG approach keeps the system lightweight while the LLM integration provides intelligent field mapping and classification.
