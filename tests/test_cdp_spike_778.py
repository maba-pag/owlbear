"""Failing tests for task #778: Add hash stability validation protocol to CDP spike.

Covers all 4 AC items:
  AC1:  Hash stability protocol present in spike — --hash-stability argparse flag
        and _run_hash_stability() helper function
  AC2:  Protocol tests at least 2 pages x 3 extractions x 60s intervals
  AC3:  Results compared at raw HTML and cleaned-content levels
  AC4:  Go/no-go determination includes hash stability verdict

Strategy:
- importlib tests for _run_hash_stability helper and --hash-stability argparse flag.
- trafilatura stubbed via patch.dict(sys.modules) + pytest fixture (handles both
  top-level and inline ``import trafilatura`` patterns).
- playwright stubbed so spike can be loaded without browser driver installed.
- time.sleep patched to avoid actual 60-second waits in CI.

All tests fail on current HEAD (cdp-spike.py has no _run_hash_stability function
and no --hash-stability argparse flag).
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
_URL_A = "https://contoso.sharepoint.com/sites/team"
_URL_B = "https://contoso.confluence.atlassian.net/wiki/spaces/PROJ"
_SAMPLE_HTML_A = "<html><body><h1>Team Site</h1><p>Important content.</p><footer>Copyright 2026</footer></body></html>"
_SAMPLE_HTML_B = "<html><body><h1>Confluence Space</h1><p>Project docs.</p><footer>Atlassian</footer></body></html>"
_CLEANED_TEXT_A = "# Team Site\n\nImportant content."
_CLEANED_TEXT_B = "# Confluence Space\n\nProject docs."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trafilatura_stub(*, return_value: str | None = _CLEANED_TEXT_A) -> MagicMock:
    stub = MagicMock()
    stub.extract = MagicMock(return_value=return_value)
    return stub


@pytest.fixture()
def trafilatura_stub() -> Iterator[MagicMock]:
    """Inject trafilatura stub into sys.modules for the duration of the test.

    Ensures both module-level and inline ``import trafilatura`` see the stub.
    """
    stub = _make_trafilatura_stub()
    with patch.dict(sys.modules, {"trafilatura": stub}):
        yield stub


def _load_spike() -> Any:  # noqa: ANN401
    """Import cdp-spike.py fresh with playwright stubs pre-injected.

    Callers that need trafilatura stubbed must activate the trafilatura_stub
    fixture before calling this function.
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


def _make_mock_page(html: str = _SAMPLE_HTML_A) -> MagicMock:
    page = MagicMock()
    page.url = _URL_A
    page.inner_text = MagicMock(return_value="Body text " * 20)
    page.content = MagicMock(return_value=html)
    page.query_selector = MagicMock(return_value=None)
    page.goto = MagicMock()
    return page


def _get_stability_fn(spike: Any) -> Any:  # noqa: ANN401
    """Locate the hash stability helper in the spike module."""
    return getattr(spike, "_run_hash_stability", None) or getattr(spike, "run_hash_stability", None)


