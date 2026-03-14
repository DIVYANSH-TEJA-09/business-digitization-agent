# Agent Pipeline: Agentic Business Digitization Framework

## Pipeline Overview

The agentic pipeline consists of specialized agents that collaborate to transform unstructured documents into structured business profiles. Each agent operates independently but communicates through standardized interfaces.

## Agent Taxonomy

### Deterministic Agents
These agents use rule-based, algorithmic approaches for reliable, consistent results:
- File Discovery Agent
- Document Parsing Agent
- Table Extraction Agent
- Media Extraction Agent

### AI-Powered Agents
These agents leverage LLMs for intelligent processing:
- Vision Agent
- Schema Mapping Agent
- Classification Agent

### Coordination Agents
These agents manage workflows and validation:
- Orchestration Agent (Pipeline Coordinator)
- Validation Agent
- Indexing Agent

## Detailed Agent Specifications

### 1. File Discovery Agent

**Responsibility**: Extract ZIP and classify all files by type

**Input Contract**:
```python
@dataclass
class DiscoveryInput:
    zip_path: str
    extract_dir: str
    job_id: str
```

**Output Contract**:
```python
@dataclass
class FileCollection:
    documents: List[DocumentFile]  # PDFs, DOCX, DOC
    spreadsheets: List[SpreadsheetFile]  # XLSX, XLS, CSV
    images: List[ImageFile]  # JPG, PNG, GIF
    videos: List[VideoFile]  # MP4, AVI, MOV
    unknown: List[UnknownFile]
    directory_structure: DirectoryTree
    metadata: DiscoveryMetadata
```

**Processing Logic**:
```python
class FileDiscoveryAgent:
    """
    Discovers and classifies files from uploaded ZIP
    """
    
    def discover(self, input: DiscoveryInput) -> FileCollection:
        # Step 1: Validate ZIP file
        if not self.validate_zip(input.zip_path):
            raise InvalidZIPError("Corrupted or invalid ZIP file")
        
        # Step 2: Extract with safety checks
        extracted_files = self.safe_extract(
            input.zip_path, 
            input.extract_dir
        )
        
        # Step 3: Build directory tree
        dir_tree = self.build_directory_tree(extracted_files)
        
        # Step 4: Classify each file
        classified = self.classify_files(extracted_files)
        
        # Step 5: Generate metadata
        metadata = self.generate_metadata(classified)
        
        return FileCollection(
            documents=classified.documents,
            spreadsheets=classified.spreadsheets,
            images=classified.images,
            videos=classified.videos,
            unknown=classified.unknown,
            directory_structure=dir_tree,
            metadata=metadata
        )
    
    def classify_file(self, file_path: Path) -> FileType:
        """
        Multi-strategy file classification
        """
        # Strategy 1: MIME type detection
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            file_type = self.mime_to_file_type(mime_type)
            if file_type != FileType.UNKNOWN:
                return file_type
        
        # Strategy 2: Extension-based
        extension = file_path.suffix.lower()
        if extension in self.EXTENSION_MAP:
            return self.EXTENSION_MAP[extension]
        
        # Strategy 3: Magic number detection
        return self.detect_by_magic_number(file_path)
    
    def safe_extract(self, zip_path: str, extract_dir: str) -> List[Path]:
        """
        Secure ZIP extraction with validation
        """
        extracted = []
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Check for zip bombs
            self.validate_zip_safety(zip_ref)
            
            # Extract with path sanitization
            for member in zip_ref.namelist():
                # Prevent path traversal attacks
                safe_path = self.sanitize_path(member)
                
                if safe_path:
                    zip_ref.extract(member, extract_dir)
                    extracted.append(Path(extract_dir) / safe_path)
        
        return extracted
```

**Error Handling**:
- Corrupted ZIP → Raise clear error
- Unsupported file types → Mark as unknown
- Path traversal attempts → Sanitize and log
- Extraction failures → Partial success with warnings

**Performance**: <2 seconds for typical business folders (10-50 files)

---

### 2. Document Parsing Agent

**Responsibility**: Extract text and structure from documents

**Input Contract**:
```python
@dataclass
class ParseInput:
    file_path: str
    file_type: FileType
    job_id: str
```

**Output Contract**:
```python
@dataclass
class ParsedDocument:
    doc_id: str
    source_file: str
    file_type: FileType
    pages: List[Page]
    total_pages: int
    metadata: DocumentMetadata
    parsing_errors: List[str]
```

