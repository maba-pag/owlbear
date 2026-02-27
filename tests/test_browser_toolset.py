"""Tests for BrowserToolset — FunctionToolset wrapping all 6 browser actions.

Covers: tool registration (6 tools with correct names), delegation to action
functions with injected page/config, BrowserManager lifecycle (setup/teardown),
page property guard, default config fallback, composition with SkillRegistry,
and FunctionToolset inheritance.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from owlbear.tools.browser.config import BrowserConfig
from owlbear.tools.browser.toolset import BrowserToolset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_TOOL_NAMES = frozenset(
    {
        "browser_navigate",
        "browser_click",
        "browser_type",
        "browser_select",
        "browser_read_text",
        "browser_screenshot",
    }
)


def _make_mock_page() -> AsyncMock:
    """Build a mock Playwright Page."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value="Mock Title")
    type(page).url = PropertyMock(return_value="https://example.com")
    page.wait_for_selector = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.select_option = AsyncMock()
    page.inner_text = AsyncMock(return_value="page text")
    page.screenshot = AsyncMock(return_value=b"\x89PNG")
    return page


def _make_mock_manager(page: AsyncMock) -> MagicMock:
    """Build a mock BrowserManager that exposes the given page."""
    mgr = MagicMock()
    type(mgr).page = PropertyMock(return_value=page)
    mgr.__aenter__ = AsyncMock(return_value=mgr)
    mgr.__aexit__ = AsyncMock(return_value=None)
    return mgr


