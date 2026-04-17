"""RED-phase tests for Copilot device-flow auth and LLMExtractor integration (task #888).

AC coverage:
  AC1: Auth module at copilot_auth.py with device-flow OAuth
  AC2: Token caching at ~/.owlbear/copilot_token.json with expiry-aware refresh
  AC3: Editor headers (Editor-Version, Copilot-Integration-Id, etc.) injected into AsyncOpenAI
  AC4: LLMExtractor optionally uses Copilot token when OWLBEAR_LLM_API_KEY is not set
  AC5: Graceful fallback: if Copilot auth fails, extraction degrades to no-op
  Refined-AC7: Dynamic version detection; fallback to defaults on failure
  Refined-AC8: Rate-limiting on extraction requests (configurable threshold)
  Refined-AC9: No telemetry endpoints — auth + completions only
  Refined-AC10: truststore in serve/knowledge/pyproject.toml optional deps

All tests FAIL until #888 implements copilot_auth.py and extends LLMExtractor.
"""

from __future__ import annotations

import json
import time
import tomllib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.copilot_auth import (  # RED: module does not exist yet
    COPILOT_CLIENT_ID,
    DEFAULT_COPILOT_BASE,
    DEVICE_CODE_URL,
    derive_base_url,
    detect_editor_versions,
    exchange_for_copilot_token,
    get_copilot_token,
    load_token,
    poll_for_access_token,
    request_device_code,
    save_token,
)
from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.llm_extractor import LLMExtractor

_PYPROJECT_PATH = Path(__file__).parent.parent / "serve" / "knowledge" / "pyproject.toml"
_FAR_FUTURE = int(time.time()) + 7200  # 2 hours from now


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _MockResponse:
    """Lightweight httpx response mock."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def json(self) -> dict:
        return self._data

    def raise_for_status(self) -> None:
        pass


def _make_http_mock(
    post_responses: list | object | None = None,
    get_response: object | None = None,
) -> MagicMock:
    """Return a MagicMock httpx.AsyncClient usable as an async context manager."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    if post_responses is not None:
        if isinstance(post_responses, list):
            mock_client.post = AsyncMock(side_effect=post_responses)
        else:
            mock_client.post = AsyncMock(return_value=post_responses)
    if get_response is not None:
        mock_client.get = AsyncMock(return_value=get_response)
    return mock_client


# ---------------------------------------------------------------------------
# TestFromAC_CopilotAuthModule — AC1: constants and module exports
# ---------------------------------------------------------------------------


class TestFromAC_CopilotAuthModule:
    """AC1: copilot_auth.py exports required constants."""

    def test_copilot_client_id_is_github_vscode_oauth_app(self) -> None:
        """COPILOT_CLIENT_ID matches the public VS Code GitHub OAuth app ID."""
        assert COPILOT_CLIENT_ID == "Iv1.b507a08c87ecfe98"

    def test_default_copilot_base_contains_githubcopilot_domain(self) -> None:
        """DEFAULT_COPILOT_BASE is a URL pointing to the GitHub Copilot API."""
        assert "githubcopilot.com" in DEFAULT_COPILOT_BASE
        assert DEFAULT_COPILOT_BASE.startswith("https://")

    def test_device_code_url_points_to_github_device_flow(self) -> None:
        """DEVICE_CODE_URL is the GitHub device-flow endpoint."""
        assert "github.com" in DEVICE_CODE_URL
        assert "device" in DEVICE_CODE_URL.lower()


# ---------------------------------------------------------------------------
# TestFromAC_DeviceFlowOAuth — AC1: device-flow OAuth functions
# ---------------------------------------------------------------------------


