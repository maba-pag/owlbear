"""Tests for #1206: Remove storage.load_config wrapper / clean up double-validation.

AC coverage:
  AC1: storage.py no longer defines or exports load_config (td:1)
       — symbol absent from __all__, module attributes, and module docstring
  AC5: No double _validate_claim_timeout call in any load path (td:1)
       — config_loader.load_config invokes _validate_claim_timeout exactly once
"""

from __future__ import annotations

from pathlib import Path

import owlbear_kanban.storage as storage_mod

# ---------------------------------------------------------------------------
# Shared board fixture
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - done
priorities:
  - someday
  - important
  - critical
entry_status: research
claim_timeout: 1h
next_id: 1
agent_map:
  research: []
  backlog: []
  done: []
"""


def _make_board(tmp_path: Path, config_yaml: str = _CONFIG_YAML) -> Path:
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1: storage.py no longer defines or exports load_config
# ---------------------------------------------------------------------------


class TestFromAC_StorageDropsLoadConfig:
    """Verify load_config is fully removed from storage.py public surface (AC1)."""

    def test_load_config_absent_from_dunder_all(self) -> None:
        """load_config must not appear in owlbear_kanban.storage.__all__."""
        assert "load_config" not in storage_mod.__all__

    def test_load_config_not_an_attribute_on_storage_module(self) -> None:
        """storage module must not define a load_config attribute at all."""
        assert not hasattr(storage_mod, "load_config")

    def test_load_config_absent_from_module_docstring(self) -> None:
        """Module docstring (Public API section) must not list load_config."""
        docstring = storage_mod.__doc__ or ""
        assert "load_config" not in docstring


# ---------------------------------------------------------------------------
# AC5: No double _validate_claim_timeout call in any load path
# ---------------------------------------------------------------------------


class TestFromAC_NoDoubleValidation:
    """storage.py must not contain a redundant _validate_claim_timeout call (AC5).

    The double-call exists because storage.load_config re-invokes
    _validate_claim_timeout after delegating to config_loader.load_config.
    After the wrapper is removed, storage.py must not reference
    _validate_claim_timeout at all.
    """

    def test_storage_does_not_reference_validate_claim_timeout(self) -> None:
        """storage.py source must not contain _validate_claim_timeout (no re-call)."""
        import inspect

        source = inspect.getsource(storage_mod)
        assert "_validate_claim_timeout" not in source, (
            "storage.py still references _validate_claim_timeout — "
            "the double-validation wrapper has not been removed"
        )


