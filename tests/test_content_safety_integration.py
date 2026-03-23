"""Integration tests for untrusted content wrapping at web-extraction points.

RED-phase tests for task #725. Verifies that each direct-to-LLM web-extraction
output path applies ``wrap_untrusted_content()`` wrapping, gated by the
``OwlBearSettings.wrap_web_content`` config flag.

Also verifies that ``bookmark_pipeline._default_web_read()`` is *excluded*
from wrapping (stores to knowledge graph, not direct LLM context).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Pre-load modules that tests import inside ``patch.dict("sys.modules", ...)``.
# Python 3.12+ ``patch.dict`` snapshots the full dict on entry and restores it
# on exit, removing any modules added during the context.  Pre-importing here
# ensures they survive across consecutive ``patch.dict`` blocks in the same test.
import owlbear.tools.browser.content_extractor  # noqa: F401

# ---------------------------------------------------------------------------
# Sentinel strings used to assert wrapping presence / absence.
# ---------------------------------------------------------------------------

_OPEN_TAG = "<untrusted_web_content"
_CLOSE_TAG = "</untrusted_web_content>"


# ===========================================================================
# AC: browser_read_text() wraps return value
# ===========================================================================


class TestFromACBrowserReadTextWrapping:
    """browser_read_text() return value is wrapped with untrusted-content tags."""

    @pytest.mark.asyncio
    async def test_wraps_return_value(self) -> None:
        """browser_read_text() output contains untrusted-content tags."""
        from owlbear.tools.browser.actions import browser_read_text

        page = AsyncMock()
        page.inner_text = AsyncMock(return_value="Page body text from the web")

        result = await browser_read_text(page=page)

        assert _OPEN_TAG in result, "browser_read_text must wrap output"
        assert _CLOSE_TAG in result
        assert "Page body text from the web" in result

    @pytest.mark.asyncio
    async def test_wraps_with_no_selector(self) -> None:
        """Full-page read (selector=None) also wraps its result."""
        from owlbear.tools.browser.actions import browser_read_text

        page = AsyncMock()
        page.inner_text = AsyncMock(return_value="Full page content")

        result = await browser_read_text(page=page, selector=None)

        assert _OPEN_TAG in result

    @pytest.mark.asyncio
    async def test_skips_wrapping_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When wrap_web_content=False, browser_read_text() returns raw text.

        Verifies BOTH states: wrapping works by default, then is skipped when
        disabled. This prevents the test from passing trivially when wrapping
        is not yet implemented.
        """
        from owlbear.tools.browser.actions import browser_read_text

        # Step 1: verify wrapping IS applied by default (will fail in RED)
        page_default = AsyncMock()
        page_default.inner_text = AsyncMock(return_value="Default text")
        result_default = await browser_read_text(page=page_default)
        assert _OPEN_TAG in result_default, "wrapping must work by default first"

        # Step 2: verify wrapping is NOT applied when disabled
        monkeypatch.setenv("OWLBEAR_WRAP_WEB_CONTENT", "false")
        page_disabled = AsyncMock()
        page_disabled.inner_text = AsyncMock(return_value="Unwrapped text")
        result_disabled = await browser_read_text(page=page_disabled)
        assert _OPEN_TAG not in result_disabled, "wrapping must be skipped when disabled"
        assert "Unwrapped text" in result_disabled


# ===========================================================================
# AC: extract_content() .text field wraps
# ===========================================================================


