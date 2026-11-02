"""``owlbear improvement``: the marked assumptions, Retro and the Spotter's test, defined as ``project_commands`` are.

Each command only parses: it returns the ``argparse.Namespace`` that ``cases_cli`` runs. Loading this module imports
no other OwlBear module but the groups' shared parts, so ``owlbear --help`` stays fast (TD-263).
"""

from argparse import Namespace
from typing import Annotated

from cyclopts import Group, Parameter, validators

from owlbear_delivery_next.commands.command_apps import group

improvement = group("improvement", "Improvement's marked assumptions, Retro and the Spotter's test.")
retro = group("retro", "Retro: judge a finished Change or chat (Improvement design §5).")
spotter_test = group("test", "The Spotter's steered-versus-silent test: its declaration and frozen inputs (§4).")
improvement.command(retro)
improvement.command(spotter_test)
UNIT = Group("Unit", validator=validators.LimitedChoice(1, 1))  # exactly one, as argparse's required group


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


@spotter_test.command
def declare(*, outcome: str, start_threshold: str, promote_threshold: str) -> Namespace:
    """Declare the test, or change the declaration of one not started; refused once it started.

    Args:
        outcome: The primary outcome the arms are compared on.
        start_threshold: The live-delivery Retro grade the test may start at.
        promote_threshold: What promotes the steered arm.
    """
    return Namespace(command="improvement", action="test", test="declare", outcome=outcome,
                     start_threshold=start_threshold, promote_threshold=promote_threshold)  # fmt: skip


@spotter_test.command
def start() -> Namespace:
    """Start the declared test: the Spotter's model, effort, context, prompt and cases freeze until it ends."""
    return Namespace(command="improvement", action="test", test="start")


@spotter_test.command
def end() -> Namespace:
    """End the running test: its frozen inputs are released."""
    return Namespace(command="improvement", action="test", test="end")


@spotter_test.command
def show() -> Namespace:
    """The test's declaration, state and frozen versions."""
    return Namespace(command="improvement", action="test", test="show")
