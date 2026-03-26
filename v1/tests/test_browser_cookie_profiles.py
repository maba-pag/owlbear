"""Tests for cookie-persistence profiles in BrowserConfig and BrowserManager.

TDD RED phase for #760.  All tests MUST fail until the feature is implemented.

Covers: config fields + validator, cookie save/restore, graceful degradation,
atomic write, no-cookie-logging, both launch/CDP modes, and bootstrap wiring.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.tools.browser.config import BrowserConfig

MANAGER_MODULE = "owlbear.tools.browser.manager"

# Synthetic cookie data — values are fake, never real credentials.
SAMPLE_COOKIES = [
    {"name": "session", "value": "abc123secret", "domain": "example.com", "path": "/"},
    {"name": "pref", "value": "dark-mode", "domain": "example.com", "path": "/settings"},
]


def _assert_no_json_files(directory: Path) -> None:
    """Assert no .json files exist in *directory* (sync helper for ASYNC240)."""
    json_files = list(directory.glob("*.json"))
    assert not json_files, "Cookie files created when profile is None"


# ---------------------------------------------------------------------------
# Shared Playwright mock fixture (mirrors pw_mocks from test_browser_manager)
# ---------------------------------------------------------------------------


@pytest.fixture
def pw_mocks():
    """Playwright mock chain with cookie support on both launch and CDP contexts."""
    mock_page = AsyncMock(name="Page")
    mock_page.set_default_timeout = MagicMock()

    mock_context = AsyncMock(name="BrowserContext")
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.cookies = AsyncMock(return_value=SAMPLE_COOKIES)
    mock_context.add_cookies = AsyncMock()

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
    mock_cdp_context.cookies = AsyncMock(return_value=SAMPLE_COOKIES)
    mock_cdp_context.add_cookies = AsyncMock()

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


# ---------------------------------------------------------------------------
# Config: profile_name + profile_dir fields, model validator
# ---------------------------------------------------------------------------


class TestFromACCookieProfileConfig:
    """BrowserConfig must expose profile_name, profile_dir, and a both-or-neither validator."""

    def test_default_profile_name_is_none(self) -> None:
        cfg = BrowserConfig()
        assert cfg.profile_name is None

    def test_default_profile_dir_is_none(self) -> None:
        cfg = BrowserConfig()
        assert cfg.profile_dir is None

    def test_both_set_is_valid(self, tmp_path: Path) -> None:
        cfg = BrowserConfig(profile_name="myprofile", profile_dir=tmp_path)
        assert cfg.profile_name == "myprofile"
        assert cfg.profile_dir == tmp_path

    def test_profile_name_only_raises(self) -> None:
        with pytest.raises(ValidationError):
            BrowserConfig(profile_name="myprofile")

    def test_profile_dir_only_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            BrowserConfig(profile_dir=tmp_path)


# ---------------------------------------------------------------------------
# Cookie save: __aexit__ writes cookies to {profile_dir}/{profile_name}.json
# ---------------------------------------------------------------------------


class TestFromACCookieSave:
    """Exiting BrowserManager saves cookies to a JSON file in profile_dir."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cookies_saved_on_exit_launch_mode(
        self, pw_mocks: dict, tmp_path: Path
    ) -> None:
        """Launch mode: cookie file created in profile_dir after __aexit__."""
        cfg = BrowserConfig(profile_name="test", profile_dir=tmp_path)
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        cookie_file = tmp_path / "test.json"
        assert cookie_file.exists(), "Cookie file was not written on exit"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cookies_saved_on_exit_cdp_mode(
        self, pw_mocks: dict, tmp_path: Path
    ) -> None:
        """CDP mode: cookie file created in profile_dir after __aexit__."""
        cfg = BrowserConfig(
            profile_name="test",
            profile_dir=tmp_path,
            cdp_endpoint="http://localhost:9222",
        )
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        cookie_file = tmp_path / "test.json"
        assert cookie_file.exists(), "Cookie file was not written on exit (CDP mode)"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_saved_cookies_are_valid_json(
        self, pw_mocks: dict, tmp_path: Path
    ) -> None:
        """Saved cookie file contains valid JSON matching context.cookies() output."""
        cfg = BrowserConfig(profile_name="test", profile_dir=tmp_path)
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        cookie_file = tmp_path / "test.json"
        saved = json.loads(cookie_file.read_text(encoding="utf-8"))
        assert saved == SAMPLE_COOKIES

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_save_when_no_profile(self, pw_mocks: dict, tmp_path: Path) -> None:
        """When profile_name is None, no cookie file should be written."""
        cfg = BrowserConfig()
        # Verify the field exists (fails until field is added)
        assert cfg.profile_name is None
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        _assert_no_json_files(tmp_path)


