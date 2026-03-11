"""Tests for BearClaw auth CLI commands (login + status)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


class TestAuthLogin:
    """Test `bearclaw auth login` device-flow command."""

    def test_login_prints_user_code(self) -> None:
        """Login should display the user_code for the user to enter."""
        device_resp = {
            "device_code": "dc_1234",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        with (
            patch(
                "bearclaw.commands.auth.request_device_code",
                new_callable=AsyncMock,
                return_value=device_resp,
            ),
            patch(
                "bearclaw.commands.auth.poll_for_access_token",
                new_callable=AsyncMock,
                return_value="ghu_fake_token",
            ),
            patch(
                "bearclaw.commands.auth.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value={"token": "copilot_tok", "expires_at": 9999999999},
            ),
            patch("bearclaw.commands.auth.save_token") as _mock_save,
            patch("bearclaw.commands.auth.webbrowser") as _mock_wb,
        ):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0
        assert "ABCD-1234" in result.output

    def test_login_prints_verification_uri(self) -> None:
        """Login should display the verification URL."""
        device_resp = {
            "device_code": "dc_1234",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        with (
            patch(
                "bearclaw.commands.auth.request_device_code",
                new_callable=AsyncMock,
                return_value=device_resp,
            ),
            patch(
                "bearclaw.commands.auth.poll_for_access_token",
                new_callable=AsyncMock,
                return_value="ghu_fake_token",
            ),
            patch(
                "bearclaw.commands.auth.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value={"token": "copilot_tok", "expires_at": 9999999999},
            ),
            patch("bearclaw.commands.auth.save_token"),
            patch("bearclaw.commands.auth.webbrowser"),
        ):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0
        assert "https://github.com/login/device" in result.output

    def test_login_opens_browser(self) -> None:
        """Login should open the verification URI in the user's browser."""
        device_resp = {
            "device_code": "dc_1234",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        with (
            patch(
                "bearclaw.commands.auth.request_device_code",
                new_callable=AsyncMock,
                return_value=device_resp,
            ),
            patch(
                "bearclaw.commands.auth.poll_for_access_token",
                new_callable=AsyncMock,
                return_value="ghu_fake_token",
            ),
            patch(
                "bearclaw.commands.auth.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value={"token": "copilot_tok", "expires_at": 9999999999},
            ),
            patch("bearclaw.commands.auth.save_token"),
            patch("bearclaw.commands.auth.webbrowser") as mock_wb,
        ):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0
        mock_wb.open.assert_called_once_with("https://github.com/login/device")

    def test_login_calls_full_device_flow(self) -> None:
        """Login should call request → poll → exchange → save in sequence."""
        device_resp = {
            "device_code": "dc_1234",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        copilot_data = {"token": "copilot_tok", "expires_at": 9999999999}
        with (
            patch(
                "bearclaw.commands.auth.request_device_code",
                new_callable=AsyncMock,
                return_value=device_resp,
            ) as mock_device,
            patch(
                "bearclaw.commands.auth.poll_for_access_token",
                new_callable=AsyncMock,
                return_value="ghu_fake_token",
            ) as mock_poll,
            patch(
                "bearclaw.commands.auth.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value=copilot_data,
            ) as mock_exchange,
            patch("bearclaw.commands.auth.save_token") as mock_save,
            patch("bearclaw.commands.auth.webbrowser"),
        ):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0
        mock_device.assert_called_once()
        mock_poll.assert_called_once_with("dc_1234", interval=5, expires_in=900)
        mock_exchange.assert_called_once_with("ghu_fake_token")
        mock_save.assert_called_once_with(copilot_data)

    def test_login_prints_success_message(self) -> None:
        """Login should print a success message after saving the token."""
        device_resp = {
            "device_code": "dc_1234",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        with (
            patch(
                "bearclaw.commands.auth.request_device_code",
                new_callable=AsyncMock,
                return_value=device_resp,
            ),
            patch(
                "bearclaw.commands.auth.poll_for_access_token",
                new_callable=AsyncMock,
                return_value="ghu_fake_token",
            ),
            patch(
                "bearclaw.commands.auth.exchange_for_copilot_token",
                new_callable=AsyncMock,
                return_value={"token": "copilot_tok", "expires_at": 9999999999},
            ),
            patch("bearclaw.commands.auth.save_token"),
            patch("bearclaw.commands.auth.webbrowser"),
        ):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0
        # Should indicate success somehow
        assert "success" in result.output.lower() or "authenticated" in result.output.lower()

    def test_login_handles_error_gracefully(self) -> None:
        """Login should catch exceptions and print an error message."""
        with patch(
            "bearclaw.commands.auth.request_device_code",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Network error"),
        ):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 1
        assert "error" in result.output.lower() or "failed" in result.output.lower()


class TestAuthStatus:
    """Test `bearclaw auth status` command."""

    def test_status_authenticated_with_valid_token(self) -> None:
        """Valid cached token → prints 'Authenticated'."""
        token_data = {
            "token": "tid=x;exp=9999999999;proxy-ep=proxy.individual.githubcopilot.com",
            "expires_at": 9999999999,
        }
        with patch("bearclaw.commands.auth.load_token", return_value=token_data):
            result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "authenticated" in result.output.lower()

    def test_status_not_authenticated_when_no_token(self) -> None:
        """No cached token → prints 'Not authenticated'."""
        with patch("bearclaw.commands.auth.load_token", return_value=None):
            result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "not authenticated" in result.output.lower()

    def test_status_shows_model_name(self) -> None:
        """Status should display the configured model name."""
        token_data = {
            "token": "tid=x;exp=9999999999;proxy-ep=proxy.individual.githubcopilot.com",
            "expires_at": 9999999999,
        }
        with patch("bearclaw.commands.auth.load_token", return_value=token_data):
            result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "gpt-4o" in result.output

    def test_status_shows_base_url(self) -> None:
        """Status should display the derived base URL."""
        token_data = {
            "token": "tid=x;exp=9999999999;proxy-ep=proxy.individual.githubcopilot.com",
            "expires_at": 9999999999,
        }
        with patch("bearclaw.commands.auth.load_token", return_value=token_data):
            result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "api.individual.githubcopilot.com" in result.output
