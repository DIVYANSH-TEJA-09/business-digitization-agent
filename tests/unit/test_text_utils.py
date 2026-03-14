"""
Unit tests for backend.utils.text_utils

Covers:
    - clean_text
    - remove_headers_footers
    - extract_sections
    - text_to_markdown
    - tables_to_markdown
    - truncate_text
    - count_tokens_estimate
"""

import pytest

from backend.utils.text_utils import (
    clean_text,
    count_tokens_estimate,
    extract_sections,
    remove_headers_footers,
    tables_to_markdown,
    text_to_markdown,
    truncate_text,
)


# =============================================================================
# clean_text
# =============================================================================

class TestCleanText:

    def test_empty_string_returns_empty(self):
        assert clean_text("") == ""

    def test_none_like_falsy_returns_empty(self):
        # The function checks `if not text`
        assert clean_text("") == ""

    def test_strips_whitespace(self):
        assert clean_text("  hello world  ") == "hello world"

    def test_collapses_multiple_spaces(self):
        result = clean_text("hello     world")
        assert "  " not in result
        assert "hello world" in result

    def test_collapses_excessive_newlines(self):
        result = clean_text("line1\n\n\n\n\nline2")
        assert "\n\n\n" not in result
        assert "line1" in result
        assert "line2" in result

    def test_removes_null_bytes(self):
        result = clean_text("hello\x00world")
        assert "\x00" not in result
        assert "hello" in result
        assert "world" in result

    def test_removes_control_characters(self):
        result = clean_text("hello\x01\x02\x03world")
        assert "\x01" not in result
        assert "helloworld" in result

    def test_replaces_tabs_with_spaces(self):
        result = clean_text("col1\tcol2")
        assert "\t" not in result
        assert "col1" in result

    def test_unicode_normalization(self):
        # NFC normalization — composed form
        text = "\u00e9"  # é (precomposed)
        result = clean_text(text)
        assert len(result) == 1

    def test_preserves_newlines(self):
        result = clean_text("line1\nline2")
        assert "\n" in result

    def test_strips_each_line(self):
        result = clean_text("  line1  \n  line2  ")
        lines = result.split("\n")
        for line in lines:
            assert line == line.strip()


# =============================================================================
# remove_headers_footers
# =============================================================================

class TestRemoveHeadersFooters:

    def test_empty_returns_empty(self):
        assert remove_headers_footers("") == ""

    def test_removes_standalone_page_numbers(self):
        text = "Some content\n1\nMore content"
        result = remove_headers_footers(text)
        assert "Some content" in result
        assert "More content" in result

    def test_removes_page_n_of_m(self):
        text = "Header\nPage 3 of 10\nContent"
        result = remove_headers_footers(text)
        assert "Page 3 of 10" not in result
        assert "Content" in result

    def test_removes_dash_page_numbers(self):
        text = "Content\n- 5 -\nMore"
        result = remove_headers_footers(text)
        assert "- 5 -" not in result

    def test_removes_separator_lines(self):
        text = "Section\n---\nContent"
        result = remove_headers_footers(text)
        assert "---" not in result
        assert "Content" in result

    def test_preserves_normal_content(self):
        text = "TrekoTrip Adventures offers premium trekking packages."
        result = remove_headers_footers(text)
        assert result.strip() == text.strip()


# =============================================================================
# extract_sections
# =============================================================================

class TestExtractSections:

    def test_empty_returns_empty_list(self):
        assert extract_sections("") == []

    def test_detects_all_caps_heading(self):
        text = "PRICING\nHampta Pass: 12000\nSpiti Valley: 18000"
        sections = extract_sections(text)
        headings = [s["heading"] for s in sections]
        assert "PRICING" in headings

    def test_detects_underlined_heading(self):
        text = "Overview\n========\nThis is a travel company."
        sections = extract_sections(text)
        assert len(sections) >= 1

    def test_section_has_content(self):
        text = "CONTACT\nPhone: +91-9876543210\nEmail: info@trekotrip.in"
        sections = extract_sections(text)
        contact_section = next(
            (s for s in sections if s["heading"] == "CONTACT"), None
        )
        assert contact_section is not None
        assert "Phone" in contact_section["content"]

    def test_no_headings_returns_one_section(self):
        text = "This is plain text without any headings."
        sections = extract_sections(text)
        assert len(sections) == 1
        assert sections[0]["heading"] == ""


