"""E2E dispatch integration test — full dispatch stack without Copilot CLI.

Tests orchestrate() from owlbear.orchestrator.loop directly:
planner gates, wave assembly, AcpClient, mock ACP agent, kanban board mutations,
and audit log. Deterministic and CI-friendly (no Copilot CLI required).

Task #156.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear.audit.log import AuditLog
from owlbear.orchestrator.loop import orchestrate

if TYPE_CHECKING:
    pass


MOCK_AGENT_PATH = Path("tests/fixtures/mock_acp_agent.py").resolve()

# ---------------------------------------------------------------------------
# Board configuration — full pipeline statuses required for --next to work
# ---------------------------------------------------------------------------

_BOARD_CONFIG = """\
version: 10
board:
    name: test-integration
tasks_dir: tasks
statuses:
    - name: research
    - name: backlog
    - name: todo
    - name: in-progress
    - name: review
    - name: docs
    - name: done
priorities:
    - someday
    - nice-to-have
    - important
    - needed
    - critical
defaults:
    status: research
    priority: important
    class: standard
tui:
    title_lines: 1
next_id: 1
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_kanban_bin() -> Path:
    """Resolve the kanban-md binary or skip the test if not found.

    Resolution order:
    1. ``KANBAN_BIN`` environment variable
    2. ``kanban/kanban-md.exe`` relative to the repository root
    """
    env_bin = os.environ.get("KANBAN_BIN")
    if env_bin:
        p = Path(env_bin)
        if p.exists():
            return p

    repo_root = Path(__file__).resolve().parent.parent
    convention = repo_root / ".owlbear" / "kanban" / "kanban-md.exe"
    if convention.exists():
        return convention

    pytest.skip("kanban-md binary not found — run kanban/setup.ps1 or set KANBAN_BIN env var")


@pytest.fixture
def board_dir(tmp_path: Path, real_kanban_bin: Path) -> Path:
    """Create a temp board via kanban-md with a seed task at todo with AC in body."""
    (tmp_path / "tasks").mkdir()
    (tmp_path / "config.yml").write_text(_BOARD_CONFIG, encoding="utf-8")
    bin_str = str(real_kanban_bin)
    dir_str = str(tmp_path)
    subprocess.run([bin_str, "--dir", dir_str, "create", "Seed integration task"], check=True)
    subprocess.run([bin_str, "--dir", dir_str, "move", "1", "todo"], check=True)
    subprocess.run(
        [bin_str, "--dir", dir_str, "edit", "1", "-a", "## Acceptance Criteria\n\n- Does something useful"],
        check=True,
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_seed_task(board_dir: Path) -> str:
    """Return the raw content of the seed task file (task id 1, created by kanban-md)."""
    # kanban-md names task files as NNN-slug.md; use *.md since only one task exists.
    task_files = list((board_dir / "tasks").glob("*.md"))
    assert task_files, "No task files found in board_dir/tasks/"
    return task_files[0].read_text(encoding="utf-8")


async def _run_orchestrate(
    real_kanban_bin: Path,
    board_dir: Path,
    audit_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AuditLog:
    """Wire up and run orchestrate(), returning the AuditLog for inspection."""
    monkeypatch.setenv("KANBAN_DIR", str(board_dir))
    monkeypatch.setenv("KANBAN_BIN", str(real_kanban_bin))
    audit_log = AuditLog(audit_dir)
    await orchestrate(
        kanban_bin=real_kanban_bin,
        kanban_dir=board_dir,
        copilot_cmd=[sys.executable, str(MOCK_AGENT_PATH)],
        audit_log=audit_log,
        wave_size=4,
    )
    return audit_log


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_DispatchIntegration:
    """Integration tests for the full dispatch stack via orchestrate().

    Each test uses a fresh tmp_path board and audit dir — no shared state.
    """

    # AC: orchestrate() completes without raising
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_orchestrate_completes_without_raising(
        self,
        real_kanban_bin: Path,
        board_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """orchestrate() returns normally — no exception raised."""
        await _run_orchestrate(real_kanban_bin, board_dir, tmp_path / "audit", monkeypatch)

    # AC: seed task status changed from todo after orchestrate completes
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_seed_task_status_changes_from_todo(
        self,
        real_kanban_bin: Path,
        board_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Seed task status is no longer 'todo' after dispatch (mock agent moves it --next)."""
        await _run_orchestrate(real_kanban_bin, board_dir, tmp_path / "audit", monkeypatch)

        content = _read_seed_task(board_dir)
        assert "status: todo" not in content

    # AC: seed task body contains "Mock agent processed" annotation
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_seed_task_body_contains_mock_annotation(
        self,
        real_kanban_bin: Path,
        board_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Seed task body contains 'Mock agent processed' after dispatch (mock agent edits it)."""
        await _run_orchestrate(real_kanban_bin, board_dir, tmp_path / "audit", monkeypatch)

        content = _read_seed_task(board_dir)
        assert "Mock agent processed" in content

    # AC: audit log dir contains at least one .jsonl file with a DispatchEvent for seed task
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_audit_log_contains_dispatch_event_for_seed_task(
        self,
        real_kanban_bin: Path,
        board_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Audit log dir has at least one .jsonl file containing a DispatchEvent for task_id 1."""
        audit_dir = tmp_path / "audit"
        await _run_orchestrate(real_kanban_bin, board_dir, audit_dir, monkeypatch)

        jsonl_files = list(audit_dir.glob("*.jsonl"))
        assert len(jsonl_files) >= 1, "No .jsonl files found in audit dir"

        dispatch_events = []
        for f in jsonl_files:
            for line in f.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                data = json.loads(stripped)
                if data.get("type") == "dispatch":
                    dispatch_events.append(data)

        assert any(e["task_id"] == 1 for e in dispatch_events), (
            f"No DispatchEvent for task_id=1 found; events: {dispatch_events}"
        )
