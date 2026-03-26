"""Tests for owlbear.web_extract — extract_markdown helper contract.

Focused tests for the package-root leaf helper at the helper boundary.
Does NOT cover downstream caller rewires (content_extractor, bookmark_pipeline,
context_hydration) — those are tracked in #875, #825, and #873.
"""

from __future__ import annotations

import builtins
import contextlib
from unittest.mock import MagicMock, patch

import pytest

from owlbear.web_extract import extract_markdown

# ===========================================================================
# AC2 — Success path: one trafilatura.extract call with correct kwargs
# ===========================================================================


class TestFromAC_ExtractMarkdownSuccess:
    """Success-path cases patch the helper-local trafilatura lookup.

    Asserts one call to trafilatura.extract(html, output_format="markdown",
    include_links=True, url=url) and that the raw markdown string is returned.
    """

    @patch("owlbear.web_extract.trafilatura")
    def test_returns_extracted_markdown(self, mock_traf: MagicMock) -> None:
        """Success path returns the raw markdown string from trafilatura.extract."""
        mock_traf.extract.return_value = "# Hello World"
        result = extract_markdown("<html><body>Hello</body></html>")
        assert result == "# Hello World"

    @patch("owlbear.web_extract.trafilatura")
    def test_calls_trafilatura_with_correct_kwargs(self, mock_traf: MagicMock) -> None:
        """extract_markdown calls trafilatura.extract with output_format, include_links, and url."""
        mock_traf.extract.return_value = "# Content"
        html = "<html><body>Content</body></html>"
        extract_markdown(html)
        mock_traf.extract.assert_called_once_with(
            html,
            output_format="markdown",
            include_links=True,
            url=None,
        )

    @patch("owlbear.web_extract.trafilatura")
    def test_exactly_one_trafilatura_extract_call(self, mock_traf: MagicMock) -> None:
        """extract_markdown makes exactly one call to trafilatura.extract per invocation."""
        mock_traf.extract.return_value = "content"
        extract_markdown("<p>text</p>")
        assert mock_traf.extract.call_count == 1


# ===========================================================================
# AC3 — URL forwarding: default None and explicit URL passed unchanged
# ===========================================================================


class TestFromAC_ExtractMarkdownUrlForwarding:
    """url defaults to None; a provided URL is forwarded to trafilatura.extract unchanged."""

    @patch("owlbear.web_extract.trafilatura")
    def test_default_url_is_none(self, mock_traf: MagicMock) -> None:
        """When url is omitted, trafilatura.extract receives url=None."""
        mock_traf.extract.return_value = "content"
        extract_markdown("<p>x</p>")
        mock_traf.extract.assert_called_once_with(
            "<p>x</p>",
            output_format="markdown",
            include_links=True,
            url=None,
        )

    @patch("owlbear.web_extract.trafilatura")
    def test_provided_url_forwarded_unchanged(self, mock_traf: MagicMock) -> None:
        """A provided URL is forwarded to trafilatura.extract unchanged."""
        url = "https://example.com/article"
        mock_traf.extract.return_value = "content"
        extract_markdown("<p>x</p>", url=url)
        mock_traf.extract.assert_called_once_with(
            "<p>x</p>",
            output_format="markdown",
            include_links=True,
            url=url,
        )

    @patch("owlbear.web_extract.trafilatura")
    def test_url_forwarding_does_not_affect_return_value(self, mock_traf: MagicMock) -> None:
        """Providing a URL does not alter the returned markdown string."""
        mock_traf.extract.return_value = "# Article"
        result = extract_markdown("<p>x</p>", url="https://example.com")
        assert result == "# Article"


# ===========================================================================
# AC4 — Fallback: None or raised exception → empty string, no re-raise
# ===========================================================================


