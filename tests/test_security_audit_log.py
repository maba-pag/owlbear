"""RED tests for #847 — workspace-scoped security audit log (guard/gate/terminal).

Tests the contract defined in #525 AC before implementation exists.
All tests are expected to fail until owlbear.safety.audit_log is implemented
and audit_sink parameters are added to CommandSafetyGuard, ApprovalGateToolset,
and TerminalToolset.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# This import drives the RED phase — module does not exist yet.
from owlbear.safety.audit_log import SecurityAuditLog, SecurityEvent

# These modules exist; tests verify NEW audit_sink parameter support.
from owlbear.core.command_guard import BlockedCommandError, CommandSafetyGuard
from owlbear.core.hooks import HookRegistry
from owlbear.safety.gate import ApprovalGateToolset
from owlbear.safety.policy import ApprovalPolicy, ApprovalRule, ApprovalSession
from owlbear.tools.terminal import TerminalToolset

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

_SRC_ROOT = Path(__file__).parent.parent / "src"


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_security_event(**overrides: Any) -> SecurityEvent:
    """Build a minimal SecurityEvent for contract testing."""
    defaults: dict[str, Any] = {
        "timestamp": "2026-03-18T00:00:00Z",
        "event_type": "command_blocked",
        "severity": "high",
        "actor": "agent",
        "session_id": "test-session",
        "tool_name": "run_in_terminal",
        "detail": "Command blocked by pattern",
        "metadata": {},
    }
    defaults.update(overrides)
    return SecurityEvent(**defaults)


def _make_channel(responses: list[str | None] | None = None) -> MagicMock:
    """Create a mock ChannelPlugin with queued receive responses."""
    if responses is None:
        responses = ["yes"]
    ch = MagicMock()
    ch.send = AsyncMock()
    ch.send_blocks = AsyncMock()
    ch.receive = AsyncMock(side_effect=list(responses))
    return ch


def _make_inner() -> MagicMock:
    """Create a mock inner toolset for ApprovalGateToolset wrapping."""
    inner = MagicMock()
    inner.call_tool = AsyncMock(return_value="tool_result")
    return inner


def _blocked_cmd_data(cmd: str) -> dict[str, object]:
    return {"tool_name": "run_in_terminal", "args": {"command": cmd}}


def _blocked_file_data(path: str) -> dict[str, object]:
    return {"tool_name": "create_file", "args": {"path": path}}


# ---------------------------------------------------------------------------
# TestFromAC_SecurityAuditLogStore
# ---------------------------------------------------------------------------


class TestFromAC_SecurityAuditLogStore:
    """SecurityAuditLog writes SecurityEvent records with the exact schema
    and trims to max_entries=500_000."""

    def test_security_event_has_all_required_fields(self) -> None:
        """SecurityEvent has exactly the 8 required schema fields."""
        event = _make_security_event()
        for field_name in (
            "timestamp",
            "event_type",
            "severity",
            "actor",
            "session_id",
            "tool_name",
            "detail",
            "metadata",
        ):
            assert hasattr(event, field_name), f"Missing field: {field_name}"

    def test_security_event_tool_name_is_optional(self) -> None:
        """tool_name may be None for non-tool security events."""
        event = _make_security_event(tool_name=None)
        assert event.tool_name is None

    def test_security_event_metadata_is_dict(self) -> None:
        """metadata field stores arbitrary key/value context."""
        event = _make_security_event(metadata={"pattern": r"rm\s+-rf", "command": "rm -rf /"})
        assert event.metadata == {"pattern": r"rm\s+-rf", "command": "rm -rf /"}

    def test_security_event_severity_field(self) -> None:
        """severity field accepts expected severity-level strings."""
        for level in ("low", "medium", "high", "critical"):
            event = _make_security_event(severity=level)
            assert event.severity == level

    def test_audit_log_persists_to_correct_path(self, tmp_path: Path) -> None:
        """SecurityAuditLog stores events at {workspace}/.owlbear/security_audit.jsonl."""
        store = SecurityAuditLog(tmp_path)
        expected = tmp_path / ".owlbear" / "security_audit.jsonl"
        assert store.path == expected

    def test_audit_log_default_max_entries_is_500000(self, tmp_path: Path) -> None:
        """Default max_entries is exactly 500_000."""
        store = SecurityAuditLog(tmp_path)
        assert store.max_entries == 500_000

    def test_audit_log_empty_store_returns_empty_list(self, tmp_path: Path) -> None:
        """load() returns [] when no events have been logged."""
        store = SecurityAuditLog(tmp_path)
        assert store.load() == []

    def test_audit_log_log_method_appends_event(self, tmp_path: Path) -> None:
        """log() writes an event readable by load()."""
        store = SecurityAuditLog(tmp_path)
        store.log(
            event_type="command_blocked",
            severity="high",
            actor="agent",
            session_id="s1",
            tool_name="run_in_terminal",
            detail="blocked rm -rf /",
            metadata={"pattern": r"rm\s+-rf"},
        )
        records = store.load()
        assert len(records) == 1
        assert records[0].event_type == "command_blocked"

    def test_audit_log_preserves_all_schema_fields(self, tmp_path: Path) -> None:
        """Round-trip via log()/load() preserves all 8 schema fields."""
        store = SecurityAuditLog(tmp_path)
        store.log(
            event_type="approval_denied",
            severity="medium",
            actor="user",
            session_id="sess-42",
            tool_name="git_push",
            detail="user denied",
            metadata={"response": "no"},
        )
        event = store.load()[0]
        assert event.event_type == "approval_denied"
        assert event.severity == "medium"
        assert event.actor == "user"
        assert event.session_id == "sess-42"
        assert event.tool_name == "git_push"
        assert event.detail == "user denied"
        assert event.metadata == {"response": "no"}
        # timestamp is auto-generated, must be a non-empty string
        assert isinstance(event.timestamp, str)
        assert event.timestamp

    def test_audit_log_trims_to_max_entries_on_overflow(self, tmp_path: Path) -> None:
        """When entry count exceeds max_entries, only the newest max_entries remain."""
        store = SecurityAuditLog(tmp_path, max_entries=5)
        for i in range(8):
            store.log(
                event_type="command_blocked",
                severity="low",
                actor="agent",
                session_id=f"s{i}",
                tool_name=None,
                detail=f"event-{i}",
                metadata={},
            )
        records = store.load()
        assert len(records) == 5
        sessions = [r.session_id for r in records]
        # oldest entries trimmed
        assert "s0" not in sessions
        assert "s1" not in sessions
        assert "s2" not in sessions
        # newest entries retained
        assert "s7" in sessions

    def test_audit_log_custom_max_entries_accepted(self, tmp_path: Path) -> None:
        """Constructor max_entries parameter is respected."""
        store = SecurityAuditLog(tmp_path, max_entries=100)
        assert store.max_entries == 100


# ---------------------------------------------------------------------------
# TestFromAC_CommandBlockedAuditEvent
# ---------------------------------------------------------------------------


class TestFromAC_CommandBlockedAuditEvent:
    """Blocked shell/file actions append command_blocked and preserve the
    existing block outcome."""

    def test_guard_accepts_audit_sink_parameter(self) -> None:
        """CommandSafetyGuard constructor accepts audit_sink keyword argument."""
        sink = MagicMock()
        guard = CommandSafetyGuard(audit_sink=sink)
        assert guard is not None

    def test_blocked_command_calls_audit_sink(self) -> None:
        """When a shell command is blocked, audit_sink is called once."""
        sink = MagicMock()
        guard = CommandSafetyGuard(audit_sink=sink)
        with pytest.raises(BlockedCommandError):
            _run(guard(_blocked_cmd_data("rm -rf /")))
        sink.assert_called_once()

    def test_blocked_command_audit_event_type_is_command_blocked(self) -> None:
        """Audit sink receives SecurityEvent with event_type='command_blocked'."""
        sink = MagicMock()
        guard = CommandSafetyGuard(audit_sink=sink)
        with pytest.raises(BlockedCommandError):
            _run(guard(_blocked_cmd_data("rm -rf /")))
        event = sink.call_args[0][0]
        assert event.event_type == "command_blocked"

    def test_blocked_command_preserves_blocked_command_error(self) -> None:
        """BlockedCommandError is still raised when audit_sink is provided."""
        sink = MagicMock()
        guard = CommandSafetyGuard(audit_sink=sink)
        with pytest.raises(BlockedCommandError):
            _run(guard(_blocked_cmd_data("rm -rf /")))

    def test_blocked_file_path_calls_audit_sink(self) -> None:
        """Blocked file path also triggers the audit_sink."""
        sink = MagicMock()
        guard = CommandSafetyGuard(audit_sink=sink)
        with pytest.raises(BlockedCommandError):
            _run(guard(_blocked_file_data(".env")))
        sink.assert_called_once()

    def test_blocked_file_audit_event_type_is_command_blocked(self) -> None:
        """File-path block also emits event_type='command_blocked'."""
        sink = MagicMock()
        guard = CommandSafetyGuard(audit_sink=sink)
        with pytest.raises(BlockedCommandError):
            _run(guard(_blocked_file_data(".env")))
        event = sink.call_args[0][0]
        assert event.event_type == "command_blocked"

    def test_safe_command_does_not_call_audit_sink(self) -> None:
        """Safe, non-blocked commands do not trigger the audit_sink."""
        sink = MagicMock()
        guard = CommandSafetyGuard(audit_sink=sink)
        _run(guard(_blocked_cmd_data("echo hello")))
        sink.assert_not_called()

    def test_no_audit_sink_does_not_change_existing_guard_behaviour(self) -> None:
        """With no audit_sink (default None), guard behaviour is unchanged."""
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            _run(guard(_blocked_cmd_data("rm -rf /")))


# ---------------------------------------------------------------------------
# TestFromAC_ApprovalDecisionAuditEvents
# ---------------------------------------------------------------------------


class TestFromAC_ApprovalDecisionAuditEvents:
    """Approval grant, deny, timeout, and approve-all append the expected
    event types."""

    def _make_gate(
        self,
        *,
        audit_sink: Any = None,
        responses: list[str | None] | None = None,
    ) -> ApprovalGateToolset:
        inner = _make_inner()
        channel = _make_channel(responses or ["yes"])
        return ApprovalGateToolset(
            wrapped=inner,
            policy=ApprovalPolicy(rules=[ApprovalRule(tool_name="git_push")]),
            session=ApprovalSession(),
            channel=channel,
            hooks=HookRegistry(),
            audit_sink=audit_sink,
        )

    def test_gate_accepts_audit_sink_parameter(self) -> None:
        """ApprovalGateToolset accepts audit_sink keyword argument."""
        gate = self._make_gate(audit_sink=MagicMock())
        assert gate is not None

    def test_approved_response_appends_approval_granted(self) -> None:
        """'yes' response causes audit_sink to receive event_type='approval_granted'."""
        sink = MagicMock()
        gate = self._make_gate(audit_sink=sink, responses=["yes"])
        ctx, tool = MagicMock(), MagicMock()
        _run(gate.call_tool("git_push", {}, ctx, tool))
        event_types = [c[0][0].event_type for c in sink.call_args_list]
        assert "approval_granted" in event_types

    def test_denied_response_appends_approval_denied(self) -> None:
        """'no' response causes audit_sink to receive event_type='approval_denied'."""
        sink = MagicMock()
        gate = self._make_gate(audit_sink=sink, responses=["no"])
        ctx, tool = MagicMock(), MagicMock()
        _run(gate.call_tool("git_push", {}, ctx, tool))
        event_types = [c[0][0].event_type for c in sink.call_args_list]
        assert "approval_denied" in event_types

    def test_timeout_response_appends_approval_timeout(self) -> None:
        """None (timeout) causes audit_sink to receive event_type='approval_timeout'."""
        sink = MagicMock()
        gate = self._make_gate(audit_sink=sink, responses=[None])
        ctx, tool = MagicMock(), MagicMock()
        _run(gate.call_tool("git_push", {}, ctx, tool))
        event_types = [c[0][0].event_type for c in sink.call_args_list]
        assert "approval_timeout" in event_types

    def test_approve_all_response_appends_approval_granted_all(self) -> None:
        """'approve all {tool}' causes audit_sink to receive event_type='approval_granted_all'."""
        sink = MagicMock()
        gate = self._make_gate(audit_sink=sink, responses=["approve all git_push"])
        ctx, tool = MagicMock(), MagicMock()
        _run(gate.call_tool("git_push", {}, ctx, tool))
        event_types = [c[0][0].event_type for c in sink.call_args_list]
        assert "approval_granted_all" in event_types

    def test_audit_sink_does_not_change_approved_tool_result(self) -> None:
        """With audit_sink=..., 'yes' response still returns the wrapped tool result."""
        sink = MagicMock()
        gate = self._make_gate(audit_sink=sink, responses=["yes"])
        ctx, tool = MagicMock(), MagicMock()
        result = _run(gate.call_tool("git_push", {}, ctx, tool))
        assert result == "tool_result"

    def test_audit_sink_does_not_change_denied_message(self) -> None:
        """With audit_sink=..., 'no' response still returns a denial message."""
        sink = MagicMock()
        gate = self._make_gate(audit_sink=sink, responses=["no"])
        ctx, tool = MagicMock(), MagicMock()
        result = _run(gate.call_tool("git_push", {}, ctx, tool))
        assert isinstance(result, str)
        assert "denied" in result.lower()

    def test_audit_sink_does_not_change_timeout_message(self) -> None:
        """With audit_sink=..., None (timeout) still returns a cancellation message."""
        sink = MagicMock()
        gate = self._make_gate(audit_sink=sink, responses=[None])
        ctx, tool = MagicMock(), MagicMock()
        result = _run(gate.call_tool("git_push", {}, ctx, tool))
        assert isinstance(result, str)
        assert "timeout" in result.lower() or "cancel" in result.lower()


# ---------------------------------------------------------------------------
# TestFromAC_PathEscapeAuditEvent
# ---------------------------------------------------------------------------


class TestFromAC_PathEscapeAuditEvent:
    """invalid working_dir in TerminalToolset appends path_escape_blocked
    and preserves the existing PermissionError behavior."""

    def test_terminal_accepts_audit_sink_parameter(self, tmp_path: Path) -> None:
        """TerminalToolset constructor accepts audit_sink keyword argument."""
        sink = MagicMock()
        ts = TerminalToolset(workspace_root=tmp_path, audit_sink=sink)
        assert ts is not None

    def test_path_escape_calls_audit_sink(self, tmp_path: Path) -> None:
        """Escaping workspace via working_dir triggers audit_sink exactly once."""
        sink = MagicMock()
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        ts = TerminalToolset(workspace_root=workspace, audit_sink=sink)
        with pytest.raises(PermissionError):
            _run(ts.run_command("echo hi", working_dir="../../outside"))
        sink.assert_called_once()

    def test_path_escape_audit_event_type_is_path_escape_blocked(self, tmp_path: Path) -> None:
        """Audit event from a path escape has event_type='path_escape_blocked'."""
        sink = MagicMock()
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        ts = TerminalToolset(workspace_root=workspace, audit_sink=sink)
        with pytest.raises(PermissionError):
            _run(ts.run_command("echo hi", working_dir="../../outside"))
        event = sink.call_args[0][0]
        assert event.event_type == "path_escape_blocked"

    def test_path_escape_permission_error_still_propagates(self, tmp_path: Path) -> None:
        """PermissionError is preserved after the audit event is recorded."""
        sink = MagicMock()
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        ts = TerminalToolset(workspace_root=workspace, audit_sink=sink)
        with pytest.raises(PermissionError):
            _run(ts.run_command("echo hi", working_dir="../../outside"))

    def test_valid_working_dir_does_not_trigger_audit_sink(self, tmp_path: Path) -> None:
        """A valid working_dir within workspace does not call audit_sink."""
        sink = MagicMock()
        sub = tmp_path / "sub"
        sub.mkdir()
        ts = TerminalToolset(workspace_root=tmp_path, audit_sink=sink)
        _run(ts.run_command("echo hi", working_dir="sub"))
        sink.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_BestEffortAuditLogging
# ---------------------------------------------------------------------------


class TestFromAC_BestEffortAuditLogging:
    """append failure in the audit sink does not change the existing
    block/allow/timeout behavior."""

    @staticmethod
    def _bad_sink(event: Any) -> None:  # noqa: ARG004
        msg = "simulated audit sink failure"
        raise RuntimeError(msg)

    def test_raising_sink_does_not_suppress_blocked_command_error(self) -> None:
        """If audit_sink raises, BlockedCommandError is still raised by the guard."""
        guard = CommandSafetyGuard(audit_sink=self._bad_sink)
        with pytest.raises(BlockedCommandError):
            _run(guard(_blocked_cmd_data("rm -rf /")))

    def test_raising_sink_does_not_change_approved_tool_result(self) -> None:
        """If audit_sink raises on approval_granted, the tool result is still returned."""
        inner = _make_inner()
        channel = _make_channel(["yes"])
        gate = ApprovalGateToolset(
            wrapped=inner,
            policy=ApprovalPolicy(rules=[ApprovalRule(tool_name="git_push")]),
            session=ApprovalSession(),
            channel=channel,
            hooks=HookRegistry(),
            audit_sink=self._bad_sink,
        )
        ctx, tool = MagicMock(), MagicMock()
        result = _run(gate.call_tool("git_push", {}, ctx, tool))
        assert result == "tool_result"

    def test_raising_sink_does_not_change_approval_denied_message(self) -> None:
        """If audit_sink raises on approval_denied, the denial message is still returned."""
        inner = _make_inner()
        channel = _make_channel(["no"])
        gate = ApprovalGateToolset(
            wrapped=inner,
            policy=ApprovalPolicy(rules=[ApprovalRule(tool_name="git_push")]),
            session=ApprovalSession(),
            channel=channel,
            hooks=HookRegistry(),
            audit_sink=self._bad_sink,
        )
        ctx, tool = MagicMock(), MagicMock()
        result = _run(gate.call_tool("git_push", {}, ctx, tool))
        assert "denied" in str(result).lower()

    def test_raising_sink_does_not_change_approval_timeout_message(self) -> None:
        """If audit_sink raises on approval_timeout, the cancellation message is still returned."""
        inner = _make_inner()
        channel = _make_channel([None])
        gate = ApprovalGateToolset(
            wrapped=inner,
            policy=ApprovalPolicy(rules=[ApprovalRule(tool_name="git_push")]),
            session=ApprovalSession(),
            channel=channel,
            hooks=HookRegistry(),
            audit_sink=self._bad_sink,
        )
        ctx, tool = MagicMock(), MagicMock()
        result = _run(gate.call_tool("git_push", {}, ctx, tool))
        assert "timeout" in str(result).lower() or "cancel" in str(result).lower()

    def test_raising_sink_does_not_suppress_path_escape_permission_error(
        self, tmp_path: Path
    ) -> None:
        """If audit_sink raises during path escape logging, PermissionError still propagates."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        ts = TerminalToolset(workspace_root=workspace, audit_sink=self._bad_sink)
        with pytest.raises(PermissionError):
            _run(ts.run_command("echo hi", working_dir="../../outside"))


