"""Failing tests for task #777: Expand cdp-spike.py with trafilatura extraction quality test.

Covers all 4 AC items:
  AC1:  Spike script includes trafilatura extraction after CDP text extraction
  AC2:  Both standard and favor_precision modes tested
  AC3:  Output logged with quality metrics (text length, paragraph count, boilerplate indicators)
  AC4:  At least 5 URLs configured (3 SharePoint, 2 Confluence)

Strategy:
- importlib tests for new helper function (_extract_trafilatura / extract_trafilatura).
- trafilatura stubbed via pytest fixture + patch.dict(sys.modules) — active both during
  module load AND during function calls (handles both top-level and inline imports).
- playwright also stubbed so spike can be loaded without browser driver installed.
- URL configuration tests use getattr on spike module constants and argparse fallback.

All tests fail on current HEAD (cdp-spike.py has no trafilatura helper, no DEFAULT_URLS,
no --urls argument).
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
_SPIKE_PATH = ROOT / ".owlbear" / "scratch" / "cdp-spike.py"
_SAMPLE_URL = "https://contoso.sharepoint.com/sites/team"
_SAMPLE_HTML = (
    "<html><head><title>Team Site</title></head><body>"
    "<nav>Home \u203a Sites \u203a Team</nav>"
    "<main>"
    "<h1>Welcome to the Team Site</h1>"
    "<p>First content paragraph with important information.</p>"
    "<p>Second paragraph with project details.</p>"
    "</main>"
    "<footer>Copyright 2026 Contoso. Privacy Policy. Terms of Use.</footer>"
    "</body></html>"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trafilatura_stub() -> MagicMock:
    """Return a MagicMock stub for the trafilatura package."""
    stub = MagicMock()
    stub.extract = MagicMock(return_value="# Welcome to the Team Site\n\nFirst content paragraph.\n\nSecond paragraph.")
    return stub


@pytest.fixture()
def trafilatura_stub() -> Iterator[MagicMock]:
    """Inject trafilatura stub into sys.modules for the duration of the test.

    This ensures both module-level ``import trafilatura`` (resolved at load time)
    and inline ``import trafilatura`` (resolved at call time) see the stub.
    """
    stub = _make_trafilatura_stub()
    with patch.dict(sys.modules, {"trafilatura": stub}):
        yield stub


def _load_spike() -> Any:  # noqa: ANN401
    """Import cdp-spike.py fresh with playwright stubs pre-injected.

    Trafilatura is managed separately by the ``trafilatura_stub`` fixture —
    callers must activate that fixture before calling this function.

    Raises pytest.fail if the spike file does not exist.
    """
    if not _SPIKE_PATH.exists():
        pytest.fail(
            f"cdp-spike.py not found at {_SPIKE_PATH} — builder must implement the script before tests can run."
        )

    pw_stub = MagicMock()
    pw_stub.sync_playwright = MagicMock()
    pw_stub.TimeoutError = type("TimeoutError", (Exception,), {})

    injected: list[str] = []
    for key in ("playwright", "playwright.sync_api"):
        if key not in sys.modules:
            sys.modules[key] = pw_stub
            injected.append(key)

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


def _make_mock_page(url: str = _SAMPLE_URL) -> MagicMock:
    """Return a MagicMock page object with sensible defaults."""
    page = MagicMock()
    page.url = url
    page.inner_text = MagicMock(return_value="Body text " * 20)
    page.content = MagicMock(return_value=_SAMPLE_HTML)
    page.query_selector = MagicMock(return_value=None)
    page.goto = MagicMock()
    return page


def _get_extract_fn(spike: Any) -> Any:  # noqa: ANN401
    """Locate the trafilatura extraction helper in the spike module."""
    return getattr(spike, "_extract_trafilatura", None) or getattr(spike, "extract_trafilatura", None)


# ---------------------------------------------------------------------------
# TestFromAC_TrafilaturaExtraction  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_TrafilaturaExtraction:
    """AC1: Spike script includes trafilatura extraction after CDP text extraction."""

    def test_extract_trafilatura_function_exists(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Script must expose _extract_trafilatura() or extract_trafilatura() helper."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), (
            "Script must expose '_extract_trafilatura()' or 'extract_trafilatura()'. "
            "AC1 requires trafilatura extraction added after CDP text extraction."
        )

    def test_extract_trafilatura_calls_page_content_for_raw_html(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Must call page.content() to capture raw HTML — not just page.inner_text()."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        assert page.content.called, (
            "_extract_trafilatura must call page.content() to obtain full HTML. "
            "AC1 specifies 'capture raw page.content() (full HTML)' — inner_text() is insufficient."
        )

    def test_extract_trafilatura_passes_html_to_trafilatura(self, trafilatura_stub: MagicMock) -> None:
        """Must pass HTML from page.content() into trafilatura.extract()."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        page = _make_mock_page()
        page.content = MagicMock(return_value=_SAMPLE_HTML)
        fn(page, _SAMPLE_URL)

        assert trafilatura_stub.extract.called, (
            "_extract_trafilatura must call trafilatura.extract(). "
            "AC1 requires trafilatura to process the HTML fetched via page.content()."
        )
        # Verify HTML from page.content() was passed in (first positional arg)
        first_call = trafilatura_stub.extract.call_args_list[0]
        html_arg = first_call.args[0] if first_call.args else first_call.kwargs.get("text")
        assert html_arg == _SAMPLE_HTML, (
            f"trafilatura.extract() must receive the HTML from page.content(). Got: {repr(html_arg)[:120]}"
        )

    def test_extract_trafilatura_handles_none_from_trafilatura_without_raising(
        self, trafilatura_stub: MagicMock
    ) -> None:
        """When trafilatura.extract returns None, must not raise — log gracefully instead."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        trafilatura_stub.extract = MagicMock(return_value=None)
        page = _make_mock_page()
        try:
            fn(page, _SAMPLE_URL)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(
                f"_extract_trafilatura raised {type(exc).__name__} when trafilatura.extract "
                f"returned None. Must handle None gracefully (log a warning, continue)."
            )

    def test_extract_trafilatura_produces_log_output_on_success(
        self, trafilatura_stub: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Must produce stdout/stderr log output containing extraction metrics."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        trafilatura_stub.extract = MagicMock(return_value="Content paragraph one.\n\nContent paragraph two.")
        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        captured = capsys.readouterr()
        assert (captured.out + captured.err).strip(), (
            "_extract_trafilatura must produce log output. "
            "AC3 requires quality metrics (text length, paragraph count, boilerplate) to be logged."
        )


# ---------------------------------------------------------------------------
# TestFromAC_ExtractionModes  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_ExtractionModes:
    """AC2: Both standard and favor_precision modes tested per extraction."""

    def test_trafilatura_called_at_least_twice_per_extraction(self, trafilatura_stub: MagicMock) -> None:
        """Must invoke trafilatura.extract at least twice: once standard, once with favor_precision."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        trafilatura_stub.extract.reset_mock()
        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        call_count = trafilatura_stub.extract.call_count
        assert call_count >= 2, (
            f"_extract_trafilatura must call trafilatura.extract() at least twice "
            f"(standard mode + favor_precision=True mode). Got {call_count} call(s). "
            "AC2 requires both modes be exercised."
        )

    def test_standard_mode_call_does_not_set_favor_precision_true(self, trafilatura_stub: MagicMock) -> None:
        """At least one call must NOT have favor_precision=True (standard mode)."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        calls = trafilatura_stub.extract.call_args_list
        has_standard = any(not c.kwargs.get("favor_precision", False) for c in calls)
        assert has_standard, (
            f"_extract_trafilatura must invoke trafilatura.extract() in standard mode "
            f"(without favor_precision=True). AC2 requires both modes. "
            f"Recorded calls: {calls}"
        )

    def test_favor_precision_true_mode_called(self, trafilatura_stub: MagicMock) -> None:
        """At least one call must pass favor_precision=True."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        calls = trafilatura_stub.extract.call_args_list
        has_precision = any(c.kwargs.get("favor_precision") is True for c in calls)
        assert has_precision, (
            f"_extract_trafilatura must call trafilatura.extract(favor_precision=True). "
            f"AC2 explicitly requires this mode. Recorded calls: {calls}"
        )

    def test_both_modes_use_output_format_markdown(self, trafilatura_stub: MagicMock) -> None:
        """Both extraction calls must specify output_format='markdown'."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        calls = trafilatura_stub.extract.call_args_list
        assert len(calls) >= 2, f"Expected at least 2 trafilatura.extract() calls, got {len(calls)}."
        for i, c in enumerate(calls):
            fmt = c.kwargs.get("output_format")
            assert fmt == "markdown", (
                f"Call #{i + 1} to trafilatura.extract() must use output_format='markdown'. "
                f"Specified in AC2 call signature. Got output_format={fmt!r}. Call: {c}"
            )

    def test_both_modes_pass_include_links_true(self, trafilatura_stub: MagicMock) -> None:
        """Both extraction calls must pass include_links=True per AC2 spec."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        calls = trafilatura_stub.extract.call_args_list
        assert len(calls) >= 2, f"Expected at least 2 trafilatura.extract() calls, got {len(calls)}."
        for i, c in enumerate(calls):
            include_links = c.kwargs.get("include_links")
            assert include_links is True, (
                f"Call #{i + 1} to trafilatura.extract() must pass include_links=True. "
                f"AC2 specifies this parameter. Got include_links={include_links!r}. Call: {c}"
            )

    def test_both_modes_pass_url_parameter(self, trafilatura_stub: MagicMock) -> None:
        """Both extraction calls must pass the page URL to trafilatura (url= parameter)."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        page = _make_mock_page(url=_SAMPLE_URL)
        fn(page, _SAMPLE_URL)

        calls = trafilatura_stub.extract.call_args_list
        assert len(calls) >= 2, f"Expected at least 2 trafilatura.extract() calls, got {len(calls)}."
        for i, c in enumerate(calls):
            passed_url = c.kwargs.get("url") or c.kwargs.get("record_id")
            assert passed_url is not None, (
                f"Call #{i + 1} to trafilatura.extract() must receive the page URL via url= "
                f"parameter. AC2 specifies 'url=page_url' for accurate link resolution. "
                f"Call: {c}"
            )


# ---------------------------------------------------------------------------
# TestFromAC_QualityMetrics  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_QualityMetrics:
    """AC3: Output logged with quality metrics (text length, paragraph count, boilerplate indicators)."""

    def test_quality_metrics_log_text_length(
        self, trafilatura_stub: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Must log character count of trafilatura output text."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        content = "Word " * 100  # exactly 500 chars
        trafilatura_stub.extract = MagicMock(return_value=content)
        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "500" in output or "length" in output.lower(), (
            f"Quality metrics must include text length (500 chars in this test). "
            f"AC3 specifies 'text length' as a required metric. Got: {output!r}"
        )

    def test_quality_metrics_log_paragraph_count(
        self, trafilatura_stub: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Must log paragraph count from trafilatura extraction output."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        # Three paragraphs separated by double newlines (standard markdown format)
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        trafilatura_stub.extract = MagicMock(return_value=content)
        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "3" in output or "paragraph" in output.lower() or "para" in output.lower(), (
            f"Quality metrics must include paragraph count (3 paragraphs in this test). "
            f"AC3 specifies 'paragraph count' as a required metric. Got: {output!r}"
        )

    def test_quality_metrics_log_boilerplate_indicators(
        self, trafilatura_stub: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Must detect and log boilerplate indicators (nav text, footer text, breadcrumbs)."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        # Content that contains known boilerplate patterns from research §3.3
        boilerplate_content = (
            "Home \u203a Sites \u203a Team\n"
            "Sign in\n"
            "Copyright 2026 Contoso\n"
            "Privacy Policy\n"
            "Terms of Use\n"
            "Powered by Viva\n"
            "Cookie settings\n"
            "Footer links here"
        )
        trafilatura_stub.extract = MagicMock(return_value=boilerplate_content)
        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        captured = capsys.readouterr()
        output = (captured.out + captured.err).lower()

        # Any of these indicate boilerplate detection was logged
        boilerplate_signals = [
            "boilerplate",
            "nav",
            "footer",
            "breadcrumb",
            "indicator",
            "copyright",
            "sign in",
            "sign out",
            "privacy",
            "terms",
            "powered",
            "cookie",
        ]
        found = any(signal in output for signal in boilerplate_signals)
        assert found, (
            f"Quality metrics must log boilerplate indicator presence. "
            f"AC3 specifies 'boilerplate indicators (nav text, footer text, breadcrumb patterns)'. "
            f"Got: {(captured.out + captured.err)!r}"
        )

    def test_quality_metrics_handle_none_extraction_gracefully(
        self, trafilatura_stub: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When trafilatura returns None, metrics log must reflect zero/empty result."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        trafilatura_stub.extract = MagicMock(return_value=None)
        page = _make_mock_page()
        fn(page, _SAMPLE_URL)  # must not raise

        captured = capsys.readouterr()
        output = (captured.out + captured.err).lower()
        assert (
            "none" in output
            or "0" in output
            or "no content" in output
            or "empty" in output
            or "null" in output
            or "failed" in output
            or "error" in output
        ), (
            f"When trafilatura.extract returns None, metrics log must acknowledge it "
            f"(e.g., length=0, 'no content', 'extraction failed'). Got: {output!r}"
        )

    def test_quality_metrics_compare_standard_vs_precision_output(
        self, trafilatura_stub: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Must log a comparison between standard and favor_precision extraction results."""
        spike = _load_spike()
        fn = _get_extract_fn(spike)
        assert callable(fn), "Script must expose _extract_trafilatura() helper."

        standard_text = "Long boilerplate nav text\n\nReal paragraph.\n\nAnother real paragraph."
        precision_text = "Real paragraph.\n\nAnother real paragraph."

        def _side_effect(*args: Any, **kwargs: Any) -> str:  # noqa: ARG001
            return precision_text if kwargs.get("favor_precision") else standard_text

        trafilatura_stub.extract = MagicMock(side_effect=_side_effect)
        page = _make_mock_page()
        fn(page, _SAMPLE_URL)

        captured = capsys.readouterr()
        output = (captured.out + captured.err).lower()

        # Must log at least one of: mode names, length values, or explicit comparison
        assert (
            "standard" in output
            or "precision" in output
            or "favor_precision" in output
            or str(len(standard_text)) in (captured.out + captured.err)
            or str(len(precision_text)) in (captured.out + captured.err)
        ), (
            f"Quality metrics must compare standard vs favor_precision extraction output. "
            f"AC3 specifies comparing both modes; logging separate lengths satisfies this. "
            f"Got: {(captured.out + captured.err)!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_URLConfiguration  (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_URLConfiguration:
    """AC4: At least 5 URLs configured (3 SharePoint, 2 Confluence)."""

    def _get_parse_args(self, spike: Any) -> Any:  # noqa: ANN401
        fn = getattr(spike, "_parse_args", None) or getattr(spike, "parse_args", None)
        assert callable(fn), "Script must expose _parse_args() / parse_args()."
        return fn

    def test_script_accepts_multiple_urls_argument(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Must accept --urls multi-value argument for configuring multiple targets."""
        spike = _load_spike()
        parse_args = self._get_parse_args(spike)

        try:
            ns = parse_args(
                [
                    "--urls",
                    "https://contoso.sharepoint.com/s/a",
                    "https://contoso.sharepoint.com/s/b",
                ]
            )
        except SystemExit:
            pytest.fail(
                "Script argparse rejected --urls flag (SystemExit). "
                "AC4 requires multi-URL support via --urls or TARGET_URLS env var."
            )

        urls = getattr(ns, "urls", None) or getattr(ns, "url", None)
        assert urls is not None, (
            "--urls parsed without error but namespace has no 'urls' attribute. "
            "AC4 requires a --urls argument that returns a list of URLs."
        )

    def test_default_urls_include_at_least_five_entries(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
        monkeypatch: pytest.MonkeyPatch,  # noqa: ARG002
    ) -> None:
        """Default URL list must have at least 5 entries when no env/CLI override is given."""
        spike = _load_spike()

        default_urls: Any = (
            getattr(spike, "DEFAULT_URLS", None)
            or getattr(spike, "_DEFAULT_URLS", None)
            or getattr(spike, "TARGET_URLS", None)
            or getattr(spike, "_TARGET_URLS", None)
        )

        if default_urls is None:
            # Fallback: check argparse default for --urls
            parse_args = self._get_parse_args(spike)
            monkeypatch.delenv("TARGET_URLS", raising=False)
            monkeypatch.delenv("TARGET_URL", raising=False)
            ns = parse_args([])
            default_urls = getattr(ns, "urls", None)

        assert default_urls is not None, (
            "Script must define DEFAULT_URLS / _DEFAULT_URLS constant or a --urls default "
            "containing at least 5 URLs. "
            "AC4 requires 3 SharePoint + 2 Confluence URLs preconfigured."
        )

        url_list = (
            [u.strip() for u in default_urls.split(",") if u.strip()]
            if isinstance(default_urls, str)
            else list(default_urls)
        )
        assert len(url_list) >= 5, (
            f"Default URL list must have at least 5 entries (3 SharePoint + 2 Confluence). "
            f"AC4 requirement. Got {len(url_list)}: {url_list}"
        )

    def test_default_urls_include_three_sharepoint_entries(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Default URL list must include at least 3 SharePoint placeholder URLs."""
        spike = _load_spike()

        default_urls: Any = (
            getattr(spike, "DEFAULT_URLS", None)
            or getattr(spike, "_DEFAULT_URLS", None)
            or getattr(spike, "TARGET_URLS", None)
            or getattr(spike, "_TARGET_URLS", None)
        )
        assert default_urls is not None, (
            "Script must define DEFAULT_URLS / _DEFAULT_URLS constant. "
            "AC4 requires at least 3 SharePoint placeholder URLs to be preconfigured."
        )

        url_list = (
            [u.strip() for u in default_urls.split(",") if u.strip()]
            if isinstance(default_urls, str)
            else list(default_urls)
        )
        sp_count = sum(1 for u in url_list if "sharepoint" in u.lower())
        assert sp_count >= 3, (
            f"Default URL list must have at least 3 SharePoint entries. "
            f"AC4 requirement (3 SharePoint, 2 Confluence). "
            f"Got {sp_count} SharePoint URL(s) in: {url_list}"
        )

    def test_default_urls_include_two_confluence_entries(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Default URL list must include at least 2 Confluence placeholder URLs."""
        spike = _load_spike()

        default_urls: Any = (
            getattr(spike, "DEFAULT_URLS", None)
            or getattr(spike, "_DEFAULT_URLS", None)
            or getattr(spike, "TARGET_URLS", None)
            or getattr(spike, "_TARGET_URLS", None)
        )
        assert default_urls is not None, (
            "Script must define DEFAULT_URLS / _DEFAULT_URLS constant. "
            "AC4 requires at least 2 Confluence placeholder URLs to be preconfigured."
        )

        url_list = (
            [u.strip() for u in default_urls.split(",") if u.strip()]
            if isinstance(default_urls, str)
            else list(default_urls)
        )
        conf_count = sum(1 for u in url_list if "confluence" in u.lower() or "atlassian" in u.lower())
        assert conf_count >= 2, (
            f"Default URL list must have at least 2 Confluence entries. "
            f"AC4 requirement (3 SharePoint, 2 Confluence). "
            f"Got {conf_count} Confluence URL(s) in: {url_list}"
        )

    def test_script_help_documents_multi_url_option(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """--help output must document --urls or TARGET_URLS for multi-URL configuration."""
        import subprocess  # noqa: PLC0415
        import sys as _sys  # noqa: PLC0415

        result = subprocess.run(
            [_sys.executable, str(_SPIKE_PATH), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        assert "--urls" in output or "TARGET_URLS" in output, (
            f"--help output must mention '--urls' or 'TARGET_URLS' for multi-URL support. "
            f"AC4 requires users to know how to configure 5+ URLs. Got: {output!r}"
        )
