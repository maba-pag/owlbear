"""Entry point for the owlbear-knowledge-mcp MCP server."""

from __future__ import annotations

from owlbear_knowledge_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
