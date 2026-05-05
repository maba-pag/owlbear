"""Failing tests for #1218: Cockpit security — validate decision_id against path traversal.

AC coverage:
  ac1-traversal-payloads  — _find_decision_path() raises HTTPException(422) for invalid ids
  ac1-before-io           — validation fires before any Path.exists() or filesystem I/O
  ac2-route-422           — POST /decisions/{decision_id}/resolve returns 422 for malformed ids
  ac3-payloads            — specific traversal payloads exercised directly on _find_decision_path()

All tests FAIL (RED phase) — _find_decision_path() currently has no allowlist validation;
it proceeds directly to filesystem I/O for all inputs including traversal payloads.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from owlbear_cockpit.routes.decisions import _find_decision_path

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


@pytest.fixture
def decisions_dir(tmp_path: Path) -> Path:
    return _make_decisions_dir(tmp_path)


@pytest.fixture
def client(tmp_path: Path, decisions_dir: Path):
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit import deps as cockpit_deps  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    board_dir = _make_board(tmp_path)
    engine = KanbanEngine(board_dir)
    engine.list_tasks()

    app.dependency_overrides[get_engine] = lambda: engine

    get_decisions_dir_dep = getattr(cockpit_deps, "get_decisions_dir", None)
    if get_decisions_dir_dep is not None:
        app.dependency_overrides[get_decisions_dir_dep] = lambda: decisions_dir

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestFromAC_DecisionIdValidation:
    """AC1 + AC3: _find_decision_path() raises HTTPException(422) for invalid decision_ids.

    Covers all traversal payloads specified in AC3 as direct unit-level tests.
    """

    @pytest.mark.parametrize(
        "bad_id",
        [
            "../../etc/passwd",  # classic path traversal
            "foo/bar",  # embedded slash
            "..\\secret",  # backslash traversal vector
            "",  # empty string — no match for ^[a-zA-Z0-9]…
            ".hidden",  # starts with dot, not [a-zA-Z0-9]
        ],
    )
    def test_invalid_id_raises_http422(self, bad_id: str, tmp_path: Path) -> None:
        """AC1+AC3: each traversal/invalid payload raises HTTPException(422)."""
        with pytest.raises(HTTPException) as exc_info:
            _find_decision_path(tmp_path, bad_id)
        assert exc_info.value.status_code == 422, (
            f"Expected status_code=422 for decision_id={bad_id!r}; "
            f"got {exc_info.value.status_code}"
        )

    def test_traversal_dot_dot_slash_raises_422(self, tmp_path: Path) -> None:
        """AC3 explicit: '../../etc/passwd' raises HTTPException(422)."""
        with pytest.raises(HTTPException) as exc_info:
            _find_decision_path(tmp_path, "../../etc/passwd")
        assert exc_info.value.status_code == 422

    def test_traversal_foo_slash_bar_raises_422(self, tmp_path: Path) -> None:
        """AC3 explicit: 'foo/bar' (embedded slash) raises HTTPException(422)."""
        with pytest.raises(HTTPException) as exc_info:
            _find_decision_path(tmp_path, "foo/bar")
        assert exc_info.value.status_code == 422

    def test_traversal_backslash_raises_422(self, tmp_path: Path) -> None:
        """AC3 explicit: '..\\secret' (backslash vector) raises HTTPException(422)."""
        with pytest.raises(HTTPException) as exc_info:
            _find_decision_path(tmp_path, "..\\secret")
        assert exc_info.value.status_code == 422

    def test_empty_string_raises_422(self, tmp_path: Path) -> None:
        """AC3 explicit: empty string raises HTTPException(422)."""
        with pytest.raises(HTTPException) as exc_info:
            _find_decision_path(tmp_path, "")
        assert exc_info.value.status_code == 422

    def test_dot_hidden_raises_422(self, tmp_path: Path) -> None:
        """AC3 explicit: '.hidden' (starts with dot) raises HTTPException(422)."""
        with pytest.raises(HTTPException) as exc_info:
            _find_decision_path(tmp_path, ".hidden")
        assert exc_info.value.status_code == 422

    def test_valid_id_returns_pending_path(self, tmp_path: Path) -> None:
        """AC3: valid allowlisted id '1234-some-slug' passes validation and returns file path.

        Proves the success branch of _find_decision_path() is reachable — a regression
        that incorrectly rejects allowlisted ids would raise here rather than return a path.
        """
        decisions_dir = tmp_path / "decisions"
        pending_dir = decisions_dir / "pending"
        pending_dir.mkdir(parents=True)
        (decisions_dir / "resolved").mkdir()
        decision_file = pending_dir / "1234-some-slug.md"
        decision_file.write_text(
            "---\nresponse: pending\n---\n# Test DR\n", encoding="utf-8"
        )

        result = _find_decision_path(decisions_dir, "1234-some-slug")

        assert result == decision_file, (
            f"Expected _find_decision_path to return {decision_file!r}, got {result!r}"
        )


class TestFromAC_ValidationBeforeFilesystemIO:
    """AC1: validation must execute before any Path.exists() or filesystem I/O.

    Proves the allowlist check is a pre-condition gate, not a post-hoc filter.
    """

    def test_no_filesystem_io_for_traversal_payload(self, tmp_path: Path) -> None:
        """AC1: Path.exists() must not be called when decision_id is a traversal payload."""
        exists_calls: list[str] = []

        def spy_exists(self: Path) -> bool:
            exists_calls.append(str(self))
            return False

        with (
            patch.object(Path, "exists", spy_exists),
            pytest.raises(HTTPException) as exc_info,
        ):
            _find_decision_path(tmp_path, "../../etc/passwd")

        assert exc_info.value.status_code == 422, (
            f"Expected HTTPException(422), got status_code={exc_info.value.status_code}"
        )
        assert exists_calls == [], (
            f"Path.exists() must NOT be called before allowlist validation; "
            f"called {len(exists_calls)} time(s) with: {exists_calls}"
        )

    def test_no_filesystem_io_for_empty_id(self, tmp_path: Path) -> None:
        """AC1: Path.exists() not called for empty-string decision_id."""
        exists_calls: list[str] = []

        def spy_exists(self: Path) -> bool:
            exists_calls.append(str(self))
            return False

        with (
            patch.object(Path, "exists", spy_exists),
            pytest.raises(HTTPException) as exc_info,
        ):
            _find_decision_path(tmp_path, "")

        assert exc_info.value.status_code == 422
        assert exists_calls == [], (
            f"Path.exists() must NOT be called before validation; called with: {exists_calls}"
        )


class TestFromAC_RouteRejects422:
    """AC2: POST /decisions/{decision_id}/resolve returns HTTP 422 for malformed ids."""

    def test_route_422_for_dot_hidden_id(self, client: TestClient) -> None:
        """AC2 smoke: route returns 422 for '.hidden' decision_id."""
        response = client.post(
            "/api/decisions/.hidden/resolve",
            json={"response": "approved"},
        )
        assert response.status_code == 422, (
            f"Expected HTTP 422 for malformed decision_id '.hidden'; "
            f"got {response.status_code}: {response.text}"
        )

    def test_route_422_for_dot_dot_traversal_id(self, client: TestClient) -> None:
        """AC2: route returns 422 for URL-decoded traversal segment '..secret'."""
        # FastAPI routing rejects literal '/' in path params, so we use '..' prefix
        response = client.post(
            "/api/decisions/..secret/resolve",
            json={"response": "approved"},
        )
        assert response.status_code == 422, (
            f"Expected HTTP 422 for '..secret'; got {response.status_code}: {response.text}"
        )
