"""The one entry of every Delivery process (TD-173): it reads the command, then imports only what that command needs.

``python -m owlbear_delivery_next run <change> --repo PATH`` starts a step runner, ``mcp --repo PATH`` the chat
server and ``step-mcp --inbox PATH`` a window step's relay; anything else is a command of the owner's CLI, such as
``--repo PATH host``.
"""

from __future__ import annotations

import sys
from importlib import import_module

PROCESSES = {"run": "runner", "mcp": "mcp_server", "step-mcp": "step_mcp"}  # started by Delivery itself


def main(argv: list[str] | None = None) -> int:
    """Run one command; a process command gets the arguments after its name."""
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in PROCESSES:
        name, rest = PROCESSES[args[0]], args[1:]
    else:
        name, rest = "cli", args
    return import_module(f"owlbear_delivery_next.commands.{name}").main(rest) or 0
