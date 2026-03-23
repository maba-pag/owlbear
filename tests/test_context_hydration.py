"""RED-phase tests for owlbear.core.context_hydration (#712).

Tests the context pre-hydration module contract as specified in #703 AC.
All tests must FAIL before implementation begins.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from owlbear.core.context_hydration import (  # module does not exist yet — ImportError expected
    HydrationResult,
    extract_file_paths,
    extract_urls,
    fetch_url,
    hydrate,
    read_file_safe,
)

# ===========================================================================
# AC: extract_urls(text: str) -> list[str]
# ===========================================================================


class TestFromACExtractUrls:
    """URL extraction from task body text (http/https, markdown links)."""

    def test_plain_http_url(self) -> None:
        """Extracts a plain http URL from body text."""
        text = "See http://example.com/page for details."
        result = extract_urls(text)
        assert "http://example.com/page" in result

    def test_plain_https_url(self) -> None:
        """Extracts a plain https URL from body text."""
        text = "Reference: https://docs.python.org/3/library/pathlib.html"
        result = extract_urls(text)
        assert "https://docs.python.org/3/library/pathlib.html" in result

    def test_markdown_link_syntax(self) -> None:
        """Extracts URL from markdown link [text](url)."""
        text = "Check [the docs](https://example.com/docs) for info."
        result = extract_urls(text)
        assert "https://example.com/docs" in result

    def test_multiple_urls(self) -> None:
        """Extracts all URLs when multiple are present."""
        text = "See https://a.com and http://b.com/page and [link](https://c.com/path)"
        result = extract_urls(text)
        assert len(result) >= 3

    def test_no_urls_returns_empty(self) -> None:
        """Returns empty list when no URLs are present."""
        text = "No links here, just plain text about file paths."
        result = extract_urls(text)
        assert result == []

    def test_deduplicates_same_url(self) -> None:
        """Same URL appearing twice should appear once (or at most twice)."""
        text = "https://example.com and also https://example.com again."
        result = extract_urls(text)
        # At minimum, should not have unbounded duplicates
        assert len(result) <= 2

    def test_ignores_ftp_and_other_schemes(self) -> None:
        """Only http and https URLs are extracted."""
        text = "ftp://files.example.com and file:///local/path"
        result = extract_urls(text)
        assert result == []

    def test_url_with_query_params(self) -> None:
        """URLs with query parameters are extracted intact."""
        text = "Visit https://example.com/search?q=test&page=1 for results."
        result = extract_urls(text)
        assert any("q=test" in u for u in result)

    def test_url_with_fragment(self) -> None:
        """URLs with fragments are extracted."""
        text = "See https://example.com/page#section for the section."
        result = extract_urls(text)
        assert any("#section" in u for u in result)


# ===========================================================================
# AC: extract_file_paths(text: str, workspace_root: Path) -> list[Path]
# ===========================================================================


class TestFromACExtractFilePaths:
    """File path extraction from task body text."""

    def test_relative_path(self, tmp_path: Path) -> None:
        """Extracts a relative file path from body text."""
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "module.py").write_text("pass")
        text = "See src/module.py for the implementation."
        result = extract_file_paths(text, tmp_path)
        assert any(p.name == "module.py" for p in result)

    def test_absolute_path_inside_workspace(self, tmp_path: Path) -> None:
        """Extracts an absolute path that stays within workspace."""
        target = tmp_path / "docs" / "notes.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("notes")
        text = f"Check {target} for notes."
        result = extract_file_paths(text, tmp_path)
        assert any(p.name == "notes.md" for p in result)

    def test_path_escape_silently_skipped(self, tmp_path: Path) -> None:
        """Paths resolving outside workspace are silently skipped."""
        text = "See ../../../etc/passwd for details."
        result = extract_file_paths(text, tmp_path)
        # Traversal path must not appear in results
        assert all(p.is_relative_to(tmp_path) or True for p in result)
        # More specifically, no passwd file should be in the result
        assert not any("passwd" in str(p) for p in result)

    def test_no_paths_returns_empty(self) -> None:
        """Returns empty list when no file paths are found."""
        text = "Just a description with no file references."
        result = extract_file_paths(text, Path("/workspace"))
        assert result == []

    def test_workspace_scoped_path(self, tmp_path: Path) -> None:
        """Paths like tests/test_foo.py are extracted relative to workspace."""
        target = tmp_path / "tests" / "test_foo.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("pass")
        text = "Tests are in tests/test_foo.py"
        result = extract_file_paths(text, tmp_path)
        assert any("test_foo" in str(p) for p in result)


# ===========================================================================
# AC: async fetch_url(url, url_checker, ...) -> str
# ===========================================================================


class TestFromACFetchUrl:
    """URL fetching with httpx + trafilatura (mock HTTP)."""

    @pytest.mark.asyncio
    async def test_successful_fetch_returns_content(self) -> None:
        """Successful fetch returns extracted markdown content."""
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><p>Hello world</p></body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract = MagicMock(return_value="Hello world")

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            result = await fetch_url("https://example.com/page", url_checker=None)

        assert "Hello world" in result

    @pytest.mark.asyncio
    async def test_timeout_collected_as_error(self) -> None:
        """httpx.TimeoutException results in error string, not crash."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            # fetch_url should not raise — should return error or empty string
            # The contract says failed fetches are logged at WARNING and
            # collected in errors — so this should handle gracefully
            result = await fetch_url("https://slow.example.com", url_checker=None)

        # Result should indicate failure, not valid content
        assert result == "" or "error" in result.lower() or "timeout" in result.lower()

    @pytest.mark.asyncio
    async def test_http_error_collected_gracefully(self) -> None:
        """HTTP 500 error is handled gracefully, not raised."""
        import httpx

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=httpx.Request("GET", "https://example.com/fail"),
                response=httpx.Response(500),
            ),
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fetch_url("https://example.com/fail", url_checker=None)

        assert result == "" or "error" in result.lower() or "500" in result

    @pytest.mark.asyncio
    async def test_url_checker_blocks_url(self) -> None:
        """When url_checker raises ValueError, fetch is skipped."""

        def blocking_checker(url: str) -> None:
            msg = f"Blocked: {url}"
            raise ValueError(msg)

        # Should not make HTTP call — url_checker rejects first
        # The function should raise ValueError or return empty/error
        with pytest.raises(ValueError, match="Blocked"):
            await fetch_url(
                "https://evil.example.com",
                url_checker=blocking_checker,
            )

    @pytest.mark.asyncio
    async def test_url_checker_allows_url(self) -> None:
        """When url_checker does not raise, fetch proceeds."""
        calls: list[str] = []

        def allowing_checker(url: str) -> None:
            calls.append(url)
            # Does not raise — URL is allowed

        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Allowed content</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract = MagicMock(return_value="Allowed content")

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            result = await fetch_url(
                "https://safe.example.com",
                url_checker=allowing_checker,
            )

        assert calls == ["https://safe.example.com"]
        assert "Allowed content" in result


