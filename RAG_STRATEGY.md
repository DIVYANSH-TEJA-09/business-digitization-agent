# RAG Strategy: Vectorless Retrieval for Business Digitization

## RAG Overview

Traditional RAG (Retrieval-Augmented Generation) systems use vector embeddings for semantic search. This project implements a **vectorless RAG approach** using an inverted page index system, optimized for business document processing.

## Why Vectorless RAG?

### Advantages Over Vector-Based RAG

| Aspect | Vectorless (Page Index) | Vector-Based |
|--------|------------------------|--------------|
| **Setup Cost** | No embedding generation | Expensive embedding computation |
| **Latency** | Fast keyword lookups | Vector similarity computation overhead |
| **Explainability** | Clear why results returned | Black box similarity scores |
| **Memory** | Lightweight index | Large vector storage |
| **Deterministic** | Same query = same results | Embedding model dependent |
| **Debugging** | Easy to trace | Difficult to debug relevance |

### When Vectorless Works Best

✅ **Good Fit:**
- Structured business documents
- Exact keyword matching important
- Limited document corpus (10-100 docs)
- Need for explainable retrieval
- Cost-sensitive applications

❌ **Not Ideal:**
- Semantic similarity critical
- Massive document collections (1000s+)
- Multilingual with no keyword overlap
- Query reformulation needed

## Page Index Architecture

### Core Components

```python
class PageIndex:
    """
    Vectorless inverted index for fast document retrieval
    """
    
    def __init__(self):
        # Document storage
        self.documents: Dict[str, ParsedDocument] = {}
        
        # Inverted indices
        self.page_index: Dict[str, List[PageReference]] = {}
        self.table_index: Dict[TableType, List[TableReference]] = {}
        self.media_index: Dict[ImageCategory, List[MediaReference]] = {}
        
        # Metadata
        self.index_metadata: IndexMetadata = IndexMetadata()
        
        # Statistics
        self.stats: IndexStats = IndexStats()
```

### Indexing Process

```python
class IndexingAgent:
    """
    Build and manage the page index
    """
    
    def build_index(
        self, 
        parsed_docs: List[ParsedDocument],
        tables: List[StructuredTable],
        media: MediaCollection
    ) -> PageIndex:
        """
        Create comprehensive inverted index
        """
        index = PageIndex()
        
        # Index documents by page
        for doc in parsed_docs:
            index.documents[doc.doc_id] = doc
            self.index_document_pages(doc, index)
        
        # Index tables by type and content
        for table in tables:
            self.index_table(table, index)
        
        # Index media by category
        for image in media.images:
            self.index_media(image, index)
        
        # Build statistics
        index.stats = self.compute_statistics(index)
        
        return index
    
    def index_document_pages(
        self, 
        doc: ParsedDocument, 
        index: PageIndex
    ):
        """
        Create inverted index for each page
        """
        for page in doc.pages:
            # Extract keywords from page text
            keywords = self.extract_keywords(page.text)
            
            # Create page references
            for keyword in keywords:
                if keyword not in index.page_index:
                    index.page_index[keyword] = []
                
                index.page_index[keyword].append(PageReference(
                    doc_id=doc.doc_id,
                    page_number=page.number,
                    snippet=self.extract_snippet(page.text, keyword),
                    relevance_score=self.calculate_keyword_relevance(
                        keyword, page.text
                    )
                ))
```

### Keyword Extraction

