"""The ``owlbear`` command (TD-257, TD-272): OwlBear on this Mac, and the project commands under one name.

With no command it starts OwlBear if it is stopped, else shows its status. ``owlbear-next``'s project commands run
under it unchanged. Each command imports what it needs only when it runs, so help and completion stay fast.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT = {
    "setup": "check readiness, confirm the profile and register the chat server of a clone",
    "profile": "detect a clone's project profile",
    "seed": "seed a pre-approved one-task Change",
    "answer": "write an answer into a Change's inbox",
    "show": "print a Change's step, exit and open question",
    "data": "show or set the shared settings repository",
    "home": "show OwlBear's folder on this machine",
    "design-pack": "show, install or update the pinned design pack",
    "backlog": "the improvement backlog",
}


def parser() -> argparse.ArgumentParser:
    """Every command, for help and the zsh completion."""
    p = argparse.ArgumentParser(
        prog="owlbear", description="OwlBear on this Mac: with no command it starts OwlBear, else shows its status."
    )
    sub = p.add_subparsers(dest="command")
    sub.add_parser("start", help="start OwlBear in the background, paused until you press Resume")
    sub.add_parser("stop", help="stop OwlBear; running steps finish on their own")
    sub.add_parser("restart", help="stop OwlBear, then start it")
    shown = sub.add_parser("status", help="OwlBear's address, pause and projects; --repo: one clone's Changes")
    shown.add_argument("--repo", type=Path, help="a clone whose Changes to list")
    logs = sub.add_parser("logs", help="the end of OwlBear's log")
    logs.add_argument("-n", "--lines", type=int, default=40)
    sub.add_parser("doctor", help="check git, gh and each project's readiness from OwlBear's environment")
    auto = sub.add_parser("autostart", help="start OwlBear at login, or not")
    auto.add_argument("state", choices=("on", "off"))
    sub.add_parser("install", help="write the completion; ask before linking the command and adding the login item")
    sub.add_parser("uninstall", help="remove the command's link and the login item")
    for name, said in PROJECT.items():
        sub.add_parser(name, help=f"{said} (as owlbear-next {name}; --repo PATH names the clone)", add_help=False)
    return p


def forward(argv: list[str]) -> int:
    """Run a project command as ``owlbear-next`` does, with ``--repo`` moved before the command it follows."""
    from owlbear_delivery_next.commands import cli  # noqa: PLC0415 - only a project command needs it

    rest, repo = [], []
    words = iter(argv)
    for word in words:
        if word == "--repo":
            repo = ["--repo", next(words, "")]
        elif word.startswith("--repo="):
            repo = ["--repo", word.removeprefix("--repo=")]
        else:
            rest.append(word)
    return cli.main([*repo, *rest])


def ask_tty(question: str) -> bool:
    """A yes or no from the owner in the terminal; no when nobody can answer."""
    if not sys.stdin.isatty():
        return False
    return input(f"{question} [y/N] ").strip().lower() in {"y", "yes"}


def say(text: str) -> None:
    """One line to the terminal."""
    sys.stdout.write(text + "\n")


def run(a: argparse.Namespace, dropped: list[str]) -> int:
    """One machine command, importing its module only now."""
    from owlbear_delivery_next.machine_host import control, install  # noqa: PLC0415 - not for help or a project

    commands = {
        None: lambda: control.status(say) if control.serve.running() else control.start(say),
        "start": lambda: control.start(say),
        "stop": lambda: control.stop(say),
        "status": lambda: control.status(say),
        "restart": lambda: control.stop(say) or control.start(say),
        "logs": lambda: control.logs(say, a.lines),
        "autostart": lambda: control.autostart(say, on=a.state == "on"),
        "install": lambda: install.install(say, ask_tty, parser()),
        "uninstall": lambda: install.uninstall(say),
        "doctor": lambda: install.doctor(say, dropped),
    }
    return commands[a.command]()


def main(argv: list[str] | None = None) -> int:
    """Run one ``owlbear`` command."""
    args = sys.argv[1:] if argv is None else argv
    if sys.platform != "darwin":
        sys.stderr.write("OwlBear runs on macOS only for now (TD-262)\n")
        return 2
    from owlbear_delivery_next.machine_host import environment  # noqa: PLC0415

    dropped = environment.scrub()  # before anything else, so probes and the host it starts see the same environment
    if args and args[0] in PROJECT:
        return forward(args)
    a = parser().parse_args(args)
    if a.command == "status" and a.repo:
        return forward(["status", "--repo", str(a.repo)])
    return run(a, dropped)