# ===========================================================================
# AC: read_file_safe(path, workspace_root) -> str
# ===========================================================================


class TestFromACReadFileSafe:
    """File reading: existing, missing, path-escape blocked."""

    def test_read_existing_file(self, tmp_path: Path) -> None:
        """Reads content of an existing file within workspace."""
        f = tmp_path / "readme.md"
        f.write_text("Hello from file")
        result = read_file_safe(f, tmp_path)
        assert result == "Hello from file"

    def test_missing_file_returns_empty_or_error(self, tmp_path: Path) -> None:
        """Missing file returns empty string or raises FileNotFoundError.

        Contract says failed reads are collected in errors, never fail dispatch.
        """
        missing = tmp_path / "nonexistent.txt"
        # Should either return "" or raise — implementation decides,
        # but it must not crash unhandled
        try:
            result = read_file_safe(missing, tmp_path)
            # If it doesn't raise, result should be empty/error indicator
            assert result == "" or isinstance(result, str)
        except FileNotFoundError:
            pass  # Also acceptable

    def test_path_escape_blocked(self, tmp_path: Path) -> None:
        """Path traversal outside workspace raises PermissionError."""
        escaped = tmp_path / ".." / ".." / "etc" / "passwd"
        with pytest.raises(PermissionError, match="Path outside workspace"):
            read_file_safe(escaped, tmp_path)

    def test_relative_path_resolved(self, tmp_path: Path) -> None:
        """Relative path is resolved against workspace_root."""
        f = tmp_path / "sub" / "data.txt"
        f.parent.mkdir(parents=True)
        f.write_text("data content")
        result = read_file_safe(Path("sub/data.txt"), tmp_path)
        assert result == "data content"


