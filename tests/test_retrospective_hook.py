"""Tests for RetrospectiveHook — TASK_COMPLETE retrospective learning hook.

Covers: triviality filter (rejection count + priority), fire-and-forget
via asyncio.create_task, RetroFindings model, KG ingest, registration,
and constructor interface.

This is a TEST-FIRST file — the production module does not yet exist.
All tests fail initially with ImportError.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.retrospective_hook import RetroFindings, RetrospectiveHook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_activity_log(kanban_root: Path, entries: list[dict[str, object]]) -> None:
    """Write a fake activity.jsonl into *kanban_root*."""
    log_path = kanban_root / "activity.jsonl"
    with log_path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _move_entry(
    task_id: int | str,
    from_status: str,
    to_status: str,
) -> dict[str, object]:
    """Build an activity.jsonl move entry."""
    return {
        "timestamp": "2026-03-07T10:00:00+01:00",
        "action": "move",
        "task_id": int(task_id),
        "detail": f"{from_status} -> {to_status}",
    }


def _payload(
    task_id: str = "42",
    outcome: str = "success",
) -> dict[str, object]:
    """Build a TASK_COMPLETE payload."""
    return {"task_id": task_id, "outcome": outcome}


def _mock_agent_run(findings: RetroFindings) -> AsyncMock:
    """Build an AsyncMock for Agent.run() returning the given RetroFindings."""
    mock_result = MagicMock()
    mock_result.output = findings
    return AsyncMock(return_value=mock_result)


def _sample_findings() -> RetroFindings:
    """Build a sample RetroFindings instance."""
    return RetroFindings(
        what_worked=["TDD caught edge case early"],
        what_failed=["Initial prompt was too vague"],
        error_patterns=["TypeError from missing None check"],
        reusable_patterns=["Mock activity.jsonl with tmp_path fixture"],
    )


def _kanban_show_json(task_id: str, priority: str = "important") -> str:
    """Build a fake kanban show --json response."""
    return json.dumps(
        {
            "id": int(task_id),
            "title": f"Task {task_id}",
            "status": "done",
            "priority": priority,
        }
    )


def _capturing_create_task() -> tuple[MagicMock, list[asyncio.Task[object]]]:
    """Build a mock ``asyncio.create_task`` that captures spawned tasks.

    Returns the mock and a list that will be populated with each created task.
    """
    tasks: list[asyncio.Task[object]] = []
    real_create_task = asyncio.create_task

    def _side_effect(coro: object) -> asyncio.Task[object]:
        task = real_create_task(coro)  # type: ignore[arg-type]
        tasks.append(task)
        return task

    mock = MagicMock(side_effect=_side_effect)
    return mock, tasks


# ---------------------------------------------------------------------------
# RetroFindings model
# ---------------------------------------------------------------------------


class TestRetroFindingsModel:
    """RetroFindings is a frozen BaseModel with the expected fields."""

    def test_has_what_worked_field(self) -> None:
        findings = _sample_findings()
        assert isinstance(findings.what_worked, list)
        assert all(isinstance(s, str) for s in findings.what_worked)

    def test_has_what_failed_field(self) -> None:
        findings = _sample_findings()
        assert isinstance(findings.what_failed, list)
        assert all(isinstance(s, str) for s in findings.what_failed)

    def test_has_error_patterns_field(self) -> None:
        findings = _sample_findings()
        assert isinstance(findings.error_patterns, list)
        assert all(isinstance(s, str) for s in findings.error_patterns)

    def test_has_reusable_patterns_field(self) -> None:
        findings = _sample_findings()
        assert isinstance(findings.reusable_patterns, list)
        assert all(isinstance(s, str) for s in findings.reusable_patterns)

    def test_is_frozen(self) -> None:
        findings = _sample_findings()
        with pytest.raises(ValidationError):
            findings.what_worked = ["mutated"]  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """RetrospectiveHook constructor accepts model, ingest_pipeline, kanban_root."""

    def test_accepts_model_ingest_pipeline_kanban_root(self, tmp_path: Path) -> None:
        model = MagicMock()
        ingest_pipeline = MagicMock()
        hook = RetrospectiveHook(
            model=model,
            ingest_pipeline=ingest_pipeline,
            kanban_root=tmp_path,
        )
        assert hook is not None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    """register(hooks) adds handler on HookEvent.TASK_COMPLETE."""

    def test_register_adds_to_task_complete(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=MagicMock(),
            kanban_root=tmp_path,
        )
        registry = HookRegistry()
        hook.register(registry)
        handlers = registry.handlers.get(HookEvent.TASK_COMPLETE, [])
        assert hook in handlers

    def test_register_does_not_add_to_other_events(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=MagicMock(),
            kanban_root=tmp_path,
        )
        registry = HookRegistry()
        hook.register(registry)
        for event in HookEvent:
            if event != HookEvent.TASK_COMPLETE:
                assert hook not in registry.handlers.get(event, [])


# ---------------------------------------------------------------------------
# Triviality filter — non-trivial triggers agent
# ---------------------------------------------------------------------------


class TestNonTrivialTriggersAgent:
    """Non-trivial task (>=1 rejection) triggers PydanticAI retrospective agent."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_one_rejection_triggers_agent(self, tmp_path: Path) -> None:
        """A task with 1 backward move (rejection) is non-trivial."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "todo", "in-progress"),
                _move_entry("42", "in-progress", "review"),
                _move_entry("42", "review", "todo"),  # rejection
                _move_entry("42", "todo", "in-progress"),
                _move_entry("42", "in-progress", "review"),
                _move_entry("42", "review", "done"),
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with patch(
            "owlbear.core.retrospective_hook.asyncio.create_task",
            mock_ct,
        ):
            await hook(_payload(task_id="42", outcome="success"))
            mock_ct.assert_called_once()
            await tasks[0]

        hook._agent.run.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_rejections_triggers_agent(self, tmp_path: Path) -> None:
        """Multiple rejections still trigger the agent (once)."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "review", "todo"),  # rejection 1
                _move_entry("42", "review", "backlog"),  # rejection 2
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with patch(
            "owlbear.core.retrospective_hook.asyncio.create_task",
            mock_ct,
        ):
            await hook(_payload(task_id="42", outcome="success"))
            mock_ct.assert_called_once()
            await tasks[0]

        hook._agent.run.assert_called_once()