**Processing Logic**:
```python
class DocumentParsingAgent:
    """
    Factory-based document parser with fallback strategies
    """
    
    def __init__(self):
        self.parsers = {
            FileType.PDF: PDFParser(),
            FileType.DOCX: DOCXParser(),
            FileType.DOC: DOCParser(),
        }
    
    async def parse(self, input: ParseInput) -> ParsedDocument:
        """
        Parse document using appropriate parser
        """
        parser = self.parsers.get(input.file_type)
        
        if not parser:
            raise UnsupportedFileTypeError(
                f"No parser available for {input.file_type}"
            )
        
        try:
            # Primary parsing attempt
            parsed = await parser.parse(input.file_path)
            return parsed
            
        except Exception as e:
            # Fallback parsing strategy
            logger.warning(f"Primary parser failed: {e}")
            return await self.fallback_parse(input)
    
    async def fallback_parse(self, input: ParseInput) -> ParsedDocument:
        """
        Attempt alternative parsing methods
        """
        if input.file_type == FileType.PDF:
            # Fallback 1: Try OCR if text extraction fails
            return await self.ocr_fallback(input.file_path)
        elif input.file_type == FileType.DOCX:
            # Fallback 2: Try converting to text
            return await self.text_conversion_fallback(input.file_path)
        else:
            raise ParsingError(f"All parsing strategies failed for {input.file_path}")

class PDFParser:
    """
    PDF parsing with table and image extraction
    """
    
    async def parse(self, pdf_path: str) -> ParsedDocument:
        pages = []
        errors = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    try:
                        pages.append(await self.parse_page(page, i + 1))
                    except Exception as e:
                        errors.append(f"Page {i+1}: {str(e)}")
                        logger.error(f"Failed to parse page {i+1}: {e}")
        
        except Exception as e:
            raise PDFParsingError(f"Failed to open PDF: {e}")
        
        return ParsedDocument(
            doc_id=self.generate_doc_id(pdf_path),
            source_file=pdf_path,
            file_type=FileType.PDF,
            pages=pages,
            total_pages=len(pages),
            metadata=self.extract_metadata(pdf_path),
            parsing_errors=errors
        )
    
    async def parse_page(self, page, page_num: int) -> Page:
        """
        Extract all content from a single page
        """
        return Page(
            number=page_num,
            text=page.extract_text() or "",
            tables=page.extract_tables() or [],
            images=await self.extract_images(page),
            width=page.width,
            height=page.height,
            metadata=self.extract_page_metadata(page)
        )
    
    async def extract_images(self, page) -> List[ImageInfo]:
        """
        Extract embedded images from PDF page
        """
        images = []
        
        if hasattr(page, 'images'):
            for i, img in enumerate(page.images):
                try:
                    image_data = self.extract_image_data(img)
                    images.append(ImageInfo(
                        index=i,
                        bbox=img.get('bbox'),
                        width=img.get('width'),
                        height=img.get('height'),
                        data=image_data
                    ))
                except Exception as e:
                    logger.warning(f"Failed to extract image {i}: {e}")
        
        return images

class DOCXParser:
    """
    DOCX parsing with structure preservation
    """
    
    async def parse(self, docx_path: str) -> ParsedDocument:
        doc = Document(docx_path)
        
        elements = []
        for elem in iter_block_items(doc):
            if isinstance(elem, Paragraph):
                elements.append(self.parse_paragraph(elem))
            elif isinstance(elem, Table):
                elements.append(self.parse_table(elem))
        
        return ParsedDocument(
            doc_id=self.generate_doc_id(docx_path),
            source_file=docx_path,
            file_type=FileType.DOCX,
            pages=[Page(
                number=1,
                text=self.elements_to_text(elements),
                elements=elements,
                metadata={}
            )],
            total_pages=1,
            metadata=self.extract_metadata(doc),
            parsing_errors=[]
        )
```

**Parser-Specific Strategies**:

**PDF Parser**:
- Primary: pdfplumber for text + tables
- Fallback: PyPDF2 for corrupted PDFs
- Final: OCR with Tesseract for scanned PDFs

**DOCX Parser**:
- Primary: python-docx for structured parsing
- Fallback: unzip and parse XML directly
- Final: Convert to text and parse

