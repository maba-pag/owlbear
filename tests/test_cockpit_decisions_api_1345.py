"""Failing tests for #1345: align Cockpit decision responses with DR resolver.

AC coverage:
  AC1 — POST /api/decisions/{id}/resolve accepts only approved, rejected, needs-info (td:1)
  AC2 — completed returns 422 and does not mutate the decision file (td:2)
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
    """Create a minimal board directory and return its path."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_decisions_dir(base_dir: Path) -> Path:
    """Create decisions/pending and decisions/resolved directories."""
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
    """Write a pending DR file with standard frontmatter and return its path."""
    path = decisions_dir / "pending" / f"{stem}.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: scope-decision\n"
        "created: '2026-04-30'\n"
        f"response: {response}\n"
        "---\n\n"
        f"# {stem}\n\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def _read_full(path: Path) -> str:
    """Read a file's full content as a string."""
    return path.read_text(encoding="utf-8")


def _parse_frontmatter_response(path: Path) -> str:
    """Parse only the response field from a DR file's YAML frontmatter."""
    from ruamel.yaml import YAML  # noqa: PLC0415

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_idx = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    yaml_text = "\n".join(lines[1:close_idx])
    data = YAML(typ="safe").load(yaml_text) or {}
    return str(data.get("response", ""))


@pytest.fixture
def engine(tmp_path: Path) -> KanbanEngine:
    """KanbanEngine fixture for cockpit dependency injection."""
    board_dir = _make_board(tmp_path)
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def decisions_dir(tmp_path: Path) -> Path:
    """Isolated decisions directory with pending/ and resolved/ subdirs."""
    return _make_decisions_dir(tmp_path)


@pytest.fixture
def client(engine: KanbanEngine, decisions_dir: Path):
    """FastAPI TestClient with cockpit dependency overrides."""
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


class TestFromAC_ResolveResponseEnum:
    """AC1: Only approved, rejected, needs-info accepted; completed is rejected."""

    def test_completed_response_returns_422(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """POST with response=completed returns 422 — completed is not a valid DR response.

        FAILS now: current Literal includes completed so Pydantic accepts it (200).
        """
        stem = "10-completed-rejected"
        _write_pending_dr(decisions_dir, stem=stem, task_id=10, body="Scope question.")

        response = client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed"},
        )

        assert response.status_code == 422

    def test_completed_with_notes_also_returns_422(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """POST with response=completed and notes= still returns 422 — notes do not rescue it.

        FAILS now: completed is still in the Literal, so 200 is returned.
        """
        stem = "11-completed-with-notes"
        _write_pending_dr(decisions_dir, stem=stem, task_id=11, body="Detail question.")

        response = client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed", "notes": "Done with this."},
        )

        assert response.status_code == 422


class TestFromAC_ResolveCompletedImmutability:
    """AC2: completed returns 422 AND does not mutate the decision file."""

    def test_completed_does_not_update_frontmatter_response(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """After a rejected completed POST, frontmatter response field stays 'pending'.

        FAILS now: current implementation writes 'completed' into the frontmatter.
        """
        stem = "20-frontmatter-unchanged"
        dr_path = _write_pending_dr(
            decisions_dir, stem=stem, task_id=20, body="Original question."
        )
        original_response = _parse_frontmatter_response(dr_path)
        assert original_response == "pending"

        client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed"},
        )

        assert _parse_frontmatter_response(dr_path) == "pending", (
            "Frontmatter response must remain 'pending' when completed is rejected"
        )

    def test_completed_does_not_append_response_section(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """After a rejected completed POST, no '## Response' section is appended to the file.

        FAILS now: current implementation appends the Response section even for completed.
        """
        stem = "21-no-response-section"
        dr_path = _write_pending_dr(
            decisions_dir, stem=stem, task_id=21, body="Original question body."
        )
        content_before = _read_full(dr_path)
        assert "## Response" not in content_before

        client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed"},
        )

        content_after = _read_full(dr_path)
        assert "## Response" not in content_after, (
            "No ## Response section must be appended when completed is rejected"
        )

    def test_completed_leaves_file_content_fully_unchanged(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """After a rejected completed POST, the complete file content is identical to original.

        FAILS now: current implementation rewrites the file with updated frontmatter and
        appended ## Response section, so content_after != content_before.
        """
        stem = "22-file-unchanged"
        dr_path = _write_pending_dr(
            decisions_dir, stem=stem, task_id=22, body="Immutability check body."
        )
        content_before = _read_full(dr_path)

        client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed"},
        )

        content_after = _read_full(dr_path)
        assert content_after == content_before, (
            "File content must be byte-for-byte identical when completed is rejected"
        )
