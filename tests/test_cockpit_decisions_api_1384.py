"""Failing tests for #1384: Cockpit decision lifecycle backend side effects.

AC coverage:
  AC1 — approved resolution: file moved pending→resolved, task unblocked,
         canonical summary appended to task, response shape {id, response} (td:2)
  AC2 — rejected resolution: same lifecycle assertions as approved (td:2)
  AC3 — needs-info resolution: file moved, summary appended, task stays blocked (td:2)
  AC4 — already-resolved: 409 with domain error envelope {code, message} (td:2)
  AC5 — duplicate-response (second call after first moved it): 404 {detail} (td:2)
  AC6 — unknown decision ID: 404 {detail} format (td:1) [pre-existing, protected by #1371 AC8]
  AC7 — malformed decision ID (path traversal): 422 {detail} format (td:1) [pre-existing, protected by #1371 AC8]
  AC8 — side effects observable immediately after request, no deferred sweep (td:1)

Note: AC6 and AC7 are pre-existing behaviors enforced by #1371 AC8. Passing regression guards
exist in test_cockpit_decisions_api_1189.py; no new RED-phase tests needed for those ACs.
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
# Board / decisions helpers
# ---------------------------------------------------------------------------


def _make_board(board_dir: Path) -> None:
    """Write minimal board files into *board_dir*."""
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board_dir / "tasks").mkdir(exist_ok=True)
    (board_dir / "archive").mkdir(exist_ok=True)
    (board_dir / "decisions" / "pending").mkdir(parents=True)
    (board_dir / "decisions" / "resolved").mkdir(parents=True)


def _write_pending_dr(
    board_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str = "What should we do?",
    response: str = "pending",
) -> Path:
    """Write a DR file to pending/ and return its path."""
    path = board_dir / "decisions" / "pending" / f"{stem}.md"
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


def _write_resolved_dr(
    board_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str = "What should we do?",
    response: str = "approved",
) -> Path:
    """Write a DR file directly to resolved/ (simulating a pre-resolved DR)."""
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
    engine.list_tasks()  # warm the cache so show_task can find the task
    return task.id


def _read_task_body(engine: KanbanEngine, task_id: int) -> str:
    """Return the body of a task, clearing cache first for freshness."""
    engine.list_tasks()  # bust the cache
    return engine.show_task(str(task_id)).body


def _is_task_blocked(engine: KanbanEngine, task_id: int) -> bool:
    """Return True when the task's blocked field is True on disk."""
    engine.list_tasks()  # bust the cache
    return bool(engine.show_task(str(task_id)).blocked)


# ---------------------------------------------------------------------------
# AC1: Approved resolution lifecycle
# ---------------------------------------------------------------------------