class TestFromAC_ExtractMarkdownFallback:
    """None and raised-exception fallbacks return '' without surfacing the error."""

    @patch("owlbear.web_extract.trafilatura")
    def test_returns_empty_string_when_extract_returns_none(self, mock_traf: MagicMock) -> None:
        """extract_markdown returns '' when trafilatura.extract returns None."""
        mock_traf.extract.return_value = None
        result = extract_markdown("<html></html>")
        assert result == ""

    @patch("owlbear.web_extract.trafilatura")
    def test_returns_empty_string_when_extract_raises(self, mock_traf: MagicMock) -> None:
        """extract_markdown returns '' when trafilatura.extract raises an exception."""
        mock_traf.extract.side_effect = RuntimeError("trafilatura crash")
        result = extract_markdown("<html></html>")
        assert result == ""

    @patch("owlbear.web_extract.trafilatura")
    def test_does_not_surface_extraction_exception(self, mock_traf: MagicMock) -> None:
        """extract_markdown never re-raises an exception from trafilatura.extract."""
        mock_traf.extract.side_effect = ValueError("unexpected parse error")
        try:
            result = extract_markdown("<html></html>")
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"extract_markdown raised unexpectedly: {exc}")
        assert isinstance(result, str)

    @patch("owlbear.web_extract.trafilatura")
    def test_empty_string_not_none_on_none_extract(self, mock_traf: MagicMock) -> None:
        """Return type is str, never None, when extraction returns None."""
        mock_traf.extract.return_value = None
        result = extract_markdown("<html><body>text</body></html>")
        assert result is not None
        assert isinstance(result, str)


# ===========================================================================
# AC5 — Missing dependency: narrow import-denial seam → actionable ImportError
# ===========================================================================


class TestFromAC_ExtractMarkdownMissingDependency:
    """Narrow import-denial seam at the helper boundary asserts actionable ImportError."""

    def test_raises_import_error_when_trafilatura_missing(self) -> None:
        """extract_markdown raises ImportError when trafilatura is not installed."""
        _real_import = builtins.__import__

        def _deny_trafilatura(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return _real_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=_deny_trafilatura),
            pytest.raises(ImportError),
        ):
            extract_markdown("<html></html>")

    def test_import_error_contains_owlbear_search_install_hint(self) -> None:
        """ImportError message contains the 'owlbear[search]' install hint."""
        _real_import = builtins.__import__

        def _deny_trafilatura(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return _real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_deny_trafilatura):
            with pytest.raises(ImportError) as exc_info:
                extract_markdown("<html></html>")
            assert "owlbear[search]" in str(exc_info.value)

    def test_import_error_message_references_uv(self) -> None:
        """ImportError message references 'uv' so the user knows what command to run."""
        _real_import = builtins.__import__

        def _deny_trafilatura(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return _real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_deny_trafilatura):
            with pytest.raises(ImportError) as exc_info:
                extract_markdown("<html></html>")
            assert "uv" in str(exc_info.value).lower()


# ===========================================================================
# AC2 — Lazy-import timing: trafilatura must not be imported at module load
# ===========================================================================