**Error Recovery**:
- Page-level errors don't fail entire document
- Corrupted pages marked and skipped
- Warnings logged for manual review

---

### 3. Table Extraction Agent

**Responsibility**: Detect, extract, and structure table data

**Input Contract**:
```python
@dataclass
class TableExtractionInput:
    parsed_doc: ParsedDocument
    job_id: str
```

**Output Contract**:
```python
@dataclass
class StructuredTable:
    table_id: str
    source_doc: str
    source_page: int
    headers: List[str]
    rows: List[List[str]]
    table_type: TableType
    context: str  # Surrounding text
    confidence: float
    metadata: TableMetadata
```

**Processing Logic**:
```python
class TableExtractionAgent:
    """
    Intelligent table extraction and classification
    """
    
    async def extract(self, input: TableExtractionInput) -> List[StructuredTable]:
        """
        Extract and classify all tables from document
        """
        tables = []
        
        for page in input.parsed_doc.pages:
            if hasattr(page, 'tables') and page.tables:
                for raw_table in page.tables:
                    structured = self.structure_table(raw_table)
                    
                    if self.is_valid_table(structured):
                        classified = await self.classify_table(
                            structured, 
                            page.text
                        )
                        tables.append(classified)
        
        return tables
    
    def structure_table(self, raw_table: List[List]) -> StructuredTable:
        """
        Convert raw table to structured format
        """
        # Clean and normalize data
        cleaned = self.clean_table_data(raw_table)
        
        # Detect headers
        headers = self.detect_headers(cleaned)
        
        # Extract rows
        rows = cleaned[1:] if headers else cleaned
        
        return StructuredTable(
            table_id=self.generate_table_id(),
            headers=headers,
            rows=rows,
            table_type=TableType.UNKNOWN,
            confidence=0.0,
            metadata={}
        )
    
    async def classify_table(
        self, 
        table: StructuredTable, 
        context: str
    ) -> StructuredTable:
        """
        Classify table by analyzing headers and content
        """
        # Rule-based classification
        if self.is_pricing_table(table):
            table.table_type = TableType.PRICING
            table.confidence = 0.9
        elif self.is_itinerary_table(table):
            table.table_type = TableType.ITINERARY
            table.confidence = 0.85
        elif self.is_specification_table(table):
            table.table_type = TableType.SPECIFICATIONS
            table.confidence = 0.8
        else:
            # LLM-assisted classification for ambiguous cases
            table = await self.llm_classify_table(table, context)
        
        return table
    
    def is_pricing_table(self, table: StructuredTable) -> bool:
        """
        Detect pricing tables by headers and content patterns
        """
        headers_lower = [h.lower() for h in table.headers]
        
        price_keywords = ['price', 'cost', 'rate', 'amount', 'fee', 'charge']
        has_price_column = any(
            any(keyword in header for keyword in price_keywords)
            for header in headers_lower
        )
        
        # Check if rows contain currency symbols
        has_currency = self.contains_currency_symbols(table.rows)
        
        return has_price_column or has_currency
    
    def is_itinerary_table(self, table: StructuredTable) -> bool:
        """
        Detect itinerary/schedule tables
        """
        headers_lower = [h.lower() for h in table.headers]
        
        time_keywords = ['day', 'time', 'date', 'schedule', 'itinerary']
        has_time_column = any(
            any(keyword in header for keyword in time_keywords)
            for header in headers_lower
        )
        
        # Check for time patterns in content
        has_time_data = self.contains_time_patterns(table.rows)
        
        return has_time_column or has_time_data
```

**Table Type Detection Rules**:

| Table Type | Detection Criteria |
|-----------|-------------------|
| Pricing | Headers: price, cost, rate; Currency symbols: $, €, ₹ |
| Itinerary | Headers: day, time, date; Time patterns: 9:00 AM, Day 1 |
| Specifications | Headers: spec, feature, dimension; Technical terms |
| Inventory | Headers: stock, quantity, available; Numeric values |
| General | No specific pattern detected |

---

### 4. Media Extraction Agent

**Responsibility**: Extract and organize all media files

**Input Contract**:
```python
@dataclass
class MediaExtractionInput:
    parsed_docs: List[ParsedDocument]
    standalone_media: List[str]  # Image/video files
    job_id: str
```