```python
class KeywordExtractor:
    """
    Extract searchable keywords from text
    """
    
    def __init__(self):
        # Load stopwords
        self.stopwords = set(ENGLISH_STOPWORDS)
        
        # Common business terms to always include
        self.business_terms = {
            'price', 'cost', 'product', 'service', 'hours',
            'location', 'contact', 'email', 'phone', 'website',
            'description', 'features', 'specifications'
        }
    
    def extract_keywords(self, text: str) -> Set[str]:
        """
        Multi-strategy keyword extraction
        """
        keywords = set()
        
        # Strategy 1: Tokenization with stopword removal
        tokens = self.tokenize(text)
        keywords.update(
            token for token in tokens 
            if token not in self.stopwords or token in self.business_terms
        )
        
        # Strategy 2: Named entity extraction
        entities = self.extract_entities(text)
        keywords.update(entities)
        
        # Strategy 3: N-grams (bigrams, trigrams)
        bigrams = self.extract_ngrams(tokens, n=2)
        trigrams = self.extract_ngrams(tokens, n=3)
        keywords.update(bigrams + trigrams)
        
        # Strategy 4: Key phrases (noun phrases)
        phrases = self.extract_noun_phrases(text)
        keywords.update(phrases)
        
        return keywords
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize and normalize text
        """
        # Lowercase
        text = text.lower()
        
        # Remove punctuation except in meaningful contexts
        text = re.sub(r'[^\w\s\-@.]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Normalize (lemmatization)
        tokens = [self.lemmatize(token) for token in tokens]
        
        # Filter short tokens
        tokens = [t for t in tokens if len(t) > 2]
        
        return tokens
    
    def extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities using simple heuristics
        """
        entities = []
        
        # Email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        entities.extend(emails)
        
        # Phone numbers
        phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
        entities.extend(phones)
        
        # URLs
        urls = re.findall(r'https?://\S+', text)
        entities.extend(urls)
        
        # Capitalized words (potential names/places)
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities.extend(capitalized)
        
        return [e.lower() for e in entities]
    
    def extract_ngrams(self, tokens: List[str], n: int) -> List[str]:
        """
        Extract n-grams from token list
        """
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = '_'.join(tokens[i:i+n])
            ngrams.append(ngram)
        return ngrams
```

## Retrieval Strategies

### Query Processing

```python
class QueryProcessor:
    """
    Process and expand user queries
    """
    
    def process_query(self, query: str) -> ProcessedQuery:
        """
        Normalize and expand query
        """
        # Normalize query
        normalized = self.normalize_query(query)
        
        # Extract query terms
        terms = self.extract_query_terms(normalized)
        
        # Expand with synonyms
        expanded_terms = self.expand_with_synonyms(terms)
        
        # Weight terms by importance
        weighted_terms = self.weight_terms(expanded_terms)
        
        return ProcessedQuery(
            original=query,
            normalized=normalized,
            terms=terms,
            expanded_terms=expanded_terms,
            weighted_terms=weighted_terms
        )
    
    def expand_with_synonyms(self, terms: List[str]) -> List[str]:
        """
        Add synonyms for business terms
        """
        synonym_map = {
            'price': ['cost', 'rate', 'fee', 'charge'],
            'hours': ['time', 'schedule', 'timing'],
            'location': ['address', 'place', 'where'],
            'contact': ['phone', 'email', 'reach'],
        }
        
        expanded = set(terms)
        for term in terms:
            if term in synonym_map:
                expanded.update(synonym_map[term])
        
        return list(expanded)
```

### Context Retrieval

