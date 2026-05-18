"""Failing tests for _direct_source_config HTTP branch retype (task #1656).

AC coverage:
  AC-1: _direct_source_config returns (SourceType.URL_LIST, "http", {...}) for HTTP/HTTPS URLs.
  AC-2: FILE_GLOB branch unchanged — covered by existing file:// tests in
        serve/mcp-knowledge/tests/test_direct_ingest_delta.py.
  AC-3: Existing AUTHENTICATED_WEB records not migrated — diff-verifiable, no migration code added.
  AC-4: Single-file change — diff-verifiable.
  AC-5: Focused unit test for _direct_source_config (this file); existing integration test
        test_metadata_url_creates_source_link_for_enrichment updated separately.
"""

from __future__ import annotations

from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.models import SourceType


class TestFromAC_DirectSourceConfig:
    """AC-1, AC-5: _direct_source_config returns URL_LIST for HTTP/HTTPS URLs."""

    def test_https_url_returns_url_list_type(self) -> None:
        """AC-1 happy: https:// URL returns SourceType.URL_LIST (not AUTHENTICATED_WEB)."""
        source_type, _, _ = IngestPipeline._direct_source_config("https://docs.example.com/page")
        assert source_type == SourceType.URL_LIST

    def test_http_url_returns_url_list_type(self) -> None:
        """AC-1 edge: http:// URL (plain, no TLS) also returns SourceType.URL_LIST."""
        source_type, _, _ = IngestPipeline._direct_source_config("http://example.com/doc")
        assert source_type == SourceType.URL_LIST

    def test_https_url_with_query_params_returns_url_list_type(self) -> None:
        """AC-1 edge: HTTPS URL with query parameters and path returns URL_LIST."""
        source_type, _, _ = IngestPipeline._direct_source_config("https://api.example.org/v1/data?format=json&lang=en")
        assert source_type == SourceType.URL_LIST

    def test_http_localhost_returns_url_list_not_file_glob(self) -> None:
        """AC-1 boundary: http://localhost is a network URL — returns URL_LIST, not FILE_GLOB.

        Note: file://localhost is handled by the local-path branch and returns FILE_GLOB.
        http://localhost has an http:// scheme, so it must go to the URL_LIST branch.
        """
        source_type, _, _ = IngestPipeline._direct_source_config("http://localhost/internal/page")
        assert source_type == SourceType.URL_LIST

    def test_https_url_full_return_tuple(self) -> None:
        """AC-1 / AC-5 focused unit: full return tuple for HTTP URL matches spec exactly."""
        url = "https://example.com/resource"
        result = IngestPipeline._direct_source_config(url)
        assert result == (
            SourceType.URL_LIST,
            "http",
            {"url": url, "urls": [url]},
        )
