"""RED tests for #1008 — auth success/failure audit events.

Tests the SecurityEvent contracts for _login_async() success and failure flows,
audit_log injection, token-leakage prevention, best-effort failure handling,
and CLI output preservation.

All tests expected to FAIL on current HEAD (RED phase) until #848 is implemented.
"""

from __future__ import annotations

import asyncio
import inspect
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bearclaw.commands.auth import _login_async
from owlbear.core.errors import error_to_user_message
from owlbear.safety.audit_log import SecurityAuditLog

# ---------------------------------------------------------------------------
# Test constants — values used in device-flow mocks
# ---------------------------------------------------------------------------

_DEVICE_RESP = {
    "device_code": "dc_test_secret_code",
    "user_code": "WXYZ-9999",
    "verification_uri": "https://github.com/login/device",
    "expires_in": 900,
    "interval": 5,
}
_ACCESS_TOKEN = "ghu_fake_access_token_secret"
_COPILOT_DATA = {"token": "copilot_secret_token_value", "expires_at": 9999999999}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run a coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_audit_log() -> MagicMock:
    """Create a mock SecurityAuditLog for injection testing."""
    log = MagicMock(spec=SecurityAuditLog)
    log.log = MagicMock()
    return log


def _patched_success() -> ExitStack:
    """Return an ExitStack with all device-flow helpers mocked for a successful login."""
    stack = ExitStack()
    stack.enter_context(
        patch(
            "bearclaw.commands.auth.request_device_code",
            new_callable=AsyncMock,
            return_value=_DEVICE_RESP,
        )
    )
    stack.enter_context(
        patch(
            "bearclaw.commands.auth.poll_for_access_token",
            new_callable=AsyncMock,
            return_value=_ACCESS_TOKEN,
        )
    )
    stack.enter_context(
        patch(
            "bearclaw.commands.auth.exchange_for_copilot_token",
            new_callable=AsyncMock,
            return_value=_COPILOT_DATA,
        )
    )
    stack.enter_context(patch("bearclaw.commands.auth.save_token"))
    stack.enter_context(patch("bearclaw.commands.auth.webbrowser"))
    return stack


def _patched_failure(exc: Exception) -> ExitStack:
    """Return an ExitStack where request_device_code raises exc."""
    stack = ExitStack()
    stack.enter_context(
        patch(
            "bearclaw.commands.auth.request_device_code",
            new_callable=AsyncMock,
            side_effect=exc,
        )
    )
    stack.enter_context(patch("bearclaw.commands.auth.webbrowser"))
    return stack


# ---------------------------------------------------------------------------
# TestFromAC_AuthSuccessEvent
# ---------------------------------------------------------------------------


class TestFromAC_AuthSuccessEvent:
    """auth_success SecurityEvent contract — all 7 field values must be exact.

    From #1008 AC1 / #848 AC1: event after save_token() succeeds.
    All tests fail RED because _login_async() does not yet accept audit_log.
    """

    def test_auth_success_event_type(self) -> None:
        """auth_success event must have event_type='auth_success'."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        mock_log.log.assert_called_once()
        _, kwargs = mock_log.log.call_args
        assert kwargs["event_type"] == "auth_success"

    def test_auth_success_severity(self) -> None:
        """auth_success event must have severity='info'."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["severity"] == "info"

    def test_auth_success_actor(self) -> None:
        """auth_success event must have actor='user'."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["actor"] == "user"

    def test_auth_success_session_id_is_empty_string(self) -> None:
        """auth_success event must have session_id='' (no session context at CLI level)."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["session_id"] == ""

    def test_auth_success_tool_name_is_none(self) -> None:
        """auth_success event must have tool_name=None (CLI login is not a tool-call)."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["tool_name"] is None

    def test_auth_success_detail_exact_string(self) -> None:
        """auth_success event must have detail='Copilot device-flow login succeeded'."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["detail"] == "Copilot device-flow login succeeded"

    def test_auth_success_metadata_is_empty_dict(self) -> None:
        """auth_success event must have metadata={}."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["metadata"] == {}

    def test_auth_success_event_emitted_exactly_once(self) -> None:
        """Exactly one audit event is emitted on successful login."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        assert mock_log.log.call_count == 1


# ---------------------------------------------------------------------------
# TestFromAC_AuthFailureEvent
# ---------------------------------------------------------------------------