def _setup_toolset_with_mock_manager(page: AsyncMock) -> BrowserToolset:
    """Create a BrowserToolset with a mock manager injected (simulates setup)."""
    toolset = BrowserToolset()
    mgr = _make_mock_manager(page)
    toolset._manager = mgr  # noqa: SLF001
    return toolset


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestBrowserToolsetRegistration:
    """BrowserToolset registers all 6 browser tools on FunctionToolset."""

    def test_registers_six_tools(self) -> None:
        toolset = BrowserToolset()
        assert len(toolset.tools) == 6

    def test_tool_names_match(self) -> None:
        toolset = BrowserToolset()
        assert set(toolset.tools) == EXPECTED_TOOL_NAMES

    def test_inherits_from_function_toolset(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        toolset = BrowserToolset()
        assert isinstance(toolset, FunctionToolset)


# ---------------------------------------------------------------------------
# Tool delegation — each wrapper delegates to the correct action function
# ---------------------------------------------------------------------------


class TestBrowserToolsetDelegation:
    """Wrapper tools delegate to the underlying action functions."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_navigate", new_callable=AsyncMock)
    async def test_navigate_delegates(self, mock_nav: AsyncMock) -> None:
        mock_nav.return_value = "Navigated to Example (https://example.com)"
        page = _make_mock_page()
        toolset = _setup_toolset_with_mock_manager(page)

        result = await toolset._navigate("https://example.com")  # noqa: SLF001

        mock_nav.assert_awaited_once_with(
            "https://example.com",
            page=page,
            config=toolset.config,
        )
        assert "Navigated" in result

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_click", new_callable=AsyncMock)
    async def test_click_delegates(self, mock_click: AsyncMock) -> None:
        mock_click.return_value = "Clicked #btn"
        page = _make_mock_page()
        toolset = _setup_toolset_with_mock_manager(page)

        result = await toolset._click("#btn")  # noqa: SLF001

        mock_click.assert_awaited_once_with("#btn", page=page)
        assert result == "Clicked #btn"

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_type", new_callable=AsyncMock)
    async def test_type_delegates(self, mock_type: AsyncMock) -> None:
        mock_type.return_value = "Typed 'hello' into #input"
        page = _make_mock_page()
        toolset = _setup_toolset_with_mock_manager(page)

        result = await toolset._type("#input", "hello")  # noqa: SLF001

        mock_type.assert_awaited_once_with("#input", "hello", page=page)
        assert result == "Typed 'hello' into #input"

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_select", new_callable=AsyncMock)
    async def test_select_delegates(self, mock_select: AsyncMock) -> None:
        mock_select.return_value = "Selected 'opt1' in #dropdown"
        page = _make_mock_page()
        toolset = _setup_toolset_with_mock_manager(page)

        result = await toolset._select("#dropdown", "opt1")  # noqa: SLF001

        mock_select.assert_awaited_once_with("#dropdown", "opt1", page=page)
        assert result == "Selected 'opt1' in #dropdown"

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_read_text", new_callable=AsyncMock)
    async def test_read_text_delegates(self, mock_read: AsyncMock) -> None:
        mock_read.return_value = "page text"
        page = _make_mock_page()
        toolset = _setup_toolset_with_mock_manager(page)

        result = await toolset._read_text()  # noqa: SLF001

        mock_read.assert_awaited_once_with(page=page, selector=None, max_length=5000)
        assert result == "page text"

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_read_text", new_callable=AsyncMock)
    async def test_read_text_with_selector(self, mock_read: AsyncMock) -> None:
        mock_read.return_value = "element text"
        page = _make_mock_page()
        toolset = _setup_toolset_with_mock_manager(page)

        result = await toolset._read_text(selector="#content", max_length=100)  # noqa: SLF001

        mock_read.assert_awaited_once_with(page=page, selector="#content", max_length=100)
        assert result == "element text"

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_screenshot", new_callable=AsyncMock)
    async def test_screenshot_delegates(self, mock_ss: AsyncMock) -> None:
        mock_ss.return_value = "base64png"
        page = _make_mock_page()
        toolset = _setup_toolset_with_mock_manager(page)

        result = await toolset._screenshot()  # noqa: SLF001

        mock_ss.assert_awaited_once_with(page=page, selector=None, full_page=True)
        assert result == "base64png"

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_screenshot", new_callable=AsyncMock)
    async def test_screenshot_with_selector(self, mock_ss: AsyncMock) -> None:
        mock_ss.return_value = "element_png"
        page = _make_mock_page()
        toolset = _setup_toolset_with_mock_manager(page)

        result = await toolset._screenshot(selector="#hero", full_page=False)  # noqa: SLF001

        mock_ss.assert_awaited_once_with(page=page, selector="#hero", full_page=False)
        assert result == "element_png"


# ---------------------------------------------------------------------------
# BrowserManager lifecycle
# ---------------------------------------------------------------------------


class TestBrowserToolsetLifecycle:
    """Setup/teardown manage BrowserManager lifecycle."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_setup_creates_manager(self, mock_mgr_cls: MagicMock) -> None:
        page = _make_mock_page()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset()
        await toolset.setup()

        mock_mgr_cls.assert_called_once_with(toolset.config)
        mock_mgr.__aenter__.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_page_accessible_after_setup(self, mock_mgr_cls: MagicMock) -> None:
        page = _make_mock_page()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset()
        await toolset.setup()

        assert toolset.page is page

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_teardown_exits_manager(self, mock_mgr_cls: MagicMock) -> None:
        page = _make_mock_page()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset()
        await toolset.setup()
        await toolset.teardown()

        mock_mgr.__aexit__.assert_awaited_once_with(None, None, None)

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_teardown_clears_manager(self, mock_mgr_cls: MagicMock) -> None:
        page = _make_mock_page()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset()
        await toolset.setup()
        await toolset.teardown()

        with pytest.raises(RuntimeError, match="not set up"):
            _ = toolset.page

    @pytest.mark.asyncio(loop_scope="function")
    async def test_teardown_noop_when_not_setup(self) -> None:
        """Teardown on a fresh toolset does nothing (no error)."""
        toolset = BrowserToolset()
        await toolset.teardown()  # should not raise


# ---------------------------------------------------------------------------
# Page property guard
# ---------------------------------------------------------------------------


class TestBrowserToolsetPageProperty:
    """Page property raises RuntimeError when BrowserManager is not set up."""

    def test_page_raises_before_setup(self) -> None:
        toolset = BrowserToolset()
        with pytest.raises(RuntimeError, match="not set up"):
            _ = toolset.page


# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------


class TestBrowserToolsetDefaultConfig:
    """Default BrowserConfig used when None is passed."""

    def test_default_config_when_none(self) -> None:
        toolset = BrowserToolset(config=None)
        assert isinstance(toolset.config, BrowserConfig)
        assert toolset.config == BrowserConfig()

    def test_custom_config_preserved(self) -> None:
        cfg = BrowserConfig(headless=True, timeout_ms=5000)
        toolset = BrowserToolset(config=cfg)
        assert toolset.config is cfg


# ---------------------------------------------------------------------------
# Composition with SkillRegistry
# ---------------------------------------------------------------------------


class TestBrowserToolsetComposition:
    """BrowserToolset and SkillRegistry are independent FunctionToolset instances."""

    def test_both_are_independent_toolsets(self, tmp_path: object) -> None:
        from pathlib import Path

        from owlbear.skills.registry import SkillRegistry

        # Create a minimal skills directory
        skills_dir = Path(str(tmp_path)) / "skills"
        skills_dir.mkdir()
        skill = skills_dir / "test.md"
        skill.write_text(
            "---\nname: test_skill\ndescription: A test skill\n---\n# Test\n",
            encoding="utf-8",
        )

        browser_ts = BrowserToolset()
        skill_ts = SkillRegistry(skills_dir)

        # Both are FunctionToolset instances
        from pydantic_ai.toolsets import FunctionToolset

        assert isinstance(browser_ts, FunctionToolset)
        assert isinstance(skill_ts, FunctionToolset)

        # Tool names don't overlap
        assert set(browser_ts.tools).isdisjoint(set(skill_ts.tools))

        # Both have their expected tools
        assert "browser_navigate" in browser_ts.tools
        assert "list_skills" in skill_ts.tools


# ---------------------------------------------------------------------------
# CDP-mode setup/teardown
# ---------------------------------------------------------------------------

CDP_CONFIG = BrowserConfig(cdp_endpoint="http://localhost:9222")


def _make_mock_page_with_evaluate() -> AsyncMock:
    """Build a mock Playwright Page with explicit evaluate method."""
    page = _make_mock_page()
    page.evaluate = AsyncMock(return_value=None)
    return page


class TestBrowserToolsetCDPSetupTeardown:
    """BrowserToolset in CDP mode sets up and tears down correctly."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_setup_cdp_creates_manager_with_cdp_config(self, mock_mgr_cls: MagicMock) -> None:
        """BrowserManager is constructed with the CDP config."""
        page = _make_mock_page_with_evaluate()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset(config=CDP_CONFIG)
        await toolset.setup()

        mock_mgr_cls.assert_called_once_with(CDP_CONFIG)

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_setup_cdp_enters_manager(self, mock_mgr_cls: MagicMock) -> None:
        """__aenter__ is called (triggers connect_over_cdp internally)."""
        page = _make_mock_page_with_evaluate()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset(config=CDP_CONFIG)
        await toolset.setup()

        mock_mgr.__aenter__.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_teardown_cdp_exits_manager(self, mock_mgr_cls: MagicMock) -> None:
        """teardown() calls __aexit__ (disconnects, does not close)."""
        page = _make_mock_page_with_evaluate()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset(config=CDP_CONFIG)
        await toolset.setup()
        await toolset.teardown()

        mock_mgr.__aexit__.assert_awaited_once_with(None, None, None)


# ---------------------------------------------------------------------------
# CDP-mode tool wrapper integration
# ---------------------------------------------------------------------------


class TestBrowserToolsetCDPToolWrappers:
    """Tool wrappers receive a page from CDP-connected browser."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_navigate", new_callable=AsyncMock)
    async def test_navigate_works_in_cdp_mode(self, mock_nav: AsyncMock) -> None:
        mock_nav.return_value = "Navigated to Example (https://example.com)"
        page = _make_mock_page_with_evaluate()
        toolset = BrowserToolset(config=CDP_CONFIG)
        mgr = _make_mock_manager(page)
        toolset._manager = mgr  # noqa: SLF001

        result = await toolset._navigate("https://example.com")  # noqa: SLF001

        mock_nav.assert_awaited_once_with(
            "https://example.com",
            page=page,
            config=CDP_CONFIG,
        )
        assert "Navigated" in result

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_read_text", new_callable=AsyncMock)
    async def test_read_text_works_in_cdp_mode(self, mock_read: AsyncMock) -> None:
        mock_read.return_value = "CDP page text"
        page = _make_mock_page_with_evaluate()
        toolset = BrowserToolset(config=CDP_CONFIG)
        mgr = _make_mock_manager(page)
        toolset._manager = mgr  # noqa: SLF001

        result = await toolset._read_text()  # noqa: SLF001

        mock_read.assert_awaited_once_with(page=page, selector=None, max_length=5000)
        assert result == "CDP page text"

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.browser_navigate", new_callable=AsyncMock)
    async def test_navigate_safety_guard_in_cdp_mode(self, mock_nav: AsyncMock) -> None:
        """Navigate tool applies URL safety guard identically in CDP mode."""
        cdp_cfg = BrowserConfig(
            cdp_endpoint="http://localhost:9222",
            blocked_urls=[r".*evil\.com.*"],
        )
        mock_nav.return_value = "Navigated"
        page = _make_mock_page_with_evaluate()
        toolset = BrowserToolset(config=cdp_cfg)
        mgr = _make_mock_manager(page)
        toolset._manager = mgr  # noqa: SLF001

        await toolset._navigate("https://safe.com")  # noqa: SLF001

        # Config with blocked_urls is passed through to navigate
        mock_nav.assert_awaited_once_with(
            "https://safe.com",
            page=page,
            config=cdp_cfg,
        )


