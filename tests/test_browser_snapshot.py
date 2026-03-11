"""Tests for BrowserManager.snapshot() — CDP accessibility tree snapshot.

RED-phase tests for task #735. All tests must FAIL (the implementation
does not exist yet).  Mock CDPSession.send() with canned AXNode responses.
"""

from __future__ import annotations

import dataclasses
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.tools.browser.config import BrowserConfig

MODULE = "owlbear.tools.browser.manager"

# ---------------------------------------------------------------------------
# Canned CDP Accessibility.getFullAXTree response
# ---------------------------------------------------------------------------
# Mix of roles: interactive (button, link, textbox), text (StaticText, heading),
# non-interactive (generic, RootWebArea), and one ignored node.

CANNED_AX_TREE: dict = {
    "nodes": [
        {
            "nodeId": "1",
            "backendDOMNodeId": 1,
            "role": {"type": "role", "value": "RootWebArea"},
            "name": {"type": "computedString", "value": "Test Page"},
            "description": {"type": "computedString", "value": ""},
            "properties": [],
            "ignored": False,
        },
        {
            "nodeId": "2",
            "backendDOMNodeId": 2,
            "role": {"type": "role", "value": "button"},
            "name": {"type": "computedString", "value": "Submit"},
            "description": {"type": "computedString", "value": "Submit the form"},
            "properties": [
                {"name": "focusable", "value": {"type": "booleanOrUndefined", "value": True}},
            ],
            "ignored": False,
        },
        {
            "nodeId": "3",
            "backendDOMNodeId": 3,
            "role": {"type": "role", "value": "link"},
            "name": {"type": "computedString", "value": "Home"},
            "description": {"type": "computedString", "value": ""},
            "properties": [
                {"name": "focusable", "value": {"type": "booleanOrUndefined", "value": True}},
            ],
            "ignored": False,
        },
        {
            "nodeId": "4",
            "backendDOMNodeId": 4,
            "role": {"type": "role", "value": "StaticText"},
            "name": {"type": "computedString", "value": "Hello World"},
            "description": {"type": "computedString", "value": ""},
            "properties": [],
            "ignored": False,
        },
        {
            "nodeId": "5",
            "backendDOMNodeId": 5,
            "role": {"type": "role", "value": "heading"},
            "name": {"type": "computedString", "value": "Page Title"},
            "description": {"type": "computedString", "value": ""},
            "properties": [
                {"name": "level", "value": {"type": "integer", "value": 2}},
            ],
            "ignored": False,
        },
        {
            "nodeId": "6",
            "backendDOMNodeId": 6,
            "role": {"type": "role", "value": "generic"},
            "name": {"type": "computedString", "value": ""},
            "description": {"type": "computedString", "value": ""},
            "properties": [],
            "ignored": False,
        },
        {
            "nodeId": "7",
            "backendDOMNodeId": 7,
            "role": {"type": "role", "value": "textbox"},
            "name": {"type": "computedString", "value": "Email"},
            "description": {"type": "computedString", "value": "Enter your email"},
            "properties": [
                {"name": "focusable", "value": {"type": "booleanOrUndefined", "value": True}},
            ],
            "ignored": False,
        },
        {
            "nodeId": "8",
            "backendDOMNodeId": 8,
            "role": {"type": "role", "value": "none"},
            "name": {"type": "computedString", "value": ""},
            "description": {"type": "computedString", "value": ""},
            "properties": [],
            "ignored": True,
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pw_mocks():
    """Build a complete Playwright mock chain (mirrors test_browser_manager.py)."""
    mock_page = AsyncMock(name="Page")
    mock_page.set_default_timeout = MagicMock()
    mock_context = AsyncMock(name="BrowserContext")
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser = AsyncMock(name="Browser")
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_pw = AsyncMock(name="Playwright")
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw_instance = AsyncMock(name="PlaywrightContextManager")
    mock_pw_instance.start = AsyncMock(return_value=mock_pw)

    # CDP-mode mocks
    mock_cdp_page = AsyncMock(name="CDPPage")
    mock_cdp_page.set_default_timeout = MagicMock()
    mock_cdp_context = AsyncMock(name="CDPBrowserContext")
    mock_cdp_context.new_page = AsyncMock(return_value=mock_cdp_page)
    mock_cdp_browser = AsyncMock(name="CDPBrowser")
    mock_cdp_browser.contexts = [MagicMock(name="DefaultContext_DO_NOT_USE")]
    mock_cdp_browser.new_context = AsyncMock(return_value=mock_cdp_context)
    mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_cdp_browser)

    return {
        "page": mock_page,
        "context": mock_context,
        "browser": mock_browser,
        "pw": mock_pw,
        "pw_instance": mock_pw_instance,
        "cdp_page": mock_cdp_page,
        "cdp_context": mock_cdp_context,
        "cdp_browser": mock_cdp_browser,
    }


@pytest.fixture
def cdp_session():
    """Mock CDP session whose send() returns the canned AX tree."""
    session = AsyncMock(name="CDPSession")
    session.send = AsyncMock(return_value=CANNED_AX_TREE)
    session.detach = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# TestFromAC_AXNodeInfo — AC: frozen dataclass with correct fields
# ---------------------------------------------------------------------------


class TestFromAC_AXNodeInfo:  # noqa: N801
    """AXNodeInfo frozen dataclass: id, role, name, description, properties."""

    def test_construction_with_all_fields(self):
        from owlbear.tools.browser.manager import AXNodeInfo

        info = AXNodeInfo(
            id=42,
            role="button",
            name="Submit",
            description="Submit the form",
            properties={"focusable": True},
        )
        assert info.id == 42
        assert info.role == "button"
        assert info.name == "Submit"
        assert info.description == "Submit the form"
        assert info.properties == {"focusable": True}

    def test_is_dataclass(self):
        from owlbear.tools.browser.manager import AXNodeInfo

        assert dataclasses.is_dataclass(AXNodeInfo)

    def test_is_frozen(self):
        from owlbear.tools.browser.manager import AXNodeInfo

        info = AXNodeInfo(id=1, role="link", name="Home", description="", properties={})
        with pytest.raises(dataclasses.FrozenInstanceError):
            info.role = "button"  # type: ignore[misc]

    def test_has_expected_field_names(self):
        from owlbear.tools.browser.manager import AXNodeInfo

        field_names = {f.name for f in dataclasses.fields(AXNodeInfo)}
        assert field_names == {"id", "role", "name", "description", "properties"}


# ---------------------------------------------------------------------------
# TestFromAC_SnapshotFull — AC: filter='full' returns all non-ignored nodes
# ---------------------------------------------------------------------------


class TestFromAC_SnapshotFull:  # noqa: N801
    """snapshot(filter='full') returns list[AXNodeInfo] with all non-ignored nodes."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_all_non_ignored_nodes(self, pw_mocks, cdp_session):
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="full")

        # 8 canned nodes, 1 ignored → expect 7
        assert len(result) == 7

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_ax_node_info_instances(self, pw_mocks, cdp_session):
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import AXNodeInfo, BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="full")

        assert all(isinstance(node, AXNodeInfo) for node in result)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_excludes_ignored_nodes(self, pw_mocks, cdp_session):
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="full")

        # backendDOMNodeId=8 is ignored — must not appear
        ids = {node.id for node in result}
        assert 8 not in ids

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_tree_returns_empty_list(self, pw_mocks):
        empty_session = AsyncMock(name="CDPSession")
        empty_session.send = AsyncMock(return_value={"nodes": []})
        empty_session.detach = AsyncMock()
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=empty_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="full")

        assert result == []


# ---------------------------------------------------------------------------
# TestFromAC_SnapshotInteractive — AC: filter='interactive'
# ---------------------------------------------------------------------------


class TestFromAC_SnapshotInteractive:  # noqa: N801
    """snapshot(filter='interactive') returns only focusable/actionable nodes."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_interactive_roles(self, pw_mocks, cdp_session):
        """button, link, textbox should all be included."""
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="interactive")

        roles = {node.role for node in result}
        assert "button" in roles
        assert "link" in roles
        assert "textbox" in roles

    @pytest.mark.asyncio(loop_scope="function")
    async def test_excludes_non_interactive(self, pw_mocks, cdp_session):
        """StaticText, heading, generic, RootWebArea excluded from interactive."""
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="interactive")

        roles = {node.role for node in result}
        assert "StaticText" not in roles
        assert "heading" not in roles
        assert "generic" not in roles

    @pytest.mark.asyncio(loop_scope="function")
    async def test_focusable_generic_included(self, pw_mocks):
        """A generic node with focusable=True should be included."""
        focusable_generic = {
            "nodes": [
                {
                    "nodeId": "1",
                    "backendDOMNodeId": 10,
                    "role": {"type": "role", "value": "generic"},
                    "name": {"type": "computedString", "value": "Clickable div"},
                    "description": {"type": "computedString", "value": ""},
                    "properties": [
                        {
                            "name": "focusable",
                            "value": {"type": "booleanOrUndefined", "value": True},
                        },
                    ],
                    "ignored": False,
                },
            ],
        }
        session = AsyncMock(name="CDPSession")
        session.send = AsyncMock(return_value=focusable_generic)
        session.detach = AsyncMock()
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="interactive")

        assert len(result) == 1
        assert result[0].name == "Clickable div"


