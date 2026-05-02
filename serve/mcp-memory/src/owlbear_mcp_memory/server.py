"""OwlBear MCP memory server with markdown file-engine lifespan context."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from owlbear_mcp_memory.engine import MemoryEngine

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    "AppContext",
    "_apply_tool_exclusions",  # noqa: F822 — defined in tools.py
    "app_lifespan",
    "approve_entry",  # noqa: F822 — defined in tools.py
    "delete_entry",  # noqa: F822 — defined in tools.py
    "mcp",
    "query_memory",  # noqa: F822 — defined in tools.py
    "store_learning",  # noqa: F822 — defined in tools.py
    "update_entry",  # noqa: F822 — defined in tools.py
]

_DEFAULT_MEMORY_DIR = ".owlbear/memory"


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    engine: MemoryEngine
    caller: str


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:  # pragma: no cover
    """Initialize and expose the markdown file engine for memory tools."""
    memory_dir = Path(os.environ.get("OWLBEAR_MEMORY_DIR", _DEFAULT_MEMORY_DIR))
    caller = os.environ.get("OWLBEAR_MEMORY_CALLER", "unknown")
    engine = MemoryEngine(memory_dir=memory_dir)
    yield AppContext(engine=engine, caller=caller)


mcp = FastMCP("owlbear-memory", lifespan=app_lifespan)

# Import for tool registration side effects.
from owlbear_mcp_memory import tools as _tools  # noqa: E402,F401
