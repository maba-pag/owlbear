"""TDD RED-phase tests for #208 — orchestrator dispatch loop.

Targets:
  - owlbear.orchestrator.waves:  AgentCategory, AGENT_CATEGORY, Wave, assemble_waves
  - owlbear.orchestrator.loop:   AGENT_PROMPT_PREFIX, CycleResult, LoopState,
                                  dispatch_entry, dispatch_wave, run_loop, format_prompt
  - owlbear.planner.models:      DispatchEntry.retry_hint field

All tests fail on current HEAD: owlbear.orchestrator does not exist yet.

Note on worked example test: task #208 spec states '4-wave output' based on the
orchestration skill's worked example (which was written with consolidation ENABLED).
Task #146 AC disables consolidation (step 6: SKIP). With consolidation disabled,
the 14-task input produces 3 waves (the 4 solo-builder waves are dropped by the drop
rule). This discrepancy is noted here as a quality gap — the builder should clarify.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports fail RED-phase: owlbear.orchestrator does not exist yet.
from owlbear.orchestrator.waves import (  # type: ignore[import]
    Wave,
    assemble_waves,
)
from owlbear.orchestrator.loop import (  # type: ignore[import]
    AGENT_PROMPT_PREFIX,
    CycleResult,
    LoopState,
    dispatch_entry,
    dispatch_wave,
    format_prompt,
    run_loop,
)
from owlbear.planner.models import DispatchEntry
from owlbear_orchestrator.acp_client import AcpClient, AcpClientError


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _entry(task_id: int, agent: str) -> DispatchEntry:
    """Create a minimal DispatchEntry for wave / dispatch tests."""
    return DispatchEntry(task_id=task_id, agent=agent, target_status="done")


def _make_client() -> MagicMock:
    """Return a mock AcpClient with new_session and prompt as AsyncMocks."""
    client = MagicMock(spec=AcpClient)
    session_resp = MagicMock()
    session_resp.session_id = "test-session-abc"
    client.new_session = AsyncMock(return_value=session_resp)
    client.prompt = AsyncMock(return_value=MagicMock())
    return client


def _wave_agents(wave: Wave) -> list[str]:
    """Extract agent names from a wave in entry order."""
    return [e.agent for e in wave.entries]


def _wave_ids(wave: Wave) -> list[int]:
    """Extract task IDs from a wave in entry order."""
    return [e.task_id for e in wave.entries]


# ===========================================================================
# Wave Assembly (assemble_waves)
# ===========================================================================


class TestFromAC_WaveAssembly:  # noqa: N801
    """assemble_waves() — four-bucket algorithm, all 14 AC lines from task #208."""

    def test_empty_input_returns_empty_list(self) -> None:
        """Empty entry list returns empty wave list."""
        result = assemble_waves([], wave_size=4, cycle=1)
        assert result == []

    def test_single_auditor_returns_one_wave(self) -> None:
        """Single auditor entry produces exactly one wave containing that entry."""
        waves = assemble_waves([_entry(1, "auditor")], wave_size=4, cycle=1)
        assert len(waves) == 1
        assert _wave_agents(waves[0]) == ["auditor"]

    def test_auditor_wave_fills_with_light_flex_priority_order(self) -> None:
        """Auditor wave fills remaining slots with light-flex agents in priority order."""
        entries = [
            _entry(10, "auditor"),
            _entry(20, "researcher"),
            _entry(30, "writer"),
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        assert len(waves) == 1
        agents = _wave_agents(waves[0])
        assert agents[0] == "auditor"
        assert "researcher" in agents
        assert "writer" in agents

    def test_builder_wave_fills_with_heavy_flex_when_no_light(self) -> None:
        """Builder wave fills slots with heavy flex when no light flex remains."""
        entries = [
            _entry(1, "builder"),
            _entry(2, "reviewer"),
            _entry(3, "test-writer"),
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        # All three in one wave (builder + 2 heavy = 3 entries, not solo → kept)
        assert len(waves) >= 1
        first_agents = _wave_agents(waves[0])
        assert "builder" in first_agents
        heavy_in_wave = sum(1 for a in first_agents if a in ("reviewer", "test-writer"))
        assert heavy_in_wave >= 1

    def test_builder_wave_fills_light_flex_before_heavy_flex(self) -> None:
        """Builder wave fills light-flex slots first, then heavy-flex."""
        entries = [
            _entry(1, "builder"),
            _entry(2, "writer"),      # light flex
            _entry(3, "reviewer"),    # heavy flex
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        # All three go into the builder wave
        assert len(waves) == 1
        agents = _wave_agents(waves[0])
        assert "builder" in agents
        assert "writer" in agents
        assert "reviewer" in agents
        # light flex (writer) must come before heavy flex (reviewer) within the wave
        assert agents.index("writer") < agents.index("reviewer")

    def test_multiple_builders_one_per_wave(self) -> None:
        """No two builders ever share a wave."""
        entries = [_entry(i, "builder") for i in range(1, 5)]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        for wave in waves:
            builder_count = sum(1 for e in wave.entries if e.agent == "builder")
            assert builder_count <= 1, "two builders in the same wave"

    def test_auditor_and_builder_never_share_wave(self) -> None:
        """Auditor and builder are never placed in the same wave."""
        entries = [
            _entry(1, "auditor"),
            _entry(2, "builder"),
            _entry(3, "writer"),  # light flex — fills auditor wave
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        for wave in waves:
            agents = _wave_agents(wave)
            assert not ("auditor" in agents and "builder" in agents), (
                "auditor and builder must not share a wave"
            )

    def test_overflow_flex_agents_chunked_into_wave_size_waves(self) -> None:
        """Remaining flex agents after builder/auditor fill go into overflow waves."""
        # 6 light-flex writers → need 2 waves (4 + 2, but solo wave of 2 is not solo)
        entries = [_entry(i, "writer") for i in range(1, 7)]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        for wave in waves:
            assert len(wave.entries) <= 4
        # All 6 must be dispatched (no drop — wave of 2 is not solo)
        all_dispatched = [e for w in waves for e in w.entries]
        assert len(all_dispatched) == 6

    def test_periodic_curator_added_to_last_wave_with_free_slot(self) -> None:
        """cycle % 5 == 0: curator entry added to the last wave that has room."""
        entries = [
            _entry(1, "auditor"),
            _entry(2, "researcher"),
            _entry(3, "writer"),
            # wave_size=4 → 1 free slot in the only wave
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=5)
        last_wave_agents = _wave_agents(waves[-1])
        assert "curator" in last_wave_agents

    def test_periodic_curator_skipped_if_all_waves_full(self) -> None:
        """cycle % 5 == 0: curator skipped if every wave is already at wave_size capacity."""
        entries = [
            _entry(1, "auditor"),
            _entry(2, "researcher"),
            _entry(3, "writer"),
            _entry(4, "architect"),
            # wave_size=4 → exactly full, no slot available
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=5)
        for wave in waves:
            assert "curator" not in _wave_agents(wave)

    def test_non_periodic_cycle_no_curator_added(self) -> None:
        """Non-multiple-of-5 cycle: no curator is added regardless of slots."""
        entries = [
            _entry(1, "auditor"),
            _entry(2, "researcher"),
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=3)
        for wave in waves:
            assert "curator" not in _wave_agents(wave)

    def test_drop_rule_solo_non_auditor_wave_dropped(self) -> None:
        """Solo non-auditor, non-retry wave is dropped (deferred to next cycle)."""
        # auditor wave fills with light; builder is left solo → drop
        entries = [
            _entry(1, "auditor"),
            _entry(2, "researcher"),
            _entry(3, "writer"),
            _entry(4, "architect"),  # fills auditor wave to capacity
            _entry(5, "builder"),    # solo builder wave → drop
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        dispatched_agents = [e.agent for w in waves for e in w.entries]
        assert "builder" not in dispatched_agents

    def test_drop_rule_exception_keeps_first_non_auditor_wave(self) -> None:
        """Exception: first non-auditor wave kept when dropping would eliminate all non-auditor waves."""
        # Solo builder — no other non-auditor waves exist, so it must be kept
        entries = [_entry(1, "builder")]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        assert len(waves) == 1
        assert waves[0].entries[0].task_id == 1

    def test_worked_example_14_tasks_correct_output_without_consolidation(self) -> None:
        """Skill worked example input with consolidation DEACTIVATED.

        Input (priority order): 14 tasks across all agent types.
        Expected with consolidation SKIP (per #146 AC):
          Wave 1: auditor + 3 light flex (full)
          Wave 2: builder + 1 light + 2 heavy (full)
          Wave 3: builder + 1 heavy
          Waves 4-7 (solo builders): dropped by drop rule (non-auditor waves exist)
        → 3 waves, 10 tasks dispatched.
        """
        entries = [
            _entry(862, "reviewer"),
            _entry(780, "reviewer"),
            _entry(920, "test-writer"),
            _entry(947, "researcher"),
            _entry(910, "auditor"),
            _entry(788, "writer"),
            _entry(781, "writer"),
            _entry(728, "writer"),
            _entry(853, "builder"),
            _entry(934, "builder"),
            _entry(521, "builder"),
            _entry(556, "builder"),
            _entry(733, "builder"),
            _entry(775, "builder"),
        ]
        waves = assemble_waves(entries, wave_size=4, cycle=1)
        assert len(waves) == 3  # consolidation SKIP: solo builders dropped
        # Wave 1: auditor + 3 light flex
        assert _wave_agents(waves[0])[0] == "auditor"
        assert len(waves[0].entries) == 4
        # Wave 2: builder + 3 flex (full)
        assert "builder" in _wave_agents(waves[1])
        assert len(waves[1].entries) == 4
        # Wave 3: builder + 1 heavy
        assert "builder" in _wave_agents(waves[2])
        assert len(waves[2].entries) == 2


# ===========================================================================
# format_prompt
# ===========================================================================


class TestFromAC_FormatPrompt:  # noqa: N801
    """format_prompt() and AGENT_PROMPT_PREFIX — all AC lines from task #208."""

    def test_standard_agent_returns_prefix_colon_task_id(self) -> None:
        """Standard agent: format_prompt returns '{prefix}: #{task_id}'."""
        entry = _entry(42, "builder")
        result = format_prompt(entry)
        prefix = AGENT_PROMPT_PREFIX["builder"]
        assert result == f"{prefix}: #42"

    def test_truthy_retry_hint_appends_context_line(self) -> None:
        """Truthy retry_hint: '\\nRetry context: {hint}' appended to standard format."""
        entry = DispatchEntry(
            task_id=99,
            agent="builder",
            target_status="review",
            retry_hint="Missing coverage on parser module",
        )
        result = format_prompt(entry)
        prefix = AGENT_PROMPT_PREFIX["builder"]
        expected = f"{prefix}: #99\nRetry context: Missing coverage on parser module"
        assert result == expected

    def test_curator_returns_prefix_only_no_task_id(self) -> None:
        """Curator exception: format_prompt returns only the prefix string."""
        entry = _entry(0, "curator")
        result = format_prompt(entry)
        prefix = AGENT_PROMPT_PREFIX["curator"]
        assert result == prefix
        assert "#" not in result
        assert ":" not in result or result == prefix  # prefix itself may not contain ":"

    def test_all_nine_agent_types_have_prefix_entry(self) -> None:
        """AGENT_PROMPT_PREFIX covers exactly the 9 defined agent types."""
        expected = {
            "architect", "builder", "reviewer", "test-writer",
            "researcher", "writer", "auditor", "kanban-planner", "curator",
        }
        assert set(AGENT_PROMPT_PREFIX.keys()) == expected

    @pytest.mark.parametrize("agent", [
        "architect", "builder", "reviewer", "test-writer",
        "researcher", "writer", "auditor", "kanban-planner",
    ])
    def test_non_curator_agent_includes_task_id_in_prompt(self, agent: str) -> None:
        """Each non-curator agent prompt contains '#{task_id}'."""
        entry = _entry(101, agent)
        result = format_prompt(entry)
        assert "#101" in result


# ===========================================================================
# CycleResult and LoopState dataclasses
# ===========================================================================


class TestFromAC_Dataclasses:  # noqa: N801
    """CycleResult (frozen dataclass) and LoopState (mutable dataclass) contracts."""

    def test_cycle_result_is_frozen_immutable(self) -> None:
        """CycleResult is frozen: attribute reassignment raises an error."""
        result = CycleResult(successes=[1, 2], failures=[], rate_limited=False)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            result.successes = [3]  # type: ignore[misc]

    def test_loop_state_defaults_sequential_remaining_zero(self) -> None:
        """LoopState(): sequential_remaining defaults to 0."""
        state = LoopState()
        assert state.sequential_remaining == 0

    def test_loop_state_defaults_cycle_zero(self) -> None:
        """LoopState(): cycle defaults to 0."""
        state = LoopState()
        assert state.cycle == 0

    def test_loop_state_defaults_empty_sets(self) -> None:
        """LoopState(): stale_retried and crash_failures default to empty sets."""
        state = LoopState()
        assert state.stale_retried == set()
        assert state.crash_failures == set()


# ===========================================================================
# dispatch_entry
# ===========================================================================


class TestFromAC_DispatchEntry:  # noqa: N801
    """dispatch_entry() — success and error paths, mocked AcpClient."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_success_calls_new_session_and_prompt_returns_true(self) -> None:
        """Success: new_session and prompt are both called; True is returned."""
        client = _make_client()
        entry = _entry(42, "builder")
        result = await dispatch_entry(entry, client)
        assert result is True
        client.new_session.assert_called_once()
        client.prompt.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_acp_client_error_returns_false_no_retry(self) -> None:
        """AcpClientError: returns False; new_session called ONCE (no retry in dispatch_entry)."""
        client = _make_client()
        client.new_session = AsyncMock(
            side_effect=AcpClientError("acp failure", category=MagicMock())
        )
        result = await dispatch_entry(_entry(7, "builder"), client)
        assert result is False
        client.new_session.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_timeout_error_returns_false_no_retry(self) -> None:
        """TimeoutError: returns False; no retry from dispatch_entry itself."""
        client = _make_client()
        client.new_session = AsyncMock(side_effect=TimeoutError("timed out"))
        result = await dispatch_entry(_entry(8, "builder"), client)
        assert result is False
        client.new_session.assert_called_once()


# ===========================================================================
# dispatch_wave
# ===========================================================================


class TestFromAC_DispatchWave:  # noqa: N801
    """dispatch_wave() — parallel/sequential modes and rate-limit detection."""

    @staticmethod
    def _make_wave(*agents: str) -> Wave:
        """Build a Wave from a sequence of agent names (task_ids start at 1)."""
        entries = [_entry(i + 1, agent) for i, agent in enumerate(agents)]
        return Wave(entries=entries)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_parallel_mode_all_entries_dispatched(self) -> None:
        """sequential_remaining=0: all wave entries are dispatched (parallel gather mode)."""
        client = _make_client()
        state = LoopState(sequential_remaining=0)
        wave = self._make_wave("researcher", "writer", "architect")
        result = await dispatch_wave(wave, client, state)
        assert client.new_session.call_count == 3
        assert isinstance(result, CycleResult)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sequential_mode_counter_decremented_per_dispatch(self) -> None:
        """sequential_remaining > 0: counter decremented by one for each dispatched entry."""
        client = _make_client()
        state = LoopState(sequential_remaining=3)
        wave = self._make_wave("builder", "researcher")
        await dispatch_wave(wave, client, state)
        # 2 dispatches → 3 - 2 = 1
        assert state.sequential_remaining == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_rate_limit_hyphenated_sets_sequential_remaining_and_flag(self) -> None:
        """'rate-limited' in exception message → sequential_remaining=3, rate_limited=True."""
        client = _make_client()
        client.new_session = AsyncMock(
            side_effect=Exception("agent is rate-limited, please wait")
        )
        state = LoopState(sequential_remaining=0)
        result = await dispatch_wave(self._make_wave("builder"), client, state)
        assert state.sequential_remaining == 3
        assert result.rate_limited is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_rate_limit_underscore_variant(self) -> None:
        """'rate_limited' in exception message triggers sequential mode."""
        client = _make_client()
        client.new_session = AsyncMock(
            side_effect=Exception("rate_limited: quota exceeded")
        )
        state = LoopState(sequential_remaining=0)
        result = await dispatch_wave(self._make_wave("builder"), client, state)
        assert state.sequential_remaining == 3
        assert result.rate_limited is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_rate_limit_rate_limits_variant(self) -> None:
        """'rate limits' in exception message triggers sequential mode."""
        client = _make_client()
        client.new_session = AsyncMock(
            side_effect=Exception("exceeded rate limits for your plan")
        )
        state = LoopState(sequential_remaining=0)
        result = await dispatch_wave(self._make_wave("builder"), client, state)
        assert state.sequential_remaining == 3
        assert result.rate_limited is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_rate_limit_crash_retried_once_second_crash_recorded_as_failure(
        self,
    ) -> None:
        """Non-rate-limit error: retry once; second crash records task_id as failure."""
        client = _make_client()
        client.new_session = AsyncMock(side_effect=Exception("internal server error"))
        state = LoopState(sequential_remaining=0)
        result = await dispatch_wave(self._make_wave("builder"), client, state)
        assert 1 in result.failures

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_rate_limit_crash_no_wave_level_retry_single_call(self) -> None:
        """Non-rate-limit exception: dispatch_entry called exactly once — no wave-level retry."""
        client = _make_client()
        client.new_session = AsyncMock(side_effect=Exception("internal server error"))
        state = LoopState(sequential_remaining=0)
        result = await dispatch_wave(self._make_wave("builder"), client, state)
        assert 1 in result.failures
        assert client.new_session.call_count == 1  # no retry within the wave
        assert result.rate_limited is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sequential_mode_dispatch_entry_returns_false_recorded_as_failure(
        self,
    ) -> None:
        """Sequential mode: dispatch_entry returning False (AcpClientError) records task_id in failures."""
        client = _make_client()
        client.new_session = AsyncMock(side_effect=AcpClientError("connection refused", category=MagicMock()))
        state = LoopState(sequential_remaining=2)
        result = await dispatch_wave(self._make_wave("builder"), client, state)
        assert 1 in result.failures
        assert result.rate_limited is False
        assert state.sequential_remaining == 1  # decremented by one dispatch

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sequential_mode_uncaught_exception_recorded_as_failure(self) -> None:
        """Sequential mode: uncaught exception in dispatch_entry is caught by _dispatch_sequential and recorded as failure."""
        client = _make_client()
        client.new_session = AsyncMock(side_effect=RuntimeError("upstream crash"))
        state = LoopState(sequential_remaining=2)
        result = await dispatch_wave(self._make_wave("builder"), client, state)
        assert 1 in result.failures
        assert result.rate_limited is False
        assert state.sequential_remaining == 1  # decremented by one dispatch

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sequential_mode_rate_limit_exception_sets_rate_limited_flag(
        self,
    ) -> None:
        """Sequential mode: rate-limit exception sets rate_limited=True on CycleResult."""
        client = _make_client()
        client.new_session = AsyncMock(
            side_effect=Exception("rate-limited by provider")
        )
        state = LoopState(sequential_remaining=2)
        result = await dispatch_wave(self._make_wave("builder"), client, state)
        assert result.rate_limited is True
        # _apply_wave_result resets sequential_remaining to 3; _dispatch_sequential
        # then decrements it once (for the single entry dispatched) → 2
        assert state.sequential_remaining == 2

    @pytest.mark.asyncio(loop_scope="function")
    async def test_mixed_results_successes_and_failures_recorded(self) -> None:
        """Mixed wave: succeeded entries in CycleResult.successes, failed in .failures."""
        client = _make_client()
        call_count = 0

        async def _new_session_side_effect(**_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:  # every second call fails
                msg = "internal error"
                raise RuntimeError(msg)
            resp = MagicMock()
            resp.session_id = f"sess-{call_count}"
            return resp

        client.new_session = AsyncMock(side_effect=_new_session_side_effect)
        state = LoopState(sequential_remaining=0)
        wave = self._make_wave("researcher", "builder")  # task_ids 1, 2
        result = await dispatch_wave(wave, client, state)
        assert 1 in result.successes  # researcher (task_id=1) succeeded
        assert 2 in result.failures   # builder (task_id=2) failed


# ===========================================================================
# run_loop
# ===========================================================================


class TestFromAC_RunLoop:  # noqa: N801
    """run_loop() — full loop logic, mocked planner and AcpClient."""

    @staticmethod
    def _plan(*pairs: tuple[int, str]) -> MagicMock:
        """Return a mock DispatchPlan with the given (task_id, agent) pairs."""
        plan = MagicMock()
        plan.entries = [_entry(tid, agent) for tid, agent in pairs]
        return plan

    @staticmethod
    def _empty_plan() -> MagicMock:
        plan = MagicMock()
        plan.entries = []
        return plan

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_plan_exits_immediately_without_dispatching(self) -> None:
        """Empty dispatch plan: loop exits without dispatching (new_session never called)."""
        client = _make_client()
        with (
            patch("owlbear.orchestrator.loop.read_board", new=AsyncMock(return_value=[])),
            patch(
                "owlbear.orchestrator.loop.select_tasks",
                return_value=self._empty_plan(),
            ),
        ):
            await run_loop(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
            )
        client.new_session.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_single_cycle_replans_and_exits_on_empty_replan(self) -> None:
        """Single-cycle: tasks dispatched; replan returns empty; loop exits."""
        client = _make_client()
        call_count = 0

        def _select(*_args: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return self._plan((10, "researcher"))
            return self._empty_plan()

        with (
            patch("owlbear.orchestrator.loop.read_board", new=AsyncMock(return_value=[])),
            patch("owlbear.orchestrator.loop.select_tasks", side_effect=_select),
        ):
            await run_loop(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
            )
        assert call_count == 2  # planned cycle 1 + empty replan

    @pytest.mark.asyncio(loop_scope="function")
    async def test_crash_failures_passed_to_planner_next_cycle(self) -> None:
        """Crash failures from cycle N are forwarded to select_tasks in cycle N+1."""
        client = _make_client()
        client.new_session = AsyncMock(side_effect=Exception("crash"))
        call_count = 0
        captured: list[dict] = []

        def _select(*_args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            captured.append(dict(kwargs))
            if call_count <= 2:
                return self._plan((5, "researcher"))
            return self._empty_plan()

        with (
            patch("owlbear.orchestrator.loop.read_board", new=AsyncMock(return_value=[])),
            patch("owlbear.orchestrator.loop.select_tasks", side_effect=_select),
        ):
            await run_loop(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
            )
        second_call = captured[1]
        crash_ids = second_call.get(
            "crash_failures", second_call.get("crash_failure_ids", set())
        )
        assert 5 in crash_ids

    @pytest.mark.asyncio(loop_scope="function")
    async def test_stale_retried_ids_tracked_across_cycles(self) -> None:
        """Entry with retry_hint: its task_id tracked in stale_retried for next cycle."""
        client = _make_client()
        call_count = 0
        captured: list[dict] = []

        def _select(*_args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            captured.append(dict(kwargs))
            if call_count == 1:
                plan = MagicMock()
                plan.entries = [
                    DispatchEntry(
                        task_id=77,
                        agent="researcher",
                        target_status="backlog",
                        retry_hint="prior stale context",
                    )
                ]
                return plan
            return self._empty_plan()

        with (
            patch("owlbear.orchestrator.loop.read_board", new=AsyncMock(return_value=[])),
            patch("owlbear.orchestrator.loop.select_tasks", side_effect=_select),
        ):
            await run_loop(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
            )
        second_call = captured[1]
        stale = second_call.get(
            "stale_retried", second_call.get("stale_retried_ids", set())
        )
        assert 77 in stale

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cycle_counter_increments_each_iteration(self) -> None:
        """LoopState.cycle increments by 1 after each completed dispatch cycle."""
        client = _make_client()
        call_count = 0

        def _select(*_args: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return self._plan((11, "researcher"))
            return self._empty_plan()

        with (
            patch("owlbear.orchestrator.loop.read_board", new=AsyncMock(return_value=[])),
            patch("owlbear.orchestrator.loop.select_tasks", side_effect=_select),
        ):
            await run_loop(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
            )
        # 3 calls: cycle 1, cycle 2, empty replan → 2 full cycles completed
        assert call_count == 3


# ===========================================================================
# DispatchEntry.retry_hint field
# ===========================================================================


class TestFromAC_DispatchEntryRetryHint:  # noqa: N801
    """DispatchEntry.retry_hint extension — backward compatibility and population."""

    def test_retry_hint_defaults_to_empty_string(self) -> None:
        """DispatchEntry created without retry_hint has retry_hint == ''."""
        entry = DispatchEntry(task_id=1, agent="builder", target_status="review")
        assert entry.retry_hint == ""

    def test_retry_hint_stores_provided_value(self) -> None:
        """DispatchEntry with retry_hint='...' preserves the value."""
        entry = DispatchEntry(
            task_id=2,
            agent="builder",
            target_status="review",
            retry_hint="Coverage missing on parser.py",
        )
        assert entry.retry_hint == "Coverage missing on parser.py"


# ===========================================================================
# Retry-cycle additions (#20): reviewer found run_loop calls select_tasks
# with wrong kwargs (masked by over-mocking), missing scope param, missing
# orchestrate() function, and missing __init__.py exports.
# ===========================================================================


class TestFromAC_RunLoopCallSignature:  # noqa: N801
    """run_loop() must call select_tasks(tasks) with NO extra kwargs.

    The existing TestFromAC_RunLoop tests fully mock select_tasks, which masks
    a TypeError at runtime. These tests use the real select_tasks so the
    signature mismatch surfaces as a test failure.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_board_exits_cleanly_with_real_select_tasks(self) -> None:
        """Empty board: run_loop exits without TypeError when select_tasks is NOT mocked."""
        client = _make_client()
        with patch("owlbear.orchestrator.loop.read_board", new=AsyncMock(return_value=[])):
            # Real select_tasks — exposes TypeError if run_loop passes extra kwargs
            await run_loop(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
            )
        client.new_session.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_run_loop_accepts_scope_keyword_argument(self) -> None:
        """run_loop must accept scope: str | None = None keyword argument."""
        client = _make_client()
        with patch("owlbear.orchestrator.loop.read_board", new=AsyncMock(return_value=[])):
            await run_loop(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
                scope="phase-1",
            )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_scope_forwarded_to_read_board(self) -> None:
        """scope kwarg must be forwarded to read_board() on each cycle."""
        client = _make_client()
        read_board_mock = AsyncMock(return_value=[])
        with patch("owlbear.orchestrator.loop.read_board", new=read_board_mock):
            await run_loop(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
                scope="phase-3",
            )
        assert any(
            c.kwargs.get("scope") == "phase-3"
            for c in read_board_mock.call_args_list
        ), "scope must be forwarded to read_board"


class TestFromAC_OrchestratorPackageExports:  # noqa: N801
    """owlbear.orchestrator.__init__ must re-export the complete symbol set."""

    def test_exports_assemble_waves(self) -> None:
        """assemble_waves must be importable directly from owlbear.orchestrator."""
        import owlbear.orchestrator as pkg

        assert hasattr(pkg, "assemble_waves"), "assemble_waves missing from owlbear.orchestrator"

    def test_exports_wave(self) -> None:
        """Wave must be importable directly from owlbear.orchestrator."""
        import owlbear.orchestrator as pkg

        assert hasattr(pkg, "Wave"), "Wave missing from owlbear.orchestrator"

    def test_exports_loop_state(self) -> None:
        """LoopState must be importable directly from owlbear.orchestrator."""
        import owlbear.orchestrator as pkg

        assert hasattr(pkg, "LoopState"), "LoopState missing from owlbear.orchestrator"

    def test_exports_cycle_result(self) -> None:
        """CycleResult must be importable directly from owlbear.orchestrator."""
        import owlbear.orchestrator as pkg

        assert hasattr(pkg, "CycleResult"), "CycleResult missing from owlbear.orchestrator"

    def test_exports_format_prompt(self) -> None:
        """format_prompt must be importable directly from owlbear.orchestrator."""
        import owlbear.orchestrator as pkg

        assert hasattr(pkg, "format_prompt"), "format_prompt missing from owlbear.orchestrator"

    def test_exports_orchestrate(self) -> None:
        """orchestrate must be importable directly from owlbear.orchestrator."""
        import owlbear.orchestrator as pkg

        assert hasattr(pkg, "orchestrate"), "orchestrate missing from owlbear.orchestrator"


class TestFromAC_OrchestrateFunction:  # noqa: N801
    """orchestrate() — top-level async entry point in owlbear.orchestrator."""

    def test_orchestrate_is_callable(self) -> None:
        """orchestrate must be a callable (not None, not a non-callable attribute)."""
        import owlbear.orchestrator as pkg

        fn = getattr(pkg, "orchestrate", None)
        assert callable(fn), "orchestrate must be callable"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_orchestrate_runs_without_typeerror_on_empty_board(self) -> None:
        """orchestrate(kanban_bin, kanban_dir, client) completes on an empty board."""
        import owlbear.orchestrator as pkg

        orchestrate_fn = pkg.orchestrate  # type: ignore[attr-defined]
        client = _make_client()
        with patch("owlbear.orchestrator.loop.read_board", new=AsyncMock(return_value=[])):
            await orchestrate_fn(
                kanban_bin=Path("kanban/kanban-md.exe"),
                kanban_dir=Path("kanban"),
                client=client,
            )
