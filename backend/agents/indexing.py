"""
Indexing Agent - Vectorless RAG

Builds inverted index for fast document retrieval without embeddings.
Implements keyword extraction, indexing, and context-aware retrieval.
"""
import os
import re
import time
from typing import List, Dict, Set, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from backend.models.schemas import (
    IndexingInput,
    IndexingOutput,
    PageIndex,
    PageReference,
    ParsedDocument,
    Page,
    StructuredTable,
    ExtractedImage,
    TreeNode,
)
from backend.models.enums import TableType, ImageCategory
from backend.utils.logger import get_logger


logger = get_logger(__name__)


# Common English stopwords to remove
STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
    'this', 'that', 'these', 'those', 'it', 'its', 'as', 'if', 'then',
    'than', 'so', 'such', 'both', 'each', 'few', 'more', 'most', 'other',
    'some', 'any', 'no', 'not', 'only', 'own', 'same', 'very', 'just',
    'also', 'now', 'here', 'there', 'when', 'where', 'why', 'how',
    'all', 'about', 'into', 'over', 'after', 'before', 'between',
    'under', 'again', 'further', 'once', 'during', 'while', 'through',
    'what', 'which', 'who', 'whom', 'whose', 'your', 'you', 'we', 'they'
}

# Business-specific terms to always keep
BUSINESS_TERMS = {
    'price', 'cost', 'product', 'service', 'hours', 'location', 'contact',
    'email', 'phone', 'website', 'description', 'features', 'specifications',
    'menu', 'booking', 'reservation', 'payment', 'delivery', 'shipping'
}


