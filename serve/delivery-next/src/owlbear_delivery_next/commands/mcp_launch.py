"""OwlBear's other chat servers, run from the installed version (D-01M5Q5GKHX7BJTXPEW2MHGS9E0, "move all").

``python -m owlbear_delivery_next serve memory`` (or ``knowledge``, ``browser``) runs that package's MCP server in
this process. The dispatcher has pinned it to its version's own folder and taken a lease first, so a chat keeps the
server it started with while OwlBear updates beneath it, and no update removes that code. The servers are named,
not imported: Delivery depends on none of them. Their working folder and environment are the client's.
"""

from __future__ import annotations

import importlib.util
import runpy
import sys

SERVERS = {"memory": "owlbear_memory_mcp", "knowledge": "owlbear_knowledge_mcp", "browser": "owlbear_browser_mcp"}
USAGE = f"usage: python -m owlbear_delivery_next serve {{{','.join(SERVERS)}}}"


def main(argv: list[str]) -> int:
    """Run the named server until its client ends it; 2 for a wrong name, or a server this install lacks."""
    if argv == ["--help"]:
        print(USAGE)  # noqa: T201 - asked for; no client reads it
        return 0
    if len(argv) != 1 or argv[0] not in SERVERS:
        print(f"{USAGE}: {' '.join(argv) or 'no server'} is not one", file=sys.stderr)  # noqa: T201
        return 2
    module = SERVERS[argv[0]]
    if importlib.util.find_spec(module) is None:
        lacking = f"{module} is not installed in {sys.prefix}: this OwlBear install is incomplete"
        print(lacking, file=sys.stderr)  # noqa: T201
        return 2
    sys.argv = [sys.argv[0]]  # the servers read no arguments
    runpy.run_module(module, run_name="__main__", alter_sys=True)  # an import error inside it is its own, raised
    return 0
