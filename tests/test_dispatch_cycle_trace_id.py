"""Failing tests for audit-centric dispatch-cycle trace ID (#434, RED phase).

AC coverage:
  AC1 - models.py: DispatchEvent and CompletionEvent gain cycle_id: str = "" field
  AC2 - loop.py: run_loop() generates uuid4().hex ONCE per cycle iteration, all waves share it
  AC3 - loop.py: cycle_id passed via explicit kwarg to dispatch_wave() and dispatch_entry()
  AC4 - loop.py: dispatch_entry() sets cycle_id on both DispatchEvent and CompletionEvent
  AC5 - log.py: AuditLog.query() accepts optional cycle_id: str | None = None filter
  AC6 - no Channel A/B format changes (dispatch_entry still returns bool)

Module paths:
  packages/orchestrator/src/owlbear/audit/models.py
  packages/orchestrator/src/owlbear/audit/log.py
  packages/orchestrator/src/owlbear/orchestrator/loop.py
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.audit import AuditLog, CompletionEvent, DispatchEvent
from owlbear.audit.models import audit_adapter
from owlbear.orchestrator import dispatch_entry, run_loop  # type: ignore[import]
from owlbear.orchestrator.loop import LoopState, dispatch_wave
from owlbear.orchestrator.waves import assemble_waves
from owlbear.planner.models import DispatchEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def entry() -> DispatchEntry:
    return DispatchEntry(task_id=7, agent="builder", target_status="review")


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    session_resp = MagicMock()
    session_resp.session_id = "cycle-test-sess"
    client.new_session = AsyncMock(return_value=session_resp)
    client.prompt = AsyncMock(return_value=MagicMock())
    return client


@pytest.fixture
def mock_audit_log() -> MagicMock:
    return MagicMock(spec=AuditLog)


def _dispatch_dict(cycle_id: str = "", task_id: int = 1, agent: str = "builder") -> dict[str, Any]:
    return {
        "type": "dispatch",
        "timestamp": "2026-03-30T10:00:00+00:00",
        "task_id": task_id,
        "agent": agent,
        "prompt_summary": f"task {task_id}",
        "session_id": "sess-1",
        "cycle_id": cycle_id,
    }


def _completion_dict(cycle_id: str = "", task_id: int = 1, agent: str = "builder") -> dict[str, Any]:
    return {
        "type": "completion",
        "timestamp": "2026-03-30T10:01:00+00:00",
        "task_id": task_id,
        "agent": agent,
        "outcome": "success",
        "duration_ms": 500,
        "files_changed": [],
        "cycle_id": cycle_id,
    }


# ---------------------------------------------------------------------------
# AC1: DispatchEvent and CompletionEvent gain cycle_id: str = "" field
# ---------------------------------------------------------------------------


class TestFromAC_CycleIdModels:  # noqa: N801
    """DispatchEvent and CompletionEvent gain cycle_id: str = "" field (#434 AC1)."""

    # --- DispatchEvent ---

    def test_dispatch_event_has_cycle_id_field(self) -> None:
        """DispatchEvent must expose a cycle_id attribute."""
        event = DispatchEvent(
            timestamp="2026-03-30T10:00:00+00:00",
            task_id=1,
            agent="builder",
            prompt_summary="x",
            session_id="s1",
        )
        assert hasattr(event, "cycle_id"), "DispatchEvent is missing the cycle_id field"

    def test_dispatch_event_cycle_id_defaults_to_empty_string(self) -> None:
        """DispatchEvent.cycle_id must default to '' for backwards compat with legacy JSONL."""
        event = DispatchEvent(
            timestamp="2026-03-30T10:00:00+00:00",
            task_id=1,
            agent="builder",
            prompt_summary="x",
            session_id="s1",
        )
        assert event.cycle_id == ""

    def test_dispatch_event_cycle_id_accepts_value(self) -> None:
        """DispatchEvent must accept a non-empty cycle_id at construction time."""
        event = DispatchEvent(
            timestamp="2026-03-30T10:00:00+00:00",
            task_id=1,
            agent="builder",
            prompt_summary="x",
            session_id="s1",
            cycle_id="abc123hex",
        )
        assert event.cycle_id == "abc123hex"

    def test_dispatch_event_cycle_id_serializes_to_json(self) -> None:
        """cycle_id must appear in DispatchEvent.model_dump_json() output."""
        event = DispatchEvent(
            timestamp="2026-03-30T10:00:00+00:00",
            task_id=1,
            agent="builder",
            prompt_summary="x",
            session_id="s1",
            cycle_id="myhex",
        )
        dumped = json.loads(event.model_dump_json())
        assert "cycle_id" in dumped
        assert dumped["cycle_id"] == "myhex"

    # --- CompletionEvent ---

    def test_completion_event_has_cycle_id_field(self) -> None:
        """CompletionEvent must expose a cycle_id attribute."""
        event = CompletionEvent(
            timestamp="2026-03-30T10:01:00+00:00",
            task_id=1,
            agent="builder",
            outcome="success",
            duration_ms=100,
            files_changed=[],
        )
        assert hasattr(event, "cycle_id"), "CompletionEvent is missing the cycle_id field"

    def test_completion_event_cycle_id_defaults_to_empty_string(self) -> None:
        """CompletionEvent.cycle_id must default to '' for backwards compat."""
        event = CompletionEvent(
            timestamp="2026-03-30T10:01:00+00:00",
            task_id=1,
            agent="builder",
            outcome="success",
            duration_ms=100,
            files_changed=[],
        )
        assert event.cycle_id == ""

    def test_completion_event_cycle_id_accepts_value(self) -> None:
        """CompletionEvent must accept a non-empty cycle_id at construction time."""
        event = CompletionEvent(
            timestamp="2026-03-30T10:01:00+00:00",
            task_id=1,
            agent="builder",
            outcome="success",
            duration_ms=100,
            files_changed=[],
            cycle_id="cycle-hex-456",
        )
        assert event.cycle_id == "cycle-hex-456"

    def test_completion_event_cycle_id_serializes_to_json(self) -> None:
        """cycle_id must appear in CompletionEvent.model_dump_json() output."""
        event = CompletionEvent(
            timestamp="2026-03-30T10:01:00+00:00",
            task_id=1,
            agent="builder",
            outcome="success",
            duration_ms=500,
            files_changed=[],
            cycle_id="comphex",
        )
        dumped = json.loads(event.model_dump_json())
        assert "cycle_id" in dumped
        assert dumped["cycle_id"] == "comphex"

    # --- TypeAdapter / JSONL round-trip ---

    def test_audit_adapter_deserializes_dispatch_with_cycle_id(self) -> None:
        """audit_adapter must deserialize a JSONL line that contains cycle_id."""
        raw = json.dumps(_dispatch_dict(cycle_id="somehex"))
        event = audit_adapter.validate_json(raw)
        assert isinstance(event, DispatchEvent)
        assert event.cycle_id == "somehex"

    def test_audit_adapter_deserializes_completion_with_cycle_id(self) -> None:
        """audit_adapter must deserialize a JSONL line with cycle_id in CompletionEvent."""
        raw = json.dumps(_completion_dict(cycle_id="anotherhex"))
        event = audit_adapter.validate_json(raw)
        assert isinstance(event, CompletionEvent)
        assert event.cycle_id == "anotherhex"

    def test_audit_adapter_deserializes_legacy_dispatch_without_cycle_id(self) -> None:
        """audit_adapter must accept legacy JSONL without cycle_id; defaults to ''."""
        raw = json.dumps({
            "type": "dispatch",
            "timestamp": "2026-03-30T10:00:00+00:00",
            "task_id": 1,
            "agent": "builder",
            "prompt_summary": "do something",
            "session_id": "sess-1",
            # no cycle_id key
        })
        event = audit_adapter.validate_json(raw)
        assert isinstance(event, DispatchEvent)
        assert event.cycle_id == ""

    def test_audit_adapter_deserializes_legacy_completion_without_cycle_id(self) -> None:
        """audit_adapter must accept legacy JSONL without cycle_id on CompletionEvent."""
        raw = json.dumps({
            "type": "completion",
            "timestamp": "2026-03-30T10:01:00+00:00",
            "task_id": 1,
            "agent": "builder",
            "outcome": "success",
            "duration_ms": 100,
            "files_changed": [],
            # no cycle_id key
        })
        event = audit_adapter.validate_json(raw)
        assert isinstance(event, CompletionEvent)
        assert event.cycle_id == ""


# ---------------------------------------------------------------------------
# AC3: cycle_id passed via explicit keyword parameter
# ---------------------------------------------------------------------------


class TestFromAC_CycleIdSignatures:  # noqa: N801
    """dispatch_entry() and dispatch_wave() must accept cycle_id as explicit kwarg (#434 AC3)."""

    def test_dispatch_entry_accepts_cycle_id_kwarg(self) -> None:
        """dispatch_entry signature must declare cycle_id as a keyword-only parameter."""
        sig = inspect.signature(dispatch_entry)
        assert "cycle_id" in sig.parameters, (
            "dispatch_entry must accept cycle_id as a keyword parameter"
        )

    def test_dispatch_wave_accepts_cycle_id_kwarg(self) -> None:
        """dispatch_wave signature must declare cycle_id as a keyword-only parameter."""
        sig = inspect.signature(dispatch_wave)
        assert "cycle_id" in sig.parameters, (
            "dispatch_wave must accept cycle_id as a keyword parameter"
        )


# ---------------------------------------------------------------------------
# AC4: dispatch_entry() sets cycle_id on both DispatchEvent and CompletionEvent
# ---------------------------------------------------------------------------


class TestFromAC_CycleIdDispatchEntry:  # noqa: N801
    """dispatch_entry() propagates cycle_id to both events it constructs (#434 AC4)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_event_carries_provided_cycle_id(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """DispatchEvent logged by dispatch_entry must carry the provided cycle_id."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log, cycle_id="deadbeef")

        mock_audit_log.log_dispatch.assert_called_once()
        event: DispatchEvent = mock_audit_log.log_dispatch.call_args.args[0]
        assert isinstance(event, DispatchEvent)
        assert event.cycle_id == "deadbeef"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_completion_event_carries_provided_cycle_id(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """CompletionEvent logged by dispatch_entry must carry the provided cycle_id."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log, cycle_id="cafebabe")

        mock_audit_log.log_completion.assert_called_once()
        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert isinstance(event, CompletionEvent)
        assert event.cycle_id == "cafebabe"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_both_events_share_the_same_cycle_id(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """DispatchEvent and CompletionEvent must carry the identical cycle_id."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log, cycle_id="shared123")

        dispatch_ev: DispatchEvent = mock_audit_log.log_dispatch.call_args.args[0]
        completion_ev: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert dispatch_ev.cycle_id == completion_ev.cycle_id == "shared123"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_default_cycle_id_sets_empty_string_on_both_events(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """When no cycle_id is provided, both events get cycle_id='' (backwards compat)."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        dispatch_ev: DispatchEvent = mock_audit_log.log_dispatch.call_args.args[0]
        completion_ev: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert dispatch_ev.cycle_id == ""
        assert completion_ev.cycle_id == ""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_entry_still_returns_bool(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """dispatch_entry must still return bool — no Channel A/B format change (#434 AC6)."""
        result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log, cycle_id="x")
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# AC3 + AC4: dispatch_wave threads cycle_id through to dispatch_entry
# ---------------------------------------------------------------------------


class TestFromAC_CycleIdDispatchWave:  # noqa: N801
    """dispatch_wave() forwards cycle_id to every dispatch_entry() call (#434 AC3)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_wave_forwards_cycle_id_to_dispatch_entry(
        self,
        mock_client: MagicMock,
    ) -> None:
        """dispatch_wave must pass cycle_id kwarg to each dispatch_entry() call."""
        wave_entries = [DispatchEntry(task_id=5, agent="builder", target_status="review")]
        waves = assemble_waves(wave_entries, wave_size=4, cycle=1)
        assert waves, "Expected at least one wave from assemble_waves"

        state = LoopState()

        with patch(
            "owlbear.orchestrator.loop.dispatch_entry",
            new=AsyncMock(return_value=True),
        ) as mock_de:
            await dispatch_wave(waves[0], mock_client, state, cycle_id="forwarded123")

        assert mock_de.called
        call_kwargs = mock_de.call_args.kwargs
        assert "cycle_id" in call_kwargs, (
            "dispatch_wave must forward cycle_id to dispatch_entry as a keyword argument"
        )
        assert call_kwargs["cycle_id"] == "forwarded123"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_wave_forwards_cycle_id_to_all_entries(
        self,
        mock_client: MagicMock,
    ) -> None:
        """dispatch_wave must pass the same cycle_id to every dispatch_entry call in the wave."""
        wave_entries = [
            DispatchEntry(task_id=10, agent="builder", target_status="review"),
            DispatchEntry(task_id=11, agent="researcher", target_status="backlog"),
        ]
        waves = assemble_waves(wave_entries, wave_size=4, cycle=1)
        assert waves

        state = LoopState()

        with patch(
            "owlbear.orchestrator.loop.dispatch_entry",
            new=AsyncMock(return_value=True),
        ) as mock_de:
            await dispatch_wave(waves[0], mock_client, state, cycle_id="broadcast-id")

        cycle_ids = [c.kwargs.get("cycle_id") for c in mock_de.call_args_list]
        assert all(cid == "broadcast-id" for cid in cycle_ids), (
            f"All entries must receive the same cycle_id; got {cycle_ids}"
        )


# ---------------------------------------------------------------------------
# AC2: run_loop() generates uuid4().hex ONCE per cycle; all waves share it
# ---------------------------------------------------------------------------


class TestFromAC_CycleIdRunLoop:  # noqa: N801
    """run_loop() generates uuid4().hex once per cycle; waves share it (#434 AC2)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_run_loop_passes_cycle_id_to_dispatch_wave(
        self,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """run_loop must pass a cycle_id (32-char uuid4 hex) to dispatch_wave."""
        kanban_bin = tmp_path / "kanban-md.exe"
        kanban_bin.touch()

        wave_entry = DispatchEntry(task_id=2, agent="builder", target_status="review")

        with (
            patch(
                "owlbear.orchestrator.loop.read_board",
                new=AsyncMock(return_value=[MagicMock()]),  # always returns tasks; loop exits via select_tasks
            ),
            patch(
                "owlbear.orchestrator.loop.select_tasks",
                side_effect=[
                    MagicMock(entries=[wave_entry]),  # cycle 1: entries to dispatch
                    MagicMock(entries=[]),            # cycle 2: empty → break
                ],
            ),
            patch(
                "owlbear.orchestrator.loop.assemble_waves",
                return_value=[MagicMock(entries=[wave_entry])],
            ),
            patch(
                "owlbear.orchestrator.loop.dispatch_wave",
                new=AsyncMock(return_value=MagicMock(successes=[2], failures=[], rate_limited=False)),
            ) as mock_dispatch_wave,
        ):
            await run_loop(
                kanban_bin=kanban_bin,
                kanban_dir=tmp_path,
                client=mock_client,
            )

        assert mock_dispatch_wave.called
        call_kwargs = mock_dispatch_wave.call_args.kwargs
        assert "cycle_id" in call_kwargs, (
            "run_loop must pass cycle_id to dispatch_wave as a keyword argument"
        )
        cycle_id = call_kwargs["cycle_id"]
        assert isinstance(cycle_id, str), "cycle_id must be a string"
        assert len(cycle_id) == 32, f"uuid4().hex is 32 chars; got {len(cycle_id)!r}"
        assert all(c in "0123456789abcdef" for c in cycle_id), (
            f"cycle_id must be lowercase hex; got {cycle_id!r}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_waves_within_one_cycle_share_the_same_cycle_id(
        self,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """All waves within a single cycle must receive the same cycle_id."""
        kanban_bin = tmp_path / "kanban-md.exe"
        kanban_bin.touch()

        wave1 = MagicMock(entries=[DispatchEntry(task_id=3, agent="builder", target_status="review")])
        wave2 = MagicMock(entries=[DispatchEntry(task_id=4, agent="reviewer", target_status="docs")])
        wave_result = MagicMock(successes=[], failures=[], rate_limited=False)

        entries = [
            DispatchEntry(task_id=3, agent="builder", target_status="review"),
            DispatchEntry(task_id=4, agent="reviewer", target_status="docs"),
        ]

        with (
            patch(
                "owlbear.orchestrator.loop.read_board",
                new=AsyncMock(return_value=[MagicMock()]),  # loop exits via select_tasks
            ),
            patch(
                "owlbear.orchestrator.loop.select_tasks",
                side_effect=[
                    MagicMock(entries=entries),  # cycle 1: dispatch both entries
                    MagicMock(entries=[]),        # cycle 2: empty → break
                ],
            ),
            patch(
                "owlbear.orchestrator.loop.assemble_waves",
                return_value=[wave1, wave2],
            ),
            patch(
                "owlbear.orchestrator.loop.dispatch_wave",
                new=AsyncMock(return_value=wave_result),
            ) as mock_dw,
        ):
            await run_loop(
                kanban_bin=kanban_bin,
                kanban_dir=tmp_path,
                client=mock_client,
            )

        assert mock_dw.call_count == 2, f"Expected 2 waves dispatched, got {mock_dw.call_count}"
        cycle_ids = [c.kwargs.get("cycle_id") for c in mock_dw.call_args_list]
        assert cycle_ids[0] is not None, "Wave 1 must receive a cycle_id"
        assert cycle_ids[1] is not None, "Wave 2 must receive a cycle_id"
        assert cycle_ids[0] == cycle_ids[1], (
            f"Waves in the same cycle must share cycle_id; got {cycle_ids}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_different_cycles_get_different_cycle_ids(
        self,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Each cycle iteration must generate a distinct cycle_id (uuid4 is random)."""
        kanban_bin = tmp_path / "kanban-md.exe"
        kanban_bin.touch()

        wave_entry1 = DispatchEntry(task_id=20, agent="builder", target_status="review")
        wave_entry2 = DispatchEntry(task_id=21, agent="builder", target_status="review")
        wave_result = MagicMock(successes=[], failures=[], rate_limited=False)

        with (
            patch(
                "owlbear.orchestrator.loop.read_board",
                new=AsyncMock(return_value=[MagicMock()]),  # loop exits via select_tasks
            ),
            patch(
                "owlbear.orchestrator.loop.select_tasks",
                side_effect=[
                    MagicMock(entries=[wave_entry1]),  # cycle 1
                    MagicMock(entries=[wave_entry2]),  # cycle 2
                    MagicMock(entries=[]),             # cycle 3: empty → break
                ],
            ),
            patch(
                "owlbear.orchestrator.loop.assemble_waves",
                side_effect=[
                    [MagicMock(entries=[wave_entry1])],
                    [MagicMock(entries=[wave_entry2])],
                ],
            ),
            patch(
                "owlbear.orchestrator.loop.dispatch_wave",
                new=AsyncMock(return_value=wave_result),
            ) as mock_dw,
        ):
            await run_loop(
                kanban_bin=kanban_bin,
                kanban_dir=tmp_path,
                client=mock_client,
            )

        assert mock_dw.call_count == 2, f"Expected 2 dispatch_wave calls; got {mock_dw.call_count}"
        cycle_ids = [c.kwargs.get("cycle_id") for c in mock_dw.call_args_list]
        assert cycle_ids[0] is not None, "Cycle 1 must pass a cycle_id to dispatch_wave"
        assert cycle_ids[1] is not None, "Cycle 2 must pass a cycle_id to dispatch_wave"
        assert cycle_ids[0] != cycle_ids[1], (
            "Different cycle iterations must produce different cycle_ids"
        )


# ---------------------------------------------------------------------------
# AC5: AuditLog.query() accepts optional cycle_id filter
# ---------------------------------------------------------------------------


class TestFromAC_CycleIdAuditQuery:  # noqa: N801
    """AuditLog.query() accepts optional cycle_id: str | None = None filter (#434 AC5)."""

    def test_query_accepts_cycle_id_parameter(self) -> None:
        """AuditLog.query() must declare cycle_id as a keyword parameter."""
        sig = inspect.signature(AuditLog.query)
        assert "cycle_id" in sig.parameters, (
            "AuditLog.query must accept an optional cycle_id filter parameter"
        )

    def test_query_cycle_id_default_is_none(self) -> None:
        """AuditLog.query()'s cycle_id parameter must default to None (no filter)."""
        sig = inspect.signature(AuditLog.query)
        assert sig.parameters["cycle_id"].default is None

    def test_query_cycle_id_none_returns_all_events(self, tmp_path: Path) -> None:
        """query(cycle_id=None) must return all events including legacy with cycle_id=''."""
        log = AuditLog(tmp_path / "audit")
        log._audit_dir.mkdir(parents=True, exist_ok=True)

        # write one legacy (no cycle_id) and one with cycle_id
        legacy_line = json.dumps({
            "type": "dispatch",
            "timestamp": "2026-03-30T10:00:00+00:00",
            "task_id": 1,
            "agent": "builder",
            "prompt_summary": "x",
            "session_id": "s1",
        })
        new_line = json.dumps(_completion_dict(cycle_id="cycle-abc"))
        (log._audit_dir / "session.jsonl").write_text(
            legacy_line + "\n" + new_line + "\n", encoding="utf-8"
        )

        events = log.query(cycle_id=None)
        assert len(events) == 2

    def test_query_filters_by_exact_cycle_id(self, tmp_path: Path) -> None:
        """query(cycle_id='X') must return only events whose cycle_id equals 'X'."""
        log = AuditLog(tmp_path / "audit")
        log._audit_dir.mkdir(parents=True, exist_ok=True)

        matching = json.dumps(_dispatch_dict(cycle_id="match-hex"))
        other = json.dumps(_dispatch_dict(cycle_id="other-hex", task_id=2))
        (log._audit_dir / "sess.jsonl").write_text(
            matching + "\n" + other + "\n", encoding="utf-8"
        )

        events = log.query(cycle_id="match-hex")
        assert len(events) == 1
        assert events[0].cycle_id == "match-hex"  # type: ignore[union-attr]

    def test_query_nonmatching_cycle_id_returns_empty_list(self, tmp_path: Path) -> None:
        """query(cycle_id='no-match') must return empty list when nothing matches."""
        log = AuditLog(tmp_path / "audit")
        log._audit_dir.mkdir(parents=True, exist_ok=True)

        (log._audit_dir / "sess.jsonl").write_text(
            json.dumps(_dispatch_dict(cycle_id="actual-hex")) + "\n", encoding="utf-8"
        )

        events = log.query(cycle_id="no-match")
        assert events == []

    def test_query_cycle_id_filter_on_empty_directory(self, tmp_path: Path) -> None:
        """query(cycle_id='X') on empty or missing directory must return empty list."""
        log = AuditLog(tmp_path / "audit")
        # directory does not yet exist
        events = log.query(cycle_id="any-id")
        assert events == []

    def test_query_cycle_id_filter_composes_with_agent_filter(self, tmp_path: Path) -> None:
        """cycle_id filter must combine with agent filter (both conditions applied)."""
        log = AuditLog(tmp_path / "audit")
        log._audit_dir.mkdir(parents=True, exist_ok=True)

        builder_event = json.dumps(_dispatch_dict(cycle_id="cycle-xyz", agent="builder", task_id=1))
        reviewer_event = json.dumps(_dispatch_dict(cycle_id="cycle-xyz", agent="reviewer", task_id=2))
        (log._audit_dir / "sess.jsonl").write_text(
            builder_event + "\n" + reviewer_event + "\n", encoding="utf-8"
        )

        events = log.query(cycle_id="cycle-xyz", agent="builder")
        assert len(events) == 1
        assert events[0].agent == "builder"
        assert events[0].cycle_id == "cycle-xyz"  # type: ignore[union-attr]

    def test_query_cycle_id_empty_string_matches_only_legacy(self, tmp_path: Path) -> None:
        """query(cycle_id='') must return only events with cycle_id='' (legacy events)."""
        log = AuditLog(tmp_path / "audit")
        log._audit_dir.mkdir(parents=True, exist_ok=True)

        legacy = json.dumps({
            "type": "dispatch",
            "timestamp": "2026-03-30T10:00:00+00:00",
            "task_id": 1,
            "agent": "builder",
            "prompt_summary": "x",
            "session_id": "s1",
            # no cycle_id → will default to ""
        })
        new_event = json.dumps(_dispatch_dict(cycle_id="new-hex", task_id=2))

        (log._audit_dir / "sess.jsonl").write_text(
            legacy + "\n" + new_event + "\n", encoding="utf-8"
        )

        events = log.query(cycle_id="")
        assert len(events) == 1
        assert events[0].task_id == 1
