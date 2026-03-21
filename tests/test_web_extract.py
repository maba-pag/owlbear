"""Tests for owlbear.web_extract — extract_markdown helper contract.

Focused tests for the package-root leaf helper at the helper boundary.
Does NOT cover downstream caller rewires (content_extractor, bookmark_pipeline,
context_hydration) — those are tracked in #875, #825, and #873.
"""

from __future__ import annotations

import builtins
from unittest.mock import MagicMock, patch

import pytest
from owlbear.web_extract import extract_markdown

# ===========================================================================
# AC2 — Success path: one trafilatura.extract call with correct kwargs
# ===========================================================================


class TestFromAC_ExtractMarkdownSuccess:
    """Success-path cases patch the helper-local trafilatura lookup.

    Asserts one call to trafilatura.extract(html, output_format="markdown",
    include_links=True, url=url) and that the raw markdown string is returned.
    """

    @patch("owlbear.web_extract.trafilatura")
    def test_returns_extracted_markdown(self, mock_traf: MagicMock) -> None:
        """Success path returns the raw markdown string from trafilatura.extract."""
        mock_traf.extract.return_value = "# Hello World"
        result = extract_markdown("<html><body>Hello</body></html>")
        assert result == "# Hello World"

    @patch("owlbear.web_extract.trafilatura")
    def test_calls_trafilatura_with_correct_kwargs(self, mock_traf: MagicMock) -> None:
        """extract_markdown calls trafilatura.extract with output_format, include_links, and url."""
        mock_traf.extract.return_value = "# Content"
        html = "<html><body>Content</body></html>"
        extract_markdown(html)
        mock_traf.extract.assert_called_once_with(
            html,
            output_format="markdown",
            include_links=True,
            url=None,
        )

    @patch("owlbear.web_extract.trafilatura")
    def test_exactly_one_trafilatura_extract_call(self, mock_traf: MagicMock) -> None:
        """extract_markdown makes exactly one call to trafilatura.extract per invocation."""
        mock_traf.extract.return_value = "content"
        extract_markdown("<p>text</p>")
        assert mock_traf.extract.call_count == 1


# ===========================================================================
# AC3 — URL forwarding: default None and explicit URL passed unchanged
# ===========================================================================


class TestFromAC_ExtractMarkdownUrlForwarding:
    """url defaults to None; a provided URL is forwarded to trafilatura.extract unchanged."""

    @patch("owlbear.web_extract.trafilatura")
    def test_default_url_is_none(self, mock_traf: MagicMock) -> None:
        """When url is omitted, trafilatura.extract receives url=None."""
        mock_traf.extract.return_value = "content"
        extract_markdown("<p>x</p>")
        mock_traf.extract.assert_called_once_with(
            "<p>x</p>",
            output_format="markdown",
            include_links=True,
            url=None,
        )

    @patch("owlbear.web_extract.trafilatura")
    def test_provided_url_forwarded_unchanged(self, mock_traf: MagicMock) -> None:
        """A provided URL is forwarded to trafilatura.extract unchanged."""
        url = "https://example.com/article"
        mock_traf.extract.return_value = "content"
        extract_markdown("<p>x</p>", url=url)
        mock_traf.extract.assert_called_once_with(
            "<p>x</p>",
            output_format="markdown",
            include_links=True,
            url=url,
        )

    @patch("owlbear.web_extract.trafilatura")
    def test_url_forwarding_does_not_affect_return_value(self, mock_traf: MagicMock) -> None:
        """Providing a URL does not alter the returned markdown string."""
        mock_traf.extract.return_value = "# Article"
        result = extract_markdown("<p>x</p>", url="https://example.com")
        assert result == "# Article"


# ===========================================================================
# AC4 — Fallback: None or raised exception → empty string, no re-raise
# ===========================================================================


class TestFromAC_ExtractMarkdownFallback:
    """None and raised-exception fallbacks return '' without surfacing the error."""

    @patch("owlbear.web_extract.trafilatura")
    def test_returns_empty_string_when_extract_returns_none(self, mock_traf: MagicMock) -> None:
        """extract_markdown returns '' when trafilatura.extract returns None."""
        mock_traf.extract.return_value = None
        result = extract_markdown("<html></html>")
        assert result == ""

    @patch("owlbear.web_extract.trafilatura")
    def test_returns_empty_string_when_extract_raises(self, mock_traf: MagicMock) -> None:
        """extract_markdown returns '' when trafilatura.extract raises an exception."""
        mock_traf.extract.side_effect = RuntimeError("trafilatura crash")
        result = extract_markdown("<html></html>")
        assert result == ""

    @patch("owlbear.web_extract.trafilatura")
    def test_does_not_surface_extraction_exception(self, mock_traf: MagicMock) -> None:
        """extract_markdown never re-raises an exception from trafilatura.extract."""
        mock_traf.extract.side_effect = ValueError("unexpected parse error")
        try:
            result = extract_markdown("<html></html>")
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"extract_markdown raised unexpectedly: {exc}")
        assert isinstance(result, str)

    @patch("owlbear.web_extract.trafilatura")
    def test_empty_string_not_none_on_none_extract(self, mock_traf: MagicMock) -> None:
        """Return type is str, never None, when extraction returns None."""
        mock_traf.extract.return_value = None
        result = extract_markdown("<html><body>text</body></html>")
        assert result is not None
        assert isinstance(result, str)


# ===========================================================================
# AC5 — Missing dependency: narrow import-denial seam → actionable ImportError
# ===========================================================================


class TestFromAC_ExtractMarkdownMissingDependency:
    """Narrow import-denial seam at the helper boundary asserts actionable ImportError."""

    def test_raises_import_error_when_trafilatura_missing(self) -> None:
        """extract_markdown raises ImportError when trafilatura is not installed."""
        _real_import = builtins.__import__

        def _deny_trafilatura(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return _real_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=_deny_trafilatura),
            pytest.raises(ImportError),
        ):
            extract_markdown("<html></html>")

    def test_import_error_contains_owlbear_search_install_hint(self) -> None:
        """ImportError message contains the 'owlbear[search]' install hint."""
        _real_import = builtins.__import__

        def _deny_trafilatura(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return _real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_deny_trafilatura):
            with pytest.raises(ImportError) as exc_info:
                extract_markdown("<html></html>")
            assert "owlbear[search]" in str(exc_info.value)

    def test_import_error_message_references_uv(self) -> None:
        """ImportError message references 'uv' so the user knows what command to run."""
        _real_import = builtins.__import__

        def _deny_trafilatura(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return _real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_deny_trafilatura):
            with pytest.raises(ImportError) as exc_info:
                extract_markdown("<html></html>")
            assert "uv" in str(exc_info.value).lower()
