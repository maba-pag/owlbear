"""Durable tests for cockpit decisions API coverage.

Promoted from archived task-scoped suites for #1189, #1190, #1194, #1345,
#1384, and #1385.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


_CONFIG_YAML = """\
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


def _read_full(path: Path) -> str:
    """Read a file's full content as a string."""
    return path.read_text(encoding="utf-8")


def _parse_frontmatter_response(path: Path) -> str:
    """Parse only the response field from a DR file's YAML frontmatter."""
    from ruamel.yaml import YAML

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_idx = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    yaml_text = "\n".join(lines[1:close_idx])
    data = YAML(typ="safe").load(yaml_text) or {}
    return str(data.get("response", ""))


def _make_board_pattern_b(board_dir: Path) -> None:
    """Write minimal board files into *board_dir* with in-board decisions dirs."""
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board_dir / "tasks").mkdir(exist_ok=True)
    (board_dir / "archive").mkdir(exist_ok=True)
    (board_dir / "decisions" / "pending").mkdir(parents=True)
    (board_dir / "decisions" / "resolved").mkdir(parents=True)


def _write_pending_dr_pattern_b(
    board_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str = "What should we do?",
    response: str = "pending",
) -> Path:
    """Write a DR file to pending/ and return its path (Pattern B)."""
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


def _write_resolved_dr_pattern_b(
    board_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str = "What should we do?",
    response: str = "approved",
) -> Path:
    """Write a DR file directly to resolved/ (Pattern B)."""
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


@pytest.fixture
def board_dir_pattern_b(tmp_path: Path) -> Path:
    """Return an isolated board directory with decisions/ pre-created."""
    board = tmp_path / "board"
    _make_board_pattern_b(board)
    return board


@pytest.fixture
def engine_pattern_b(board_dir_pattern_b: Path) -> KanbanEngine:
    """KanbanEngine backed by in-board decisions directory (Pattern B)."""
    eng = KanbanEngine(board_dir_pattern_b)
    eng.list_tasks()
    return eng