```python
class ContextRetriever:
    """
    Retrieve relevant context from page index
    """
    
    def retrieve_context(
        self, 
        query: ProcessedQuery,
        index: PageIndex,
        max_pages: int = 5
    ) -> RetrievalResult:
        """
        Get most relevant pages for query
        """
        # Find pages matching query terms
        matching_pages = self.find_matching_pages(query, index)
        
        # Rank pages by relevance
        ranked_pages = self.rank_pages(matching_pages, query)
        
        # Select top pages
        top_pages = ranked_pages[:max_pages]
        
        # Build context from selected pages
        context = self.build_context(top_pages, index)
        
        return RetrievalResult(
            query=query,
            matched_pages=matching_pages,
            ranked_pages=ranked_pages,
            context=context,
            confidence=self.calculate_confidence(top_pages)
        )
    
    def find_matching_pages(
        self, 
        query: ProcessedQuery,
        index: PageIndex
    ) -> List[PageReference]:
        """
        Find all pages containing query terms
        """
        matching_pages = {}  # page_key -> PageReference
        
        for term in query.weighted_terms:
            if term in index.page_index:
                for page_ref in index.page_index[term]:
                    page_key = f"{page_ref.doc_id}:{page_ref.page_number}"
                    
                    if page_key not in matching_pages:
                        matching_pages[page_key] = page_ref
                    else:
                        # Aggregate relevance scores
                        matching_pages[page_key].relevance_score += page_ref.relevance_score
        
        return list(matching_pages.values())
    
    def rank_pages(
        self,
        pages: List[PageReference],
        query: ProcessedQuery
    ) -> List[PageReference]:
        """
        Rank pages by relevance to query
        """
        scored_pages = []
        
        for page in pages:
            score = self.calculate_page_score(page, query)
            scored_pages.append((score, page))
        
        # Sort by score (descending)
        scored_pages.sort(key=lambda x: x[0], reverse=True)
        
        return [page for score, page in scored_pages]
    
    def calculate_page_score(
        self,
        page: PageReference,
        query: ProcessedQuery
    ) -> float:
        """
        Score page relevance using multiple signals
        """
        score = 0.0
        
        # Signal 1: Term frequency in page
        score += page.relevance_score * 0.5
        
        # Signal 2: Query term coverage
        coverage = self.calculate_term_coverage(page, query)
        score += coverage * 0.3
        
        # Signal 3: Snippet quality
        snippet_quality = self.assess_snippet_quality(page.snippet)
        score += snippet_quality * 0.2
        
        return score
    
    def build_context(
        self,
        pages: List[PageReference],
        index: PageIndex
    ) -> str:
        """
        Construct context string from top pages
        """
        context_parts = []
        
        for i, page in enumerate(pages):
            # Get full page text
            doc = index.documents.get(page.doc_id)
            if not doc:
                continue
            
            page_obj = doc.pages[page.page_number - 1]
            
            # Add page context with source info
            context_parts.append(
                f"[Document: {doc.source_file}, Page {page.page_number}]\n"
                f"{page_obj.text[:1000]}"  # Limit to 1000 chars per page
            )
        
        return "\n\n".join(context_parts)
```

## Table-Specific Retrieval

```python
class TableRetriever:
    """
    Specialized retrieval for tables
    """
    
    def retrieve_tables(
        self,
        table_type: TableType,
        index: PageIndex
    ) -> List[StructuredTable]:
        """
        Get all tables of specific type
        """
        if table_type not in index.table_index:
            return []
        
        table_refs = index.table_index[table_type]
        
        # Retrieve full table objects
        tables = []
        for ref in table_refs:
            # Load table from storage
            table = self.load_table(ref.table_id)
            if table:
                tables.append(table)
        
        return tables
    
    def retrieve_pricing_tables(self, index: PageIndex) -> List[StructuredTable]:
        """
        Get all pricing tables (common need)
        """
        return self.retrieve_tables(TableType.PRICING, index)
    
    def retrieve_itinerary_tables(self, index: PageIndex) -> List[StructuredTable]:
        """
        Get all itinerary/schedule tables
        """
        return self.retrieve_tables(TableType.ITINERARY, index)
```

## Media-Specific Retrieval

```python
class MediaRetriever:
    """
    Retrieve media by category
    """
    
    def retrieve_product_images(
        self,
        index: PageIndex,
        image_analyses: List[ImageAnalysis]
    ) -> List[ImageAnalysis]:
        """
        Get all product images
        """
        return [
            img for img in image_analyses 
            if img.is_product
        ]
    
    def retrieve_service_images(
        self,
        index: PageIndex,
        image_analyses: List[ImageAnalysis]
    ) -> List[ImageAnalysis]:
        """
        Get all service-related images
        """
        return [
            img for img in image_analyses 
            if img.is_service_related
        ]
```

## LLM Integration with RAG

### Context-Aware Prompting

