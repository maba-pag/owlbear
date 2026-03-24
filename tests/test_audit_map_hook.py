"""Tests for AuditMapAdvisoryHook — TASK_COMPLETE audit-map advisory worker.

AC: #982 — eligibility gates (outcome, config flag, tag) and
coroutine safety contract (scratch-only writes, no board mutations,
optional channel notification).

All tests FAIL (RED) before the production module exists — the import
below raises ImportError, which fails every test in this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.channels.base import ChannelPlugin

# RED: module does not exist yet — all tests will fail with ImportError
from owlbear.core.audit_map_hook import AuditMapAdvisoryHook  # type: ignore[import]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(*, enabled: bool = True) -> MagicMock:
    """Build a minimal settings mock with audit_map_worker_enabled set."""
    settings = MagicMock()
    settings.audit_map_worker_enabled = enabled
    return settings


def _kanban_show_json(task_id: str, *, tags: list[str] | None = None) -> str:
    """Serialise a minimal kanban-md show --json response payload."""
    return json.dumps({"id": task_id, "tags": tags or []})


def _subprocess_returning_tags(tags: list[str], *, task_id: str = "42") -> MagicMock:
    """Build a subprocess.run mock result with the given task tags."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = _kanban_show_json(task_id, tags=tags)
    return result


def _payload(task_id: str = "42", outcome: str = "success") -> dict[str, Any]:
    """Build a TASK_COMPLETE payload."""
    return {"task_id": task_id, "outcome": outcome}


def _make_hook(
    tmp_path: Path,
    *,
    enabled: bool = True,
    supervisor: object | None = None,
    channel: object | None = None,
) -> AuditMapAdvisoryHook:
    """Create an AuditMapAdvisoryHook with sensible test defaults."""
    return AuditMapAdvisoryHook(
        settings=_make_settings(enabled=enabled),
        supervisor=supervisor if supervisor is not None else MagicMock(),
        kanban_root=tmp_path,
        workspace_root=tmp_path,
        channel=channel,
    )


async def _trigger_and_capture_worker(
    tmp_path: Path,
    *,
    task_id: str = "42",
    channel: object | None = None,
) -> Any:
    """Drive __call__ through all passing gates and return the scheduled awaitable.

    Uses a real MagicMock supervisor; subprocess.run is patched to return a
    kanban-md JSON with the ``worker:audit-map`` tag.  Returns the single
    argument passed to ``supervisor.schedule()``.
    """
    supervisor = MagicMock()
    hook = _make_hook(tmp_path, supervisor=supervisor, channel=channel)
    with patch(
        "owlbear.core.audit_map_hook.subprocess.run",
        return_value=_subprocess_returning_tags(["worker:audit-map"], task_id=task_id),
    ):
        await hook(_payload(task_id=task_id, outcome="success"))
    supervisor.schedule.assert_called_once()
    return supervisor.schedule.call_args[0][0]


# ---------------------------------------------------------------------------
# AC2-AC5: Eligibility gates in __call__
# ---------------------------------------------------------------------------