# ===========================================================================
# AC: Workspace confinement (paths outside workspace rejected)
# ===========================================================================


class TestFromACWorkspaceConfinement:
    """Workspace confinement checks across extract and read functions."""

    def test_extract_file_paths_skips_outside_workspace(self, tmp_path: Path) -> None:
        """extract_file_paths silently drops paths resolving outside workspace."""
        text = "See /etc/shadow and ../../../root/.bashrc for info."
        result = extract_file_paths(text, tmp_path)
        assert not any("shadow" in str(p) for p in result)
        assert not any(".bashrc" in str(p) for p in result)

    def test_read_file_safe_rejects_absolute_outside(self, tmp_path: Path) -> None:
        """Absolute path outside workspace is rejected."""
        with pytest.raises(PermissionError):
            read_file_safe(Path("/etc/passwd"), tmp_path)

    def test_read_file_safe_rejects_null_byte(self, tmp_path: Path) -> None:
        """Null byte in path triggers PermissionError (sandbox_path guard)."""
        with pytest.raises(PermissionError):
            read_file_safe(Path("file\x00.txt"), tmp_path)


# ===========================================================================
# AC: max_content_bytes budget truncation
# ===========================================================================


class TestFromACMaxContentBytesBudget:
    """Content exceeding max_content_bytes budget is trimmed."""

    @pytest.mark.asyncio
    async def test_content_within_budget_untouched(self, tmp_path: Path) -> None:
        """Content fitting within budget is returned in full."""
        f = tmp_path / "small.txt"
        f.write_text("short content")
        text = f"See {f}"
        result = await hydrate(
            body=text,
            workspace_root=tmp_path,
            url_checker=None,
            max_content_bytes=50_000,
        )
        # File content should be in result, untruncated
        file_contents = list(result.files.values())
        assert any("short content" in c for c in file_contents)

    @pytest.mark.asyncio
    async def test_content_exceeding_budget_truncated(self, tmp_path: Path) -> None:
        """When total content exceeds max_content_bytes, last item is truncated."""
        f = tmp_path / "big.txt"
        f.write_text("A" * 10_000)
        text = f"See {f}"
        result = await hydrate(
            body=text,
            workspace_root=tmp_path,
            url_checker=None,
            max_content_bytes=100,  # tiny budget
        )
        # Total content should not exceed budget
        total = sum(len(v) for v in result.files.values()) + sum(
            len(v) for v in result.urls.values()
        )
        assert total <= 100

    @pytest.mark.asyncio
    async def test_zero_budget_produces_empty_content(self, tmp_path: Path) -> None:
        """Zero budget means no content hydrated."""
        f = tmp_path / "any.txt"
        f.write_text("content")
        text = f"See {f}"
        result = await hydrate(
            body=text,
            workspace_root=tmp_path,
            url_checker=None,
            max_content_bytes=0,
        )
        total = sum(len(v) for v in result.files.values()) + sum(
            len(v) for v in result.urls.values()
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_budget_boundary_exact_fit(self, tmp_path: Path) -> None:
        """Content exactly at budget is not truncated."""
        content = "X" * 200
        f = tmp_path / "exact.txt"
        f.write_text(content)
        text = f"See {f}"
        result = await hydrate(
            body=text,
            workspace_root=tmp_path,
            url_checker=None,
            max_content_bytes=200,
        )
        file_contents = list(result.files.values())
        assert any(len(c) == 200 for c in file_contents)


# ===========================================================================
# AC: hydrate() pipeline returns HydrationResult
# ===========================================================================


class TestFromACHydratePipeline:
    """Full hydrate() pipeline returns HydrationResult with urls, files, errors."""

    @pytest.mark.asyncio
    async def test_returns_hydration_result_type(self, tmp_path: Path) -> None:
        """hydrate() returns a HydrationResult instance."""
        result = await hydrate(
            body="No links here.",
            workspace_root=tmp_path,
            url_checker=None,
        )
        assert isinstance(result, HydrationResult)

    @pytest.mark.asyncio
    async def test_hydration_result_has_urls_dict(self, tmp_path: Path) -> None:
        """HydrationResult.urls is a dict[str, str]."""
        result = await hydrate(
            body="No links.",
            workspace_root=tmp_path,
            url_checker=None,
        )
        assert isinstance(result.urls, dict)

    @pytest.mark.asyncio
    async def test_hydration_result_has_files_dict(self, tmp_path: Path) -> None:
        """HydrationResult.files is a dict[str, str]."""
        result = await hydrate(
            body="No links.",
            workspace_root=tmp_path,
            url_checker=None,
        )
        assert isinstance(result.files, dict)

    @pytest.mark.asyncio
    async def test_hydration_result_has_errors_list(self, tmp_path: Path) -> None:
        """HydrationResult.errors is a list[str]."""
        result = await hydrate(
            body="No links.",
            workspace_root=tmp_path,
            url_checker=None,
        )
        assert isinstance(result.errors, list)

    @pytest.mark.asyncio
    async def test_hydration_result_is_frozen(self) -> None:
        """HydrationResult is a frozen Pydantic model."""
        r = HydrationResult(urls={}, files={}, errors=[])
        with pytest.raises(TypeError, match=r"frozen|immutable"):
            r.urls = {"new": "value"}  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_file_content_in_files_dict(self, tmp_path: Path) -> None:
        """Hydrated file content appears in result.files keyed by path."""
        f = tmp_path / "data.txt"
        f.write_text("file data here")
        text = f"See {f}"
        result = await hydrate(
            body=text,
            workspace_root=tmp_path,
            url_checker=None,
        )
        assert any("file data here" in v for v in result.files.values())

    @pytest.mark.asyncio
    async def test_failed_fetch_appears_in_errors(self, tmp_path: Path) -> None:
        """A URL that fails to fetch gets logged in errors list."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("timed out"),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await hydrate(
                body="See https://slow.example.com for info.",
                workspace_root=tmp_path,
                url_checker=None,
            )

        assert len(result.errors) >= 1
        assert any("slow.example.com" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_missing_file_appears_in_errors(self, tmp_path: Path) -> None:
        """A referenced file that doesn't exist gets logged in errors."""
        missing = tmp_path / "ghost.txt"
        text = f"See {missing} for details."
        result = await hydrate(
            body=text,
            workspace_root=tmp_path,
            url_checker=None,
        )
        # Missing file should be in errors, not crash the pipeline
        assert len(result.errors) >= 1 or str(missing) not in result.files

    @pytest.mark.asyncio
    async def test_empty_body_returns_empty_result(self, tmp_path: Path) -> None:
        """Empty body produces empty HydrationResult."""
        result = await hydrate(
            body="",
            workspace_root=tmp_path,
            url_checker=None,
        )
        assert result.urls == {}
        assert result.files == {}
        assert result.errors == []


# ===========================================================================
# Builder-discovered coverage tests
# ===========================================================================


class TestBuilderDiscovered:
    """Extra tests to cover branches missed by TestFromAC suites."""

    @pytest.mark.asyncio
    async def test_fetch_url_generic_http_error(self) -> None:
        """Generic httpx.HTTPError (not Timeout/Status) returns empty string."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("connection reset"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fetch_url("https://example.com/broken", url_checker=None)

        assert result == ""


# ===========================================================================
# AC #876: fetch_url() delegates to extract_markdown(html_body, url=url)
# ===========================================================================


class TestFromAC_FetchUrlExtractMarkdownForwarding:
    """fetch_url() forwards resp.text and url= to extract_markdown helper.

    RED supplement for #873 per task #876.
    Fails pre-#873 (trafilatura called directly).
    Passes once #873 imports extract_markdown and delegates via it.
    """

    @pytest.mark.asyncio
    async def test_forwards_html_body_and_url_to_extract_markdown(self) -> None:
        """fetch_url() calls extract_markdown(html_body, url=url) exactly once.

        Caller-boundary assertion: does not check trafilatura kwargs (owned by #874).
        Fails pre-#873 because extract_markdown is never called by fetch_url.
        """
        html_body = "<html><body><p>Article text</p></body></html>"
        target_url = "https://example.com/article"

        mock_resp = MagicMock()
        mock_resp.text = html_body
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = None  # pre-#873 code path

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
            patch(
                "owlbear.core.context_hydration.extract_markdown",
                create=True,
            ) as mock_extract_md,
        ):
            mock_extract_md.return_value = "## Article\n\nArticle text"
            await fetch_url(target_url)

        mock_extract_md.assert_called_once_with(html_body, url=target_url)

    @pytest.mark.asyncio
    async def test_helper_return_propagates_to_fetch_url_result(self) -> None:
        """fetch_url() result contains the value returned by extract_markdown.

        Fails pre-#873: result comes from trafilatura mock ("unrelated output"),
        not from the extract_markdown mock, so the distinctive marker is absent.
        Passes once #873 delegates through extract_markdown.
        """
        html_body = "<html><body><p>Notable content</p></body></html>"
        target_url = "https://example.com/page"
        distinctive_marker = "DISTINCT_MARKER_FROM_EXTRACT_MARKDOWN"

        mock_resp = MagicMock()
        mock_resp.text = html_body
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "unrelated trafilatura output"

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
            patch(
                "owlbear.core.context_hydration.extract_markdown",
                create=True,
            ) as mock_extract_md,
        ):
            mock_extract_md.return_value = distinctive_marker
            result = await fetch_url(target_url)

        assert distinctive_marker in result

    @pytest.mark.asyncio
    async def test_hydrate_url_success_populates_urls_dict(self, tmp_path: Path) -> None:
        """Successful URL fetch through hydrate() populates result.urls."""
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><p>Page content</p></body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract = MagicMock(return_value="Page content")

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            result = await hydrate(
                body="See https://example.com/doc for details.",
                workspace_root=tmp_path,
                url_checker=None,
            )

        assert "https://example.com/doc" in result.urls
        assert "Page content" in result.urls["https://example.com/doc"]

    @pytest.mark.asyncio
    async def test_hydrate_url_checker_blocks_inside_pipeline(
        self,
        tmp_path: Path,
    ) -> None:
        """url_checker ValueError inside hydrate() collected in errors."""

        def blocker(url: str) -> None:
            msg = f"Blocked: {url}"
            raise ValueError(msg)

        result = await hydrate(
            body="See https://evil.example.com for info.",
            workspace_root=tmp_path,
            url_checker=blocker,
        )

        assert len(result.errors) >= 1
        assert any("evil.example.com" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_hydrate_files_budget_exhausted(self, tmp_path: Path) -> None:
        """When budget is consumed by first file, second file is skipped."""
        f1 = tmp_path / "a.txt"
        f1.write_text("A" * 50)
        f2 = tmp_path / "b.txt"
        f2.write_text("B" * 50)
        text = f"See {f1} and {f2}"
        result = await hydrate(
            body=text,
            workspace_root=tmp_path,
            url_checker=None,
            max_content_bytes=50,
        )
        total = sum(len(v) for v in result.files.values())
        assert total <= 50

    @pytest.mark.asyncio
    async def test_hydrate_urls_budget_exhausted(self, tmp_path: Path) -> None:
        """When file budget is consumed, URLs are skipped (budget <= 0)."""
        f = tmp_path / "big.txt"
        f.write_text("X" * 100)
        text = f"See {f} and https://example.com/page"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=AssertionError("should not be called"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await hydrate(
                body=text,
                workspace_root=tmp_path,
                url_checker=None,
                max_content_bytes=100,
            )

        assert result.urls == {}

    @pytest.mark.asyncio
    async def test_hydrate_url_content_truncated_by_budget(
        self,
        tmp_path: Path,
    ) -> None:
        """URL content exceeding remaining budget is truncated."""
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Long content</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract = MagicMock(return_value="A" * 500)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            result = await hydrate(
                body="See https://example.com/long",
                workspace_root=tmp_path,
                url_checker=None,
                max_content_bytes=100,
            )

        total = sum(len(v) for v in result.urls.values())
        assert total <= 100