@pytest.fixture
def client_pattern_b(engine_pattern_b: KanbanEngine):
    """FastAPI TestClient with engine override only (Pattern B)."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine_pattern_b
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _create_blocked_task_pattern_b(engine: KanbanEngine, title: str) -> int:
    """Create a task and block it immediately; return integer task ID."""
    task = engine.create_task(title)
    engine.edit_task(task.id, blocked=True, block_reason="DR pending")
    engine.list_tasks()
    return task.id


def _read_task_body_pattern_b(engine: KanbanEngine, task_id: int) -> str:
    """Return current task body after cache refresh."""
    engine.list_tasks()
    return engine.show_task(str(task_id)).body


def _is_task_blocked_pattern_b(engine: KanbanEngine, task_id: int) -> bool:
    """Return True when the task remains blocked on disk."""
    engine.list_tasks()
    return bool(engine.show_task(str(task_id)).blocked)


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

    def test_pending_ignores_non_pending_and_malformed_files(self, client: TestClient, decisions_dir: Path) -> None:
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
        (decisions_dir / "pending" / "not-a-decision.txt").write_text("ignored", encoding="utf-8")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["items"][0]["id"] == "31-still-pending"

    def test_pending_body_and_preview_preserve_full_markdown(self, client: TestClient, decisions_dir: Path) -> None:
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

    def test_pending_plain_paragraph_title_is_not_entire_request(
        self,
        client: TestClient,
        decisions_dir: Path,
    ) -> None:
        """Plain decision paragraphs get a compact title while body/preview stay intact."""
        body = (
            "Decision needed later: choose ownership model for knowledge source lifecycle after #1556 "
            "and #1557 complete. Default should be continue with the current owner until the lifecycle "
            "flow is explicit."
        )
        _write_pending_dr(
            decisions_dir,
            stem="1558-decision",
            task_id=1558,
            body=body,
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["title"] == "Choose ownership model for knowledge source lifecycle"
        assert item["body"] == body
        assert item["body_preview"] == body[:200]

    def test_pending_empty_returns_zero_and_empty_items(self, client: TestClient) -> None:
        """Empty pending directory returns the empty response shape."""
        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json() == {"count": 0, "items": []}

    def test_missing_pending_dir_returns_zero_and_empty_items(self, engine: KanbanEngine, tmp_path: Path) -> None:
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

    def test_resolve_rejects_invalid_response_enum(self, client: TestClient, decisions_dir: Path) -> None:
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

    def test_resolve_returns_404_for_unknown_decision_id(self, client: TestClient) -> None:
        """Resolve returns 404 when the decision file does not exist."""
        response = client.post(
            "/api/decisions/not-a-real-id/resolve",
            json={"response": "approved"},
        )

        assert response.status_code == 404


class TestFromAC_DecisionsPending:
    """Coverage promoted from task #1189 for GET /api/decisions/pending."""

    def test_pending_returns_count_and_items(self, client: TestClient, decisions_dir: Path) -> None:
        _write_pending_dr(
            decisions_dir,
            stem="42-awaiting-approval",
            task_id=42,
            body="# Question\nShould we proceed with option A?",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload.get("count"), int)
        assert isinstance(payload.get("items"), list)
        assert payload["count"] == len(payload["items"]) == 1

    def test_pending_item_shape(self, client: TestClient, decisions_dir: Path) -> None:
        _write_pending_dr(
            decisions_dir,
            stem="7-clarify-scope",
            task_id=7,
            body="# Decision: clarify scope\nDetails go here.",
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

    def test_body_preview_is_truncated_to_around_200_chars(
        self,
        client: TestClient,
        decisions_dir: Path,
    ) -> None:
        unique_prefix = "# Long request\nTOKEN-START-"
        long_body = unique_prefix + ("lorem ipsum dolor sit amet " * 30)
        _write_pending_dr(
            decisions_dir,
            stem="8-long-body",
            task_id=8,
            body=long_body,
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        preview = response.json()["items"][0]["body_preview"]
        assert isinstance(preview, str)
        assert preview
        assert long_body.startswith(preview)
        assert preview.startswith(unique_prefix)
        assert len(preview) <= 200

    def test_pending_empty_returns_zero_and_empty_items_1189(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json() == {"count": 0, "items": []}


class TestFromAC_DecisionsResolve:
    """Coverage promoted from task #1189 for POST /api/decisions/{id}/resolve."""

    @pytest.mark.parametrize(
        ("resolution", "notes"),
        [
            ("approved", "Looks good."),
            ("needs-info", None),
            ("rejected", "Not aligned with scope."),
        ],
    )
    def test_resolve_accepts_response_enum_and_optional_notes(
        self,
        client: TestClient,
        decisions_dir: Path,
        resolution: str,
        notes: str | None,
    ) -> None:
        decision_id = f"42-awaiting-approval-{resolution}"
        _write_pending_dr(
            decisions_dir,
            stem=decision_id,
            task_id=42,
            body="# Question\nApprove this decision?",
        )

        payload: dict[str, str] = {"response": resolution}
        if notes is not None:
            payload["notes"] = notes

        response = client.post(
            f"/api/decisions/{decision_id}/resolve",
            json=payload,
        )

        assert response.status_code == 200

    def test_resolve_updates_response_field_and_appends_response_section(
        self,
        client: TestClient,
        decisions_dir: Path,
    ) -> None:
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
        assert dr_path.exists(), "Resolved endpoint must persist an updated DR file"
        frontmatter = _parse_frontmatter(dr_path)
        assert frontmatter["response"] == "rejected"

        content = dr_path.read_text(encoding="utf-8")
        assert "## Response" in content
        assert "Not aligned with scope." in content

    def test_resolve_returns_404_for_unknown_decision_id_1189(self, client: TestClient) -> None:
        response = client.post(
            "/api/decisions/not-a-real-id/resolve",
            json={"response": "approved"},
        )

        assert response.status_code == 404

    def test_resolve_rejects_invalid_response_enum_1189(
        self,
        client: TestClient,
        decisions_dir: Path,
    ) -> None:
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


class TestFromAC_GetPendingRegistered:
    """AC: GET /api/decisions/pending endpoint registered in Cockpit routes."""

    def test_get_pending_endpoint_exists_and_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/decisions/pending")

        assert response.status_code == 200


class TestFromAC_GetPendingParsing:
    """AC: Parses pending/*.md files and returns structured JSON."""

    def test_reads_pending_md_and_returns_item(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="10-scope-question", task_id=10, body="Need direction.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert len(payload["items"]) == 1

    def test_non_md_files_in_pending_are_ignored(self, client: TestClient, decisions_dir: Path) -> None:
        (decisions_dir / "pending" / "not-a-decision.txt").write_text(
            "---\ntask_id: 99\n---\nsome text\n", encoding="utf-8"
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_malformed_yaml_in_pending_is_skipped_not_crashed(self, client: TestClient, decisions_dir: Path) -> None:
        (decisions_dir / "pending" / "bad-yaml.md").write_text(
            "---\nkey: [unclosed bracket\n---\nBody text.\n", encoding="utf-8"
        )
        _write_dr(decisions_dir, stem="11-valid-dr", task_id=11, body="Valid DR body.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_multiple_pending_files_all_returned(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="20-first-dr", task_id=20, body="First question.")
        _write_dr(decisions_dir, stem="21-second-dr", task_id=21, body="Second question.")
        _write_dr(decisions_dir, stem="22-third-dr", task_id=22, body="Third question.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 3
        assert len(payload["items"]) == 3

    def test_exact_metadata_values_are_forwarded(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="10-metadata-exact", task_id=10, body="Need direction.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["task_id"] == 10
        assert item["agent"] == "builder"
        assert item["request_type"] == "scope-decision"
        assert item["created"] == "2026-04-30"


class TestFromAC_GetPendingFilter:
    """AC: Only includes items where frontmatter response == pending."""

    def test_resolved_dr_in_pending_dir_is_excluded(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(
            decisions_dir,
            stem="30-already-approved",
            task_id=30,
            body="Already resolved.",
            response="approved",
        )
        _write_dr(decisions_dir, stem="31-still-pending", task_id=31, body="Still waiting.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["items"][0]["id"] == "31-still-pending"

    def test_dr_with_no_response_field_is_excluded(self, client: TestClient, decisions_dir: Path) -> None:
        path = decisions_dir / "pending" / "no-response-field.md"
        path.write_text(
            "---\ntask_id: 99\nagent: builder\nrequest_type: scope-decision\ncreated: '2026-04-30'\n---\n\n# No response field\n\nBody text.\n",
            encoding="utf-8",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json()["count"] == 0


class TestFromAC_GetPendingShape:
    """AC: Response shape with required pending decision fields."""

    def test_item_contains_all_required_fields(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="40-shape-test", task_id=40, body="Shape test body.")

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

    def test_item_id_equals_file_stem(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="41-specific-stem", task_id=41, body="Stem test.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == "41-specific-stem"

    def test_count_equals_length_of_items(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="42-count-check", task_id=42, body="Count test.")

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == len(payload["items"])


class TestFromAC_GetPendingBodyPreview:
    """AC: body_preview truncation behavior."""

    def test_body_preview_is_at_most_200_chars(self, client: TestClient, decisions_dir: Path) -> None:
        long_body = "START-" + ("x" * 500)
        _write_dr(decisions_dir, stem="50-long-body", task_id=50, body=long_body)

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        preview = response.json()["items"][0]["body_preview"]
        assert len(preview) <= 200

    def test_body_preview_starts_from_body_content(self, client: TestClient, decisions_dir: Path) -> None:
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
    """AC: Empty or missing pending directory response shape."""

    def test_empty_pending_dir_returns_zero(self, client: TestClient) -> None:
        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        assert response.json() == {"count": 0, "items": []}

    def test_missing_pending_dir_returns_zero(self, engine: KanbanEngine, tmp_path: Path) -> None:
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
            c = TestClient(app)
            response = c.get("/api/decisions/pending")
            assert response.status_code == 200
            assert response.json() == {"count": 0, "items": []}
        finally:
            app.dependency_overrides.clear()


class TestFromAC_PostResolveRegistered:
    """AC: POST /api/decisions/{id}/resolve endpoint registration."""

    def test_post_resolve_endpoint_exists(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="60-registered-check", task_id=60, body="Check route.")

        response = client.post(
            "/api/decisions/60-registered-check/resolve",
            json={"response": "approved"},
        )

        assert response.status_code == 200


class TestFromAC_PostResolveEnum:
    """AC: Valid and invalid resolve response enum handling."""

    @pytest.mark.parametrize("resolution", ["approved", "needs-info", "rejected"])
    def test_each_valid_enum_value_is_accepted(self, client: TestClient, decisions_dir: Path, resolution: str) -> None:
        stem = f"70-enum-{resolution.replace('-', '_')}"
        _write_dr(decisions_dir, stem=stem, task_id=70, body="Enum validation test.")

        response = client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": resolution},
        )

        assert response.status_code == 200

    def test_invalid_enum_value_returns_422(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="71-bad-enum", task_id=71, body="Bad enum test.")

        response = client.post(
            "/api/decisions/71-bad-enum/resolve",
            json={"response": "not-a-valid-status"},
        )

        assert response.status_code == 422

    def test_notes_field_is_optional(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="72-no-notes", task_id=72, body="Notes optional test.")

        response = client.post(
            "/api/decisions/72-no-notes/resolve",
            json={"response": "approved"},
        )

        assert response.status_code == 200

    def test_notes_field_accepts_empty_string(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="73-empty-notes", task_id=73, body="Empty notes test.")

        response = client.post(
            "/api/decisions/73-empty-notes/resolve",
            json={"response": "approved", "notes": ""},
        )

        assert response.status_code == 200


class TestFromAC_PostResolvePersistence:
    """AC: Resolve persistence and response section behavior."""

    def test_response_field_updated_in_frontmatter(self, client: TestClient, decisions_dir: Path) -> None:
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

        dr_path = decisions_dir / "resolved" / "80-fm-update.md"
        frontmatter = _parse_frontmatter(dr_path)
        assert frontmatter["response"] == "needs-info"

    def test_response_section_appended_with_notes(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="81-response-section", task_id=81, body="Section test.")

        client.post(
            "/api/decisions/81-response-section/resolve",
            json={"response": "rejected", "notes": "Out of scope for this sprint."},
        )

        content = (decisions_dir / "resolved" / "81-response-section.md").read_text(encoding="utf-8")
        assert "## Response" in content
        assert "Out of scope for this sprint." in content

    def test_response_section_appended_even_without_notes(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="82-no-notes-section", task_id=82, body="No notes test.")

        client.post(
            "/api/decisions/82-no-notes-section/resolve",
            json={"response": "approved"},
        )

        content = (decisions_dir / "resolved" / "82-no-notes-section.md").read_text(encoding="utf-8")
        assert "## Response" in content

    def test_original_body_is_preserved_after_resolve(self, client: TestClient, decisions_dir: Path) -> None:
        unique_marker = "ORIGINAL-BODY-MARKER-XYZ"
        _write_dr(decisions_dir, stem="83-body-preserved", task_id=83, body=unique_marker)

        resp = client.post(
            "/api/decisions/83-body-preserved/resolve",
            json={"response": "approved", "notes": "Approved."},
        )
        assert resp.status_code == 200

        content = (decisions_dir / "resolved" / "83-body-preserved.md").read_text(encoding="utf-8")
        assert unique_marker in content

    def test_response_section_appended_after_original_body(self, client: TestClient, decisions_dir: Path) -> None:
        body_marker = "ORIGINAL-BODY-MARKER-84"
        _write_dr(decisions_dir, stem="84-ordering-check", task_id=84, body=body_marker)

        client.post(
            "/api/decisions/84-ordering-check/resolve",
            json={"response": "approved", "notes": "Ordering check."},
        )

        content = (decisions_dir / "resolved" / "84-ordering-check.md").read_text(encoding="utf-8")
        assert body_marker in content
        assert "## Response" in content
        assert content.index(body_marker) < content.index("## Response")


class TestFromAC_PostResolveNotFound:
    """AC: 404 behavior for unknown decision IDs."""

    def test_unknown_decision_id_returns_404(self, client: TestClient, decisions_dir: Path) -> None:
        _write_dr(decisions_dir, stem="90-exists", task_id=90, body="Exists.")
        assert client.post("/api/decisions/90-exists/resolve", json={"response": "approved"}).status_code == 200

        response = client.post(
            "/api/decisions/does-not-exist-anywhere/resolve",
            json={"response": "approved"},
        )

        assert response.status_code == 404


class TestFromAC_PendingDecisionsBodyField:
    """Coverage promoted from #1194 for full body field behavior."""

    def test_pending_item_includes_body_field(self, client: TestClient, decisions_dir: Path) -> None:
        _write_pending_dr(
            decisions_dir,
            stem="42-scope-decision",
            task_id=42,
            body="## Context\n\nShould we include feature X?",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "body" in item, f"Pending item must include 'body' field; got keys: {sorted(item.keys())}"

    def test_body_field_matches_full_markdown_body(self, client: TestClient, decisions_dir: Path) -> None:
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
            f"'body' must be the full markdown body text; expected {body_text!r}, got {item['body']!r}"
        )

    def test_body_not_truncated_unlike_body_preview(self, client: TestClient, decisions_dir: Path) -> None:
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


class TestFromAC_ResolveResponseEnum:
    """Coverage promoted from #1345 for completed enum rejection."""

    def test_completed_response_returns_422(self, client: TestClient, decisions_dir: Path) -> None:
        stem = "10-completed-rejected"
        _write_pending_dr(decisions_dir, stem=stem, task_id=10, body="Scope question.")

        response = client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed"},
        )

        assert response.status_code == 422

    def test_completed_with_notes_also_returns_422(self, client: TestClient, decisions_dir: Path) -> None:
        stem = "11-completed-with-notes"
        _write_pending_dr(decisions_dir, stem=stem, task_id=11, body="Detail question.")

        response = client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed", "notes": "Done with this."},
        )

        assert response.status_code == 422


class TestFromAC_ResolveCompletedImmutability:
    """Coverage promoted from #1345 for rejected-completed immutability."""

    def test_completed_does_not_update_frontmatter_response(self, client: TestClient, decisions_dir: Path) -> None:
        stem = "20-frontmatter-unchanged"
        dr_path = _write_pending_dr(decisions_dir, stem=stem, task_id=20, body="Original question.")
        original_response = _parse_frontmatter_response(dr_path)
        assert original_response == "pending"

        client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed"},
        )

        assert _parse_frontmatter_response(dr_path) == "pending", (
            "Frontmatter response must remain 'pending' when completed is rejected"
        )

    def test_completed_does_not_append_response_section(self, client: TestClient, decisions_dir: Path) -> None:
        stem = "21-no-response-section"
        dr_path = _write_pending_dr(decisions_dir, stem=stem, task_id=21, body="Original question body.")
        content_before = _read_full(dr_path)
        assert "## Response" not in content_before

        client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed"},
        )

        content_after = _read_full(dr_path)
        assert "## Response" not in content_after, "No ## Response section must be appended when completed is rejected"

    def test_completed_leaves_file_content_fully_unchanged(self, client: TestClient, decisions_dir: Path) -> None:
        stem = "22-file-unchanged"
        dr_path = _write_pending_dr(decisions_dir, stem=stem, task_id=22, body="Immutability check body.")
        content_before = _read_full(dr_path)

        client.post(
            f"/api/decisions/{stem}/resolve",
            json={"response": "completed"},
        )

        content_after = _read_full(dr_path)
        assert content_after == content_before, (
            "File content must be byte-for-byte identical when completed is rejected"
        )


class TestFromAC_ApprovedResolution:
    """Coverage promoted from #1384 for approved resolution lifecycle."""

    def test_approve_moves_dr_from_pending_to_resolved(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Approve move task")
        stem = f"{task_id}-scope-decision"
        pending_path = _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert not pending_path.exists(), "DR file must be removed from pending/ after approval"

    def test_approve_places_dr_in_resolved(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Approve to resolved task")
        stem = f"{task_id}-scope-resolved"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)
        resolved_path = board_dir_pattern_b / "decisions" / "resolved" / f"{stem}.md"

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert resolved_path.exists(), "DR file must appear in resolved/ after approval"

    def test_approve_unblocks_the_associated_task(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Approve unblock task")
        stem = f"{task_id}-scope-unblock"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)
        assert _is_task_blocked_pattern_b(engine_pattern_b, task_id)

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert not _is_task_blocked_pattern_b(engine_pattern_b, task_id), "Task must be unblocked after approval"

    def test_approve_appends_canonical_summary_to_task_body(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Approve summary task")
        stem = f"{task_id}-scope-summary"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id, body="Summary body text.")

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        body = _read_task_body_pattern_b(engine_pattern_b, task_id)
        assert "## Decision Request" in body
        assert "approved" in body

    def test_approve_response_body_shape(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Approve response shape task")
        stem = f"{task_id}-approve-shape"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"id": stem, "response": "approved"}

    def test_approve_summary_includes_source_line(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Approve source line task")
        stem = f"{task_id}-approve-source"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id, body="Decide the scope.")

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        body = _read_task_body_pattern_b(engine_pattern_b, task_id)
        assert "- source:" in body


class TestFromAC_RejectedResolution:
    """Coverage promoted from #1384 for rejected resolution lifecycle."""

    def test_reject_moves_dr_from_pending_to_resolved(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Reject move task")
        stem = f"{task_id}-reject-move"
        pending_path = _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert not pending_path.exists(), "DR file must be removed from pending/ after rejection"

    def test_reject_places_dr_in_resolved(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Reject to resolved task")
        stem = f"{task_id}-reject-resolved"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)
        resolved_path = board_dir_pattern_b / "decisions" / "resolved" / f"{stem}.md"

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert resolved_path.exists(), "DR file must appear in resolved/ after rejection"

    def test_reject_unblocks_the_associated_task(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Reject unblock task")
        stem = f"{task_id}-reject-unblock"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert not _is_task_blocked_pattern_b(engine_pattern_b, task_id), "Task must be unblocked after rejection"

    def test_reject_appends_canonical_summary_to_task_body(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Reject summary task")
        stem = f"{task_id}-reject-summary"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        body = _read_task_body_pattern_b(engine_pattern_b, task_id)
        assert "## Decision Request" in body
        assert "rejected" in body

    def test_reject_response_body_shape(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Reject response shape task")
        stem = f"{task_id}-reject-shape"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"id": stem, "response": "rejected"}

    def test_reject_summary_includes_source_line(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Reject source line task")
        stem = f"{task_id}-reject-source"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id, body="Decide the scope.")

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        body = _read_task_body_pattern_b(engine_pattern_b, task_id)
        assert "- source:" in body


class TestFromAC_NeedsInfoResolution:
    """Coverage promoted from #1384 for needs-info lifecycle."""

    def test_needs_info_moves_dr_to_resolved(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Needs-info move task")
        stem = f"{task_id}-needs-info-move"
        pending_path = _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)
        resolved_path = board_dir_pattern_b / "decisions" / "resolved" / f"{stem}.md"

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "needs-info"})

        assert not pending_path.exists(), "DR must leave pending/ on needs-info"
        assert resolved_path.exists(), "DR must arrive in resolved/ on needs-info"

    def test_needs_info_task_remains_blocked(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Needs-info blocked task")
        stem = f"{task_id}-needs-info-blocked"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)
        resolved_path = board_dir_pattern_b / "decisions" / "resolved" / f"{stem}.md"

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "needs-info"})

        assert resp.status_code == 200
        assert resolved_path.exists(), "DR must be moved to resolved/ on needs-info"
        assert _is_task_blocked_pattern_b(engine_pattern_b, task_id), (
            "Task must remain blocked after needs-info resolution"
        )

    def test_needs_info_appends_canonical_summary_to_task_body(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Needs-info summary task")
        stem = f"{task_id}-needs-info-summary"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "needs-info"})

        body = _read_task_body_pattern_b(engine_pattern_b, task_id)
        assert "## Decision Request" in body
        assert "needs-info" in body


class TestFromAC_AlreadyResolved:
    """Coverage promoted from #1384 for already-resolved 409 behavior."""

    def test_dr_already_in_resolved_returns_409(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Already resolved task")
        stem = f"{task_id}-already-resolved"
        _write_resolved_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id, response="approved")

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert resp.status_code == 409

    def test_dr_already_in_resolved_returns_domain_error_envelope(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Already resolved envelope task")
        stem = f"{task_id}-already-resolved-envelope"
        _write_resolved_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id, response="rejected")

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert resp.status_code == 409
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_dr_in_pending_with_non_pending_frontmatter_returns_409(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "In-place already answered task")
        stem = f"{task_id}-already-answered"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id, response="approved")

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert resp.status_code == 409

    def test_already_resolved_409_uses_domain_envelope(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "In-place envelope check task")
        stem = f"{task_id}-in-place-envelope"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id, response="needs-info")

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert resp.status_code == 409
        body = resp.json()
        assert "code" in body
        assert "message" in body


class TestFromAC_DuplicateResponse:
    """Coverage promoted from #1384 for duplicate-response behavior."""

    def test_second_resolve_returns_404(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Duplicate resolve task")
        stem = f"{task_id}-dup-resolve"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        first = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})
        assert first.status_code == 200

        second = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})
        assert second.status_code == 404

    def test_second_resolve_uses_fastapi_detail_format(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Duplicate format task")
        stem = f"{task_id}-dup-format"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "rejected"})

        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body

    def test_second_resolve_different_response_also_404(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Duplicate diff response task")
        stem = f"{task_id}-dup-diff"
        _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)

        client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "needs-info"})

        assert resp.status_code == 404