class TestFromAC_ApprovedResolution:
    """AC1: Approved resolution moves file, unblocks task, appends summary, returns shape."""

    def test_approve_moves_dr_from_pending_to_resolved(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After approving, the DR file must not exist in pending/ any more.

        FAILS now: current implementation rewrites the file in-place in pending/
        — it does NOT move it to resolved/.
        """
        task_id = _create_blocked_task(engine, "Approve move task")
        stem = f"{task_id}-scope-decision"
        pending_path = _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert not pending_path.exists(), (
            "DR file must be removed from pending/ after approval"
        )

    def test_approve_places_dr_in_resolved(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After approving, the DR file must appear in resolved/.

        FAILS now: current implementation never writes to resolved/.
        """
        task_id = _create_blocked_task(engine, "Approve to resolved task")
        stem = f"{task_id}-scope-resolved"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)
        resolved_path = board_dir / "decisions" / "resolved" / f"{stem}.md"

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert resolved_path.exists(), (
            "DR file must appear in resolved/ after approval"
        )

    def test_approve_unblocks_the_associated_task(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After approving, the task referenced in the DR frontmatter must be unblocked.

        FAILS now: current implementation does not call engine.edit_task(blocked=False).
        """
        task_id = _create_blocked_task(engine, "Approve unblock task")
        stem = f"{task_id}-scope-unblock"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)
        assert _is_task_blocked(engine, task_id), "Pre-condition: task must start blocked"

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert not _is_task_blocked(engine, task_id), (
            "Task must be unblocked after approval"
        )

    def test_approve_appends_canonical_summary_to_task_body(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After approving, the task body must contain a canonical ## Decision Request block.

        FAILS now: current implementation rewrites the DR file only; task body is untouched.
        """
        task_id = _create_blocked_task(engine, "Approve summary task")
        stem = f"{task_id}-scope-summary"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id, body="Summary body text.")

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        body = _read_task_body(engine, task_id)
        assert "## Decision Request" in body, (
            "Task body must contain canonical ## Decision Request section"
        )
        assert "approved" in body, (
            "## Decision Request block must mention the resolution response"
        )

    def test_approve_response_body_shape(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """POST response for approved resolution must be exactly {id, response}.

        FAILS now if implementation omits either key or adds extra keys.
        Current implementation returns {"id": ..., "response": ...} so this
        passes; added here to pin the contract per reviewer AC1 gap.
        """
        task_id = _create_blocked_task(engine, "Approve response shape task")
        stem = f"{task_id}-approve-shape"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"id": stem, "response": "approved"}, (
            "Approved resolution POST must return exactly {id, response} shape"
        )

    def test_approve_summary_includes_source_line(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Approved resolution: canonical task summary must contain the '- source:' line.

        FAILS now if _canonical_summary omits the source field.  Current impl
        includes it; test added to pin the contract per reviewer AC1 gap.
        """
        task_id = _create_blocked_task(engine, "Approve source line task")
        stem = f"{task_id}-approve-source"
        _write_pending_dr(
            board_dir, stem=stem, task_id=task_id, body="Decide the scope."
        )

        client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )

        body = _read_task_body(engine, task_id)
        assert "- source:" in body, (
            "Canonical task summary must include '- source:' line (from _canonical_summary)"
        )


# ---------------------------------------------------------------------------
# AC2: Rejected resolution lifecycle
# ---------------------------------------------------------------------------


class TestFromAC_RejectedResolution:
    """AC2: Rejected resolution: same lifecycle assertions as approved."""

    def test_reject_moves_dr_from_pending_to_resolved(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After rejecting, DR file must not exist in pending/.

        FAILS now: current implementation does not move the file.
        """
        task_id = _create_blocked_task(engine, "Reject move task")
        stem = f"{task_id}-reject-move"
        pending_path = _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert not pending_path.exists(), (
            "DR file must be removed from pending/ after rejection"
        )

    def test_reject_places_dr_in_resolved(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After rejecting, DR file must appear in resolved/.

        FAILS now: current implementation never writes to resolved/.
        """
        task_id = _create_blocked_task(engine, "Reject to resolved task")
        stem = f"{task_id}-reject-resolved"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)
        resolved_path = board_dir / "decisions" / "resolved" / f"{stem}.md"

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert resolved_path.exists(), (
            "DR file must appear in resolved/ after rejection"
        )

    def test_reject_unblocks_the_associated_task(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After rejecting, the associated task must be unblocked.

        FAILS now: current implementation does not call engine.edit_task(blocked=False).
        """
        task_id = _create_blocked_task(engine, "Reject unblock task")
        stem = f"{task_id}-reject-unblock"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert not _is_task_blocked(engine, task_id), (
            "Task must be unblocked after rejection"
        )

    def test_reject_appends_canonical_summary_to_task_body(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After rejecting, the task body must contain a canonical ## Decision Request block.

        FAILS now: current implementation does not append to the task body.
        """
        task_id = _create_blocked_task(engine, "Reject summary task")
        stem = f"{task_id}-reject-summary"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        body = _read_task_body(engine, task_id)
        assert "## Decision Request" in body, (
            "Task body must contain canonical ## Decision Request section after rejection"
        )
        assert "rejected" in body, (
            "## Decision Request block must mention the rejection response"
        )

    def test_reject_response_body_shape(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """POST response for rejected resolution must be exactly {id, response}.

        FAILS now if implementation omits either key or adds extra keys.
        Current implementation returns {"id": ..., "response": ...} so this
        passes; added here to pin the contract per reviewer AC2 gap.
        """
        task_id = _create_blocked_task(engine, "Reject response shape task")
        stem = f"{task_id}-reject-shape"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "rejected"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"id": stem, "response": "rejected"}, (
            "Rejected resolution POST must return exactly {id, response} shape"
        )

    def test_reject_summary_includes_source_line(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Rejected resolution: canonical task summary must contain the '- source:' line.

        FAILS now if _canonical_summary omits the source field.  Current impl
        includes it; test added to pin the contract per reviewer AC2 gap.
        """
        task_id = _create_blocked_task(engine, "Reject source line task")
        stem = f"{task_id}-reject-source"
        _write_pending_dr(
            board_dir, stem=stem, task_id=task_id, body="Decide the scope."
        )

        client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "rejected"}
        )

        body = _read_task_body(engine, task_id)
        assert "- source:" in body, (
            "Canonical task summary must include '- source:' line (from _canonical_summary)"
        )


# ---------------------------------------------------------------------------
# AC3: Needs-info resolution lifecycle
# ---------------------------------------------------------------------------


class TestFromAC_NeedsInfoResolution:
    """AC3: Needs-info: file moved, summary appended, task remains blocked."""

    def test_needs_info_moves_dr_to_resolved(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After needs-info, DR file must move from pending/ to resolved/.

        FAILS now: current implementation rewrites in-place in pending/.
        """
        task_id = _create_blocked_task(engine, "Needs-info move task")
        stem = f"{task_id}-needs-info-move"
        pending_path = _write_pending_dr(board_dir, stem=stem, task_id=task_id)
        resolved_path = board_dir / "decisions" / "resolved" / f"{stem}.md"

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "needs-info"})

        assert not pending_path.exists(), "DR must leave pending/ on needs-info"
        assert resolved_path.exists(), "DR must arrive in resolved/ on needs-info"

    def test_needs_info_task_remains_blocked(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After needs-info, the associated task must still be blocked AND file must be moved.

        FAILS now: current implementation does not move the file out of pending/,
        so the resolved-path assertion fails. The task stays blocked only by accident
        (no intentional unblock call) — the test also asserts the canonical contract:
        needs-info must NOT unblock the task, AND must move the DR to resolved/.
        """
        task_id = _create_blocked_task(engine, "Needs-info blocked task")
        stem = f"{task_id}-needs-info-blocked"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)
        resolved_path = board_dir / "decisions" / "resolved" / f"{stem}.md"

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "needs-info"}
        )

        assert resp.status_code == 200, "needs-info must succeed"
        # This assertion fails against current impl (file is NOT moved):
        assert resolved_path.exists(), "DR must be moved to resolved/ on needs-info"
        assert _is_task_blocked(engine, task_id), (
            "Task must remain blocked after needs-info resolution"
        )

    def test_needs_info_appends_canonical_summary_to_task_body(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After needs-info, the task body must contain a ## Decision Request block.

        FAILS now: current implementation does not append anything to the task body.
        """
        task_id = _create_blocked_task(engine, "Needs-info summary task")
        stem = f"{task_id}-needs-info-summary"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "needs-info"})

        body = _read_task_body(engine, task_id)
        assert "## Decision Request" in body, (
            "Task body must contain canonical ## Decision Request section on needs-info"
        )
        assert "needs-info" in body, (
            "## Decision Request block must mention the needs-info response"
        )


# ---------------------------------------------------------------------------
# AC4: Already-resolved returns 409 domain error envelope
# ---------------------------------------------------------------------------


class TestFromAC_AlreadyResolved:
    """AC4: Already-resolved DR (in resolved/ or frontmatter != pending) → 409 {code, message}."""

    def test_dr_already_in_resolved_returns_409(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """POST resolve on a DR that is already in resolved/ must return HTTP 409.

        FAILS now: current _find_decision_path returns the file from resolved/ and
        rewrites it, returning 200 instead of 409.
        """
        task_id = _create_blocked_task(engine, "Already resolved task")
        stem = f"{task_id}-already-resolved"
        _write_resolved_dr(board_dir, stem=stem, task_id=task_id, response="approved")

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )

        assert resp.status_code == 409, (
            "Resolving an already-resolved DR must return 409"
        )

    def test_dr_already_in_resolved_returns_domain_error_envelope(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """409 response for already-resolved DR must use domain envelope {code, message}.

        FAILS now: current implementation returns 200 (not 409) for files in resolved/.
        """
        task_id = _create_blocked_task(engine, "Already resolved envelope task")
        stem = f"{task_id}-already-resolved-envelope"
        _write_resolved_dr(board_dir, stem=stem, task_id=task_id, response="rejected")

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )

        assert resp.status_code == 409
        body = resp.json()
        assert "code" in body, "Domain error envelope must include 'code' field"
        assert "message" in body, "Domain error envelope must include 'message' field"

    def test_dr_in_pending_with_non_pending_frontmatter_returns_409(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """POST resolve on a DR with frontmatter response != pending → 409.

        Represents a DR that was answered in-place without being moved.
        FAILS now: current implementation overwrites the response field without
        checking whether it was already answered, returning 200.
        """
        task_id = _create_blocked_task(engine, "In-place already answered task")
        stem = f"{task_id}-already-answered"
        _write_pending_dr(
            board_dir, stem=stem, task_id=task_id, response="approved"
        )

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "rejected"}
        )

        assert resp.status_code == 409, (
            "Resolving a DR whose frontmatter response is already non-pending must return 409"
        )

    def test_already_resolved_409_uses_domain_envelope(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """409 for in-pending but non-pending frontmatter must use {code, message} format.

        FAILS now: current implementation returns 200 without checking the response field.
        """
        task_id = _create_blocked_task(engine, "In-place envelope check task")
        stem = f"{task_id}-in-place-envelope"
        _write_pending_dr(
            board_dir, stem=stem, task_id=task_id, response="needs-info"
        )

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )

        assert resp.status_code == 409
        body = resp.json()
        assert "code" in body, "Domain error envelope must have 'code'"
        assert "message" in body, "Domain error envelope must have 'message'"


# ---------------------------------------------------------------------------
# AC5: Duplicate-response (second call after first moved it) → 404 {detail}
# ---------------------------------------------------------------------------


class TestFromAC_DuplicateResponse:
    """AC5: Second resolve call on a moved DR must return 404 with FastAPI {detail} format."""

    def test_second_resolve_returns_404(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Sequential second POST to resolve the same ID → 404.

        After the first call moves the DR from pending/, the second call must
        not find it in pending/ and must return 404.

        FAILS now: current implementation rewrites the file in pending/ (no move),
        so the second call returns 200.
        """
        task_id = _create_blocked_task(engine, "Duplicate resolve task")
        stem = f"{task_id}-dup-resolve"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        # First call — must succeed
        first = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )
        assert first.status_code == 200, "First resolve must succeed"

        # Second call — must 404 (file is gone from pending/ after move)
        second = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )
        assert second.status_code == 404, (
            "Second resolve on the same DR after first moved it must return 404"
        )

    def test_second_resolve_uses_fastapi_detail_format(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Second POST returns 404 with FastAPI {detail} format (not domain envelope).

        FAILS now: current implementation returns 200 for the second call.
        """
        task_id = _create_blocked_task(engine, "Duplicate format task")
        stem = f"{task_id}-dup-format"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        # First call
        client.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        # Second call — check format
        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "rejected"}
        )

        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body, (
            "Duplicate-response 404 must use FastAPI {detail} format, not domain envelope"
        )

    def test_second_resolve_different_response_also_404(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Second resolve with a different response value also returns 404 (not 422 or 409).

        The response enum is valid; the failure is that the file is gone.
        FAILS now: current implementation returns 200.
        """
        task_id = _create_blocked_task(engine, "Duplicate diff response task")
        stem = f"{task_id}-dup-diff"
        _write_pending_dr(board_dir, stem=stem, task_id=task_id)

        client.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "needs-info"}
        )

        assert resp.status_code == 404, (
            "Second resolve with any valid response returns 404 once file is gone from pending/"
        )


