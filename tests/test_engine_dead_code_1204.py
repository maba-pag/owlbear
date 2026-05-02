"""Tests for task #1204 — Remove _validate_engine_config; trust model validator.

AC1 (td:1): _validate_engine_config function deleted from engine.py.

AC5 (td:1): BoardConfig._validate_semantics still rejects invalid configs.
  — Covered by TestFromAC_ValidateSemanticsStillRejects below (retry cycle:
    reviewer required direct executable proof replacing the false reference to
    the non-existent TestFromAC_BoardConfigSemanticValidation class).
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


# ---------------------------------------------------------------------------
# AC5 — BoardConfig._validate_semantics still rejects invalid configurations
# ---------------------------------------------------------------------------

# Minimal valid flat-key dict (no grouped sub-model instances) used as a base
# for each invalid variant.  Flat keys avoid the "mixing" branch in
# _normalise_legacy that would raise ERR_INVALID_STATUS before _validate_semantics runs.
_VALID_BASE: dict = {
    "statuses": ["research", "done"],
    "priorities": ["low"],
    "entry_status": "research",
    "terminal_status": "done",
    "claim_timeout": "1h",
}


class TestFromAC_ValidateSemanticsStillRejects:
    """AC5: BoardConfig._validate_semantics rejects all listed invalid configs.

    Proof that the model-level semantic validator still enforces the same
    invariants that _validate_engine_config used to check — empty statuses,
    empty priorities, invalid entry_status, invalid terminal_status, invalid
    claim_timeout, non-list agent_compatibility, asymmetric agent_compatibility.

    All tests use BoardConfig.model_validate() with flat-key dicts so that
    _normalise_legacy routes through the non-grouped path, leaving
    _validate_semantics as the sole gate under test.
    """

    def test_empty_statuses_raises(self) -> None:
        """Empty statuses list must be rejected with ERR_INVALID_STATUS."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "statuses": []}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_INVALID_STATUS"

    def test_empty_priorities_raises(self) -> None:
        """Empty priorities list must be rejected with ERR_INVALID_PRIORITY."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "priorities": []}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_INVALID_PRIORITY"

    def test_invalid_entry_status_raises(self) -> None:
        """entry_status not in statuses must be rejected with ERR_ENTRY_STATUS_INVALID."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "entry_status": "nonexistent"}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_ENTRY_STATUS_INVALID"

    def test_invalid_terminal_status_raises(self) -> None:
        """terminal_status != statuses[-1] must be rejected with ERR_TERMINAL_STATUS_INVALID."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        # "research" is in statuses but is not the last element
        cfg = {**_VALID_BASE, "terminal_status": "research"}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_TERMINAL_STATUS_INVALID"

    def test_invalid_claim_timeout_raises(self) -> None:
        """Unparseable claim_timeout must be rejected with ERR_INVALID_CLAIM_TIMEOUT."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "claim_timeout": "not-a-duration"}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_non_list_agent_compatibility_raises(self) -> None:
        """agent_compatibility value that is not a list must be rejected."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "agent_compatibility": {"agent-a": "should-be-a-list"}}
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(cfg)

    def test_asymmetric_agent_compatibility_raises(self) -> None:
        """One-sided agent_compatibility entry must be rejected."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        # agent-a lists agent-b as compatible but agent-b has no entry at all
        cfg = {**_VALID_BASE, "agent_compatibility": {"agent-a": ["agent-b"]}}
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(cfg)