class TestFromAC_AuditMapAdvisoryHookEligibility:
    """``__call__`` eligibility gates: outcome, config flag, and audit-map tag.

    All tests FAIL (RED) before ``AuditMapAdvisoryHook`` exists.
    """

    # -- AC2: outcome gate ---------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_failure_outcome_skips_schedule(self, tmp_path: Path) -> None:
        """AC2: outcome == 'failure' → returns immediately; no tag lookup, no schedule."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch("owlbear.core.audit_map_hook.subprocess.run") as mock_subprocess:
            await hook(_payload(outcome="failure"))
        supervisor.schedule.assert_not_called()
        mock_subprocess.assert_not_called()  # proves immediate return before tag lookup

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_success_outcome_skipped_skips_schedule(self, tmp_path: Path) -> None:
        """AC2 edge: outcome == 'skipped' → returns immediately; no tag lookup, no schedule."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch("owlbear.core.audit_map_hook.subprocess.run") as mock_subprocess:
            await hook(_payload(outcome="skipped"))
        supervisor.schedule.assert_not_called()
        mock_subprocess.assert_not_called()  # proves immediate return before tag lookup

    # -- AC3: config flag gate -----------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_config_flag_false_skips_schedule(self, tmp_path: Path) -> None:
        """AC3: audit_map_worker_enabled=False → returns immediately; no tag lookup, no schedule."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, enabled=False, supervisor=supervisor)
        with patch("owlbear.core.audit_map_hook.subprocess.run") as mock_subprocess:
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_not_called()
        mock_subprocess.assert_not_called()  # proves immediate return before tag lookup

    # -- AC4: worker:audit-map tag gate --------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_missing_audit_map_tag_skips_schedule(self, tmp_path: Path) -> None:
        """AC4: task has unrelated tags but not 'worker:audit-map' → schedule not called."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags(["phase-6", "type:build"]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_tags_skips_schedule(self, tmp_path: Path) -> None:
        """AC4 edge: task has no tags at all → supervisor.schedule() not called."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags([]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_tag_resolution_uses_subprocess_kanban_show_json(self, tmp_path: Path) -> None:
        """AC4: tag resolution invokes subprocess.run with kanban-md show <id> --json."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        mock_run = MagicMock(return_value=_subprocess_returning_tags(["worker:audit-map"]))
        with patch("owlbear.core.audit_map_hook.subprocess.run", mock_run):
            await hook(_payload(task_id="99", outcome="success"))
        mock_run.assert_called_once()
        call_args: list[str] = [str(a) for a in mock_run.call_args[0][0]]
        assert "show" in call_args, f"Expected 'show' in subprocess args: {call_args}"
        assert "99" in call_args, f"Expected task_id '99' in subprocess args: {call_args}"
        assert "--json" in call_args, f"Expected '--json' in subprocess args: {call_args}"

    # -- AC5: successful schedule call ---------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_all_gates_pass_calls_schedule_exactly_once(self, tmp_path: Path) -> None:
        """AC5: outcome=success + flag=True + tag present → supervisor.schedule() once."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags(["worker:audit-map", "phase-6"]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_all_gates_pass_schedule_receives_lazy_awaitable(self, tmp_path: Path) -> None:
        """AC5: argument to supervisor.schedule() is a _LazyCoroutine-style awaitable."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags(["worker:audit-map"]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_called_once()
        scheduled = supervisor.schedule.call_args[0][0]
        # Must satisfy _LazyCoroutine contract: has __await__ and close()
        assert hasattr(scheduled, "__await__"), (
            "schedule() argument must have __await__ (_LazyCoroutine pattern)"
        )
        assert hasattr(scheduled, "close"), (
            "schedule() argument must have close() to avoid unawaited-coroutine warnings"
        )
        # Defensive: clean up to avoid ResourceWarning
        scheduled.close()


# ---------------------------------------------------------------------------
# AC6-AC9: Worker coroutine safety contract
# ---------------------------------------------------------------------------


