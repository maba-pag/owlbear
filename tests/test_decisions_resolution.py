from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_CONFIG_YAML = """\
next_id: 1
"""

_OPTIONS_VALID = [
    {
        "option_id": "option-a",
        "label": "Option Alpha",
        "confidence": 0.8,
        "recommended": True,
        "rationale": "Preferred option.",
    },
    {
        "option_id": "option-b",
        "label": "Option Beta",
        "confidence": 0.5,
        "recommended": False,
        "rationale": "Alternative option.",
    },
]


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory for integration tests."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _rewrite_resolution_fields(
    request_path: Path,
    *,
    selected_option_id: str | None,
    free_text: str | None,
) -> None:
    """Update pending request frontmatter resolution fields in-place."""
    text = request_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_idx = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    frontmatter_text = "\n".join(lines[1:close_idx])
    body_text = "\n".join(lines[close_idx + 1 :])

    yaml = YAML(typ="safe")
    frontmatter = yaml.load(frontmatter_text) or {}
    resolution = frontmatter.get("resolution") or {}
    resolution["selected_option_id"] = selected_option_id
    resolution["free_text"] = free_text
    frontmatter["resolution"] = resolution

    write_yaml = YAML()
    write_yaml.default_flow_style = False
    from io import StringIO

    buffer = StringIO()
    write_yaml.dump(frontmatter, buffer)
    dumped_frontmatter = buffer.getvalue().strip()

    updated = f"---\n{dumped_frontmatter}\n---\n{body_text}\n"
    request_path.write_text(updated, encoding="utf-8", newline="\n")


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Temporary board directory for each test."""
    return _make_board(tmp_path)


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """Real KanbanEngine wired to a temporary board."""
    eng = KanbanEngine(board_dir, activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient using the real engine dependency override."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestEndToEndDecisionResolution:
    """AC1: decision request can be listed and resolved through Cockpit API."""

    def test_resolve_decision_unblocks_and_appends_selected_label(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        task_id = int(engine.create_task("Decision target", status="build").id)
        request = engine.create_request(
            task_id,
            "decision",
            "Choose approach",
            "Select one option.",
            "builder",
            options=_OPTIONS_VALID,
            body="## Question\nWhich option should we use?",
        )

        pending = client.get("/api/requests/pending")
        assert pending.status_code == 200
        pending_items = pending.json()
        matched = [item for item in pending_items if item["request_id"] == request.request_id]
        assert len(matched) == 1
        assert matched[0]["kind"] == "decision"
        assert len(matched[0]["options"]) == 2

        response = client.post(
            f"/api/requests/{request.request_id}/resolve",
            json={"selected_option_id": "option-a", "free_text": None, "kind": "decision"},
        )
        assert response.status_code == 200

        task = engine.show_task(str(task_id))
        assert "## DR: Choose approach" in task.body
        assert "Option Alpha" in task.body
        assert task.blocked is False

    def test_pending_response_includes_all_structured_fields(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """Reviewer gap: pending response must prove ALL public contract fields, not just kind and options count."""
        task_id = int(engine.create_task("Field check target", status="build").id)
        request = engine.create_request(
            task_id,
            "decision",
            "Field check title",
            "Field check summary.",
            "builder",
            options=_OPTIONS_VALID,
            body="## Body\nField check body.",
        )

        pending = client.get("/api/requests/pending")
        assert pending.status_code == 200
        items = pending.json()
        matched = [item for item in items if item["request_id"] == request.request_id]
        assert len(matched) == 1
        item = matched[0]

        # All structured response fields must be present and correct
        assert item["request_id"] == request.request_id
        assert item["task_id"] == task_id
        assert item["kind"] == "decision"
        assert item["title"] == "Field check title"
        assert item["summary"] == "Field check summary."
        assert item["agent"] == "builder"
        assert item["created_at"] is not None
        assert item["body"] == "## Body\nField check body."
        assert len(item["options"]) == 2
        assert item["options"][0]["option_id"] == "option-a"
        assert item["options"][0]["label"] == "Option Alpha"
        assert item["options"][0]["confidence"] == 0.8
        assert item["options"][0]["recommended"] is True
        assert item["options"][0]["rationale"] == "Preferred option."
        assert item["options"][1]["option_id"] == "option-b"
        assert item["options"][1]["label"] == "Option Beta"
        assert item["options"][1]["confidence"] == 0.5
        assert item["options"][1]["recommended"] is False
        assert item["options"][1]["rationale"] == "Alternative option."

    def test_resolve_writes_submitted_option_not_first_or_recommended(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """Reviewer gap: writeback must prove the SUBMITTED option_id is resolved, not hardcoded first/recommended."""
        task_id = int(engine.create_task("Non-recommended target", status="build").id)
        request = engine.create_request(
            task_id,
            "decision",
            "Choose approach",
            "Select one option.",
            "builder",
            options=_OPTIONS_VALID,
            body="## Question\nWhich option?",
        )

        # Submit option-b (NOT the recommended option-a / first option)
        response = client.post(
            f"/api/requests/{request.request_id}/resolve",
            json={"selected_option_id": "option-b", "free_text": None, "kind": "decision"},
        )
        assert response.status_code == 200

        task = engine.show_task(str(task_id))
        # The DR header, the submitted (non-recommended) option label, and unblock must all hold
        assert "## DR: Choose approach" in task.body
        assert "- **Selected:** Option Beta" in task.body
        assert "Option Alpha" not in task.body
        assert task.blocked is False


class TestEndToEndActionResolution:
    """AC2: action request can be resolved via bare-complete normalization."""

    def test_resolve_action_with_bare_complete_unblocks_and_appends_outcome(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        task_id = int(engine.create_task("Action target", status="build").id)
        request = engine.create_request(
            task_id,
            "action",
            "Run action",
            "Execute operation.",
            "builder",
            body="## Action\nRun the operation.",
        )

        response = client.post(
            f"/api/requests/{request.request_id}/resolve",
            json={"selected_option_id": None, "free_text": None, "kind": "action"},
        )
        assert response.status_code == 200

        task = engine.show_task(str(task_id))
        assert "## AR: Run action" in task.body
        assert "**Outcome:**" in task.body
        assert task.blocked is False

    def test_resolve_bare_complete_writes_exact_empty_string_not_none(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """Reviewer gap: bare-complete normalization must produce empty string outcome, not None/null/placeholder."""
        task_id = int(engine.create_task("Bare complete target", status="build").id)
        request = engine.create_request(
            task_id,
            "action",
            "Normalized action",
            "Normalization check.",
            "builder",
            body="## Action\nNormalize this.",
        )

        # Bare complete: selected_option_id=None, free_text=None, kind=action → free_text normalized to ""
        response = client.post(
            f"/api/requests/{request.request_id}/resolve",
            json={"selected_option_id": None, "free_text": None, "kind": "action"},
        )
        assert response.status_code == 200

        # Verify resolve response payload is structured correctly
        resp_data = response.json()
        assert resp_data["request_id"] == request.request_id
        assert resp_data["task_id"] == task_id
        assert resp_data["kind"] == "action"
        assert resp_data["title"] == "Normalized action"
        assert resp_data["resolved_at"] is not None

        task = engine.show_task(str(task_id))
        # Exact normalized writeback: free_text="" produces "- **Outcome:** " (empty, not "None")
        # Use line-boundary assertion to prove exact empty-string outcome, not a substring match.
        assert "## AR: Normalized action" in task.body
        outcome_lines = [line for line in task.body.splitlines() if "**Outcome:**" in line]
        assert len(outcome_lines) == 1
        assert outcome_lines[0] == "- **Outcome:** "
        assert task.blocked is False


class TestConditionalUnblockWithSiblings:
    """AC3: task stays blocked until all sibling pending requests are resolved."""

    def test_task_stays_blocked_until_last_sibling_resolves(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        task_id = int(engine.create_task("Sibling target", status="build").id)
        first = engine.create_request(
            task_id,
            "action",
            "First action",
            "First summary.",
            "builder",
        )
        second = engine.create_request(
            task_id,
            "action",
            "Second action",
            "Second summary.",
            "builder",
        )

        first_resp = client.post(
            f"/api/requests/{first.request_id}/resolve",
            json={"selected_option_id": None, "free_text": "first done", "kind": "action"},
        )
        assert first_resp.status_code == 200
        task_after_first = engine.show_task(str(task_id))
        assert task_after_first.blocked is True

        second_resp = client.post(
            f"/api/requests/{second.request_id}/resolve",
            json={"selected_option_id": None, "free_text": "second done", "kind": "action"},
        )
        assert second_resp.status_code == 200
        task_after_second = engine.show_task(str(task_id))
        assert task_after_second.blocked is False


class TestSweepViaPickTasksIntegration:
    """AC4: pick_tasks triggers request sweep and side effects for pre-resolved pending files."""

    def test_pick_tasks_sweeps_pending_request_and_applies_writeback(
        self,
        engine: KanbanEngine,
    ) -> None:
        task_id = int(engine.create_task("Sweep target", status="build").id)
        request = engine.create_request(
            task_id,
            "action",
            "Swept action",
            "Swept summary.",
            "builder",
            body="## Action\nPerform via sweep.",
        )

        pending_path = Path(engine.kanban_dir) / "decisions" / "pending" / f"{request.request_id}.md"
        resolved_path = Path(engine.kanban_dir) / "decisions" / "resolved" / f"{request.request_id}.md"
        assert pending_path.exists()

        _rewrite_resolution_fields(
            pending_path,
            selected_option_id=None,
            free_text="swept complete",
        )

        engine.agent_view().pick_tasks()

        assert not pending_path.exists()
        assert resolved_path.exists()

        yaml = YAML(typ="safe")
        resolved_text = resolved_path.read_text(encoding="utf-8")
        lines = resolved_text.splitlines()
        close_idx = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
        resolved_frontmatter = yaml.load("\n".join(lines[1:close_idx])) or {}
        assert resolved_frontmatter["resolution"]["resolved_at"] is not None

        task = engine.show_task(str(task_id))
        assert "## AR: Swept action" in task.body
        assert "**Outcome:** swept complete" in task.body
        assert task.blocked is False
