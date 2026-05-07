"""Tests for #1385: Cockpit decision lifecycle backend unification.

AC coverage:
  AC1 — routes/decisions.py imports DR file parsing from owlbear_kanban.decisions
         instead of maintaining a local _parse_dr implementation. (td:1)
  AC2 — Task summary formatting uses the shared function from owlbear_kanban.decisions
         instead of a local _canonical_summary. (td:1)
  AC3 — owlbear_kanban.decisions exposes shared helpers as public API
         (parse_dr and canonical_summary importable without underscore). (td:1)
  AC4 — Cockpit-specific HTTP concerns remain in the cockpit module:
         _validate_decision_id, _extract_title. Cockpit must not define _parse_dr
         or _canonical_summary after delegating to kanban. (td:1)
  AC5 — Error format contract preserved: already-resolved → 409 {code, message}.
         Structural prerequisite: parse_dr importable from owlbear_kanban.decisions. (td:1)
  AC6 — All tests in tests/test_cockpit_decisions_api_1384.py pass without modification.
         [covered by existing suite — no new RED-phase test possible for meta-AC]
  AC7 — All tests in tests/test_decisions_1181.py pass without modification.
         [covered by existing suite — no new RED-phase test possible for meta-AC]

Note: AC6 and AC7 are "pass without modification" meta-contracts enforced by running
the full test suite. The existing files test_cockpit_decisions_api_1384.py and
test_decisions_1181.py are the regression contracts for those ACs. No new failing
tests can be written for "X test suite passes" assertions.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - docs
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""


# ---------------------------------------------------------------------------
# Board / decision helpers
# ---------------------------------------------------------------------------


def _make_board(board_dir: Path) -> None:
    """Write minimal board files into *board_dir*."""
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board_dir / "tasks").mkdir(exist_ok=True)
    (board_dir / "archive").mkdir(exist_ok=True)
    (board_dir / "decisions" / "pending").mkdir(parents=True)
    (board_dir / "decisions" / "resolved").mkdir(parents=True)


def _write_resolved_dr(
    board_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str = "What should we do?",
    response: str = "approved",
) -> Path:
    """Write a DR file directly to resolved/ (simulating an externally resolved DR)."""
    path = board_dir / "decisions" / "resolved" / f"{stem}.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: scope-decision\n"
        "created: '2026-05-06'\n"
        f"response: {response}\n"
        "---\n\n"
        f"# {stem}\n\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Return an isolated board directory with decisions/ pre-created."""
    bd = tmp_path / "board"
    _make_board(bd)
    return bd


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine backed by the isolated board, with index pre-warmed."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with engine dependency override."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _create_blocked_task(engine: KanbanEngine, title: str) -> int:
    """Create a task and immediately block it; return its integer ID."""
    task = engine.create_task(title)
    engine.edit_task(task.id, blocked=True, block_reason="DR pending")
    engine.list_tasks()
    return task.id


# ---------------------------------------------------------------------------
# AC3: owlbear_kanban.decisions exposes shared helpers as public API
# ---------------------------------------------------------------------------


class TestFromAC_PublicAPIExposure:
    """AC3: owlbear_kanban.decisions must export parse_dr and canonical_summary publicly."""

    def test_parse_dr_importable_from_kanban_decisions(self) -> None:
        """parse_dr must be importable from owlbear_kanban.decisions as a public symbol.

        FAILS now: the module only defines _parse_dr (private, underscore-prefixed).
        After builder promotes it, this import will succeed.
        """
        from owlbear_kanban.decisions import parse_dr  # noqa: F401

    def test_canonical_summary_importable_from_kanban_decisions(self) -> None:
        """canonical_summary must be importable from owlbear_kanban.decisions as a public symbol.

        FAILS now: the module has _append_summary (private, different signature) but no
        public canonical_summary helper. After builder adds the public wrapper, import succeeds.
        """
        from owlbear_kanban.decisions import canonical_summary  # noqa: F401


# ---------------------------------------------------------------------------
# AC1 + AC2: cockpit routes/decisions.py delegates to shared kanban helpers
# ---------------------------------------------------------------------------


