"""Tests for owlbear.tools cached lazy export implementation (task #879).

These tests verify the lazy-loading behavior introduced by #879:
  - Module-level __getattr__ exists (PEP 562, AC 3)
  - Bare import does not eagerly load any tool submodule (AC 6)
  - Exported names are absent from module vars before first access (AC 4)
  - __getattr__ raises AttributeError for unsupported names (AC 5)
  - No custom __dir__ or new runtime dependency added (AC 8)
"""

from __future__ import annotations

import contextlib
import subprocess
import sys

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXPECTED_NAMES: tuple[str, ...] = (
    "AskUserToolset",
    "FileToolset",
    "GitHubToolset",
    "GitLocalToolset",
    "HookedToolset",
    "KanbanToolset",
    "MCPServerRegistry",
    "TerminalToolset",
    "find_toolset",
    "unwrap",
)

_TOOL_SUBMODULES: tuple[str, ...] = (
    "owlbear.tools.ask_user",
    "owlbear.tools.filesystem",
    "owlbear.tools.git_local",
    "owlbear.tools.github_api",
    "owlbear.tools.hooked",
    "owlbear.tools.kanban",
    "owlbear.tools.mcp_registry",
    "owlbear.tools.protocols",
    "owlbear.tools.terminal",
)


# ---------------------------------------------------------------------------
# AC 3: Module-level __getattr__ in the repo's cached importlib style
# ---------------------------------------------------------------------------


class TestFromAC_LazyExportMechanism:
    """AC 3: Replace eager top-level imports with lazy import map + __getattr__."""

    def test_module_has_module_level_getattr(self) -> None:
        """owlbear.tools must expose __getattr__ in its module __dict__ (PEP 562)."""
        import owlbear.tools

        # PEP 562 module __getattr__ is a plain function in the module's __dict__.
        # The current eager-import module has no __getattr__; this FAILS until #879
        # adds def __getattr__(name) at module level.
        assert "__getattr__" in owlbear.tools.__dict__, (
            "owlbear.tools does not define a module-level __getattr__; "
            "eager imports must first be replaced with the lazy __getattr__ pattern"
        )

    def test_module_getattr_is_callable(self) -> None:
        """__getattr__ must be a callable (plain function, not a descriptor)."""
        import owlbear.tools

        ga = owlbear.tools.__dict__.get("__getattr__")
        assert ga is not None, "__getattr__ not in owlbear.tools.__dict__"
        assert callable(ga), "__getattr__ must be callable"

    def test_lazy_import_map_covers_all_public_names(self) -> None:
        """Every name in __all__ must have a lazy route via __getattr__.

        After the implementation, accessing each public name must succeed
        without requiring eager submodule loading at import time.  This test
        verifies the contract by calling __getattr__ directly for each name.
        """
        import owlbear.tools

        ga = owlbear.tools.__dict__.get("__getattr__")
        assert ga is not None, "__getattr__ not defined (lazy map incomplete)"
        for name in _EXPECTED_NAMES:
            result = ga(name)
            assert result is not None, f"__getattr__({name!r}) returned None"


# ---------------------------------------------------------------------------
# AC 4: Caching — resolved objects cached in module globals
# ---------------------------------------------------------------------------


