"""CockpitView facade for cockpit-facing Kanban operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_kanban.models import (
    ActivityCompactionResult,
    ActivityEvent,
    BoardConfig,
    CleanupResult,
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
_FIELD_UNSET = object()


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

    def edit_task(  # noqa: C901, PLR0912, PLR0913
        self,
        task_id: int,
        *,
        expected_updated: str,
        title: str | None = None,
        body: str | None | object = _FIELD_UNSET,
        append_body: str = "",
        timestamp: bool = False,
        priority: str = "",
        parent: int | None | object = _FIELD_UNSET,
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
        if body is not _FIELD_UNSET:
            kwargs["body"] = body
        if append_body:
            kwargs["append_body"] = append_body
            kwargs["timestamp"] = timestamp
        if priority:
            kwargs["priority"] = priority
        if isinstance(parent, int) and parent < 0:
            raise ValidationError(
                code="ERR_PARENT_NOT_FOUND",
                user_message="parent must be >= 0 or null",
            )
        if parent is not _FIELD_UNSET:
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
                self.engine.validate_archival(
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

    def cleanup(self) -> CleanupResult:
        """Run maintenance cleanup and return released, archived, and skipped results."""
        return self.engine.cleanup()

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
