"""Entry point for ``python -m owlbear_mcp_browser``."""

from __future__ import annotations

from owlbear_mcp_browser.server import mcp

if __name__ == "__main__":
    mcp.run()