# ---------------------------------------------------------------------------
# Triviality filter — trivial skips agent
# ---------------------------------------------------------------------------


class TestTrivialSkipsAgent:
    """Trivial task (0 rejections AND priority < needed) skips retrospective."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_zero_rejections_low_priority_skips(self, tmp_path: Path) -> None:
        """0 rejections + priority 'important' (< needed) => skip."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "todo", "in-progress"),
                _move_entry("42", "in-progress", "review"),
                _move_entry("42", "review", "done"),
            ],
        )

        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = AsyncMock()

        with patch(
            "owlbear.core.retrospective_hook.subprocess.run",
            return_value=MagicMock(
                stdout=_kanban_show_json("42", priority="important"),
                returncode=0,
            ),
        ):
            await hook(_payload(task_id="42", outcome="success"))

        hook._agent.run.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_zero_rejections_someday_skips(self, tmp_path: Path) -> None:
        """0 rejections + priority 'someday' => skip (even lower priority)."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "todo", "done"),
            ],
        )

        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = AsyncMock()

        with patch(
            "owlbear.core.retrospective_hook.subprocess.run",
            return_value=MagicMock(
                stdout=_kanban_show_json("42", priority="someday"),
                returncode=0,
            ),
        ):
            await hook(_payload(task_id="42", outcome="success"))

        hook._agent.run.assert_not_called()


# ---------------------------------------------------------------------------
# Priority >= needed triggers even with 0 rejections
# ---------------------------------------------------------------------------


class TestHighPriorityTriggersAgent:
    """Priority >= needed triggers retrospective even with 0 rejections."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_needed_priority_triggers(self, tmp_path: Path) -> None:
        """0 rejections + priority 'needed' => triggers agent."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "todo", "done"),  # no rejections
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with (
            patch(
                "owlbear.core.retrospective_hook.subprocess.run",
                return_value=MagicMock(
                    stdout=_kanban_show_json("42", priority="needed"),
                    returncode=0,
                ),
            ),
            patch(
                "owlbear.core.retrospective_hook.asyncio.create_task",
                mock_ct,
            ),
        ):
            await hook(_payload(task_id="42", outcome="success"))
            mock_ct.assert_called_once()
            await tasks[0]

        hook._agent.run.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_critical_priority_triggers(self, tmp_path: Path) -> None:
        """0 rejections + priority 'critical' => triggers agent."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "todo", "done"),
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with (
            patch(
                "owlbear.core.retrospective_hook.subprocess.run",
                return_value=MagicMock(
                    stdout=_kanban_show_json("42", priority="critical"),
                    returncode=0,
                ),
            ),
            patch(
                "owlbear.core.retrospective_hook.asyncio.create_task",
                mock_ct,
            ),
        ):
            await hook(_payload(task_id="42", outcome="success"))
            mock_ct.assert_called_once()
            await tasks[0]

        hook._agent.run.assert_called_once()