# ---------------------------------------------------------------------------
# AC8: Side effects observable immediately — no deferred sweep
# ---------------------------------------------------------------------------


class TestFromAC_ImmediateEffects:
    """AC8: All lifecycle side effects are observable immediately after the HTTP request."""

    def test_file_move_and_unblock_visible_without_sweep(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """After POST returns, both file-move and task-unblock are immediately visible.

        No background sweep, poll, or secondary trigger is needed.
        FAILS now: current implementation does neither move nor unblock, so both
        post-request checks fail against current code.
        """
        task_id = _create_blocked_task(engine, "Immediate effects task")
        stem = f"{task_id}-immediate"
        pending_path = _write_pending_dr(board_dir, stem=stem, task_id=task_id)
        resolved_path = board_dir / "decisions" / "resolved" / f"{stem}.md"

        resp = client.post(
            f"/api/decisions/{stem}/resolve", json={"response": "approved"}
        )

        # All assertions checked inline — no sweep triggered before checking
        assert resp.status_code == 200, "Request must succeed"
        assert not pending_path.exists(), "File must have moved out of pending/ immediately"
        assert resolved_path.exists(), "File must be in resolved/ immediately"
        assert not _is_task_blocked(engine, task_id), (
            "Task must be unblocked immediately — no sweep required"
        )
