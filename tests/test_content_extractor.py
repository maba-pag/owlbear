"""Tests for browser content_extractor — trafilatura-based HTML extraction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.tools.browser.content_extractor import ExtractionResult, extract_content


@pytest.fixture(autouse=True)
def _disable_wrap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable content wrapping so tests verify raw extraction logic."""
    monkeypatch.setenv("OWLBEAR_WRAP_WEB_CONTENT", "false")

# ---------------------------------------------------------------------------
# ExtractionResult model tests
# ---------------------------------------------------------------------------


class TestExtractionResult:
    """ExtractionResult is a frozen Pydantic model with the right fields."""

    def test_fields_present(self):
        """ExtractionResult has text, title, author, date, metadata."""
        result = ExtractionResult(
            text="hello",
            title="Title",
            author="Author",
            date="2026-01-01",
            metadata={"key": "value"},
        )
        assert result.text == "hello"
        assert result.title == "Title"
        assert result.author == "Author"
        assert result.date == "2026-01-01"
        assert result.metadata == {"key": "value"}

    def test_frozen(self):
        """ExtractionResult instances are immutable."""
        result = ExtractionResult(text="x", title=None, author=None, date=None, metadata={})
        with pytest.raises(ValidationError):
            result.text = "changed"  # type: ignore[misc]

    def test_optional_fields_default_none(self):
        """title, author, date default to None; metadata defaults to empty dict."""
        result = ExtractionResult(text="body")
        assert result.title is None
        assert result.author is None
        assert result.date is None
        assert result.metadata == {}


# ---------------------------------------------------------------------------
# extract_content() tests — trafilatura fully mocked
# ---------------------------------------------------------------------------


class TestExtractContent:
    """extract_content() delegates to trafilatura and returns ExtractionResult."""

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_happy_path(self, mock_traf):
        """Returns ExtractionResult with extracted text and metadata."""
        mock_traf.extract.return_value = "# Extracted Markdown"
        mock_meta = MagicMock()
        mock_meta.title = "Page Title"
        mock_meta.author = "Jane Doe"
        mock_meta.date = "2026-02-27"
        mock_traf.extract_metadata.return_value = mock_meta

        result = extract_content("<html><body>Hello</body></html>")

        assert type(result).__name__ == "ExtractionResult"
        assert result.text == "# Extracted Markdown"
        assert result.title == "Page Title"
        assert result.author == "Jane Doe"
        assert result.date == "2026-02-27"

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_calls_extract_with_markdown_format(self, mock_traf):
        """Calls trafilatura.extract with output_format='markdown'."""
        mock_traf.extract.return_value = "text"
        mock_traf.extract_metadata.return_value = None

        html = "<html><body>content</body></html>"
        extract_content(html)

        mock_traf.extract.assert_called_once()
        call_kwargs = mock_traf.extract.call_args
        assert call_kwargs.kwargs.get("output_format") == "markdown"
        assert call_kwargs.kwargs.get("include_links") is True

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_passes_url_to_trafilatura(self, mock_traf):
        """Passes url parameter to trafilatura for link resolution."""
        mock_traf.extract.return_value = "text"
        mock_traf.extract_metadata.return_value = None

        extract_content("<html></html>", url="https://example.com/page")

        call_kwargs = mock_traf.extract.call_args
        assert call_kwargs.kwargs.get("url") == "https://example.com/page"

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_extract_returns_none_gives_empty_text(self, mock_traf):
        """Returns ExtractionResult with text='' when extract returns None."""
        mock_traf.extract.return_value = None
        mock_traf.extract_metadata.return_value = None

        result = extract_content("<html></html>")

        assert result.text == ""

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_extract_metadata_returns_none(self, mock_traf):
        """Handles None from extract_metadata gracefully."""
        mock_traf.extract.return_value = "some text"
        mock_traf.extract_metadata.return_value = None

        result = extract_content("<html></html>")

        assert result.text == "some text"
        assert result.title is None
        assert result.author is None
        assert result.date is None
        assert result.metadata == {}

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_no_exception_on_extraction_failure(self, mock_traf):
        """Does not raise on trafilatura failure — returns empty result."""
        mock_traf.extract.side_effect = Exception("parsing failed")
        mock_traf.extract_metadata.return_value = None

        result = extract_content("<html></html>")

        assert result.text == ""
        assert result.title is None

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_metadata_dict_populated(self, mock_traf):
        """Metadata dict contains title, author, date from extract_metadata."""
        mock_traf.extract.return_value = "body"
        mock_meta = MagicMock()
        mock_meta.title = "T"
        mock_meta.author = "A"
        mock_meta.date = "D"
        mock_traf.extract_metadata.return_value = mock_meta

        result = extract_content("<html></html>")

        assert "title" in result.metadata
        assert "author" in result.metadata
        assert "date" in result.metadata
        assert result.metadata["title"] == "T"

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_url_defaults_to_none(self, mock_traf):
        """url parameter defaults to None when not provided."""
        mock_traf.extract.return_value = "text"
        mock_traf.extract_metadata.return_value = None

        extract_content("<html></html>")

        call_kwargs = mock_traf.extract.call_args
        assert call_kwargs.kwargs.get("url") is None

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    def test_metadata_extraction_failure_graceful(self, mock_traf):
        """If extract_metadata raises, still returns result with text."""
        mock_traf.extract.return_value = "good text"
        mock_traf.extract_metadata.side_effect = Exception("metadata fail")

        result = extract_content("<html></html>")

        assert result.text == "good text"
        assert result.title is None
        assert result.metadata == {}
