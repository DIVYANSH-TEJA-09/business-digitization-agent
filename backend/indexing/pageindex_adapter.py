"""
Module: pageindex_adapter.py
Purpose: PageIndex-compatible tree index builder using Groq (GPT-OSS-120B).

Implements the core PageIndex logic — building a hierarchical tree index
from documents — but using our Groq integration instead of OpenAI directly.

This is a lightweight reimplementation of VectifyAI/PageIndex's tree
generation, adapted for our pipeline and LLM providers.

Tree Structure:
    {
        "title": "Document Title",
        "node_id": "0000",
        "start_index": 1,
        "end_index": 10,
        "summary": "...",
        "nodes": [
            {
                "title": "Section 1",
                "node_id": "0001",
                ...
            }
        ]
    }
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.models.schemas import DocumentIndex, PageIndexNode, ParsedDocument
from backend.utils.llm_client import llm_client
from backend.utils.logger import get_logger
from backend.utils.storage_manager import storage_manager
from backend.utils.text_utils import (
    clean_text,
    count_tokens_estimate,
    tables_to_markdown,
    text_to_markdown,
    truncate_text,
)

logger = get_logger(__name__)

# Tree generation config
MAX_PAGES_PER_NODE = 10
MAX_TOKENS_PER_NODE = 15000
TOC_CHECK_PAGES = 10


class PageIndexAdapter:
    """
    Builds PageIndex-compatible tree indexes from parsed documents.

    Uses GPT-OSS-120B via Groq for:
        1. Detecting table-of-contents structure
        2. Generating section splits and hierarchy
        3. Creating node summaries

    Supports two workflows:
        - PDF documents: Uses page-level structure
        - Non-PDF documents (DOCX, Excel): Converts to Markdown first,
          then builds tree from heading structure
    """

    def __init__(self):
        self.client = llm_client

    def build_index(
        self, parsed_doc: ParsedDocument, job_id: str
    ) -> DocumentIndex:
        """
        Build a PageIndex tree for a parsed document.

        Args:
            parsed_doc: Document to index
            job_id: Job ID for storage

        Returns:
            DocumentIndex with hierarchical tree structure
        """
        doc_name = Path(parsed_doc.source_file).name
        logger.info(f"Building PageIndex tree: {doc_name}")

        try:
            if parsed_doc.total_pages <= 1:
                # Single-page or non-paged documents — use markdown approach
                tree = self._build_tree_from_text(parsed_doc)
            elif parsed_doc.total_pages <= 3:
                # Very short docs — single node with summary
                tree = self._build_simple_tree(parsed_doc)
            else:
                # Multi-page docs — full tree generation
                tree = self._build_tree_from_pages(parsed_doc)

            # Assign node IDs
            self._assign_node_ids(tree)

            # Create index
            index = DocumentIndex(
                doc_id=parsed_doc.doc_id,
                source_file=parsed_doc.source_file,
                tree=tree,
                description=tree.summary if tree else "",
                total_pages=parsed_doc.total_pages,
            )

            # Save to storage
            index_json = index.model_dump_json(indent=2)
            storage_manager.save_index(
                job_id, parsed_doc.doc_id, index_json
            )

            logger.info(
                f"PageIndex tree built: {doc_name} — "
                f"{self._count_nodes(tree)} nodes"
            )

            return index

        except Exception as e:
            logger.warning(f"Failed to build PageIndex tree for {doc_name}: {e}")
            # Return a minimal index on failure
            return DocumentIndex(
                doc_id=parsed_doc.doc_id,
                source_file=parsed_doc.source_file,
                tree=None,
                description="",
                total_pages=parsed_doc.total_pages,
            )

    def build_indexes(
        self, parsed_docs: List[ParsedDocument], job_id: str
    ) -> List[DocumentIndex]:
        """Build indexes for multiple documents."""
        indexes = []
        for doc in parsed_docs:
            index = self.build_index(doc, job_id)
            indexes.append(index)
        return indexes

    def search_tree(
        self,
        query: str,
        index: DocumentIndex,
        parsed_doc: ParsedDocument,
        max_results: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Search a PageIndex tree using LLM reasoning.

        Instead of vector similarity, uses the LLM to navigate
        the tree and find relevant sections.

        Args:
            query: The search query
            index: Document index with tree structure
            parsed_doc: The parsed document for retrieving actual content
            max_results: Maximum number of relevant sections

        Returns:
            List of relevant page contents with references
        """
        if not index.tree:
            # No tree — return full text truncated
            return [{
                "content": truncate_text(parsed_doc.full_text, 5000),
                "source": parsed_doc.source_file,
                "pages": "all",
                "title": "Full Document",
            }]

        # Build tree summary for LLM
        tree_summary = self._tree_to_summary(index.tree)

        prompt = f"""Given this document's table of contents:

{tree_summary}

And this query: "{query}"

Which sections are most relevant? Return a JSON array of the most relevant
node_ids (up to {max_results}). Consider which sections would contain
information about: {query}

Respond with ONLY a JSON array like: ["0001", "0003", "0005"]"""

        try:
            response = self.client.chat_groq(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=200,
            )

            # Parse response
            node_ids = json.loads(response.strip())
            if not isinstance(node_ids, list):
                node_ids = [str(node_ids)]

        except Exception:
            # Fallback: return all leaf nodes
            node_ids = [index.tree.node_id] if index.tree else []

        # Retrieve content for selected nodes
        results = []
        for node_id in node_ids[:max_results]:
            node = self._find_node(index.tree, node_id)
            if node:
                content = self._get_node_content(node, parsed_doc)
                results.append({
                    "content": content,
                    "source": parsed_doc.source_file,
                    "pages": f"{node.start_index}-{node.end_index}",
                    "title": node.title,
                    "node_id": node.node_id,
                })

        return results if results else [{
            "content": truncate_text(parsed_doc.full_text, 5000),
            "source": parsed_doc.source_file,
            "pages": "all",
            "title": "Full Document",
        }]

    def _build_tree_from_pages(self, doc: ParsedDocument) -> PageIndexNode:
        """Build tree from a multi-page document (e.g., PDF)."""
        # Step 1: Build page summaries for the LLM
        page_summaries = []
        for page in doc.pages[:50]:  # Limit to first 50 pages
            summary = page.text[:300] if page.text else "[empty page]"
            table_info = f" [{len(page.tables)} table(s)]" if page.tables else ""
            page_summaries.append(
                f"Page {page.number}: {summary}{table_info}"
            )

        pages_text = "\n".join(page_summaries)

        prompt = f"""Analyze this document's page-by-page content and create a hierarchical
table of contents structure as JSON.

RULES:
- Each node has: title, start_index (start page), end_index (end page), summary, nodes (children)
- Top-level node should span all pages
- Group related pages into sections and subsections
- Maximum {MAX_PAGES_PER_NODE} pages per leaf node
- Use the actual content to determine section titles and boundaries
- Return valid JSON only

Document pages:
{pages_text}

Return a JSON object:
{{
    "title": "Document Title",
    "start_index": 1,
    "end_index": {doc.total_pages},
    "summary": "Brief document description",
    "nodes": [
        {{
            "title": "Section Name",
            "start_index": 1,
            "end_index": 5,
            "summary": "Section description",
            "nodes": []
        }}
    ]
}}"""

        try:
            response = self.client.chat_groq(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=3000,
                response_format={"type": "json_object"},
            )

            tree_data = json.loads(response)
            return self._dict_to_tree(tree_data)

        except Exception as e:
            logger.warning(f"LLM tree generation failed: {e}")
            return self._build_simple_tree(doc)

    def _build_tree_from_text(self, doc: ParsedDocument) -> PageIndexNode:
        """Build tree from document text (for single-page/non-paged docs)."""
        # Convert to markdown first
        md_text = text_to_markdown(
            doc.full_text,
            title=doc.metadata.title,
            source_file=Path(doc.source_file).name,
        )

        # Add tables as markdown
        for page in doc.pages:
            if page.tables:
                md_text += "\n\n" + tables_to_markdown(page.tables)

        # If text is short enough, just create a single node
        token_count = count_tokens_estimate(md_text)
        if token_count < MAX_TOKENS_PER_NODE:
            return PageIndexNode(
                title=doc.metadata.title or Path(doc.source_file).name,
                node_id="0000",
                start_index=1,
                end_index=max(doc.total_pages, 1),
                summary=truncate_text(md_text, 500),
                nodes=[],
            )

        # For longer text, ask LLM to create structure
        prompt = f"""Analyze this document and create a hierarchical table of contents as JSON.

RULES:
- Each node has: title, start_index (1), end_index (1), summary, nodes (children)
- Group content into logical sections
- Return valid JSON only

Document:
{truncate_text(md_text, 10000)}

Return JSON:
{{"title": "...", "start_index": 1, "end_index": 1, "summary": "...", "nodes": [...]}}"""

        try:
            response = self.client.chat_groq(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            tree_data = json.loads(response)
            return self._dict_to_tree(tree_data)
        except Exception:
            return self._build_simple_tree(doc)

    def _build_simple_tree(self, doc: ParsedDocument) -> PageIndexNode:
        """Build a minimal single-node tree."""
        return PageIndexNode(
            title=doc.metadata.title or Path(doc.source_file).name,
            node_id="0000",
            start_index=1,
            end_index=max(doc.total_pages, 1),
            summary=truncate_text(doc.full_text, 500),
            nodes=[],
        )

    def _dict_to_tree(self, data: Dict[str, Any]) -> PageIndexNode:
        """Convert a dict/JSON to PageIndexNode recursively."""
        children = []
        for child_data in data.get("nodes", []):
            if isinstance(child_data, dict):
                children.append(self._dict_to_tree(child_data))

        return PageIndexNode(
            title=data.get("title", "Untitled"),
            node_id=data.get("node_id", "0000"),
            start_index=data.get("start_index", 1),
            end_index=data.get("end_index", 1),
            summary=data.get("summary", ""),
            nodes=children,
        )

    def _assign_node_ids(self, node: PageIndexNode, counter: list = None) -> None:
        """Assign sequential node IDs to all nodes in the tree."""
        if counter is None:
            counter = [0]

        node.node_id = str(counter[0]).zfill(4)
        counter[0] += 1

        for child in node.nodes:
            self._assign_node_ids(child, counter)

    def _tree_to_summary(self, node: PageIndexNode, depth: int = 0) -> str:
        """Convert tree to a readable summary for LLM consumption."""
        indent = "  " * depth
        lines = [
            f"{indent}[{node.node_id}] {node.title} "
            f"(pages {node.start_index}-{node.end_index}): {node.summary[:100]}"
        ]
        for child in node.nodes:
            lines.append(self._tree_to_summary(child, depth + 1))
        return "\n".join(lines)

    def _find_node(
        self, node: PageIndexNode, node_id: str
    ) -> Optional[PageIndexNode]:
        """Find a node by its ID in the tree."""
        if node.node_id == node_id:
            return node
        for child in node.nodes:
            found = self._find_node(child, node_id)
            if found:
                return found
        return None

    def _get_node_content(
        self, node: PageIndexNode, doc: ParsedDocument
    ) -> str:
        """Get the text content for a tree node from the parsed document."""
        content_parts = []
        for page in doc.pages:
            if node.start_index <= page.number <= node.end_index:
                if page.text:
                    content_parts.append(page.text)
                if page.tables:
                    content_parts.append(tables_to_markdown(page.tables))

        content = "\n\n".join(content_parts)
        return truncate_text(content, 8000)

    def _count_nodes(self, node: Optional[PageIndexNode]) -> int:
        """Count total nodes in the tree."""
        if not node:
            return 0
        count = 1
        for child in node.nodes:
            count += self._count_nodes(child)
        return count


# Singleton instance
pageindex_adapter = PageIndexAdapter()
