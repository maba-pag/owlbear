"""Tests for knowledge intake — file, URL, and text content readers."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.intake import (
    IntakeResult,
    read_file,
    read_text,
    read_url,
)

# -- IntakeResult model -------------------------------------------------------


class TestIntakeResult:
    """IntakeResult is a frozen Pydantic model."""

    def test_frozen(self) -> None:
        result = IntakeResult(content="hello", source="test", metadata={})
        with pytest.raises(ValidationError):
            result.content = "changed"  # type: ignore[misc]

    def test_fields(self) -> None:
        result = IntakeResult(
            content="body",
            source="somewhere",
            metadata={"source_type": "text", "fetched_at": "2026-01-01T00:00:00"},
        )
        assert result.content == "body"
        assert result.source == "somewhere"
        assert result.metadata["source_type"] == "text"
        assert "fetched_at" in result.metadata


# -- read_file -----------------------------------------------------------------


class TestReadFile:
    """read_file reads a file from disk and returns IntakeResult."""

    @pytest.mark.anyio
    async def test_returns_intake_result_with_content(self, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        p = root / "sample.txt"
        p.write_text("hello world", encoding="utf-8")

        result = await read_file(p, workspace_root=root)

        assert isinstance(result, IntakeResult)
        assert result.content == "hello world"

    @pytest.mark.anyio
    async def test_source_is_file_path(self, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        p = root / "data.md"
        p.write_text("# Title", encoding="utf-8")

        result = await read_file(p, workspace_root=root)

        assert result.source == str(p)

    @pytest.mark.anyio
    async def test_metadata_source_type_is_file(self, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        p = root / "info.txt"
        p.write_text("content", encoding="utf-8")

        result = await read_file(p, workspace_root=root)

        assert result.metadata["source_type"] == "file"

    @pytest.mark.anyio
    async def test_metadata_has_fetched_at(self, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        p = root / "ts.txt"
        p.write_text("time", encoding="utf-8")

        result = await read_file(p, workspace_root=root)

        assert "fetched_at" in result.metadata
        # Verify it's a valid ISO timestamp
        datetime.datetime.fromisoformat(result.metadata["fetched_at"])

    @pytest.mark.anyio
    async def test_workspace_root_is_required(self, tmp_path: object) -> None:
        """workspace_root is a mandatory keyword arg — omitting it raises TypeError."""
        from pathlib import Path

        root = Path(str(tmp_path))
        p = root / "sample.txt"
        p.write_text("data", encoding="utf-8")

        with pytest.raises(TypeError):
            await read_file(p)  # type: ignore[call-arg]

    @pytest.mark.anyio
    async def test_file_not_found_raises(self, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            await read_file(root / "nonexistent.txt", workspace_root=root)

    @pytest.mark.anyio
    async def test_accepts_str_path(self, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        p = root / "str_path.txt"
        p.write_text("via string", encoding="utf-8")

        result = await read_file(str(p), workspace_root=root)

        assert result.content == "via string"

    # -- Sandbox tests ---------------------------------------------------------

    @pytest.mark.anyio
    async def test_traversal_rejected(self, tmp_path: object) -> None:
        """Path traversal (../) outside workspace_root raises PermissionError."""
        from pathlib import Path

        root = Path(str(tmp_path)) / "workspace"
        root.mkdir()

        with pytest.raises(PermissionError, match="outside workspace"):
            await read_file("../secret.txt", workspace_root=root)

    @pytest.mark.anyio
    async def test_absolute_outside_rejected(self, tmp_path: object) -> None:
        """Absolute path outside workspace_root raises PermissionError."""
        from pathlib import Path

        root = Path(str(tmp_path)) / "workspace"
        root.mkdir()

        with pytest.raises(PermissionError, match="outside workspace"):
            await read_file("/etc/passwd", workspace_root=root)

    @pytest.mark.anyio
    async def test_null_byte_rejected(self, tmp_path: object) -> None:
        """Path containing null byte raises PermissionError."""
        from pathlib import Path

        root = Path(str(tmp_path))

        with pytest.raises(PermissionError, match="outside workspace"):
            await read_file("file\x00.txt", workspace_root=root)

    @pytest.mark.anyio
    async def test_valid_path_accepted(self, tmp_path: object) -> None:
        """Valid path inside workspace_root returns IntakeResult normally."""
        from pathlib import Path

        root = Path(str(tmp_path))
        sub = root / "docs"
        sub.mkdir()
        f = sub / "readme.md"
        f.write_text("# Hello", encoding="utf-8")

        result = await read_file("docs/readme.md", workspace_root=root)

        assert isinstance(result, IntakeResult)
        assert result.content == "# Hello"


# -- read_url ------------------------------------------------------------------


class TestReadUrl:
    """read_url fetches a URL via httpx and returns IntakeResult."""

    @pytest.mark.anyio
    async def test_returns_intake_result_with_content(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "fetched content"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear.memory.knowledge.intake.httpx.AsyncClient", return_value=mock_client):
            result = await read_url("https://example.com/page")

        assert isinstance(result, IntakeResult)
        assert result.content == "fetched content"

    @pytest.mark.anyio
    async def test_source_is_url(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "data"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear.memory.knowledge.intake.httpx.AsyncClient", return_value=mock_client):
            result = await read_url("https://example.com/doc")

        assert result.source == "https://example.com/doc"

    @pytest.mark.anyio
    async def test_metadata_source_type_is_url(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "data"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear.memory.knowledge.intake.httpx.AsyncClient", return_value=mock_client):
            result = await read_url("https://example.com")

        assert result.metadata["source_type"] == "url"

    @pytest.mark.anyio
    async def test_metadata_has_fetched_at(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "data"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear.memory.knowledge.intake.httpx.AsyncClient", return_value=mock_client):
            result = await read_url("https://example.com")

        assert "fetched_at" in result.metadata
        datetime.datetime.fromisoformat(result.metadata["fetched_at"])

    @pytest.mark.anyio
    async def test_http_error_propagates(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(spec=httpx.Request),
            response=mock_response,
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("owlbear.memory.knowledge.intake.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await read_url("https://example.com/fail")


# -- read_text -----------------------------------------------------------------


class TestReadText:
    """read_text wraps raw text into IntakeResult."""

    def test_returns_intake_result(self) -> None:
        result = read_text("some text")
        assert isinstance(result, IntakeResult)
        assert result.content == "some text"

    def test_default_source_is_inline(self) -> None:
        result = read_text("hello")
        assert result.source == "inline"

    def test_custom_source(self) -> None:
        result = read_text("hello", source="clipboard")
        assert result.source == "clipboard"

    def test_metadata_source_type_is_text(self) -> None:
        result = read_text("hello")
        assert result.metadata["source_type"] == "text"

    def test_metadata_has_fetched_at(self) -> None:
        result = read_text("hello")
        assert "fetched_at" in result.metadata
        datetime.datetime.fromisoformat(result.metadata["fetched_at"])


# -- read_url retry behaviour -------------------------------------------------


class TestReadUrlRetry:
    """read_url retries transient HTTP errors via TRANSIENT_RETRY."""

    @pytest.mark.anyio
    async def test_retries_502_then_succeeds(self) -> None:
        """Mock 502 twice then 200 — verify IntakeResult returned with correct content."""
        resp_502 = MagicMock(spec=httpx.Response)
        resp_502.status_code = 502
        resp_502.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Gateway",
            request=MagicMock(spec=httpx.Request),
            response=resp_502,
        )

        resp_200 = MagicMock(spec=httpx.Response)
        resp_200.text = "success content"
        resp_200.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=[resp_502, resp_502, resp_200])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "owlbear.memory.knowledge.intake.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await read_url("https://example.com/retry")

        assert isinstance(result, IntakeResult)
        assert result.content == "success content"
        assert mock_client.get.call_count == 3

    @pytest.mark.anyio
    async def test_preserves_timeout_config(self) -> None:
        """httpx.Timeout(30, connect=5) is still passed to AsyncClient."""
        resp_ok = MagicMock(spec=httpx.Response)
        resp_ok.text = "ok"
        resp_ok.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=resp_ok)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "owlbear.memory.knowledge.intake.httpx.AsyncClient",
            return_value=mock_client,
        ) as mock_cls:
            await read_url("https://example.com")

        call_kwargs = mock_cls.call_args[1]
        timeout = call_kwargs["timeout"]
        assert isinstance(timeout, httpx.Timeout)
        assert timeout.read == 30
        assert timeout.connect == 5
