"""Failing tests for #1190: implement decisions API endpoints.

AC coverage:
  - GET /api/decisions/pending endpoint registered in Cockpit routes (td:1)
  - Reads pending/*.md files, parses frontmatter, returns structured JSON (td:2)
  - Only includes items where frontmatter response == "pending" (td:1)
  - Response shape: {count, items[{id, task_id, agent, request_type, created, title, body_preview}]} (td:1)
  - body_preview truncated to ~200 chars (td:1)
  - Returns {count:0, items:[]} when pending/ is empty or missing (td:1)
  - POST /api/decisions/{id}/resolve endpoint registered (td:1)
  - Accepts {response: enum, notes?: string} for approved/needs-info/rejected/completed (td:2)
  - Updates file: sets response in frontmatter, appends ## Response section with notes (td:2)
  - Returns 404 for non-existent DR id (td:1)
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


def _write_dr(  # noqa: PLR0913
    decisions_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str,
    response: str = "pending",
    subdir: str = "pending",
) -> Path:
    """Write a decision request file and return its path."""
    path = decisions_dir / subdir / f"{stem}.md"
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


def _parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a decision request markdown file."""
    from ruamel.yaml import YAML  # noqa: PLC0415

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_idx = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    frontmatter_text = "\n".join(lines[1:close_idx])
    return YAML(typ="safe").load(frontmatter_text) or {}


@pytest.fixture
def engine(tmp_path: Path) -> KanbanEngine:
    """KanbanEngine fixture for cockpit app dependency injection."""
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


class TestFromAC_GetPendingRegistered:
    """AC: GET /api/decisions/pending endpoint registered in Cockpit routes."""

    def test_get_pending_endpoint_exists_and_returns_200(
        self, client: TestClient
    ) -> None:
        """GET /api/decisions/pending is a registered route returning 200."""
        response = client.get("/api/decisions/pending")

        assert response.status_code == 200


