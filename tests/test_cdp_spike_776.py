"""Failing tests for task #776: Implement cdp-spike.py per research #752.

Covers all 11 AC items:
  AC1:  .owlbear/scratch/cdp-spike.py exists
  AC2:  Runnable with `uv run python .owlbear/scratch/cdp-spike.py`
  AC3:  Finds Edge at standard Windows paths + EDGE_PATH override
  AC4:  Launch args include --remote-debugging-port, --user-data-dir, --remote-allow-origins
  AC5:  Connects via playwright.chromium.connect_over_cdp("http://127.0.0.1:9222", is_local=True)
  AC6:  Configurable URL via --url CLI arg and TARGET_URL env var
  AC7:  Detects SSO redirect, login page, and auto-authentication
  AC8:  Extracts page.inner_text("body") and logs text length
  AC9:  Handles all error cases from research §3.4 with clear messages
  AC10: Logs timestamps for EDR/DLP correlation
  AC11: Cleans up (disconnect, terminate subprocess) on all exit paths

Strategy:
- Subprocess tests for file existence, runnable, CLI flags, env vars, error messages.
- importlib tests for helper functions (playwright pre-mocked in sys.modules so tests
  fail on missing file / missing function, NOT on playwright installation state).

All tests fail on current HEAD (.owlbear/scratch/cdp-spike.py does not exist yet).
"""

from __future__ import annotations

import contextlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
_SPIKE_PATH = ROOT / ".owlbear" / "scratch" / "cdp-spike.py"
_PROFILE_SUBPATH = ".owlbear/scratch/cdp-spike-profile"
_PROFILE_DIR = ROOT / ".owlbear" / "scratch" / "cdp-spike-profile"
_DEFAULT_PORT = 9222
_DEFAULT_HOST = "127.0.0.1"
_CDP_ENDPOINT = f"http://{_DEFAULT_HOST}:{_DEFAULT_PORT}"
_ALLOW_ORIGINS_FLAG = f"--remote-allow-origins={_CDP_ENDPOINT}"
_EDGE_X86 = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
_EDGE_PF = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
_IDP_URL = "https://login.microsoftonline.com/org/oauth2/authorize"
_TARGET_URL = "https://company.sharepoint.com/sites/team"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(*args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run cdp-spike.py via python with given CLI arguments."""
    import os  # noqa: PLC0415

    env = {**os.environ, **(extra_env or {})}
    return subprocess.run(
        [sys.executable, str(_SPIKE_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _make_pw_mock() -> MagicMock:
    """Return a MagicMock that satisfies 'from playwright.sync_api import ...' imports."""
    mod = MagicMock()
    mod.sync_playwright = MagicMock()
    mod.TimeoutError = type("TimeoutError", (Exception,), {})
    return mod


def _load_spike() -> Any:  # noqa: ANN401
    """Import cdp-spike.py as a module with playwright stubs injected.

    Tests that call this will fail with pytest.fail() when the file does not exist,
    and with AttributeError when a required helper function is missing.
    """
    if not _SPIKE_PATH.exists():
        pytest.fail(
            f"cdp-spike.py not found at {_SPIKE_PATH} — AC1 not satisfied; "
            "builder must create the script."
        )

    # Pre-stub playwright so the script can be imported in a test environment
    # that does not have playwright installed.
    pw_stub = _make_pw_mock()
    injected: list[str] = []
    for key in ("playwright", "playwright.sync_api"):
        if key not in sys.modules:
            sys.modules[key] = pw_stub
            injected.append(key)

    # Remove any previously cached version so each load is fresh.
    sys.modules.pop("cdp_spike", None)
    try:
        spec = importlib.util.spec_from_file_location("cdp_spike", _SPIKE_PATH)
        assert spec is not None
        assert spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        for key in injected:
            sys.modules.pop(key, None)

    return mod


def _make_mock_page(url: str = _TARGET_URL) -> MagicMock:
    page = MagicMock()
    page.url = url
    page.title = MagicMock(return_value="SharePoint Home")
    page.inner_text = MagicMock(return_value="Body text " * 20)
    page.query_selector = MagicMock(return_value=None)
    page.goto = MagicMock()
    return page


def _make_mock_browser(page: MagicMock | None = None) -> MagicMock:
    if page is None:
        page = _make_mock_page()
    browser = MagicMock()
    context = MagicMock()
    context.pages = [page]
    browser.contexts = [context]
    browser.disconnect = MagicMock()
    browser.close = MagicMock()
    return browser


def _make_mock_process() -> MagicMock:
    proc = MagicMock()
    proc.pid = 42000
    proc.returncode = None
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = MagicMock(return_value=0)
    return proc


# ---------------------------------------------------------------------------
# TestFromAC_ScriptExists  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """AC1: Script exists at .owlbear/scratch/cdp-spike.py."""

    def test_script_file_exists_at_expected_path(self) -> None:
        assert _SPIKE_PATH.exists(), (
            f"Script not found at {_SPIKE_PATH}. "
            "Builder must create .owlbear/scratch/cdp-spike.py."
        )


# ---------------------------------------------------------------------------
# TestFromAC_Runnable  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_Runnable:
    """AC2: Runnable with `uv run python .owlbear/scratch/cdp-spike.py`."""

    def test_help_flag_exits_zero(self) -> None:
        """--help must print usage and exit 0."""
        result = _run("--help")
        assert result.returncode == 0, (
            f"--help exited {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_help_output_documents_url_option(self) -> None:
        """--help output must mention --url or TARGET_URL so users know how to configure the target."""
        result = _run("--help")
        assert "--url" in result.stdout or "TARGET_URL" in result.stdout, (
            f"--help output does not mention --url or TARGET_URL.\nstdout: {result.stdout}"
        )

    def test_script_has_main_guard(self) -> None:
        """Script must guard main logic under `if __name__ == '__main__':` to allow importlib loading."""
        text = _SPIKE_PATH.read_text(encoding="utf-8")
        assert '__name__ == "__main__"' in text or "__name__ == '__main__'" in text, (
            "Script must contain `if __name__ == '__main__':` guard."
        )

    def test_script_has_docstring(self) -> None:
        """Script must have a module docstring describing its purpose."""
        text = _SPIKE_PATH.read_text(encoding="utf-8")
        # File must start with triple-quote docstring (possibly after shebang/encoding)
        stripped = text.lstrip()
        assert stripped.startswith(('"""', "'''")), (
            "Script must have a module-level docstring."
        )