# ---------------------------------------------------------------------------
# Failure outcome skips retrospective
# ---------------------------------------------------------------------------


class TestFailureOutcomeSkips:
    """outcome='failure' skips retrospective (only successful tasks)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_failure_outcome_skips(self, tmp_path: Path) -> None:
        """Failed tasks never get a retrospective, even if non-trivial."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "review", "todo"),  # rejection (non-trivial)
            ],
        )

        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = AsyncMock()

        await hook(_payload(task_id="42", outcome="failure"))

        hook._agent.run.assert_not_called()


# ---------------------------------------------------------------------------
# KG ingest — ingest_text called with formatted findings + metadata
# ---------------------------------------------------------------------------


class TestKnowledgeGraphIngest:
    """ingest_text called with formatted findings and correct metadata."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ingest_text_called_with_findings(self, tmp_path: Path) -> None:
        """ingest_text receives text containing the findings."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "review", "todo"),  # 1 rejection => non-trivial
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with patch(
            "owlbear.core.retrospective_hook.asyncio.create_task",
            mock_ct,
        ):
            await hook(_payload(task_id="42", outcome="success"))
            await tasks[0]

        mock_ingest.ingest_text.assert_called_once()
        call_args = mock_ingest.ingest_text.call_args
        text_arg = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Text should contain the findings content
        assert "TDD caught edge case early" in text_arg
        assert "Initial prompt was too vague" in text_arg
        assert "TypeError from missing None check" in text_arg
        assert "Mock activity.jsonl with tmp_path fixture" in text_arg

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ingest_metadata_has_source_type(self, tmp_path: Path) -> None:
        """metadata contains source_type='retrospective'."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "review", "todo"),
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with patch(
            "owlbear.core.retrospective_hook.asyncio.create_task",
            mock_ct,
        ):
            await hook(_payload(task_id="42", outcome="success"))
            await tasks[0]

        call_args = mock_ingest.ingest_text.call_args
        metadata = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("metadata")
        assert metadata["source_type"] == "retrospective"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ingest_metadata_has_task_id(self, tmp_path: Path) -> None:
        """metadata contains task_id."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "review", "todo"),
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with patch(
            "owlbear.core.retrospective_hook.asyncio.create_task",
            mock_ct,
        ):
            await hook(_payload(task_id="42", outcome="success"))
            await tasks[0]

        call_args = mock_ingest.ingest_text.call_args
        metadata = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("metadata")
        assert metadata["task_id"] == "42"


# ---------------------------------------------------------------------------
# Fire-and-forget — __call__ spawns create_task and returns immediately
# ---------------------------------------------------------------------------


