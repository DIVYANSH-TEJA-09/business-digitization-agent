# Cursor AI Prompt: Agentic Business Digitization Framework

## Project Context

You are developing an **Agentic Business Digitization Framework** - a sophisticated AI-powered system that automatically converts unstructured business documents into structured digital business profiles with product and service inventories.

## Core Objective

Build a production-grade system that:
- Accepts ZIP files containing mixed business documents (PDF, DOCX, Excel, images, videos)
- Intelligently extracts and structures business information using multi-agent workflows
- Generates comprehensive digital business profiles with product/service inventories
- Provides dynamic UI rendering based on detected business type
- Enables post-digitization editing and refinement

## System Constraints

### CRITICAL RULES
1. **NEVER fabricate data** - If information doesn't exist in source documents, leave fields empty
2. **FOCUS ONLY on Use Case 1** - Agentic Chat Framework for Business Digitization
3. **NO feature creep** - Implement only specified requirements
4. **Deterministic parsing** - Use scripts for document/table/media extraction
5. **LLM for intelligence only** - Summarization, metadata extraction, schema mapping

## Technical Architecture Requirements

### Input Processing
- ZIP file ingestion with automatic file type detection
- Multi-format document parsing: PDF, DOC/DOCX, Excel, images, videos
- Embedded media extraction from compound documents
- Hierarchical folder structure preservation

### Data Extraction Pipeline
- **PDF Processing**: Text extraction, table detection, embedded image extraction
- **DOCX Processing**: Structured content parsing, table extraction, media handling
- **Excel Processing**: Sheet parsing, table structure recognition, data validation
- **Image Processing**: Vision-language model integration for metadata generation
- **Video Detection**: Format recognition and metadata extraction

### RAG Strategy
- **Vectorless approach** using Page Index system
- Document-level and page-level indexing
- Context-aware retrieval without embedding pipelines
- Efficient lookup for schema mapping

### Schema Generation
```
BUSINESS PROFILE:
├── Description
├── Media (images/videos)
├── Working Hours
├── Location Details
├── Contact Information
├── Payment Methods
├── Fulfillment Information
├── Reviews/Ratings
└── Tags

PRODUCT INVENTORY (if detected):
├── Product Description
├── Media
├── Pricing
├── Specifications
├── Inventory Status
├── Cancellation/Refund Policy
└── Warranty Information

SERVICE INVENTORY (if detected):
├── Description
├── Media
├── Pricing
├── Best Time to Experience
├── Itinerary
├── Nearby Landmarks
├── Festivals
├── Local Food
├── FAQ
├── Payment/Cancellation Policy
├── What to Carry
├── Languages Spoken
├── Risk and Safety
└── Tags
```

### Agent Orchestration
- **Document Discovery Agent**: File enumeration and classification
- **Parsing Agent**: Format-specific extraction
- **Table Extraction Agent**: Structured data recognition
- **Media Extraction Agent**: Image/video processing
- **Vision Agent**: Multimodal content understanding
- **Schema Mapping Agent**: LLM-assisted field population
- **Validation Agent**: Quality assurance and completeness checking

## Development Phases

### Phase 1: ZIP Ingestion & File Discovery
- Implement secure ZIP extraction
- Create file type detection system
- Build file hierarchy mapper

### Phase 2: Document Parsing & Text Extraction
- Integrate PDF parser (PyPDF2/pdfplumber)
- Implement DOCX parser (python-docx)
- Build text normalization pipeline

### Phase 3: Table Extraction & Structuring
- Develop table detection algorithms
- Create structured data converters
- Implement table-to-JSON transformation

### Phase 4: Media Extraction
- Extract embedded images from PDFs
- Process standalone media files
- Generate media metadata and associations

### Phase 5: LLM-Assisted Schema Mapping
- Design prompt templates for field extraction
- Implement Claude API integration
- Create context-aware mapping logic

### Phase 6: Schema Validation
- Build validation rules engine
- Implement completeness scoring
- Create error handling and recovery

### Phase 7: Business Profile Generation
- Assemble final structured output
- Generate JSON schema-compliant profiles
- Create profile versioning system

### Phase 8: Dynamic UI Rendering
- Build conditional rendering engine
- Create product/service inventory displays
- Implement editing interface

## Code Quality Standards

