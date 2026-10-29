"""The project commands, defined once (#679): ``owlbear-next`` parses with them and ``owlbear`` lists them.

Each command only parses: it returns the ``argparse.Namespace`` that :func:`commands.cli.run` runs, with the
argparse names and defaults the handlers read. ``--repo PATH`` comes before the command and names the clone; the
current folder by default. Loading this module imports no other OwlBear module, so ``owlbear --help`` and its
completion stay fast (TD-263); a check that needs one imports it when the option is parsed.
"""

import sys
from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, NoReturn

from cyclopts import App, Group, Parameter, validators
from cyclopts.help import DefaultFormatter

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions


class _Usage(DefaultFormatter):
    """Cyclopts' help with argparse's lower-case ``usage:`` line."""

    def render_usage(self, console: Console, options: ConsoleOptions, usage: object) -> None:  # noqa: ARG002
        """Print ``usage: …``."""
        from rich.text import Text  # noqa: PLC0415 - only help prints it

        if usage:
            plain = usage.plain if isinstance(usage, Text) else str(usage)
            console.print(Text("usage: " + plain.removeprefix("Usage:").strip()))


_LAST = Parameter(allow_repeating=True)  # a repeated option keeps its last value, as argparse did


def _app(name: str | None = None, said: str | None = None) -> App:
    group = App(
        name=name,
        help=said,
        version_flags=[],
        result_action="return_value",
        help_formatter=_Usage(),
        default_parameter=_LAST,
    )
    group.default(_missing)
    return group


def _missing() -> NoReturn:
    """A group given no command: refused as argparse refused it."""
    _refuse("a command is required")


def _refuse(said: str) -> NoReturn:
    """A usage error: said on stderr, exit 2, before anything runs."""
    sys.stderr.write(f"owlbear-next: error: {said}\n")
    sys.exit(2)


def _pairs(values: list[str] | None) -> list[tuple[str, ...]]:
    """``KEY=VALUE`` per value, split at the first ``=`` as argparse's converter did."""
    return [tuple(v.split("=", 1)) for v in values or []]


