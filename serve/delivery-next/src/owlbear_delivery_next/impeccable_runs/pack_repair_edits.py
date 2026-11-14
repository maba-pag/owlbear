"""An agent's CI repair of the Impeccable pull request: what in its change stops for the owner (``pack_repair``).

Lint, format, CI workflow, hook or security configuration is held: the owner may push it. A weakened test (a deleted
test file, an added skip or early return, a removed assertion or test) and what only an update may change
(the kind's ``refused``) are never pushed. Every other edit of an existing test file, including a Python test only
reformatted (its syntax tree unchanged), waits for the owner's review of its diff: the patterns are a quick filter,
no proof that a test still checks as much.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.impeccable_runs import pack_rounds
from owlbear_delivery_next.impeccable_runs.pack_repair_content import IMPECCABLE, Kind
from owlbear_delivery_next.workflow_steps import check_weakening
from owlbear_delivery_next.workflow_steps.check_weakening import LINKS, configured, weakened

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.impeccable import pack_git
    from owlbear_delivery_next.impeccable_runs.pack_repair import Repair


staged = check_weakening.staged  # the pack's callers read it here


def config(run: str, r: Repair) -> dict[str, Any]:
    """The owner's question about a held repair: a weakened check is never pushed, other holds he may let through.

    He is shown the diff of the paths it asks about; when that is too long to show whole, nothing is pushed from it.
    """
    made, said = r.commit[:12], f"The agent said: {r.summary}"
    config = f"; it also changes configuration: {', '.join(r.held[:10])}" if r.held else ""
    if r.refused:
        text = (f"The agent's CI repair {made} weakens a check or changes what only an update may: "
                f"{', '.join(r.refused[:10])}. Delivery pushed nothing and never pushes it.")  # fmt: skip
        ask, options = "Try again without it, or discard?", [pack_rounds.RETRY, pack_rounds.DISCARD]
    elif r.suppressions:
        text = (f"The agent's CI repair {made} adds suppressions that need your approval:\n"
                f"{chr(10).join(r.suppressions)}\nNothing was pushed. Review its complete patch.")  # fmt: skip
        ask = "Push this exact repair, including its suppressions?"
        options = [pack_rounds.PUSH_REVIEWED if r.reviewed else pack_rounds.PUSH_CONFIG, pack_rounds.DISCARD]
    elif r.reviewed:
        text = (f"The agent's CI repair {made} changes tests: {', '.join(r.reviewed[:10])}{config}. Delivery's "
                "pattern check found no known weakening, but cannot tell that the tests still check as much: review "
                "its diff. Nothing was pushed.")  # fmt: skip
        ask, options = "Push it, or discard?", [pack_rounds.PUSH_REVIEWED, pack_rounds.DISCARD]
    else:
        text = (f"The agent's CI repair {made} changes {', '.join(r.held[:10])}: lint, format, CI workflow, hook or "
                "security configuration. Delivery pushed nothing.")  # fmt: skip
        ask = "Push it as it is, try again without it, or discard?"
        options = [pack_rounds.PUSH_CONFIG, pack_rounds.RETRY, pack_rounds.DISCARD]
    if r.diff_cut:  # never pushed unseen
        why = "holds binary content, which" if r.diff_binary else "is too large to review here, so it"
        text = f"{text} Its diff of these files {why} cannot be reviewed or pushed from here."
        ask, options = "Try again without it, or discard?", [pack_rounds.RETRY, pack_rounds.DISCARD]
    q = pack_rounds.question(f"{run}:repair-config:{made}", "repair-config", f"{text} {ask} {said}", [],
                             commit=r.commit, paths=asked(r) if r.suppressions else [*r.refused, *r.reviewed, *r.held],
                             diff=r.diff)  # fmt: skip
    q["options"] = pack_rounds.published(options, opened=True)
    return q


def asked(r: Repair) -> list[str]:
    """The repository paths the held question asks about: its held, refused and reviewed files, without the reasons."""
    named = {*r.held, *r.refused, *r.reviewed}
    if r.suppressions:
        return r.paths
    return [p for p in r.paths if p in named or any(n.startswith(f"{p} (") for n in named)]


def held(  # noqa: PLR0913 - the copy, its head, the change, the package with its pinned skills, and the kind
    run: pack_git.Git,
    at: Path,
    head: str,
    changed: list[tuple[str, str]],
    *,
    package: str,
    skills: list[str],
    kind: Kind = IMPECCABLE,
) -> tuple[list[str], ...]:
    """What in the change stops for the owner: its configuration, what is never pushed and its other test edits.

    The weakening patterns (a deleted test, an added skip or early return, a removed assertion or test)
    are a quick filter, not a proof; every other edit of an existing test file is held for the owner's review.
    """
    held = [p for p, how in changed if configured(p) or how.split()[0] in LINKS]
    held += [p for p, _ in changed if p not in held and check_weakening.suppressions(run, at, head, p)]
    found = {path: weakened(run, at, head, path, how) for path, how in changed}
    refused = [f"{p} ({found[p][0]})" for p, how in changed if how.endswith("D") and found[p][0]]
    refused += [
        f"{p} ({kind.refusal})" for p, how in changed if kind.refused(package, p, not how.endswith("D"), skills)
    ]
    refused += [f"{p} ({found[p][0]})" for p, how in changed if not how.endswith("D") and found[p][0]]
    reviewed = [f"{p} ({found[p][1]} a test)" for p, _ in changed if found[p][1]]
    return held, refused, reviewed
