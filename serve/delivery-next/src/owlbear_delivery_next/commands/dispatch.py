"""The one entry of every Delivery process (TD-173): it reads the command, then imports only what that command needs.

``python -m owlbear_delivery_next run <change> --repo PATH`` starts a step runner, ``mcp --repo PATH`` the chat
server, ``step-mcp --inbox PATH`` a window step's relay and ``machine`` the machine host (TD-242); anything else is
a command of the owner's CLI, such as ``--repo PATH status``.
"""

from __future__ import annotations

import sys
from importlib import import_module

PROCESSES = {  # started by Delivery itself
    "run": "commands.runner",
    "mcp": "commands.mcp_server",
    "step-mcp": "commands.step_mcp",
    "machine": "machine_host.serve",
    "selfcheck": "machine_host.selfcheck",  # a new version's check before it takes over (self-update §5.1)
}


def main(argv: list[str] | None = None) -> int:
    """Run one command; a process command gets the arguments after its name.

    Each process holds a lease on its installed version while it runs, so no update removes its code (§3).
    """
    from owlbear_delivery_next.local_system import leases  # noqa: PLC0415 - before the command's own imports

    leases.take()
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in PROCESSES:
        name, rest = PROCESSES[args[0]], args[1:]
    else:
        name, rest = "commands.cli", args
    return import_module(f"owlbear_delivery_next.{name}").main(rest) or 0