class TestFromAC_AuthFailureEvent:
    """auth_failure SecurityEvent contract — all field values on login exception.

    From #1008 AC1 / #848 AC2: event on login flow exception before propagation.
    All tests fail RED because _login_async() does not yet accept audit_log.
    """

    def test_auth_failure_event_type(self) -> None:
        """auth_failure event must have event_type='auth_failure'."""
        mock_log = _make_audit_log()
        exc = RuntimeError("network timeout")
        with _patched_failure(exc), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        mock_log.log.assert_called_once()
        _, kwargs = mock_log.log.call_args
        assert kwargs["event_type"] == "auth_failure"

    def test_auth_failure_severity(self) -> None:
        """auth_failure event must have severity='warning'."""
        mock_log = _make_audit_log()
        exc = RuntimeError("network timeout")
        with _patched_failure(exc), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["severity"] == "warning"

    def test_auth_failure_actor(self) -> None:
        """auth_failure event must have actor='user'."""
        mock_log = _make_audit_log()
        exc = RuntimeError("network timeout")
        with _patched_failure(exc), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["actor"] == "user"

    def test_auth_failure_detail_equals_error_to_user_message(self) -> None:
        """auth_failure detail must equal error_to_user_message(exc)."""
        mock_log = _make_audit_log()
        exc = RuntimeError("something went wrong")
        with _patched_failure(exc), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["detail"] == error_to_user_message(exc)

    def test_auth_failure_metadata_is_empty_dict(self) -> None:
        """auth_failure event must have metadata={}."""
        mock_log = _make_audit_log()
        exc = RuntimeError("fail")
        with _patched_failure(exc), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert kwargs["metadata"] == {}

    def test_auth_failure_original_exception_propagates(self) -> None:
        """The original exception must propagate unchanged after the audit event is logged."""
        mock_log = _make_audit_log()
        exc = ValueError("token_expired_sentinel")
        with _patched_failure(exc), pytest.raises(ValueError, match="token_expired_sentinel"):
            _run(_login_async(audit_log=mock_log))

    def test_auth_failure_event_emitted_exactly_once(self) -> None:
        """Exactly one audit event is emitted on login failure."""
        mock_log = _make_audit_log()
        with _patched_failure(RuntimeError("fail")), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        assert mock_log.log.call_count == 1


# ---------------------------------------------------------------------------
# TestFromAC_TokenLeakagePrevention
# ---------------------------------------------------------------------------


class TestFromAC_TokenLeakagePrevention:
    """Neither auth_success nor auth_failure events leak token secrets.

    From #1008 AC2 / #848 AC3: access_token, copilot_token, device_code,
    user_code must not appear in detail or metadata.
    All tests fail RED because _login_async() does not yet accept audit_log.
    """

    _FORBIDDEN_KEYS = ("access_token", "copilot_token", "device_code", "user_code")

    def test_success_detail_excludes_raw_access_token_value(self) -> None:
        """auth_success detail must not contain the raw access token value."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert _ACCESS_TOKEN not in kwargs["detail"]

    def test_success_detail_excludes_raw_device_code_value(self) -> None:
        """auth_success detail must not contain the raw device_code value."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert "dc_test_secret_code" not in kwargs["detail"]

    def test_success_detail_excludes_raw_user_code_value(self) -> None:
        """auth_success detail must not contain the raw user_code value."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        assert "WXYZ-9999" not in kwargs["detail"]

    def test_success_metadata_excludes_all_forbidden_keys(self) -> None:
        """auth_success metadata must not contain any forbidden token key."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        for key in self._FORBIDDEN_KEYS:
            assert key not in kwargs["metadata"], f"Forbidden key '{key}' in metadata"

    def test_success_metadata_excludes_token_values(self) -> None:
        """auth_success metadata must not contain any raw token value."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        metadata_str = str(kwargs["metadata"])
        for secret in (_ACCESS_TOKEN, "copilot_secret_token_value", "dc_test_secret_code"):
            assert secret not in metadata_str, f"Secret value leaked into metadata: {secret!r}"

    def test_failure_detail_excludes_forbidden_key_strings(self) -> None:
        """auth_failure detail must not contain the literal strings 'access_token' etc."""
        mock_log = _make_audit_log()
        exc = RuntimeError("Login failed")
        with _patched_failure(exc), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        for key in self._FORBIDDEN_KEYS:
            assert key not in kwargs["detail"], f"Forbidden key '{key}' found in detail"

    def test_failure_metadata_excludes_all_forbidden_keys(self) -> None:
        """auth_failure metadata must not contain any forbidden token key."""
        mock_log = _make_audit_log()
        exc = RuntimeError("Login failed")
        with _patched_failure(exc), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        _, kwargs = mock_log.log.call_args
        for key in self._FORBIDDEN_KEYS:
            assert key not in kwargs["metadata"], f"Forbidden key '{key}' found in metadata"


# ---------------------------------------------------------------------------
# TestFromAC_AuditLogInjection
# ---------------------------------------------------------------------------


class TestFromAC_AuditLogInjection:
    """_login_async() accepts audit_log for test injection.

    From #1008 AC3 / #848 AC5.
    Tests fail RED because _login_async() does not yet have this parameter.
    """

    def test_login_async_accepts_audit_log_kwarg_without_type_error(self) -> None:
        """_login_async(audit_log=...) must not raise TypeError."""
        mock_log = _make_audit_log()
        with _patched_success():
            # Fails RED: TypeError: _login_async() got an unexpected keyword argument
            _run(_login_async(audit_log=mock_log))

    def test_login_async_signature_has_audit_log_parameter(self) -> None:
        """_login_async function signature must declare an 'audit_log' parameter."""
        sig = inspect.signature(_login_async)
        assert "audit_log" in sig.parameters, (
            "_login_async() must have an 'audit_log' parameter for test injection"
        )

    def test_login_async_uses_injected_audit_log_not_a_new_instance(self) -> None:
        """The injected audit_log is the one that receives log() calls (not a new instance)."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        assert mock_log.log.called, "Injected audit_log.log() must be called"

    def test_login_async_accepts_none_as_audit_log(self) -> None:
        """Passing audit_log=None should be accepted (default — no injection)."""
        with _patched_success():
            # Fails RED: TypeError — _login_async() does not yet accept audit_log
            _run(_login_async(audit_log=None))


