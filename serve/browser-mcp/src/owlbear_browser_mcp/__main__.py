"""Entry point for ``python -m owlbear_browser_mcp``."""

from __future__ import annotations

from owlbear_browser_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