class TestFromAC_AuditMapAdvisoryHookWorker:
    """Scheduled coroutine: scratch-only writes, no board mutations, channel notification.

    Each test drives the hook through ``__call__`` with all gates passing,
    captures the scheduled ``_LazyCoroutine``, then awaits it to verify
    the worker's safety contract.

    All tests FAIL (RED) before ``AuditMapAdvisoryHook`` exists.
    """

    # -- AC6: scratch-only artifact ------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_writes_scratch_file_at_correct_path(self, tmp_path: Path) -> None:
        """AC6: worker creates docs/scratch/{task-id}-audit-map.md under workspace_root."""
        lazy_coro: Any = await _trigger_and_capture_worker(tmp_path, task_id="42")
        await lazy_coro
        expected = tmp_path / "docs" / "scratch" / "42-audit-map.md"
        assert expected.is_file(), f"Expected scratch file at {expected} after worker run"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_creates_no_other_docs_files(self, tmp_path: Path) -> None:
        """AC6 edge: no files created under docs/ outside docs/scratch/."""
        docs_root = tmp_path / "docs"
        docs_root.mkdir(parents=True, exist_ok=True)
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42")
        await lazy_coro
        non_scratch = [f for f in docs_root.rglob("*") if f.is_file() and "scratch" not in f.parts]
        assert not non_scratch, (
            f"Worker must not create files outside docs/scratch/, found: {non_scratch}"
        )

    # -- AC7: no board mutations ---------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_does_not_call_subprocess_during_execution(self, tmp_path: Path) -> None:
        """AC7: worker coroutine makes no subprocess.run calls (including kanban-md)."""
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42")
        with patch("owlbear.core.audit_map_hook.subprocess.run") as mock_run:
            await lazy_coro
        mock_run.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_does_not_write_to_src(self, tmp_path: Path) -> None:
        """AC7: worker coroutine writes no files under src/."""
        src_root = tmp_path / "src"
        src_root.mkdir(parents=True, exist_ok=True)
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42")
        await lazy_coro
        src_files = [f for f in src_root.rglob("*") if f.is_file()]
        assert not src_files, f"Worker must not write to src/, but found: {src_files}"

    # -- AC8: channel notification when available ----------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_sends_channel_message_once(self, tmp_path: Path) -> None:
        """AC8: channel.send() called exactly once when channel is provided."""
        channel = AsyncMock(spec=ChannelPlugin)
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42", channel=channel)
        await lazy_coro
        channel.send.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_channel_message_contains_task_id(self, tmp_path: Path) -> None:
        """AC8: the message sent via channel.send() contains the task ID."""
        channel = AsyncMock(spec=ChannelPlugin)
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="77", channel=channel)
        await lazy_coro
        channel.send.assert_called_once()
        message: str = channel.send.call_args[0][0]
        assert "77" in message, (
            f"channel.send() message must contain task ID '77', got: {message!r}"
        )

    # -- AC9: no error / no send when channel is None ------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_completes_without_error_when_channel_none(self, tmp_path: Path) -> None:
        """AC9: channel=None → worker completes without raising any exception."""
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42", channel=None)
        # Must not raise
        await lazy_coro

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_channel_send_not_called_when_channel_none(self, tmp_path: Path) -> None:
        """AC9: channel=None → channel.send() is never called."""
        channel_spy = AsyncMock(spec=ChannelPlugin)
        lazy_coro_none = await _trigger_and_capture_worker(tmp_path, task_id="43", channel=None)
        await lazy_coro_none
        channel_spy.send.assert_not_called()


# ---------------------------------------------------------------------------
# AC6/AC7: Path-traversal confinement (retry gap — missing from first TestFromAC_ cycle)
# ---------------------------------------------------------------------------