# ---------------------------------------------------------------------------
# TestFromAC_BestEffortAuditWrite
# ---------------------------------------------------------------------------


class TestFromAC_BestEffortAuditWrite:
    """Audit-log write failures are swallowed and never affect login outcome.

    From #1008 AC4 / #848 AC7.
    All tests fail RED because _login_async() does not yet accept audit_log.
    """

    def test_audit_log_error_on_success_does_not_raise(self) -> None:
        """Login succeeds even when audit_log.log() raises an OSError."""
        mock_log = _make_audit_log()
        mock_log.log.side_effect = OSError("disk full")
        with _patched_success():
            # Must NOT raise — best-effort only
            _run(_login_async(audit_log=mock_log))

    def test_audit_log_error_does_not_mask_original_login_error(self) -> None:
        """When login fails AND audit_log.log() also fails, original login error propagates."""
        mock_log = _make_audit_log()
        mock_log.log.side_effect = OSError("disk full")
        exc = RuntimeError("poll_timeout_sentinel")
        with _patched_failure(exc), pytest.raises(RuntimeError, match="poll_timeout_sentinel"):
            _run(_login_async(audit_log=mock_log))

    def test_audit_log_log_is_called_on_failure_before_propagation(self) -> None:
        """audit_log.log() is invoked for auth_failure even when the exception propagates."""
        call_order: list[str] = []
        mock_log = _make_audit_log()
        mock_log.log.side_effect = lambda **_kw: call_order.append("audit")
        exc = RuntimeError("fail")
        with _patched_failure(exc), pytest.raises(RuntimeError):
            _run(_login_async(audit_log=mock_log))
        assert "audit" in call_order, "audit_log.log() must be called for auth_failure events"


# ---------------------------------------------------------------------------
# TestFromAC_CLIBehaviorPreserved
# ---------------------------------------------------------------------------


class TestFromAC_CLIBehaviorPreserved:
    """Existing CLI output and webbrowser behavior unchanged when audit_log injected.

    From #1008 AC5 / #848 AC4.
    All tests fail RED because _login_async() does not yet accept audit_log.
    """

    def test_browser_opened_with_verification_uri(self) -> None:
        """webbrowser.open() is still called with the verification_uri when audit_log injected."""
        mock_log = _make_audit_log()
        with (
            patch(
                "bearclaw.commands.auth.request_device_code",
                new_callable=AsyncMock,
                return_value=_DEVICE_RESP,
            ),
            patch(
                "bearclaw.commands.auth.poll_for_access_token",
                new_callable=AsyncMock,
                return_value=_ACCESS_TOKEN,
            ),
            patch(
                "bearclaw.commands.auth.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value=_COPILOT_DATA,
            ),
            patch("bearclaw.commands.auth.save_token"),
            patch("bearclaw.commands.auth.webbrowser") as mock_wb,
        ):
            _run(_login_async(audit_log=mock_log))
        mock_wb.open.assert_called_once_with("https://github.com/login/device")

    def test_save_token_called_with_copilot_data(self) -> None:
        """save_token() still called with the copilot token data when audit_log injected."""
        mock_log = _make_audit_log()
        with (
            patch(
                "bearclaw.commands.auth.request_device_code",
                new_callable=AsyncMock,
                return_value=_DEVICE_RESP,
            ),
            patch(
                "bearclaw.commands.auth.poll_for_access_token",
                new_callable=AsyncMock,
                return_value=_ACCESS_TOKEN,
            ),
            patch(
                "bearclaw.commands.auth.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value=_COPILOT_DATA,
            ),
            patch("bearclaw.commands.auth.save_token") as mock_save,
            patch("bearclaw.commands.auth.webbrowser"),
        ):
            _run(_login_async(audit_log=mock_log))
        mock_save.assert_called_once_with(_COPILOT_DATA)

    def test_user_code_echoed_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """typer.echo output preserved: user code still printed when audit_log injected."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        captured = capsys.readouterr()
        assert "WXYZ-9999" in captured.out

    def test_success_message_echoed_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """typer.echo output preserved: success message still printed when audit_log injected."""
        mock_log = _make_audit_log()
        with _patched_success():
            _run(_login_async(audit_log=mock_log))
        captured = capsys.readouterr()
        assert "authenticated" in captured.out.lower() or "success" in captured.out.lower()