### Architecture Patterns
- **Microservices approach** for each processing stage
- **Event-driven architecture** for agent coordination
- **Factory pattern** for parser selection
- **Strategy pattern** for schema mapping
- **Repository pattern** for data access

### Error Handling
- Graceful degradation when files are corrupted
- Detailed logging for debugging
- Retry logic for transient failures
- User-friendly error messages

### Testing Requirements
- Unit tests for each parser
- Integration tests for end-to-end workflows
- Test fixtures with sample business documents
- Performance benchmarks for large ZIP files

### Documentation Standards
- Inline code documentation
- API documentation for all agents
- Architecture decision records (ADRs)
- Deployment guides

## Technology Stack Recommendations

### Backend
- **Language**: Python 3.10+
- **Document Parsing**: PyPDF2, pdfplumber, python-docx, openpyxl, pandas
- **Image Processing**: Pillow, pdf2image
- **LLM Integration**: Anthropic Claude API (Sonnet 4)
- **File Handling**: zipfile, pathlib, mimetypes
- **Data Validation**: Pydantic for schema validation

### Frontend
- **Framework**: React with TypeScript
- **State Management**: Zustand or Redux
- **UI Components**: shadcn/ui or Material-UI
- **Form Handling**: React Hook Form
- **File Upload**: react-dropzone

### Storage & Indexing
- **Document Storage**: Local filesystem with organized structure
- **Index Storage**: SQLite or lightweight JSON-based index
- **Media Storage**: Organized directory structure with references

## Workflow Orchestration

```python
class BusinessDigitizationPipeline:
    """
    Main orchestrator for the agentic digitization workflow
    """
    def process_business_folder(self, zip_path: str) -> BusinessProfile:
        # 1. Extract and discover files
        files = self.file_discovery_agent.process(zip_path)
        
        # 2. Parse documents in parallel
        parsed_docs = self.parsing_agent.parse_all(files)
        
        # 3. Extract tables
        tables = self.table_extraction_agent.extract(parsed_docs)
        
        # 4. Extract media
        media = self.media_extraction_agent.extract(parsed_docs, files)
        
        # 5. Build page index for RAG
        page_index = self.indexing_agent.build_index(parsed_docs)
        
        # 6. LLM-assisted schema mapping
        profile = self.schema_mapping_agent.map_to_schema(
            parsed_docs, tables, media, page_index
        )
        
        # 7. Validate and refine
        validated_profile = self.validation_agent.validate(profile)
        
        return validated_profile
```

## Key Implementation Considerations

### Multimodal Processing
- Use Claude's vision capabilities for image understanding
- Generate descriptive metadata for products/services from images
- Associate images with correct inventory items using context

### Context Management
- Maintain document context throughout pipeline
- Track provenance of extracted information
- Enable traceability from output back to source

### Scalability
- Process large ZIP files efficiently
- Handle hundreds of documents
- Parallel processing where possible
- Progress tracking for user feedback

### Flexibility
- Detect business type dynamically (product vs. service vs. mixed)
- Adapt schema based on available information
- Support partial information gracefully

## Success Criteria

1. ✅ Successfully processes ZIP files with 10+ mixed format documents
2. ✅ Extracts text, tables, and embedded media with >90% accuracy
3. ✅ Generates valid business profiles without fabricated data
4. ✅ Renders dynamic UI based on detected inventory type
5. ✅ Allows full editing of generated profiles
6. ✅ Processes typical business folder in <2 minutes
7. ✅ Provides clear error messages for unsupported formats
8. ✅ Maintains data provenance for all extracted fields

## Development Approach

1. **Start with documentation** - Generate all MD files first
2. **Build incrementally** - Complete each phase before moving forward
3. **Test continuously** - Validate each component with real documents
4. **Iterate based on results** - Refine extraction accuracy
5. **Optimize last** - Focus on correctness before performance

## Notes for AI Assistant

- Prioritize **correctness over speed**
- Ask for clarification when document format is ambiguous
- Suggest improvements to extraction accuracy
- Flag potential data quality issues
- Recommend additional validation rules
- Propose user experience enhancements

---

**Remember**: This system must be production-ready, not a prototype. Every component should handle edge cases, provide meaningful errors, and maintain data integrity throughout the pipeline.
