# Document Parsing Strategy: Agentic Business Digitization Framework

## Parsing Philosophy

Document parsing is the foundation of accurate business digitization. The strategy prioritizes:
1. **Deterministic extraction** - Rule-based, reliable parsing
2. **Structure preservation** - Maintain document organization
3. **Graceful degradation** - Continue on partial failures
4. **Multi-strategy fallback** - Alternative parsing methods
5. **Context retention** - Keep surrounding information

## PDF Parsing Strategy

### Primary Library: pdfplumber

**Why pdfplumber?**
- Superior table detection and extraction
- Preserves layout information
- Handles complex formatting
- Better than PyPDF2 for structured content

### PDF Parsing Workflow

```python
class PDFParser:
    """
    Multi-layered PDF parsing strategy
    """
    
    def __init__(self):
        self.primary_parser = pdfplumber
        self.fallback_parser = PyPDF2
        self.ocr_engine = pytesseract
    
    async def parse(self, pdf_path: str) -> ParsedDocument:
        """
        Hierarchical parsing with fallbacks
        """
        try:
            # Strategy 1: pdfplumber (best for structured PDFs)
            return await self.parse_with_pdfplumber(pdf_path)
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")
            
            try:
                # Strategy 2: PyPDF2 (fallback for simpler extraction)
                return await self.parse_with_pypdf2(pdf_path)
            except Exception as e2:
                logger.warning(f"PyPDF2 failed: {e2}")
                
                # Strategy 3: OCR (for scanned PDFs or images)
                return await self.parse_with_ocr(pdf_path)
```

### Layer 1: Text Extraction

```python
def extract_text_structured(self, page) -> str:
    """
    Extract text while preserving structure
    """
    # pdfplumber's layout analysis
    text = page.extract_text(layout=True)
    
    # Clean and normalize
    text = self.normalize_whitespace(text)
    text = self.fix_unicode_issues(text)
    text = self.remove_artifacts(text)
    
    return text

def normalize_whitespace(self, text: str) -> str:
    """
    Clean excessive whitespace while preserving structure
    """
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Preserve intentional line breaks
    text = re.sub(r'\n\n+', '\n\n', text)
    
    # Remove trailing whitespace
    lines = [line.rstrip() for line in text.split('\n')]
    
    return '\n'.join(lines)
```

### Layer 2: Table Extraction

```python
def extract_tables_from_page(self, page) -> List[List[List[str]]]:
    """
    Extract tables with multiple strategies
    """
    tables = []
    
    # Strategy 1: pdfplumber's built-in table detection
    try:
        page_tables = page.extract_tables()
        for table in page_tables:
            if self.is_valid_table(table):
                tables.append(self.clean_table(table))
    except Exception as e:
        logger.warning(f"Table extraction failed: {e}")
    
    # Strategy 2: Detect tables by visual layout
    if not tables:
        visual_tables = self.detect_tables_by_layout(page)
        tables.extend(visual_tables)
    
    return tables

def is_valid_table(self, table: List[List[str]]) -> bool:
    """
    Validate table structure
    """
    if not table or len(table) < 2:
        return False
    
    # Check if table has consistent column count
    column_counts = [len(row) for row in table]
    if len(set(column_counts)) > 2:  # Allow some variation
        return False
    
    # Check if table has meaningful content
    non_empty_cells = sum(1 for row in table for cell in row if cell and cell.strip())
    total_cells = sum(len(row) for row in table)
    
    if total_cells == 0 or non_empty_cells / total_cells < 0.3:
        return False
    
    return True

def clean_table(self, table: List[List[str]]) -> List[List[str]]:
    """
    Clean and normalize table data
    """
    cleaned = []
    
    for row in table:
        cleaned_row = []
        for cell in row:
            if cell is None:
                cleaned_row.append("")
            else:
                # Remove excessive whitespace
                cleaned_cell = ' '.join(cell.split())
                cleaned_row.append(cleaned_cell)
        cleaned.append(cleaned_row)
    
    return cleaned
```

### Layer 3: Image Extraction

