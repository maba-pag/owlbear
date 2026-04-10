"""OwlBear MCP browser server — exposes browser content fetching via MCP."""

from owlbear_mcp_browser import server
from owlbear_mcp_browser.server import mcp_app

__all__ = ["mcp_app", "server"]