class TestFireAndForget:
    """__call__ spawns asyncio.create_task and returns immediately."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_call_spawns_create_task(self, tmp_path: Path) -> None:
        """__call__ uses asyncio.create_task so it does not block emit."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "review", "todo"),  # non-trivial
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with patch(
            "owlbear.core.retrospective_hook.asyncio.create_task",
            mock_ct,
        ):
            await hook(_payload(task_id="42", outcome="success"))
            # Confirm create_task was called (fire-and-forget pattern)
            mock_ct.assert_called_once()
            await tasks[0]  # cleanup

    @pytest.mark.asyncio(loop_scope="function")
    async def test_call_returns_none(self, tmp_path: Path) -> None:
        """__call__ returns None (does not return the task)."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "review", "todo"),
            ],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with patch(
            "owlbear.core.retrospective_hook.asyncio.create_task",
            mock_ct,
        ):
            result = await hook(_payload(task_id="42", outcome="success"))
            await tasks[0]  # cleanup

        assert result is None


# ---------------------------------------------------------------------------
# Non-dict payload — typed contract now guarantees dict (AC3 removed isinstance guards)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Error isolation — background task logs and swallows exceptions
# ---------------------------------------------------------------------------


class TestErrorIsolation:
    """Exceptions in background task are logged and swallowed."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_agent_run_exception_is_logged_and_swallowed(self, tmp_path: Path) -> None:
        """If _agent.run raises, logger.exception is called and no exception propagates."""
        _write_activity_log(
            tmp_path,
            [
                _move_entry("42", "review", "todo"),  # non-trivial
            ],
        )

        mock_ingest = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = AsyncMock(side_effect=RuntimeError("LLM exploded"))

        mock_ct, tasks = _capturing_create_task()
        with (
            patch(
                "owlbear.core.retrospective_hook.asyncio.create_task",
                mock_ct,
            ),
            patch(
                "owlbear.core.retrospective_hook.logger",
            ) as mock_logger,
        ):
            await hook(_payload(task_id="42", outcome="success"))
            # Await the spawned task — it should NOT raise
            await tasks[0]

        mock_logger.exception.assert_called_once()
        # ingest_text should NOT have been called since agent.run failed
        mock_ingest.ingest_text.assert_not_called()


# ---------------------------------------------------------------------------
# Lazy agent creation — _get_agent when _agent is None
# ---------------------------------------------------------------------------