# ---------------------------------------------------------------------------
# Cookie restore: __aenter__ restores cookies via add_cookies()
# ---------------------------------------------------------------------------


class TestFromACCookieRestore:
    """Entering BrowserManager restores cookies from profile JSON when it exists."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cookies_restored_on_enter_launch_mode(
        self, pw_mocks: dict, tmp_path: Path
    ) -> None:
        """Launch mode: add_cookies() called with saved cookies on __aenter__."""
        cookie_file = tmp_path / "test.json"
        cookie_file.write_text(json.dumps(SAMPLE_COOKIES), encoding="utf-8")

        cfg = BrowserConfig(profile_name="test", profile_dir=tmp_path)
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["context"].add_cookies.assert_awaited_once_with(SAMPLE_COOKIES)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cookies_restored_on_enter_cdp_mode(
        self, pw_mocks: dict, tmp_path: Path
    ) -> None:
        """CDP mode: add_cookies() called with saved cookies on __aenter__."""
        cookie_file = tmp_path / "test.json"
        cookie_file.write_text(json.dumps(SAMPLE_COOKIES), encoding="utf-8")

        cfg = BrowserConfig(
            profile_name="test",
            profile_dir=tmp_path,
            cdp_endpoint="http://localhost:9222",
        )
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["cdp_context"].add_cookies.assert_awaited_once_with(SAMPLE_COOKIES)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_restore_when_no_profile(self, pw_mocks: dict) -> None:
        """When profile is None, add_cookies() must NOT be called."""
        cfg = BrowserConfig()
        # Verify the field exists (fails until field is added)
        assert cfg.profile_name is None
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["context"].add_cookies.assert_not_awaited()


# ---------------------------------------------------------------------------
# Graceful degradation: corrupt JSON → warning, missing file → no-op
# ---------------------------------------------------------------------------


class TestFromACCookieGracefulDegradation:
    """Corrupt or missing profile JSON: log warning and continue, never block."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_missing_file_is_noop(self, pw_mocks: dict, tmp_path: Path) -> None:
        """Missing cookie file on enter: no error, no add_cookies() call."""
        cfg = BrowserConfig(profile_name="nonexistent", profile_dir=tmp_path)
        # Verify the config accepted the profile (fails until field is added)
        assert cfg.profile_name == "nonexistent"
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["context"].add_cookies.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_corrupt_json_logs_warning(
        self, pw_mocks: dict, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Corrupt JSON file: a WARNING is logged, browser starts normally."""
        cookie_file = tmp_path / "bad.json"
        cookie_file.write_text("{invalid json!!!}", encoding="utf-8")

        cfg = BrowserConfig(profile_name="bad", profile_dir=tmp_path)
        # Verify the config accepted the profile (fails until field is added)
        assert cfg.profile_name == "bad"
        with (
            caplog.at_level(logging.WARNING),
            patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]),
        ):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        assert any(
            record.levelno == logging.WARNING for record in caplog.records
        ), "No WARNING logged for corrupt cookie file"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_corrupt_json_does_not_raise(
        self, pw_mocks: dict, tmp_path: Path
    ) -> None:
        """Corrupt JSON: browser session starts normally, no exception raised."""
        cookie_file = tmp_path / "corrupt.json"
        cookie_file.write_text("not-json-at-all", encoding="utf-8")

        cfg = BrowserConfig(profile_name="corrupt", profile_dir=tmp_path)
        # Verify the config accepted the profile (fails until field is added)
        assert cfg.profile_name == "corrupt"
        with patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            # Must not raise — graceful degradation
            async with BrowserManager(config=cfg):
                pass


# ---------------------------------------------------------------------------
# Atomic write: verify temp + os.replace pattern
# ---------------------------------------------------------------------------


class TestFromACCookieAtomicWrite:
    """Cookie file written atomically: temp file + os.replace()."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_os_replace_used_for_atomic_write(
        self, pw_mocks: dict, tmp_path: Path
    ) -> None:
        """os.replace() is called to atomically move temp file to final path."""
        cfg = BrowserConfig(profile_name="atomic", profile_dir=tmp_path)
        with (
            patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]),
            patch("os.replace", wraps=os.replace) as mock_replace,
        ):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        mock_replace.assert_called_once()
        final_path = str(mock_replace.call_args[0][1])
        assert final_path.endswith("atomic.json"), f"Final path was {final_path}"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_temp_file_in_same_directory(
        self, pw_mocks: dict, tmp_path: Path
    ) -> None:
        """Temp file is created in the same directory as the final cookie file."""
        cfg = BrowserConfig(profile_name="samedir", profile_dir=tmp_path)
        with (
            patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]),
            patch("os.replace", wraps=os.replace) as mock_replace,
        ):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        mock_replace.assert_called_once()
        temp_path = Path(str(mock_replace.call_args[0][0]))
        assert temp_path.parent == tmp_path, "Temp file not in same directory as cookie file"