```python
def extract_images_from_page(self, page, page_num: int) -> List[ExtractedImage]:
    """
    Extract embedded images with metadata
    """
    images = []
    
    # Access page images
    if hasattr(page, 'images'):
        for i, img_info in enumerate(page.images):
            try:
                # Extract image data
                image = self.extract_image_data(page, img_info)
                
                if image:
                    images.append(ExtractedImage(
                        image_id=f"img_{page_num}_{i}",
                        file_path=self.save_image(image, page_num, i),
                        source_page=page_num,
                        width=int(img_info.get('width', 0)),
                        height=int(img_info.get('height', 0)),
                        extraction_method="pdfplumber",
                        is_embedded=True
                    ))
            except Exception as e:
                logger.warning(f"Failed to extract image {i} from page {page_num}: {e}")
    
    return images

def extract_image_data(self, page, img_info: dict) -> Optional[Image]:
    """
    Extract actual image bytes from PDF
    """
    try:
        # Get image object reference
        xref = img_info.get('xref')
        if not xref:
            return None
        
        # Extract image using pdf file handle
        base_image = page.pdf.pdf.extract_image(xref)
        
        if base_image:
            image_bytes = base_image["image"]
            return Image.open(io.BytesIO(image_bytes))
    
    except Exception as e:
        logger.error(f"Image extraction error: {e}")
        return None
```

### Layer 4: PDF Metadata Extraction

```python
def extract_pdf_metadata(self, pdf_path: str) -> DocumentMetadata:
    """
    Extract document properties
    """
    with pdfplumber.open(pdf_path) as pdf:
        metadata = pdf.metadata or {}
        
        return DocumentMetadata(
            title=metadata.get('Title'),
            author=metadata.get('Author'),
            creation_date=self.parse_pdf_date(metadata.get('CreationDate')),
            modification_date=self.parse_pdf_date(metadata.get('ModDate')),
            page_count=len(pdf.pages),
            file_size=os.path.getsize(pdf_path)
        )

def parse_pdf_date(self, date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse PDF date format (D:YYYYMMDDHHmmSS)
    """
    if not date_str:
        return None
    
    try:
        # Remove 'D:' prefix and timezone info
        date_str = date_str.replace('D:', '').split('+')[0].split('-')[0]
        return datetime.strptime(date_str[:14], '%Y%m%d%H%M%S')
    except Exception:
        return None
```

### OCR Fallback Strategy

```python
async def parse_with_ocr(self, pdf_path: str) -> ParsedDocument:
    """
    OCR-based parsing for scanned PDFs
    """
    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=300)
    
    pages = []
    for i, image in enumerate(images):
        # Enhance image for better OCR
        enhanced = self.enhance_for_ocr(image)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(
            enhanced,
            config='--psm 6'  # Assume uniform block of text
        )
        
        pages.append(Page(
            number=i + 1,
            text=text,
            metadata={'extraction_method': 'ocr'}
        ))
    
    return ParsedDocument(
        doc_id=self.generate_doc_id(pdf_path),
        source_file=pdf_path,
        file_type=FileType.PDF,
        pages=pages,
        total_pages=len(pages),
        metadata=self.extract_pdf_metadata(pdf_path),
        parsing_errors=[]
    )

def enhance_for_ocr(self, image: Image) -> Image:
    """
    Image preprocessing for better OCR accuracy
    """
    # Convert to grayscale
    gray = image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(2.0)
    
    # Denoise
    denoised = contrasted.filter(ImageFilter.MedianFilter(size=3))
    
    # Sharpen
    sharpened = denoised.filter(ImageFilter.SHARPEN)
    
    return sharpened
```

## DOCX Parsing Strategy

### Primary Library: python-docx

### DOCX Parsing Workflow

```python
class DOCXParser:
    """
    Structured DOCX parsing preserving document elements
    """
    
    async def parse(self, docx_path: str) -> ParsedDocument:
        """
        Parse DOCX with full structure preservation
        """
        doc = Document(docx_path)
        
        elements = []
        
        # Iterate through all document elements
        for element in self.iter_block_items(doc):
            if isinstance(element, Paragraph):
                elements.append(self.parse_paragraph(element))
            elif isinstance(element, Table):
                elements.append(self.parse_docx_table(element))
        
        # Extract embedded images
        images = self.extract_docx_images(doc, docx_path)
        
        # Combine elements into text
        full_text = self.elements_to_text(elements)
        
        return ParsedDocument(
            doc_id=self.generate_doc_id(docx_path),
            source_file=docx_path,
            file_type=FileType.DOCX,
            pages=[Page(
                number=1,
                text=full_text,
                elements=elements,
                images=images,
                metadata={}
            )],
            total_pages=1,
            metadata=self.extract_docx_metadata(doc),
            parsing_errors=[]
        )
```

