"""DiagramService — async wrapper around the Kroki HTTP API."""

from __future__ import annotations

import httpx

SUPPORTED_TYPES = frozenset({"mermaid", "plantuml", "graphviz", "d2", "c4plantuml", "excalidraw"})
SUPPORTED_FORMATS = frozenset({"svg", "png"})
_SVG_ONLY_TYPES = frozenset({"excalidraw"})


class DiagramError(Exception):
    """Raised when Kroki returns a non-2xx response."""

    def __init__(self, *, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Kroki returned {status_code}: {body}")


class DiagramService:
    """Thin async client for the Kroki diagram rendering API.

    Args:
        server_url: Base URL of the Kroki instance. Trailing slash is stripped.
    """

    def __init__(self, server_url: str = "https://kroki.io") -> None:
        self._server_url = server_url.rstrip("/")

    async def generate(
        self,
        diagram_type: str,
        source: str,
        output_format: str = "svg",
    ) -> bytes:
        """Render *source* via Kroki and return the raw image/SVG bytes.

        Raises:
            ValueError: If *diagram_type*, *output_format*, or *source* is invalid.
            DiagramError: If Kroki returns a non-2xx status.
        """
        if diagram_type not in SUPPORTED_TYPES:
            msg = f"Unsupported diagram_type: {diagram_type!r}"
            raise ValueError(msg)
        if output_format not in SUPPORTED_FORMATS:
            msg = f"Unsupported output_format: {output_format!r}"
            raise ValueError(msg)
        if diagram_type in _SVG_ONLY_TYPES and output_format != "svg":
            msg = "excalidraw only supports svg output"
            raise ValueError(msg)
        if not source or not source.strip():
            msg = "source must not be empty"
            raise ValueError(msg)

        url = f"{self._server_url}/{diagram_type}/{output_format}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=5)) as client:
            resp = await client.post(
                url,
                content=source,
                headers={"Content-Type": "text/plain"},
            )

        if not resp.is_success:
            raise DiagramError(status_code=resp.status_code, body=resp.text)

        return resp.content
