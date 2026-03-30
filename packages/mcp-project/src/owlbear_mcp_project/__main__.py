"""Entry point for ``python -m owlbear_mcp_project``."""

from __future__ import annotations

from owlbear_mcp_project.server import mcp

if __name__ == "__main__":
    mcp.run()