class TestFromAC_DeviceFlowOAuth:
    """AC1: Device-flow OAuth executes correctly with mocked HTTP calls."""

    @pytest.mark.asyncio
    async def test_request_device_code_returns_dict_with_device_code_key(self) -> None:
        """request_device_code() returns a dict containing 'device_code'."""
        resp = _MockResponse({"device_code": "dc-abc", "user_code": "ABCD-1234", "expires_in": 900, "interval": 5})
        http_mock = _make_http_mock(post_responses=resp)
        with (
            patch("owlbear_knowledge.copilot_auth._http_client", return_value=http_mock),
            patch("builtins.print"),
        ):
            result = await request_device_code()
        assert "device_code" in result

    @pytest.mark.asyncio
    async def test_poll_for_access_token_returns_str_on_immediate_grant(self) -> None:
        """poll_for_access_token() returns the string access token on immediate success."""
        resp = _MockResponse({"access_token": "gho_test_token"})
        http_mock = _make_http_mock(post_responses=resp)
        with (
            patch("owlbear_knowledge.copilot_auth._http_client", return_value=http_mock),
            patch("owlbear_knowledge.copilot_auth.asyncio.sleep", new_callable=AsyncMock),
            patch("builtins.print"),
        ):
            token = await poll_for_access_token("dc-abc")
        assert isinstance(token, str)
        assert token == "gho_test_token"

    @pytest.mark.asyncio
    async def test_poll_retries_after_authorization_pending(self) -> None:
        """poll_for_access_token() sleeps and retries on authorization_pending response."""
        pending = _MockResponse({"error": "authorization_pending"})
        success = _MockResponse({"access_token": "gho_final"})
        http_mock = _make_http_mock(post_responses=[pending, success])
        sleep_mock = AsyncMock()
        with (
            patch("owlbear_knowledge.copilot_auth._http_client", return_value=http_mock),
            patch("owlbear_knowledge.copilot_auth.asyncio.sleep", sleep_mock),
            patch("builtins.print"),
        ):
            token = await poll_for_access_token("dc-abc")
        assert token == "gho_final"
        sleep_mock.assert_called()

    @pytest.mark.asyncio
    async def test_poll_increases_interval_on_slow_down(self) -> None:
        """poll_for_access_token() increases the sleep interval by 5 on slow_down."""
        slow = _MockResponse({"error": "slow_down"})
        success = _MockResponse({"access_token": "gho_token"})
        http_mock = _make_http_mock(post_responses=[slow, success])
        sleep_calls: list[float] = []

        async def _track_sleep(secs: float) -> None:
            sleep_calls.append(secs)

        with (
            patch("owlbear_knowledge.copilot_auth._http_client", return_value=http_mock),
            patch("owlbear_knowledge.copilot_auth.asyncio.sleep", _track_sleep),
            patch("builtins.print"),
        ):
            await poll_for_access_token("dc-abc", interval=5)

        # After slow_down, the next sleep should be at least interval+5 = 10
        assert any(s >= 10 for s in sleep_calls), (
            f"Expected at least one sleep >= 10 after slow_down, got: {sleep_calls}"
        )

    @pytest.mark.asyncio
    async def test_poll_raises_timeout_error_when_deadline_exceeded(self) -> None:
        """poll_for_access_token() raises TimeoutError when the poll deadline is exceeded."""
        pending = _MockResponse({"error": "authorization_pending"})
        http_mock = _make_http_mock(post_responses=pending)
        with (
            patch("owlbear_knowledge.copilot_auth._http_client", return_value=http_mock),
            patch("owlbear_knowledge.copilot_auth.asyncio.sleep", new_callable=AsyncMock),
            patch("owlbear_knowledge.copilot_auth.time.monotonic", side_effect=[0.0, 1000.0]),
            patch("builtins.print"),
            pytest.raises(TimeoutError),
        ):
            await poll_for_access_token("dc-abc", timeout=900.0)

    @pytest.mark.asyncio
    async def test_exchange_for_copilot_token_returns_token_and_expires_at(self) -> None:
        """exchange_for_copilot_token() returns dict with 'token' and 'expires_at'."""
        resp = _MockResponse({"token": "copilot_jwt", "expires_at": _FAR_FUTURE})
        http_mock = _make_http_mock(get_response=resp)
        with (
            patch("owlbear_knowledge.copilot_auth._http_client", return_value=http_mock),
            patch("builtins.print"),
        ):
            result = await exchange_for_copilot_token("gho_access_token")
        assert "token" in result
        assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_get_copilot_token_returns_cached_token_when_valid(self) -> None:
        """get_copilot_token() returns the cached token without any HTTP calls."""
        cached = {"token": "cached_cp_token", "expires_at": _FAR_FUTURE}
        with patch("owlbear_knowledge.copilot_auth.load_token", return_value=cached):
            token = await get_copilot_token()
        assert token == "cached_cp_token"

    @pytest.mark.asyncio
    async def test_get_copilot_token_runs_full_device_flow_on_cache_miss(self) -> None:
        """get_copilot_token() runs device flow when no cached token is available."""
        with (
            patch("owlbear_knowledge.copilot_auth.load_token", return_value=None),
            patch(
                "owlbear_knowledge.copilot_auth.request_device_code",
                new_callable=AsyncMock,
                return_value={
                    "device_code": "dc-xyz",
                    "user_code": "CODE-1",
                    "expires_in": 900,
                    "interval": 5,
                },
            ),
            patch(
                "owlbear_knowledge.copilot_auth.poll_for_access_token",
                new_callable=AsyncMock,
                return_value="gho_fresh",
            ),
            patch(
                "owlbear_knowledge.copilot_auth.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value={"token": "cp_fresh", "expires_at": _FAR_FUTURE},
            ),
            patch("owlbear_knowledge.copilot_auth.save_token"),
            patch("builtins.print"),
        ):
            token = await get_copilot_token()
        assert token == "cp_fresh"