class TestFromAC_ImportDelegation:
    """AC1/AC2: cockpit routes/decisions.py must not duplicate parser or summary logic."""

    def test_cockpit_does_not_define_local_parse_dr(self) -> None:
        """After refactoring, cockpit must not define its own _parse_dr.

        FAILS now: owlbear_cockpit.routes.decisions currently owns a local
        _parse_dr function that duplicates owlbear_kanban.decisions._parse_dr.
        """
        import owlbear_cockpit.routes.decisions as m  # noqa: PLC0415

        assert not hasattr(m, "_parse_dr"), (
            "cockpit routes/decisions.py must not define local _parse_dr after "
            "delegating to owlbear_kanban.decisions"
        )

    def test_cockpit_does_not_define_local_canonical_summary(self) -> None:
        """After refactoring, cockpit must not define its own _canonical_summary.

        FAILS now: owlbear_cockpit.routes.decisions currently owns a local
        _canonical_summary function that duplicates kanban's summary logic.
        """
        import owlbear_cockpit.routes.decisions as m  # noqa: PLC0415

        assert not hasattr(m, "_canonical_summary"), (
            "cockpit routes/decisions.py must not define local _canonical_summary after "
            "delegating to owlbear_kanban.decisions"
        )


# ---------------------------------------------------------------------------
# AC4: cockpit retains HTTP-specific concerns, discards duplicated domain logic
# ---------------------------------------------------------------------------


class TestFromAC_CockpitBoundary:
    """AC4: Cockpit retains _validate_decision_id and _extract_title; sheds _parse_dr and _canonical_summary."""

    def test_cockpit_retains_validate_decision_id_and_removes_local_parse_dr(
        self,
    ) -> None:
        """Cockpit must keep _validate_decision_id AND must not keep _parse_dr.

        The positive assertion (_validate_decision_id present) is a regression guard.
        The negative assertion (no _parse_dr) FAILS now — cockpit currently defines
        its own _parse_dr — and will pass after the builder delegates to kanban.
        """
        import owlbear_cockpit.routes.decisions as m  # noqa: PLC0415

        assert hasattr(m, "_validate_decision_id"), (
            "Cockpit must retain _validate_decision_id (HTTP-specific concern)"
        )
        assert not hasattr(m, "_parse_dr"), (
            "Cockpit must not define local _parse_dr after delegating to kanban (AC1)"
        )

    def test_cockpit_retains_extract_title_and_removes_local_canonical_summary(
        self,
    ) -> None:
        """Cockpit must keep _extract_title AND must not keep _canonical_summary.

        The positive assertion (_extract_title present) is a regression guard.
        The negative assertion (no _canonical_summary) FAILS now — cockpit currently
        defines its own _canonical_summary — and will pass after builder delegates to kanban.
        """
        import owlbear_cockpit.routes.decisions as m  # noqa: PLC0415

        assert hasattr(m, "_extract_title"), (
            "Cockpit must retain _extract_title (HTTP-specific concern for list endpoint)"
        )
        assert not hasattr(m, "_canonical_summary"), (
            "Cockpit must not define local _canonical_summary after delegating to kanban (AC2)"
        )


# ---------------------------------------------------------------------------
# AC5: error format contract preserved after import refactoring
# ---------------------------------------------------------------------------


class TestFromAC_ErrorFormatPreserved:
    """AC5: already-resolved → 409 with domain envelope {code, message} after shared API promoted."""

    def test_already_resolved_returns_409_domain_envelope(
        self,
        client: TestClient,
        engine: KanbanEngine,
        board_dir: Path,
    ) -> None:
        """DR resolved outside cockpit → POST resolve → 409 with {code, message} envelope.

        Structural prerequisite (AC3): parse_dr must be importable from
        owlbear_kanban.decisions. FAILS now because that import fails (only
        _parse_dr, private, exists). After builder promotes parse_dr to public
        API, the import succeeds and the error envelope assertion is verified.
        """
        from owlbear_kanban.decisions import parse_dr  # noqa: F401  # AC3 prerequisite

        task_id = _create_blocked_task(engine, "already-resolved-envelope-task")
        stem = f"{task_id}-already-resolved-envelope"
        # Write a DR that was resolved externally (not via cockpit-api) → triggers 409.
        _write_resolved_dr(board_dir, stem=stem, task_id=task_id, response="approved")

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )

        assert resp.status_code == 409, (
            "Already-resolved DR must return 409 Conflict"
        )
        data = resp.json()
        assert "code" in data, (
            "Already-resolved 409 response must include 'code' in domain envelope"
        )
        assert "message" in data, (
            "Already-resolved 409 response must include 'message' in domain envelope"
        )