class TestFromACExtractContentWrapping:
    """extract_content() .text field is wrapped with untrusted-content tags."""

    def test_wraps_text_field(self) -> None:
        """extract_content().text contains untrusted-content tags."""
        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Extracted article text"
        mock_meta = MagicMock()
        mock_meta.title = "Title"
        mock_meta.author = None
        mock_meta.date = None
        mock_trafilatura.extract_metadata.return_value = mock_meta

        with patch.dict("sys.modules", {"trafilatura": mock_trafilatura}):
            from importlib import reload

            import owlbear.tools.browser.content_extractor as mod

            reload(mod)
            result = mod.extract_content(
                "<html><body>hello</body></html>",
                url="https://example.com",
            )

        assert _OPEN_TAG in result.text, "extract_content .text must be wrapped"
        assert _CLOSE_TAG in result.text
        assert "Extracted article text" in result.text

    def test_wraps_text_field_with_source_url(self) -> None:
        """Wrapped text includes the source URL in the open tag attribute."""
        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Article body"
        mock_trafilatura.extract_metadata.return_value = None

        with patch.dict("sys.modules", {"trafilatura": mock_trafilatura}):
            from importlib import reload

            import owlbear.tools.browser.content_extractor as mod

            reload(mod)
            result = mod.extract_content(
                "<html><body>test</body></html>",
                url="https://news.example.com/article",
            )

        assert 'url="https://news.example.com/article"' in result.text

    def test_skips_wrapping_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When wrap_web_content=False, extract_content().text is raw.

        Verifies BOTH states: wrapping by default, then skip when disabled.
        """
        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Article text"
        mock_trafilatura.extract_metadata.return_value = None

        # Step 1: verify wrapping IS applied by default (fails in RED)
        with patch.dict("sys.modules", {"trafilatura": mock_trafilatura}):
            from importlib import reload

            import owlbear.tools.browser.content_extractor as mod

            reload(mod)
            result_default = mod.extract_content("<html><body>x</body></html>")
        assert _OPEN_TAG in result_default.text, "wrapping must work by default first"

        # Step 2: verify wrapping NOT applied when disabled
        monkeypatch.setenv("OWLBEAR_WRAP_WEB_CONTENT", "false")
        with patch.dict("sys.modules", {"trafilatura": mock_trafilatura}):
            reload(mod)
            result_disabled = mod.extract_content("<html><body>x</body></html>")
        assert _OPEN_TAG not in result_disabled.text, "wrapping must be skipped when disabled"


# ===========================================================================
# AC: WebSearchToolset._web_read() wraps return value
# ===========================================================================


class TestFromACWebReadWrapping:
    """WebSearchToolset._web_read() wraps its return value."""

    @pytest.fixture
    def _mock_httpx(self) -> AsyncMock:
        """Mock httpx.AsyncClient for web_read tests."""
        response = MagicMock()
        response.status_code = 200
        response.text = "<html><body><p>Web page</p></body></html>"
        response.raise_for_status = MagicMock()

        client = AsyncMock()
        client.get.return_value = response

        cm = AsyncMock()
        cm.__aenter__.return_value = client
        cm.__aexit__.return_value = False

        return cm

    @pytest.mark.asyncio
    async def test_wraps_return_value(self, _mock_httpx: AsyncMock) -> None:
        """_web_read() output contains untrusted-content tags."""
        from owlbear.tools.web_search import WebSearchToolset

        with (
            patch("owlbear.tools.web_search.httpx.AsyncClient", return_value=_mock_httpx),
            patch("owlbear.tools.web_search.trafilatura") as mock_traf,
        ):
            mock_traf.extract.return_value = "Extracted web content"
            ts = WebSearchToolset()
            result = await ts._web_read("https://example.com")

        assert _OPEN_TAG in result, "_web_read must wrap output"
        assert _CLOSE_TAG in result
        assert "Extracted web content" in result

    @pytest.mark.asyncio
    async def test_skips_wrapping_when_disabled(
        self, _mock_httpx: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When wrap_web_content=False, _web_read() returns raw text.

        Verifies BOTH states: wrapping by default, then skip when disabled.
        """
        from owlbear.tools.web_search import WebSearchToolset

        # Step 1: verify wrapping IS applied by default (fails in RED)
        with (
            patch("owlbear.tools.web_search.httpx.AsyncClient", return_value=_mock_httpx),
            patch("owlbear.tools.web_search.trafilatura") as mock_traf,
        ):
            mock_traf.extract.return_value = "Web content"
            ts = WebSearchToolset()
            result_default = await ts._web_read("https://example.com")
        assert _OPEN_TAG in result_default, "wrapping must work by default first"

        # Step 2: verify wrapping NOT applied when disabled
        monkeypatch.setenv("OWLBEAR_WRAP_WEB_CONTENT", "false")
        with (
            patch("owlbear.tools.web_search.httpx.AsyncClient", return_value=_mock_httpx),
            patch("owlbear.tools.web_search.trafilatura") as mock_traf,
        ):
            mock_traf.extract.return_value = "Raw web content"
            ts2 = WebSearchToolset()
            result_disabled = await ts2._web_read("https://example.com")
        assert _OPEN_TAG not in result_disabled, "wrapping must be skipped when disabled"


