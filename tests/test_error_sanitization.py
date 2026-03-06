"""Tests for error_to_user_message() — sanitize exceptions for user-facing channels.

TDD RED phase: function doesn't exist yet; all tests should fail on import or stub.
Target: 100% branch coverage on error_to_user_message().
"""

from __future__ import annotations

import httpx
import openai
import pydantic

from owlbear.core.errors import error_to_user_message

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_status_error(status_code: int, url: str = "https://x") -> httpx.HTTPStatusError:
    """Build an ``httpx.HTTPStatusError`` with the given status code and URL."""
    response = httpx.Response(status_code, request=httpx.Request("GET", url))
    return httpx.HTTPStatusError("err", request=response.request, response=response)


class _DummyModel(pydantic.BaseModel):
    name: str


# ---------------------------------------------------------------------------
# Known exception types → safe canned messages
# ---------------------------------------------------------------------------


class TestKnownExceptions:
    """Known httpx/openai/pydantic exceptions produce safe canned messages."""

    def test_http_status_error_contains_status_code(self) -> None:
        exc = _http_status_error(401, url="https://api.example.com?token=ghp_secret")
        result = error_to_user_message(exc)
        assert "401" in result

    def test_http_status_error_no_url_leak(self) -> None:
        exc = _http_status_error(401, url="https://api.example.com?token=ghp_secret")
        result = error_to_user_message(exc)
        assert "api.example.com" not in result
        assert "ghp_secret" not in result

    def test_connect_error_safe_message(self) -> None:
        exc = httpx.ConnectError("Failed to connect to api.copilot.githubcopilot.com:443")
        result = error_to_user_message(exc)
        assert result == "Connection failed"

    def test_connect_error_no_hostname(self) -> None:
        exc = httpx.ConnectError("Failed to connect to api.copilot.githubcopilot.com:443")
        result = error_to_user_message(exc)
        assert "copilot" not in result.lower()

    def test_timeout_safe_message(self) -> None:
        exc = httpx.ReadTimeout("Timed out reading https://api.example.com/v1/chat/completions")
        result = error_to_user_message(exc)
        assert result == "Request timed out"

    def test_timeout_no_url(self) -> None:
        exc = httpx.ReadTimeout("Timed out reading https://api.example.com/v1/chat/completions")
        result = error_to_user_message(exc)
        assert "api.example.com" not in result

    def test_openai_auth_error(self) -> None:
        exc = openai.AuthenticationError(
            message="Invalid API key",
            body=None,
            response=httpx.Response(401, request=httpx.Request("POST", "https://x")),
        )
        result = error_to_user_message(exc)
        assert result == "Authentication failed"

    def test_pydantic_validation_error(self) -> None:
        try:
            _DummyModel.model_validate({"name": 123})  # type: ignore[arg-type]
        except pydantic.ValidationError as exc:
            result = error_to_user_message(exc)
        assert result == "Validation error"


# ---------------------------------------------------------------------------
# Unknown exceptions → scrubbed fallback
# ---------------------------------------------------------------------------


class TestScrubPatterns:
    """Unknown exceptions have sensitive patterns scrubbed from their message."""

    def test_url_replaced(self) -> None:
        exc = RuntimeError("Failed at https://api.example.com?token=secret123")
        result = error_to_user_message(exc)
        assert "https://api.example.com" not in result
        assert "[URL]" in result

    def test_bearer_token_replaced(self) -> None:
        exc = RuntimeError("Header: Bearer ghp_abc123XYZ")
        result = error_to_user_message(exc)
        assert "ghp_abc123" not in result
        assert "[REDACTED]" in result

    def test_query_param_secrets_replaced(self) -> None:
        exc = RuntimeError("Request with token=abc123&key=xyz789")
        result = error_to_user_message(exc)
        assert "abc123" not in result
        assert "xyz789" not in result
        assert "token=[REDACTED]" in result
        assert "key=[REDACTED]" in result

    def test_windows_path_replaced(self) -> None:
        exc = RuntimeError(r"Error reading C:\Users\foo\bar.py")
        result = error_to_user_message(exc)
        assert r"C:\Users\foo" not in result
        assert "[PATH]" in result

    def test_unix_path_replaced(self) -> None:
        exc = RuntimeError("Error reading /home/foo/bar.py")
        result = error_to_user_message(exc)
        assert "/home/foo" not in result
        assert "[PATH]" in result


# ---------------------------------------------------------------------------
# Benign / edge cases
# ---------------------------------------------------------------------------


class TestBenignAndEdgeCases:
    """Benign exceptions preserve type name + message. Return type is str."""

    def test_benign_value_error_preserved(self) -> None:
        exc = ValueError("bad input")
        result = error_to_user_message(exc)
        assert result == "ValueError: bad input"

    def test_return_type_is_always_str(self) -> None:
        for exc in (
            httpx.ConnectError("x"),
            RuntimeError("x"),
            ValueError("y"),
        ):
            result = error_to_user_message(exc)
            assert isinstance(result, str)