**Output Contract**:
```python
@dataclass
class MediaCollection:
    images: List[ExtractedImage]
    videos: List[ExtractedVideo]
    total_count: int
    extraction_summary: MediaSummary
```

**Processing Logic**:
```python
class MediaExtractionAgent:
    """
    Extract embedded and standalone media
    """
    
    async def extract_all(
        self, 
        input: MediaExtractionInput
    ) -> MediaCollection:
        """
        Parallel extraction from documents and standalone files
        """
        # Extract embedded images from documents
        embedded_tasks = [
            self.extract_from_document(doc) 
            for doc in input.parsed_docs
        ]
        embedded_results = await asyncio.gather(*embedded_tasks)
        embedded_images = [img for result in embedded_results for img in result]
        
        # Process standalone media files
        standalone_images = await self.process_standalone_images(
            input.standalone_media
        )
        
        standalone_videos = await self.process_standalone_videos(
            input.standalone_media
        )
        
        # Combine and deduplicate
        all_images = self.deduplicate_images(
            embedded_images + standalone_images
        )
        
        return MediaCollection(
            images=all_images,
            videos=standalone_videos,
            total_count=len(all_images) + len(standalone_videos),
            extraction_summary=self.generate_summary(all_images, standalone_videos)
        )
    
    async def extract_from_document(
        self, 
        doc: ParsedDocument
    ) -> List[ExtractedImage]:
        """
        Extract embedded images based on document type
        """
        if doc.file_type == FileType.PDF:
            return await self.extract_from_pdf(doc)
        elif doc.file_type == FileType.DOCX:
            return await self.extract_from_docx(doc)
        else:
            return []
    
    async def extract_from_pdf(
        self, 
        doc: ParsedDocument
    ) -> List[ExtractedImage]:
        """
        Extract images from PDF using pdf2image
        """
        images = []
        
        with pdfplumber.open(doc.source_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_images = self.extract_images_from_page(page, page_num)
                images.extend(page_images)
        
        return images
    
    def deduplicate_images(
        self, 
        images: List[ExtractedImage]
    ) -> List[ExtractedImage]:
        """
        Remove duplicate images using perceptual hashing
        """
        seen_hashes = set()
        unique_images = []
        
        for img in images:
            img_hash = self.calculate_image_hash(img)
            
            if img_hash not in seen_hashes:
                seen_hashes.add(img_hash)
                unique_images.append(img)
        
        return unique_images
```

---

### 5. Vision Agent

**Responsibility**: Analyze images using vision-language models

**Input Contract**:
```python
@dataclass
class VisionAnalysisInput:
    image: ExtractedImage
    context: str  # Surrounding text from document
    job_id: str
```

**Output Contract**:
```python
@dataclass
class ImageAnalysis:
    description: str
    category: ImageCategory
    tags: List[str]
    is_product: bool
    is_service_related: bool
    suggested_associations: List[str]
    confidence: float
    metadata: Dict[str, Any]
```

**Processing Logic**:
```python
class VisionAgent:
    """
    Claude-powered image analysis
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.prompt_template = self.load_vision_prompt_template()
    
    async def analyze(self, input: VisionAnalysisInput) -> ImageAnalysis:
        """
        Analyze image with context-aware prompting
        """
        # Encode image to base64
        image_data = self.encode_image(input.image.path)
        
        # Build context-aware prompt
        prompt = self.build_vision_prompt(input.context)
        
        # Call Claude's vision API
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": input.image.mime_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )
        
        # Parse response
        analysis_data = self.parse_vision_response(response.content[0].text)
        
        return ImageAnalysis(
            description=analysis_data['description'],
            category=ImageCategory(analysis_data['category']),
            tags=analysis_data['tags'],
            is_product=analysis_data['is_product'],
            is_service_related=analysis_data['is_service_related'],
            suggested_associations=analysis_data.get('associations', []),
            confidence=analysis_data.get('confidence', 0.8),
            metadata=analysis_data.get('metadata', {})
        )
    
    def build_vision_prompt(self, context: str) -> str:
        """
        Context-aware vision analysis prompt
        """
        return f"""
        Analyze this image in the context of a business digitization project.
        
        Document context: {context[:500]}
        
        Provide a JSON response with:
        {{
            "description": "Brief 2-3 sentence description of what's shown",
            "category": "product|service|food|destination|person|document|other",
            "tags": ["tag1", "tag2", ...],
            "is_product": true|false,
            "is_service_related": true|false,
            "associations": ["suggested product/service names this might relate to"],
            "confidence": 0.0-1.0
        }}
        
        Be specific and descriptive. Focus on business-relevant details.
        """
```