# ---------------------------------------------------------------------------
# TestFromAC_EdgeDiscovery  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_EdgeDiscovery:
    """AC3: Finds Edge executable at standard Windows paths."""

    def test_find_edge_returns_x86_path_when_present(self) -> None:
        """Primary path C:\\Program Files (x86)\\...\\msedge.exe is checked first."""
        spike = _load_spike()
        find_edge = getattr(spike, "_find_edge", None) or getattr(spike, "find_edge", None)
        assert callable(find_edge), "Script must expose a _find_edge() / find_edge() helper."

        def _exists(self: Any) -> bool:  # noqa: ANN401
            return str(self) == _EDGE_X86

        with patch.object(Path, "exists", _exists):
            result = find_edge()
        assert str(result) == _EDGE_X86

    def test_find_edge_falls_back_to_program_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to C:\\Program Files\\...\\msedge.exe when x86 path is missing."""
        spike = _load_spike()
        find_edge = getattr(spike, "_find_edge", None) or getattr(spike, "find_edge", None)
        assert callable(find_edge)

        monkeypatch.delenv("EDGE_PATH", raising=False)

        def _exists(self: Any) -> bool:  # noqa: ANN401
            p = str(self)
            if p == _EDGE_X86:
                return False
            return p == _EDGE_PF

        with patch.object(Path, "exists", _exists):
            result = find_edge()
        assert str(result) == _EDGE_PF

    def test_edge_path_env_var_overrides_default_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """EDGE_PATH env var must be honoured before any filesystem checks."""
        spike = _load_spike()
        find_edge = getattr(spike, "_find_edge", None) or getattr(spike, "find_edge", None)
        assert callable(find_edge)

        custom = r"D:\custom\edge\msedge.exe"
        monkeypatch.setenv("EDGE_PATH", custom)
        with patch.object(Path, "exists", return_value=True):
            result = find_edge()
        assert str(result) == custom

    def test_find_edge_raises_on_missing_binary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Must raise an exception (or call sys.exit) when Edge cannot be found."""
        spike = _load_spike()
        find_edge = getattr(spike, "_find_edge", None) or getattr(spike, "find_edge", None)
        assert callable(find_edge)

        monkeypatch.delenv("EDGE_PATH", raising=False)
        with (
            patch.object(Path, "exists", return_value=False),
            pytest.raises((SystemExit, FileNotFoundError, RuntimeError, OSError)),
        ):
            find_edge()

    def test_edge_not_found_error_message_guides_user(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Not-found error message must mention Edge or EDGE_PATH so user knows what to do."""
        spike = _load_spike()
        find_edge = getattr(spike, "_find_edge", None) or getattr(spike, "find_edge", None)
        assert callable(find_edge)

        monkeypatch.delenv("EDGE_PATH", raising=False)
        with (
            patch.object(Path, "exists", return_value=False),
            contextlib.suppress(SystemExit, FileNotFoundError, RuntimeError, OSError),
        ):
            find_edge()
        captured = capsys.readouterr()
        output = (captured.out + captured.err).lower()
        assert "edge" in output or "edge_path" in output.lower(), (
            f"Error output must mention Edge or EDGE_PATH. Got: {captured.out!r} / {captured.err!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_LaunchArgs  (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_LaunchArgs:
    """AC4: Launch args include --remote-debugging-port, --user-data-dir, --remote-allow-origins."""

    def _get_build_args(self, spike: Any) -> Any:  # noqa: ANN401
        fn = getattr(spike, "_build_launch_args", None) or getattr(spike, "build_launch_args", None)
        assert callable(fn), "Script must expose _build_launch_args() / build_launch_args()."
        return fn

    def test_launch_args_include_remote_debugging_port(self) -> None:
        spike = _load_spike()
        build_args = self._get_build_args(spike)
        args = build_args(port=_DEFAULT_PORT, user_data_dir=str(_PROFILE_DIR))
        combined = " ".join(str(a) for a in args)
        assert f"--remote-debugging-port={_DEFAULT_PORT}" in combined, (
            f"--remote-debugging-port={_DEFAULT_PORT} not found in: {args}"
        )

    def test_launch_args_include_user_data_dir(self) -> None:
        """Chrome 136 requirement: --user-data-dir must be present."""
        spike = _load_spike()
        build_args = self._get_build_args(spike)
        args = build_args(port=_DEFAULT_PORT, user_data_dir=str(_PROFILE_DIR))
        combined = " ".join(str(a) for a in args)
        assert "--user-data-dir" in combined, f"--user-data-dir not found in: {args}"

    def test_launch_args_include_remote_allow_origins(self) -> None:
        """Security (Gap A / brief HR#4): --remote-allow-origins must be present."""
        spike = _load_spike()
        build_args = self._get_build_args(spike)
        args = build_args(port=_DEFAULT_PORT, user_data_dir=str(_PROFILE_DIR))
        combined = " ".join(str(a) for a in args)
        assert "--remote-allow-origins" in combined, (
            f"--remote-allow-origins not found in: {args}. "
            "Required by brief HR#4 (Gap A from research #776)."
        )

    def test_remote_allow_origins_binds_to_127_0_0_1_port(self) -> None:
        """--remote-allow-origins must include http://127.0.0.1:{port}."""
        spike = _load_spike()
        build_args = self._get_build_args(spike)
        args = build_args(port=_DEFAULT_PORT, user_data_dir=str(_PROFILE_DIR))
        combined = " ".join(str(a) for a in args)
        assert f"http://{_DEFAULT_HOST}:{_DEFAULT_PORT}" in combined, (
            f"--remote-allow-origins must include {_CDP_ENDPOINT}. Got: {args}"
        )

    def test_user_data_dir_uses_spike_profile_subdirectory(self) -> None:
        """Default --user-data-dir must point to .owlbear/scratch/cdp-spike-profile."""
        spike = _load_spike()
        build_args = self._get_build_args(spike)
        args = build_args(port=_DEFAULT_PORT, user_data_dir=str(_PROFILE_DIR))
        combined = " ".join(str(a) for a in args)
        assert "cdp-spike-profile" in combined, (
            f"Args must reference cdp-spike-profile directory. Got: {args}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CDPConnection  (AC5)
# ---------------------------------------------------------------------------


class TestFromAC_CDPConnection:
    """AC5: Connects via playwright.chromium.connect_over_cdp("http://127.0.0.1:9222", is_local=True)."""

    def _get_connect_fn(self, spike: Any) -> Any:  # noqa: ANN401
        fn = getattr(spike, "_connect_cdp", None) or getattr(spike, "connect_cdp", None)
        assert callable(fn), "Script must expose _connect_cdp() / connect_cdp() helper."
        return fn

    def test_connect_cdp_passes_127_0_0_1_endpoint(self) -> None:
        spike = _load_spike()
        connect_cdp = self._get_connect_fn(spike)

        mock_browser = _make_mock_browser()
        mock_pw = MagicMock()
        mock_pw.chromium.connect_over_cdp = MagicMock(return_value=mock_browser)

        connect_cdp(mock_pw, port=_DEFAULT_PORT)

        call_args = mock_pw.chromium.connect_over_cdp.call_args
        assert call_args is not None, "connect_over_cdp was never called."
        positional_and_kw = str(call_args)
        assert _CDP_ENDPOINT in positional_and_kw, (
            f"connect_over_cdp must be called with {_CDP_ENDPOINT!r}. call_args={call_args}"
        )

    def test_connect_cdp_passes_is_local_true(self) -> None:
        """is_local=True is required for local CDP connections (performance + correctness)."""
        spike = _load_spike()
        connect_cdp = self._get_connect_fn(spike)

        mock_browser = _make_mock_browser()
        mock_pw = MagicMock()
        mock_pw.chromium.connect_over_cdp = MagicMock(return_value=mock_browser)

        connect_cdp(mock_pw, port=_DEFAULT_PORT)

        call_args = mock_pw.chromium.connect_over_cdp.call_args
        assert call_args is not None
        # is_local=True must appear either as keyword arg or positional
        kw_is_local = call_args.kwargs.get("is_local")
        positional_is_local = (len(call_args.args) > 1 and call_args.args[1] is True)
        assert kw_is_local is True or positional_is_local, (
            f"connect_over_cdp must be called with is_local=True. call_args={call_args}"
        )

    def test_connect_cdp_returns_browser_object(self) -> None:
        spike = _load_spike()
        connect_cdp = self._get_connect_fn(spike)

        mock_browser = _make_mock_browser()
        mock_pw = MagicMock()
        mock_pw.chromium.connect_over_cdp = MagicMock(return_value=mock_browser)

        result = connect_cdp(mock_pw, port=_DEFAULT_PORT)
        assert result is mock_browser


# ---------------------------------------------------------------------------
# TestFromAC_URLConfig  (AC6)
# ---------------------------------------------------------------------------


class TestFromAC_URLConfig:
    """AC6: Configurable target URL via --url CLI arg and TARGET_URL env var (Gap B)."""

    def _get_parse_args(self, spike: Any) -> Any:  # noqa: ANN401
        fn = getattr(spike, "_parse_args", None) or getattr(spike, "parse_args", None)
        assert callable(fn), "Script must expose _parse_args() / parse_args() for argparse testing."
        return fn

    def test_parse_args_accepts_url_flag(self) -> None:
        """--url CLI flag must be accepted by argparse."""
        spike = _load_spike()
        parse_args = self._get_parse_args(spike)
        ns = parse_args(["--url", "https://example.sharepoint.com/page"])
        url = getattr(ns, "url", None) or getattr(ns, "target_url", None)
        assert url == "https://example.sharepoint.com/page", (
            f"--url flag not parsed correctly. Namespace: {ns}"
        )

    def test_target_url_env_var_used_as_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TARGET_URL env var must be used when --url is not provided (Gap B)."""
        spike = _load_spike()
        parse_args = self._get_parse_args(spike)
        env_url = "https://env-var-sharepoint.example.com/sites/home"
        monkeypatch.setenv("TARGET_URL", env_url)
        ns = parse_args([])
        url = getattr(ns, "url", None) or getattr(ns, "target_url", None)
        assert url == env_url or (url is not None and "env-var-sharepoint" in url), (
            f"TARGET_URL env var not used as default. url={url!r}. Namespace: {ns}"
        )

    def test_hardcoded_default_url_when_no_arg_and_no_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A sensible SharePoint default must exist when neither --url nor TARGET_URL is set."""
        spike = _load_spike()
        parse_args = self._get_parse_args(spike)
        monkeypatch.delenv("TARGET_URL", raising=False)
        ns = parse_args([])
        url = getattr(ns, "url", None) or getattr(ns, "target_url", None)
        assert url is not None, f"Expected a default HTTPS URL, got: {url!r}."
        assert url.startswith("https://"), f"URL must start with https://, got: {url!r}."


# ---------------------------------------------------------------------------
# TestFromAC_SSODetection  (AC7)
# ---------------------------------------------------------------------------


class TestFromAC_SSODetection:
    """AC7: Detect SSO redirect vs auto-authentication vs login page."""

    def _get_detect_sso(self, spike: Any) -> Any:  # noqa: ANN401
        fn = getattr(spike, "_detect_sso", None) or getattr(spike, "detect_sso", None)
        assert callable(fn), "Script must expose _detect_sso() / detect_sso() helper."
        return fn

    def test_detects_sso_redirect_when_url_is_idp(self) -> None:
        """URL redirected to IdP domain → 'sso_redirect' (or string containing 'redirect')."""
        spike = _load_spike()
        detect_sso = self._get_detect_sso(spike)
        page = _make_mock_page(url=_IDP_URL)
        page.query_selector = MagicMock(return_value=None)
        result = detect_sso(page, target_url=_TARGET_URL)
        assert "redirect" in str(result).lower() or "sso" in str(result).lower(), (
            f"Expected SSO redirect classification, got: {result!r}"
        )

    def test_detects_login_page_when_password_input_present(self) -> None:
        """Password input found on page → 'login_page' (or string containing 'login')."""
        spike = _load_spike()
        detect_sso = self._get_detect_sso(spike)
        page = _make_mock_page(url="https://login.microsoftonline.com/login")
        mock_input = MagicMock()
        page.query_selector = MagicMock(return_value=mock_input)  # password field found
        result = detect_sso(page, target_url=_TARGET_URL)
        assert "login" in str(result).lower() or "auth" in str(result).lower(), (
            f"Expected login page classification, got: {result!r}"
        )

    def test_detects_authenticated_when_url_matches_target(self) -> None:
        """Page URL matching target domain → 'authenticated' (or string containing 'auth'/'success')."""
        spike = _load_spike()
        detect_sso = self._get_detect_sso(spike)
        page = _make_mock_page(url=_TARGET_URL)
        page.query_selector = MagicMock(return_value=None)
        result = detect_sso(page, target_url=_TARGET_URL)
        assert (
            "auth" in str(result).lower()
            or "success" in str(result).lower()
            or "ok" in str(result).lower()
        ), (
            f"Expected authenticated classification, got: {result!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_TextExtraction  (AC8)
# ---------------------------------------------------------------------------


class TestFromAC_TextExtraction:
    """AC8: Extracts page.inner_text("body") and logs text length."""

    def _get_extract_text(self, spike: Any) -> Any:  # noqa: ANN401
        fn = getattr(spike, "_extract_text", None) or getattr(spike, "extract_text", None)
        assert callable(fn), "Script must expose _extract_text() / extract_text() helper."
        return fn

    def test_extract_calls_inner_text_with_body_selector(self) -> None:
        """page.inner_text('body') must be called to extract page content."""
        spike = _load_spike()
        extract_text = self._get_extract_text(spike)
        page = _make_mock_page()
        extract_text(page)
        page.inner_text.assert_called_with("body")

    def test_extract_returns_the_body_text(self) -> None:
        spike = _load_spike()
        extract_text = self._get_extract_text(spike)
        page = _make_mock_page()
        page.inner_text = MagicMock(return_value="Extracted body text here")
        result = extract_text(page)
        assert result == "Extracted body text here", (
            f"extract_text must return the string from page.inner_text('body'). Got: {result!r}"
        )

    def test_extract_logs_text_length(self, capsys: pytest.CaptureFixture[str]) -> None:
        """AC8 requires logging text length — must print character count to stdout."""
        spike = _load_spike()
        extract_text = self._get_extract_text(spike)
        page = _make_mock_page()
        page.inner_text = MagicMock(return_value="X" * 512)
        extract_text(page)
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "512" in output or "length" in output.lower(), (
            f"Expected text length (512) or 'length' in log output. Got: {output!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ErrorHandling  (AC9)
# ---------------------------------------------------------------------------


class TestFromAC_ErrorHandling:
    """AC9: Handles all error cases from research §3.4 with clear messages."""

    def test_cdp_timeout_message_mentions_cdp_or_connection(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TimeoutError from connect_over_cdp must produce a 'CDP connection failed' message."""
        spike = _load_spike()
        connect_cdp = getattr(spike, "_connect_cdp", None) or getattr(spike, "connect_cdp", None)
        assert callable(connect_cdp), "Script must expose _connect_cdp() / connect_cdp()."

        # Build a TimeoutError type using the spike's own reference or a generic one
        timeout_error_cls = getattr(spike, "PlaywrightTimeoutError", None) or TimeoutError

        mock_pw = MagicMock()
        mock_pw.chromium.connect_over_cdp = MagicMock(
            side_effect=timeout_error_cls("CDP endpoint did not respond")
        )

        with contextlib.suppress(SystemExit, RuntimeError, TimeoutError):
            connect_cdp(mock_pw, port=_DEFAULT_PORT)

        captured = capsys.readouterr()
        output = (captured.out + captured.err).lower()
        assert "cdp" in output or "timeout" in output or "connect" in output or "fail" in output, (
            f"Expected clear error message about CDP/timeout/connection failure. Got: {output!r}"
        )

    def test_port_in_use_detected_by_helper(self) -> None:
        """check_port (or similar) must return truthy when port is already bound."""
        spike = _load_spike()
        check_port = (
            getattr(spike, "_check_port_in_use", None)
            or getattr(spike, "check_port_in_use", None)
            or getattr(spike, "_check_port", None)
            or getattr(spike, "check_port", None)
        )
        assert callable(check_port), (
            "Script must expose a port-in-use check helper "
            "_check_port_in_use() / check_port_in_use() / _check_port() / check_port()."
        )

        # Patch socket.socket so connect_ex returns 0 (= port open / in use)
        with patch("socket.socket") as mock_sock_cls:
            inst = MagicMock()
            inst.__enter__ = MagicMock(return_value=inst)
            inst.__exit__ = MagicMock(return_value=False)
            inst.connect_ex = MagicMock(return_value=0)
            mock_sock_cls.return_value = inst
            result = check_port(_DEFAULT_PORT)

        assert result, (
            f"check_port({_DEFAULT_PORT}) must return truthy when port is already bound. Got: {result!r}"
        )

    def test_port_not_in_use_detected_by_helper(self) -> None:
        """check_port must return falsy when port is free."""
        spike = _load_spike()
        check_port = (
            getattr(spike, "_check_port_in_use", None)
            or getattr(spike, "check_port_in_use", None)
            or getattr(spike, "_check_port", None)
            or getattr(spike, "check_port", None)
        )
        assert callable(check_port)

        with patch("socket.socket") as mock_sock_cls:
            inst = MagicMock()
            inst.__enter__ = MagicMock(return_value=inst)
            inst.__exit__ = MagicMock(return_value=False)
            inst.connect_ex = MagicMock(return_value=111)  # non-zero = port free
            mock_sock_cls.return_value = inst
            result = check_port(_DEFAULT_PORT)

        assert not result, (
            f"check_port({_DEFAULT_PORT}) must return falsy when port is free. Got: {result!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_TimestampLogging  (AC10)
# ---------------------------------------------------------------------------


class TestFromAC_TimestampLogging:
    """AC10: Logs timestamps for EDR/DLP correlation."""

    def _get_log_step(self, spike: Any) -> Any:  # noqa: ANN401
        fn = getattr(spike, "_log_step", None) or getattr(spike, "log_step", None)
        assert callable(fn), "Script must expose _log_step() / log_step() for timestamped logging."
        return fn

    def test_log_step_includes_timestamp_digits(self, capsys: pytest.CaptureFixture[str]) -> None:
        """log_step must print a timestamp (ISO8601/datetime) alongside the message."""
        spike = _load_spike()
        log_step = self._get_log_step(spike)
        log_step("STEP_1 starting Edge launch")
        captured = capsys.readouterr()
        output = captured.out + captured.err
        # Timestamp must contain at minimum a 4-digit year
        assert re.search(r"\d{4}", output), (
            f"No timestamp found in log_step output. Got: {output!r}"
        )

    def test_log_step_includes_the_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """log_step must echo the step message alongside the timestamp."""
        spike = _load_spike()
        log_step = self._get_log_step(spike)
        sentinel = "UNIQUE_SENTINEL_MESSAGE_42"
        log_step(sentinel)
        captured = capsys.readouterr()
        assert sentinel in (captured.out + captured.err), (
            f"log_step did not echo the message. Got: {captured.out!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_Cleanup  (AC11)
# ---------------------------------------------------------------------------


class TestFromAC_Cleanup:
    """AC11: Cleans up (disconnect, terminate subprocess) on all exit paths."""

    def _get_cleanup(self, spike: Any) -> Any:  # noqa: ANN401
        fn = getattr(spike, "_cleanup", None) or getattr(spike, "cleanup", None)
        assert callable(fn), "Script must expose _cleanup() / cleanup() helper."
        return fn

    def test_cleanup_disconnects_browser(self) -> None:
        spike = _load_spike()
        cleanup = self._get_cleanup(spike)
        browser = _make_mock_browser()
        proc = _make_mock_process()
        cleanup(browser=browser, process=proc)
        assert browser.disconnect.called or browser.close.called, (
            "cleanup must call browser.disconnect() or browser.close()."
        )

    def test_cleanup_terminates_process(self) -> None:
        spike = _load_spike()
        cleanup = self._get_cleanup(spike)
        browser = _make_mock_browser()
        proc = _make_mock_process()
        cleanup(browser=browser, process=proc)
        assert proc.terminate.called or proc.kill.called, (
            "cleanup must call process.terminate() or process.kill()."
        )

    def test_cleanup_handles_none_browser_without_raising(self) -> None:
        """cleanup must guard against None browser (e.g., connect_over_cdp failed)."""
        spike = _load_spike()
        cleanup = self._get_cleanup(spike)
        proc = _make_mock_process()
        cleanup(browser=None, process=proc)  # must not raise

    def test_cleanup_handles_none_process_without_raising(self) -> None:
        """cleanup must guard against None process (e.g., Edge failed to launch)."""
        spike = _load_spike()
        cleanup = self._get_cleanup(spike)
        browser = _make_mock_browser()
        cleanup(browser=browser, process=None)  # must not raise

    def test_script_contains_try_finally_pattern(self) -> None:
        """AC11 (Gap C): Script must wrap the main flow in try/finally for guaranteed cleanup."""
        text = _SPIKE_PATH.read_text(encoding="utf-8")
        has_try = "try:" in text
        has_finally = "finally:" in text
        assert has_try, (
            "Script must contain 'try:' block for cleanup on Ctrl+C and unexpected errors "
            "(AC11, Gap C from research #776)."
        )
        assert has_finally, (
            "Script must contain 'finally:' block for guaranteed cleanup "
            "(AC11, Gap C from research #776)."
        )