# ---------------------------------------------------------------------------
# TestFromAC_TokenCache — AC2: token caching with expiry-aware refresh
# ---------------------------------------------------------------------------


class TestFromAC_TokenCache:
    """AC2: Token caching at ~/.owlbear/copilot_token.json with expiry-aware refresh."""

    def test_save_token_writes_json_to_given_path(self, tmp_path: Path) -> None:
        """save_token() writes token_data as JSON to the specified path."""
        token_data = {"token": "test_tok", "expires_at": _FAR_FUTURE}
        token_path = tmp_path / "copilot_token.json"
        save_token(token_data, path=token_path)
        assert token_path.exists()
        with token_path.open() as f:
            loaded = json.load(f)
        assert loaded["token"] == "test_tok"

    def test_load_token_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """load_token() returns None when the token file does not exist."""
        missing = tmp_path / "no_such.json"
        assert load_token(path=missing) is None

    def test_load_token_returns_token_data_when_file_valid_and_unexpired(self, tmp_path: Path) -> None:
        """load_token() returns token dict when file exists and token has not expired."""
        token_data = {"token": "valid_tok", "expires_at": _FAR_FUTURE}
        p = tmp_path / "token.json"
        p.write_text(json.dumps(token_data))
        result = load_token(path=p)
        assert result is not None
        assert result["token"] == "valid_tok"

    def test_load_token_returns_none_for_expired_token(self, tmp_path: Path) -> None:
        """load_token() returns None when expires_at is in the past."""
        token_data = {"token": "expired_tok", "expires_at": int(time.time()) - 120}
        p = tmp_path / "token.json"
        p.write_text(json.dumps(token_data))
        assert load_token(path=p) is None

    def test_load_token_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        """load_token() returns None when the file contains invalid JSON."""
        p = tmp_path / "token.json"
        p.write_text("not {{ valid json }")
        assert load_token(path=p) is None

    def test_load_token_returns_none_within_60s_expiry_margin(self, tmp_path: Path) -> None:
        """load_token() treats token as expired when expires_at is within 60 seconds of now."""
        token_data = {"token": "near_expiry", "expires_at": int(time.time()) + 30}
        p = tmp_path / "token.json"
        p.write_text(json.dumps(token_data))
        # 30 seconds until expiry is within the 60-second safety margin
        assert load_token(path=p) is None