# ---------------------------------------------------------------------------
# TestFromAC_SnapshotText — AC: filter='text'
# ---------------------------------------------------------------------------


class TestFromAC_SnapshotText:  # noqa: N801
    """snapshot(filter='text') returns only StaticText + heading nodes."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_static_text(self, pw_mocks, cdp_session):
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="text")

        roles = {node.role for node in result}
        assert "StaticText" in roles

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_headings(self, pw_mocks, cdp_session):
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="text")

        roles = {node.role for node in result}
        assert "heading" in roles

    @pytest.mark.asyncio(loop_scope="function")
    async def test_excludes_non_text_nodes(self, pw_mocks, cdp_session):
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="text")

        roles = {node.role for node in result}
        assert "button" not in roles
        assert "link" not in roles
        assert "generic" not in roles
        assert "textbox" not in roles


# ---------------------------------------------------------------------------
# TestFromAC_SnapshotCDPSession — AC: CDP session lifecycle
# ---------------------------------------------------------------------------


class TestFromAC_SnapshotCDPSession:  # noqa: N801
    """CDP session is created and detached per call (no leaked sessions)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_creates_and_detaches_session(self, pw_mocks, cdp_session):
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                await mgr.snapshot(filter="full")

        pw_mocks["context"].new_cdp_session.assert_awaited_once()
        cdp_session.detach.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_detaches_session_on_send_error(self, pw_mocks):
        """CDP session must be detached even when send() raises."""
        error_session = AsyncMock(name="CDPSession")
        error_session.send = AsyncMock(side_effect=RuntimeError("CDP error"))
        error_session.detach = AsyncMock()
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=error_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                with pytest.raises(RuntimeError, match="CDP error"):
                    await mgr.snapshot(filter="full")

        error_session.detach.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_each_call_creates_new_session(self, pw_mocks, cdp_session):
        """Two snapshot() calls should create and detach two separate sessions."""
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                await mgr.snapshot(filter="full")
                await mgr.snapshot(filter="text")

        assert pw_mocks["context"].new_cdp_session.await_count == 2
        assert cdp_session.detach.await_count == 2