class TestFromAC_LazyExportCaching:
    """AC 4: First access resolves, subsequent lookups bypass __getattr__ (globals cache)."""

    def test_exported_names_absent_from_module_vars_before_first_access(self) -> None:
        """Before any attribute access, exported names must NOT be in module __dict__.

        The current eager-import __init__.py sets all 10 names at import time,
        so this subprocess assertion fails until #879 removes the eager imports.
        """
        # Build assertion string for all 10 names
        assertions = "; ".join(
            f"assert {n!r} not in vars(mod), {n!r} + ' eagerly loaded into module vars'"
            for n in _EXPECTED_NAMES
        )
        script = (
            "import sys; import owlbear.tools; mod = sys.modules['owlbear.tools']; " + assertions
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Exported names present in vars before first access (eager loading detected):\n"
            f"{result.stderr}"
        )

    def test_attribute_present_in_module_vars_after_first_access(self) -> None:
        """After first access the attribute must be cached; before access it must be absent.

        Combined pre/post assertion so the subprocess fails NOW (eager impl puts
        GitHubToolset in vars immediately at import time, breaking the pre-check).
        """
        script = (
            "import sys; import owlbear.tools; "
            "mod = sys.modules['owlbear.tools']; "
            # Pre-access: must NOT be in vars yet (FAILS with eager loading)
            "assert 'GitHubToolset' not in vars(mod), "
            "'GitHubToolset in vars before first access (eager loading detected)'; "
            "_ = owlbear.tools.GitHubToolset; "
            # Post-access: must be cached in vars
            "assert 'GitHubToolset' in vars(mod), "
            "'GitHubToolset not cached in module globals after first access'"
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Caching pre+post-access check failed:\n{result.stderr}"

    def test_second_access_returns_same_cached_object(self) -> None:
        """Repeated getattr returns the identical object AND __getattr__ must be defined.

        Anchored to __getattr__ presence so the test fails NOW (no lazy impl yet).
        """
        import owlbear.tools

        # Anchor: __getattr__ must be defined (FAILS NOW)
        assert "__getattr__" in owlbear.tools.__dict__, (
            "__getattr__ not defined — lazy caching cannot be verified"
        )
        first = owlbear.tools.GitHubToolset
        second = owlbear.tools.GitHubToolset
        assert first is second, "Each getattr call must return the same cached object"

    def test_cached_access_does_not_call_getattr_again(self) -> None:
        """After caching, __getattr__ must NOT be invoked on a second lookup.

        Uses a subprocess to guarantee a clean module state:
          1. Import owlbear.tools (no eager side-effects)
          2. Access an attribute once (lazy load + cache)
          3. Patch __getattr__ to a crash sentinel
          4. Access the same attribute again — must use cached value, not sentinel

        FAILS NOW because owlbear.tools has no __getattr__ to patch, which means
        step 3 quietly creates a new attribute that Python ignores and the subsequent
        attribute access goes through the normal (eager) __dict__ path — the test body
        in the subprocess catches this missing-__getattr__ scenario itself.
        """
        script = """
import sys
import owlbear.tools

# Confirm __getattr__ is defined (fails in subprocess if not)
assert '__getattr__' in owlbear.tools.__dict__, '__getattr__ not defined in owlbear.tools'

# First access — triggers lazy load and caches in globals
_ = owlbear.tools.AskUserToolset

# Replace __getattr__ with a fatal sentinel; second lookup must bypass it
def _crash(name):
    raise AssertionError(f"__getattr__ called again for {name!r} — caching not working")

owlbear.tools.__getattr__ = _crash  # type: ignore[assignment]

# Second access must come from globals cache, not __getattr__
_ = sys.modules['owlbear.tools'].AskUserToolset
"""
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Caching sentinel check failed (getattr called on second lookup):\n{result.stderr}"
        )


# ---------------------------------------------------------------------------
# AC 5 + AC 6: No eager submodule loading, proper AttributeError for bad names
# ---------------------------------------------------------------------------