**Vision Capabilities**:
- Product identification
- Service visualization detection
- Menu/food item recognition
- Destination/location identification
- Document/screenshot detection
- Quality assessment

---

### 6. Indexing Agent

**Responsibility**: Build vectorless page index for RAG

**Input Contract**:
```python
@dataclass
class IndexingInput:
    parsed_docs: List[ParsedDocument]
    tables: List[StructuredTable]
    media: MediaCollection
    job_id: str
```

**Output Contract**:
```python
@dataclass
class PageIndex:
    documents: Dict[str, ParsedDocument]
    page_index: Dict[str, List[PageReference]]
    table_index: Dict[str, List[TableReference]]
    media_index: Dict[str, List[MediaReference]]
    metadata: IndexMetadata
```

**Processing Logic**:
```python
class IndexingAgent:
    """
    Build vectorless inverted index for fast retrieval
    """
    
    def build_index(self, input: IndexingInput) -> PageIndex:
        """
        Create multi-level inverted index
        """
        page_index = PageIndex(
            documents={},
            page_index={},
            table_index={},
            media_index={},
            metadata=IndexMetadata()
        )
        
        # Index documents
        for doc in input.parsed_docs:
            page_index.documents[doc.doc_id] = doc
            self.index_document(doc, page_index)
        
        # Index tables
        for table in input.tables:
            self.index_table(table, page_index)
        
        # Index media
        self.index_media(input.media, page_index)
        
        return page_index
    
    def index_document(self, doc: ParsedDocument, index: PageIndex):
        """
        Create inverted index for document pages
        """
        for page in doc.pages:
            keywords = self.extract_keywords(page.text)
            
            for keyword in keywords:
                if keyword not in index.page_index:
                    index.page_index[keyword] = []
                
                index.page_index[keyword].append(PageReference(
                    doc_id=doc.doc_id,
                    page_number=page.number,
                    snippet=self.extract_snippet(page.text, keyword),
                    relevance_score=self.calculate_relevance(page.text, keyword)
                ))
    
    def extract_keywords(self, text: str) -> Set[str]:
        """
        Extract searchable keywords from text
        """
        # Tokenization
        tokens = word_tokenize(text.lower())
        
        # Remove stopwords
        stopwords = set(ENGLISH_STOPWORDS)
        keywords = [t for t in tokens if t not in stopwords]
        
        # Add multi-word phrases
        bigrams = self.extract_bigrams(tokens)
        trigrams = self.extract_trigrams(tokens)
        
        return set(keywords + bigrams + trigrams)
```

---

### 7. Schema Mapping Agent

**Responsibility**: Map extracted data to business profile schema using LLM

**Input Contract**:
```python
@dataclass
class SchemaMappingInput:
    page_index: PageIndex
    image_analyses: List[ImageAnalysis]
    job_id: str
```

**Output Contract**:
```python
@dataclass
class BusinessProfile:
    business_info: BusinessInfo
    products: Optional[List[Product]]
    services: Optional[List[Service]]
    business_type: BusinessType
    extraction_metadata: ExtractionMetadata
```

**Processing Logic**:
```python
class SchemaMappingAgent:
    """
    LLM-powered intelligent field mapping
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    async def map_to_schema(
        self, 
        input: SchemaMappingInput
    ) -> BusinessProfile:
        """
        Multi-stage schema mapping process
        """
        # Stage 1: Classify business type
        business_type = await self.classify_business_type(input.page_index)
        
        # Stage 2: Extract core business information
        business_info = await self.extract_business_info(input.page_index)
        
        # Stage 3: Extract inventory based on type
        products, services = await self.extract_inventory(
            business_type,
            input.page_index,
            input.image_analyses
        )
        
        return BusinessProfile(
            business_info=business_info,
            products=products,
            services=services,
            business_type=business_type,
            extraction_metadata=self.generate_metadata()
        )
    
    async def classify_business_type(
        self, 
        page_index: PageIndex
    ) -> BusinessType:
        """
        Determine if business is product, service, or mixed
        """
        context = self.build_classification_context(page_index)
        
        prompt = f"""
        Analyze this business information and determine the type:
        
        {context}
        
        Respond with JSON:
        {{
            "type": "product|service|mixed",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }}
        
        Guidelines:
        - "product": Sells physical or digital products
        - "service": Provides services (consulting, travel, education, etc.)
        - "mixed": Both products and services
        """
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = json.loads(response.content[0].text)
        return BusinessType(result['type'])
    
    async def extract_products(
        self,
        page_index: PageIndex,
        image_analyses: List[ImageAnalysis]
    ) -> List[Product]:
        """
        Extract product inventory
        """
        # Find product-related content
        product_context = page_index.get_relevant_context([
            'product', 'item', 'price', 'specification', 'features'
        ])
        
        # Find product images
        product_images = [
            img for img in image_analyses if img.is_product
        ]
        
        # LLM extraction
        prompt = self.build_product_extraction_prompt(
            product_context,
            product_images
        )
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        products_data = json.loads(response.content[0].text)
        
        return [Product(**p) for p in products_data['products']]
```

