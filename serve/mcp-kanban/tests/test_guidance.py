"""TDD RED tests for KanbanTask.guidance field and collect_guidance function.

Task #974 — RED phase. All tests must FAIL until GREEN phase (#976).

AC coverage:
  - KanbanTask.guidance defaults to []
  - guidance is the first key in model_dump() (Pydantic v2 declaration-order)
  - collect_guidance("edit_block", ...) without block:user tag → DR-required message
  - collect_guidance("end_work_block", ...) without block:user tag → DR-required message
  - collect_guidance("edit_block", ...) with block:user tag → []
  - collect_guidance("end_work_block", ...) with block:user tag → []
  - collect_guidance("move", ...) forward skip >1 slot → guidance
  - collect_guidance("move", ...) 1-slot adjacent → []
  - collect_guidance("move", ...) backward → []
  - collect_guidance("end_work_success", ...) → message containing "commit"
  - collect_guidance("unknown_op", ...) → []
"""

from __future__ import annotations

from owlbear_mcp_kanban.models import KanbanTask

try:
    from owlbear_mcp_kanban.guidance import collect_guidance as _collect_guidance

    collect_guidance = _collect_guidance
except ImportError:
    collect_guidance = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATUSES = ["research", "backlog", "todo", "in-progress", "review", "docs", "done"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task(*, status: str = "todo", tags: list[str] | None = None) -> KanbanTask:
    return KanbanTask(
        id=1,
        title="Test Task",
        status=status,
        priority="needed",
        created="2026-01-01",
        updated="2026-01-01",
        tags=tags or [],
    )


def _require_guidance() -> None:
    """Fail immediately if collect_guidance module is not yet implemented."""
    assert collect_guidance is not None, (
        "owlbear_mcp_kanban.guidance module not yet implemented — ImportError on import"
    )


# ---------------------------------------------------------------------------
# TestFromAC_KanbanTaskGuidanceField
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTaskGuidanceField:
    """Contract tests for the KanbanTask.guidance field (AC: model tests)."""

    def test_guidance_defaults_to_empty_list(self) -> None:
        """KanbanTask.guidance defaults to [] when not supplied."""
        task = _task()
        assert task.guidance == []  # type: ignore[attr-defined]

    def test_guidance_is_first_key_in_model_dump(self) -> None:
        """guidance is the first key in model_dump() output (declaration-order)."""
        task = _task()
        keys = list(task.model_dump().keys())
        assert keys[0] == "guidance", f"Expected 'guidance' as first serialization key, got {keys[0]!r}"


# ---------------------------------------------------------------------------
# TestFromAC_CollectGuidance
# ---------------------------------------------------------------------------


class TestFromAC_CollectGuidance:
    """Contract tests for collect_guidance(operation, before, after, **kwargs)."""

    # -- edit_block: DR-required message -----------------------------------------

    def test_edit_block_without_block_user_tag_returns_dr_message(self) -> None:
        """edit_block without 'block:user' tag → non-empty list, first item contains 'Decision Request'."""
        _require_guidance()
        before = _task()
        after = _task(tags=["scope:foo"])
        result = collect_guidance("edit_block", before, after)  # type: ignore[misc]
        assert len(result) > 0, "Expected non-empty guidance for edit_block without block:user"
        assert "Decision Request" in result[0], f"Expected 'Decision Request' in first guidance item, got {result[0]!r}"

    def test_end_work_block_without_block_user_tag_returns_dr_message(self) -> None:
        """end_work_block without 'block:user' tag → non-empty list, first item contains 'Decision Request'."""
        _require_guidance()
        before = _task()
        after = _task(tags=["scope:bar"])
        result = collect_guidance("end_work_block", before, after)  # type: ignore[misc]
        assert len(result) > 0, "Expected non-empty guidance for end_work_block without block:user"
        assert "Decision Request" in result[0], f"Expected 'Decision Request' in first guidance item, got {result[0]!r}"

    # -- edit_block / end_work_block: block:user tag skips DR -------------------

    def test_edit_block_with_block_user_tag_returns_empty(self) -> None:
        """edit_block with 'block:user' tag → returns []."""
        _require_guidance()
        before = _task()
        after = _task(tags=["block:user"])
        result = collect_guidance("edit_block", before, after)  # type: ignore[misc]
        assert result == [], f"Expected [] for edit_block with block:user, got {result!r}"

    def test_end_work_block_with_block_user_tag_returns_empty(self) -> None:
        """end_work_block with 'block:user' tag → returns []."""
        _require_guidance()
        before = _task()
        after = _task(tags=["block:user"])
        result = collect_guidance("end_work_block", before, after)  # type: ignore[misc]
        assert result == [], f"Expected [] for end_work_block with block:user, got {result!r}"

    # -- move: forward skip >1 slot -------------------------------------------

    def test_move_forward_skip_more_than_one_slot_returns_guidance(self) -> None:
        """move where after.status is >1 slot ahead of before.status → non-empty guidance."""
        _require_guidance()
        before = _task(status="research")
        after = _task(status="todo")  # 2 slots ahead: research→backlog→todo
        result = collect_guidance("move", before, after, statuses=STATUSES)  # type: ignore[misc]
        assert len(result) > 0, f"Expected guidance for >1-slot forward move (research→todo), got {result!r}"

    # -- move: boundary — exactly 1 slot ahead --------------------------------

    def test_move_forward_one_slot_returns_empty(self) -> None:
        """move where after.status is exactly 1 slot ahead → returns []."""
        _require_guidance()
        before = _task(status="research")
        after = _task(status="backlog")  # 1 slot ahead
        result = collect_guidance("move", before, after, statuses=STATUSES)  # type: ignore[misc]
        assert result == [], f"Expected [] for 1-slot forward move (research→backlog), got {result!r}"

    # -- move: backward -------------------------------------------------------

    def test_move_backward_returns_empty(self) -> None:
        """move where after.status is behind before.status → returns []."""
        _require_guidance()
        before = _task(status="todo")
        after = _task(status="backlog")  # backward
        result = collect_guidance("move", before, after, statuses=STATUSES)  # type: ignore[misc]
        assert result == [], f"Expected [] for backward move (todo→backlog), got {result!r}"

    # -- end_work_success: commit message -------------------------------------

    def test_end_work_success_returns_commit_message(self) -> None:
        """end_work_success → non-empty list, first item contains 'commit' (case-insensitive)."""
        _require_guidance()
        before = _task()
        after = _task()
        result = collect_guidance("end_work_success", before, after)  # type: ignore[misc]
        assert len(result) > 0, "Expected non-empty guidance for end_work_success"
        assert "commit" in result[0].lower(), (
            f"Expected 'commit' (case-insensitive) in first guidance item, got {result[0]!r}"
        )

    # -- unknown operation ----------------------------------------------------

    def test_unknown_operation_returns_empty_list(self) -> None:
        """Unrecognised operation → returns []."""
        _require_guidance()
        before = _task()
        after = _task()
        result = collect_guidance("unknown_op", before, after)  # type: ignore[misc]
        assert result == [], f"Expected [] for unknown operation, got {result!r}"


# ---------------------------------------------------------------------------
# TestBuilderDiscovered
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered tests for KanbanTask.guidance field.

    AC6 (#986): model_validate from engine Task dict (no guidance key) → guidance=[].
    """

    def test_model_validate_from_dict_without_guidance_key_gives_empty_list(
        self,
    ) -> None:
        """AC6: KanbanTask.model_validate with no 'guidance' key in dict → guidance=[]."""
        engine_dict = {
            "id": 42,
            "title": "Engine task",
            "status": "todo",
            "priority": "important",
            "created": "2026-01-01",
            "updated": "2026-01-01",
        }
        task = KanbanTask.model_validate(engine_dict)
        assert task.guidance == [], (
            f"Expected guidance=[] when validating dict with no 'guidance' key, got {task.guidance!r}"
        )
