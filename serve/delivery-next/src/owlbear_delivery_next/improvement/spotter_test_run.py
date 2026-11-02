"""Starting and showing the Spotter's steered-versus-silent test (design §4), recorded by ``state_store.spotter_test``.

A start freezes what every live look sends while the test runs: the Spotter role's effective model, effort and context
in the settings given (the machine's, Global's under this machine's), and the prompt with the cases' newest examples,
its exact text, hash and version (``cases.snapshot``). ``Spotter`` applies them where it admits a look, and
``cases.commit`` refuses a change of the examples meanwhile. Running the test, its admission and promotion, is item
25's.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import cases
from owlbear_delivery_next.state_store import spotter_test

if TYPE_CHECKING:
    from owlbear_delivery_next.settings.config import Settings


def start(settings: Settings) -> dict[str, Any]:
    """Start the declared test, freezing the Spotter's role in *settings* and the prompt now; the record.

    Raises:
        SettingsUnset: The Spotter's role or its verbose setting is unset.
        spotter_test.Refused: No test is declared, or it started already; or the prompt or its examples cannot be read,
            so there is nothing whole to freeze.
    """
    settings.need("spotter.verbose")
    role = settings.agent("spotter")
    prompt = cases.snapshot(verbose=settings.spotter.verbose_on(datetime.now(UTC).date()))
    if not prompt.text or prompt.gap:
        msg = f"the Spotter test cannot start: {prompt.gap or 'the prompt is empty'}"
        raise spotter_test.Refused(msg)
    frozen = {"model": role.model or "", "effort": role.effort or "", "context": role.context or "",
              "prompt": prompt.text, "prompt_hash": prompt.hash, "cases": prompt.cases}  # fmt: skip
    return spotter_test.start(frozen)


def show() -> dict[str, Any]:
    """The newest test's state, declaration and frozen versions (the prompt's hash, not its text); ``none`` if none."""
    test = spotter_test.current()
    if test is None:
        return {"state": "none"}
    frozen = test.get("frozen")
    return {
        "id": test["id"],
        "state": spotter_test.state(test),
        "declared": test["declared"],
        "declared_at": test["declared_at"],
        "started_at": test["started_at"],
        "ended_at": test["ended_at"],
        "frozen": {k: v for k, v in frozen.items() if k != "prompt"} if frozen else None,
    }