class TestFromAC_AuditMapAdvisoryHookPathSafety:
    """Worker must never write outside docs/scratch/, regardless of task_id content.

    AC6: output confined to docs/scratch/{task-id}-audit-map.md.
    AC7: no writes under src/ or under docs/ outside scratch/.

    All tests FAIL (RED) because the current implementation joins task_id
    into the output path without sanitisation, allowing ``../`` sequences to
    escape docs/scratch/.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_single_parent_traversal_task_id_does_not_escape_scratch(
        self, tmp_path: Path
    ) -> None:
        """AC6/AC7: task_id='../escape' must not write docs/escape-audit-map.md.

        Path trace: docs/scratch/../escape-audit-map.md resolves to
        docs/escape-audit-map.md, which is outside docs/scratch/.
        """
        task_id = "../escape"
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id=task_id)
        await lazy_coro

        # Path traversal target: one level above scratch/ inside docs/
        escaped = tmp_path / "docs" / "escape-audit-map.md"
        assert not escaped.exists(), (
            f"Path traversal: worker wrote to {escaped} — file must stay inside docs/scratch/"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_double_parent_traversal_task_id_does_not_write_to_src(
        self, tmp_path: Path
    ) -> None:
        """AC7: task_id='../../src/malicious' must not write to src/malicious-audit-map.md.

        Path trace: docs/scratch/../../src/malicious-audit-map.md resolves to
        src/malicious-audit-map.md, which is under src/.
        Pre-create src/ so the write attempt succeeds and we can assert the file's presence.
        """
        task_id = "../../src/malicious"
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)

        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id=task_id)
        await lazy_coro

        # Path traversal target: two levels up from scratch/ into src/
        escaped = tmp_path / "src" / "malicious-audit-map.md"
        assert not escaped.exists(), (
            f"Path traversal: worker wrote to {escaped} — AC7 forbids writes under src/"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_all_written_files_are_under_scratch(self, tmp_path: Path) -> None:
        """AC6: after worker run with path-like task_id, every created file is inside docs/scratch/.

        Uses '../escape' — docs/scratch/../escape-audit-map.md resolves to
        docs/escape-audit-map.md, which is not inside docs/scratch/.
        """
        task_id = "../escape"
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id=task_id)
        await lazy_coro

        scratch = tmp_path / "docs" / "scratch"
        docs_root = tmp_path / "docs"
        non_scratch_files = [
            f for f in docs_root.rglob("*") if f.is_file() and not f.is_relative_to(scratch)
        ]
        assert not non_scratch_files, (
            f"AC6 violated: files outside docs/scratch/: {non_scratch_files}"
        )


class TestFromAC_AuditMapAdvisoryHookBranches:
    """Defensive branches and helper seams verifying the eligibility contract."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_task_id_skips_subprocess_and_schedule(self, tmp_path: Path) -> None:
        """Empty task IDs short-circuit before tag lookup."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch("owlbear.core.audit_map_hook.subprocess.run") as mock_run:
            await hook(_payload(task_id="", outcome="success"))
        supervisor.schedule.assert_not_called()
        mock_run.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_subprocess_exception_skips_schedule(self, tmp_path: Path) -> None:
        """Tag resolution failures are handled safely."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch("owlbear.core.audit_map_hook.subprocess.run", side_effect=RuntimeError("boom")):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_zero_subprocess_returncode_skips_schedule(self, tmp_path: Path) -> None:
        """Non-zero kanban command return code blocks scheduling."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        failed = MagicMock()
        failed.returncode = 1
        failed.stdout = ""
        with patch("owlbear.core.audit_map_hook.subprocess.run", return_value=failed):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_invalid_json_skips_schedule(self, tmp_path: Path) -> None:
        """Malformed JSON in kanban output blocks scheduling."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        malformed = MagicMock()
        malformed.returncode = 0
        malformed.stdout = "{"
        with patch("owlbear.core.audit_map_hook.subprocess.run", return_value=malformed):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_dict_json_payload_skips_schedule(self, tmp_path: Path) -> None:
        """Only dict payloads are accepted from kanban JSON output."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        payload = MagicMock()
        payload.returncode = 0
        payload.stdout = json.dumps(["worker:audit-map"])
        with patch("owlbear.core.audit_map_hook.subprocess.run", return_value=payload):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_list_tags_skips_schedule(self, tmp_path: Path) -> None:
        """A non-list tags field does not pass eligibility."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        payload = MagicMock()
        payload.returncode = 0
        payload.stdout = json.dumps({"tags": "worker:audit-map"})
        with patch("owlbear.core.audit_map_hook.subprocess.run", return_value=payload):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    def test_register_attaches_task_complete_handler(self, tmp_path: Path) -> None:
        """register() wires the hook into the task_complete event."""
        from owlbear.core.hooks import HookEvent, HookRegistry

        hook = _make_hook(tmp_path)
        registry = HookRegistry()
        hook.register(registry)
        handlers = registry.handlers.get(HookEvent.TASK_COMPLETE, [])
        assert hook in handlers

    @pytest.mark.asyncio(loop_scope="function")
    async def test_lazy_coroutine_close_after_await_is_safe(self, tmp_path: Path) -> None:
        """The scheduled lazy awaitable still supports explicit close()."""
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42")
        await lazy_coro
        lazy_coro.close()


# ---------------------------------------------------------------------------
# AC7: OwlBearSettings.audit_map_worker_enabled config field (#983)
# ---------------------------------------------------------------------------


