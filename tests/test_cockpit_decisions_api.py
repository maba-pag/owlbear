"""Durable tests for cockpit decisions API coverage.

Promoted from archived task-scoped suites for #1189, #1190, and #1194.
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
    """Write a decision request file into pending/ and return its path."""
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


def _parse_frontmatter(path: Path) -> dict[str, object]:
    """Parse YAML frontmatter from a decision request markdown file."""
    from ruamel.yaml import YAML

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_idx = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    frontmatter_text = "\n".join(lines[1:close_idx])
    return YAML(typ="safe").load(frontmatter_text) or {}


def _find_dr_file(decisions_dir: Path, decision_id: str) -> Path:
    """Return the current DR file path from pending/ or resolved/."""
    pending = decisions_dir / "pending" / f"{decision_id}.md"
    if pending.exists():
        return pending
    return decisions_dir / "resolved" / f"{decision_id}.md"


@pytest.fixture
def engine(tmp_path: Path) -> KanbanEngine:
    """KanbanEngine fixture for cockpit dependency injection."""
    board_dir = _make_board(tmp_path)
    eng = KanbanEngine(board_dir, agent_name="cockpit")
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


class TestFromAC_PendingDecisions:
    """Durable coverage for GET /api/decisions/pending."""

    def test_pending_returns_count_and_required_fields_including_body(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Pending response includes durable field set and count matches items."""
        _write_pending_dr(
            decisions_dir,
            stem="42-awaiting-approval",
            task_id=42,
            body="# Decision\nShould we proceed with option A?",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == len(payload["items"]) == 1
        item = payload["items"][0]
        required_fields = {
            "id",
            "task_id",
            "agent",
            "request_type",
            "created",
            "title",
            "body",
            "body_preview",
        }
        assert required_fields.issubset(item.keys())
        assert item["id"] == "42-awaiting-approval"
        assert item["title"] == "Decision"

    def test_pending_ignores_non_pending_and_malformed_files(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Pending list skips malformed files, non-markdown files, and resolved DRs."""
        _write_pending_dr(
            decisions_dir,
            stem="30-already-approved",
            task_id=30,
            body="# Decision\nAlready resolved.",
            response="approved",
        )
        _write_pending_dr(
            decisions_dir,
            stem="31-still-pending",
            task_id=31,
            body="# Decision\nStill waiting.",
        )
        (decisions_dir / "pending" / "bad-yaml.md").write_text(
            "---\nkey: [unclosed bracket\n---\nBody text.\n",
            encoding="utf-8",
        )
        (decisions_dir / "pending" / "not-a-decision.txt").write_text(
            "ignored", encoding="utf-8"
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["items"][0]["id"] == "31-still-pending"

    def test_pending_body_and_preview_preserve_full_markdown(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Pending list returns full body and truncated preview from the same markdown."""
        body = "## Context\n\n" + ("A very long description that goes on and on. " * 10)
        assert len(body) > 200
        _write_pending_dr(
            decisions_dir,
            stem="50-long-body",
            task_id=50,
            body=body,
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        expected_body = body.strip()
        assert item["body"] == expected_body
        assert item["body_preview"] == expected_body[:200]
        assert len(item["body_preview"]) <= 200
        assert item["body"].startswith(item["body_preview"])

    def test_pending_empty_returns_zero_and_empty_items(
        self, client: TestClient
    ) -> None:
        """Empty pending directory returns the empty response shape."""
        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json() == {"count": 0, "items": []}

    def test_missing_pending_dir_returns_zero_and_empty_items(
        self, engine: KanbanEngine, tmp_path: Path
    ) -> None:
        """Missing pending/ subdir returns the same empty response shape."""
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit import deps as cockpit_deps  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        absent_decisions_dir = tmp_path / "no-such-decisions"
        absent_decisions_dir.mkdir()

        app.dependency_overrides[get_engine] = lambda: engine
        get_decisions_dir = getattr(cockpit_deps, "get_decisions_dir", None)
        if get_decisions_dir is not None:
            app.dependency_overrides[get_decisions_dir] = lambda: absent_decisions_dir

        try:
            response = TestClient(app).get("/api/decisions/pending")
            assert response.status_code == 200
            assert response.json() == {"count": 0, "items": []}
        finally:
            app.dependency_overrides.clear()


class TestFromAC_ResolveDecisions:
    """Durable coverage for POST /api/decisions/{id}/resolve."""

    @pytest.mark.parametrize(
        ("resolution", "notes"),
        [
            ("approved", "Looks good."),
            ("needs-info", None),
            ("rejected", "Not aligned with scope."),
            ("completed", "Implemented as requested."),
        ],
    )
    def test_resolve_accepts_valid_responses_and_optional_notes(
        self,
        client: TestClient,
        decisions_dir: Path,
        resolution: str,
        notes: str | None,
    ) -> None:
        """Resolve accepts each enum value and allows notes to be omitted."""
        decision_id = f"42-awaiting-approval-{resolution}"
        _write_pending_dr(
            decisions_dir,
            stem=decision_id,
            task_id=42,
            body="# Question\nApprove this decision?",
        )

        payload = {"response": resolution}
        if notes is not None:
            payload["notes"] = notes

        response = client.post(f"/api/decisions/{decision_id}/resolve", json=payload)

        assert response.status_code == 200

    def test_resolve_updates_frontmatter_and_appends_response_section(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Resolve persists the response value and appends a markdown response section."""
        decision_id = "55-needs-triage"
        _write_pending_dr(
            decisions_dir,
            stem=decision_id,
            task_id=55,
            body="# Context\nNeed direction before proceeding.",
        )

        response = client.post(
            f"/api/decisions/{decision_id}/resolve",
            json={"response": "rejected", "notes": "Not aligned with scope."},
        )

        assert response.status_code == 200
        dr_path = _find_dr_file(decisions_dir, decision_id)
        assert dr_path.exists()
        assert _parse_frontmatter(dr_path)["response"] == "rejected"
        content = dr_path.read_text(encoding="utf-8")
        assert "## Response" in content
        assert "Not aligned with scope." in content

    def test_resolve_preserves_original_body_before_response_section(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Resolve keeps the original body intact and appends the response at the end."""
        decision_id = "84-ordering-check"
        body_marker = "ORIGINAL-BODY-MARKER-84"
        _write_pending_dr(
            decisions_dir,
            stem=decision_id,
            task_id=84,
            body=f"# Context\n\n{body_marker}",
        )

        response = client.post(
            f"/api/decisions/{decision_id}/resolve",
            json={"response": "approved", "notes": "Ordering check."},
        )

        assert response.status_code == 200
        content = _find_dr_file(decisions_dir, decision_id).read_text(encoding="utf-8")
        assert body_marker in content
        assert "## Response" in content
        assert content.index(body_marker) < content.index("## Response")

    def test_resolve_rejects_invalid_response_enum(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Resolve rejects unknown response enum values with 422."""
        decision_id = "77-invalid-enum"
        _write_pending_dr(
            decisions_dir,
            stem=decision_id,
            task_id=77,
            body="# Question\nWhich option should we choose?",
        )

        response = client.post(
            f"/api/decisions/{decision_id}/resolve",
            json={"response": "invalid-status"},
        )

        assert response.status_code == 422

    def test_resolve_returns_404_for_unknown_decision_id(
        self, client: TestClient
    ) -> None:
        """Resolve returns 404 when the decision file does not exist."""
        response = client.post(
            "/api/decisions/not-a-real-id/resolve",
            json={"response": "approved"},
        )

        assert response.status_code == 404
