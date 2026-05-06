"""GET-after-mutation cache-invalidation proofs for cockpit edit and release routes (#1401).

AC coverage:
  AC1: GET /api/tasks reflects title changes after POST /api/tasks/{id}/edit
        (field-inspection: locate task by ID, assert title == new value)
  AC2: GET /api/tasks reflects exact tag replacement after POST /api/tasks/{id}/edit
        (field-inspection: exact set equality — no stale or extra tags permitted)
  AC3: GET /api/tasks reflects claimed=False after POST /api/tasks/{id}/release
        (field-inspection: locate task by ID, assert claimed == False)

All tests follow the prime→mutate→re-read pattern:
  1. Prime cache via initial GET /api/tasks.
  2. Perform mutation via the corresponding POST route.
  3. Assert a fresh GET /api/tasks reflects the change.

Assertion strategy: field-inspection on the task summary object (distinct from the
move-route proof in test_cockpit_cache_sse_1346.py which uses filter-exclusion).

Proofs depend on:
  serve/cockpit/src/owlbear_cockpit/cache.py  — MtimeScanCache passive invalidation
  serve/cockpit/src/owlbear_cockpit/routes/read.py — cache.has_changed_at check
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban import KanbanEngine


# ---------------------------------------------------------------------------
# Board config & helpers (self-contained, no shared fixtures from other modules)
# ---------------------------------------------------------------------------

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
    """Create a minimal kanban board directory. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1 / AC2 / AC3 proof tests
# ---------------------------------------------------------------------------


