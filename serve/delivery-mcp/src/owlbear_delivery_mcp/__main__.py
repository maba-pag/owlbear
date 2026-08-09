"""Entry point for ``python -m owlbear_delivery_mcp``."""

from __future__ import annotations

from owlbear_delivery_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