# ---------------------------------------------------------------------------
# Tab naming in CDP mode
# ---------------------------------------------------------------------------


class TestBrowserToolsetTabNaming:
    """Tab naming behavior differs between CDP and launch mode."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_cdp_setup_sets_owlbear_title(self, mock_mgr_cls: MagicMock) -> None:
        """In CDP mode, setup() sets window title with [OwlBear] prefix."""
        page = _make_mock_page_with_evaluate()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset(config=CDP_CONFIG)
        await toolset.setup()

        page.evaluate.assert_awaited_once_with("document.title = '[OwlBear] ' + document.title")

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_launch_setup_no_title_setting(self, mock_mgr_cls: MagicMock) -> None:
        """In launch mode, no title setting occurs."""
        page = _make_mock_page_with_evaluate()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset()  # default launch mode
        await toolset.setup()

        page.evaluate.assert_not_awaited()


# ---------------------------------------------------------------------------
# CDP warning log
# ---------------------------------------------------------------------------


class TestBrowserToolsetCDPWarningLog:
    """CDP mode logs a warning about full session access."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_cdp_setup_logs_warning(self, mock_mgr_cls: MagicMock) -> None:
        page = _make_mock_page_with_evaluate()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset(config=CDP_CONFIG)

        with patch("owlbear.tools.browser.toolset.logger") as mock_logger:
            await toolset.setup()
            mock_logger.warning.assert_called_once_with(
                "CDP mode: attached to user browser — full session access"
            )

    @pytest.mark.asyncio(loop_scope="function")
    @patch("owlbear.tools.browser.toolset.BrowserManager")
    async def test_launch_setup_no_cdp_warning(self, mock_mgr_cls: MagicMock) -> None:
        page = _make_mock_page_with_evaluate()
        mock_mgr = _make_mock_manager(page)
        mock_mgr_cls.return_value = mock_mgr

        toolset = BrowserToolset()  # launch mode

        with patch("owlbear.tools.browser.toolset.logger") as mock_logger:
            await toolset.setup()
            mock_logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestBrowserToolsetBackwardCompat:
    """Default BrowserToolset still uses launch mode — no CDP behavior."""

    def test_default_toolset_has_no_cdp_endpoint(self) -> None:
        toolset = BrowserToolset()
        assert toolset.config.cdp_endpoint is None

    def test_default_toolset_registers_six_tools(self) -> None:
        toolset = BrowserToolset()
        assert set(toolset.tools) == EXPECTED_TOOL_NAMES
