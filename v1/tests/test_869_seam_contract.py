"""Seam-replacement contract tests for task #869 (retry cycle).

Asserts that specific test methods in test_context_hydration.py and
test_content_safety_integration.py have had their legacy
``patch.dict("sys.modules", {"trafilatura": ...})`` seams replaced with
direct ``patch("owlbear.core.context_hydration.extract_markdown")`` seams.

These are structural (meta) tests: they inspect the source of peer test files
via the AST and FAIL while the legacy seams are still present.  They PASS once
the builder completes the #869 replacement work.

AC coverage:
- AC1 (4 tests): All 4 direct trafilatura mocks in test_context_hydration.py replaced.
- AC2 (5 tests): All 5 fetch_url-related trafilatura mocks in
  test_content_safety_integration.py replaced.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_DIR = pathlib.Path(__file__).parent
_CTX_HYDRATION = _TEST_DIR / "test_context_hydration.py"
_CONTENT_SAFETY = _TEST_DIR / "test_content_safety_integration.py"


def _extract_method_source(source: str, class_name: str, method_name: str) -> str:
    """Return the full source text of *method_name* inside *class_name*.

    Args:
        source: Full text of the Python source file.
        class_name: Name of the class that contains the method.
        method_name: Name of the method to extract.

    Returns:
        The source lines of the method as a single string.

    Raises:
        AssertionError: If the class or method is not found.
    """
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == method_name
                ):
                    start = item.lineno - 1
                    end = item.end_lineno  # 1-based inclusive
                    return "\n".join(lines[start:end])
            msg = f"Method {class_name}.{method_name} not found"
            raise AssertionError(msg)
    msg = f"Class {class_name} not found"
    raise AssertionError(msg)


def _has_sys_modules_trafilatura(method_src: str) -> bool:
    """Return True if the method source contains a sys.modules trafilatura patch.

    Args:
        method_src: Source text of the method under inspection.

    Returns:
        True when ``patch.dict("sys.modules", {"trafilatura": ...})`` is present.
    """
    return 'patch.dict("sys.modules"' in method_src and '"trafilatura"' in method_src


def _has_module_local_extract_markdown(method_src: str) -> bool:
    """Return True if the method patches the module-local extract_markdown seam.

    Checks that ``owlbear.core.context_hydration.extract_markdown`` is patched
    *without* the ``create=True`` flag that was required before #876 added the
    real import.

    Args:
        method_src: Source text of the method under inspection.

    Returns:
        True when the module-local seam is present and create=True is absent.
    """
    return (
        "owlbear.core.context_hydration.extract_markdown" in method_src
        and "create=True" not in method_src
    )


# ---------------------------------------------------------------------------
# AC1 — test_context_hydration.py (4 methods)
# ---------------------------------------------------------------------------


class TestFromAC_ReplacedTrafilaturaSeamContextHydration:
    """AC1: All 4 direct sys.modules trafilatura patches in test_context_hydration.py replaced.

    Each test fails while the legacy ``patch.dict("sys.modules", {"trafilatura": ...})``
    is still present in the named method.  It passes once the builder replaces that
    seam with ``patch("owlbear.core.context_hydration.extract_markdown")``.
    """

    @pytest.fixture(scope="class")
    def source(self) -> str:
        """Return the full source of test_context_hydration.py."""
        return _CTX_HYDRATION.read_text(encoding="utf-8")

    def test_ac1_fetch_url_success_no_sys_modules_trafilatura(self, source: str) -> None:
        """TestFromACFetchUrl::test_successful_fetch_returns_content uses module-local seam.

        Fails while ``patch.dict("sys.modules", {"trafilatura": ...})`` remains in
        that method.  Passes once builder replaces it with the module-local mock.
        """
        method_src = _extract_method_source(
            source,
            "TestFromACFetchUrl",
            "test_successful_fetch_returns_content",
        )
        assert not _has_sys_modules_trafilatura(method_src), (
            "TestFromACFetchUrl::test_successful_fetch_returns_content still uses "
            "patch.dict('sys.modules', {'trafilatura':...}) — replace with "
            "patch('owlbear.core.context_hydration.extract_markdown')  [AC1]"
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromACFetchUrl::test_successful_fetch_returns_content must use "
            "patch('owlbear.core.context_hydration.extract_markdown') without "
            "create=True  [AC1]"
        )

    def test_ac1_fetch_url_checker_allows_no_sys_modules_trafilatura(self, source: str) -> None:
        """TestFromACFetchUrl::test_url_checker_allows_url uses module-local seam.

        Fails while the method still patches sys.modules trafilatura.
        """
        method_src = _extract_method_source(
            source,
            "TestFromACFetchUrl",
            "test_url_checker_allows_url",
        )
        assert not _has_sys_modules_trafilatura(method_src), (
            "TestFromACFetchUrl::test_url_checker_allows_url still patches "
            "sys.modules trafilatura  [AC1]"
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromACFetchUrl::test_url_checker_allows_url must use "
            "module-local extract_markdown mock without create=True  [AC1]"
        )

    def test_ac1_forwarding_html_url_no_sys_modules_trafilatura(self, source: str) -> None:
        """test_forwards_html_body_and_url_to_extract_markdown uses module-local seam.

        Class: TestFromAC_FetchUrlExtractMarkdownForwarding.

        Fails because the method has both sys.modules trafilatura AND
        create=True on the extract_markdown patch.  Passes once both are removed.
        """
        method_src = _extract_method_source(
            source,
            "TestFromAC_FetchUrlExtractMarkdownForwarding",
            "test_forwards_html_body_and_url_to_extract_markdown",
        )
        assert not _has_sys_modules_trafilatura(method_src), (
            "TestFromAC_FetchUrlExtractMarkdownForwarding::"
            "test_forwards_html_body_and_url_to_extract_markdown "
            "still uses sys.modules trafilatura  [AC1]"
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromAC_FetchUrlExtractMarkdownForwarding::"
            "test_forwards_html_body_and_url_to_extract_markdown "
            "must use extract_markdown without create=True  [AC1]"
        )

    def test_ac1_forwarding_result_propagates_no_sys_modules_trafilatura(self, source: str) -> None:
        """test_helper_return_propagates_to_fetch_url_result uses module-local seam.

        Class: TestFromAC_FetchUrlExtractMarkdownForwarding.

        Fails because the method has both sys.modules trafilatura AND
        create=True on the extract_markdown patch.  Passes once both are removed.
        """
        method_src = _extract_method_source(
            source,
            "TestFromAC_FetchUrlExtractMarkdownForwarding",
            "test_helper_return_propagates_to_fetch_url_result",
        )
        assert not _has_sys_modules_trafilatura(method_src), (
            "TestFromAC_FetchUrlExtractMarkdownForwarding::"
            "test_helper_return_propagates_to_fetch_url_result "
            "still uses sys.modules trafilatura  [AC1]"
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromAC_FetchUrlExtractMarkdownForwarding::"
            "test_helper_return_propagates_to_fetch_url_result "
            "must use extract_markdown without create=True  [AC1]"
        )


# ---------------------------------------------------------------------------
# AC2 — test_content_safety_integration.py (5 methods)
# ---------------------------------------------------------------------------


class TestFromAC_ReplacedTrafilaturaSeamContentSafety:
    """AC2: All 5 fetch_url-related sys.modules trafilatura patches replaced.

    Target file: test_content_safety_integration.py.

    Each test fails while the legacy seam is present in the named method and
    passes once the builder replaces it with the module-local extract_markdown patch.
    """

    @pytest.fixture(scope="class")
    def source(self) -> str:
        """Return the full source of test_content_safety_integration.py."""
        return _CONTENT_SAFETY.read_text(encoding="utf-8")

    def test_ac2_wraps_return_value_no_sys_modules_trafilatura(self, source: str) -> None:
        """TestFromACFetchUrlWrapping::test_wraps_return_value uses module-local seam.

        Fails while the method patches sys.modules trafilatura (line ~270).
        """
        method_src = _extract_method_source(
            source,
            "TestFromACFetchUrlWrapping",
            "test_wraps_return_value",
        )
        assert not _has_sys_modules_trafilatura(method_src), (
            "TestFromACFetchUrlWrapping::test_wraps_return_value still uses "
            "sys.modules trafilatura  [AC2]"
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromACFetchUrlWrapping::test_wraps_return_value must use "
            "module-local extract_markdown mock without create=True  [AC2]"
        )

    def test_ac2_wraps_source_url_no_sys_modules_trafilatura(self, source: str) -> None:
        """TestFromACFetchUrlWrapping::test_wraps_with_source_url_attribute uses module-local seam.

        Fails while the method patches sys.modules trafilatura (line ~298).
        """
        method_src = _extract_method_source(
            source,
            "TestFromACFetchUrlWrapping",
            "test_wraps_with_source_url_attribute",
        )
        assert not _has_sys_modules_trafilatura(method_src), (
            "TestFromACFetchUrlWrapping::test_wraps_with_source_url_attribute "
            "still uses sys.modules trafilatura  [AC2]"
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromACFetchUrlWrapping::test_wraps_with_source_url_attribute "
            "must use module-local extract_markdown mock without create=True  [AC2]"
        )

    def test_ac2_skips_wrapping_when_disabled_no_sys_modules_trafilatura(self, source: str) -> None:
        """TestFromACFetchUrlWrapping::test_skips_wrapping_when_disabled uses module-local seam.

        This two-step method has two sys.modules patches (lines ~327, ~336).
        Both must be replaced with the module-local extract_markdown seam.
        """
        method_src = _extract_method_source(
            source,
            "TestFromACFetchUrlWrapping",
            "test_skips_wrapping_when_disabled",
        )
        assert not _has_sys_modules_trafilatura(method_src), (
            "TestFromACFetchUrlWrapping::test_skips_wrapping_when_disabled "
            "still uses sys.modules trafilatura  [AC2]"
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromACFetchUrlWrapping::test_skips_wrapping_when_disabled "
            "must use module-local extract_markdown mock without create=True  [AC2]"
        )

    def test_ac2_bookmark_contrast_has_module_local_for_fetch_url_side(self, source: str) -> None:
        """BookmarkPipelineExcluded contrast test — fetch_url side uses module-local seam.

        Method: test_default_web_read_does_not_wrap_while_fetch_url_does.

        The fetch_url assertion block must use
        ``patch("owlbear.core.context_hydration.extract_markdown")`` without
        ``create=True``.  The bookmark side may still use sys.modules (bookmark_pipeline
        has not yet been migrated); this test checks only that the module-local seam
        is present somewhere in the method, which requires the fetch_url side to use it.

        Fails because the method currently has no extract_markdown patch at all (line ~379).
        """
        method_src = _extract_method_source(
            source,
            "TestFromACBookmarkPipelineExcluded",
            "test_default_web_read_does_not_wrap_while_fetch_url_does",
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromACBookmarkPipelineExcluded::"
            "test_default_web_read_does_not_wrap_while_fetch_url_does "
            "fetch_url side must use patch('owlbear.core.context_hydration.extract_markdown') "
            "without create=True  [AC2]"
        )

    def test_ac2_extract_markdown_seam_no_sys_modules_trafilatura(self, source: str) -> None:
        """test_fetch_url_forwards_to_helper_and_wraps_output uses pure module-local seam.

        Class: TestFromAC_FetchUrlExtractMarkdownSeam.

        Fails because the method currently has BOTH sys.modules trafilatura AND
        ``create=True`` on the extract_markdown patch (line ~449).  Passes once
        the builder removes both legacy elements.
        """
        method_src = _extract_method_source(
            source,
            "TestFromAC_FetchUrlExtractMarkdownSeam",
            "test_fetch_url_forwards_to_helper_and_wraps_output",
        )
        assert not _has_sys_modules_trafilatura(method_src), (
            "TestFromAC_FetchUrlExtractMarkdownSeam::"
            "test_fetch_url_forwards_to_helper_and_wraps_output "
            "still uses sys.modules trafilatura backup  [AC2]"
        )
        assert _has_module_local_extract_markdown(method_src), (
            "TestFromAC_FetchUrlExtractMarkdownSeam::"
            "test_fetch_url_forwards_to_helper_and_wraps_output "
            "must use extract_markdown without create=True  [AC2]"
        )
