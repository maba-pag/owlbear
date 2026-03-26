"""Tests for owlbear.core.errors — ErrorCategory enum + classify_error + ToolError."""

from __future__ import annotations

import json
import types
import unittest.mock

import httpx
import openai
import pydantic
import pytest

from owlbear.core.errors import BlockedCommandError, ErrorCategory, ToolError, classify_error

# ---------------------------------------------------------------------------
# ErrorCategory enum
# ---------------------------------------------------------------------------


class TestErrorCategory:
    """ErrorCategory is a StrEnum with exactly 4 members."""

    def test_has_four_members(self) -> None:
        assert len(ErrorCategory) == 4

    def test_members(self) -> None:
        assert set(ErrorCategory) == {
            ErrorCategory.TRANSIENT,
            ErrorCategory.AUTH,
            ErrorCategory.PERMANENT,
            ErrorCategory.TOOL_SEMANTIC,
        }

    def test_is_str(self) -> None:
        for member in ErrorCategory:
            assert isinstance(member, str)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Build an ``httpx.HTTPStatusError`` with the given status code."""
    response = httpx.Response(status_code, request=httpx.Request("GET", "https://x"))
    return httpx.HTTPStatusError("err", request=response.request, response=response)


# ---------------------------------------------------------------------------
# classify_error — TRANSIENT
# ---------------------------------------------------------------------------


class TestTransient:
    """Errors that should be retried with backoff."""

    def test_connect_error(self) -> None:
        exc = httpx.ConnectError("fail")
        assert classify_error(exc) is ErrorCategory.TRANSIENT

    def test_timeout_exception(self) -> None:
        exc = httpx.TimeoutException("timeout")
        assert classify_error(exc) is ErrorCategory.TRANSIENT

    def test_http_429(self) -> None:
        assert classify_error(_http_status_error(429)) is ErrorCategory.TRANSIENT

    def test_http_502(self) -> None:
        assert classify_error(_http_status_error(502)) is ErrorCategory.TRANSIENT

    def test_http_503(self) -> None:
        assert classify_error(_http_status_error(503)) is ErrorCategory.TRANSIENT

    def test_http_504(self) -> None:
        assert classify_error(_http_status_error(504)) is ErrorCategory.TRANSIENT

    def test_builtin_timeout_error(self) -> None:
        assert classify_error(TimeoutError("t")) is ErrorCategory.TRANSIENT

    def test_builtin_connection_error(self) -> None:
        assert classify_error(ConnectionError("c")) is ErrorCategory.TRANSIENT


# ---------------------------------------------------------------------------
# classify_error — AUTH
# ---------------------------------------------------------------------------


class TestAuth:
    """Errors requiring token refresh."""

    def test_http_401(self) -> None:
        assert classify_error(_http_status_error(401)) is ErrorCategory.AUTH

    def test_http_403(self) -> None:
        assert classify_error(_http_status_error(403)) is ErrorCategory.AUTH

    def test_openai_authentication_error(self) -> None:
        exc = openai.AuthenticationError(
            message="bad key",
            response=httpx.Response(401, request=httpx.Request("POST", "https://x")),
            body=None,
        )
        assert classify_error(exc) is ErrorCategory.AUTH

    def test_openai_permission_denied_error(self) -> None:
        exc = openai.PermissionDeniedError(
            message="denied",
            response=httpx.Response(403, request=httpx.Request("POST", "https://x")),
            body=None,
        )
        assert classify_error(exc) is ErrorCategory.AUTH


# ---------------------------------------------------------------------------
# classify_error — PERMANENT
# ---------------------------------------------------------------------------


class TestPermanent:
    """Non-retryable errors."""

    def test_file_not_found(self) -> None:
        assert classify_error(FileNotFoundError("x")) is ErrorCategory.PERMANENT

    def test_permission_error(self) -> None:
        assert classify_error(PermissionError("x")) is ErrorCategory.PERMANENT

    def test_blocked_command_error(self) -> None:
        exc = BlockedCommandError("rm -rf /", r"rm\s+-rf\s+/")
        assert classify_error(exc) is ErrorCategory.PERMANENT

    def test_pydantic_validation_error(self) -> None:
        class _M(pydantic.BaseModel):
            x: int

        with pytest.raises(pydantic.ValidationError) as exc_info:
            _M.model_validate({"x": "not_int"})
        assert classify_error(exc_info.value) is ErrorCategory.PERMANENT

    def test_unknown_defaults_to_permanent(self) -> None:
        assert classify_error(RuntimeError("unknown")) is ErrorCategory.PERMANENT

    def test_custom_exception_defaults_to_permanent(self) -> None:
        class _CustomError(Exception): ...

        assert classify_error(_CustomError()) is ErrorCategory.PERMANENT


# ---------------------------------------------------------------------------
# classify_error — TOOL_SEMANTIC
# ---------------------------------------------------------------------------


class TestToolSemantic:
    """Errors the model can self-correct."""

    def test_value_error(self) -> None:
        assert classify_error(ValueError("bad")) is ErrorCategory.TOOL_SEMANTIC

    def test_key_error(self) -> None:
        assert classify_error(KeyError("k")) is ErrorCategory.TOOL_SEMANTIC

    def test_type_error(self) -> None:
        assert classify_error(TypeError("t")) is ErrorCategory.TOOL_SEMANTIC


# ---------------------------------------------------------------------------
# Purity — no side effects
# ---------------------------------------------------------------------------


class TestPurity:
    """classify_error is a pure function."""

    def test_returns_same_result_for_same_input(self) -> None:
        exc = httpx.ConnectError("fail")
        assert classify_error(exc) is classify_error(exc)

    def test_no_mutation_of_exception(self) -> None:
        exc = ValueError("x")
        original_args = exc.args
        classify_error(exc)
        assert exc.args is original_args


# ---------------------------------------------------------------------------
# ToolError — frozen dataclass
# ---------------------------------------------------------------------------


class TestToolErrorFields:
    """ToolError has 4 fields: status, error_type, tool_name, message."""

    def test_status_always_error(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.PERMANENT,
            tool_name="delegate_to_agent",
            message="something broke",
        )
        assert err.status == "error"

    def test_error_type_is_error_category(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.TRANSIENT,
            tool_name="run_command",
            message="timeout",
        )
        assert err.error_type is ErrorCategory.TRANSIENT

    def test_tool_name(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.PERMANENT,
            tool_name="delegate_to_agent",
            message="x",
        )
        assert err.tool_name == "delegate_to_agent"

    def test_message(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.TOOL_SEMANTIC,
            tool_name="run_command",
            message="bad input",
        )
        assert err.message == "bad input"

    def test_frozen(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.PERMANENT,
            tool_name="x",
            message="y",
        )
        with pytest.raises(AttributeError):
            err.message = "changed"  # type: ignore[misc]


class TestToolErrorToDict:
    """ToolError.to_dict() returns a JSON-serializable dict."""

    def test_returns_dict_with_four_keys(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.PERMANENT,
            tool_name="delegate_to_agent",
            message="agent_registry not configured",
        )
        d = err.to_dict()
        assert set(d.keys()) == {"status", "error_type", "tool_name", "message"}

    def test_status_key(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.PERMANENT,
            tool_name="x",
            message="y",
        )
        assert err.to_dict()["status"] == "error"

    def test_error_type_is_string_value(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.TRANSIENT,
            tool_name="x",
            message="y",
        )
        assert err.to_dict()["error_type"] == "transient"

    def test_tool_name_value(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.PERMANENT,
            tool_name="delegate_to_agent",
            message="y",
        )
        assert err.to_dict()["tool_name"] == "delegate_to_agent"

    def test_message_value(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.TOOL_SEMANTIC,
            tool_name="x",
            message="agent not found: builder",
        )
        assert err.to_dict()["message"] == "agent not found: builder"

    def test_json_serializable(self) -> None:
        err = ToolError(
            error_type=ErrorCategory.AUTH,
            tool_name="delegate_to_agent",
            message="token expired",
        )
        raw = json.dumps(err.to_dict())
        parsed = json.loads(raw)
        assert parsed["error_type"] == "auth"
        assert parsed["tool_name"] == "delegate_to_agent"
        assert parsed["message"] == "token expired"

    def test_roundtrip_all_categories(self) -> None:
        for cat in ErrorCategory:
            err = ToolError(error_type=cat, tool_name="t", message="m")
            parsed = json.loads(json.dumps(err.to_dict()))
            assert parsed["error_type"] == cat.value


# ---------------------------------------------------------------------------
# classify_error / error_to_user_message — openai NOT importable
# ---------------------------------------------------------------------------


class TestClassifyErrorWithoutOpenai:
    """When openai is not installed, errors.py loads and degrades gracefully."""

    def _reload_without_openai(self) -> types.ModuleType:
        """Reload ``owlbear.core.errors`` with openai missing from sys.modules."""
        import importlib
        import sys

        import owlbear.core.errors as mod

        with unittest.mock.patch.dict(sys.modules, {"openai": None}):
            importlib.reload(mod)
        return mod

    def teardown_method(self) -> None:
        """Restore errors module to normal (with openai available)."""
        import importlib

        import owlbear.core.errors as mod

        importlib.reload(mod)

    def test_import_succeeds(self) -> None:
        mod = self._reload_without_openai()
        assert hasattr(mod, "classify_error")

    def test_classify_runtime_error_returns_permanent(self) -> None:
        mod = self._reload_without_openai()
        assert mod.classify_error(RuntimeError("x")) is mod.ErrorCategory.PERMANENT

    def test_classify_connect_error_returns_transient(self) -> None:
        mod = self._reload_without_openai()
        assert mod.classify_error(httpx.ConnectError("x")) is mod.ErrorCategory.TRANSIENT

    def test_classify_value_error_returns_tool_semantic(self) -> None:
        mod = self._reload_without_openai()
        assert mod.classify_error(ValueError("x")) is mod.ErrorCategory.TOOL_SEMANTIC

    def test_error_to_user_message_unknown_type(self) -> None:
        mod = self._reload_without_openai()
        result = mod.error_to_user_message(RuntimeError("boom"))
        assert isinstance(result, str)
        assert "RuntimeError" in result

    def test_error_to_user_message_httpx_connect(self) -> None:
        mod = self._reload_without_openai()
        result = mod.error_to_user_message(httpx.ConnectError("fail"))
        assert result == "Connection failed"


# ---------------------------------------------------------------------------
# ACP RequestError → ErrorCategory contract (task #71)
# ---------------------------------------------------------------------------

try:
    from acp.exceptions import RequestError as AcpRequestError

    _ACP_AVAILABLE = True
except ImportError:
    AcpRequestError = None  # type: ignore[assignment,misc]
    _ACP_AVAILABLE = False


@pytest.mark.skipif(not _ACP_AVAILABLE, reason="acp package not installed")
class TestFromAC_AcpErrors:
    """ACP RequestError → ErrorCategory contract.

    Tests the classify_error contract for ACP RequestError error codes.

    RED state at time of writing (task #71): tests for TRANSIENT (-32603),
    AUTH (-32000), TOOL_SEMANTIC (-32002), and graceful-degradation will FAIL
    because classify_error has no ACP branch yet.  PERMANENT tests pass by
    coincidence (the default fallback is PERMANENT).
    """

    def test_parse_error_is_permanent(self) -> None:
        """RequestError(-32700) → PERMANENT: malformed JSON is an SDK/process bug."""
        exc = AcpRequestError(-32700, "Parse error")
        assert classify_error(exc) == ErrorCategory.PERMANENT

    def test_invalid_request_is_permanent(self) -> None:
        """RequestError(-32600) → PERMANENT: invalid RPC structure is an SDK bug."""
        exc = AcpRequestError(-32600, "Invalid Request")
        assert classify_error(exc) == ErrorCategory.PERMANENT

    def test_method_not_found_is_permanent(self) -> None:
        """RequestError(-32601) → PERMANENT: wrong method name is a code bug."""
        exc = AcpRequestError(-32601, "Method not found")
        assert classify_error(exc) == ErrorCategory.PERMANENT

    def test_invalid_params_is_permanent(self) -> None:
        """RequestError(-32602) → PERMANENT: wrong params is a code bug."""
        exc = AcpRequestError(-32602, "Invalid params")
        assert classify_error(exc) == ErrorCategory.PERMANENT

    def test_internal_error_is_transient(self) -> None:
        """RequestError(-32603) → TRANSIENT: agent internal failure may recover."""
        exc = AcpRequestError(-32603, "Internal error")
        assert classify_error(exc) == ErrorCategory.TRANSIENT

    def test_auth_required_is_auth(self) -> None:
        """RequestError(-32000) → AUTH: Copilot CLI needs re-authentication."""
        exc = AcpRequestError(-32000, "Auth required")
        assert classify_error(exc) == ErrorCategory.AUTH

    def test_resource_not_found_is_tool_semantic(self) -> None:
        """RequestError(-32002) → TOOL_SEMANTIC: stale session/resource, model can retry."""
        exc = AcpRequestError(-32002, "Resource not found")
        assert classify_error(exc) == ErrorCategory.TOOL_SEMANTIC

    def test_unknown_code_is_permanent(self) -> None:
        """RequestError with an unknown code → PERMANENT (safe default for undefined codes)."""
        exc = AcpRequestError(-32099, "Unknown error code")
        assert classify_error(exc) == ErrorCategory.PERMANENT

    def test_broken_pipe_is_transient(self) -> None:
        """BrokenPipeError → TRANSIENT via ConnectionError inheritance (existing behavior)."""
        exc = BrokenPipeError("Connection reset by peer")
        assert classify_error(exc) == ErrorCategory.TRANSIENT

    def test_acp_not_installed_graceful_degradation(self) -> None:
        """When AcpRequestError is None in the module, the isinstance branch is skipped."""
        exc = AcpRequestError(-32603, "Internal error")
        with unittest.mock.patch("owlbear.core.errors.AcpRequestError", None):
            result = classify_error(exc)
        # Without the ACP branch, RequestError falls through to default PERMANENT
        assert result == ErrorCategory.PERMANENT
