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
# extract_content() tests — post-#875 extract_markdown delegation seam
# ---------------------------------------------------------------------------


class TestFromAC_ExtractMarkdownDelegation:
    """After #875, extract_content() delegates text extraction to extract_markdown.

    Failure contract (pre-#875 / RED):
        Patching owlbear.tools.browser.content_extractor.extract_markdown raises
        AttributeError because that name is not yet imported in the module.  All
        tests in this class therefore error before #875 is implemented.

    AC coverage:
        AC2 — success path, one delegation call, metadata fields preserved
        AC3 — default-url and provided-url forwarding
        AC4 — empty helper output and local extract_metadata failure
        AC5 — no direct trafilatura.extract assertion in any test
    """

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_success_path_delegates_to_extract_markdown(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """extract_content() delegates text extraction and preserves metadata fields."""
        mock_extract_md.return_value = "# Extracted Markdown"
        mock_meta = MagicMock()
        mock_meta.title = "Page Title"
        mock_meta.author = "Jane Doe"
        mock_meta.date = "2026-02-27"
        mock_traf.extract_metadata.return_value = mock_meta

        html = "<html><body>Hello</body></html>"
        result = extract_content(html, url="https://example.com/page")

        mock_extract_md.assert_called_once_with(html, url="https://example.com/page")
        assert type(result).__name__ == "ExtractionResult"
        assert result.text == "# Extracted Markdown"
        assert result.title == "Page Title"
        assert result.author == "Jane Doe"
        assert result.date == "2026-02-27"

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_exactly_one_delegation_call(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """extract_content() calls extract_markdown exactly once per invocation."""
        mock_extract_md.return_value = "text"
        mock_traf.extract_metadata.return_value = None

        extract_content("<html><body>x</body></html>", url="https://example.com")

        assert mock_extract_md.call_count == 1

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_no_direct_trafilatura_extract_called(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """extract_markdown delegation replaces direct trafilatura.extract calls."""
        mock_extract_md.return_value = "text"
        mock_traf.extract_metadata.return_value = None

        extract_content("<html></html>")

        mock_traf.extract.assert_not_called()

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_default_url_calls_extract_markdown_with_none(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """When no URL is provided, extract_markdown is called with url=None."""
        mock_extract_md.return_value = "text"
        mock_traf.extract_metadata.return_value = None

        html = "<html><body>content</body></html>"
        extract_content(html)

        mock_extract_md.assert_called_once_with(html, url=None)

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_provided_url_forwarded_unchanged(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """Provided URL is forwarded unchanged to extract_markdown."""
        mock_extract_md.return_value = "text"
        mock_traf.extract_metadata.return_value = None

        url = "https://example.com/article?q=test#section"
        extract_content("<html></html>", url=url)

        mock_extract_md.assert_called_once_with("<html></html>", url=url)

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_empty_helper_output_gives_empty_text(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """Empty string from extract_markdown results in ExtractionResult.text=''."""
        mock_extract_md.return_value = ""
        mock_traf.extract_metadata.return_value = None

        result = extract_content("<html></html>")

        assert result.text == ""

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_local_extract_metadata_failure_graceful(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """If extract_metadata raises locally, result carries text but empty metadata."""
        mock_extract_md.return_value = "good text"
        mock_traf.extract_metadata.side_effect = Exception("metadata fail")

        result = extract_content("<html></html>")

        assert result.text == "good text"
        assert result.title is None
        assert result.author is None
        assert result.date is None
        assert result.metadata == {}

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_extract_metadata_none_gives_empty_metadata(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """None from extract_metadata leaves metadata={} and all fields None."""
        mock_extract_md.return_value = "text"
        mock_traf.extract_metadata.return_value = None

        result = extract_content("<html></html>")

        assert result.title is None
        assert result.author is None
        assert result.date is None
        assert result.metadata == {}

    @patch("owlbear.tools.browser.content_extractor.trafilatura")
    @patch("owlbear.tools.browser.content_extractor.extract_markdown")
    def test_metadata_fields_preserved_in_result(
        self, mock_extract_md: MagicMock, mock_traf: MagicMock
    ) -> None:
        """ExtractionResult.metadata dict contains title, author, date from extract_metadata."""
        mock_extract_md.return_value = "body"
        mock_meta = MagicMock()
        mock_meta.title = "T"
        mock_meta.author = "A"
        mock_meta.date = "D"
        mock_traf.extract_metadata.return_value = mock_meta

        result = extract_content("<html></html>")

        assert result.metadata.get("title") == "T"
        assert result.metadata.get("author") == "A"
        assert result.metadata.get("date") == "D"
