"""Entry point for ``python -m owlbear_mcp_browser``."""

from __future__ import annotations

from owlbear_mcp_browser.server import _mcp

if __name__ == "__main__":
    _mcp.run()
