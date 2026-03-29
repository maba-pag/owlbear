"""Entry point for ``python -m owlbear_mcp_kanban``."""

from __future__ import annotations

from owlbear_mcp_kanban.server import mcp

if __name__ == "__main__":
    mcp.run()
