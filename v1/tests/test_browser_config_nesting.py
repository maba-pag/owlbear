"""Tests for AC #553: Nest BrowserConfig into OwlBearSettings.

Covers:
  AC1 — model_config must include nested_model_default_partial_update=True
  AC3 — Module layering: BrowserConfig defined in owlbear.config, re-exported
         from owlbear.tools.browser.config
  AC5 — All 4 bootstrap call sites use settings.browser instead of BrowserConfig()
  AC6 — BrowserManager and BrowserToolset fallback defaults unchanged
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import owlbear.config as _owlbear_config_module
import owlbear.tools.browser.config as _owlbear_tools_browser_config
from owlbear.bootstrap import _build_hydrator
from owlbear.bootstrap.hooks import build_hooks
from owlbear.bootstrap.knowledge import _build_web_search_toolset
from owlbear.bootstrap.toolsets import build_toolsets
from owlbear.channels.base import ChannelPlugin
from owlbear.config import OwlBearSettings
from owlbear.core.hooks import HookRegistry
from owlbear.tools.browser.config import BrowserConfig
from owlbear.tools.browser.manager import BrowserManager
from owlbear.tools.browser.toolset import BrowserToolset

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# AC1 — model_config must include nested_model_default_partial_update=True
# ---------------------------------------------------------------------------


class TestFromAC_ModelConfigNestedPartialUpdate:
    """AC1: model_config must have nested_model_default_partial_update=True."""

    def test_nested_model_default_partial_update_is_true(self) -> None:
        """nested_model_default_partial_update must be explicitly set to True."""
        assert OwlBearSettings.model_config.get("nested_model_default_partial_update") is True


# ---------------------------------------------------------------------------
# AC3 — Module layering: BrowserConfig class defined in owlbear.config
# ---------------------------------------------------------------------------


class TestFromAC_BrowserConfigModuleLayering:
    """AC3: BrowserConfig class must be defined in owlbear.config leaf node."""

    def test_browser_config_module_is_owlbear_config(self) -> None:
        """BrowserConfig.__module__ must be 'owlbear.config' after the class is moved there."""
        assert BrowserConfig.__module__ == "owlbear.config", (
            f"BrowserConfig is in {BrowserConfig.__module__!r}, "
            "expected 'owlbear.config'. Move from tools/browser/config.py."
        )

    def test_owlbear_config_has_no_import_from_tools_browser(self) -> None:
        """config.py must not import from owlbear.tools — leaf-node constraint."""
        source = inspect.getsource(_owlbear_config_module)
        assert "from owlbear.tools" not in source, (
            "config.py imports from owlbear.tools, violating the leaf-node rule. "
            "Define BrowserConfig in config.py; re-export from tools/browser/config.py."
        )

    def test_tools_browser_config_reexports_with_owlbear_config_module(self) -> None:
        """tools.browser.config.BrowserConfig must originate in owlbear.config after move."""
        tools_bc = _owlbear_tools_browser_config.BrowserConfig
        assert tools_bc.__module__ == "owlbear.config", (
            f"tools.browser.config.BrowserConfig.__module__ is {tools_bc.__module__!r}, "
            "expected 'owlbear.config'."
        )


# ---------------------------------------------------------------------------
# AC5 — bootstrap/hooks.py: build_hooks must use settings.browser
# ---------------------------------------------------------------------------


class TestFromAC_BootstrapHooksUseSettingsBrowser:
    """AC5: build_hooks must pass settings.browser to URLSafetyGuard."""

    def test_build_hooks_passes_settings_browser_to_url_safety_guard(self) -> None:
        """URLSafetyGuard must receive config=settings.browser, not a fresh BrowserConfig()."""
        custom_browser = BrowserConfig(headless=True)  # non-default
        settings = OwlBearSettings(browser=custom_browser)

        with patch("owlbear.bootstrap.hooks.URLSafetyGuard") as mock_guard_cls:
            mock_guard_cls.return_value = MagicMock()
            build_hooks(settings, workspace_root=None)

            assert mock_guard_cls.called, "URLSafetyGuard not instantiated in build_hooks"
            config_arg = mock_guard_cls.call_args.kwargs.get("config")
            assert config_arg == custom_browser, (
                f"URLSafetyGuard got headless={getattr(config_arg, 'headless', '?')}, "
                "expected headless=True from settings.browser."
            )


# ---------------------------------------------------------------------------
# AC5 — bootstrap/toolsets.py: build_toolsets must use settings.browser
# ---------------------------------------------------------------------------


class TestFromAC_BootstrapToolsetsUseSettingsBrowser:
    """AC5: build_toolsets must pass settings.browser to BrowserToolset."""

    def test_build_toolsets_passes_settings_browser_to_browser_toolset(
        self, tmp_path: Path
    ) -> None:
        """BrowserToolset must receive config=settings.browser, not a fresh BrowserConfig()."""
        custom_browser = BrowserConfig(headless=True)  # non-default
        settings = OwlBearSettings(browser=custom_browser, approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with patch("owlbear.bootstrap.toolsets.BrowserToolset") as mock_bt:
            mock_bt.return_value = MagicMock()
            build_toolsets(settings, tmp_path, hooks, channel)

            assert mock_bt.called, "BrowserToolset not instantiated in build_toolsets"
            config_arg = mock_bt.call_args.kwargs.get("config")
            assert config_arg == custom_browser, (
                f"BrowserToolset got headless={getattr(config_arg, 'headless', '?')}, "
                "expected headless=True from settings.browser."
            )


# ---------------------------------------------------------------------------
# AC5 — bootstrap/knowledge.py: _build_web_search_toolset must accept browser_config
# ---------------------------------------------------------------------------


class TestFromAC_WebSearchToolsetBrowserConfigParam:
    """AC5: _build_web_search_toolset must accept a browser_config parameter."""

    def test_build_web_search_toolset_signature_includes_browser_config(self) -> None:
        """_build_web_search_toolset must declare a browser_config parameter."""
        sig = inspect.signature(_build_web_search_toolset)
        assert "browser_config" in sig.parameters, (
            f"Parameters: {list(sig.parameters)}. "
            "AC5 requires browser_config so bootstrap can pass settings.browser."
        )

    def test_build_web_search_toolset_accepts_browser_config_kwarg(self) -> None:
        """Calling _build_web_search_toolset(browser_config=...) must not raise TypeError."""
        # Must not raise TypeError: "unexpected keyword argument 'browser_config'"
        _build_web_search_toolset(browser_config=BrowserConfig())


# ---------------------------------------------------------------------------
# AC5 — bootstrap/__init__.py: _build_hydrator must accept a settings param
# ---------------------------------------------------------------------------


class TestFromAC_HydratorSettingsParam:
    """AC5: _build_hydrator must accept a settings parameter and use settings.browser."""

    def test_build_hydrator_signature_includes_settings(self) -> None:
        """_build_hydrator must declare a 'settings' parameter."""
        sig = inspect.signature(_build_hydrator)
        assert "settings" in sig.parameters, (
            f"Parameters: {list(sig.parameters)}. "
            "AC5 requires a settings param so bootstrap can pass settings.browser."
        )

    def test_build_hydrator_accepts_settings_as_second_positional(
        self, tmp_path: Path
    ) -> None:
        """_build_hydrator(workspace, settings) must not raise TypeError."""
        # Currently: _build_hydrator(workspace) has no settings param → TypeError
        _build_hydrator(tmp_path, OwlBearSettings())

    def test_build_hydrator_uses_settings_browser_for_url_guard(
        self, tmp_path: Path
    ) -> None:
        """_build_hydrator must pass settings.browser to URLSafetyGuard."""
        custom_browser = BrowserConfig(headless=True)
        settings = OwlBearSettings(browser=custom_browser)

        with patch("owlbear.tools.browser.safety.URLSafetyGuard") as mock_guard_cls:
            mock_guard_cls.return_value = MagicMock()
            _build_hydrator(tmp_path, settings)

            assert mock_guard_cls.called, "URLSafetyGuard not created inside _build_hydrator"
            config_arg = mock_guard_cls.call_args.kwargs.get("config")
            assert config_arg == custom_browser, (
                f"Got headless={getattr(config_arg, 'headless', '?')}, "
                "expected headless=True from settings.browser."
            )


# ---------------------------------------------------------------------------
# AC6 — BrowserManager and BrowserToolset fallback defaults unchanged
# ---------------------------------------------------------------------------


class TestFromAC_BrowserFallbackDefaultsPreserved:
    """AC6: BrowserManager/BrowserToolset None-config fallback uses owlbear.config.BrowserConfig."""

    def test_browser_manager_none_config_fallback_from_owlbear_config(self) -> None:
        """BrowserManager(config=None)._config class must originate from owlbear.config."""
        mgr = BrowserManager(config=None)
        assert mgr._config.__class__.__module__ == "owlbear.config", (
            f"BrowserManager fallback is {mgr._config.__class__.__module__!r}, "
            "expected 'owlbear.config' after moving BrowserConfig there."
        )

    def test_browser_toolset_none_config_fallback_from_owlbear_config(self) -> None:
        """BrowserToolset(config=None)._config class must originate from owlbear.config."""
        ts = BrowserToolset(config=None)
        assert ts._config.__class__.__module__ == "owlbear.config", (
            f"BrowserToolset fallback is {ts._config.__class__.__module__!r}, "
            "expected 'owlbear.config' after moving BrowserConfig there."
        )