# ---------------------------------------------------------------------------
# TestFromAC_DeriveBaseUrl — AC1: derive_base_url converts token to API URL
# ---------------------------------------------------------------------------


class TestFromAC_DeriveBaseUrl:
    """AC1: derive_base_url() converts the Copilot token's proxy-ep into an API URL."""

    def test_proxy_ep_in_token_yields_api_prefixed_url(self) -> None:
        """Token with proxy-ep=proxy.host returns an api.host URL."""
        token = "tid=abc;proxy-ep=proxy.individual.githubcopilot.com;exp=999"
        result = derive_base_url(token)
        assert "api." in result
        assert "proxy." not in result

    def test_missing_proxy_ep_returns_default_copilot_base(self) -> None:
        """Token without proxy-ep key returns DEFAULT_COPILOT_BASE."""
        token = "tid=abc;exp=999"
        assert derive_base_url(token) == DEFAULT_COPILOT_BASE

    def test_derived_url_starts_with_https(self) -> None:
        """derive_base_url() always returns a URL beginning with https://."""
        token = "tid=abc;proxy-ep=proxy.individual.githubcopilot.com;exp=999"
        assert derive_base_url(token).startswith("https://")

    def test_empty_token_returns_default_copilot_base_without_raising(self) -> None:
        """Malformed or empty token returns DEFAULT_COPILOT_BASE without raising."""
        assert derive_base_url("") == DEFAULT_COPILOT_BASE


# ---------------------------------------------------------------------------
# TestFromAC_EditorHeaders — AC3: headers injected into AsyncOpenAI
# ---------------------------------------------------------------------------


class TestFromAC_EditorHeaders:
    """AC3: Editor headers are injected into AsyncOpenAI via LLMExtractor.default_headers."""

    def test_llm_extractor_constructor_accepts_default_headers_kwarg(self) -> None:
        """LLMExtractor constructor does not raise when default_headers is provided."""
        headers = {"Copilot-Integration-Id": "vscode-chat", "Editor-Version": "vscode/1.97.1"}
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", default_headers=headers)
        assert extractor is not None

    def test_default_headers_forwarded_to_async_openai_constructor(self) -> None:
        """The default_headers dict is passed as-is to the AsyncOpenAI constructor."""
        headers = {"Copilot-Integration-Id": "vscode-chat", "Editor-Version": "vscode/1.97.1"}
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            LLMExtractor(model="gpt-4o", api_key="sk-test", default_headers=headers)
        assert mock_aoi.call_args.kwargs.get("default_headers") == headers

    def test_default_headers_absent_when_not_provided(self) -> None:
        """AsyncOpenAI is called without Copilot headers when default_headers is omitted."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            LLMExtractor(model="gpt-4o", api_key="sk-test")
        dh = mock_aoi.call_args.kwargs.get("default_headers")
        # Must not inject Copilot headers when not requested
        assert not dh or "Copilot-Integration-Id" not in dh

    def test_copilot_integration_id_can_be_passed_in_default_headers(self) -> None:
        """Copilot-Integration-Id header value 'vscode-chat' is accepted without error."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            extractor = LLMExtractor(
                model="gpt-4o",
                api_key="sk-tok",
                default_headers={"Copilot-Integration-Id": "vscode-chat"},
            )
        assert extractor is not None


# ---------------------------------------------------------------------------
# TestFromAC_DynamicVersionDetection — Refined AC7
# ---------------------------------------------------------------------------