class TestFromAC_983_AuditMapConfigFlag:
    """AC7: audit_map_worker_enabled: bool = Field(default=False) in OwlBearSettings.

    All tests FAIL (RED) until the field is added to src/owlbear/config.py.
    """

    def test_owlbear_settings_has_audit_map_worker_enabled_field(self) -> None:
        """AC7: OwlBearSettings exposes audit_map_worker_enabled as a model field."""
        from owlbear.config import OwlBearSettings

        assert "audit_map_worker_enabled" in OwlBearSettings.model_fields, (
            "OwlBearSettings must declare audit_map_worker_enabled as a Pydantic model field"
        )

    def test_audit_map_worker_enabled_defaults_to_false(self) -> None:
        """AC7: audit_map_worker_enabled defaults to False when not set."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert settings.audit_map_worker_enabled is False, (
            "audit_map_worker_enabled must default to False"
        )

    def test_audit_map_worker_enabled_is_bool_not_int(self) -> None:
        """AC7: the default value is strictly bool, not an int or other truthy type."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert type(settings.audit_map_worker_enabled) is bool, (
            "audit_map_worker_enabled must be a bool, not an int or other type"
        )

    def test_audit_map_worker_enabled_can_be_set_to_true(self) -> None:
        """AC7: passing audit_map_worker_enabled=True produces a settings object with True."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(audit_map_worker_enabled=True)
        assert settings.audit_map_worker_enabled is True

    def test_audit_map_worker_enabled_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC7: OWLBEAR_AUDIT_MAP_WORKER_ENABLED env-var overrides the default to True."""
        import importlib

        monkeypatch.setenv("OWLBEAR_AUDIT_MAP_WORKER_ENABLED", "true")
        import owlbear.config as _cfg_mod

        # Force a fresh settings construction so the env-var is picked up.
        fresh = _cfg_mod.OwlBearSettings()
        assert fresh.audit_map_worker_enabled is True, (
            "OWLBEAR_AUDIT_MAP_WORKER_ENABLED=true must set audit_map_worker_enabled to True"
        )
        importlib.invalidate_caches()


# ---------------------------------------------------------------------------
# AC8: _wire_post_model_hooks() with channel parameter (#983)
# ---------------------------------------------------------------------------


