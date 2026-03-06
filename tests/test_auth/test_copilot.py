"""Tests for owlbear.auth.copilot — Copilot OAuth device-flow module."""

from __future__ import annotations

import json
import stat
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from owlbear.auth.copilot import (
    COPILOT_TOKEN_URL,
    DEFAULT_COPILOT_BASE,
    DEVICE_CODE_URL,
    derive_base_url,
    exchange_for_copilot_token,
    load_or_refresh_token,
    load_token,
    poll_for_access_token,
    request_device_code,
    save_token,
)

# ---------------------------------------------------------------------------
# request_device_code
# ---------------------------------------------------------------------------


class TestRequestDeviceCode:
    """POST to GitHub device/code endpoint."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_expected_fields(self) -> None:
        """Device code response must include all required fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "device_code": "abc123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client):
            result = await request_device_code()

        assert result["device_code"] == "abc123"
        assert result["user_code"] == "ABCD-1234"
        assert result["verification_uri"] == "https://github.com/login/device"
        assert result["expires_in"] == 900
        assert result["interval"] == 5


# ---------------------------------------------------------------------------
# poll_for_access_token
# ---------------------------------------------------------------------------


class TestPollForAccessToken:
    """Polling loop for user authorization."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_handles_authorization_pending(self) -> None:
        """Should retry on authorization_pending then succeed."""
        pending = MagicMock()
        pending.json.return_value = {"error": "authorization_pending"}

        success = MagicMock()
        success.json.return_value = {"access_token": "ghu_token123"}

        mock_client = AsyncMock()
        mock_client.post.side_effect = [pending, success]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client),
            patch("owlbear.auth.copilot.asyncio.sleep", new_callable=AsyncMock),
        ):
            token = await poll_for_access_token("device123", interval=1, expires_in=60)

        assert token == "ghu_token123"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_handles_slow_down_increases_interval(self) -> None:
        """slow_down error should increase interval by 5 seconds."""
        slow = MagicMock()
        slow.json.return_value = {"error": "slow_down"}

        success = MagicMock()
        success.json.return_value = {"access_token": "ghu_slow_ok"}

        mock_client = AsyncMock()
        mock_client.post.side_effect = [slow, success]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        sleep_mock = AsyncMock()
        with (
            patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client),
            patch("owlbear.auth.copilot.asyncio.sleep", sleep_mock),
        ):
            token = await poll_for_access_token("device123", interval=5, expires_in=60)

        assert token == "ghu_slow_ok"
        # First sleep should be with interval+5=10 (slow_down increases by 5)
        sleep_mock.assert_any_call(10)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_token_on_success(self) -> None:
        """Should return access_token immediately when present."""
        success = MagicMock()
        success.json.return_value = {"access_token": "ghu_immediate"}

        mock_client = AsyncMock()
        mock_client.post.side_effect = [success]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client),
            patch("owlbear.auth.copilot.asyncio.sleep", new_callable=AsyncMock),
        ):
            token = await poll_for_access_token("device123", interval=1, expires_in=60)

        assert token == "ghu_immediate"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_timeout_on_expiry(self) -> None:
        """Should raise TimeoutError when device code expires."""
        pending = MagicMock()
        pending.json.return_value = {"error": "authorization_pending"}

        mock_client = AsyncMock()
        mock_client.post.return_value = pending
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Simulate time progression: first call within window, second past expiry
        time_values = iter([0.0, 0.0, 100.0])

        with (
            patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client),
            patch("owlbear.auth.copilot.asyncio.sleep", new_callable=AsyncMock),
            patch("owlbear.auth.copilot.time.time", side_effect=time_values),
            pytest.raises(TimeoutError, match="expired"),
        ):
            await poll_for_access_token("device123", interval=1, expires_in=10)


# ---------------------------------------------------------------------------
# exchange_for_copilot_token
# ---------------------------------------------------------------------------


class TestExchangeForCopilotToken:
    """Exchange GitHub access token for Copilot session token."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_token_dict(self) -> None:
        """Should return dict with token and expires_at."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "token": "tid=abc;exp=9999999999;sku=free;proxy-ep=proxy.example.com",
            "expires_at": 9999999999,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client):
            result = await exchange_for_copilot_token("ghu_access_token")

        assert "token" in result
        assert "expires_at" in result
        assert result["expires_at"] == 9999999999


# ---------------------------------------------------------------------------
# TRANSIENT_RETRY integration — request_device_code
# ---------------------------------------------------------------------------


class TestRequestDeviceCodeRetry:
    """Verify TRANSIENT_RETRY decorator on request_device_code."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_retries_on_502_then_succeeds(self) -> None:
        """502 twice then 200 → 3 calls total, success returned."""
        success_response = MagicMock()
        success_response.json.return_value = {
            "device_code": "abc",
            "user_code": "XXXX",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        success_response.raise_for_status = MagicMock()

        error_response_1 = httpx.Response(502, request=httpx.Request("POST", DEVICE_CODE_URL))
        error_response_2 = httpx.Response(502, request=httpx.Request("POST", DEVICE_CODE_URL))

        call_count = 0

        async def _fake_post(*_args: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                msg = "Server Error"
                raise httpx.HTTPStatusError(
                    msg,
                    request=httpx.Request("POST", DEVICE_CODE_URL),
                    response=error_response_1 if call_count == 1 else error_response_2,
                )
            return success_response

        mock_client = AsyncMock()
        mock_client.post = _fake_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client):
            result = await request_device_code()

        assert result["device_code"] == "abc"
        assert call_count == 3

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_retry_on_401(self) -> None:
        """401 is non-transient → 1 call only, exception propagates."""
        error_response = httpx.Response(401, request=httpx.Request("POST", DEVICE_CODE_URL))

        call_count = 0

        async def _fake_post(*_args: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            msg = "Unauthorized"
            raise httpx.HTTPStatusError(
                msg,
                request=httpx.Request("POST", DEVICE_CODE_URL),
                response=error_response,
            )

        mock_client = AsyncMock()
        mock_client.post = _fake_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(httpx.HTTPStatusError, match="Unauthorized"),
        ):
            await request_device_code()

        assert call_count == 1


# ---------------------------------------------------------------------------
# TRANSIENT_RETRY integration — exchange_for_copilot_token
# ---------------------------------------------------------------------------


class TestExchangeForCopilotTokenRetry:
    """Verify TRANSIENT_RETRY decorator on exchange_for_copilot_token."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_retries_on_502_then_succeeds(self) -> None:
        """502 twice then 200 → 3 calls total, success returned."""
        success_response = MagicMock()
        success_response.json.return_value = {
            "token": "tid=ok",
            "expires_at": 9999999999,
        }
        success_response.raise_for_status = MagicMock()

        call_count = 0

        async def _fake_get(*_args: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                msg = "Bad Gateway"
                raise httpx.HTTPStatusError(
                    msg,
                    request=httpx.Request("GET", COPILOT_TOKEN_URL),
                    response=httpx.Response(502, request=httpx.Request("GET", COPILOT_TOKEN_URL)),
                )
            return success_response

        mock_client = AsyncMock()
        mock_client.get = _fake_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client):
            result = await exchange_for_copilot_token("ghu_token")

        assert result["token"] == "tid=ok"
        assert call_count == 3

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_retry_on_401(self) -> None:
        """401 is non-transient → 1 call only, exception propagates."""
        call_count = 0

        async def _fake_get(*_args: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            msg = "Unauthorized"
            raise httpx.HTTPStatusError(
                msg,
                request=httpx.Request("GET", COPILOT_TOKEN_URL),
                response=httpx.Response(401, request=httpx.Request("GET", COPILOT_TOKEN_URL)),
            )

        mock_client = AsyncMock()
        mock_client.get = _fake_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("owlbear.auth.copilot.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(httpx.HTTPStatusError, match="Unauthorized"),
        ):
            await exchange_for_copilot_token("ghu_token")

        assert call_count == 1


# ---------------------------------------------------------------------------
# derive_base_url
# ---------------------------------------------------------------------------


class TestDeriveBaseUrl:
    """Parse proxy-ep from semicolon-delimited token and derive API URL."""

    def test_parses_proxy_ep_from_token(self) -> None:
        """Should extract proxy-ep and convert proxy→api in hostname."""
        token = "tid=abc;exp=123;sku=free;proxy-ep=proxy.individual.githubcopilot.com"
        url = derive_base_url(token)
        assert url == "https://api.individual.githubcopilot.com"

    def test_returns_default_when_no_proxy_ep(self) -> None:
        """Should return DEFAULT_COPILOT_BASE when proxy-ep is not found."""
        token = "tid=abc;exp=123;sku=free"
        url = derive_base_url(token)
        assert url == DEFAULT_COPILOT_BASE

    def test_handles_spaces_around_semicolons(self) -> None:
        """Whitespace around parts should not break parsing."""
        token = "tid=abc ; proxy-ep=proxy.example.com ; sku=free"
        url = derive_base_url(token)
        assert url == "https://api.example.com"


# ---------------------------------------------------------------------------
# Token caching: save + load round-trip
# ---------------------------------------------------------------------------


class TestTokenCaching:
    """Save and load tokens to/from JSON file."""

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        """Token data should survive a save→load cycle."""
        token_path = tmp_path / "copilot_token.json"
        token_data = {"token": "abc123", "expires_at": 9999999999}

        save_token(token_data, token_path)
        loaded = load_token(token_path)

        assert loaded is not None
        assert loaded["token"] == "abc123"
        assert loaded["expires_at"] == 9999999999

    def test_load_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """load_token should return None when file doesn't exist."""
        result = load_token(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_returns_none_for_expired_token(self, tmp_path: Path) -> None:
        """load_token should return None when token has expired (with 60s margin)."""
        token_path = tmp_path / "copilot_token.json"
        # Token that expires 30 seconds from now (within 60s safety margin)
        expires_at = int(time.time()) + 30
        token_data = {"token": "expiring", "expires_at": expires_at}

        save_token(token_data, token_path)
        loaded = load_token(token_path)

        assert loaded is None

    def test_load_returns_token_when_not_expired(self, tmp_path: Path) -> None:
        """load_token should return data when token is valid (beyond 60s margin)."""
        token_path = tmp_path / "copilot_token.json"
        # Token that expires 120 seconds from now (well beyond 60s safety margin)
        expires_at = int(time.time()) + 120
        token_data = {"token": "fresh_token", "expires_at": expires_at}

        save_token(token_data, token_path)
        loaded = load_token(token_path)

        assert loaded is not None
        assert loaded["token"] == "fresh_token"

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        """save_token should create parent dirs if they don't exist."""
        token_path = tmp_path / "subdir" / "copilot_token.json"
        token_data = {"token": "nested", "expires_at": 9999999999}

        save_token(token_data, token_path)

        assert token_path.exists()
        loaded = json.loads(token_path.read_text())
        assert loaded["token"] == "nested"

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions only")
    def test_save_sets_file_permissions_0600(self, tmp_path: Path) -> None:
        """save_token should create the file with mode 0o600 on Unix."""
        token_path = tmp_path / "copilot_token.json"
        token_data = {"token": "secret", "expires_at": 9999999999}

        save_token(token_data, token_path)

        file_mode = stat.S_IMODE(token_path.stat().st_mode)
        assert file_mode == 0o600

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions only")
    def test_save_sets_parent_dir_permissions_0700(self, tmp_path: Path) -> None:
        """save_token should set parent directory mode to 0o700 on Unix."""
        token_path = tmp_path / "newdir" / "copilot_token.json"
        token_data = {"token": "secret", "expires_at": 9999999999}

        save_token(token_data, token_path)

        dir_mode = stat.S_IMODE(token_path.parent.stat().st_mode)
        assert dir_mode == 0o700

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_save_uses_write_text_on_windows(self, tmp_path: Path) -> None:
        """save_token should use Path.write_text() on Windows."""
        token_path = tmp_path / "copilot_token.json"
        token_data = {"token": "wintoken", "expires_at": 9999999999}

        save_token(token_data, token_path)

        # Verify file was created and data round-trips
        loaded = json.loads(token_path.read_text())
        assert loaded["token"] == "wintoken"


# ---------------------------------------------------------------------------
# load_or_refresh_token — convenience function
# ---------------------------------------------------------------------------


class TestLoadOrRefreshToken:
    """Convenience function: load cached token or run full OAuth flow."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_cached_token_when_valid(self, tmp_path: Path) -> None:
        """Should return cached token without hitting the network."""
        token_path = tmp_path / "copilot_token.json"
        expires_at = int(time.time()) + 3600
        token_data = {"token": "cached_token_value", "expires_at": expires_at}
        token_path.write_text(json.dumps(token_data))

        result = await load_or_refresh_token(token_path)

        assert result == "cached_token_value"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_runs_full_flow_when_no_cache(self, tmp_path: Path) -> None:
        """Should execute device flow when no cached token exists."""
        token_path = tmp_path / "copilot_token.json"

        # Mock the full flow
        with (
            patch(
                "owlbear.auth.copilot.request_device_code",
                new_callable=AsyncMock,
                return_value={
                    "device_code": "dev123",
                    "user_code": "ABCD-1234",
                    "verification_uri": "https://github.com/login/device",
                    "expires_in": 900,
                    "interval": 5,
                },
            ),
            patch(
                "owlbear.auth.copilot.poll_for_access_token",
                new_callable=AsyncMock,
                return_value="ghu_access",
            ),
            patch(
                "owlbear.auth.copilot.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value={
                    "token": "new_copilot_token",
                    "expires_at": int(time.time()) + 3600,
                },
            ),
        ):
            result = await load_or_refresh_token(token_path)

        assert result == "new_copilot_token"
        # Verify token was saved to disk
        assert token_path.exists()
        saved = json.loads(token_path.read_text())
        assert saved["token"] == "new_copilot_token"
