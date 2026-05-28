"""Tests for CompositeSourceFetcher — task #1909.

Target: serve/knowledge/src/owlbear_knowledge/source_fetcher.py

AC coverage:
  AC1 — CompositeSourceFetcher satisfies SourceFetcher protocol (isinstance passes)
  AC2 — URL_LIST: iterates urls, one FetchedDocument per success, one FetchError per failure
  AC3 — FILE_GLOB: resolves patterns, deduplicates paths, one FetchedDocument per readable file
  AC4 — AUTHENTICATED_WEB: calls factory(fetch_method).fetch(base_url), returns one FetchedDocument
  AC5 — INLINE: returns FetchResult(documents=(), errors=())
  AC6 — Cancellation: cancel.is_set()=True between items stops iteration, partial results returned
  AC7 — Item-level exceptions caught as FetchError(uri=..., error=str(exc)); never raises
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.protocols.fetcher import FetchError, FetchResult, SourceFetcher
from owlbear_knowledge.protocols.sources import (
    AuthenticatedWebConfig,
    ConfiguredSourceRecord,
    FetchTransport,
    FileGlobConfig,
    InlineConfig,
    SourceHealth,
    SourceKind,
    SourceState,
    UrlListConfig,
)
from owlbear_knowledge.source_fetcher import CompositeSourceFetcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(
    kind: SourceKind,
    config: object,
    *,
    fetch_method: FetchTransport = FetchTransport.HTTP,
    source_id: str = "src-1",
) -> ConfiguredSourceRecord:
    return ConfiguredSourceRecord(
        id=source_id,
        name=f"Source {source_id}",
        state=SourceState.ACTIVE,
        kind=kind,
        fetch_method=fetch_method,
        config=config,  # type: ignore[arg-type]
        health=SourceHealth.UNKNOWN,
        refreshable=True,
        enrich=False,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _url_source(urls: tuple[str, ...], source_id: str = "src-url") -> ConfiguredSourceRecord:
    return _make_source(
        SourceKind.URL_LIST,
        UrlListConfig(urls=urls),
        fetch_method=FetchTransport.HTTP,
        source_id=source_id,
    )


def _file_source(
    patterns: tuple[str, ...],
    base_path: str = ".",
    *,
    follow_symlinks: bool = False,
    source_id: str = "src-file",
) -> ConfiguredSourceRecord:
    return _make_source(
        SourceKind.FILE_GLOB,
        FileGlobConfig(patterns=patterns, base_path=base_path, follow_symlinks=follow_symlinks),
        fetch_method=FetchTransport.FILESYSTEM,
        source_id=source_id,
    )


def _auth_source(
    base_url: str = "https://internal.example.com",
    fetch_method: FetchTransport = FetchTransport.BROWSER,
    source_id: str = "src-auth",
) -> ConfiguredSourceRecord:
    return _make_source(
        SourceKind.AUTHENTICATED_WEB,
        AuthenticatedWebConfig(base_url=base_url, auth_profile="default"),
        fetch_method=fetch_method,
        source_id=source_id,
    )


def _inline_source(source_id: str = "src-inline") -> ConfiguredSourceRecord:
    return _make_source(
        SourceKind.INLINE,
        InlineConfig(),
        fetch_method=FetchTransport.NONE,
        source_id=source_id,
    )


def _intake_result(content: str, source: str) -> IntakeResult:
    return IntakeResult(
        content=content,
        source=source,
        metadata={"source_type": "url", "fetched_at": datetime.now(tz=UTC).isoformat()},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_factory() -> MagicMock:
    """Content fetcher factory returning an AsyncMock ContentFetcher."""
    fetcher = AsyncMock()
    fetcher.fetch = AsyncMock(return_value="authenticated content")
    return MagicMock(return_value=fetcher)


@pytest.fixture()
def composite(tmp_path: Path, mock_factory: MagicMock) -> CompositeSourceFetcher:
    return CompositeSourceFetcher(
        workspace_root=tmp_path,
        content_fetcher_factory=mock_factory,
    )


# ---------------------------------------------------------------------------
# TestFromAC_CompositeSourceFetcher
# ---------------------------------------------------------------------------


class TestCompositeSourceFetcher:
    # ------------------------------------------------------------------ #
    # AC1 — Protocol conformance                                           #
    # ------------------------------------------------------------------ #

    def test_isinstance_source_fetcher_protocol(self, composite: CompositeSourceFetcher) -> None:
        """CompositeSourceFetcher must satisfy the SourceFetcher runtime protocol."""
        assert isinstance(composite, SourceFetcher)

    # ------------------------------------------------------------------ #
    # AC2 — URL_LIST                                                       #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_url_list_single_url_returns_one_document(self, composite: CompositeSourceFetcher) -> None:
        url = "https://example.com/page"
        source = _url_source((url,))
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            return_value=_intake_result("page content", url),
        ):
            result = await composite.fetch_source(source)
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_url_list_document_title_equals_url(self, composite: CompositeSourceFetcher) -> None:
        url = "https://example.com/page"
        source = _url_source((url,))
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            return_value=_intake_result("page content", url),
        ):
            result = await composite.fetch_source(source)
        assert result.documents[0].title == url

    @pytest.mark.asyncio
    async def test_url_list_document_text_equals_fetched_content(self, composite: CompositeSourceFetcher) -> None:
        url = "https://example.com/article"
        source = _url_source((url,))
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            return_value=_intake_result("article body", url),
        ):
            result = await composite.fetch_source(source)
        assert result.documents[0].text == "article body"

    @pytest.mark.asyncio
    async def test_url_list_document_uri_equals_url(self, composite: CompositeSourceFetcher) -> None:
        url = "https://example.com/resource"
        source = _url_source((url,))
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            return_value=_intake_result("content", url),
        ):
            result = await composite.fetch_source(source)
        assert result.documents[0].uri == url

    @pytest.mark.asyncio
    async def test_url_list_multiple_urls_returns_one_document_per_url(self, composite: CompositeSourceFetcher) -> None:
        urls = (
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        )
        source = _url_source(urls)
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=[_intake_result(f"content-{i}", u) for i, u in enumerate(urls)],
        ):
            result = await composite.fetch_source(source)
        assert len(result.documents) == 3

    @pytest.mark.asyncio
    async def test_url_list_empty_urls_returns_empty_fetch_result(self, composite: CompositeSourceFetcher) -> None:
        source = _url_source(())
        result = await composite.fetch_source(source)
        assert isinstance(result, FetchResult)
        assert len(result.documents) == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_url_list_failed_url_captured_as_fetch_error(self, composite: CompositeSourceFetcher) -> None:
        url = "https://bad.example.com/missing"
        source = _url_source((url,))
        exc = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", url),
            response=httpx.Response(404),
        )
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=exc,
        ):
            result = await composite.fetch_source(source)
        assert len(result.documents) == 0
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], FetchError)

    @pytest.mark.asyncio
    async def test_url_list_fetch_error_uri_equals_failed_url(self, composite: CompositeSourceFetcher) -> None:
        url = "https://bad.example.com/missing"
        source = _url_source((url,))
        exc = httpx.HTTPStatusError(
            "404",
            request=httpx.Request("GET", url),
            response=httpx.Response(404),
        )
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=exc,
        ):
            result = await composite.fetch_source(source)
        assert result.errors[0].uri == url

    @pytest.mark.asyncio
    async def test_url_list_fetch_error_message_equals_str_exception(self, composite: CompositeSourceFetcher) -> None:
        url = "https://bad.example.com/timeout"
        source = _url_source((url,))
        exc = httpx.HTTPStatusError(
            "503 Service Unavailable",
            request=httpx.Request("GET", url),
            response=httpx.Response(503),
        )
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=exc,
        ):
            result = await composite.fetch_source(source)
        assert result.errors[0].error == str(exc)

    @pytest.mark.asyncio
    async def test_url_list_batch_continues_after_url_failure(self, composite: CompositeSourceFetcher) -> None:
        url_bad = "https://bad.example.com/fail"
        url_good = "https://example.com/ok"
        source = _url_source((url_bad, url_good))
        exc = httpx.HTTPStatusError(
            "500",
            request=httpx.Request("GET", url_bad),
            response=httpx.Response(500),
        )
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=[exc, _intake_result("good content", url_good)],
        ):
            result = await composite.fetch_source(source)
        assert len(result.documents) == 1
        assert len(result.errors) == 1
        assert result.documents[0].uri == url_good

    # ------------------------------------------------------------------ #
    # AC3 — FILE_GLOB                                                      #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_file_glob_single_pattern_returns_one_document_per_file(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        (tmp_path / "doc.txt").write_text("hello world", encoding="utf-8")
        source = _file_source(("*.txt",))
        result = await composite.fetch_source(source)
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_file_glob_document_text_equals_file_content(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        (tmp_path / "report.txt").write_text("report content here", encoding="utf-8")
        source = _file_source(("*.txt",))
        result = await composite.fetch_source(source)
        assert result.documents[0].text == "report content here"

    @pytest.mark.asyncio
    async def test_file_glob_pattern_matching_no_files_returns_empty(self, composite: CompositeSourceFetcher) -> None:
        source = _file_source(("*.nonexistent",))
        result = await composite.fetch_source(source)
        assert isinstance(result, FetchResult)
        assert len(result.documents) == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_file_glob_multiple_patterns_returns_one_document_per_file(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        (tmp_path / "a.txt").write_text("file a", encoding="utf-8")
        (tmp_path / "b.md").write_text("file b", encoding="utf-8")
        source = _file_source(("*.txt", "*.md"))
        result = await composite.fetch_source(source)
        assert len(result.documents) == 2

    @pytest.mark.asyncio
    async def test_file_glob_deduplicates_paths_across_patterns(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        """Two patterns matching the same file must yield exactly one FetchedDocument."""
        (tmp_path / "shared.txt").write_text("shared content", encoding="utf-8")
        source = _file_source(("*.txt", "shared*.txt"))
        result = await composite.fetch_source(source)
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_file_glob_file_not_found_captured_as_fetch_error(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        """FileNotFoundError during file read is captured as FetchError."""
        (tmp_path / "target.txt").write_text("data", encoding="utf-8")
        source = _file_source(("*.txt",))
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_file",
            new_callable=AsyncMock,
            side_effect=FileNotFoundError("gone"),
        ):
            result = await composite.fetch_source(source)
        assert len(result.errors) >= 1
        assert isinstance(result.errors[0], FetchError)

    @pytest.mark.asyncio
    async def test_file_glob_permission_error_captured_as_fetch_error(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        """PermissionError (sandbox escape) during read is captured as FetchError."""
        (tmp_path / "restricted.txt").write_text("data", encoding="utf-8")
        source = _file_source(("*.txt",))
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_file",
            new_callable=AsyncMock,
            side_effect=PermissionError("path escapes sandbox"),
        ):
            result = await composite.fetch_source(source)
        assert len(result.errors) >= 1
        assert isinstance(result.errors[0], FetchError)

    # ------------------------------------------------------------------ #
    # AC4 — AUTHENTICATED_WEB                                              #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_auth_web_calls_factory_with_source_fetch_method(
        self, composite: CompositeSourceFetcher, mock_factory: MagicMock
    ) -> None:
        source = _auth_source(fetch_method=FetchTransport.BROWSER)
        await composite.fetch_source(source)
        mock_factory.assert_called_once_with(FetchTransport.BROWSER)

    @pytest.mark.asyncio
    async def test_auth_web_calls_content_fetcher_fetch_with_base_url(
        self, composite: CompositeSourceFetcher, mock_factory: MagicMock
    ) -> None:
        base_url = "https://internal.example.com/docs"
        source = _auth_source(base_url=base_url)
        await composite.fetch_source(source)
        mock_factory.return_value.fetch.assert_called_once_with(base_url)

    @pytest.mark.asyncio
    async def test_auth_web_returns_exactly_one_document(self, composite: CompositeSourceFetcher) -> None:
        result = await composite.fetch_source(_auth_source())
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_auth_web_document_title_equals_base_url(self, composite: CompositeSourceFetcher) -> None:
        base_url = "https://internal.example.com/wiki"
        result = await composite.fetch_source(_auth_source(base_url=base_url))
        assert result.documents[0].title == base_url

    @pytest.mark.asyncio
    async def test_auth_web_document_text_equals_fetched_content(
        self, composite: CompositeSourceFetcher, mock_factory: MagicMock
    ) -> None:
        mock_factory.return_value.fetch = AsyncMock(return_value="wiki content")
        result = await composite.fetch_source(_auth_source())
        assert result.documents[0].text == "wiki content"

    @pytest.mark.asyncio
    async def test_auth_web_document_uri_equals_base_url(self, composite: CompositeSourceFetcher) -> None:
        base_url = "https://internal.example.com/api"
        result = await composite.fetch_source(_auth_source(base_url=base_url))
        assert result.documents[0].uri == base_url

    @pytest.mark.asyncio
    async def test_auth_web_content_fetcher_failure_appended_as_fetch_error(
        self, composite: CompositeSourceFetcher, mock_factory: MagicMock
    ) -> None:
        mock_factory.return_value.fetch = AsyncMock(side_effect=RuntimeError("browser failed"))
        result = await composite.fetch_source(_auth_source())
        assert len(result.documents) == 0
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], FetchError)

    @pytest.mark.asyncio
    async def test_auth_web_fetch_error_uri_equals_base_url(
        self, composite: CompositeSourceFetcher, mock_factory: MagicMock
    ) -> None:
        base_url = "https://internal.example.com/secure"
        mock_factory.return_value.fetch = AsyncMock(side_effect=RuntimeError("auth failed"))
        result = await composite.fetch_source(_auth_source(base_url=base_url))
        assert result.errors[0].uri == base_url

    # ------------------------------------------------------------------ #
    # AC5 — INLINE                                                         #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_inline_returns_fetch_result_instance(self, composite: CompositeSourceFetcher) -> None:
        result = await composite.fetch_source(_inline_source())
        assert isinstance(result, FetchResult)

    @pytest.mark.asyncio
    async def test_inline_documents_tuple_is_empty(self, composite: CompositeSourceFetcher) -> None:
        result = await composite.fetch_source(_inline_source())
        assert result.documents == ()

    @pytest.mark.asyncio
    async def test_inline_errors_tuple_is_empty(self, composite: CompositeSourceFetcher) -> None:
        result = await composite.fetch_source(_inline_source())
        assert result.errors == ()

    # ------------------------------------------------------------------ #
    # AC6 — Cancellation                                                   #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_cancel_stops_url_iteration_not_all_items_fetched(self, composite: CompositeSourceFetcher) -> None:
        """When cancel fires, fewer than N reads happen for N URLs."""
        urls = (
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        )
        source = _url_source(urls)
        cancel = MagicMock()
        cancel.is_set.return_value = True  # always cancel
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            return_value=_intake_result("content", urls[0]),
        ) as mock_read:
            result = await composite.fetch_source(source, cancel=cancel)
        assert isinstance(result, FetchResult)
        assert mock_read.call_count < 3

    @pytest.mark.asyncio
    async def test_cancel_returns_partial_results_collected_before_cancel(
        self, composite: CompositeSourceFetcher
    ) -> None:
        """Documents fetched before cancel fires are present in the returned FetchResult."""
        urls = (
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        )
        source = _url_source(urls)
        cancel = MagicMock()
        # returns False once then True — fires between first and second items
        cancel.is_set.side_effect = [False, True, True]
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=[_intake_result(f"content-{i}", u) for i, u in enumerate(urls)],
        ):
            result = await composite.fetch_source(source, cancel=cancel)
        assert isinstance(result, FetchResult)
        # at least one doc returned (before cancel) but not all three
        assert 0 < len(result.documents) < 3

    @pytest.mark.asyncio
    async def test_cancel_none_processes_all_urls(self, composite: CompositeSourceFetcher) -> None:
        """cancel=None means no cancellation — all URLs processed."""
        urls = ("https://example.com/x", "https://example.com/y")
        source = _url_source(urls)
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=[_intake_result("content", u) for u in urls],
        ):
            result = await composite.fetch_source(source, cancel=None)
        assert len(result.documents) == 2

    @pytest.mark.asyncio
    async def test_cancel_stops_file_glob_iteration_not_all_files_read(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        """When cancel fires between FILE_GLOB items, fewer than N reads happen."""
        for i in range(3):
            (tmp_path / f"file{i}.txt").write_text(f"content {i}", encoding="utf-8")
        source = _file_source(("*.txt",))
        cancel = MagicMock()
        cancel.is_set.return_value = True  # always cancel
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_file",
            new_callable=AsyncMock,
            return_value=_intake_result("content", "file0.txt"),
        ) as mock_read:
            result = await composite.fetch_source(source, cancel=cancel)
        assert isinstance(result, FetchResult)
        assert mock_read.call_count < 3

    # ------------------------------------------------------------------ #
    # AC7 — Item-level exceptions never raised                             #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_http_status_error_caught_as_fetch_error_not_raised(self, composite: CompositeSourceFetcher) -> None:
        url = "https://example.com/gone"
        source = _url_source((url,))
        exc = httpx.HTTPStatusError(
            "404",
            request=httpx.Request("GET", url),
            response=httpx.Response(404),
        )
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=exc,
        ):
            result = await composite.fetch_source(source)  # must not raise
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_file_not_found_error_caught_as_fetch_error_not_raised(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        (tmp_path / "present.txt").write_text("data", encoding="utf-8")
        source = _file_source(("*.txt",))
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_file",
            new_callable=AsyncMock,
            side_effect=FileNotFoundError("file vanished"),
        ):
            result = await composite.fetch_source(source)  # must not raise
        assert len(result.errors) >= 1

    @pytest.mark.asyncio
    async def test_permission_error_caught_as_fetch_error_not_raised(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        (tmp_path / "restricted.txt").write_text("data", encoding="utf-8")
        source = _file_source(("*.txt",))
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_file",
            new_callable=AsyncMock,
            side_effect=PermissionError("access denied"),
        ):
            result = await composite.fetch_source(source)  # must not raise
        assert len(result.errors) >= 1

    @pytest.mark.asyncio
    async def test_content_fetcher_exception_caught_as_fetch_error_not_raised(
        self, composite: CompositeSourceFetcher, mock_factory: MagicMock
    ) -> None:
        mock_factory.return_value.fetch = AsyncMock(side_effect=Exception("browser crash"))
        result = await composite.fetch_source(_auth_source())  # must not raise
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_url_fetch_error_error_field_equals_str_of_exception(self, composite: CompositeSourceFetcher) -> None:
        url = "https://example.com/page"
        source = _url_source((url,))
        exc = httpx.HTTPStatusError(
            "503 Service Unavailable",
            request=httpx.Request("GET", url),
            response=httpx.Response(503),
        )
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_url",
            new_callable=AsyncMock,
            side_effect=exc,
        ):
            result = await composite.fetch_source(source)
        assert result.errors[0].error == str(exc)

    # ------------------------------------------------------------------ #
    # AC3 retry gap — non-default base_path                                #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_file_glob_non_default_base_path_globs_relative_to_base_path(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        """Globbing must use config.base_path, not workspace_root.

        Two txt files at workspace root; one txt file in a 'docs' subdirectory.
        A source configured with base_path='docs' must return exactly one document
        (the subdir file). If base_path were ignored and workspace_root were used,
        two documents would be returned.
        """
        (tmp_path / "root_a.txt").write_text("root file a", encoding="utf-8")
        (tmp_path / "root_b.txt").write_text("root file b", encoding="utf-8")
        subdir = tmp_path / "docs"
        subdir.mkdir()
        (subdir / "manual.txt").write_text("manual content", encoding="utf-8")
        source = _file_source(("*.txt",), base_path="docs")
        result = await composite.fetch_source(source)
        assert len(result.documents) == 1
        assert result.documents[0].text == "manual content"

    # ------------------------------------------------------------------ #
    # AC7 retry gaps — exact FetchError payload                            #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_file_glob_file_not_found_fetch_error_uri_and_error_exact(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        """FILE_GLOB FileNotFoundError → FetchError.uri equals matched path str, .error equals str(exc)."""
        (tmp_path / "target.txt").write_text("data", encoding="utf-8")
        source = _file_source(("*.txt",))
        exc = FileNotFoundError("file vanished")
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_file",
            new_callable=AsyncMock,
            side_effect=exc,
        ):
            result = await composite.fetch_source(source)
        assert len(result.errors) == 1
        expected_uri = str((tmp_path / "target.txt").resolve())
        assert result.errors[0].uri == expected_uri
        assert result.errors[0].error == str(exc)

    @pytest.mark.asyncio
    async def test_file_glob_permission_error_fetch_error_uri_and_error_exact(
        self, composite: CompositeSourceFetcher, tmp_path: Path
    ) -> None:
        """FILE_GLOB PermissionError → FetchError.uri equals matched path str, .error equals str(exc)."""
        (tmp_path / "restricted.txt").write_text("data", encoding="utf-8")
        source = _file_source(("*.txt",))
        exc = PermissionError("path escapes sandbox")
        with patch(
            "owlbear_knowledge.source_fetcher.intake.read_file",
            new_callable=AsyncMock,
            side_effect=exc,
        ):
            result = await composite.fetch_source(source)
        assert len(result.errors) == 1
        expected_uri = str((tmp_path / "restricted.txt").resolve())
        assert result.errors[0].uri == expected_uri
        assert result.errors[0].error == str(exc)

    @pytest.mark.asyncio
    async def test_auth_web_fetch_error_error_equals_str_of_exception(
        self, composite: CompositeSourceFetcher, mock_factory: MagicMock
    ) -> None:
        """AUTHENTICATED_WEB failure → FetchError.error equals str(exc) per AC7 contract."""
        exc = RuntimeError("browser connection timed out")
        mock_factory.return_value.fetch = AsyncMock(side_effect=exc)
        result = await composite.fetch_source(_auth_source())
        assert result.errors[0].error == str(exc)