class TestFromAC_983_AuditMapWiringInBootstrap:
    """AC8: _wire_post_model_hooks() wires AuditMapAdvisoryHook behind config flag,
    accepts a channel= parameter, and threads it to the hook.

    All tests FAIL (RED) until _wire_post_model_hooks accepts channel= and
    wires AuditMapAdvisoryHook when audit_map_worker_enabled=True.
    """

    def test_wire_post_model_hooks_accepts_channel_kwarg(self, tmp_path: Path) -> None:
        """AC8: _wire_post_model_hooks does not raise TypeError when called with channel=None."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookRegistry

        hooks = HookRegistry()
        settings = OwlBearSettings()

        # Must not raise TypeError for unexpected keyword argument 'channel'
        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),  # ingest_pipeline
            channel=None,
        )

    def test_audit_map_hook_registered_when_flag_enabled_and_ingest_available(
        self, tmp_path: Path
    ) -> None:
        """AC8: AuditMapAdvisoryHook registered for TASK_COMPLETE when flag=True and ingest set."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.config import OwlBearSettings
        from owlbear.core.audit_map_hook import AuditMapAdvisoryHook
        from owlbear.core.hooks import HookEvent, HookRegistry

        hooks = HookRegistry()
        settings = OwlBearSettings(audit_map_worker_enabled=True)

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),  # ingest_pipeline available
            channel=None,
        )

        handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        audit_handlers = [h for h in handlers if isinstance(h, AuditMapAdvisoryHook)]
        assert len(audit_handlers) == 1, (
            f"Exactly one AuditMapAdvisoryHook must be registered, found {len(audit_handlers)}"
        )

    def test_audit_map_hook_not_registered_when_flag_disabled(self, tmp_path: Path) -> None:
        """AC8: AuditMapAdvisoryHook is NOT registered when audit_map_worker_enabled=False."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.config import OwlBearSettings
        from owlbear.core.audit_map_hook import AuditMapAdvisoryHook
        from owlbear.core.hooks import HookEvent, HookRegistry

        hooks = HookRegistry()
        settings = OwlBearSettings(audit_map_worker_enabled=False)

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),  # ingest_pipeline present but flag off
            channel=None,
        )

        handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        audit_handlers = [h for h in handlers if isinstance(h, AuditMapAdvisoryHook)]
        assert len(audit_handlers) == 0, (
            "AuditMapAdvisoryHook must NOT be registered when audit_map_worker_enabled=False"
        )

    def test_audit_map_hook_not_registered_when_ingest_pipeline_none(
        self, tmp_path: Path
    ) -> None:
        """AC8: AuditMapAdvisoryHook is NOT registered when ingest_pipeline is None."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.config import OwlBearSettings
        from owlbear.core.audit_map_hook import AuditMapAdvisoryHook
        from owlbear.core.hooks import HookEvent, HookRegistry

        hooks = HookRegistry()
        settings = OwlBearSettings(audit_map_worker_enabled=True)

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            None,  # ingest_pipeline unavailable
            channel=None,
        )

        handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        audit_handlers = [h for h in handlers if isinstance(h, AuditMapAdvisoryHook)]
        assert len(audit_handlers) == 0, (
            "AuditMapAdvisoryHook must NOT be registered when ingest_pipeline is None"
        )

    def test_audit_map_hook_receives_channel_when_provided(self, tmp_path: Path) -> None:
        """AC8: channel passed to _wire_post_model_hooks is threaded to AuditMapAdvisoryHook."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.channels.base import ChannelPlugin
        from owlbear.config import OwlBearSettings
        from owlbear.core.audit_map_hook import AuditMapAdvisoryHook
        from owlbear.core.hooks import HookEvent, HookRegistry

        hooks = HookRegistry()
        settings = OwlBearSettings(audit_map_worker_enabled=True)
        channel = MagicMock(spec=ChannelPlugin)

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),
            channel=channel,
        )

        handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        audit_hook = next((h for h in handlers if isinstance(h, AuditMapAdvisoryHook)), None)
        assert audit_hook is not None, "AuditMapAdvisoryHook must be registered"
        assert audit_hook._channel is channel, (
            "channel passed to _wire_post_model_hooks must reach the AuditMapAdvisoryHook"
        )

    def test_audit_map_hook_channel_is_none_when_channel_none_passed(
        self, tmp_path: Path
    ) -> None:
        """AC8: AuditMapAdvisoryHook._channel is None when channel=None is forwarded."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.config import OwlBearSettings
        from owlbear.core.audit_map_hook import AuditMapAdvisoryHook
        from owlbear.core.hooks import HookEvent, HookRegistry

        hooks = HookRegistry()
        settings = OwlBearSettings(audit_map_worker_enabled=True)

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),
            channel=None,
        )

        handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        audit_hook = next((h for h in handlers if isinstance(h, AuditMapAdvisoryHook)), None)
        assert audit_hook is not None, "AuditMapAdvisoryHook must be registered"
        assert audit_hook._channel is None, (
            "AuditMapAdvisoryHook._channel must be None when channel=None is passed"
        )

    def test_audit_map_hook_shares_supervisor_with_retrospective_hook(
        self, tmp_path: Path
    ) -> None:
        """AC8: AuditMapAdvisoryHook shares the same HookWorkerSupervisor as RetrospectiveHook."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.config import OwlBearSettings
        from owlbear.core.audit_map_hook import AuditMapAdvisoryHook
        from owlbear.core.hooks import HookEvent, HookRegistry
        from owlbear.core.retrospective_hook import RetrospectiveHook

        hooks = HookRegistry()
        settings = OwlBearSettings(audit_map_worker_enabled=True)

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),
            channel=None,
        )

        handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        retro_hook = next((h for h in handlers if isinstance(h, RetrospectiveHook)), None)
        audit_hook = next((h for h in handlers if isinstance(h, AuditMapAdvisoryHook)), None)

        assert retro_hook is not None, "RetrospectiveHook must be registered for TASK_COMPLETE"
        assert audit_hook is not None, "AuditMapAdvisoryHook must be registered for TASK_COMPLETE"
        assert audit_hook._supervisor is retro_hook._supervisor, (
            "AuditMapAdvisoryHook and RetrospectiveHook must share the same HookWorkerSupervisor"
        )