# ---------------------------------------------------------------------------
# TestFromAC_HashStabilityProtocol  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_HashStabilityProtocol:
    """AC1: Hash stability protocol present in spike as --hash-stability flag + helper."""

    def test_hash_stability_flag_accepted_by_argparse(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """argparse must accept --hash-stability flag without raising SystemExit."""
        spike = _load_spike()
        assert hasattr(spike, "_parse_args"), (
            "Spike must expose _parse_args(). AC1 requires --hash-stability flag added to the argparse configuration."
        )
        try:
            args = spike._parse_args(["--hash-stability"])
        except SystemExit as exc:
            pytest.fail(
                f"_parse_args(['--hash-stability']) raised SystemExit({exc.code}). "
                "AC1 requires --hash-stability to be a valid CLI flag."
            )
        assert hasattr(args, "hash_stability") or hasattr(args, "hash-stability"), (
            "--hash-stability must be stored in the argparse Namespace. "
            "Builder guidance: add `parser.add_argument('--hash-stability', action='store_true')`."
        )

    def test_hash_stability_flag_defaults_to_false(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """--hash-stability must default to False/None (opt-in, not enabled by default)."""
        spike = _load_spike()
        args = spike._parse_args([])
        flag_val = getattr(args, "hash_stability", getattr(args, "hash-stability", _CLEANED_TEXT_A))
        assert flag_val is False or flag_val is None, (
            f"--hash-stability defaults to {flag_val!r}, expected False or None. "
            "Builder guidance: 'opt-in, minimal' — flag must be off unless explicitly provided."
        )

    def test_run_hash_stability_function_exists(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Script must expose _run_hash_stability() or run_hash_stability() callable."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), (
            "Script must expose '_run_hash_stability()' or 'run_hash_stability()'. "
            "AC1 + builder guidance §2: this is the implementation anchor for hash stability."
        )


# ---------------------------------------------------------------------------
# TestFromAC_ExtractionProtocol  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_ExtractionProtocol:
    """AC2: Protocol tests at least 2 pages x 3 extractions x 60s intervals."""

    def test_page_content_called_3_times_per_url(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Must call page.content() at least 3 times per URL (3 extractions per AC2)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        page = _make_mock_page()
        with patch("time.sleep"):
            fn(page, [_URL_A])

        assert page.content.call_count >= 3, (
            f"page.content() called {page.content.call_count} time(s) for a single URL. "
            "AC2 requires 3 extractions per page — must call page.content() at least 3 times."
        )

    def test_sleep_between_extractions_at_least_60_seconds(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Must sleep ≥60 seconds between consecutive extractions (AC2: 60s intervals)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        page = _make_mock_page()
        with patch("time.sleep") as mock_sleep:
            fn(page, [_URL_A])

        sleep_calls = mock_sleep.call_args_list
        assert len(sleep_calls) >= 2, (
            f"time.sleep() was called {len(sleep_calls)} time(s). "
            "AC2 requires 3 extractions x 60s apart -- needs at least 2 sleep calls of >=60s each."
        )
        for c in sleep_calls:
            seconds = c.args[0] if c.args else next(iter(c.kwargs.values()))
            assert seconds >= 60, (
                f"time.sleep({seconds}) — interval must be ≥ 60 seconds. "
                "AC2 specifies 60s between extractions for meaningful hash stability measurement."
            )

    def test_accepts_list_of_multiple_urls(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """Function must accept a list of URLs and not raise on 2-URL input (AC2: ≥2 pages)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        page = _make_mock_page()
        try:
            with patch("time.sleep"):
                fn(page, [_URL_A, _URL_B])
        except (TypeError, AttributeError) as exc:
            pytest.fail(
                f"_run_hash_stability raised {type(exc).__name__} with 2 URLs: {exc}. "
                "AC2 requires testing at least 2 target pages."
            )

    def test_extracts_all_urls_not_just_first(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
    ) -> None:
        """All URLs in the list must be processed — function must not stop after the first URL."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        page = _make_mock_page()
        with patch("time.sleep"):
            fn(page, [_URL_A, _URL_B])

        # 3 extractions x 2 URLs = >=6 total page.content() calls
        assert page.content.call_count >= 6, (
            f"page.content() called {page.content.call_count} time(s) for 2 URLs. "
            "AC2 requires 3 extractions per page -- for 2 URLs that means >=6 total content() calls."
        )


# ---------------------------------------------------------------------------
# TestFromAC_HashComparison  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_HashComparison:
    """AC3: Results compared at raw HTML and cleaned-content levels."""

    def test_trafilatura_called_per_extraction_for_cleaned_hash(
        self,
        trafilatura_stub: MagicMock,
    ) -> None:
        """Must call trafilatura.extract() ≥3 times per URL to produce cleaned hashes."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        page = _make_mock_page()
        with patch("time.sleep"):
            fn(page, [_URL_A])

        assert trafilatura_stub.extract.call_count >= 3, (
            f"trafilatura.extract() called {trafilatura_stub.extract.call_count} times for 1 URL. "
            "AC3 requires cleaned content to be hashed — must call extract() at least 3 times "
            "(once per extraction per URL)."
        )

    def test_logs_raw_html_hash_information(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Must log raw HTML hash information per URL (AC3: 'document the delta' for raw HTML)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        page = _make_mock_page()
        with patch("time.sleep"):
            fn(page, [_URL_A])

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert any(kw in output.lower() for kw in ("raw", "html", "hash")), (
            "Log output must reference raw HTML hashing. "
            "AC3 requires documenting the delta between raw HTML hashes across extractions."
        )

    def test_logs_cleaned_content_hash_information(
        self,
        trafilatura_stub: MagicMock,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Must log cleaned content hash information per URL (AC3: cleaned hashes must match)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        page = _make_mock_page()
        with patch("time.sleep"):
            fn(page, [_URL_A])

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert any(kw in output.lower() for kw in ("clean", "trafilatura", "hash")), (
            "Log output must reference cleaned content hash comparison. "
            "AC3: cleaned hash stability is the go/no-go signal — it must appear in the log."
        )

    def test_logs_diff_output_when_cleaned_hashes_differ(
        self,
        trafilatura_stub: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When cleaned hashes differ, must log diff information (builder guidance §5)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        # Return different cleaned text on every call → hashes always differ → difflib triggered
        call_count: list[int] = [0]

        def unstable_extract(*args: Any, **kwargs: Any) -> str:  # noqa: ARG001
            call_count[0] += 1
            return f"{_CLEANED_TEXT_A}\n\nDynamic timestamp: {call_count[0]}"

        trafilatura_stub.extract = MagicMock(side_effect=unstable_extract)
        page = _make_mock_page()

        with patch("time.sleep"):
            fn(page, [_URL_A])

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert any(kw in output.lower() for kw in ("diff", "differ", "mismatch", "unstable", "change")), (
            "When cleaned hashes differ, must log diff or mismatch information. "
            "Builder guidance §5: use difflib.unified_diff on cleaned text when hashes differ."
        )


# ---------------------------------------------------------------------------
# TestFromAC_GoNoGoVerdict  (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_GoNoGoVerdict:
    """AC4: Go/no-go determination includes hash stability verdict."""

    def test_logs_go_verdict_when_all_cleaned_hashes_stable(
        self,
        trafilatura_stub: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Must log GO or STABLE verdict when all cleaned hashes match (happy path)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        trafilatura_stub.extract = MagicMock(return_value=_CLEANED_TEXT_A)
        page = _make_mock_page()

        with patch("time.sleep"):
            fn(page, [_URL_A])

        captured = capsys.readouterr()
        output = (captured.out + captured.err).upper()
        assert "GO" in output or "STABLE" in output or "PASS" in output, (
            f"Output does not contain GO/STABLE/PASS when hashes are stable: {output[:300]!r}. "
            "AC4 requires the hash stability verdict to be logged."
        )

    def test_logs_nogo_verdict_when_cleaned_hashes_unstable(
        self,
        trafilatura_stub: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Must log NO-GO or FAIL verdict when cleaned hashes differ across extractions."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        call_count: list[int] = [0]

        def unstable_extract(*args: Any, **kwargs: Any) -> str:  # noqa: ARG001
            call_count[0] += 1
            return f"{_CLEANED_TEXT_A}\n\nParagraph count: {call_count[0]}"

        trafilatura_stub.extract = MagicMock(side_effect=unstable_extract)
        page = _make_mock_page()

        with patch("time.sleep"):
            fn(page, [_URL_A])

        captured = capsys.readouterr()
        output = (captured.out + captured.err).upper()
        assert "NO-GO" in output or "NOGO" in output or "UNSTABLE" in output or "FAIL" in output, (
            f"Output does not contain NO-GO/FAIL/UNSTABLE when hashes are unstable: "
            f"{output[:300]!r}. "
            "AC4: when cleaned hashes are unstable the log must contain a NO-GO signal."
        )

    def test_none_from_trafilatura_does_not_raise(
        self,
        trafilatura_stub: MagicMock,
    ) -> None:
        """When trafilatura.extract() returns None, must not raise TypeError (builder guidance §4)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        trafilatura_stub.extract = MagicMock(return_value=None)
        page = _make_mock_page()

        try:
            with patch("time.sleep"):
                fn(page, [_URL_A])
        except TypeError as exc:
            pytest.fail(
                f"_run_hash_stability raised TypeError when trafilatura.extract returned None: {exc}. "
                "Builder guidance §4: guard against None before sha256(cleaned.encode())."
            )
        except Exception as exc:  # noqa: BLE001
            pytest.fail(
                f"_run_hash_stability raised {type(exc).__name__} when trafilatura returned None: "
                f"{exc}. Must handle None gracefully."
            )

    def test_none_from_trafilatura_marks_url_as_fail_in_log(
        self,
        trafilatura_stub: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When trafilatura returns None, URL result must be logged as FAIL (builder guidance §4)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        trafilatura_stub.extract = MagicMock(return_value=None)
        page = _make_mock_page()

        with patch("time.sleep"):
            fn(page, [_URL_A])

        captured = capsys.readouterr()
        output = (captured.out + captured.err).upper()
        assert "FAIL" in output or "NO-GO" in output or "NONE" in output or "WARN" in output or "ERROR" in output, (
            f"Output does not indicate failure when trafilatura returned None: {output[:300]!r}. "
            "Builder guidance §4: 'log and mark as FAIL if extraction returns None'."
        )

    def test_overall_verdict_logged_across_multiple_urls(
        self,
        trafilatura_stub: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Must log an overall verdict across all URLs (AC4: overall go/no-go, not per-URL only)."""
        spike = _load_spike()
        fn = _get_stability_fn(spike)
        assert callable(fn), "Script must expose _run_hash_stability()."

        trafilatura_stub.extract = MagicMock(return_value=_CLEANED_TEXT_A)
        page = _make_mock_page()

        with patch("time.sleep"):
            fn(page, [_URL_A, _URL_B])

        captured = capsys.readouterr()
        output = (captured.out + captured.err).upper()
        assert "GO" in output or "STABLE" in output or "PASS" in output or "OVERALL" in output, (
            f"No overall verdict found for 2-URL run: {output[:400]!r}. "
            "AC4: go/no-go determination must cover all tested URLs collectively."
        )