class TestFromAC_ImmediateEffects:
    """Coverage promoted from #1384 for immediate side-effects visibility."""

    def test_file_move_and_unblock_visible_without_sweep(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "Immediate effects task")
        stem = f"{task_id}-immediate"
        pending_path = _write_pending_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id)
        resolved_path = board_dir_pattern_b / "decisions" / "resolved" / f"{stem}.md"

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert resp.status_code == 200
        assert not pending_path.exists()
        assert resolved_path.exists()
        assert not _is_task_blocked_pattern_b(engine_pattern_b, task_id)


class TestFromAC_PublicAPIExposure:
    """Coverage promoted from #1385 for kanban decisions public symbols."""

    def test_parse_dr_importable_from_kanban_decisions(self) -> None:
        from owlbear_kanban.decisions import parse_dr  # noqa: F401, PLC0415

    def test_canonical_summary_importable_from_kanban_decisions(self) -> None:
        from owlbear_kanban.decisions import canonical_summary  # noqa: F401, PLC0415


class TestFromAC_ImportDelegation:
    """Coverage promoted from #1385 for cockpit import delegation boundaries."""

    def test_cockpit_does_not_define_local_parse_dr(self) -> None:
        import owlbear_cockpit.routes.decisions as module  # noqa: PLC0415

        assert not hasattr(module, "_parse_dr")

    def test_cockpit_does_not_define_local_canonical_summary(self) -> None:
        import owlbear_cockpit.routes.decisions as module  # noqa: PLC0415

        assert not hasattr(module, "_canonical_summary")


