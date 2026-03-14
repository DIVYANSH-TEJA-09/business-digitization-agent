"""
Module: text_utils.py
Purpose: Text cleaning and normalization utilities.

Provides functions to clean extracted text from documents,
remove artifacts, normalize whitespace, and prepare text
for LLM consumption and Markdown conversion.
"""

import re
import unicodedata
from typing import List, Optional


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text.

    Operations:
        - Normalize Unicode characters
        - Remove null bytes and control characters
        - Normalize whitespace (collapse multiple spaces/newlines)
        - Strip leading/trailing whitespace

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text string
    """
    if not text:
        return ""

    # Normalize Unicode (NFC form)
    text = unicodedata.normalize("NFC", text)

    # Remove null bytes and most control characters (keep newlines, tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Replace tabs with spaces
    text = text.replace("\t", "    ")

    # Collapse multiple spaces (but not newlines) into single space
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def remove_headers_footers(text: str) -> str:
    """
    Attempt to remove repeated headers/footers from extracted text.

    Common patterns:
        - Page numbers (e.g., "Page 1 of 10", "- 3 -")
        - Confidentiality notices
        - Company names repeated on every page
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip standalone page numbers
        if re.match(r"^(page\s+)?\d+(\s+(of|\/)\s+\d+)?$", stripped, re.IGNORECASE):
            continue

        # Skip lines that are just dashes or underscores (separators)
        if re.match(r"^[-_=]{3,}$", stripped):
            continue

        # Skip lines that are just "- N -" style page numbers
        if re.match(r"^-\s*\d+\s*-$", stripped):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_sections(text: str) -> List[dict]:
    """
    Split text into sections based on heading patterns.

    Detects headings by:
        - ALL CAPS lines (likely headings)
        - Lines followed by === or --- underlines
        - Short lines (<80 chars) that are standalone

    Returns:
        List of dicts with 'heading' and 'content' keys
    """
    if not text:
        return []

    lines = text.split("\n")
    sections = []
    current_heading = ""
    current_content = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            current_content.append("")
            continue

        is_heading = False

        # Check for ALL CAPS heading (at least 3 chars, mostly letters)
        if (
            len(stripped) >= 3
            and len(stripped) < 80
            and stripped.upper() == stripped
            and sum(c.isalpha() for c in stripped) > len(stripped) * 0.5
        ):
            is_heading = True

        # Check for underlined heading (next line is === or ---)
        if (
            i + 1 < len(lines)
            and re.match(r"^[=\-]{3,}$", lines[i + 1].strip())
        ):
            is_heading = True

        if is_heading:
            # Save previous section
            if current_heading or current_content:
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_content).strip(),
                })
            current_heading = stripped
            current_content = []
        else:
            current_content.append(line)

    # Don't forget the last section
    if current_heading or current_content:
        sections.append({
            "heading": current_heading,
            "content": "\n".join(current_content).strip(),
        })

    return sections


def text_to_markdown(
    text: str,
    title: Optional[str] = None,
    source_file: Optional[str] = None,
) -> str:
    """
    Convert extracted document text to structured Markdown.

    This is used to prepare documents for PageIndex tree generation.
    PageIndex works best with properly formatted Markdown with headings.

    Args:
        text: Cleaned document text
        title: Optional document title (used as H1)
        source_file: Optional source filename for context

    Returns:
        Markdown-formatted string
    """
    md_parts = []

    # Document title
    if title:
        md_parts.append(f"# {title}")
    elif source_file:
        md_parts.append(f"# {source_file}")

    md_parts.append("")

    # Extract sections and convert to markdown headings
    sections = extract_sections(text)

    if sections:
        for section in sections:
            if section["heading"]:
                md_parts.append(f"## {section['heading'].title()}")
            if section["content"]:
                md_parts.append(section["content"])
            md_parts.append("")
    else:
        # No sections detected — just use the text as-is
        md_parts.append(text)

    return "\n".join(md_parts)


def tables_to_markdown(tables: List[List[List[str]]]) -> str:
    """
    Convert extracted table data to Markdown table format.

    Args:
        tables: List of tables, each being a list of rows (list of cells)

    Returns:
        Markdown-formatted tables string
    """
    if not tables:
        return ""

    md_parts = []

    for table_idx, table in enumerate(tables):
        if not table or len(table) < 1:
            continue

        # First row as headers
        headers = [str(cell).strip() if cell else "" for cell in table[0]]
        if not any(headers):
            continue

        md_parts.append(f"### Table {table_idx + 1}")
        md_parts.append("")
        md_parts.append("| " + " | ".join(headers) + " |")
        md_parts.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Data rows
        for row in table[1:]:
            cells = [str(cell).strip() if cell else "" for cell in row]
            # Pad/truncate to match header count
            while len(cells) < len(headers):
                cells.append("")
            cells = cells[: len(headers)]
            md_parts.append("| " + " | ".join(cells) + " |")

        md_parts.append("")

    return "\n".join(md_parts)


def truncate_text(text: str, max_chars: int = 50000) -> str:
    """
    Truncate text to a maximum character count, preserving word boundaries.

    Used when preparing context for LLM calls to stay within token limits.
    """
    if len(text) <= max_chars:
        return text

    # Find last space before max_chars
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]

    return truncated + "\n\n[... text truncated ...]"


def count_tokens_estimate(text: str) -> int:
    """
    Rough estimate of token count (1 token ≈ 4 characters).

    This is a fast approximation, not exact tokenization.
    """
    return len(text) // 4