class TestFromAC_NoEagerSubmoduleLoading:
    """AC 6: All tool submodules absent from sys.modules after bare import owlbear.tools."""

    def test_all_tool_submodules_absent_after_bare_import(self) -> None:
        """None of the 9 tool submodule paths may appear in sys.modules after bare import."""
        assertions = "; ".join(
            f"assert {m!r} not in sys.modules, {m!r} + ' eagerly loaded'" for m in _TOOL_SUBMODULES
        )
        script = f"import sys; import owlbear.tools; {assertions}"
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Tool submodule(s) eagerly loaded by bare 'import owlbear.tools':\n{result.stderr}"
        )

    def test_github_api_submodule_loaded_after_github_toolset_access(self) -> None:
        """github_api absent before GitHubToolset access, present after.

        Combined pre/post assertion; the pre-check fails NOW because eager loading
        puts owlbear.tools.github_api in sys.modules at bare import time.
        """
        script = (
            "import sys; import owlbear.tools; "
            # Pre-access: github_api must NOT be loaded yet (FAILS with eager loading)
            "assert 'owlbear.tools.github_api' not in sys.modules, "
            "'owlbear.tools.github_api loaded before GitHubToolset access (eager)'; "
            "_ = owlbear.tools.GitHubToolset; "
            # Post-access: github_api must now be in sys.modules
            "assert 'owlbear.tools.github_api' in sys.modules, "
            "'owlbear.tools.github_api not loaded after GitHubToolset access'"
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"github_api pre+post access check failed:\n{result.stderr}"

    def test_core_retry_absent_after_bare_import(self) -> None:
        """owlbear.core.retry must not be loaded transitively by bare import owlbear.tools."""
        script = (
            "import sys; import owlbear.tools; "
            "assert 'owlbear.core.retry' not in sys.modules, "
            "'owlbear.core.retry eagerly loaded by bare import'"
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"owlbear.core.retry eagerly loaded by bare 'import owlbear.tools':\n{result.stderr}"
        )


# ---------------------------------------------------------------------------
# AC 5: AttributeError for unsupported names (no sentinel, no API widening)
# ---------------------------------------------------------------------------


class TestFromAC_UnsupportedAttributeError:
    """AC 5: __getattr__ must raise AttributeError for names not in the lazy map."""

    def test_getattr_raises_attribute_error_for_unknown_names(self) -> None:
        """Calling __getattr__ directly with an unsupported name must raise AttributeError.

        Verifies both that __getattr__ exists (FAILS NOW — not defined yet) and
        that it raises AttributeError rather than returning None/sentinel.
        """
        import owlbear.tools

        ga = owlbear.tools.__dict__.get("__getattr__")
        assert ga is not None, "__getattr__ not defined in owlbear.tools"

        with pytest.raises(AttributeError):
            ga("ThisNameWillNeverBeInThePublicAPI")

    def test_unknown_attribute_not_added_to_module_namespace(self) -> None:
        """A failed __getattr__ call must not pollute the module namespace."""
        import owlbear.tools

        ga = owlbear.tools.__dict__.get("__getattr__")
        assert ga is not None, "__getattr__ not defined"

        probe = "UnknownNameProbe12345"
        with contextlib.suppress(AttributeError):
            ga(probe)

        assert probe not in vars(owlbear.tools), (
            f"{probe!r} was added to module namespace on failed __getattr__ call"
        )

    def test_attribute_error_message_names_the_module(self) -> None:
        """AttributeError from __getattr__ must identify owlbear.tools in the message."""
        import owlbear.tools

        ga = owlbear.tools.__dict__.get("__getattr__")
        assert ga is not None, "__getattr__ not defined"

        with pytest.raises(AttributeError, match=r"owlbear\.tools"):
            ga("CompletelyBogusSymbol")


# ---------------------------------------------------------------------------
# AC 8: No __dir__ override, no lazy_loader or unexpected runtime dependency
# ---------------------------------------------------------------------------


class TestFromAC_NoNewDependencies:
    """AC 8: __dir__ and lazy_loader must remain absent from the module."""

    def test_tools_module_has_custom_dir_for_parity(self) -> None:
        """owlbear.tools must define a custom __dir__ for dir() parity.

        This test FAILS on the current tree because owlbear.tools has no __dir__.
        The builder must add ``def __dir__() -> list[str]: return list(__all__)``
        to tools/__init__.py (task #883).
        """
        import owlbear.tools

        assert "__dir__" in owlbear.tools.__dict__, (
            "owlbear.tools does not define a custom __dir__; "
            "dir(owlbear.tools) will not expose the curated public names until "
            "#883 adds __dir__"
        )

    def test_lazy_loader_package_not_imported_by_tools(self) -> None:
        """The lazy_loader PyPI package must not appear in sys.modules after import.

        Currently PASSES (lazy_loader not used); anchored to __getattr__ presence
        so the whole class fails until the lazy implementation lands.
        """
        import owlbear.tools

        # Anchor: __getattr__ must be present to confirm lazy impl is in place
        assert "__getattr__" in owlbear.tools.__dict__, (
            "__getattr__ not defined — lazy_loader guard has no implementation to verify"
        )
        assert "lazy_loader" not in sys.modules, (
            "lazy_loader found in sys.modules — new dependency forbidden by AC 8"
        )


# ---------------------------------------------------------------------------
# AC dir()-parity: dir(owlbear.tools) exposes exactly the 10 curated names
# ---------------------------------------------------------------------------


class TestFromAC_DirParity:
    """dir(owlbear.tools) must expose the 10 curated public names without eager loading.

    These tests FAIL on the current tree because owlbear.tools has no __dir__,
    so dir() returns only module globals which contain none of the 10 curated
    public symbols before they are accessed.
    """

    def test_dir_exposes_all_curated_names_subprocess(self) -> None:
        """dir(owlbear.tools) must include all 10 supported public names.

        Uses a clean subprocess so no prior attribute accesses pollute the check.
        Verifies the positive parity contract: every name from __all__ appears in
        dir() after a bare import, without triggering heavy submodule loads.
        FAILS on the current tree because __dir__ is absent and dir() returns no
        curated names.
        """
        expected = sorted(
            [
                "AskUserToolset",
                "FileToolset",
                "GitHubToolset",
                "GitLocalToolset",
                "HookedToolset",
                "KanbanToolset",
                "MCPServerRegistry",
                "TerminalToolset",
                "find_toolset",
                "unwrap",
            ]
        )
        expected_repr = repr(expected)
        script = (
            "import sys, owlbear.tools; "
            f"expected = {expected_repr}; "
            "d = dir(owlbear.tools); "
            "missing = [n for n in expected if n not in d]; "
            "assert not missing, "
            "f'dir(owlbear.tools) is missing curated names: {missing}'; "
            "assert 'owlbear.tools.github_api' not in sys.modules, "
            "'dir(owlbear.tools) loaded owlbear.tools.github_api (eager import detected)'; "
            "assert 'owlbear.core.retry' not in sys.modules, "
            "'dir(owlbear.tools) loaded owlbear.core.retry (eager import detected)'"
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"dir() parity + lazy-load check failed:\n{result.stderr}"


# ---------------------------------------------------------------------------
# AC 3 boundary: dir(owlbear.tools) exposes EXACTLY the 10 names — no extras
# ---------------------------------------------------------------------------


class TestFromAC_DirExactBoundary:
    """dir(owlbear.tools) must expose exactly the 10 curated public names and no others.

    The positive presence check (all 10 present) lives in TestFromAC_DirParity.
    This class guards the UPPER bound: no public (non-underscore) name beyond
    the 10-name __all__ contract may appear in dir(owlbear.tools).

    These tests FAIL on the current tree because owlbear.tools has no __dir__,
    so dir() includes 'importlib' in its public names and excludes the 10 curated
    names, making the exact-set equality assertion fail.
    """

    def test_dir_exposes_no_public_names_beyond_all_contract_subprocess(self) -> None:
        """dir(owlbear.tools) must expose exactly the curated __all__ names as public API.

        Uses a clean subprocess to avoid state pollution from prior attribute accesses.
        Public names are those that do NOT start with ``_``.  After a correct
        ``def __dir__() -> list[str]: return list(__all__)`` implementation,
        ``dir(owlbear.tools)`` returns exactly the 10-name surface — no internal
        helper symbols such as ``importlib`` or ``_LAZY_IMPORTS`` leak into the
        public view.

        FAILS on the current tree: no custom ``__dir__`` means ``dir()`` exposes
        the module globals (including ``importlib``) and omits all 10 curated names,
        so the set-equality assertion fails.
        """
        expected = sorted(
            [
                "AskUserToolset",
                "FileToolset",
                "GitHubToolset",
                "GitLocalToolset",
                "HookedToolset",
                "KanbanToolset",
                "MCPServerRegistry",
                "TerminalToolset",
                "find_toolset",
                "unwrap",
            ]
        )
        expected_repr = repr(expected)
        script = (
            "import sys, owlbear.tools; "
            f"expected = {expected_repr}; "
            "d = dir(owlbear.tools); "
            "public = sorted(n for n in d if not n.startswith('_')); "
            "assert public == expected, "
            "f'dir(owlbear.tools) public names {public!r} != expected {expected!r}'"
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"dir() exact-boundary check failed:\n{result.stderr}"
