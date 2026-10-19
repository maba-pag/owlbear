"""The ``owlbear`` command (TD-257, TD-327): OwlBear on this Mac, and the project commands under one name.

With no command it starts OwlBear if it is stopped, else shows its status. ``owlbear-next``'s project commands run
under it unchanged. Each command imports what it needs only when it runs, so help stays fast, and the zsh
completion is a static file written at install, so TAB never starts Python (TD-263).
"""

import sys
from pathlib import Path  # noqa: TC003 - Cyclopts reads the annotations when it parses
from typing import Annotated, Literal

from cyclopts import App, Parameter

PROJECT = {
    "setup": "Check readiness, confirm the profile and register the chat server of a clone",
    "profile": "Detect a clone's project profile",
    "seed": "Seed a pre-approved one-task Change",
    "answer": "Write an answer into a Change's inbox",
    "show": "Print a Change's step, exit and open question",
    "data": "Show or set the shared settings repository",
    "home": "Show OwlBear's folder on this machine",
    "design-pack": "Show, install or update the pinned design pack",
    "backlog": "The improvement backlog",
}
DROPPED: list[str] = []  # what the environment scrub removed, for doctor

app = App(
    name="owlbear",
    help="OwlBear on this Mac: with no command it starts OwlBear, else shows its status.",
    version_flags=[],
    result_action="return_value",
)
for _name, _said in PROJECT.items():
    app.command(App(name=_name, help=f"{_said} (as owlbear-next {_name}; --repo PATH names the clone)"))


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


# Each command imports its module only when it runs, never for help or a project command.
@app.default
def default() -> int:
    """Start OwlBear running if it is stopped, else show its status."""
    from owlbear_delivery_next.machine_host import control  # noqa: PLC0415

    return control.status(say) if control.serve.running() else control.start(say)


@app.command
def start(*, paused: bool = False) -> int:
    """Start OwlBear in the background, running.

    Args:
        paused: Start paused until you press Resume.
    """
    from owlbear_delivery_next.machine_host import control  # noqa: PLC0415

    return control.start(say, paused=paused)


@app.command
def stop() -> int:
    """Stop OwlBear; running steps finish on their own."""
    from owlbear_delivery_next.machine_host import control  # noqa: PLC0415

    return control.stop(say)


@app.command
def restart(*, paused: bool = False) -> int:
    """Stop OwlBear, then start it running or paused as it was.

    Args:
        paused: Start paused until you press Resume, even if it ran.
    """
    from owlbear_delivery_next.machine_host import control  # noqa: PLC0415

    listed = control.projects()
    return control.stop(say) or control.start(say, paused=paused or bool(listed and listed["paused"]))


@app.command
def status(*, repo: Path | None = None) -> int:
    """OwlBear's address, pause and projects.

    Args:
        repo: A clone whose Changes to list.
    """
    if repo:
        return forward(["status", "--repo", str(repo)])
    from owlbear_delivery_next.machine_host import control  # noqa: PLC0415

    return control.status(say)


@app.command
def logs(*, lines: Annotated[int, Parameter(name=["--lines", "-n"])] = 40) -> int:
    """The end of OwlBear's log.

    Args:
        lines: How many lines to show.
    """
    from owlbear_delivery_next.machine_host import control  # noqa: PLC0415

    return control.logs(say, lines)


@app.command
def doctor() -> int:
    """Check git, gh and each project's readiness from OwlBear's environment."""
    from owlbear_delivery_next.machine_host import install as installer  # noqa: PLC0415

    return installer.doctor(say, DROPPED)


@app.command
def autostart(state: Literal["on", "off"], /) -> int:
    """Start OwlBear at login, or not.

    Args:
        state: on or off.
    """
    from owlbear_delivery_next.machine_host import control  # noqa: PLC0415

    return control.autostart(say, on=state == "on")


@app.command
def install() -> int:
    """Write the completion; ask before linking the command and adding the login item."""
    from owlbear_delivery_next.machine_host import install as installer  # noqa: PLC0415

    return installer.install(say, ask_tty, app)


@app.command
def uninstall() -> int:
    """Remove the command's link and the login item."""
    from owlbear_delivery_next.machine_host import install as installer  # noqa: PLC0415

    return installer.uninstall(say)


def main(argv: list[str] | None = None) -> int:
    """Run one ``owlbear`` command."""
    args = sys.argv[1:] if argv is None else argv
    if sys.platform != "darwin":
        sys.stderr.write("OwlBear runs on macOS only for now (TD-262)\n")
        return 2
    from owlbear_delivery_next.machine_host import environment  # noqa: PLC0415

    DROPPED[:] = environment.scrub()  # before anything else, so probes and the host it starts see the same environment
    if args and args[0] in PROJECT:
        return forward(args)
    return app(args) or 0  # help returns nothing
