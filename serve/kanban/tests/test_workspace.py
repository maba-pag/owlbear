"""Behavioral coverage for native workspace assembly."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from owlbear_kanban import NativeWorkspace, parse_claim_expiry


def test_native_workspace_resolves_native_roots_without_legacy_board_files(tmp_path: Path) -> None:
    work_root = tmp_path / ".owlbear" / "work"
    work_root.mkdir(parents=True)

    workspace = NativeWorkspace(work_root, timedelta(minutes=5))

    assert workspace.work_root == work_root.resolve()
    assert workspace.changes_dir == tmp_path / ".owlbear" / "changes"
    assert workspace.workspace_root == tmp_path
    assert workspace.proof_root == tmp_path / ".owlbear" / "scratch" / "proof"
    assert workspace.legacy_snapshot_root == tmp_path / ".owlbear" / "legacy"
    assert not (work_root / "tasks").exists()
    assert not (work_root / "config.yml").exists()


@pytest.mark.parametrize("claim_expiry", [timedelta(0), timedelta(seconds=-1)])
def test_native_workspace_rejects_non_positive_claim_expiry(tmp_path: Path, claim_expiry: timedelta) -> None:
    with pytest.raises(ValueError, match="claim expiry must be positive"):
        NativeWorkspace(tmp_path, claim_expiry)


def test_parse_claim_expiry_uses_native_units() -> None:
    assert parse_claim_expiry("30m") == timedelta(minutes=30)
    assert parse_claim_expiry("2h") == timedelta(hours=2)
    with pytest.raises(ValueError, match="claim expiry"):
        parse_claim_expiry("0h")