class TestFromAC_CockpitBoundary:
    """Coverage promoted from #1385 for retained HTTP-specific helpers."""

    def test_cockpit_retains_validate_decision_id_and_removes_local_parse_dr(
        self,
    ) -> None:
        import owlbear_cockpit.routes.decisions as module  # noqa: PLC0415

        assert hasattr(module, "_validate_decision_id")
        assert not hasattr(module, "_parse_dr")

    def test_cockpit_retains_extract_title_and_removes_local_canonical_summary(
        self,
    ) -> None:
        import owlbear_cockpit.routes.decisions as module  # noqa: PLC0415

        assert hasattr(module, "_extract_title")
        assert not hasattr(module, "_canonical_summary")


class TestFromAC_ErrorFormatPreserved:
    """Coverage promoted from #1385 for domain envelope preservation."""

    def test_already_resolved_returns_409_domain_envelope(
        self,
        client_pattern_b: TestClient,
        engine_pattern_b: KanbanEngine,
        board_dir_pattern_b: Path,
    ) -> None:
        from owlbear_kanban.decisions import parse_dr  # noqa: F401, PLC0415

        task_id = _create_blocked_task_pattern_b(engine_pattern_b, "already-resolved-envelope-task")
        stem = f"{task_id}-already-resolved-envelope"
        _write_resolved_dr_pattern_b(board_dir_pattern_b, stem=stem, task_id=task_id, response="approved")

        resp = client_pattern_b.post(f"/api/decisions/{stem}/resolve", json={"response": "approved"})

        assert resp.status_code == 409
        data = resp.json()
        assert "code" in data
        assert "message" in data