### Paragraph Parsing

```python
def parse_paragraph(self, paragraph: Paragraph) -> dict:
    """
    Extract paragraph with formatting
    """
    return {
        'type': 'paragraph',
        'text': paragraph.text,
        'style': paragraph.style.name if paragraph.style else 'Normal',
        'alignment': str(paragraph.alignment) if paragraph.alignment else None,
        'is_heading': paragraph.style.name.startswith('Heading') if paragraph.style else False,
        'level': self.extract_heading_level(paragraph),
        'formatting': self.extract_formatting(paragraph)
    }

def extract_formatting(self, paragraph: Paragraph) -> dict:
    """
    Extract text formatting details
    """
    formatting = {
        'bold': False,
        'italic': False,
        'underline': False,
        'font_size': None,
        'font_name': None
    }
    
    if paragraph.runs:
        first_run = paragraph.runs[0]
        formatting['bold'] = first_run.bold or False
        formatting['italic'] = first_run.italic or False
        formatting['underline'] = first_run.underline or False
        
        if first_run.font.size:
            formatting['font_size'] = first_run.font.size.pt
        if first_run.font.name:
            formatting['font_name'] = first_run.font.name
    
    return formatting
```

### Table Parsing

```python
def parse_docx_table(self, table: Table) -> dict:
    """
    Extract table structure from DOCX
    """
    rows_data = []
    
    for row in table.rows:
        row_data = []
        for cell in row.cells:
            # Handle merged cells
            cell_text = cell.text.strip()
            row_data.append(cell_text)
        rows_data.append(row_data)
    
    # Detect headers
    has_header = self.detect_table_header(rows_data)
    
    return {
        'type': 'table',
        'rows': rows_data,
        'has_header': has_header,
        'row_count': len(rows_data),
        'column_count': len(rows_data[0]) if rows_data else 0
    }

def detect_table_header(self, rows: List[List[str]]) -> bool:
    """
    Determine if first row is a header
    """
    if not rows or len(rows) < 2:
        return False
    
    first_row = rows[0]
    
    # Check if first row cells are non-empty
    if not all(first_row):
        return False
    
    # Check if first row is different from subsequent rows
    # (headers often have different formatting/content patterns)
    return True
```

### Image Extraction from DOCX

```python
def extract_docx_images(self, doc: Document, docx_path: str) -> List[ExtractedImage]:
    """
    Extract embedded images from DOCX
    """
    images = []
    
    # DOCX files are ZIP archives
    with zipfile.ZipFile(docx_path) as docx_zip:
        # Images are in word/media/ folder
        media_files = [
            f for f in docx_zip.namelist() 
            if f.startswith('word/media/')
        ]
        
        for i, media_file in enumerate(media_files):
            try:
                # Extract image bytes
                image_bytes = docx_zip.read(media_file)
                
                # Determine image format
                image_format = self.detect_image_format(media_file)
                
                # Save image
                image_path = self.save_docx_image(image_bytes, i, image_format)
                
                # Get image dimensions
                with Image.open(io.BytesIO(image_bytes)) as img:
                    width, height = img.size
                
                images.append(ExtractedImage(
                    image_id=f"docx_img_{i}",
                    file_path=image_path,
                    source_doc=docx_path,
                    width=width,
                    height=height,
                    file_size=len(image_bytes),
                    mime_type=f"image/{image_format}",
                    extraction_method="docx",
                    is_embedded=True
                ))
            
            except Exception as e:
                logger.warning(f"Failed to extract DOCX image {media_file}: {e}")
    
    return images
```

## Excel Parsing Strategy

### Primary Library: openpyxl + pandas

### Excel Parsing Workflow

```python
class ExcelParser:
    """
    Excel/spreadsheet parsing
    """
    
    async def parse(self, excel_path: str) -> ParsedDocument:
        """
        Parse Excel workbook
        """
        workbook = openpyxl.load_workbook(excel_path, data_only=True)
        
        sheets_data = []
        
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            sheet_data = self.parse_sheet(sheet, sheet_name)
            sheets_data.append(sheet_data)
        
        return ParsedDocument(
            doc_id=self.generate_doc_id(excel_path),
            source_file=excel_path,
            file_type=FileType.XLSX,
            pages=[Page(
                number=i + 1,
                text=self.sheet_to_text(sheet),
                tables=[sheet['data']],
                metadata={'sheet_name': sheet['name']}
            ) for i, sheet in enumerate(sheets_data)],
            total_pages=len(sheets_data),
            metadata=self.extract_excel_metadata(workbook),
            parsing_errors=[]
        )
    
    def parse_sheet(self, sheet, sheet_name: str) -> dict:
        """
        Convert sheet to structured data
        """
        # Get data range
        data = []
        for row in sheet.iter_rows(values_only=True):
            # Skip completely empty rows
            if not any(row):
                continue
            
            # Convert to strings, handle None
            row_data = [str(cell) if cell is not None else "" for cell in row]
            data.append(row_data)
        
        return {
            'name': sheet_name,
            'data': data,
            'row_count': len(data),
            'column_count': len(data[0]) if data else 0
        }
```

