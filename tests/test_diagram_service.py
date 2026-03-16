"""Tests for DiagramService — Kroki HTTP API wrapper.

Covers: happy-path generation (mocked httpx POST), input validation guards,
error handling for Kroki failure responses, and httpx client configuration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from owlbear.tools.diagram.service import SUPPORTED_TYPES, DiagramError, DiagramService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODULE = "owlbear.tools.diagram.service"
DEFAULT_URL = "https://kroki.io"

DIAGRAM_TYPES = ("mermaid", "plantuml", "graphviz", "d2", "c4plantuml", "excalidraw")
OUTPUT_FORMATS = ("svg", "png")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    *,
    content: bytes = b"<svg>ok</svg>",
    status_code: int = 200,
) -> httpx.Response:
    """Build a real httpx.Response with the given binary payload."""
    return httpx.Response(
        status_code=status_code,
        content=content,
        request=httpx.Request("POST", f"{DEFAULT_URL}/mermaid/svg"),
    )


def _make_client(response: httpx.Response) -> AsyncMock:
    """Build a mock httpx.AsyncClient that returns *response* for POST."""
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# TestGenerate — happy-path generation (mocked httpx POST)
# ---------------------------------------------------------------------------


class TestGenerate:
    """DiagramService.generate sends correct POST requests and returns bytes."""

    @pytest.mark.asyncio
    async def test_generate_mermaid_svg(self) -> None:
        svg_bytes = b"<svg>mermaid</svg>"
        resp = _make_response(content=svg_bytes)
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            result = await svc.generate("mermaid", "graph TD; A-->B", "svg")

        assert result == svg_bytes
        client.post.assert_awaited_once()
        call_args = client.post.call_args
        assert call_args[0][0] == f"{DEFAULT_URL}/mermaid/svg"

    @pytest.mark.asyncio
    async def test_generate_plantuml_png(self) -> None:
        png_bytes = b"\x89PNGfake"
        resp = _make_response(content=png_bytes)
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            result = await svc.generate("plantuml", "@startuml\nA->B\n@enduml", "png")

        assert result == png_bytes
        call_args = client.post.call_args
        assert call_args[0][0] == f"{DEFAULT_URL}/plantuml/png"

    @pytest.mark.asyncio
    async def test_generate_graphviz(self) -> None:
        svg_bytes = b"<svg>graphviz</svg>"
        resp = _make_response(content=svg_bytes)
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            result = await svc.generate("graphviz", "digraph G { A -> B }", "svg")

        assert result == svg_bytes
        call_args = client.post.call_args
        assert call_args[0][0] == f"{DEFAULT_URL}/graphviz/svg"

    @pytest.mark.asyncio
    async def test_generate_d2(self) -> None:
        svg_bytes = b"<svg>d2</svg>"
        resp = _make_response(content=svg_bytes)
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            result = await svc.generate("d2", "x -> y", "svg")

        assert result == svg_bytes
        call_args = client.post.call_args
        assert call_args[0][0] == f"{DEFAULT_URL}/d2/svg"

    @pytest.mark.asyncio
    async def test_generate_c4plantuml(self) -> None:
        svg_bytes = b"<svg>c4</svg>"
        resp = _make_response(content=svg_bytes)
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            result = await svc.generate("c4plantuml", "C4Context {...}", "svg")

        assert result == svg_bytes
        call_args = client.post.call_args
        assert call_args[0][0] == f"{DEFAULT_URL}/c4plantuml/svg"

    @pytest.mark.asyncio
    async def test_request_body_is_plain_text(self) -> None:
        """POST body is the raw diagram source, Content-Type is text/plain."""
        source = "graph TD; A-->B"
        resp = _make_response()
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            await svc.generate("mermaid", source, "svg")

        call_kwargs = client.post.call_args
        assert call_kwargs.kwargs.get("content") == source
        headers = call_kwargs.kwargs.get("headers", {})
        assert headers.get("Content-Type") == "text/plain"

    @pytest.mark.asyncio
    async def test_default_format_is_svg(self) -> None:
        resp = _make_response()
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            await svc.generate("mermaid", "graph TD; A-->B")

        call_args = client.post.call_args
        assert call_args[0][0].endswith("/svg")

    @pytest.mark.asyncio
    async def test_custom_server_url(self) -> None:
        custom_url = "https://custom.example.com"
        resp = _make_response()
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService(server_url=custom_url)
            await svc.generate("mermaid", "graph TD; A-->B", "svg")

        call_args = client.post.call_args
        assert call_args[0][0] == f"{custom_url}/mermaid/svg"

    @pytest.mark.asyncio
    async def test_trailing_slash_stripped(self) -> None:
        resp = _make_response()
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService(server_url="https://kroki.io/")
            await svc.generate("mermaid", "graph TD; A-->B", "svg")

        call_args = client.post.call_args
        assert call_args[0][0] == f"{DEFAULT_URL}/mermaid/svg"


# ---------------------------------------------------------------------------
# TestValidation — input guards (no HTTP call)
# ---------------------------------------------------------------------------


class TestValidation:
    """Input validation rejects bad diagram_type, output_format, and source."""

    @pytest.mark.asyncio
    async def test_unknown_diagram_type_raises_value_error(self) -> None:
        svc = DiagramService()
        with pytest.raises(ValueError, match="diagram_type"):
            await svc.generate("unknown", "some source")

    @pytest.mark.asyncio
    async def test_unknown_output_format_raises_value_error(self) -> None:
        svc = DiagramService()
        with pytest.raises(ValueError, match="output_format"):
            await svc.generate("mermaid", "some source", "pdf")

    @pytest.mark.asyncio
    async def test_empty_source_raises_value_error(self) -> None:
        svc = DiagramService()
        with pytest.raises(ValueError, match="source"):
            await svc.generate("mermaid", "")

    @pytest.mark.asyncio
    async def test_whitespace_only_source_raises_value_error(self) -> None:
        svc = DiagramService()
        with pytest.raises(ValueError, match="source"):
            await svc.generate("mermaid", "   ")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("diagram_type", DIAGRAM_TYPES)
    async def test_known_types_accepted(self, diagram_type: str) -> None:
        resp = _make_response()
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            result = await svc.generate(diagram_type, "source code")

        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("output_format", OUTPUT_FORMATS)
    async def test_known_formats_accepted(self, output_format: str) -> None:
        resp = _make_response()
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            result = await svc.generate("mermaid", "source code", output_format)

        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# TestErrorHandling — Kroki failure responses
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """DiagramError raised on non-2xx; transport errors propagate unwrapped."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 500])
    async def test_non_2xx_raises_diagram_error_with_status_and_body(
        self,
        status_code: int,
    ) -> None:
        body = b"Bad diagram syntax"
        resp = _make_response(content=body, status_code=status_code)
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            with pytest.raises(DiagramError) as exc_info:
                await svc.generate("mermaid", "bad source", "svg")

        assert exc_info.value.status_code == status_code
        assert "Bad diagram syntax" in exc_info.value.body

    @pytest.mark.asyncio
    async def test_connect_error_propagates(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            with pytest.raises(httpx.ConnectError):
                await svc.generate("mermaid", "source", "svg")

    @pytest.mark.asyncio
    async def test_timeout_error_propagates(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            with pytest.raises(httpx.TimeoutException):
                await svc.generate("mermaid", "source", "svg")

    @pytest.mark.asyncio
    async def test_diagram_error_attributes(self) -> None:
        """DiagramError stores status_code and body as attributes."""
        err = DiagramError(status_code=422, body="Unprocessable")
        assert err.status_code == 422
        assert err.body == "Unprocessable"


# ---------------------------------------------------------------------------
# TestHttpxConfig — client construction
# ---------------------------------------------------------------------------


class TestHttpxConfig:
    """httpx.AsyncClient is created with the correct timeout."""

    @pytest.mark.asyncio
    async def test_timeout_configuration(self) -> None:
        resp = _make_response()
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client) as mock_cls:
            svc = DiagramService()
            await svc.generate("mermaid", "graph TD; A-->B", "svg")

        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args.kwargs
        timeout = call_kwargs.get("timeout")
        assert isinstance(timeout, httpx.Timeout)
        assert timeout.read == 30
        assert timeout.connect == 5


# ---------------------------------------------------------------------------
# Package exports — task #620
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TestFromAC_ExcalidrawSupport — excalidraw in DiagramService (#836)
# ---------------------------------------------------------------------------


class TestFromAC_ExcalidrawSupport:  # noqa: N801
    """Excalidraw support: SVG generation, PNG rejection, SUPPORTED_TYPES membership."""

    @pytest.mark.asyncio
    async def test_generate_excalidraw_svg(self) -> None:
        """generate('excalidraw', ..., 'svg') POSTs to /excalidraw/svg and returns bytes."""
        svg_bytes = b"<svg>excalidraw</svg>"
        resp = _make_response(content=svg_bytes)
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            svc = DiagramService()
            result = await svc.generate("excalidraw", '{"type":"excalidraw","elements":[]}', "svg")

        assert result == svg_bytes
        client.post.assert_awaited_once()
        call_args = client.post.call_args
        assert call_args[0][0] == f"{DEFAULT_URL}/excalidraw/svg"

    @pytest.mark.asyncio
    async def test_excalidraw_png_raises_value_error(self) -> None:
        """generate('excalidraw', ..., 'png') raises ValueError mentioning SVG-only."""
        svc = DiagramService()
        with pytest.raises(ValueError, match="only supports svg"):
            await svc.generate(
                "excalidraw",
                '{"type":"excalidraw","elements":[]}',
                "png",
            )

    def test_excalidraw_in_supported_types(self) -> None:
        """'excalidraw' must be a member of SUPPORTED_TYPES."""
        assert "excalidraw" in SUPPORTED_TYPES


# ---------------------------------------------------------------------------
# TestFromAC_SvgOnlyTypes — _SVG_ONLY_TYPES constant contract (#833)
# ---------------------------------------------------------------------------


class TestFromAC_SvgOnlyTypes:  # noqa: N801
    """_SVG_ONLY_TYPES module-level constant: existence, type, content, consistency."""

    def test_svg_only_types_constant_exists(self) -> None:
        """_SVG_ONLY_TYPES must be importable from the service module."""
        import owlbear.tools.diagram.service as svc

        assert hasattr(svc, "_SVG_ONLY_TYPES"), "_SVG_ONLY_TYPES not found in service module"

    def test_svg_only_types_is_frozenset(self) -> None:
        """_SVG_ONLY_TYPES must be a frozenset (immutable constant)."""
        from owlbear.tools.diagram.service import _SVG_ONLY_TYPES

        assert isinstance(_SVG_ONLY_TYPES, frozenset)

    def test_svg_only_types_contains_excalidraw(self) -> None:
        """'excalidraw' must be in _SVG_ONLY_TYPES."""
        from owlbear.tools.diagram.service import _SVG_ONLY_TYPES

        assert "excalidraw" in _SVG_ONLY_TYPES

    def test_svg_only_types_subset_of_supported_types(self) -> None:
        """Every SVG-only type must also be a valid SUPPORTED_TYPES member."""
        from owlbear.tools.diagram.service import _SVG_ONLY_TYPES

        assert _SVG_ONLY_TYPES <= SUPPORTED_TYPES, (
            f"SVG-only types not in SUPPORTED_TYPES: {_SVG_ONLY_TYPES - SUPPORTED_TYPES}"
        )


class TestPackageExports:
    """DiagramService and DiagramError should be importable from the package __init__."""

    def test_diagram_service_exported(self) -> None:
        """DiagramService should be importable from owlbear.tools.diagram."""
        from owlbear.tools.diagram import DiagramService as Exported

        assert Exported is DiagramService

    def test_diagram_error_exported(self) -> None:
        """DiagramError should be importable from owlbear.tools.diagram."""
        from owlbear.tools.diagram import DiagramError as Exported

        assert Exported is DiagramError