**Prompting Strategy**:
- **System prompts**: Clear schema definitions
- **Context injection**: Relevant excerpts only (token efficiency)
- **JSON output**: Structured, parseable responses
- **Few-shot examples**: For complex schemas
- **Validation**: Check for required fields

---

### 8. Validation Agent

**Responsibility**: Validate generated profiles and score completeness

**Input Contract**:
```python
@dataclass
class ValidationInput:
    profile: BusinessProfile
    job_id: str
```

**Output Contract**:
```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    completeness_score: float
    field_scores: Dict[str, float]
    validated_profile: BusinessProfile
```

**Processing Logic**:
```python
class ValidationAgent:
    """
    Schema validation and quality scoring
    """
    
    def validate(self, input: ValidationInput) -> ValidationResult:
        """
        Comprehensive validation
        """
        errors = []
        warnings = []
        field_scores = {}
        
        # Validate business info
        business_errors = self.validate_business_info(input.profile.business_info)
        errors.extend(business_errors)
        field_scores['business_info'] = self.score_business_info(
            input.profile.business_info
        )
        
        # Validate products
        if input.profile.products:
            for i, product in enumerate(input.profile.products):
                product_errors = self.validate_product(product)
                if product_errors:
                    errors.extend([f"Product {i+1}: {e}" for e in product_errors])
            
            field_scores['products'] = self.score_products(input.profile.products)
        
        # Validate services
        if input.profile.services:
            for i, service in enumerate(input.profile.services):
                service_errors = self.validate_service(service)
                if service_errors:
                    errors.extend([f"Service {i+1}: {e}" for e in service_errors])
            
            field_scores['services'] = self.score_services(input.profile.services)
        
        # Calculate overall completeness
        completeness = self.calculate_completeness(input.profile, field_scores)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            completeness_score=completeness,
            field_scores=field_scores,
            validated_profile=input.profile
        )
```

## Agent Coordination Patterns

### Sequential Processing
```
FileDiscovery → DocumentParsing → TableExtraction → MediaExtraction → Vision → Indexing → SchemaMapping → Validation
```

### Parallel Processing
```
DocumentParsing:
  ├── doc1.pdf (async)
  ├── doc2.docx (async)
  └── doc3.pdf (async)

VisionAnalysis:
  ├── image1.jpg (async)
  ├── image2.png (async)
  └── image3.jpg (async)
```

### Error Propagation
- **Soft failures**: Continue with partial results
- **Hard failures**: Stop pipeline and report
- **Retry logic**: 3 attempts for transient errors

## Inter-Agent Communication

### Message Format
```python
@dataclass
class AgentMessage:
    sender: str
    receiver: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    job_id: str
```

### Event Bus
```python
class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
    
    def publish(self, event: AgentMessage):
        """Broadcast event to subscribers"""
        if event.message_type in self.subscribers:
            for handler in self.subscribers[event.message_type]:
                handler(event)
    
    def subscribe(self, message_type: MessageType, handler: Callable):
        """Register handler for message type"""
        if message_type not in self.subscribers:
            self.subscribers[message_type] = []
        self.subscribers[message_type].append(handler)
```

## Conclusion

This agent pipeline provides a robust, modular approach to business digitization. Each agent has clear responsibilities, well-defined interfaces, and graceful error handling. The combination of deterministic parsing and AI-powered intelligence ensures both reliability and flexibility.