class TestLazyAgentCreation:
    """_get_agent lazily creates a PydanticAI Agent on first use."""

    def test_creates_agent_on_first_use(self, tmp_path: Path) -> None:
        model = MagicMock()
        hook = RetrospectiveHook(
            model=model,
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        assert hook._agent is None
        with patch("owlbear.core.retrospective_hook.Agent") as mock_agent_cls:
            agent = hook._get_agent()
            mock_agent_cls.assert_called_once_with(
                model,
                system_prompt=(
                    "You are a retrospective analyst for a software development team. "
                    "Given a completed task description and its activity history, produce "
                    "structured findings: what worked, what failed, error patterns observed, "
                    "and reusable patterns discovered."
                ),
                output_type=RetroFindings,
            )
            assert agent is mock_agent_cls.return_value

    def test_reuses_agent_on_subsequent_calls(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        with patch("owlbear.core.retrospective_hook.Agent") as mock_agent_cls:
            first = hook._get_agent()
            second = hook._get_agent()
            mock_agent_cls.assert_called_once()
            assert first is second


# ---------------------------------------------------------------------------
# Empty / missing task_id skips
# ---------------------------------------------------------------------------


class TestEmptyTaskIdSkips:
    """Payload with missing or empty task_id silently skips."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_missing_task_id_skips(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = AsyncMock()

        await hook({"outcome": "success"})

        hook._agent.run.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_string_task_id_skips(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = AsyncMock()

        await hook({"outcome": "success", "task_id": ""})

        hook._agent.run.assert_not_called()


# ---------------------------------------------------------------------------
# _count_rejections edge cases
# ---------------------------------------------------------------------------


class TestCountRejectionsEdgeCases:
    """Edge cases in _count_rejections: no file, malformed JSON, filtering."""

    def test_no_activity_file_returns_zero(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        assert hook._count_rejections("42") == 0

    def test_malformed_json_line_skipped(self, tmp_path: Path) -> None:
        log_path = tmp_path / "activity.jsonl"
        log_path.write_text("not valid json\n", encoding="utf-8")
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        assert hook._count_rejections("42") == 0

    def test_non_move_entries_ignored(self, tmp_path: Path) -> None:
        _write_activity_log(
            tmp_path,
            [
                {"action": "create", "task_id": 42, "detail": "created task"},
                {"action": "edit", "task_id": 42, "detail": "edited"},
            ],
        )
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        assert hook._count_rejections("42") == 0

    def test_different_task_id_ignored(self, tmp_path: Path) -> None:
        _write_activity_log(
            tmp_path,
            [_move_entry("99", "review", "todo")],
        )
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        assert hook._count_rejections("42") == 0

    def test_empty_lines_skipped(self, tmp_path: Path) -> None:
        log_path = tmp_path / "activity.jsonl"
        content = "\n\n" + json.dumps(_move_entry("42", "review", "todo")) + "\n\n"
        log_path.write_text(content, encoding="utf-8")
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        assert hook._count_rejections("42") == 1

    def test_move_without_arrow_not_counted(self, tmp_path: Path) -> None:
        _write_activity_log(
            tmp_path,
            [{"action": "move", "task_id": 42, "detail": "moved somewhere"}],
        )
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        assert hook._count_rejections("42") == 0


# ---------------------------------------------------------------------------
# _get_priority edge cases
# ---------------------------------------------------------------------------


class TestGetPriorityEdgeCases:
    """Edge cases in _get_priority: subprocess errors, unknown priorities."""

    def test_subprocess_raises_returns_important(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        with patch(
            "owlbear.core.retrospective_hook.subprocess.run",
            side_effect=OSError("command not found"),
        ):
            assert hook._get_priority("42") == "important"

    def test_nonzero_returncode_returns_important(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        with patch(
            "owlbear.core.retrospective_hook.subprocess.run",
            return_value=MagicMock(returncode=1, stdout=""),
        ):
            assert hook._get_priority("42") == "important"

    def test_unknown_priority_returns_important(self, tmp_path: Path) -> None:
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=AsyncMock(),
            kanban_root=tmp_path,
        )
        with patch(
            "owlbear.core.retrospective_hook.subprocess.run",
            return_value=MagicMock(
                returncode=0,
                stdout=json.dumps({"priority": "ultra-mega-critical"}),
            ),
        ):
            assert hook._get_priority("42") == "important"


# ---------------------------------------------------------------------------
# _run_retrospective: ingest_text error path
# ---------------------------------------------------------------------------


class TestIngestTextError:
    """ingest_text failure in _run_retrospective is logged and swallowed."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ingest_text_raises_logged_and_swallowed(self, tmp_path: Path) -> None:
        _write_activity_log(
            tmp_path,
            [_move_entry("42", "review", "todo")],
        )

        findings = _sample_findings()
        mock_ingest = AsyncMock()
        mock_ingest.ingest_text = AsyncMock(side_effect=RuntimeError("DB down"))
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(findings)

        mock_ct, tasks = _capturing_create_task()
        with (
            patch("owlbear.core.retrospective_hook.asyncio.create_task", mock_ct),
            patch("owlbear.core.retrospective_hook.logger") as mock_logger,
        ):
            await hook(_payload(task_id="42", outcome="success"))
            await tasks[0]

        mock_logger.exception.assert_called_once()
        hook._agent.run.assert_called_once()


# ===========================================================================
# cancel= parameter — cooperative cancellation seam (task #880)
# ===========================================================================


class TestFromAC_RetrospectiveHookCancellation:
    """hook composes a per-operation cancel signal with daemon shutdown for ingest_text."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_hook_passes_cancel_kwarg_to_ingest_text_composed_with_shutdown(
        self, tmp_path: Path
    ) -> None:
        """_run_retrospective calls ingest_text with a cancel= signal linked to daemon shutdown."""
        shutdown_event = asyncio.Event()
        mock_ingest = AsyncMock()

        # This constructor call fails TypeError on current HEAD (shutdown_event not accepted)
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
            shutdown_event=shutdown_event,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(_sample_findings())

        await hook._run_retrospective("42")

        mock_ingest.ingest_text.assert_called_once()
        call_kwargs = mock_ingest.ingest_text.call_args.kwargs
        assert "cancel" in call_kwargs, "ingest_text must receive a cancel= signal"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cancel_signal_is_set_when_daemon_shutdown_fires(self, tmp_path: Path) -> None:
        """The cancel= passed to ingest_text is set when the daemon shutdown event fires."""
        shutdown_event = asyncio.Event()
        captured: dict[str, object] = {}

        async def capture_cancel(*_args: object, **kwargs: object) -> object:
            captured["cancel"] = kwargs.get("cancel")
            return MagicMock()

        mock_ingest = AsyncMock()
        mock_ingest.ingest_text = capture_cancel

        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
            shutdown_event=shutdown_event,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(_sample_findings())

        shutdown_event.set()
        await hook._run_retrospective("42")

        cancel_signal = captured.get("cancel")
        assert cancel_signal is not None, "cancel signal must be passed to ingest_text"
        assert cancel_signal.is_set(), "cancel signal must be set when daemon shutdown fires"


# ---------------------------------------------------------------------------
# TDD RED: LinkedCancelSignal live-propagation seam — bootstrap wiring (#870)
# ---------------------------------------------------------------------------


class TestFromAC_870_RetrospectiveHookLinkedSignal:
    """RetrospectiveHook forwards a pre-composed LinkedCancelSignal to ingest_text.

    AC 5: Compose the per-operation signal only in the daemon-owned ingest path.
    The cancel signal forwarded to ingest_text must reflect the live state of
    shutdown_event, not a one-time snapshot taken when _run_retrospective starts.

    Fails on current HEAD because _run_retrospective creates a new asyncio.Event()
    per call and only snapshot-copies shutdown_event.is_set() at startup; a
    LinkedCancelSignal that was live-linked to shutdown_event at construction time
    does not yet exist.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cancel_reflects_live_shutdown_event_set_after_retrospective_completes(
        self, tmp_path: Path
    ) -> None:
        """cancel signal forwarded to ingest_text reflects live shutdown_event state.

        After _run_retrospective completes, setting shutdown_event must cause the
        cancel signal received by ingest_text to also report is_set() == True.
        A simple snapshot copy (asyncio.Event() created at call time) does NOT
        satisfy this contract — only a LinkedCancelSignal delegating to shutdown_event
        at is_set() call time satisfies it.
        """
        shutdown_event = asyncio.Event()  # NOT set initially
        captured: dict[str, object] = {}

        async def capture_cancel(**kwargs: object) -> object:
            captured["cancel"] = kwargs.get("cancel")
            return MagicMock()

        mock_ingest = AsyncMock()
        mock_ingest.ingest_text = capture_cancel

        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
            shutdown_event=shutdown_event,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(_sample_findings())

        # shutdown_event is NOT set at the time _run_retrospective is called
        assert not shutdown_event.is_set()
        await hook._run_retrospective("42")

        cancel_signal = captured.get("cancel")
        assert cancel_signal is not None, "cancel signal must be passed to ingest_text"

        # Before setting shutdown_event, the cancel signal should not be set
        assert not cancel_signal.is_set(), "cancel should not report set before shutdown fires"

        # Set shutdown_event AFTER _run_retrospective has already completed
        shutdown_event.set()

        # The linked cancel signal must reflect the live state of shutdown_event;
        # a snapshot copy (plain asyncio.Event) would return False here.
        assert cancel_signal.is_set(), (
            "cancel signal must reflect live shutdown_event state — "
            "use LinkedCancelSignal, not a snapshot asyncio.Event()"
        )


# ---------------------------------------------------------------------------
# TDD RED: RetrospectiveHook supervisor seam (#966)
# ---------------------------------------------------------------------------


class TestFromAC_RetrospectiveHookSupervisorSeam:
    """RetrospectiveHook.__call__ delegates background work through an injected
    HookWorkerSupervisor.schedule() seam instead of asyncio.create_task(), while
    preserving existing eligibility gates and the cancel= ingestion seam.

    All tests fail on HEAD because RetrospectiveHook.__init__ does not yet
    accept a ``supervisor`` keyword argument.
    """

    def _make_hook(
        self,
        tmp_path: Path,
        supervisor: object,
        ingest: object | None = None,
    ) -> RetrospectiveHook:
        return RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=ingest or AsyncMock(),
            kanban_root=tmp_path,
            supervisor=supervisor,  # fails today: unexpected keyword argument
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_call_uses_supervisor_schedule_not_create_task(self, tmp_path: Path) -> None:
        """Non-trivial success outcome calls supervisor.schedule(), not asyncio.create_task()."""
        _write_activity_log(
            tmp_path,
            [_move_entry("42", "review", "todo")],  # one rejection → non-trivial
        )
        mock_supervisor = MagicMock()
        hook = self._make_hook(tmp_path, mock_supervisor)
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(_sample_findings())

        with patch("owlbear.core.retrospective_hook.asyncio.create_task") as mock_ct:
            await hook(_payload(task_id="42", outcome="success"))
            mock_ct.assert_not_called()

        mock_supervisor.schedule.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_failure_outcome_skips_supervisor_schedule(self, tmp_path: Path) -> None:
        """Non-success outcome does not reach supervisor.schedule()."""
        # success-only gate must be preserved
        _write_activity_log(
            tmp_path,
            [_move_entry("42", "review", "todo")],  # rejection (non-trivial)
        )
        mock_supervisor = MagicMock()
        hook = self._make_hook(tmp_path, mock_supervisor)

        await hook(_payload(task_id="42", outcome="failure"))

        mock_supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_trivial_task_skips_supervisor_schedule(self, tmp_path: Path) -> None:
        """Zero rejections + low priority skips supervisor.schedule()."""
        # eligibility gate must be preserved
        _write_activity_log(
            tmp_path,
            [_move_entry("42", "todo", "done")],  # forward move, no rejection
        )
        mock_supervisor = MagicMock()
        hook = self._make_hook(tmp_path, mock_supervisor)

        with patch(
            "owlbear.core.retrospective_hook.subprocess.run",
            return_value=MagicMock(
                stdout=_kanban_show_json("42", priority="important"),
                returncode=0,
            ),
        ):
            await hook(_payload(task_id="42", outcome="success"))

        mock_supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_rejection_gate_preserved_with_supervisor(self, tmp_path: Path) -> None:
        """At least one rejection → supervisor.schedule() is called (rejection gate intact)."""
        _write_activity_log(
            tmp_path,
            [_move_entry("42", "review", "todo")],  # one rejection
        )
        mock_supervisor = MagicMock()
        hook = self._make_hook(tmp_path, mock_supervisor)
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(_sample_findings())

        await hook(_payload(task_id="42", outcome="success"))

        mock_supervisor.schedule.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_run_retrospective_cancel_seam_preserved_with_supervisor(
        self, tmp_path: Path
    ) -> None:
        """_run_retrospective() still passes cancel= kwarg to ingest_text."""
        # cancel= seam must be preserved when supervisor is injected
        mock_ingest = AsyncMock()
        mock_supervisor = MagicMock()

        # supervisor= fails today: unexpected keyword argument
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
            supervisor=mock_supervisor,
        )
        hook._agent = MagicMock()
        hook._agent.run = _mock_agent_run(_sample_findings())

        await hook._run_retrospective("42")

        mock_ingest.ingest_text.assert_called_once()
        call_kwargs = mock_ingest.ingest_text.call_args.kwargs
        assert "cancel" in call_kwargs, "_run_retrospective must pass cancel= to ingest_text"
        assert isinstance(call_kwargs["cancel"], asyncio.Event)