# ===========================================================================
# AC: fetch_url() wraps return value
# ===========================================================================


class TestFromACFetchUrlWrapping:
    """core/context_hydration.fetch_url() wraps its return value."""

    @pytest.mark.asyncio
    async def test_wraps_return_value(self) -> None:
        """fetch_url() output contains untrusted-content tags."""
        from owlbear.core.context_hydration import fetch_url

        mock_resp = MagicMock()
        mock_resp.text = "<html><body>article</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Fetched article content"

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            result = await fetch_url("https://example.com/article")

        assert _OPEN_TAG in result, "fetch_url must wrap output"
        assert _CLOSE_TAG in result
        assert "Fetched article content" in result

    @pytest.mark.asyncio
    async def test_wraps_with_source_url_attribute(self) -> None:
        """fetch_url() wrapping includes source URL in open tag."""
        from owlbear.core.context_hydration import fetch_url

        mock_resp = MagicMock()
        mock_resp.text = "<html>page</html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Some content"

        url = "https://example.com/doc"
        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            result = await fetch_url(url)

        assert f'url="{url}"' in result, "fetch_url wrapping should include source URL"

    @pytest.mark.asyncio
    async def test_skips_wrapping_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When wrap_web_content=False, fetch_url() returns raw text.

        Verifies BOTH states: wrapping by default, then skip when disabled.
        """
        from owlbear.core.context_hydration import fetch_url

        mock_resp = MagicMock()
        mock_resp.text = "<html>page</html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Hydrated content"

        # Step 1: verify wrapping IS applied by default (fails in RED)
        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            result_default = await fetch_url("https://example.com/page")
        assert _OPEN_TAG in result_default, "wrapping must work by default first"

        # Step 2: verify wrapping NOT applied when disabled
        monkeypatch.setenv("OWLBEAR_WRAP_WEB_CONTENT", "false")
        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            result_disabled = await fetch_url("https://example.com/page")
        assert _OPEN_TAG not in result_disabled, "wrapping must be skipped when disabled"


# ===========================================================================
# AC: bookmark_pipeline._default_web_read() EXCLUDED from wrapping
# ===========================================================================


class TestFromACBookmarkPipelineExcluded:
    """bookmark_pipeline._default_web_read() must NOT wrap content.

    Contrasts against fetch_url() which DOES wrap: verifies the exclusion
    is intentional, not just "wrapping isn't implemented anywhere yet".
    """

    @pytest.mark.asyncio
    async def test_default_web_read_does_not_wrap_while_fetch_url_does(self) -> None:
        """_default_web_read() returns raw text while fetch_url() wraps.

        This contrast test ensures the bookmark exclusion is deliberate.
        If neither path wraps, the test fails (RED) because fetch_url
        should wrap but doesn't yet.
        """
        from owlbear.core.context_hydration import fetch_url

        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Content</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Article text"

        # fetch_url MUST wrap (contrast baseline — fails in RED)
        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            fetch_result = await fetch_url("https://example.com/article")
        assert _OPEN_TAG in fetch_result, (
            "fetch_url must wrap — contrast baseline for bookmark exclusion"
        )

        # _default_web_read must NOT wrap
        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            from owlbear.memory.knowledge.bookmark_pipeline import _default_web_read

            bookmark_result = await _default_web_read("https://example.com/bookmark")

        assert bookmark_result is not None
        assert _OPEN_TAG not in bookmark_result, (
            "bookmark_pipeline._default_web_read must NOT wrap — "
            "content goes to knowledge graph, not LLM context"
        )
        assert bookmark_result == "Article text"


# ===========================================================================
# AC #876: fetch_url() caller-seam — delegates to module-local extract_markdown
# ===========================================================================


class TestFromAC_FetchUrlExtractMarkdownSeam:
    """fetch_url() caller-seam: delegates to module-local extract_markdown.

    Caller-boundary assertions per task #876.  Does not test helper-internal
    trafilatura kwargs (owned by #874 / tests/test_web_extract.py).
    Fails pre-#873: extract_markdown is never called by fetch_url.
    Passes once #873 imports extract_markdown and calls it with resp.text + url.
    """

    @pytest.mark.asyncio
    async def test_fetch_url_forwards_to_helper_and_wraps_output(self) -> None:
        """fetch_url() calls extract_markdown(html_body, url=url) once and wraps result.

        Two invariants:
        1. Caller-seam: extract_markdown called exactly once with the fetched HTML
           body as first positional arg and url= as keyword arg.
        2. Wrapping contract: the raw helper return value is wrapped by
           wrap_untrusted_content, so the final result contains _OPEN_TAG.

        Both invariants fail pre-#873 (assert_called_once_with raises because
        the mock is never invoked; result is empty so _OPEN_TAG is absent).
        """
        from owlbear.core.context_hydration import fetch_url

        html_body = "<html><body><p>Web article</p></body></html>"
        target_url = "https://example.com/news/story"

        mock_resp = MagicMock()
        mock_resp.text = html_body
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = None  # pre-#873 fallback

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
            patch(
                "owlbear.core.context_hydration.extract_markdown",
                create=True,
            ) as mock_extract_md,
        ):
            mock_extract_md.return_value = "extracted news article"
            result = await fetch_url(target_url)

        # Seam assertion: helper forwarded html body and url= (fails pre-#873)
        mock_extract_md.assert_called_once_with(html_body, url=target_url)
        # Wrapping assertion: raw helper output still passes through wrap_untrusted_content
        assert _OPEN_TAG in result, "wrapping must be applied to extract_markdown return value"


# ===========================================================================
# AC #867: bookmark_pipeline contrast — extract_markdown seam (RED for #825)
# ===========================================================================


class TestFromAC_BookmarkExtractMarkdownContrast:
    """Bookmark side patches owlbear.memory.knowledge.bookmark_pipeline.extract_markdown.

    After #825, _default_web_read() imports and calls extract_markdown rather than
    importing trafilatura directly.  These tests use the new module-local seam for
    the bookmark side while fetch_url() continues to use sys.modules[trafilatura],
    proving the mixed-seam architecture is correct and the bookmark path stays raw.

    Tests FAIL against current HEAD because bookmark_pipeline.py does not yet
    import extract_markdown (AttributeError at patch teardown — intended seam
    mismatch, not a syntax error).
    """

    @pytest.mark.asyncio
    async def test_bookmark_side_uses_extract_markdown_seam_and_returns_raw(
        self,
    ) -> None:
        """bookmark side patches extract_markdown; result is raw (no wrap tag).

        Contrast invariant: fetch_url() wraps output while _default_web_read()
        returns raw Markdown.  The bookmark mock returns Markdown with link
        syntax so the raw-vs-wrapped contrast is unambiguous.
        """
        from owlbear.core.context_hydration import fetch_url
        from owlbear.memory.knowledge.bookmark_pipeline import _default_web_read

        # --- fetch_url side: still uses sys.modules[trafilatura] seam ----------
        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Article text"

        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Content</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            fetch_result = await fetch_url("https://example.com/article")

        assert _OPEN_TAG in fetch_result, (
            "fetch_url must wrap — contrast baseline for bookmark exclusion"
        )

        # --- bookmark side: patches module-local extract_markdown (after #825) --
        # NOTE: patch() raises AttributeError on current HEAD because
        # bookmark_pipeline.py does not yet import extract_markdown.
        # This is the intended seam-mismatch failure for the RED phase.
        raw_markdown = "[Python docs](https://docs.python.org)"

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch(
                "owlbear.memory.knowledge.bookmark_pipeline.extract_markdown",
                return_value=raw_markdown,
            ),
            patch("owlbear.core.retry.TRANSIENT_RETRY", lambda fn: fn),
        ):
            bookmark_result = await _default_web_read("https://example.com/bookmark")

        assert bookmark_result is not None
        assert _OPEN_TAG not in bookmark_result, (
            "bookmark_pipeline._default_web_read must NOT wrap — "
            "content goes to knowledge graph, not LLM context"
        )
        assert bookmark_result == raw_markdown


# ===========================================================================
# AC #869: fetch_url() wrap-seam — module-local extract_markdown (replaces sys.modules)
# ===========================================================================


class TestFromAC_FetchUrlWrapsByExtractMarkdown:
    """fetch_url() wrapping tests using module-local extract_markdown seam.

    Replaces the 5 fetch_url-related sys.modules["trafilatura"] patches in:
    - TestFromACFetchUrlWrapping::test_wraps_return_value
    - TestFromACFetchUrlWrapping::test_wraps_with_source_url_attribute
    - TestFromACFetchUrlWrapping::test_skips_wrapping_when_disabled
    - TestFromACBookmarkPipelineExcluded::test_default_web_read_does_not_wrap_while_fetch_url_does
    - TestFromAC_FetchUrlExtractMarkdownSeam::test_fetch_url_forwards_to_helper_and_wraps_output

    Patches owlbear.core.context_hydration.extract_markdown directly (no sys.modules).
    Raw markdown from the helper mock passes through fetch_url's wrap_untrusted_content.
    No create=True: fails with AttributeError against pre-#873 code where the import
    does not exist in context_hydration.py — that AttributeError is the intended RED failure.
    """

    @pytest.fixture
    def _mock_http(self) -> AsyncMock:
        """Minimal httpx mock returning simple HTML."""
        response = MagicMock()
        response.text = "<html><body>content</body></html>"
        response.raise_for_status = MagicMock()
        client = AsyncMock()
        client.get = AsyncMock(return_value=response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        return client

    @pytest.mark.asyncio
    async def test_wraps_raw_extract_markdown_output(self, _mock_http: AsyncMock) -> None:
        """fetch_url() wraps the raw string returned by extract_markdown.

        Replaces TestFromACFetchUrlWrapping::test_wraps_return_value.
        No sys.modules: mock is the module-local seam the caller uses.
        Raw helper return → wrap_untrusted_content applied → _OPEN_TAG in result.
        """
        from owlbear.core.context_hydration import fetch_url

        with (
            patch("httpx.AsyncClient", return_value=_mock_http),
            patch("owlbear.core.context_hydration.extract_markdown") as mock_extract_md,
        ):
            mock_extract_md.return_value = "Fetched article content"
            result = await fetch_url("https://example.com/article")

        assert _OPEN_TAG in result, "fetch_url must wrap extract_markdown output"
        assert _CLOSE_TAG in result
        assert "Fetched article content" in result

    @pytest.mark.asyncio
    async def test_wrap_tag_includes_source_url_attribute(self, _mock_http: AsyncMock) -> None:
        """fetch_url() open wrap tag includes url= attribute with the fetched URL.

        Replaces TestFromACFetchUrlWrapping::test_wraps_with_source_url_attribute.
        """
        from owlbear.core.context_hydration import fetch_url

        url = "https://example.com/doc"
        with (
            patch("httpx.AsyncClient", return_value=_mock_http),
            patch("owlbear.core.context_hydration.extract_markdown") as mock_extract_md,
        ):
            mock_extract_md.return_value = "Some content"
            result = await fetch_url(url)

        assert f'url="{url}"' in result

    @pytest.mark.asyncio
    async def test_wrapping_disabled_returns_raw_extract_markdown(
        self, _mock_http: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When wrap_web_content=False, fetch_url() returns raw helper output.

        Replaces TestFromACFetchUrlWrapping::test_skips_wrapping_when_disabled.
        Verifies BOTH states using module-local seam: wrapped by default, raw when disabled.
        """
        from owlbear.core.context_hydration import fetch_url

        # Step 1: verify wrapping IS applied with module-local seam
        with (
            patch("httpx.AsyncClient", return_value=_mock_http),
            patch("owlbear.core.context_hydration.extract_markdown") as mock_extract_md,
        ):
            mock_extract_md.return_value = "Raw content"
            result_default = await fetch_url("https://example.com/page")

        assert _OPEN_TAG in result_default, "wrapping must be applied by default"

        # Step 2: wrapping skipped when disabled
        monkeypatch.setenv("OWLBEAR_WRAP_WEB_CONTENT", "false")
        with (
            patch("httpx.AsyncClient", return_value=_mock_http),
            patch("owlbear.core.context_hydration.extract_markdown") as mock_extract_md,
        ):
            mock_extract_md.return_value = "Raw content"
            result_disabled = await fetch_url("https://example.com/page")

        assert _OPEN_TAG not in result_disabled, "wrapping must be skipped when disabled"

    @pytest.mark.asyncio
    async def test_fetch_url_wraps_while_bookmark_does_not_contrast(
        self, _mock_http: AsyncMock
    ) -> None:
        """fetch_url() wraps; bookmark_pipeline._default_web_read() stays raw.

        Replaces TestFromACBookmarkPipelineExcluded contrast test.
        The fetch_url side uses module-local extract_markdown mock (no sys.modules).
        The bookmark side uses sys.modules trafilatura (bookmark_pipeline still uses
        trafilatura directly until #825 is implemented).
        """
        from owlbear.core.context_hydration import fetch_url

        # fetch_url side: module-local extract_markdown mock
        with (
            patch("httpx.AsyncClient", return_value=_mock_http),
            patch("owlbear.core.context_hydration.extract_markdown") as mock_extract_md,
        ):
            mock_extract_md.return_value = "Article text"
            fetch_result = await fetch_url("https://example.com/article")

        assert _OPEN_TAG in fetch_result, "fetch_url must wrap — contrast baseline"
        assert "Article text" in fetch_result

        # bookmark side: _default_web_read must not wrap
        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Article text"

        with (
            patch("httpx.AsyncClient", return_value=_mock_http),
            patch.dict("sys.modules", {"trafilatura": mock_trafilatura}),
        ):
            from owlbear.memory.knowledge.bookmark_pipeline import _default_web_read

            bookmark_result = await _default_web_read("https://example.com/bookmark")

        assert bookmark_result is not None
        assert _OPEN_TAG not in bookmark_result, "bookmark path must not wrap"

    @pytest.mark.asyncio
    async def test_none_from_extract_markdown_not_wrapped(self, _mock_http: AsyncMock) -> None:
        """When extract_markdown returns None, fetch_url() returns empty string.

        Replaces the combined sys.modules + extract_markdown test in
        TestFromAC_FetchUrlExtractMarkdownSeam, but without the sys.modules layer.
        None from helper → or "" guard in fetch_url → result is empty, not wrapped.
        """
        from owlbear.core.context_hydration import fetch_url

        with (
            patch("httpx.AsyncClient", return_value=_mock_http),
            patch("owlbear.core.context_hydration.extract_markdown") as mock_extract_md,
        ):
            mock_extract_md.return_value = None
            result = await fetch_url("https://example.com/empty")

        assert result == ""
        assert _OPEN_TAG not in result