# ---------------------------------------------------------------------------
# No cookie logging: cookie values must not appear in log output
# ---------------------------------------------------------------------------


class TestFromACCookieNoLogging:
    """Cookie values (potential auth tokens) must never appear in log output."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_save_does_not_log_cookie_values(
        self, pw_mocks: dict, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """On save, cookie values like 'abc123secret' must not appear in logs."""
        cfg = BrowserConfig(profile_name="secret", profile_dir=tmp_path)
        with (
            caplog.at_level(logging.DEBUG),
            patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]),
        ):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        for cookie in SAMPLE_COOKIES:
            assert cookie["value"] not in caplog.text, (
                f"Cookie value {cookie['value']!r} leaked into logs during save"
            )
        # Guard against vacuous pass: verify that cookies were actually saved
        cookie_file = tmp_path / "secret.json"
        assert cookie_file.exists(), "Cookie file not written — assertion above is vacuous"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_restore_does_not_log_cookie_values(
        self, pw_mocks: dict, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """On restore, cookie values must not appear in logs."""
        cookie_file = tmp_path / "logged.json"
        cookie_file.write_text(json.dumps(SAMPLE_COOKIES), encoding="utf-8")

        cfg = BrowserConfig(profile_name="logged", profile_dir=tmp_path)
        with (
            caplog.at_level(logging.DEBUG),
            patch(f"{MANAGER_MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]),
        ):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                # Guard: verify restore actually happened
                pw_mocks["context"].add_cookies.assert_awaited_once()

        for cookie in SAMPLE_COOKIES:
            assert cookie["value"] not in caplog.text, (
                f"Cookie value {cookie['value']!r} leaked into logs during restore"
            )


# ---------------------------------------------------------------------------
# Bootstrap wiring: sandbox_path validation + mkdir for profile_dir
# ---------------------------------------------------------------------------


class TestFromACCookieBootstrapWiring:
    """Bootstrap validates profile_dir with sandbox_path and creates the directory."""

    @pytest.fixture(autouse=True)
    def _mock_copilot(self):
        """Prevent real Copilot client creation during bootstrap tests."""
        with patch(
            "owlbear.bootstrap.create_copilot_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            yield

    def test_bootstrap_imports_sandbox_path(self) -> None:
        """Bootstrap module must import sandbox_path for profile validation."""
        import owlbear.bootstrap.toolsets as mod

        assert hasattr(mod, "sandbox_path"), "sandbox_path not imported in bootstrap.toolsets"

    def test_browser_config_has_profile_dir_after_bootstrap(self, tmp_path: Path) -> None:
        """BrowserToolset config must have profile_dir field after build_toolsets."""
        from owlbear.bootstrap import build_toolsets
        from owlbear.channels.base import ChannelPlugin
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookRegistry
        from owlbear.tools.protocols import unwrap

        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

        from owlbear.tools.browser.toolset import BrowserToolset

        browser_ts = next(
            unwrap(ts) for ts in toolsets if isinstance(unwrap(ts), BrowserToolset)
        )
        assert hasattr(browser_ts._config, "profile_dir")

    def test_profile_dir_created_by_bootstrap(self, tmp_path: Path) -> None:
        """build_toolsets creates a browser profiles directory under workspace."""
        from owlbear.bootstrap import build_toolsets
        from owlbear.channels.base import ChannelPlugin
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookRegistry

        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        build_toolsets(settings, tmp_path, hooks, channel)

        profile_dirs = list(tmp_path.glob("**/browser_profiles"))
        assert len(profile_dirs) >= 1, "No browser_profiles directory created by bootstrap"