class IndexingAgent:
    """
    Builds and manages vectorless page index for RAG
    
    Features:
    - Keyword extraction with business term awareness
    - Inverted index for fast lookup
    - Table and media indexing
    - Context-aware retrieval
    - Query expansion with synonyms
    """
    
    def __init__(self):
        """Initialize Indexing Agent"""
        self.keyword_extractor = KeywordExtractor()
        self.retriever = ContextRetriever()
    
    def build_index(self, input: IndexingInput) -> PageIndex:
        """
        Build hierarchical page index (PageIndex-style)
        
        Args:
            input: Indexing input with documents, tables, media
            
        Returns:
            PageIndex object with tree structure
        """
        start_time = time.time()
        
        logger.info(f"Building PageIndex for {len(input.parsed_documents)} documents")
        
        try:
            # Initialize index
            page_index = PageIndex(
                documents={},
                tree_root=None,
                page_index=defaultdict(list),
                table_index=defaultdict(list),
                media_index=defaultdict(list),
                metadata={
                    'created_at': datetime.now().isoformat(),
                    'total_documents': len(input.parsed_documents),
                    'total_tables': len(input.tables),
                    'total_images': len(input.images),
                    'index_type': 'hierarchical_tree'
                }
            )
            
            # Index documents and build tree
            tree_nodes = []
            for doc in input.parsed_documents:
                try:
                    doc_node = self._index_document(doc, page_index)
                    if doc_node:
                        tree_nodes.append(doc_node)
                except Exception as e:
                    logger.warning(f"Failed to index document {doc.doc_id}: {e}")
                    continue
            
            # Create tree root
            if tree_nodes:
                page_index.tree_root = TreeNode(
                    title="Root",
                    node_id="root",
                    children=tree_nodes,
                    summary=f"Index containing {len(tree_nodes)} documents"
                )
            
            # Index tables
            for table in input.tables:
                try:
                    self._index_table(table, page_index)
                except Exception as e:
                    logger.warning(f"Failed to index table: {e}")
                    continue
            
            # Index media
            for image in input.images:
                try:
                    self._index_media(image, page_index)
                except Exception as e:
                    logger.warning(f"Failed to index image: {e}")
                    continue
            
            # Convert defaultdict to regular dict for serialization
            page_index.page_index = {k: v for k, v in page_index.page_index.items()}
            page_index.table_index = {k: v for k, v in page_index.table_index.items()}
            page_index.media_index = {k: v for k, v in page_index.media_index.items()}
            
            # Calculate statistics
            page_index.metadata['total_keywords'] = len(page_index.page_index)
            page_index.metadata['total_tree_nodes'] = self._count_tree_nodes(page_index.tree_root)
            page_index.metadata['build_time_seconds'] = time.time() - start_time
            
            logger.info(
                f"PageIndex built: {page_index.metadata['total_keywords']} keywords, "
                f"{page_index.metadata['total_tree_nodes']} tree nodes "
                f"in {page_index.metadata['build_time_seconds']:.2f}s"
            )
            
            # Debug: Log sample keywords
            if page_index.page_index:
                sample_keywords = list(page_index.page_index.keys())[:10]
                logger.info(f"Sample keywords: {sample_keywords}")
            else:
                logger.warning("No keywords indexed!")
            
            return page_index
            
        except Exception as e:
            logger.error(f"Index building failed: {e}")
            # Return empty index instead of failing
            return PageIndex(
                documents={},
                tree_root=None,
                page_index={},
                table_index={},
                media_index={},
                metadata={
                    'error': str(e),
                    'build_time_seconds': time.time() - start_time
                }
            )
    
    def _index_document(self, doc: ParsedDocument, page_index: PageIndex) -> Optional[TreeNode]:
        """
        Index a parsed document and create tree node
        """
        try:
            # Store document
            page_index.documents[doc.doc_id] = doc
            logger.info(f"📄 Indexing document: {doc.doc_id} ({os.path.basename(doc.source_file)})")
            
            # Create document tree node
            doc_node = TreeNode(
                title=os.path.basename(doc.source_file),
                node_id=doc.doc_id,
                start_page=1,
                end_page=doc.total_pages,
                doc_id=doc.doc_id,
                summary=f"Document with {doc.total_pages} pages"
            )
            
            # Index each page
            all_keywords = set()
            pages_indexed = 0
            total_refs = 0
            
            for page_idx, page in enumerate(doc.pages):
                try:
                    # Extract keywords from page text
                    keywords = self.keyword_extractor.extract_keywords(page.text)
                    all_keywords.update(keywords)
                    
                    if page_idx < 3:  # Log first 3 pages
                        logger.info(f"  Page {page_idx+1}: Extracted {len(keywords)} keywords: {list(keywords)[:10]}")
                    
                    # Create page references
                    keywords_added = 0
                    for keyword in keywords:
                        try:
                            # Validate keyword
                            if not keyword or not isinstance(keyword, str):
                                continue
                            
                            # Clean keyword
                            keyword_clean = keyword.strip().lower()
                            if len(keyword_clean) < 2:
                                continue
                            
                            snippet = self._extract_snippet(page.text, keyword_clean)
                            
                            # Create PageReference
                            page_ref = PageReference(
                                doc_id=doc.doc_id,
                                page_number=page.number,
                                snippet=snippet,
                                relevance_score=self._calculate_keyword_relevance(keyword_clean, page.text)
                            )
                            
                            # Add to index - handle dict properly (not defaultdict!)
                            if keyword_clean not in page_index.page_index:
                                page_index.page_index[keyword_clean] = []
                            page_index.page_index[keyword_clean].append(page_ref)
                            keywords_added += 1
                            total_refs += 1
                            
                        except Exception as e:
                            logger.warning(f"    ⚠️ Keyword '{keyword}' failed: {e}")
                            continue
                    
                    if keywords_added > 0:
                        pages_indexed += 1
                    
                    if page_idx < 3:  # Log first 3 pages
                        logger.info(f"  ✅ Page {page_idx+1}: Added {keywords_added} keywords to index")
                    
                except Exception as e:
                    logger.warning(f"  ❌ Page {page.number} failed: {e}")
                    continue
            
            logger.info(f"📊 Document {doc.doc_id}: {pages_indexed}/{doc.total_pages} pages, {len(all_keywords)} keywords, {total_refs} refs, index size: {len(page_index.page_index)}")
            
            # Force print for debugging
            print(f"📊 INDEX DEBUG: {doc.doc_id} -> {len(all_keywords)} keywords extracted, {len(page_index.page_index)} in index")
            if page_index.page_index and len(page_index.page_index) > 0:
                print(f"   Sample keys: {list(page_index.page_index.keys())[:5]}")
            else:
                print(f"   ⚠️ INDEX IS EMPTY! This is the bug!")
            
            # Add keywords to node
            doc_node.keywords = [k for k in all_keywords if k and isinstance(k, str) and len(k) > 2]
            doc_node.content_snippet = doc.pages[0].text[:500] if doc.pages else ""
            
            return doc_node
            
        except Exception as e:
            logger.error(f"❌ Document {doc.doc_id} failed: {e}")
            return None
    
    def _count_tree_nodes(self, node: Optional[TreeNode]) -> int:
        """Count total tree nodes"""
        if not node:
            return 0
        count = 1
        for child in node.children:
            count += self._count_tree_nodes(child)
        return count
    
    def _index_table(self, table: StructuredTable, page_index: PageIndex):
        """
        Index a structured table
        
        Args:
            table: StructuredTable to index
            page_index: PageIndex to update
        """
        # Index by table type
        table_type = table.table_type.value
        
        # Extract keywords from headers and content
        header_keywords = self.keyword_extractor.extract_keywords(' '.join(table.headers))
        content_keywords = self.keyword_extractor.extract_keywords(
            ' '.join(' '.join(row) for row in table.rows[:5])  # First 5 rows
        )
        
        all_keywords = set(header_keywords) | set(content_keywords)
        
        for keyword in all_keywords:
            page_index.table_index[keyword].append({
                'table_id': table.table_id,
                'doc_id': table.source_doc,
                'page_number': table.source_page,
                'table_type': table_type,
                'headers': table.headers,
                'snippet': table.context[:200] if table.context else ''
            })
    
    def _index_media(self, image: ExtractedImage, page_index: PageIndex):
        """
        Index an image
        
        Args:
            image: ExtractedImage to index
            page_index: PageIndex to update
        """
        # Index by category and metadata
        category = image.metadata.get('category', 'unknown')
        
        # Extract keywords from description if available
        description = image.metadata.get('description', '')
        keywords = self.keyword_extractor.extract_keywords(description)
        
        for keyword in keywords:
            page_index.media_index[keyword].append({
                'image_id': image.image_id,
                'file_path': image.file_path,
                'category': category,
                'source_doc': image.source_doc,
                'description': description[:200] if description else ''
            })
    
    def _extract_snippet(self, text: str, keyword: str, context_size: int = 100) -> str:
        """
        Extract snippet around keyword
        
        Args:
            text: Full text
            keyword: Keyword to find
            context_size: Characters before/after keyword
            
        Returns:
            Snippet string
        """
        # Find keyword position (case-insensitive)
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        pos = text_lower.find(keyword_lower)
        if pos == -1:
            return text[:context_size * 2]
        
        # Extract snippet
        start = max(0, pos - context_size)
        end = min(len(text), pos + len(keyword) + context_size)
        
        snippet = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet.replace('\n', ' ').strip()
    
    def _calculate_keyword_relevance(self, keyword: str, text: str) -> float:
        """
        Calculate keyword relevance score
        
        Args:
            keyword: Keyword
            text: Full text
            
        Returns:
            Relevance score (0.0-1.0)
        """
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Count occurrences
        count = text_lower.count(keyword_lower)
        
        # Base score from frequency
        freq_score = min(count * 0.2, 0.6)  # Cap at 0.6
        
        # Bonus for business terms
        business_bonus = 0.2 if keyword_lower in BUSINESS_TERMS else 0.0
        
        # Bonus for position (first 500 chars more important)
        position_bonus = 0.2 if keyword_lower in text_lower[:500] else 0.0
        
        return min(freq_score + business_bonus + position_bonus, 1.0)
    
    def retrieve_context(
        self,
        query: str,
        page_index: PageIndex,
        max_pages: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for query
        
        Args:
            query: Search query
            page_index: PageIndex to search
            max_pages: Maximum pages to return
            
        Returns:
            Retrieval result dictionary
        """
        return self.retriever.retrieve(query, page_index, max_pages)


class KeywordExtractor:
    """
    Extracts searchable keywords from text
    """
    
    def __init__(self):
        """Initialize keyword extractor"""
        self.stopwords = STOPWORDS
        self.business_terms = BUSINESS_TERMS
    
    def extract_keywords(self, text: str) -> Set[str]:
        """
        Extract keywords from text using multiple strategies
        
        Args:
            text: Input text
            
        Returns:
            Set of clean keywords
        """
        if not text:
            return set()
        
        keywords = set()
        
        # Strategy 1: Tokenization with stopword removal
        tokens = self._tokenize(text)
        keywords.update(tokens)
        
        # Strategy 2: Named entity extraction (emails, phones, URLs)
        entities = self._extract_entities(text)
        keywords.update(entities)
        
        # Strategy 3: N-grams (bigrams, trigrams) - only clean ones
        bigrams = self._extract_ngrams(tokens, n=2)
        trigrams = self._extract_ngrams(tokens, n=3)
        keywords.update(bigrams + trigrams)
        
        # Final cleanup: Ensure all keywords are clean strings
        clean_keywords = set()
        for kw in keywords:
            if isinstance(kw, str):
                # Remove any remaining underscores/hyphens
                kw = kw.replace('_', ' ').replace('-', ' ')
                # Split compound words
                parts = kw.split()
                clean_keywords.update([p.strip() for p in parts if len(p.strip()) > 2])
        
        return clean_keywords
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize and normalize text
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        # Lowercase
        text = text.lower()
        
        # Replace underscores and hyphens with spaces (split compound words)
        text = re.sub(r'[_-]', ' ', text)
        
        # Remove punctuation except in meaningful contexts
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Filter: Remove stopwords (keep business terms), numbers, short tokens
        filtered = [
            t for t in tokens
            if (t not in self.stopwords or t in self.business_terms)
            and not t.isdigit()  # Remove pure numbers
            and len(t) > 2  # Filter short tokens
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for t in filtered:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        
        return unique
    
    def _extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities using simple heuristics
        
        Args:
            text: Input text
            
        Returns:
            List of entities
        """
        entities = []
        
        # Email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        entities.extend([e.lower() for e in emails])
        
        # Phone numbers
        phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
        entities.extend(phones)
        
        # URLs
        urls = re.findall(r'https?://\S+', text)
        entities.extend([u.lower() for u in urls])
        
        # Prices
        prices = re.findall(r'\$[\d,]+(?:\.\d{2})?', text)
        entities.extend(prices)
        
        return entities
    
    def _extract_ngrams(self, tokens: List[str], n: int) -> List[str]:
        """
        Extract n-grams from token list
        
        Args:
            tokens: List of tokens
            n: N-gram size
            
        Returns:
            List of n-grams
        """
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = '_'.join(tokens[i:i+n])
            ngrams.append(ngram)
        return ngrams


class ContextRetriever:
    """
    Retrieves relevant context from page index
    """
    
    def __init__(self):
        """Initialize context retriever"""
        self.synonym_map = {
            'price': ['cost', 'rate', 'fee', 'charge'],
            'hours': ['time', 'schedule', 'timing', 'open'],
            'location': ['address', 'place', 'where', 'near'],
            'contact': ['phone', 'email', 'reach', 'call'],
            'product': ['item', 'goods', 'merchandise'],
            'service': ['offering', 'package', 'tour']
        }
    
    def retrieve(
        self,
        query: str,
        page_index: PageIndex,
        max_pages: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for query
        
        Args:
            query: Search query
            page_index: PageIndex to search
            max_pages: Maximum pages to return
            
        Returns:
            Retrieval result dictionary
        """
        try:
            # Process query
            query_terms = self._process_query(query)
            
            # Find matching pages
            matching_pages = self._find_matching_pages(query_terms, page_index)
            
            # Rank pages
            ranked_pages = self._rank_pages(matching_pages, query_terms)
            
            # Select top pages
            top_pages = ranked_pages[:max_pages]
            
            # Build context
            context = self._build_context(top_pages, page_index)
            
            return {
                'query': query,
                'matched_pages': len(matching_pages),
                'ranked_pages': [p.__dict__ for p in top_pages],  # Convert to dict for serialization
                'context': context,
                'confidence': self._calculate_confidence(top_pages)
            }
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return {
                'query': query,
                'matched_pages': 0,
                'ranked_pages': [],
                'context': '',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _process_query(self, query: str) -> List[str]:
        """
        Process and expand query
        
        Args:
            query: Search query
            
        Returns:
            List of query terms
        """
        # Extract keywords
        extractor = KeywordExtractor()
        terms = list(extractor.extract_keywords(query))
        
        # Expand with synonyms
        expanded = set(terms)
        for term in terms:
            if term in self.synonym_map:
                expanded.update(self.synonym_map[term])
        
        return list(expanded)
    
    def _find_matching_pages(
        self,
        query_terms: List[str],
        page_index: PageIndex
    ) -> List[PageReference]:
        """
        Find all pages matching query terms
        
        Args:
            query_terms: Query terms
            page_index: PageIndex to search
            
        Returns:
            List of matching page references
        """
        matching = {}  # page_key -> PageReference
        
        for term in query_terms:
            term_lower = term.lower()
            
            if term_lower in page_index.page_index:
                for page_ref in page_index.page_index[term_lower]:
                    page_key = f"{page_ref.doc_id}:{page_ref.page_number}"
                    
                    if page_key not in matching:
                        matching[page_key] = page_ref
                    else:
                        # Aggregate relevance scores
                        matching[page_key].relevance_score += page_ref.relevance_score
        
        return list(matching.values())
    
    def _rank_pages(
        self,
        pages: List[PageReference],
        query_terms: List[str]
    ) -> List[PageReference]:
        """
        Rank pages by relevance
        
        Args:
            pages: Matching pages
            query_terms: Query terms
            
        Returns:
            Ranked list of pages
        """
        # Sort by relevance score
        sorted_pages = sorted(pages, key=lambda p: p.relevance_score, reverse=True)
        return sorted_pages
    
    def _build_context(
        self,
        pages: List[PageReference],
        page_index: PageIndex
    ) -> str:
        """
        Build context string from top pages
        
        Args:
            pages: Top ranked pages
            page_index: PageIndex
            
        Returns:
            Context string
        """
        context_parts = []
        
        for page_ref in pages:
            # Get document
            doc = page_index.documents.get(page_ref.doc_id)
            if not doc:
                continue
            
            # Get page
            if page_ref.page_number <= len(doc.pages):
                page = doc.pages[page_ref.page_number - 1]
                
                # Add context with source info
                context_parts.append(
                    f"[Document: {os.path.basename(doc.source_file)}, Page {page_ref.page_number}]\n"
                    f"{page_ref.snippet}"
                )
        
        return "\n\n".join(context_parts)
    
    def _calculate_confidence(self, pages: List[PageReference]) -> float:
        """
        Calculate retrieval confidence
        
        Args:
            pages: Retrieved pages
            
        Returns:
            Confidence score (0.0-1.0)
        """
        if not pages:
            return 0.0
        
        # Average relevance score
        avg_score = sum(p.relevance_score for p in pages) / len(pages)
        
        # Bonus for multiple matches
        count_bonus = min(len(pages) * 0.1, 0.3)
        
        return min(avg_score + count_bonus, 1.0)