# ---------------------------------------------------------------------------
# TestFromAC_SnapshotBothModes — AC: works in both launch and CDP modes
# ---------------------------------------------------------------------------


class TestFromAC_SnapshotBothModes:  # noqa: N801
    """snapshot() works in both launch and CDP modes."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_launch_mode(self, pw_mocks, cdp_session):
        """Launch mode: snapshot uses context.new_cdp_session."""
        pw_mocks["context"].new_cdp_session = AsyncMock(return_value=cdp_session)

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import AXNodeInfo, BrowserManager

            async with BrowserManager() as mgr:
                result = await mgr.snapshot(filter="full")

        assert len(result) > 0
        assert all(isinstance(n, AXNodeInfo) for n in result)
        pw_mocks["context"].new_cdp_session.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_mode(self, pw_mocks, cdp_session):
        """CDP mode: snapshot uses the CDP context's new_cdp_session."""
        pw_mocks["cdp_context"].new_cdp_session = AsyncMock(return_value=cdp_session)
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import AXNodeInfo, BrowserManager

            async with BrowserManager(config=cfg) as mgr:
                result = await mgr.snapshot(filter="full")

        assert len(result) > 0
        assert all(isinstance(n, AXNodeInfo) for n in result)
        pw_mocks["cdp_context"].new_cdp_session.assert_awaited_once()