# ---------------------------------------------------------------------------
# TestFromAC_NoConcreteSafetyImport
# ---------------------------------------------------------------------------


class TestFromAC_NoConcreteSafetyImport:
    """src/owlbear/core/command_guard.py and src/owlbear/tools/terminal.py
    do not import owlbear.safety.audit_log directly."""

    @staticmethod
    def _collect_imports(source_file: Path) -> list[str]:
        """Return all module names imported in *source_file* (via AST)."""
        source = source_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        return imports

    def test_command_guard_does_not_import_audit_log(self) -> None:
        """src/owlbear/core/command_guard.py must not import owlbear.safety.audit_log."""
        filepath = _SRC_ROOT / "owlbear" / "core" / "command_guard.py"
        imports = self._collect_imports(filepath)
        assert "owlbear.safety.audit_log" not in imports, (
            "command_guard.py must not import owlbear.safety.audit_log directly; "
            "use an injected sink or callback."
        )

    def test_terminal_does_not_import_audit_log(self) -> None:
        """src/owlbear/tools/terminal.py must not import owlbear.safety.audit_log."""
        filepath = _SRC_ROOT / "owlbear" / "tools" / "terminal.py"
        imports = self._collect_imports(filepath)
        assert "owlbear.safety.audit_log" not in imports, (
            "terminal.py must not import owlbear.safety.audit_log directly; "
            "use an injected sink or callback."
        )