class TestFromAC_GetPendingParsing:
    """AC: Reads pending/*.md files, parses frontmatter, returns structured JSON (td:2)."""

    def test_reads_pending_md_and_returns_item(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """A pending DR file is read, parsed, and returned in the items list."""
        _write_dr(
            decisions_dir, stem="10-scope-question", task_id=10, body="Need direction."
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert len(payload["items"]) == 1

    def test_non_md_files_in_pending_are_ignored(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Non-.md files in pending/ do not appear in the items list."""
        (decisions_dir / "pending" / "not-a-decision.txt").write_text(
            "---\ntask_id: 99\n---\nsome text\n", encoding="utf-8"
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_malformed_yaml_in_pending_is_skipped_not_crashed(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """A .md file with invalid YAML frontmatter is skipped; endpoint still returns 200."""
        (decisions_dir / "pending" / "bad-yaml.md").write_text(
            "---\nkey: [unclosed bracket\n---\nBody text.\n", encoding="utf-8"
        )
        _write_dr(decisions_dir, stem="11-valid-dr", task_id=11, body="Valid DR body.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        # The valid item is returned; the malformed one is skipped
        assert response.json()["count"] == 1

    def test_multiple_pending_files_all_returned(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """All pending DR files in pending/ appear in the items list."""
        _write_dr(decisions_dir, stem="20-first-dr", task_id=20, body="First question.")
        _write_dr(
            decisions_dir, stem="21-second-dr", task_id=21, body="Second question."
        )
        _write_dr(decisions_dir, stem="22-third-dr", task_id=22, body="Third question.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 3
        assert len(payload["items"]) == 3

    def test_exact_metadata_values_are_forwarded(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Returned item fields match exact frontmatter values, not just key presence."""
        # _write_dr writes task_id=10, agent="builder", request_type="scope-decision", created="2026-04-30"
        _write_dr(
            decisions_dir, stem="10-metadata-exact", task_id=10, body="Need direction."
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["task_id"] == 10
        assert item["agent"] == "builder"
        assert item["request_type"] == "scope-decision"
        assert item["created"] == "2026-04-30"


class TestFromAC_GetPendingFilter:
    """AC: Only includes items where frontmatter response == "pending" (td:1)."""

    def test_resolved_dr_in_pending_dir_is_excluded(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """A DR file in pending/ whose response field is not 'pending' is excluded."""
        _write_dr(
            decisions_dir,
            stem="30-already-approved",
            task_id=30,
            body="Already resolved.",
            response="approved",
        )
        _write_dr(
            decisions_dir, stem="31-still-pending", task_id=31, body="Still waiting."
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        # Only the item with response == "pending" appears
        assert payload["count"] == 1
        assert payload["items"][0]["id"] == "31-still-pending"

    def test_dr_with_no_response_field_is_excluded(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """A DR file with no response field in frontmatter is excluded from pending list."""
        path = decisions_dir / "pending" / "no-response-field.md"
        path.write_text(
            "---\ntask_id: 99\nagent: builder\nrequest_type: scope-decision\ncreated: '2026-04-30'\n---\n\n# No response field\n\nBody text.\n",
            encoding="utf-8",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json()["count"] == 0


class TestFromAC_GetPendingShape:
    """AC: Response shape {count, items[{id, task_id, agent, request_type, created, title, body_preview}]} (td:1)."""

    def test_item_contains_all_required_fields(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """Each item in the response has the full required field set."""
        _write_dr(
            decisions_dir, stem="40-shape-test", task_id=40, body="Shape test body."
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        required_fields = {
            "id",
            "task_id",
            "agent",
            "request_type",
            "created",
            "title",
            "body_preview",
        }
        assert required_fields.issubset(item.keys())

    def test_item_id_equals_file_stem(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """The id field in each item equals the .md file stem."""
        _write_dr(decisions_dir, stem="41-specific-stem", task_id=41, body="Stem test.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == "41-specific-stem"

    def test_count_equals_length_of_items(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """count field always equals len(items)."""
        _write_dr(decisions_dir, stem="42-count-check", task_id=42, body="Count test.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == len(payload["items"])


class TestFromAC_GetPendingBodyPreview:
    """AC: body_preview truncated to ~200 chars (td:1)."""

    def test_body_preview_is_at_most_200_chars(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """body_preview never exceeds 200 characters for long DR bodies."""
        long_body = "START-" + ("x" * 500)
        _write_dr(decisions_dir, stem="50-long-body", task_id=50, body=long_body)

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        preview = response.json()["items"][0]["body_preview"]
        assert len(preview) <= 200

    def test_body_preview_starts_from_body_content(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """body_preview content comes from the DR body, not the frontmatter."""
        _write_dr(
            decisions_dir,
            stem="51-body-source",
            task_id=51,
            body="MARKER-UNIQUE-CONTENT",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        preview = response.json()["items"][0]["body_preview"]
        assert "MARKER-UNIQUE-CONTENT" in preview


class TestFromAC_GetPendingEmpty:
    """AC: Returns {count:0, items:[]} when pending/ is empty or missing (td:1)."""

    def test_empty_pending_dir_returns_zero(self, client: TestClient) -> None:
        """An empty pending/ directory returns count=0 and empty items."""
        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json() == {"count": 0, "items": []}

    def test_missing_pending_dir_returns_zero(
        self, engine: KanbanEngine, tmp_path: Path
    ) -> None:
        """A decisions dir with no pending/ subdir returns count=0 gracefully."""
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit import deps as cockpit_deps  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        absent_decisions_dir = tmp_path / "no-such-decisions"
        absent_decisions_dir.mkdir()  # decisions/ exists but pending/ is absent

        app.dependency_overrides[get_engine] = lambda: engine
        get_decisions_dir = getattr(cockpit_deps, "get_decisions_dir", None)
        if get_decisions_dir is not None:
            app.dependency_overrides[get_decisions_dir] = lambda: absent_decisions_dir

        try:
            c = TestClient(app)
            response = c.get("/api/decisions/pending")
            assert response.status_code == 200
            assert response.json() == {"count": 0, "items": []}
        finally:
            app.dependency_overrides.clear()


class TestFromAC_PostResolveRegistered:
    """AC: POST /api/decisions/{id}/resolve endpoint registered (td:1)."""

    def test_post_resolve_endpoint_exists(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """POST /api/decisions/{id}/resolve is a registered route."""
        _write_dr(
            decisions_dir, stem="60-registered-check", task_id=60, body="Check route."
        )

        response = client.post(
            "/api/decisions/60-registered-check/resolve",
            json={"response": "approved"},
        )

        assert response.status_code == 200


class TestFromAC_PostResolveEnum:
    """AC: Accepts {response: enum, notes?: string} — all four valid values (td:2)."""

    @pytest.mark.parametrize(
        "resolution", ["approved", "needs-info", "rejected", "completed"]
    )
    def test_each_valid_enum_value_is_accepted(
        self, client: TestClient, decisions_dir: Path, resolution: str
    ) -> None:
        """Each valid response enum value returns 200."""
        stem = f"70-enum-{resolution.replace('-', '_')}"
        _write_dr(decisions_dir, stem=stem, task_id=70, body="Enum validation test.")

        response = client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": resolution},
        )

        assert response.status_code == 200

    def test_invalid_enum_value_returns_422(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """An unrecognised response value is rejected with 422 Unprocessable Entity."""
        _write_dr(decisions_dir, stem="71-bad-enum", task_id=71, body="Bad enum test.")

        response = client.post(
            "/api/decisions/71-bad-enum/resolve",
            json={"response": "not-a-valid-status"},
        )

        assert response.status_code == 422

    def test_notes_field_is_optional(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """POST body without a notes key is accepted as valid."""
        _write_dr(
            decisions_dir, stem="72-no-notes", task_id=72, body="Notes optional test."
        )

        response = client.post(
            "/api/decisions/72-no-notes/resolve",
            json={"response": "approved"},  # notes deliberately absent
        )

        assert response.status_code == 200

    def test_notes_field_accepts_empty_string(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """notes as an empty string is accepted (not a validation error)."""
        _write_dr(
            decisions_dir, stem="73-empty-notes", task_id=73, body="Empty notes test."
        )

        response = client.post(
            "/api/decisions/73-empty-notes/resolve",
            json={"response": "approved", "notes": ""},
        )

        assert response.status_code == 200


class TestFromAC_PostResolvePersistence:
    """AC: Updates file — sets response in frontmatter, appends ## Response section (td:2)."""

    def test_response_field_updated_in_frontmatter(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """After resolve, the frontmatter response field matches the submitted value."""
        _write_dr(
            decisions_dir,
            stem="80-fm-update",
            task_id=80,
            body="Frontmatter update test.",
        )

        client.post(
            "/api/decisions/80-fm-update/resolve",
            json={"response": "needs-info", "notes": "More context required."},
        )

        dr_path = decisions_dir / "pending" / "80-fm-update.md"
        frontmatter = _parse_frontmatter(dr_path)
        assert frontmatter["response"] == "needs-info"

    def test_response_section_appended_with_notes(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """After resolve, the file contains a ## Response section with the supplied notes."""
        _write_dr(
            decisions_dir, stem="81-response-section", task_id=81, body="Section test."
        )

        client.post(
            "/api/decisions/81-response-section/resolve",
            json={"response": "rejected", "notes": "Out of scope for this sprint."},
        )

        content = (decisions_dir / "pending" / "81-response-section.md").read_text(
            encoding="utf-8"
        )
        assert "## Response" in content
        assert "Out of scope for this sprint." in content

    def test_response_section_appended_even_without_notes(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """## Response section appears even when notes is not supplied."""
        _write_dr(
            decisions_dir, stem="82-no-notes-section", task_id=82, body="No notes test."
        )

        client.post(
            "/api/decisions/82-no-notes-section/resolve",
            json={"response": "approved"},
        )

        content = (decisions_dir / "pending" / "82-no-notes-section.md").read_text(
            encoding="utf-8"
        )
        assert "## Response" in content

    def test_original_body_is_preserved_after_resolve(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """The original DR body content is not lost after resolve."""
        unique_marker = "ORIGINAL-BODY-MARKER-XYZ"
        _write_dr(
            decisions_dir, stem="83-body-preserved", task_id=83, body=unique_marker
        )

        resp = client.post(
            "/api/decisions/83-body-preserved/resolve",
            json={"response": "completed", "notes": "Done."},
        )
        assert resp.status_code == 200  # proves route is registered; fails in RED

        content = (decisions_dir / "pending" / "83-body-preserved.md").read_text(
            encoding="utf-8"
        )
        assert unique_marker in content

    def test_response_section_appended_after_original_body(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """## Response section appears after original body, not before it."""
        body_marker = "ORIGINAL-BODY-MARKER-84"
        _write_dr(decisions_dir, stem="84-ordering-check", task_id=84, body=body_marker)

        client.post(
            "/api/decisions/84-ordering-check/resolve",
            json={"response": "approved", "notes": "Ordering check."},
        )

        content = (decisions_dir / "pending" / "84-ordering-check.md").read_text(
            encoding="utf-8"
        )
        assert body_marker in content
        assert "## Response" in content
        assert content.index(body_marker) < content.index("## Response")


class TestFromAC_PostResolveNotFound:
    """AC: Returns 404 for non-existent DR id (td:1)."""

    def test_unknown_decision_id_returns_404(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """POST to a non-existent decision id returns 404 Not Found."""
        # First verify the route is registered (fails in RED if route missing).
        _write_dr(decisions_dir, stem="90-exists", task_id=90, body="Exists.")
        assert (
            client.post(
                "/api/decisions/90-exists/resolve", json={"response": "approved"}
            ).status_code
            == 200
        )

        response = client.post(
            "/api/decisions/does-not-exist-anywhere/resolve",
            json={"response": "approved"},
        )

        assert response.status_code == 404
