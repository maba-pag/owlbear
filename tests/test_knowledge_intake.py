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

        p = Path(str(tmp_path)) / "sample.txt"
        p.write_text("hello world", encoding="utf-8")

        result = await read_file(p)

        assert isinstance(result, IntakeResult)
        assert result.content == "hello world"

    @pytest.mark.anyio
    async def test_source_is_file_path(self, tmp_path: object) -> None:
        from pathlib import Path

        p = Path(str(tmp_path)) / "data.md"
        p.write_text("# Title", encoding="utf-8")

        result = await read_file(p)

        assert result.source == str(p)

    @pytest.mark.anyio
    async def test_metadata_source_type_is_file(self, tmp_path: object) -> None:
        from pathlib import Path

        p = Path(str(tmp_path)) / "info.txt"
        p.write_text("content", encoding="utf-8")

        result = await read_file(p)

        assert result.metadata["source_type"] == "file"

    @pytest.mark.anyio
    async def test_metadata_has_fetched_at(self, tmp_path: object) -> None:
        from pathlib import Path

        p = Path(str(tmp_path)) / "ts.txt"
        p.write_text("time", encoding="utf-8")

        result = await read_file(p)

        assert "fetched_at" in result.metadata
        # Verify it's a valid ISO timestamp
        datetime.datetime.fromisoformat(result.metadata["fetched_at"])

    @pytest.mark.anyio
    async def test_file_not_found_raises(self) -> None:
        from pathlib import Path

        with pytest.raises(FileNotFoundError):
            await read_file(Path("/nonexistent/path/file.txt"))

    @pytest.mark.anyio
    async def test_accepts_str_path(self, tmp_path: object) -> None:
        from pathlib import Path

        p = Path(str(tmp_path)) / "str_path.txt"
        p.write_text("via string", encoding="utf-8")

        result = await read_file(str(p))

        assert result.content == "via string"


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
