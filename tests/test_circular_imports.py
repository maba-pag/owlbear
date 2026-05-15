"""Structural regression tests for circular-import elimination (task #1210).

Tests for extracting _parse_duration/_DURATION_RE to _duration.py and
_exclusive_file_lock to _locking.py, updating all call sites, and removing
the models.py duplicate.

All tests must FAIL in RED (new modules absent, old structures intact).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers to locate source paths and parse ASTs
# ---------------------------------------------------------------------------

_PKG_DIR = Path(__file__).parent.parent / "serve" / "kanban" / "src" / "owlbear_kanban"
_TESTS_DIR = Path(__file__).parent.parent / "serve" / "kanban" / "tests"
_ROOT_TESTS_DIR = Path(__file__).parent


def _source(filename: str) -> str:
    return (_PKG_DIR / filename).read_text(encoding="utf-8")


def _test_source(filename: str) -> str:
    return (_TESTS_DIR / filename).read_text(encoding="utf-8")


def _root_test_source(filename: str) -> str:
    return (_ROOT_TESTS_DIR / filename).read_text(encoding="utf-8")


def _module_imports(source: str) -> list[tuple[str, list[str]]]:
    """Return list of (module, names) for all top-level and nested Import/ImportFrom nodes."""
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [alias.name for alias in node.names]
            results.append((node.module, names))
    return results


def _has_top_level_function(source: str, funcname: str) -> bool:
    """Return True if source has a module-level FunctionDef named funcname."""
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.FunctionDef) and node.name == funcname
        for node in ast.iter_child_nodes(tree)
    )


def _has_module_level_assign(source: str, varname: str) -> bool:
    """Return True if source has a module-level assignment target named varname."""
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == varname:
                    return True
    return False


def _intra_pkg_imports(source: str, pkg_prefix: str = "owlbear_kanban") -> list[str]:
    """Return all intra-package modules imported (absolute imports starting with pkg_prefix)."""
    modules = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(pkg_prefix):
                modules.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(pkg_prefix):
                    modules.append(alias.name)
    return modules


def _module_level_imports_from(source: str, module: str) -> list[str]:
    """Return names imported at module-level scope (direct Module children) from module."""
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            return [alias.name for alias in node.names]
    return []


# ===========================================================================
# AC1 — _duration.py: exists, exports _parse_duration and _DURATION_RE,
#        only intra-package import is ConfigError from owlbear_kanban.errors
# ===========================================================================


class TestFromAC_DurationModule:
    """AC1: _duration.py exists as a true leaf module."""

    def test_duration_module_importable(self) -> None:
        """_duration module must be importable from owlbear_kanban."""
        import owlbear_kanban._duration  # noqa: F401

    def test_parse_duration_exported(self) -> None:
        """_duration must export _parse_duration as a callable."""
        from owlbear_kanban._duration import _parse_duration

        assert callable(_parse_duration)

    def test_duration_re_exported(self) -> None:
        """_duration must export _DURATION_RE as a compiled pattern."""
        from owlbear_kanban._duration import _DURATION_RE

        assert hasattr(_DURATION_RE, "match"), "_DURATION_RE must be a compiled regex"

    def test_only_intra_pkg_import_is_errors_configerror(self) -> None:
        """_duration.py intra-package imports must be limited to owlbear_kanban.errors."""
        src = _source("_duration.py")
        intra = _intra_pkg_imports(src)
        forbidden = [m for m in intra if m != "owlbear_kanban.errors"]
        assert not forbidden, (
            f"_duration.py must only import from owlbear_kanban.errors; "
            f"found unexpected intra-pkg imports: {forbidden}"
        )

    def test_parse_duration_happy_path_1h(self) -> None:
        """_parse_duration('1h') must return timedelta(hours=1)."""
        from datetime import timedelta

        from owlbear_kanban._duration import _parse_duration

        assert _parse_duration("1h") == timedelta(hours=1)

    def test_parse_duration_invalid_raises_config_error(self) -> None:
        """_parse_duration with invalid input must raise ConfigError."""
        from owlbear_kanban._duration import _parse_duration
        from owlbear_kanban.errors import ConfigError

        with pytest.raises(ConfigError):
            _parse_duration("notaduration")


# ===========================================================================
# AC3 — engine.py: local definitions of _parse_duration, _DURATION_RE
#        removed; imports them from leaf modules
# ===========================================================================


class TestFromAC_EngineDefinitionsRemoved:
    """AC3: engine.py no longer defines these symbols locally; imports from leaves."""

    def test_parse_duration_not_defined_locally_in_engine(self) -> None:
        """engine.py must NOT contain a module-level def _parse_duration."""
        src = _source("engine.py")
        assert not _has_top_level_function(src, "_parse_duration"), (
            "engine.py still defines _parse_duration as a module-level function — "
            "must be removed and imported from _duration"
        )

    def test_duration_re_not_defined_locally_in_engine(self) -> None:
        """engine.py must NOT contain a module-level _DURATION_RE assignment."""
        src = _source("engine.py")
        assert not _has_module_level_assign(src, "_DURATION_RE"), (
            "engine.py still defines _DURATION_RE at module level — "
            "must be removed and imported from _duration"
        )

    def test_engine_imports_parse_duration_from_duration(self) -> None:
        """engine.py must import _parse_duration from owlbear_kanban._duration."""
        src = _source("engine.py")
        imports = _module_imports(src)
        found = any(
            mod == "owlbear_kanban._duration" and "_parse_duration" in names
            for mod, names in imports
        )
        assert found, (
            "engine.py must import _parse_duration from owlbear_kanban._duration; "
            "import not found"
        )


# ===========================================================================
# AC4 — config_loader.py: imports _parse_duration from _duration (not engine),
#        no deferred import from engine
# ===========================================================================


class TestFromAC_ConfigLoaderImport:
    """AC4: config_loader.py imports _parse_duration from _duration, no deferred engine import."""

    def test_config_loader_imports_from_duration_not_engine(self) -> None:
        """config_loader.py must import _parse_duration from _duration, not engine."""
        src = _source("config_loader.py")
        imports = _module_imports(src)

        # Must NOT import from engine at all
        engine_imports = [mod for mod, _ in imports if mod == "owlbear_kanban.engine"]
        assert not engine_imports, (
            f"config_loader.py still imports from owlbear_kanban.engine: {engine_imports}; "
            "must import _parse_duration from owlbear_kanban._duration"
        )

    def test_config_loader_has_no_deferred_engine_import(self) -> None:
        """config_loader.py must have no inline/deferred import from owlbear_kanban.engine."""
        src = _source("config_loader.py")
        assert "owlbear_kanban.engine" not in src, (
            "config_loader.py still contains 'owlbear_kanban.engine' import; must be removed"
        )
        assert "from owlbear_kanban import engine" not in src, (
            "config_loader.py still contains 'from owlbear_kanban import engine'; must be removed"
        )

    def test_config_loader_imports_parse_duration_from_duration(self) -> None:
        """config_loader.py must have a direct import of _parse_duration from _duration."""
        src = _source("config_loader.py")
        imports = _module_imports(src)
        found = any(
            mod == "owlbear_kanban._duration" and "_parse_duration" in names
            for mod, names in imports
        )
        assert found, (
            "config_loader.py must import _parse_duration from owlbear_kanban._duration; "
            "import not found"
        )


# ===========================================================================
# AC5 — storage.py: no deferred engine import (avoids circular dependency)
# ===========================================================================


class TestFromAC_StorageImport:
    """AC5: storage.py has no imports from owlbear_kanban.engine (avoids circular dep)."""

    def test_storage_has_no_deferred_engine_import(self) -> None:
        """storage.py must have no inline/deferred import from owlbear_kanban.engine."""
        src = _source("storage.py")
        assert "owlbear_kanban.engine" not in src, (
            "storage.py still contains deferred imports from owlbear_kanban.engine"
        )

    def test_storage_no_engine_import_at_any_level(self) -> None:
        """storage.py source must contain no string 'owlbear_kanban.engine'."""
        src = _source("storage.py")
        occurrences = src.count("owlbear_kanban.engine")
        assert occurrences == 0, (
            f"storage.py still references owlbear_kanban.engine {occurrences} time(s)"
        )


# ===========================================================================
# AC6 — models.py: _parse_claim_timeout and _DURATION_RE deleted;
#        BoardConfig validator calls _parse_duration from _duration  (td:2)
# ===========================================================================


class TestFromAC_ModelsDuplicateRemoved:
    """AC6: models.py duplicate _parse_claim_timeout and _DURATION_RE removed."""

    def test_parse_claim_timeout_not_in_models_module_level(self) -> None:
        """models.py must NOT have _parse_claim_timeout as a module-level function."""
        src = _source("models.py")
        assert not _has_top_level_function(src, "_parse_claim_timeout"), (
            "models.py still defines _parse_claim_timeout — duplicate must be removed"
        )

    def test_duration_re_not_in_models_module_level(self) -> None:
        """models.py must NOT define _DURATION_RE at module level."""
        src = _source("models.py")
        assert not _has_module_level_assign(src, "_DURATION_RE"), (
            "models.py still defines _DURATION_RE — duplicate constant must be removed"
        )

    def test_models_imports_parse_duration_from_duration(self) -> None:
        """models.py must import _parse_duration from owlbear_kanban._duration."""
        src = _source("models.py")
        imports = _module_imports(src)
        found = any(
            mod == "owlbear_kanban._duration" and "_parse_duration" in names
            for mod, names in imports
        )
        assert found, (
            "models.py must import _parse_duration from owlbear_kanban._duration; "
            "the BoardConfig validator must call the canonical parser"
        )

    def test_board_config_validator_rejects_invalid_via_duration_parse(self) -> None:
        """BoardConfig validator rejects invalid claim_timeout through _duration._parse_duration."""
        # Requires _duration module to exist — fails (ModuleNotFoundError) in RED phase.
        from owlbear_kanban._duration import _parse_duration  # noqa: F401
        from owlbear_kanban.errors import ConfigError
        from owlbear_kanban.models import BoardConfig

        raw = {
            "statuses": ["research", "done"],
            "priorities": ["important"],
            "entry_status": "research",
            "terminal_status": "done",
            "next_id": 1,
            "pipeline": {"claim_timeout": "notvalid"},
        }
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(raw)

    def test_board_config_valid_claim_timeout_accepted(self) -> None:
        """BoardConfig validator must accept a valid claim_timeout string."""
        from owlbear_kanban.models import BoardConfig

        raw = {
            "statuses": ["research", "done"],
            "priorities": ["important"],
            "entry_status": "research",
            "terminal_status": "done",
            "next_id": 1,
            "pipeline": {"claim_timeout": "1h"},
        }
        config = BoardConfig.model_validate(raw)
        assert config.pipeline.claim_timeout == "1h"

    def test_parse_claim_timeout_not_importable_from_models(self) -> None:
        """_parse_claim_timeout must not be accessible from owlbear_kanban.models."""
        import owlbear_kanban.models as _models

        assert not hasattr(_models, "_parse_claim_timeout"), (
            "owlbear_kanban.models still exposes _parse_claim_timeout — "
            "duplicate function must be deleted"
        )

    def test_board_config_validate_semantics_calls_parse_duration(self) -> None:
        """_validate_semantics method of BoardConfig must call _parse_duration(…) by name,
        not just import it — a dead import does not satisfy AC6."""
        src = _source("models.py")
        tree = ast.parse(src)

        for class_node in ast.walk(tree):
            if not (
                isinstance(class_node, ast.ClassDef)
                and class_node.name == "BoardConfig"
            ):
                continue
            for method in ast.walk(class_node):
                if not (
                    isinstance(method, ast.FunctionDef)
                    and method.name == "_validate_semantics"
                ):
                    continue
                calls = [
                    child
                    for child in ast.walk(method)
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Name)
                        and child.func.id == "_parse_duration"
                    )
                ]
                assert calls, (
                    "BoardConfig._validate_semantics does not call _parse_duration(…); "
                    "a dead import of _parse_duration does not satisfy AC6 — "
                    "the canonical parser must be invoked inside the validator"
                )
                return
            pytest.fail(
                "_validate_semantics method not found inside BoardConfig class in models.py"
            )
            return

        pytest.fail("BoardConfig class not found in models.py")


# ===========================================================================
# AC7 — Test import updates: coverage_1068.py and engine_storage.py import
#        _parse_duration from _duration; dead_code_1112.py reads _locking.py
# ===========================================================================


class TestFromAC_TestFileImportUpdates:
    """AC7: Downstream test files updated to import from new leaf modules."""

    def test_engine_storage_imports_parse_duration_from_duration(self) -> None:
        """test_engine_storage.py must import _parse_duration from _duration, not engine."""
        src = _test_source("test_engine_storage.py")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "owlbear_kanban.engine"
            ):
                names = [alias.name for alias in node.names]
                assert "_parse_duration" not in names, (
                    "test_engine_storage.py still imports _parse_duration from "
                    "owlbear_kanban.engine — must be updated to owlbear_kanban._duration"
                )
        found = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "owlbear_kanban._duration"
            and any(alias.name == "_parse_duration" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert found, (
            "test_engine_storage.py must import _parse_duration from "
            "owlbear_kanban._duration; import not found"
        )