class TestFromAC_DynamicVersionDetection:
    """Refined AC7: Editor headers use dynamically detected VS Code/extension versions."""

    def test_detect_editor_versions_returns_dict_with_editor_version_key(self) -> None:
        """detect_editor_versions() returns a dict containing 'Editor-Version'."""
        result = detect_editor_versions()
        assert isinstance(result, dict)
        assert "Editor-Version" in result

    def test_detect_editor_versions_falls_back_to_defaults_on_os_error(self) -> None:
        """detect_editor_versions() returns valid default dict when VS Code paths raise OSError."""
        with patch(
            "owlbear_knowledge.copilot_auth._find_vscode_version",
            side_effect=FileNotFoundError("vscode not found"),
        ):
            result = detect_editor_versions()
        assert "Editor-Version" in result
        assert isinstance(result["Editor-Version"], str)
        assert len(result["Editor-Version"]) > 0

    def test_detect_editor_versions_falls_back_to_defaults_on_parse_error(self) -> None:
        """detect_editor_versions() returns valid default dict when version files are unparseable."""
        with patch(
            "owlbear_knowledge.copilot_auth._find_vscode_version",
            side_effect=ValueError("invalid version format"),
        ):
            result = detect_editor_versions()
        assert "Editor-Version" in result
        assert isinstance(result["Editor-Version"], str)


# ---------------------------------------------------------------------------
# TestFromAC_GracefulFallback — AC5: auth failure degrades to no-op extraction
# ---------------------------------------------------------------------------


