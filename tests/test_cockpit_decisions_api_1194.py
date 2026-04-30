"""Failing tests for #1194: P3-06 Implement resolve modal — backend body field enrichment.

AC coverage:
  ac1-body-field    — GET /api/decisions/pending items include 'body' field (full markdown text)
  ac1-body-content  — 'body' field matches the full DR markdown body (not just a preview)
  ac1-not-truncated — 'body' is NOT truncated at 200 chars (unlike 'body_preview')

All tests FAIL (RED phase) — list_pending_decisions currently returns only 'body_preview',
not the full 'body'. The builder must add 'body' to the response payload.
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


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_decisions_dir(base_dir: Path) -> Path:
    decisions_dir = base_dir / "decisions"
    (decisions_dir / "pending").mkdir(parents=True)
    (decisions_dir / "resolved").mkdir(parents=True)
    return decisions_dir


def _write_pending_dr(
    decisions_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str,
    response: str = "pending",
) -> Path:
    path = decisions_dir / "pending" / f"{stem}.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: scope-decision\n"
        "created: '2026-04-30'\n"
        f"response: {response}\n"
        "---\n\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def engine(tmp_path: Path) -> KanbanEngine:
    board_dir = _make_board(tmp_path)
    eng = KanbanEngine(board_dir, agent_name="cockpit")
    eng.list_tasks()
    return eng


@pytest.fixture
def decisions_dir(tmp_path: Path) -> Path:
    return _make_decisions_dir(tmp_path)


@pytest.fixture
def client(engine: KanbanEngine, decisions_dir: Path):
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit import deps as cockpit_deps  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine

    get_decisions_dir = getattr(cockpit_deps, "get_decisions_dir", None)
    if get_decisions_dir is not None:
        app.dependency_overrides[get_decisions_dir] = lambda: decisions_dir

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestFromAC_PendingDecisionsBodyField:
    """AC1: GET /api/decisions/pending items must include full 'body' field."""

    def test_pending_item_includes_body_field(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """AC1 smoke: each item in the pending response has a 'body' key."""
        _write_pending_dr(
            decisions_dir,
            stem="42-scope-decision",
            task_id=42,
            body="## Context\n\nShould we include feature X?",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "body" in item, (
            f"Pending item must include 'body' field; got keys: {sorted(item.keys())}"
        )

    def test_body_field_matches_full_markdown_body(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """AC1 happy: 'body' contains the full markdown body, not a preview or empty string."""
        body_text = "## Context\n\nShould we include feature X?\n\n## Options\n\n1. Yes\n2. No"
        _write_pending_dr(
            decisions_dir,
            stem="42-scope-decision",
            task_id=42,
            body=body_text,
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "body" in item, f"Item missing 'body'; got {sorted(item.keys())}"
        assert item["body"].strip() == body_text.strip(), (
            f"'body' must be the full markdown body text; "
            f"expected {body_text!r}, got {item['body']!r}"
        )

    def test_body_not_truncated_unlike_body_preview(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """AC1 boundary: 'body' is NOT truncated at 200 chars (body_preview is limited to ~200)."""
        long_body = "## Context\n\n" + ("A very long description that goes on and on. " * 10)
        assert len(long_body) > 200, "Precondition: test body must exceed 200 chars"
        _write_pending_dr(
            decisions_dir,
            stem="42-scope-decision",
            task_id=42,
            body=long_body,
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "body" in item, f"Item missing 'body'; got {sorted(item.keys())}"
        assert len(item["body"].strip()) > 200, (
            f"'body' must contain the full text (> 200 chars), not truncated like body_preview; "
            f"got {len(item.get('body', ''))} chars"
        )
        assert item["body"].strip() == long_body.strip(), (
            "'body' must be the COMPLETE body text, not a truncated preview"
        )