# =============================================================================
# text_to_markdown
# =============================================================================

class TestTextToMarkdown:

    def test_uses_source_file_as_title(self):
        md = text_to_markdown("Some content", source_file="brochure.pdf")
        assert md.startswith("# brochure.pdf")

    def test_uses_title_over_source_file(self):
        md = text_to_markdown("Content", title="My Doc", source_file="file.pdf")
        assert "# My Doc" in md
        assert "file.pdf" not in md

    def test_produces_markdown_headings_from_caps(self):
        text = "PRICING\nHampta: 12000"
        md = text_to_markdown(text, source_file="test.pdf")
        assert "##" in md

    def test_output_not_empty(self):
        md = text_to_markdown("Hello World", source_file="doc.pdf")
        assert len(md) > 0

    def test_fallback_plain_text_when_no_sections(self):
        text = "simple text without any heading patterns at all."
        md = text_to_markdown(text, source_file="doc.pdf")
        assert "simple text" in md


# =============================================================================
# tables_to_markdown
# =============================================================================

class TestTablesToMarkdown:

    def test_empty_returns_empty(self):
        assert tables_to_markdown([]) == ""

    def test_single_table_has_pipes(self):
        tables = [
            [["Name", "Price"], ["Hampta Pass", "12000"]]
        ]
        result = tables_to_markdown(tables)
        assert "|" in result

    def test_header_separator_present(self):
        tables = [
            [["Name", "Price"], ["Item", "100"]]
        ]
        result = tables_to_markdown(tables)
        assert "---" in result

    def test_multiple_tables(self):
        tables = [
            [["A", "B"], ["1", "2"]],
            [["X", "Y"], ["3", "4"]],
        ]
        result = tables_to_markdown(tables)
        assert "Table 1" in result
        assert "Table 2" in result

    def test_skips_empty_tables(self):
        tables = [[], [["A"], ["1"]]]
        result = tables_to_markdown(tables)
        assert "|" in result  # Should still produce output for non-empty

    def test_pads_short_rows(self):
        # Row has fewer cells than headers
        tables = [
            [["A", "B", "C"], ["1"]]
        ]
        result = tables_to_markdown(tables)
        # Should not raise an error
        assert "|" in result

    def test_truncates_long_rows(self):
        tables = [
            [["A", "B"], ["1", "2", "3", "4"]]
        ]
        result = tables_to_markdown(tables)
        # Should not raise; extra cells are trimmed
        assert "|" in result


# =============================================================================
# truncate_text
# =============================================================================

class TestTruncateText:

    def test_short_text_unchanged(self):
        text = "Hello world"
        assert truncate_text(text, max_chars=1000) == text

    def test_long_text_is_truncated(self):
        text = "a" * 60000
        result = truncate_text(text, max_chars=50000)
        assert len(result) <= 50100  # a bit of leeway for the ellipsis

    def test_truncated_text_ends_with_marker(self):
        text = "word " * 20000
        result = truncate_text(text, max_chars=100)
        assert "[... text truncated ...]" in result

    def test_respects_word_boundary(self):
        # 'hello world foo bar baz' is 23 chars. Limit to 6 chars forces truncation.
        # The function looks for last space before max_chars. 'hello ' has a space at
        # position 5, so it should cut at 'hello' (not 'hello w' = mid-word).
        text = "hello world foo bar baz"
        result = truncate_text(text, max_chars=6)
        # Must not end mid-word; the truncation marker should be present
        assert "[... text truncated ...]" in result
        # The kept portion should not cut through "world"
        assert "wor" not in result.split("[... text truncated ...]")[0]


# =============================================================================
# count_tokens_estimate
# =============================================================================

class TestCountTokensEstimate:

    def test_empty_string(self):
        assert count_tokens_estimate("") == 0

    def test_known_length(self):
        text = "a" * 400
        assert count_tokens_estimate(text) == 100  # 400 / 4

    def test_proportional(self):
        t1 = count_tokens_estimate("abc" * 100)
        t2 = count_tokens_estimate("abc" * 200)
        assert t2 == t1 * 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