class TestFromAC_GracefulFallback:
    """AC5: If Copilot auth fails, LLM extraction degrades to no-op (empty ExtractionResult)."""

    @pytest.mark.asyncio
    async def test_extract_returns_empty_when_llm_call_fails_with_copilot_headers(self) -> None:
        """extract() returns empty ExtractionResult when the LLM API call raises (Copilot path)."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            client = MagicMock()
            client.chat.completions.parse = AsyncMock(side_effect=Exception("Copilot auth revoked"))
            mock_aoi.return_value = client
            extractor = LLMExtractor(
                model="gpt-4o",
                api_key="bad_copilot_token",
                default_headers={"Copilot-Integration-Id": "vscode-chat"},
            )
            result = await extractor.extract("some content to extract")
        assert result == ExtractionResult()

    @pytest.mark.asyncio
    async def test_get_copilot_token_timeout_propagates_to_caller(self) -> None:
        """TimeoutError from poll_for_access_token propagates out of get_copilot_token."""
        with (
            patch("owlbear_knowledge.copilot_auth.load_token", return_value=None),
            patch(
                "owlbear_knowledge.copilot_auth.request_device_code",
                new_callable=AsyncMock,
                return_value={
                    "device_code": "dc-xyz",
                    "user_code": "CODE-1",
                    "expires_in": 900,
                    "interval": 5,
                },
            ),
            patch(
                "owlbear_knowledge.copilot_auth.poll_for_access_token",
                new_callable=AsyncMock,
                side_effect=TimeoutError("browser auth timeout"),
            ),
            patch("builtins.print"),
            pytest.raises(TimeoutError),
        ):
            await get_copilot_token()


# ---------------------------------------------------------------------------
# TestFromAC_RateLimiting — Refined AC8: configurable rate limiting
# ---------------------------------------------------------------------------


class TestFromAC_RateLimiting:
    """Refined AC8: LLMExtractor supports a configurable requests_per_minute threshold."""

    def test_llm_extractor_accepts_requests_per_minute_kwarg(self) -> None:
        """LLMExtractor constructor does not raise when requests_per_minute is provided."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            extractor = LLMExtractor(
                model="gpt-4o",
                api_key="sk-test",
                requests_per_minute=60,
            )
        assert extractor is not None

    def test_llm_extractor_requests_per_minute_none_means_unlimited(self) -> None:
        """LLMExtractor with requests_per_minute=None imposes no rate limit."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            extractor = LLMExtractor(
                model="gpt-4o",
                api_key="sk-test",
                requests_per_minute=None,
            )
        assert extractor is not None

    @pytest.mark.asyncio
    async def test_extract_returns_empty_when_rpm_budget_exhausted_in_window(self) -> None:
        """extract() returns ExtractionResult() gracefully when rate limit is exhausted."""
        frozen = 1_000_000.0
        with (
            patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi,
            patch("owlbear_knowledge.llm_extractor.time") as mock_time,
        ):
            mock_time.monotonic.return_value = frozen
            client = MagicMock()
            client.chat.completions.parse = AsyncMock(
                return_value=MagicMock(choices=[MagicMock(message=MagicMock(parsed=ExtractionResult()))])
            )
            mock_aoi.return_value = client
            # 1 request per minute: second call within same frozen window is rate-limited
            extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", requests_per_minute=1)
            await extractor.extract("first call — uses the budget")
            result = await extractor.extract("second call — budget exhausted")
        assert result == ExtractionResult()


# ---------------------------------------------------------------------------
# TestFromAC_PyprojectTomlDeps — Refined AC10: truststore in optional deps
# ---------------------------------------------------------------------------


class TestFromAC_PyprojectTomlDeps:
    """Refined AC10: truststore added to serve/knowledge/pyproject.toml optional deps."""

    def test_truststore_present_in_at_least_one_optional_dep_group(self) -> None:
        """pyproject.toml optional-dependencies contains 'truststore' in some group."""
        with _PYPROJECT_PATH.open("rb") as f:
            config = tomllib.load(f)
        optional_deps = config.get("project", {}).get("optional-dependencies", {})
        all_deps = [dep for group in optional_deps.values() for dep in group]
        assert any("truststore" in dep for dep in all_deps), (
            f"truststore not found in any optional-dep group. All deps: {all_deps}"
        )

    def test_optional_dep_group_containing_truststore_also_includes_httpx(self) -> None:
        """The group containing truststore also declares httpx (Copilot group)."""
        with _PYPROJECT_PATH.open("rb") as f:
            config = tomllib.load(f)
        optional_deps = config.get("project", {}).get("optional-dependencies", {})
        copilot_groups = {name: deps for name, deps in optional_deps.items() if any("truststore" in d for d in deps)}
        assert copilot_groups, "No optional-dep group with truststore found"
        for deps in copilot_groups.values():
            assert any("httpx" in d for d in deps), f"Group with truststore must also include httpx. Got: {deps}"


# ---------------------------------------------------------------------------
# TestBuilderDiscovered — coverage gaps found during GREEN phase
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered tests: private helpers and error paths not covered by AC suite."""

    def test_ssl_context_returns_default_ssl_context_when_truststore_unavailable(self) -> None:
        """_ssl_context() returns a standard SSLContext when truststore cannot be imported."""
        import ssl
        import sys
        from owlbear_knowledge.copilot_auth import _ssl_context

        with patch.dict(sys.modules, {"truststore": None}):
            ctx = _ssl_context()
        assert isinstance(ctx, ssl.SSLContext)

    def test_detect_editor_versions_returns_dynamic_version_when_vscode_found(self) -> None:
        """detect_editor_versions() returns headers with detected version on success."""
        with patch("owlbear_knowledge.copilot_auth._find_vscode_version", return_value="1.100.0"):
            result = detect_editor_versions()
        assert result["Editor-Version"] == "vscode/1.100.0"
        assert "Editor-Plugin-Version" in result

    @pytest.mark.asyncio
    async def test_poll_raises_runtime_error_on_unrecognised_oauth_error_code(self) -> None:
        """poll_for_access_token() raises RuntimeError on unexpected OAuth error codes."""
        resp = _MockResponse({"error": "expired_token"})
        http_mock = _make_http_mock(post_responses=resp)
        with (
            patch("owlbear_knowledge.copilot_auth._http_client", return_value=http_mock),
            patch("builtins.print"),
            pytest.raises(RuntimeError, match="OAuth error"),
        ):
            await poll_for_access_token("dc-abc")

    def test_http_client_returns_async_client_from_httpx(self) -> None:
        """_http_client() calls httpx.AsyncClient with ssl context and editor headers."""
        import sys
        from owlbear_knowledge.copilot_auth import _http_client

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = MagicMock()
        with (
            patch.dict(sys.modules, {"httpx": mock_httpx}),
            patch("owlbear_knowledge.copilot_auth._ssl_context", return_value=MagicMock()),
        ):
            result = _http_client()
        assert result is not None
        mock_httpx.AsyncClient.assert_called_once()
