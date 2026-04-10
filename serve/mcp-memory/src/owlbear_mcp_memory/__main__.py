"""Entry point for ``python -m owlbear_mcp_memory``."""

from __future__ import annotations

from owlbear_mcp_memory.server import mcp

if __name__ == "__main__":
    mcp.run()
