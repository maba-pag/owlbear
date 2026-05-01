"""CockpitView facade for cockpit-facing Kanban operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_kanban.models import (
    ActivityCompactionResult,
    ActivityEvent,
    BoardConfig,
    ListTasksResponse,
    NotFoundError,
    SessionRecord,
    ShowTaskResponse,
    SingleTaskResponse,
    Task,
    ValidationError,
)

if TYPE_CHECKING:
    from owlbear_kanban import KanbanEngine

_BLOCK_REASON_UNSET = object()


class CockpitView:
    """Minimal role-scoped wrapper for cockpit-facing engine use."""

    def __init__(self, engine: KanbanEngine) -> None:
        self.engine = engine

    def list_tasks(  # noqa: PLR0913
        self,
        *,
        status: str = "",
        tag: str = "",
        priority: str = "",
        archival_reason: str = "",
        ids: list[int] | None = None,
        parent: int | None = None,
        search: str = "",
        sort: str = "",
        unclaimed: bool = False,
        archived: bool = False,
        limit: int = 0,
        reverse: bool = False,
        blocked: bool | None = None,
    ) -> ListTasksResponse:
        """Delegate to :meth:`AgentView.list_tasks` with identical signature."""
        return self.engine.agent_view().list_tasks(
            status=status,
            tag=tag,
            priority=priority,
            archival_reason=archival_reason,
            ids=ids,
            parent=parent,
            search=search,
            sort=sort,
            unclaimed=unclaimed,
            archived=archived,
            limit=limit,
            reverse=reverse,
            blocked=blocked,
        )

    def show_task(self, task_id: int, section: str | None = None) -> ShowTaskResponse:
        """Delegate to :meth:`AgentView.show_task` with identical signature."""
        return self.engine.agent_view().show_task(task_id, section)

    @staticmethod
    def _to_single_response(task: Task) -> SingleTaskResponse:
        payload = task.model_dump()
        if isinstance(payload.get("body"), list):
            payload["body"] = None
        payload["guidance"] = []
        return SingleTaskResponse.model_validate(payload)

    @staticmethod
    def _to_task_response(response: SingleTaskResponse) -> SingleTaskResponse:
        payload = response.model_dump()
        payload["guidance"] = []
        return SingleTaskResponse.model_validate(payload)

    @staticmethod
    def _not_found(task_id: int) -> NotFoundError:
        return NotFoundError(
            code="ERR_NOT_FOUND",
            user_message=f"Task '{task_id}' not found",
        )

    def _has_archival_cycle(self, root_task_id: int, refs: list[int]) -> bool:
        def visits_root(task_id: int, seen: set[int]) -> bool:
            if task_id in seen:
                return False
            seen.add(task_id)
            try:
                task = self.engine.show_task(str(task_id))
            except FileNotFoundError:
                return False
            for dep_id in task.archival_refs:
                if dep_id == root_task_id:
                    return True
                if visits_root(dep_id, seen):
                    return True
            return False

        return any(visits_root(ref_id, set()) for ref_id in refs)

    def _validate_move_archival_for_archive(
        self,
        *,
        task_id: int,
        can_mark_completed: bool,
        config: BoardConfig,
        archival_reason: str | None,
        archival_refs: list[int],
    ) -> None:
        if not archival_reason:
            raise ValidationError(
                code="ERR_ARCHIVAL_REASON_REQUIRED",
                user_message="archival_reason is required when status='archived'",
            )
        if archival_reason not in config.policy.archival_reasons:
            raise ValidationError(
                code="ERR_ARCHIVAL_REASON_INVALID",
                user_message=(
                    "archival_reason must be one of "
                    f"{sorted(config.policy.archival_reasons)}"
                ),
            )
        if archival_reason in {"deprecated", "duplicate"} and not archival_refs:
            raise ValidationError(
                code="ERR_ARCHIVAL_REFS_REQUIRED",
                user_message=(
                    "archival_refs required for "
                    f"archival_reason='{archival_reason}'"
                ),
            )
        if archival_reason in {"completed", "dropped", "wontfix"} and archival_refs:
            raise ValidationError(
                code="ERR_ARCHIVAL_REFS_FORBIDDEN",
                user_message=(
                    "archival_refs forbidden for "
                    f"archival_reason='{archival_reason}'"
                ),
            )
        if archival_reason == "completed" and not can_mark_completed:
            raise ValidationError(
                code="ERR_COMPLETED_REQUIRES_DONE",
                user_message="archival_reason='completed' requires terminal status",
            )
        for ref_id in archival_refs:
            if ref_id == task_id:
                raise ValidationError(
                    code="ERR_ARCHIVAL_REF_SELF",
                    user_message="archival_refs cannot include the task itself",
                )
            try:
                self.engine.show_task(str(ref_id))
            except FileNotFoundError as exc:
                raise ValidationError(
                    code="ERR_ARCHIVAL_REF_MISSING",
                    user_message=f"archival reference task '{ref_id}' not found",
                ) from exc
        if self._has_archival_cycle(task_id, archival_refs):
            raise ValidationError(
                code="ERR_ARCHIVAL_REF_CYCLE",
                user_message="archival_refs would introduce a cycle",
            )

    def edit_task(  # noqa: C901, PLR0912, PLR0913
        self,
        task_id: int,
        *,
        expected_updated: str,
        title: str | None = None,
        body: str = "",
        append_body: str = "",
        timestamp: bool = False,
        priority: str = "",
        parent: int = 0,
        add_dep: list[int] | None = None,
        remove_dep: list[int] | None = None,
        add_tag: list[str] | None = None,
        remove_tag: list[str] | None = None,
        block_reason: str | None | object = _BLOCK_REASON_UNSET,
        archival_reason: str = "",
        archival_refs: list[int] | None = None,
    ) -> SingleTaskResponse:
        """Edit a task with OCC compare-and-swap validation for cockpit clients."""
        kwargs: dict[str, object] = {
            "expected_updated": expected_updated,
            "source": "cockpit",
        }
        if title is not None:
            kwargs["title"] = title
        if body:
            kwargs["body"] = body
        if append_body:
            kwargs["append_body"] = append_body
            kwargs["timestamp"] = timestamp
        if priority:
            kwargs["priority"] = priority
        if parent > 0:
            kwargs["parent"] = parent
        if add_dep is not None:
            kwargs["add_deps"] = add_dep
        if remove_dep is not None:
            kwargs["remove_deps"] = remove_dep
        if add_tag is not None:
            kwargs["add_tags"] = add_tag
        if remove_tag is not None:
            kwargs["remove_tags"] = remove_tag
        if block_reason is not _BLOCK_REASON_UNSET:
            if block_reason:
                kwargs["blocked"] = True
                kwargs["block_reason"] = block_reason
            else:
                kwargs["blocked"] = False
                kwargs["block_reason"] = None
        if archival_reason:
            kwargs["archival_reason"] = archival_reason
        if archival_refs is not None:
            kwargs["archival_refs"] = archival_refs

        try:
            task = self.engine.edit_task(str(task_id), **kwargs)
        except FileNotFoundError as exc:
            raise self._not_found(task_id) from exc
        except ValueError as exc:
            raise ValidationError(code="ERR_INVALID_STATUS", user_message=str(exc)) from exc
        return self._to_single_response(task)

    def move_task(
        self,
        task_id: int,
        status: str,
        *,
        expected_updated: str,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
    ) -> SingleTaskResponse:
        """Move a task with OCC compare-and-swap validation for cockpit clients."""
        try:
            if status == "archived":
                before = self.engine.show_task(str(task_id))
                config = self.engine.board_config()
                self._validate_move_archival_for_archive(
                    task_id=task_id,
                    can_mark_completed=before.status == config.pipeline.terminal_status,
                    config=config,
                    archival_reason=archival_reason,
                    archival_refs=archival_refs or [],
                )
            task = self.engine.move_task(
                str(task_id),
                status,
                archival_reason=archival_reason,
                archival_refs=archival_refs,
                expected_updated=expected_updated,
                source="cockpit",
            )
        except FileNotFoundError as exc:
            raise self._not_found(task_id) from exc
        except ValueError as exc:
            raise ValidationError(code="ERR_INVALID_STATUS", user_message=str(exc)) from exc
        return self._to_single_response(task)

    def release_task(
        self,
        task_id: int,
        *,
        expected_updated: str,
    ) -> SingleTaskResponse:
        """Release claim on task using OCC compare-and-swap.

        ``expected_updated`` is required; raises :class:`ConcurrencyError`
        (``ERR_STALE``) if the token does not match the stored ``updated``
        timestamp. Unclaimed tasks with a fresh token are returned unchanged
        without advancing ``updated``.
        """
        try:
            released = self.engine.release_task(
                str(task_id),
                expected_updated=expected_updated,
                source="cockpit",
            )
        except FileNotFoundError as exc:
            raise self._not_found(task_id) from exc
        return self._to_single_response(released)

    def sweep(self) -> list[int]:
        """Release expired claims and return released task IDs."""
        return self.engine.sweep()

    def list_activity(  # noqa: PLR0913
        self,
        *,
        task_id: int | None = None,
        action: str | None = None,
        source: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int | None = None,
    ) -> list[ActivityEvent]:
        """Return activity events filtered by task/action/source/time window."""
        return self.engine.list_activity(
            task_id=task_id,
            action=action,
            source=source,
            since=since,
            until=until,
            limit=limit,
        )

    def list_sessions(self, *, filter: str = "active") -> list[SessionRecord]:  # noqa: A002
        """Return derived session records with the requested filter."""
        return self.engine.list_sessions(filter=filter)

    def scan_corruption(self) -> list:
        """Read-only corruption scan for tasks and archive directories."""
        return self.engine.scan_corruption()

    def repair_storage(self) -> list:
        """Run two-phase storage repair and return repair outcomes."""
        return self.engine.repair_storage()

    def compact_activity(self) -> ActivityCompactionResult:
        """Compact activity log via storage delegate."""
        return self.engine.compact_activity()

    def board_config(self) -> BoardConfig:
        """Return board configuration."""
        return self.engine.board_config()