def _among(value: str, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        msg = f"invalid choice: {value!r} (choose from {', '.join(allowed)})"
        raise ValueError(msg)


def _call(_type: object, value: str) -> None:
    from owlbear_delivery_next.improvement import cases  # noqa: PLC0415 - only a parsed --call needs it

    _among(value, cases.CALLS)


def _call_or_none(_type: object, value: str) -> None:
    from owlbear_delivery_next.improvement import cases  # noqa: PLC0415 - only a parsed --call needs it

    _among(value, ("", *cases.CALLS))


def _stage(_type: object, value: str) -> None:
    from owlbear_delivery_next.improvement import cases  # noqa: PLC0415 - only a parsed stage needs it

    _among(value, (*cases.STAGES, "removed"))


app = _app("owlbear-next", "OwlBear's commands for one project's clone.")
backlog = _app("backlog", "The improvement backlog: issues in the shared repository (TD-84, TD-103).")
cases = _app("cases", "The Spotter cases: stages, versions, replays (Improvement design §4).")
improvement = _app("improvement", "Improvement's marked assumptions and Retro.")
retro = _app("retro", "Retro: judge a finished Change or chat (Improvement design §5).")
for _group in (backlog, cases, improvement):
    app.command(_group)
improvement.command(retro)
UNIT = Group("Unit", validator=validators.LimitedChoice(1, 1))  # exactly one, as argparse's required group


@app.meta.default
def _launch(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    repo: Annotated[Path | None, _LAST] = None,
) -> Namespace | None:
    """Parse one command; help returns nothing.

    Args:
        tokens: The command and its arguments.
        repo: The clone the command acts on; the current folder by default.
    """
    parsed = app(tokens)
    if parsed is not None:
        parsed.repo = repo or Path.cwd()
    return parsed


@app.command
def status() -> Namespace:
    """Print every Change's status line and next action."""
    return Namespace(command="status")


@app.command
def setup(
    *,
    yes: bool = False,
    local_files: Literal["yes", "no", "ask"] = "ask",
    confirm: list[str] | None = None,
    folder: str = "",
) -> Namespace:
    """Check readiness, confirm the profile and register the chat server of a clone.

    Args:
        yes: Confirm the profile (only the profile).
        local_files: Write .mcp.json and .vscode/settings.json.
        confirm: KEY=VALUE.
        folder: The project's folder in the shared settings when its name is taken.
    """
    return Namespace(command="setup", yes=yes, local_files=local_files, confirm=_pairs(confirm), folder=folder)


@app.command
def profile(
    *,
    confirm: list[str] | None = None,
    role: list[str] | None = None,
) -> Namespace:
    """Detect the project profile; --confirm KEY=VALUE records the owner's answer.

    Args:
        confirm: KEY=VALUE.
        role: ROLE=MODEL:EFFORT model override.
    """
    from owlbear_delivery_next.settings import roles  # noqa: PLC0415 - only a parsed --role needs it

    try:
        overrides = [roles.parse(r) for r in role or []]
    except ValueError as exc:
        _refuse(f"argument --role: {exc}")
    return Namespace(command="profile", confirm=_pairs(confirm), role=overrides)


@app.command
def seed(  # noqa: PLR0913 - one parameter per option
    change: str,
    /,
    *,
    title: str,
    outcome: str,
    criterion: list[str] | None = None,
    scope: list[str] | None = None,
    check: list[str] | None = None,
    install: list[str] | None = None,
    person_check: list[str] | None = None,
    target: str = "main",
) -> Namespace:
    """Seed a pre-approved one-task Change and a minimal profile.

    Args:
        change: The Change's slug.
        title: The task's title.
        outcome: The brief's outcome.
        criterion: An acceptance criterion.
        scope: A scope line of the brief and the task.
        check: A check of the task.
        install: DIR=CMD.
        person_check: ID=STEPS.
        target: The branch the Change merges into.
    """
    return Namespace(
        command="seed",
        change=change,
        title=title,
        outcome=outcome,
        criterion=criterion or [],
        scope=scope or [],
        check=check or [],
        install=_pairs(install),
        person_check=_pairs(person_check),
        target=target,
    )


@app.command
def answer(  # noqa: PLR0913 - one parameter per option
    change: str,
    /,
    *,
    question: str,
    option: str | None = None,
    text: str = "",
    kind: Literal["event", "clarification", "brief-change"] | None = None,
    statement: str = "",
    confirmed: bool = False,
    round_: Annotated[int | None, Parameter(name="--round")] = None,
    head: str = "",
    pack: str = "",
    finding: list[str] | None = None,
    task: list[str] | None = None,
    attempt: int | None = None,
) -> Namespace:
    """Write an answer into the Change inbox.

    Args:
        change: The Change's slug.
        question: The question's id.
        option: The chosen option.
        text: The answer's text.
        kind: A worker's question's class.
        statement: A clarification's intent the owner confirmed when read back.
        confirmed: The owner confirmed the statement as read back.
        round_: A visual decision: the round `show` printed.
        head: A visual decision or a final retry: the head `show` printed.
        pack: A visual decision: the design pack `show` printed.
        finding: A visual finding to send back.
        task: A final retry's plan task to rebuild.
        attempt: A final retry: the attempt `show` printed.
    """
    return Namespace(
        command="answer",
        change=change,
        question=question,
        option=option,
        text=text,
        kind=kind,
        statement=statement,
        confirmed=confirmed,
        round=round_,
        head=head,
        pack=pack,
        findings=finding or [],
        tasks=task or [],
        attempt=attempt,
    )


@app.command
def show(change: str, /) -> Namespace:
    """Print the Change's step, exit and open question.

    Args:
        change: The Change's slug.
    """
    return Namespace(command="show", change=change)


@app.command
def data(target: str | None = None, /) -> Namespace:
    """Show or set the shared settings repository (TD-57); `owlbear data --move [DEST]` moves it.

    Args:
        target: A clone address to clone or adopt, or a checkout's folder to use.
    """
    return Namespace(command="data", target=target)


@app.command
def home() -> Namespace:
    """Show OwlBear's folder on this machine (TD-198)."""
    return Namespace(command="home")


@app.command
def prepare() -> Namespace:
    """Before a reboot: bind the clone's store id and fence the offline move."""
    return Namespace(command="prepare")


@app.command
def finish() -> Namespace:
    """After a reboot: prove the preparation and move the store; the source stays in place."""
    return Namespace(command="finish")


@app.command
def design_pack(  # noqa: PLR0913 - one parameter per option
    *,
    install: bool = False,
    check: bool = False,
    diff: Path | None = None,
    to: str | None = None,
    golden: bool = False,
    replay: bool = False,
) -> Namespace:
    """Show, install or update the pinned design pack (TD-76).

    Args:
        install: Download and verify what is missing.
        check: Count upstream releases since the pinned one.
        diff: CLONE: rules and skill files changed, from an upstream clone.
        to: TAG: the candidate tag --diff compares with.
        golden: Run the engine and the in-page bundle on the golden pages.
        replay: Rerun the design judge on decided rounds (costs requests).
    """
    if bool(diff) != bool(to):
        _refuse("--diff and --to go together")
    return Namespace(
        command="design-pack", install=install, check=check, diff=diff, to=to, golden=golden, replay=replay
    )


@backlog.command
def add(
    *,
    title: str,
    text: str = "",
    source: Literal["owner", "spotter", "retro", "assistant", "review", "run"] = "assistant",
    evidence: list[str] | None = None,
) -> Namespace:
    """Add a finding; a repeat counts up its entry.

    Args:
        title: The finding's title.
        text: The finding's text.
        source: Who found it.
        evidence: A Change, step, session, path or URL.
    """
    return Namespace(command="backlog", action="add", title=title, text=text, source=source, evidence=evidence or [])


@backlog.command
def migrate() -> Namespace:
    """Once: move the file entries into GitHub issues, then delete the files."""
    return Namespace(command="backlog", action="migrate")


@cases.command(name="list")
def list_cases(*, version: int | None = None) -> Namespace:
    """The newest version's cases.

    Args:
        version: The version to list instead.
    """
    return Namespace(command="cases", action="list", version=version)


@cases.command(name="seed")
def seed_cases(*, pilot: Path | None = None, calls: Path | None = None, synthetic: bool = False) -> Namespace:
    """Seed candidates: the pilot's moments, the synthetic cases, or both.

    Args:
        pilot: The pilot's folder (watcher-replay).
        calls: JSON: each should moment's finding category.
        synthetic: The synthetic cases (a marked assumption).
    """
    return Namespace(command="cases", action="seed", pilot=pilot, calls=calls, synthetic=synthetic)


@cases.command(name="add")
def add_case(record: str, /, *, call: Annotated[str, Parameter(validator=_call)], why: str) -> Namespace:
    """A candidate from a Spotter record.

    Args:
        record: The Spotter record.
        call: The finding category the case expects, or none.
        why: Why the record makes that call.
    """
    return Namespace(command="cases", action="add", record=record, call=call, why=why)


@cases.command
def move(  # noqa: PLR0913 - one parameter per option
    case: str,
    stage: Annotated[str, Parameter(validator=_stage)],
    /,
    *,
    call: Annotated[str, Parameter(validator=_call_or_none)] = "",
    why: str = "",
    example: str = "",
    reviewed_by: str = "",
    note: str = "",
) -> Namespace:
    """Change a case's stage, call, why or example; examples changed: a paid regression.

    Args:
        case: The case's id.
        stage: Its new stage, or removed.
        call: Its new call.
        why: Its new why.
        example: The minimised moment the prompt shows (an example).
        reviewed_by: Who checked that the frozen card supports the call.
        note: A note on the change.
    """
    fields = {"call": call, "why": why, "example": example, "reviewed_by": reviewed_by, "note": note}
    return Namespace(command="cases", action="move", case=case, stage=stage, **fields)


@cases.command
def rollback(version: int, /) -> Namespace:
    """A new version copying an earlier one.

    Args:
        version: The version to copy.
    """
    return Namespace(command="cases", action="rollback", version=version)


@cases.command
def check(ids: list[str] | None = None, /) -> Namespace:
    """Retro-review checks candidates' cards against their calls (paid).

    Args:
        ids: Cases to check; every candidate when none.
    """
    return Namespace(command="cases", action="check", ids=ids or [])


@cases.command
def release() -> Namespace:
    """Freeze the reviewed corpus as a release (a marked assumption)."""
    return Namespace(command="cases", action="release")


@cases.command
def compare(a: int, b: int, /, *, release: str = "") -> Namespace:
    """Two versions on a release's reserve, once per release (paid).

    Args:
        a: The first version.
        b: The second version.
        release: The release; the newest by default.
    """
    return Namespace(command="cases", action="compare", a=a, b=b, release=release)


@cases.command
def runs(*, last: int = 10) -> Namespace:
    """Every run's result.

    Args:
        last: How many of the latest runs.
    """
    return Namespace(command="cases", action="runs", last=last)


@improvement.command
def reset() -> Namespace:
    """Retire every marked assumption."""
    return Namespace(command="improvement", action="reset")


@retro.command(name="run")
def run_retro(
    *,
    change: Annotated[str | None, Parameter(group=UNIT)] = None,
    chat: Annotated[str | None, Parameter(group=UNIT)] = None,
    synthetic: Annotated[str | bool | None, Parameter(group=UNIT, negative="")] = None,  # NAME stays a name
) -> Namespace:
    """Queue a run of one unit for the host's Retro job (paid).

    Args:
        change: PROJECT/SLUG: a finished Change; PROJECT is its folder's name or id.
        chat: SESSION: an enrolled chat, quiet for a day.
        synthetic: The synthetic units, or one NAME.
    """
    return Namespace(command="improvement", action="retro", retro="run", change=change, chat=chat, synthetic=synthetic)


@retro.command(name="status")
def retro_status(*, last: int = 10, plan: str | None = None) -> Namespace:
    """The latest runs, or with --plan what a run of a unit would ask (not paid).

    Args:
        last: How many of the latest runs.
        plan: UNIT: a unit id (chg:…, chat:…, syn:…) or PROJECT/SLUG.
    """
    return Namespace(command="improvement", action="retro", retro="status", last=last, plan=plan)