```python
class RAGPromptBuilder:
    """
    Build prompts with retrieved context
    """
    
    def build_extraction_prompt(
        self,
        field_name: str,
        context: RetrievalResult,
        schema_description: str
    ) -> str:
        """
        Create prompt with RAG context
        """
        prompt = f"""
        Extract the following field from the provided business documents:
        
        Field: {field_name}
        Schema Description: {schema_description}
        
        Relevant Document Context:
        {context.context}
        
        Instructions:
        1. Extract ONLY information present in the documents
        2. Do NOT fabricate or infer missing information
        3. If field cannot be found, return null
        4. Return response as JSON
        
        Response format:
        {{
            "{field_name}": <extracted value or null>,
            "confidence": 0.0-1.0,
            "source": "document name and page number"
        }}
        """
        
        return prompt
```

### RAG-Enhanced Schema Mapping

```python
class RAGSchemaMapper:
    """
    Use RAG for intelligent field extraction
    """
    
    def __init__(self):
        self.retriever = ContextRetriever()
        self.prompt_builder = RAGPromptBuilder()
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    async def extract_field(
        self,
        field_name: str,
        field_schema: dict,
        index: PageIndex
    ) -> Any:
        """
        Extract single field using RAG
        """
        # Build query for field
        query = ProcessedQuery(
            original=field_name,
            normalized=field_name.lower(),
            terms=[field_name.lower()],
            expanded_terms=self.expand_field_query(field_name),
            weighted_terms={}
        )
        
        # Retrieve relevant context
        context = self.retriever.retrieve_context(query, index)
        
        # Build prompt
        prompt = self.prompt_builder.build_extraction_prompt(
            field_name,
            context,
            field_schema['description']
        )
        
        # Call LLM
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse response
        result = json.loads(response.content[0].text)
        
        return result[field_name]
```

## Index Optimization

### Compression

```python
def compress_index(index: PageIndex) -> CompressedIndex:
    """
    Reduce index size while maintaining performance
    """
    compressed = CompressedIndex()
    
    # Store only top N references per keyword
    for keyword, refs in index.page_index.items():
        # Sort by relevance
        sorted_refs = sorted(
            refs, 
            key=lambda r: r.relevance_score, 
            reverse=True
        )
        
        # Keep top 10
        compressed.page_index[keyword] = sorted_refs[:10]
    
    return compressed
```

### Caching

```python
class IndexCache:
    """
    Cache frequently accessed index lookups
    """
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_counts = {}
    
    def get(self, query_key: str) -> Optional[RetrievalResult]:
        """
        Get cached result
        """
        if query_key in self.cache:
            self.access_counts[query_key] += 1
            return self.cache[query_key]
        return None
    
    def put(self, query_key: str, result: RetrievalResult):
        """
        Cache result with LRU eviction
        """
        if len(self.cache) >= self.max_size:
            # Evict least recently used
            lru_key = min(
                self.access_counts.keys(), 
                key=lambda k: self.access_counts[k]
            )
            del self.cache[lru_key]
            del self.access_counts[lru_key]
        
        self.cache[query_key] = result
        self.access_counts[query_key] = 1
```

## Performance Metrics

### Index Statistics

```python
@dataclass
class IndexStats:
    """
    Index performance metrics
    """
    total_documents: int = 0
    total_pages: int = 0
    total_keywords: int = 0
    avg_keywords_per_page: float = 0.0
    index_size_bytes: int = 0
    build_time_seconds: float = 0.0
    
    def print_summary(self):
        print(f"""
        Index Statistics:
        - Documents: {self.total_documents}
        - Pages: {self.total_pages}
        - Keywords: {self.total_keywords}
        - Avg keywords/page: {self.avg_keywords_per_page:.1f}
        - Index size: {self.index_size_bytes / 1024:.1f} KB
        - Build time: {self.build_time_seconds:.2f}s
        """)
```

## Conclusion

This vectorless RAG strategy provides:
- **Fast retrieval** through inverted indexing
- **Explainable results** with keyword matching
- **Low overhead** compared to vector embeddings
- **Deterministic behavior** for consistent results
- **Context-aware LLM integration** for intelligent extraction

The approach is optimized for the business digitization use case where documents are structured, the corpus is manageable, and exact keyword matching is valuable.
