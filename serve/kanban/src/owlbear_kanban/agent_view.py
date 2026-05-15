"""Agent-facing Kanban view facade.

Extracted from engine.py to keep KanbanEngine focused on core board operations.
"""

from __future__ import annotations

import importlib
import re
from datetime import UTC, datetime

from owlbear_kanban._duration import _parse_duration
from owlbear_kanban.body_parser import parse_body
from owlbear_kanban.corruption import (
    CorruptionError,
)
from owlbear_kanban.dispatch import PRIORITY_RANK
from owlbear_kanban.engine import (
    _BLOCK_REASON_UNSET,
    KanbanEngine,
    _task_body_as_text,
)
from owlbear_kanban.models import (
    ConcurrencyError,
    ConfigError,
    DispatchEntry,
    ListTasksResponse,
    NotFoundError,
    PickTasksResponse,
    ShowTaskResponse,
    SingleTaskResponse,
    Task,
    ValidationError,
    Wave,
)


class AgentView:
    """Minimal role-scoped wrapper for agent-facing engine use."""

    _MAX_BODY_BYTES = 500 * 1024
    _BODY_SIZE_WARNING = (
        "\u26a0\ufe0f Task body is large (>100 KB); consider splitting."
    )
    _BLOCK_AR_HINT = (
        "\u26a0\ufe0f ACTION REQUIRED: Create a Decision Request via the create_dr tool."
        " Blocks without a DR are invisible to the pipeline."
    )

    def __init__(self, engine: KanbanEngine) -> None:
        self.engine = engine

    @staticmethod
    def _to_single_response(
        task: Task, guidance: list[str] | None = None
    ) -> SingleTaskResponse:
        payload = task.model_dump()
        if isinstance(payload.get("body"), list):
            payload["body"] = None
        payload["guidance"] = guidance or []
        return SingleTaskResponse.model_validate(payload)

    @staticmethod
    def _skip_transition_guidance(
        *,
        before_status: str,
        after_status: str,
        status_names: list[str],
        include_target_column: bool = False,
    ) -> list[str]:
        try:
            from_idx = status_names.index(before_status)
            to_idx = status_names.index(after_status)
        except ValueError:
            return []
        delta = abs(to_idx - from_idx)
        if delta <= 1:
            return []
        skipped = delta if include_target_column else delta - 1
        return [
            "\u26a0\ufe0f Status skip: moved from "
            f"'{before_status}' to '{after_status}' (skipped {skipped} column(s))."
            " Verify this jump is intentional."
        ]

    def _wrap_not_found(self, task_id: int) -> NotFoundError:
        return NotFoundError(
            code="ERR_NOT_FOUND",
            user_message=f"Task '{task_id}' not found",
        )

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
        """List tasks with optional filtering and input validation.

        When ``ids`` is supplied it searches both the active and archive
        directories and reports any requested IDs that were not found in
        ``missing_ids``.  ``ids`` is mutually exclusive with all other filters.

        Args:
            status:          Filter by status string.  Use ``"archived"`` to read
                             from the archive directory.  Mutually exclusive with
                             ``ids``.
            tag:             Filter by tag.  Mutually exclusive with ``ids``.
            priority:        Filter by priority enum value.  Mutually exclusive
                             with ``ids``.
            archival_reason: Filter archived tasks by archival reason enum value.
                             Mutually exclusive with ``ids``.
            ids:             Explicit list of task IDs to fetch; searches both
                             active and archive directories.
            parent:          Filter by parent task ID.  Mutually exclusive with
                             ``ids``.
            search:          Case-insensitive substring match on title and body.
            sort:            Sort field: id, title, status, priority, created,
                             updated.
            unclaimed:       When True, only unclaimed tasks.
            archived:        When True, read from archive/ instead of tasks_dir.
            limit:           Cap on results (0 = unlimited).
            reverse:         Reverse sort order when True.
            blocked:         True = only blocked; False = only unblocked; None = all.

        Returns:
            :class:`ListTasksResponse` with ``tasks``, ``guidance``, and
            ``missing_ids`` (populated only when ``ids`` is used and some IDs
            were not found).

        Raises:
            ValidationError: ``status``, ``priority``, or ``archival_reason`` is
                             not a recognised enum value, or ``ids`` is combined
                             with other filter arguments.
        """
        config = self.engine.board_config()

        if status and status != "archived" and status not in config.pipeline.statuses:
            raise ValidationError(
                code="ERR_INVALID_STATUS",
                user_message=f"status must be one of {[*config.pipeline.statuses, 'archived']}",
            )
        if priority and priority not in config.pipeline.priorities:
            raise ValidationError(
                code="ERR_INVALID_PRIORITY",
                user_message=f"priority must be one of {config.pipeline.priorities}",
            )
        if archival_reason and archival_reason not in config.policy.archival_reasons:
            raise ValidationError(
                code="ERR_ARCHIVAL_REASON_INVALID",
                user_message=(
                    f"archival_reason must be one of {sorted(config.policy.archival_reasons)}"
                ),
            )

        if ids and (
            status
            or tag
            or priority
            or parent is not None
            or search
            or unclaimed
            or blocked is not None
            or archival_reason
        ):
            raise ValidationError(
                code="ERR_IDS_EXCLUSIVE",
                user_message="ids cannot be combined with other filters",
            )

        missing_ids: list[int] | None = None
        if ids:
            active_tasks = self.engine.list_tasks(archived=False)
            archived_tasks = self.engine.list_tasks(archived=True)
            found_by_id = {task.id: task for task in [*active_tasks, *archived_tasks]}
            wanted = set(ids)
            tasks = [task for task_id, task in found_by_id.items() if task_id in wanted]
            found = {task.id for task in tasks}
            missing = sorted(wanted - found)
            missing_ids = missing or None
        else:
            read_archived = archived or status == "archived"
            tasks = self.engine.list_tasks(
                status=status,
                tag=tag,
                priority=priority,
                parent=parent,
                search=search,
                sort=sort,
                unclaimed=unclaimed,
                archived=read_archived,
                limit=limit,
                reverse=reverse,
                blocked=blocked,
            )
            if archival_reason:
                tasks = [
                    task for task in tasks if task.archival_reason == archival_reason
                ]

        return ListTasksResponse(tasks=tasks, guidance=[], missing_ids=missing_ids)

    def show_task(self, task_id: int, section: str | None = None) -> ShowTaskResponse:
        """Fetch a single task by ID with optional section extraction.

        When ``section`` is provided only the body content under matching
        headings is returned (case-insensitive).  Multiple heading matches are
        concatenated.  If the heading is absent, ``body`` is set to ``None`` and
        ``missing_sections`` is populated.

        Args:
            task_id: Numeric task ID (integer).
            section: Heading name to extract.  ``None`` returns the full body.

        Returns:
            :class:`ShowTaskResponse` with the task payload, ``guidance``
            (populated when multiple section matches occur), and
            ``missing_sections`` (populated when the requested heading is absent).

        Raises:
            ValidationError: ``section`` is an empty string.
            NotFoundError:   No task with the given ID exists in the active or
                             archive directories.
        """
        try:
            task = self.engine.show_task(str(task_id))
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc

        payload = task.model_dump()
        if isinstance(payload.get("body"), list):
            payload["body"] = None

        active_ids: set[int] = set()
        archived_reasons: dict[int, str | None] = {}
        for dep_id in task.depends_on or []:
            try:
                dep_task = self.engine.show_task(str(dep_id))
            except (FileNotFoundError, CorruptionError, ValueError, KeyError):
                continue

            if dep_task.status == "archived":
                archived_reasons[dep_id] = dep_task.archival_reason
            else:
                active_ids.add(dep_id)

        payload["dep_status"] = self.engine._compute_dep_status(  # noqa: SLF001
            task,
            active_ids=active_ids,
            archived_reasons=archived_reasons,
        )

        guidance: list[str] = []
        missing_sections: list[str] | None = None

        if section is not None:
            section_name = section.strip()
            if not section_name:
                raise ValidationError(
                    code="ERR_SECTION_EMPTY",
                    user_message="section must not be an empty string",
                )

            body_text = (
                payload.get("body") if isinstance(payload.get("body"), str) else ""
            )
            matches = [
                part
                for part in parse_body(body_text)
                if part.heading is not None
                and part.heading.strip().casefold() == section_name.casefold()
            ]
            if not matches:
                payload["body"] = None
                missing_sections = [section_name]
            else:
                payload["body"] = "\n".join(match.content for match in matches)
                if len(matches) > 1:
                    guidance.append(
                        f"Section '{section_name}' matched {len(matches)} occurrences."
                    )

        payload["guidance"] = guidance
        payload["missing_sections"] = missing_sections
        return ShowTaskResponse.model_validate(payload)

    def pick_tasks(  # noqa: C901, PLR0912, PLR0915
        self, wave_size: int | None = None, max_waves: int = 3
    ) -> PickTasksResponse:
        """Select dispatchable tasks and arrange them into dependency-disjoint waves.

          Runs a five-step pipeline:

          1. **Validate** — ensure every status in ``config.pipeline.statuses``
              has an ``agent_map`` entry.

          2. **Filter** — exclude tasks with an active claim (per configured
           ``claim_timeout``), archived, ``blocked=True``, and
           tasks with unresolved active dependencies, archived, ``blocked=True``,
           and ``dep_status="blocked"`` tasks; rehydrate each candidate with
           ``show_task()`` to obtain the full body, skip any whose
           ``status == "archived"`` (post-rehydrate guard), then apply the
           TDD gate (in-progress tasks require ``## Test-Writer Notes`` or a
           non-impl tag) and the clarity gate (active-status tasks require
           at least one bullet/numbered AC line).  Gate predicates are
           resolved from ``owlbear_kanban.dispatch``.
          3. **Sort** — deterministic ordering: ``priority_rank ASC``,
           age (oldest first) ``DESC``, ``id ASC``.
          4. **Greedy wave assembly** — fill waves respecting three constraints:
           wave size cap, dependency disjointness (no intra-wave dep edges),
           and agent-bucket compatibility.
          5. **Agent assignment** — each :class:`DispatchEntry` carries the full
           ``BoardConfig.agent_map`` value for the task's status.

        Args:
            wave_size:  Maximum tasks per wave.  Defaults to
                        ``BoardConfig.wave_size``.
            max_waves:  Maximum number of waves to produce (default ``3``).

        Returns:
            :class:`PickTasksResponse` with ``waves`` and ``guidance``.
            Tasks that cannot be placed when ``max_waves`` is exhausted are
            dropped for the current cycle; the count is reported in
            ``guidance``.

        Raises:
            ValidationError: ``wave_size < 1``, ``max_waves < 1``, or the
                             effective wave size resolved from config is
                             ``< 1`` (``ERR_INVALID_WAVE_PARAM``).
            ConfigError: when ``agent_map`` is missing status entries
                         (``ERR_INVALID_STATUS``).
        """
        if max_waves < 1:
            raise ValidationError(
                code="ERR_INVALID_WAVE_PARAM",
                user_message="max_waves must be >= 1",
            )
        if wave_size is not None and wave_size < 1:
            raise ValidationError(
                code="ERR_INVALID_WAVE_PARAM",
                user_message="wave_size must be >= 1",
            )

        config = self.engine.board_config()
        effective_wave = (
            wave_size if wave_size is not None else config.pipeline.wave_size
        )
        if effective_wave < 1:
            raise ValidationError(
                code="ERR_INVALID_WAVE_PARAM",
                user_message="wave_size must be >= 1",
            )

        missing_statuses = [
            status
            for status in config.pipeline.statuses
            if status not in config.agents.agent_map
        ]
        if missing_statuses:
            raise ConfigError(
                code="ERR_INVALID_STATUS",
                user_message=f"agent_map missing status entries: {missing_statuses}",
            )

        claim_timeout = _parse_duration(config.pipeline.claim_timeout)
        dispatch_module = importlib.import_module("owlbear_kanban.dispatch")
        claim_is_active = dispatch_module._claim_is_active  # noqa: SLF001

        active = self.engine.list_tasks(
            archived=False,
            blocked=False,
            sort="created",
        )
        active = [task for task in active if not claim_is_active(task, claim_timeout)]
        # list_tasks computes dep_status against the full active snapshot before
        # filters, so use the projected value directly to avoid reclassifying
        # dependencies based on the filtered subset.
        dispatchable = [
            task
            for task in active
            if task.dep_status != "blocked" and task.status != "archived"
        ]
        passes_tdd = dispatch_module._passes_tdd_gate  # noqa: SLF001
        passes_clarity = dispatch_module._passes_clarity_gate  # noqa: SLF001

        gated_dispatchable: list[Task] = []
        for task in dispatchable:
            try:
                full_task = self.engine.show_task(str(task.id))
            except FileNotFoundError:
                continue
            if full_task.status == "archived":
                continue
            if not passes_tdd(full_task):
                continue
            if not passes_clarity(full_task):
                continue
            gated_dispatchable.append(full_task)

        dispatchable = gated_dispatchable
        if not dispatchable:
            return PickTasksResponse(waves=[], guidance=[])

        created_rank = {task.id: index for index, task in enumerate(active)}

        priority_rank = PRIORITY_RANK

        ordered = sorted(
            dispatchable,
            key=lambda task: (
                priority_rank.get(task.priority, len(priority_rank)),
                created_rank.get(task.id, len(created_rank)),
                task.id,
            ),
        )

        status_agents = config.agents.agent_map
        agent_types = config.agents.agent_types
        compatibility = config.agents.agent_compatibility

        def _dispatch_agent_for_status(status: str) -> str:
            mapped = status_agents.get(status, "")
            if isinstance(mapped, list):
                return str(mapped[0]) if mapped else ""
            return str(mapped)

        def _agent_bucket(agent: str) -> str:
            mapped = agent_types.get(agent, "")
            if isinstance(mapped, str):
                return mapped
            return str(mapped)

        def _has_dep_edge(left: Task, right: Task) -> bool:
            left_deps = set(left.depends_on or [])
            right_deps = set(right.depends_on or [])
            return right.id in left_deps or left.id in right_deps

        def _buckets_compatible(existing_bucket: str, candidate_bucket: str) -> bool:
            if not compatibility:
                return True
            existing_allowed = set(compatibility.get(existing_bucket, []))
            candidate_allowed = set(compatibility.get(candidate_bucket, []))
            return (
                candidate_bucket in existing_allowed
                and existing_bucket in candidate_allowed
            )

        wave_tasks: list[list[Task]] = []
        dropped = 0
        for task in ordered:
            candidate_agent = _dispatch_agent_for_status(task.status)
            candidate_bucket = _agent_bucket(candidate_agent)
            placed = False

            for wave in wave_tasks:
                if len(wave) >= effective_wave:
                    continue
                if any(_has_dep_edge(existing, task) for existing in wave):
                    continue

                compatible = True
                for existing in wave:
                    existing_agent = _dispatch_agent_for_status(existing.status)
                    existing_bucket = _agent_bucket(existing_agent)
                    if not _buckets_compatible(existing_bucket, candidate_bucket):
                        compatible = False
                        break
                if not compatible:
                    continue

                wave.append(task)
                placed = True
                break

            if placed:
                continue

            if len(wave_tasks) < max_waves:
                wave_tasks.append([task])
            else:
                dropped += 1

        waves: list[Wave] = []
        dispatched_count = 0
        for wave_index, chunk in enumerate(wave_tasks):
            entries = [
                DispatchEntry(
                    id=task.id,
                    status=task.status,
                    priority=task.priority,
                    title=task.title,
                    tags=list(task.tags),
                    agent=_dispatch_agent_for_status(task.status),
                )
                for task in chunk
            ]
            dispatched_count += len(entries)
            waves.append(Wave(index=wave_index, tasks=entries))

        guidance = [
            f"Dispatch hints: {dispatched_count} task(s) across {len(waves)} wave(s)."
        ]
        if dropped:
            guidance.append(
                f"Dropped {dropped} task(s) because no wave fit within max_waves."
            )
        return PickTasksResponse(waves=waves, guidance=guidance)

    def create_task(  # noqa: PLR0913
        self,
        *,
        title: str,
        body: str = "",
        priority: str = "",
        tags: list[str] | None = None,
        parent: int | None = None,
        depends_on: list[int] | None = None,
        ac: list[str] | None = None,
        proof_bundle: str | None = None,
    ) -> SingleTaskResponse:
        """Create a new task at the board's entry_status.

        Tasks are always created at ``BoardConfig.entry_status``; there is no
        ``status`` parameter (D50).  The entry_status predicate is evaluated
        against *body* before the task is written.

        Args:
            title:      Task title (must be non-empty).
            body:       Initial markdown body.  Must not exceed 500 KB.
            priority:   Task priority; defaults to ``BoardConfig.defaults.priority``.
            tags:       Initial tag list.
            parent:     Optional parent task ID; must refer to an existing task.
            depends_on: Optional dependency task IDs; each must refer to an existing task.
            ac:         Optional acceptance-criteria list to persist on the task.
            proof_bundle: Optional proof-bundle value to persist on the task.

        Returns:
            :class:`SingleTaskResponse` for the newly created task, including
            a ``guidance`` warning when ``body`` exceeds 100 KB.

        Raises:
            :class:`ValidationError`: title is empty (``ERR_INVALID_STATUS``),
                body exceeds 500 KB (``ERR_BODY_TOO_LARGE``),
                parent not found (``ERR_PARENT_NOT_FOUND``),
                a dependency not found (``ERR_DEP_NOT_FOUND``), or
                the entry_status predicate is not satisfied (``ERR_PREDICATE_FAILED``).
        """
        if not title.strip():
            raise ValidationError(
                code="ERR_INVALID_TITLE",
                user_message="title must not be empty",
            )
        self.engine.validate_body_size(body)

        if parent is not None and not self.engine.task_exists(parent):
            raise ValidationError(
                code="ERR_PARENT_NOT_FOUND",
                user_message=f"Parent task '{parent}' not found",
            )

        dep_ids = depends_on or []
        missing_dep = next(
            (dep_id for dep_id in dep_ids if not self.engine.task_exists(dep_id)),
            None,
        )
        if missing_dep is not None:
            raise ValidationError(
                code="ERR_DEP_NOT_FOUND",
                user_message=f"Dependency task '{missing_dep}' not found",
            )

        config = self.engine.board_config()
        entry_status = config.pipeline.entry_status
        self.engine.validate_status_predicate(
            target_status=entry_status,
            body=body,
            config=config,
        )

        try:
            task = self.engine.create_task(
                title=title,
                body=body,
                status=entry_status,
                priority=priority,
                tags=tags,
                parent=parent,
                depends_on=depends_on,
                ac=ac,
                proof_bundle=proof_bundle,
            )
        except ValueError as exc:
            raise ValidationError(
                code="ERR_INVALID_STATUS", user_message=str(exc)
            ) from exc

        guidance: list[str] = []
        if len(body.encode("utf-8")) > 100 * 1024:
            guidance.append(self._BODY_SIZE_WARNING)
        return self._to_single_response(task, guidance)

    def edit_task(  # noqa: C901, PLR0912, PLR0913, PLR0915
        self,
        task_id: int,
        *,
        title: str | None = None,
        body: str | None = None,
        append_body: str | None = None,
        timestamp: bool = False,
        priority: str | None = None,
        parent: int | None = None,
        ac: list[str] | None = None,
        add_ac: list[str] | None = None,
        remove_ac: list[str] | None = None,
        proof_bundle: str | None = None,
        add_dep: list[int] | None = None,
        remove_dep: list[int] | None = None,
        add_tag: list[str] | None = None,
        remove_tag: list[str] | None = None,
        block_reason: str | None | object = _BLOCK_REASON_UNSET,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
    ) -> SingleTaskResponse:
        """Edit fields on an existing task with semantic no-op detection.

        Raises ``ERR_NO_OP`` when all requested changes are already reflected in
        the current task state (D46-last-writer-wins; no ``expected_updated`` param).

        ``body`` and ``append_body`` are mutually exclusive.  When ``timestamp``
        is ``True``, an ISO-8601 datestamp line is prepended to ``append_body``.
        The post-append total body size is validated against the 500 KB hard cap.

        Archival fields (``archival_reason``, ``archival_refs``) are only
        permitted on archived tasks and are validated against the configured
        archival-refs matrix (§3.2).

        A non-empty *block_reason* sets ``blocked=True`` and stores the reason;
        an empty or ``None`` *block_reason* clears both fields (D53).

        Args:
            task_id:        Numeric task ID.
            title:          Replace task title (non-empty when provided).
            body:           Tri-state body control: ``None`` means no change, ``""`` clears
                            the body, non-empty text replaces the body.  Mutually exclusive
                            with *append_body*.
            append_body:    Text to append to the existing body.
            timestamp:      When ``True``, prepend an ISO-8601 datestamp to *append_body*.
            priority:       Replace task priority.
            parent:         Replace parent task ID (``0`` clears parent).
            ac:             Replace the task acceptance-criteria list.
            add_ac:         Append acceptance-criteria items to the existing list.
            remove_ac:      Remove acceptance-criteria items from the existing list.
            proof_bundle:   Replace proof-bundle value.
            add_dep:        Dependency IDs to add.
            remove_dep:     Dependency IDs to remove.
            add_tag:        Tags to add.
            remove_tag:     Tags to remove.
            block_reason:   Set or clear the block flag and reason (D53).
            archival_reason: Replace archival reason on an archived task.
            archival_refs:  Replace archival reference IDs on an archived task.

        Returns:
            :class:`SingleTaskResponse` reflecting the updated task, with a
            ``guidance`` warning when the resulting body exceeds 100 KB.

        Raises:
            :class:`ValidationError`: task not found (``ERR_TASK_NOT_FOUND``),
                *body* and *append_body* both set (``ERR_BODY_EXCLUSIVE``),
                body exceeds 500 KB (``ERR_BODY_TOO_LARGE``),
                parent not found (``ERR_PARENT_NOT_FOUND``),
                a dependency not found (``ERR_DEP_NOT_FOUND``),
                archival fields on a non-archived task (``ERR_ARCHIVAL_FIELDS_FORBIDDEN``),
                archival-refs matrix violation (various ``ERR_ARCHIVAL_*`` codes),
                no effective change detected (``ERR_NO_OP``).
        """
        try:
            existing = self.engine.show_task(str(task_id))
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc

        config = self.engine.board_config()
        title_set = title is not None
        body_set = body is not None
        append_set = bool(append_body)
        parent_set = parent is not None
        # Task IDs are 1-based, so parent=0 is an unambiguous clear sentinel.
        parent_value = None if parent == 0 else parent
        archival_reason_set = archival_reason is not None
        archival_refs_set = archival_refs is not None
        block_reason_set = block_reason is not _BLOCK_REASON_UNSET
        append_payload = append_body or ""
        append_resulting_body = ""

        if title_set and (title is None or not title.strip()):
            raise ValidationError(
                code="ERR_INVALID_TITLE",
                user_message="title must not be empty",
            )

        if body_set and append_set:
            raise ValidationError(
                code="ERR_BODY_EXCLUSIVE",
                user_message="body and append_body cannot both be set",
            )

        if body_set:
            self.engine.validate_body_size(body)

        if (
            parent_set
            and parent_value is not None
            and not self.engine.task_exists(parent_value)
        ):
            raise ValidationError(
                code="ERR_PARENT_NOT_FOUND",
                user_message=f"Parent task '{parent_value}' not found",
            )

        for dep_id in add_dep or []:
            if not self.engine.task_exists(dep_id):
                raise ValidationError(
                    code="ERR_DEP_NOT_FOUND",
                    user_message=f"Dependency task '{dep_id}' not found",
                )

        if append_set:
            if timestamp:
                stamp = datetime.now(tz=UTC).replace(microsecond=0).isoformat()
                append_payload = f"{stamp}\n{append_body}"
            current_body = existing.body if isinstance(existing.body, str) else ""
            append_resulting_body = current_body + "\n" + append_payload
            self.engine.validate_body_size(append_resulting_body)

        if archival_reason_set or archival_refs_set:
            if existing.status != "archived":
                raise ValidationError(
                    code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
                    user_message="archival fields are only allowed on archived tasks",
                )

            effective_reason = (
                archival_reason
                if archival_reason_set
                else (existing.archival_reason or "")
            )
            effective_refs = (
                archival_refs if archival_refs_set else list(existing.archival_refs)
            )
            self.engine.validate_archival(
                task_id=task_id,
                archival_reason=effective_reason,
                archival_refs=effective_refs,
                can_mark_completed=existing.status == config.pipeline.terminal_status,
                config=config,
            )

        kwargs: dict[str, object] = {}
        if title_set:
            kwargs["title"] = title
        if body_set:
            kwargs["body"] = body
        if append_set:
            kwargs["append_body"] = append_payload
        if priority is not None:
            kwargs["priority"] = priority
        if parent_set:
            kwargs["parent"] = parent_value
        if ac is not None:
            kwargs["ac"] = ac
        if add_ac is not None:
            kwargs["add_ac"] = add_ac
        if remove_ac is not None:
            kwargs["remove_ac"] = remove_ac
        if proof_bundle is not None:
            kwargs["proof_bundle"] = proof_bundle
        if add_dep is not None:
            kwargs["add_deps"] = add_dep
        if remove_dep is not None:
            kwargs["remove_deps"] = remove_dep
        if add_tag is not None:
            kwargs["add_tags"] = add_tag
        if remove_tag is not None:
            kwargs["remove_tags"] = remove_tag
        if block_reason_set:
            if block_reason:
                kwargs["blocked"] = True
                kwargs["block_reason"] = block_reason
            else:
                kwargs["blocked"] = False
                kwargs["block_reason"] = None
        if archival_reason_set:
            kwargs["archival_reason"] = archival_reason
        if archival_refs_set:
            kwargs["archival_refs"] = archival_refs

        if not kwargs and not archival_reason_set and not archival_refs_set:
            raise ValidationError(
                code="ERR_NO_OP",
                user_message="No changes requested",
            )

        changes_requested = False
        if title_set and title != existing.title:
            changes_requested = True
        if body_set and _task_body_as_text(body).rstrip("\n") != _task_body_as_text(
            existing.body
        ).rstrip("\n"):
            changes_requested = True
        if append_set:
            changes_requested = True
        if priority is not None and priority != existing.priority:
            changes_requested = True
        if parent_set and parent_value != existing.parent:
            changes_requested = True
        if ac is not None and list(ac) != list(existing.ac):
            changes_requested = True
        if add_ac is not None and any(item not in existing.ac for item in add_ac):
            changes_requested = True
        if remove_ac is not None and any(item in existing.ac for item in remove_ac):
            changes_requested = True
        if proof_bundle is not None and proof_bundle != existing.proof_bundle:
            changes_requested = True
        if add_dep is not None and any(
            dep_id not in existing.depends_on for dep_id in add_dep
        ):
            changes_requested = True
        if remove_dep is not None and any(
            dep_id in existing.depends_on for dep_id in remove_dep
        ):
            changes_requested = True
        if add_tag is not None and any(tag not in existing.tags for tag in add_tag):
            changes_requested = True
        if remove_tag is not None and any(tag in existing.tags for tag in remove_tag):
            changes_requested = True
        if block_reason_set:
            if block_reason:
                changes_requested = changes_requested or (
                    existing.blocked is not True
                    or existing.block_reason != block_reason
                )
            else:
                changes_requested = changes_requested or (
                    existing.blocked is not False or existing.block_reason is not None
                )
        if archival_reason_set:
            changes_requested = changes_requested or (
                (archival_reason or None) != (existing.archival_reason or None)
            )
        if archival_refs_set:
            changes_requested = changes_requested or (
                list(archival_refs or []) != list(existing.archival_refs)
            )

        if not changes_requested:
            raise ValidationError(
                code="ERR_NO_OP",
                user_message="No changes requested",
            )

        try:
            task = self.engine.edit_task(str(task_id), source="agent", **kwargs)
        except ValueError as exc:
            raise ValidationError(
                code="ERR_INVALID_STATUS", user_message=str(exc)
            ) from exc

        guidance: list[str] = []
        if body_set and len(_task_body_as_text(body).encode("utf-8")) > 100 * 1024:
            guidance.append(self._BODY_SIZE_WARNING)
        if append_set and len(append_resulting_body.encode("utf-8")) > 100 * 1024:
            guidance.append(self._BODY_SIZE_WARNING)
        return self._to_single_response(task, guidance)

    def move_task(
        self,
        task_id: int,
        status: str,
        *,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
    ) -> SingleTaskResponse:
        """Change the task's status with validation.

        Validates archival constraints when *status* is ``"archived"`` and
        forbids archival fields on any other transition.  Runs the configured
        status predicate before mutation.

        Args:
            task_id:         Numeric task ID.
            status:          Target status string or ``"archived"``.
            archival_reason: Required when *status* is ``"archived"``.
            archival_refs:   Optional list of related task IDs when archiving.

        Returns:
            :class:`SingleTaskResponse` with the updated task and any
            ``guidance`` strings (e.g. skip-column warning).

        Raises:
            :class:`ValidationError`: Invalid status (``ERR_INVALID_STATUS``),
                archival fields on a non-archived move
                (``ERR_ARCHIVAL_FIELDS_FORBIDDEN``), or archival constraint
                violation (various ``ERR_ARCHIVAL_*`` codes).
            :class:`NotFoundError`: No task matching *task_id*.
        """
        try:
            before = self.engine.show_task(str(task_id))
            config = self.engine.board_config()

            if status == "archived":
                self.engine.validate_archival(
                    task_id=task_id,
                    can_mark_completed=before.status == config.pipeline.terminal_status,
                    config=config,
                    archival_reason=archival_reason,
                    archival_refs=archival_refs or [],
                )
            elif archival_reason is not None or archival_refs is not None:
                raise ValidationError(
                    code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
                    user_message="archival fields are only allowed on archived tasks",
                )

            body = before.body if isinstance(before.body, str) else ""
            self.engine.validate_status_predicate(
                target_status=status,
                body=body,
                config=config,
            )

            task = self.engine.move_task(
                str(task_id),
                status,
                archival_reason=archival_reason,
                archival_refs=archival_refs,
                source="agent",
            )
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc
        except ValueError as exc:
            raise ValidationError(
                code="ERR_INVALID_STATUS", user_message=str(exc)
            ) from exc

        guidance = self._skip_transition_guidance(
            before_status=before.status,
            after_status=task.status,
            status_names=self.engine.board_config().statuses,
        )
        return self._to_single_response(task, guidance)

    def start_work(self, task_id: int) -> SingleTaskResponse:
        """Claim a task for this agent and return the full task record.

        Archived and blocked tasks cannot be claimed.  Concurrent claims by
        another agent raise ``ConcurrencyError``.

        Args:
            task_id: Numeric task ID.

        Returns:
            :class:`SingleTaskResponse` with the claimed task's current state.

        Raises:
            :class:`ValidationError`: Task is archived
                (``ERR_ARCHIVED_NOT_CLAIMABLE``) or blocked
                (``ERR_BLOCKED_NOT_CLAIMABLE``).
            :class:`ConcurrencyError`: Task is already claimed by another
                agent (``ERR_ALREADY_CLAIMED``).
            :class:`NotFoundError`: No task matching *task_id*.
        """
        guidance: list[str] = []
        try:
            task_record = self.engine.show_task(str(task_id))
            if task_record.status == "archived":
                raise ValidationError(
                    code="ERR_ARCHIVED_NOT_CLAIMABLE",
                    user_message=f"Task '{task_id}' is archived and cannot be claimed",
                )

            active_ids: set[int] = set()
            archived_reasons: dict[int, str | None] = {}
            for dep_id in task_record.depends_on or []:
                try:
                    dep_task = self.engine.show_task(str(dep_id))
                except (FileNotFoundError, CorruptionError, ValueError, KeyError):
                    continue

                if dep_task.status == "archived":
                    archived_reasons[dep_id] = dep_task.archival_reason
                else:
                    active_ids.add(dep_id)

            dep_status = self.engine._compute_dep_status(  # noqa: SLF001
                task_record,
                active_ids=active_ids,
                archived_reasons=archived_reasons,
            )

            if dep_status == "blocked" and active_ids:
                dep_ids = ", ".join(
                    str(dep_id)
                    for dep_id in (task_record.depends_on or [])
                    if dep_id in active_ids
                )
                guidance.append(
                    "⚠️ This task has unresolved dependencies "
                    f"(IDs: {dep_ids}). "
                    "Review and confirm with the user that starting this work is intentional."
                )

            task = self.engine.start_work(str(task_id))
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc
        except ValueError as exc:
            msg = str(exc)
            if "already claimed" in msg:
                claimed_at_match = re.search(r"claimed_at=([^\)\s]+)", msg)
                claimed_at_hint = (
                    f" (claimed_at={claimed_at_match.group(1)})"
                    if claimed_at_match is not None
                    else ""
                )
                raise ConcurrencyError(
                    code="ERR_ALREADY_CLAIMED",
                    user_message=(
                        f"Task '{task_id}' is already claimed by another agent"
                        f"{claimed_at_hint}"
                    ),
                ) from exc
            if "blocked" in msg and "cannot be claimed" in msg:
                raise ValidationError(
                    code="ERR_BLOCKED_NOT_CLAIMABLE",
                    user_message=f"Task '{task_id}' is blocked and cannot be claimed",
                ) from exc
            raise ValidationError(code="ERR_INVALID_STATUS", user_message=msg) from exc
        return self._to_single_response(task, guidance)

    def end_work(  # noqa: C901, PLR0912, PLR0913, PLR0915
        self,
        task_id: int,
        *,
        outcome: str,
        note: str,
        move_to: str | None = None,
        block_reason: str | None = None,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
    ) -> SingleTaskResponse:
        """Validate the outcome parameter matrix and finalise the work session.

        Enforces agent-facing constraints before any mutation: the task is
        left unchanged if validation fails (D41 atomicity).

        Args:
            task_id:         Numeric task ID.
            outcome:         One of ``"success"``, ``"fail"``, ``"reject"``,
                             ``"block"``, or ``"release"``.
            note:            Text appended with an ISO-8601 timestamp prefix.
                             Ignored for ``"release"`` on an unclaimed task.
            move_to:         Required when *outcome* is ``"reject"``; target
                             status or ``"archived"``.  Optional additional
                             status move when *outcome* is ``"block"``.
                             Optional status move on ``"success"``.
                             Forbidden on ``"release"``.
            block_reason:    Non-empty, non-whitespace string required when
                             *outcome* is ``"block"``; stored on the task.
                             Forbidden on all other outcomes.
            archival_reason: Required when *move_to* is ``"archived"``; stored
                             on the task.  Forbidden otherwise.
            archival_refs:   Optional list of related task IDs when archiving.
                             Forbidden when not archiving.

        Returns:
            :class:`SingleTaskResponse` with the updated task state and any
            guidance strings (e.g. skip-warning, block AR hint).

        Raises:
            :class:`ValidationError`: Parameter matrix violation, invalid
                outcome, blank *block_reason*, unclaimed task on a mutating
                outcome, or predicate failure on the destination status.
            :class:`ConcurrencyError`: Task already claimed by another agent.
            :class:`NotFoundError`: No task matching *task_id*.
        """
        config = self.engine.board_config()
        effective_archival_refs = list(archival_refs or [])

        valid_outcomes = {"success", "fail", "reject", "block", "release"}

        if outcome == "success":
            if move_to is not None:
                # Validate move_to is a valid pipeline status
                statuses = list(config.pipeline.statuses)
                if move_to not in statuses:
                    raise ValidationError(
                        code="ERR_MOVE_TO_INVALID_STATUS",
                        user_message=(
                            f"move_to={move_to!r} is not a valid pipeline status"
                        ),
                    )
            if archival_reason is not None or archival_refs is not None:
                raise ValidationError(
                    code="ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS",
                    user_message="archival fields are forbidden when outcome='success'",
                )
            if block_reason is not None:
                raise ValidationError(
                    code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
                    user_message="block_reason is only allowed when outcome='block'",
                )
        elif outcome == "fail":
            if move_to is not None:
                raise ValidationError(
                    code="ERR_MOVE_TO_FORBIDDEN_ON_FAIL",
                    user_message="move_to is forbidden when outcome='fail'",
                )
            if archival_reason is not None or archival_refs is not None:
                raise ValidationError(
                    code="ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL",
                    user_message="archival fields are forbidden when outcome='fail'",
                )
            if block_reason is not None:
                raise ValidationError(
                    code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
                    user_message="block_reason is only allowed when outcome='block'",
                )
        elif outcome == "reject":
            if block_reason is not None:
                raise ValidationError(
                    code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
                    user_message="block_reason is only allowed when outcome='block'",
                )
            if move_to is None:
                raise ValidationError(
                    code="ERR_REJECT_REQUIRES_MOVE_TO",
                    user_message="move_to is required when outcome='reject'",
                )
            valid_statuses = set(config.pipeline.statuses)
            valid_statuses.add("archived")
            if move_to not in valid_statuses:
                raise ValidationError(
                    code="ERR_INVALID_STATUS",
                    user_message=(f"move_to must be one of {sorted(valid_statuses)}"),
                )
            if move_to == "archived":
                self.engine.validate_archival(
                    task_id=task_id,
                    can_mark_completed=False,
                    config=config,
                    archival_reason=archival_reason,
                    archival_refs=effective_archival_refs,
                )
            elif archival_reason is not None or archival_refs is not None:
                raise ValidationError(
                    code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
                    user_message="archival fields are only allowed when move_to='archived'",
                )
        elif outcome == "block":
            if archival_reason is not None or archival_refs is not None:
                raise ValidationError(
                    code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
                    user_message="archival fields are forbidden when outcome='block'",
                )
            if block_reason is None or not block_reason.strip():
                raise ValidationError(
                    code="ERR_BLOCK_REASON_REQUIRED",
                    user_message="block_reason is required when outcome='block'",
                )
            if move_to is not None and move_to not in set(config.pipeline.statuses):
                raise ValidationError(
                    code="ERR_INVALID_STATUS",
                    user_message=f"move_to must be one of {sorted(config.pipeline.statuses)}",
                )
        elif outcome == "release":
            if move_to is not None:
                raise ValidationError(
                    code="ERR_MOVE_TO_FORBIDDEN_ON_RELEASE",
                    user_message="move_to is forbidden when outcome='release'",
                )
            if archival_reason is not None or archival_refs is not None:
                raise ValidationError(
                    code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
                    user_message="archival fields are forbidden when outcome='release'",
                )
            if block_reason is not None:
                raise ValidationError(
                    code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
                    user_message="block_reason is only allowed when outcome='block'",
                )
        elif outcome not in valid_outcomes:
            raise ValidationError(
                code="ERR_INVALID_OUTCOME",
                user_message=f"Unknown outcome: {outcome!r}",
            )

        try:
            before = self.engine.show_task(str(task_id))

            claimed = before.claimed_at is not None
            if outcome == "release" and not claimed:
                unchanged = before.model_copy(deep=True)
                unchanged.body = _task_body_as_text(unchanged.body).rstrip("\n")
                return self._to_single_response(unchanged)
            if outcome in {"success", "fail", "reject", "block"} and not claimed:
                raise ValidationError(
                    code="ERR_NOT_CLAIMED",
                    user_message=(
                        "Task must be claimed before ending work with "
                        f"outcome='{outcome}'"
                    ),
                )

            body = _task_body_as_text(before.body)
            if outcome == "success":
                statuses = list(config.pipeline.statuses)
                if before.status in statuses:
                    current_idx = statuses.index(before.status)
                    if current_idx < len(statuses) - 1:
                        self.engine.validate_status_predicate(
                            target_status=statuses[current_idx + 1],
                            body=body,
                            config=config,
                        )
            elif outcome in {"reject", "block"} and move_to is not None:
                self.engine.validate_status_predicate(
                    target_status=move_to,
                    body=body,
                    config=config,
                )

            if outcome == "release":
                task = self.engine.release_task(
                    str(task_id),
                    source="agent",
                    note=note,
                )
            else:
                safe_block_reason = block_reason or ""
                task = self.engine.end_work(
                    str(task_id),
                    note=note,
                    outcome=outcome,
                    block_reason=safe_block_reason,
                    move_to=move_to,
                    archival_reason=archival_reason,
                    archival_refs=effective_archival_refs,
                    expected_updated=before.updated,
                    source="agent",
                )
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc
        except ConcurrencyError as exc:
            if exc.code == "ERR_STALE":
                latest = self.engine.show_task(str(task_id))
                if (
                    outcome in {"success", "fail", "reject", "block"}
                    and latest.claimed_at is None
                ):
                    raise ValidationError(
                        code="ERR_NOT_CLAIMED",
                        user_message=(
                            "Task must be claimed before ending work with "
                            f"outcome='{outcome}'"
                        ),
                    ) from exc
                raise ConcurrencyError(
                    code="ERR_STALE",
                    user_message=f"Task '{task_id}' changed concurrently; reload and retry",
                ) from exc
            raise
        except ValueError as exc:
            msg = str(exc)
            if "already claimed" in msg:
                raise ConcurrencyError(
                    code="ERR_ALREADY_CLAIMED",
                    user_message=f"Task '{task_id}' is already claimed by another agent",
                ) from exc
            raise ValidationError(code="ERR_INVALID_OUTCOME", user_message=msg) from exc

        guidance: list[str] = []
        if outcome == "reject":
            guidance = self._skip_transition_guidance(
                before_status=before.status,
                after_status=task.status,
                status_names=self.engine.board_config().statuses,
                include_target_column=True,
            )
        elif outcome == "block":
            guidance = [self._BLOCK_AR_HINT]
            if move_to is not None:
                guidance.extend(
                    self._skip_transition_guidance(
                        before_status=before.status,
                        after_status=task.status,
                        status_names=self.engine.board_config().statuses,
                        include_target_column=True,
                    )
                )
        return self._to_single_response(task, guidance)