class TestFromAC_ExtractMarkdownLazyImport:
    """AC2 — trafilatura must be lazy-imported on first extract_markdown call, not at module load.

    Uses importlib.reload() to force full module code re-execution and
    builtins.__import__ tracking (combined with sys.modules removal to defeat
    the sys.modules cache hit that would otherwise suppress the __import__ call
    when trafilatura is already loaded).
    """

    def test_module_load_does_not_call_import_for_trafilatura(self) -> None:
        """Re-executing owlbear.web_extract module code must not call __import__ for trafilatura.

        The test forces a fresh module execution via importlib.reload() with
        trafilatura absent from sys.modules, then asserts that no trafilatura
        __import__ call occurred during that re-execution.  The current
        implementation has an eager ``try: import trafilatura`` at module scope
        (lines 9-12 of web_extract.py) so this test is expected to fail RED
        until the implementation is corrected.
        """
        import importlib
        import sys

        import owlbear.web_extract as we_mod

        traf_calls: list[str] = []
        _orig = builtins.__import__

        def _tracker(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                traf_calls.append(name)
            return _orig(name, *args, **kwargs)

        # Remove trafilatura from sys.modules so any module-level `import trafilatura`
        # cannot resolve via the cache and must call builtins.__import__.
        saved_traf = sys.modules.pop("trafilatura", None)
        try:
            with patch("builtins.__import__", side_effect=_tracker):
                importlib.reload(we_mod)

            assert traf_calls == [], (
                "owlbear.web_extract module code called __import__('trafilatura') at load time. "
                "AC2 requires trafilatura to be lazy-imported only when extract_markdown is "
                f"called.  Recorded import attempts: {traf_calls}"
            )
        finally:
            if saved_traf is not None:
                sys.modules["trafilatura"] = saved_traf
            # Restore the module-level trafilatura attribute to a consistent state.
            we_mod.trafilatura = saved_traf  # type: ignore[assignment]

    def test_first_trafilatura_import_attempt_is_inside_extract_markdown(self) -> None:
        """After a clean module load, the first __import__('trafilatura') call
        is in extract_markdown.

        Verifies the two-phase lazy contract described in AC2:
          Phase 1 — module reload: zero trafilatura import attempts.
          Phase 2 — extract_markdown call: at least one trafilatura import attempt.

        Phase 1 is expected to fail RED against the current implementation.
        """
        import importlib
        import sys

        import owlbear.web_extract as we_mod

        traf_calls_load: list[str] = []
        traf_calls_call: list[str] = []
        _orig = builtins.__import__

        def _tracker_load(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                traf_calls_load.append(name)
            return _orig(name, *args, **kwargs)

        def _tracker_call(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                traf_calls_call.append(name)
            return _orig(name, *args, **kwargs)

        saved_traf = sys.modules.pop("trafilatura", None)
        try:
            # Phase 1: reload module — expect NO trafilatura import.
            with patch("builtins.__import__", side_effect=_tracker_load):
                importlib.reload(we_mod)

            assert traf_calls_load == [], (
                "Module load imported trafilatura eagerly — lazy import contract violated. "
                f"Recorded: {traf_calls_load}"
            )

            # Phase 2: first extract_markdown call — expect trafilatura import attempt.
            with (
                patch("builtins.__import__", side_effect=_tracker_call),
                contextlib.suppress(ImportError),
            ):
                we_mod.extract_markdown("<html><body>test</body></html>")

            assert traf_calls_call != [], (
                "extract_markdown did not call __import__('trafilatura'). "
                "AC2 requires the first trafilatura import attempt to occur on the first "
                "extract_markdown call, not at module load time."
            )
        finally:
            if saved_traf is not None:
                sys.modules["trafilatura"] = saved_traf
            we_mod.trafilatura = saved_traf  # type: ignore[assignment]


# ===========================================================================
# AC1 — Import boundary: web_extract is a leaf module with no higher-layer imports
# ===========================================================================


class TestFromAC_ImportBoundary:
    """AC1 — web_extract.py must never import from owlbear higher-layer packages.

    Static regression guard: if a forbidden import is added to web_extract.py
    this test fails immediately, protecting the leaf-module contract.
    """

    def test_web_extract_has_no_forbidden_owlbear_layer_imports(self) -> None:
        """web_extract.py must not import owlbear.core, .tools, .memory, .agents, or .config."""
        import ast
        from pathlib import Path

        source_path = Path(__file__).parent.parent / "src" / "owlbear" / "web_extract.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))

        forbidden_prefixes = (
            "owlbear.core",
            "owlbear.tools",
            "owlbear.memory",
            "owlbear.agents",
            "owlbear.config",
        )
        nodes = list(ast.walk(tree))
        violations: list[str] = [
            f"from {node.module} import ..."
            for node in nodes
            if isinstance(node, ast.ImportFrom)
            and node.module
            and any(
                node.module == prefix or node.module.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            )
        ]
        violations += [
            f"import {alias.name}"
            for node in nodes
            if isinstance(node, ast.Import)
            for alias in node.names
            if any(
                alias.name == prefix or alias.name.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            )
        ]

        assert violations == [], (
            f"web_extract.py has forbidden higher-layer imports: {violations}. "
            "AC1 requires web_extract to be a leaf module with no owlbear internal imports."
        )
