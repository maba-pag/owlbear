"""Tests for task #1204 — Remove _validate_engine_config; trust model validator.

AC1 (td:1): _validate_engine_config function deleted from engine.py.

AC5 (td:1): BoardConfig._validate_semantics still rejects invalid configs.
  — Covered by the existing model-level test suite in
    serve/kanban/tests/test_engine_init_1068.py (TestFromAC_BoardConfigSemanticValidation).
  — Any smoke test added here for AC5 passes against current code, so per
    w-tdd-red (passing tests = implementation already exists) it is omitted.
    The builder's obligation is confirmed via that existing suite.
"""

from __future__ import annotations

import importlib
import sys

import pytest


class TestFromAC_RemoveValidateEngineConfig:
    """AC1: _validate_engine_config must not exist in owlbear_kanban.engine after deletion."""

    def _fresh_engine_module(self):  # type: ignore[return]
        """Reload engine module to defeat any cached import of the function."""
        mod_name = "owlbear_kanban.engine"
        # Ensure a clean import from disk, not from sys.modules cache.
        saved = sys.modules.pop(mod_name, None)
        try:
            return importlib.import_module(mod_name)
        finally:
            if saved is not None:
                sys.modules[mod_name] = saved

    def test_function_not_in_engine_module(self) -> None:
        """_validate_engine_config must not be a module-level attribute of owlbear_kanban.engine."""
        import owlbear_kanban.engine as engine_mod

        assert not hasattr(engine_mod, "_validate_engine_config"), (
            "_validate_engine_config still present in owlbear_kanban.engine — "
            "function must be deleted (task #1204)"
        )

    def test_function_not_importable_from_engine(self) -> None:
        """Direct import of _validate_engine_config from owlbear_kanban.engine must raise ImportError."""
        with pytest.raises(ImportError):
            from owlbear_kanban.engine import _validate_engine_config  # noqa: F401