### CSV Parsing

```python
class CSVParser:
    """
    CSV file parsing
    """
    
    async def parse(self, csv_path: str) -> ParsedDocument:
        """
        Parse CSV with encoding detection
        """
        # Detect encoding
        encoding = self.detect_encoding(csv_path)
        
        # Read CSV
        df = pd.read_csv(csv_path, encoding=encoding)
        
        # Convert to structured format
        table_data = [df.columns.tolist()] + df.values.tolist()
        
        return ParsedDocument(
            doc_id=self.generate_doc_id(csv_path),
            source_file=csv_path,
            file_type=FileType.CSV,
            pages=[Page(
                number=1,
                text=df.to_string(),
                tables=[table_data],
                metadata={}
            )],
            total_pages=1,
            metadata=DocumentMetadata(
                page_count=1,
                file_size=os.path.getsize(csv_path)
            ),
            parsing_errors=[]
        )
    
    def detect_encoding(self, file_path: str) -> str:
        """
        Detect CSV file encoding
        """
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read(10000))
        return result['encoding'] or 'utf-8'
```

## Error Handling & Recovery

### Graceful Degradation

```python
def handle_parsing_error(
    self, 
    file_path: str, 
    error: Exception
) -> ParsedDocument:
    """
    Create partial document on parsing failure
    """
    logger.error(f"Parsing failed for {file_path}: {error}")
    
    return ParsedDocument(
        doc_id=self.generate_doc_id(file_path),
        source_file=file_path,
        file_type=FileType.UNKNOWN,
        pages=[],
        total_pages=0,
        metadata=DocumentMetadata(file_size=os.path.getsize(file_path)),
        parsing_errors=[str(error)]
    )
```

### Retry Logic

```python
async def parse_with_retry(
    self, 
    file_path: str, 
    max_retries: int = 3
) -> ParsedDocument:
    """
    Retry parsing with exponential backoff
    """
    for attempt in range(max_retries):
        try:
            return await self.parse(file_path)
        except Exception as e:
            if attempt == max_retries - 1:
                return self.handle_parsing_error(file_path, e)
            
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            await asyncio.sleep(wait_time)
```

## Performance Optimization

### Parallel Document Parsing

```python
async def parse_multiple(
    self, 
    file_paths: List[str]
) -> List[ParsedDocument]:
    """
    Parse multiple documents in parallel
    """
    tasks = [self.parse(path) for path in file_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    parsed_docs = []
    for file_path, result in zip(file_paths, results):
        if isinstance(result, Exception):
            parsed_docs.append(self.handle_parsing_error(file_path, result))
        else:
            parsed_docs.append(result)
    
    return parsed_docs
```

### Memory Management

```python
def parse_large_pdf(self, pdf_path: str) -> ParsedDocument:
    """
    Stream parse large PDFs to avoid memory issues
    """
    pages = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # Parse page
            parsed_page = self.parse_page(page, i + 1)
            pages.append(parsed_page)
            
            # Clear memory every 50 pages
            if i % 50 == 0:
                gc.collect()
    
    return ParsedDocument(
        doc_id=self.generate_doc_id(pdf_path),
        source_file=pdf_path,
        file_type=FileType.PDF,
        pages=pages,
        total_pages=len(pages),
        metadata=self.extract_pdf_metadata(pdf_path),
        parsing_errors=[]
    )
```

## Conclusion

This document parsing strategy provides:
- **Robust extraction** from multiple file formats
- **Fallback mechanisms** for corrupted files
- **Structure preservation** for better context
- **Performance optimization** for large documents
- **Error recovery** for graceful degradation

The multi-layered approach ensures maximum extraction accuracy while handling real-world document complexities.
