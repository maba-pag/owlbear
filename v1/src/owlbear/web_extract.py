"""Markdown extraction helper using trafilatura.

This is a **leaf module** — it must not import from ``owlbear.core``,
``owlbear.tools``, ``owlbear.memory``, or ``owlbear.agents``.
"""

from __future__ import annotations

__all__ = ["extract_markdown"]

# Lazy sentinel: trafilatura is imported on the first extract_markdown call, not
# at module load time.  Tests that need to patch the module attribute (e.g.
# @patch("owlbear.web_extract.trafilatura")) replace this directly.
trafilatura = None  # type: ignore[assignment]


def extract_markdown(html: str, url: str | None = None) -> str:
    """Extract markdown from an HTML string via trafilatura.

    Args:
        html: The raw HTML content to extract from.
        url: Optional source URL forwarded to trafilatura for link resolution.

    Returns:
        Extracted markdown string, or empty string if extraction fails or
        produces no content.

    Raises:
        ImportError: If trafilatura is not installed, with an actionable
            install hint.
    """
    # Capture the module-level attribute — patchable via @patch("owlbear.web_extract.trafilatura").
    _traf = trafilatura
    if _traf is None:
        # Not installed at module load time.  Attempt a lazy import so that
        # builtins.__import__ denial tests can intercept this call.
        try:
            import trafilatura as _traf  # noqa: PLC0415
        except ImportError:
            msg = (
                "trafilatura is required for extract_markdown. "
                "Install it with: uv pip install 'owlbear[search]'"
            )
            raise ImportError(msg) from None

    try:
        result = _traf.extract(  # type: ignore[union-attr]
            html,
            output_format="markdown",
            include_links=True,
            url=url,
        )
    except Exception:  # noqa: BLE001
        return ""
    else:
        return result or ""