class TestFromAC_EditReleaseCacheInvalidation:
    """GET-after-mutation cache invalidation proofs for edit and release routes.

    All three tests use the prime→mutate→re-read pattern with field-inspection:
    locate the mutated task by ID in the GET /api/tasks response, then assert
    the relevant field equals the post-mutation value.
    """

    def test_get_tasks_reflects_title_after_edit_route(
        self, tmp_path: Path
    ) -> None:
        """AC1: GET /api/tasks reflects title changes after POST /api/tasks/{id}/edit.

        After editing a task's title via the cockpit edit route, a subsequent
        GET /api/tasks must return the updated title, not the cached pre-edit value.

        Fails if cache.has_changed_at() returns False after edit rewrites the task
        file (i.e. MtimeScanCache does not detect the mtime change).
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board_edit_title")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Original title", status="todo", priority="important")
        seed.list_tasks()

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime cache with the original task list.
            prime_resp = client.get("/api/tasks")
            assert prime_resp.status_code == 200
            primed = {t["id"]: t for t in prime_resp.json()["tasks"]}
            assert 1 in primed, "Precondition: task 1 must be present"
            assert primed[1]["title"] == "Original title", (
                "Precondition: task 1 must carry the original title before mutation"
            )

            # Mutate: edit title via the cockpit edit route.
            task = eng.show_task("1")
            edit_resp = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "Mutated title"},
            )
            assert edit_resp.status_code == 200, (
                f"POST /api/tasks/1/edit returned {edit_resp.status_code}: "
                f"{edit_resp.json()}"
            )

            # Re-read: GET /api/tasks must reflect the mutated title.
            resp_after = client.get("/api/tasks")
            assert resp_after.status_code == 200
            after = {t["id"]: t for t in resp_after.json()["tasks"]}
            assert 1 in after, "Task 1 must still be present after title edit"
            assert after[1]["title"] == "Mutated title", (
                "Task 1 title was updated via POST /api/tasks/1/edit but "
                "GET /api/tasks still returns the pre-edit value. "
                "Cache was not invalidated after the edit route rewrote the task file."
            )
        finally:
            app.dependency_overrides.clear()

    def test_get_tasks_reflects_tags_after_edit_route(
        self, tmp_path: Path
    ) -> None:
        """AC2: GET /api/tasks reflects exact tag replacement after POST /api/tasks/{id}/edit.

        After replacing tags via the cockpit edit route, a subsequent GET /api/tasks
        must return the new tag list with exact set equality — no stale, removed, or
        extra tags permitted.

        Fails if:
        - Cache is not invalidated (stale tag list returned), OR
        - The tag set differs from the exact replacement list for any reason.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board_edit_tags")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Tag test task", status="todo", priority="important")
        seed.list_tasks()
        # Set up known initial tags so we can assert the removed tag is absent.
        seed.edit_task("1", add_tags=["old-tag", "keep-tag"])

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime cache with the initial tag state.
            prime_resp = client.get("/api/tasks")
            assert prime_resp.status_code == 200
            primed = {t["id"]: t for t in prime_resp.json()["tasks"]}
            assert 1 in primed, "Precondition: task 1 must be present"
            assert "old-tag" in primed[1]["tags"], (
                "Precondition: old-tag must be in task 1 before mutation"
            )

            # Mutate: replace tags via the cockpit edit route (full-replacement semantics).
            task = eng.show_task("1")
            edit_resp = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "tags": ["new-tag", "another-tag"]},
            )
            assert edit_resp.status_code == 200, (
                f"POST /api/tasks/1/edit (tags) returned {edit_resp.status_code}: "
                f"{edit_resp.json()}"
            )

            # Re-read: GET /api/tasks must reflect the exact replacement tag list.
            resp_after = client.get("/api/tasks")
            assert resp_after.status_code == 200
            after = {t["id"]: t for t in resp_after.json()["tasks"]}
            assert 1 in after, "Task 1 must still be present after tag edit"
            actual_tags = set(after[1]["tags"])
            # Exact set equality — no stale, removed, or extra tags permitted.
            assert actual_tags == {"new-tag", "another-tag"}, (
                f"GET /api/tasks returned tags {actual_tags!r} after tag replacement "
                "via POST /api/tasks/1/edit — expected exactly {{'new-tag', 'another-tag'}}. "
                "Either the cache was not invalidated (stale tags returned) or the edit "
                "route does not apply full-replacement semantics (extra or removed tags remain)."
            )
        finally:
            app.dependency_overrides.clear()

    def test_get_tasks_reflects_claimed_false_after_release_route(
        self, tmp_path: Path
    ) -> None:
        """AC3: GET /api/tasks reflects claimed=False after POST /api/tasks/{id}/release.

        After releasing a claimed task via the cockpit release route, a subsequent
        GET /api/tasks must return claimed=False for that task.

        Fails if cache.has_changed_at() returns False after release rewrites the
        task file (i.e. MtimeScanCache does not detect the mtime change), causing
        GET /api/tasks to return the stale claimed=True value from cache.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board_release")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Claimed task", status="in-progress", priority="important")
        seed.list_tasks()
        seed.claim_task("1")

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime cache with task 1 in claimed=True state.
            prime_resp = client.get("/api/tasks")
            assert prime_resp.status_code == 200
            primed = {t["id"]: t for t in prime_resp.json()["tasks"]}
            assert 1 in primed, "Precondition: task 1 must be present"
            assert primed[1]["claimed"] is True, (
                "Precondition: task 1 must be claimed before release"
            )

            # Mutate: release the task via the cockpit release route.
            task = eng.show_task("1")
            release_resp = client.post(
                "/api/tasks/1/release",
                json={"updated": task.updated},
            )
            assert release_resp.status_code == 200, (
                f"POST /api/tasks/1/release returned {release_resp.status_code}: "
                f"{release_resp.json()}"
            )

            # Re-read: GET /api/tasks must reflect claimed=False for the released task.
            resp_after = client.get("/api/tasks")
            assert resp_after.status_code == 200
            after = {t["id"]: t for t in resp_after.json()["tasks"]}
            assert 1 in after, "Task 1 must still be present after release"
            assert after[1]["claimed"] is False, (
                "Task 1 was released via POST /api/tasks/1/release but "
                "GET /api/tasks still shows claimed=True. "
                "Cache was not invalidated after the release route rewrote the task file."
            )
        finally:
            app.dependency_overrides.clear()
