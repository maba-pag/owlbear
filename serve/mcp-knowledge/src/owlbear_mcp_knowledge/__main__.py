"""Entry point for the owlbear-mcp-knowledge MCP server."""

from __future__ import annotations

from owlbear_mcp_knowledge.server import mcp

if __name__ == "__main__":
    mcp.run()
