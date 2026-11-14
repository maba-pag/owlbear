"""Validation of a worker's committed build against its required checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import check_hint

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.change_contracts.models import ItemRef
    from owlbear_delivery_next.change_contracts.tools import BuildResult, Worktree


def few(paths: Sequence[str]) -> str:
    """A bounded list of paths for a field error."""
    return ", ".join(paths[:5]) + (f" and {len(paths) - 5} more" if len(paths) > 5 else "")  # noqa: PLR2004


def _response(result: BuildResult, item: ItemRef | None) -> list[str]:
    r = result.response
    if item is None:
        return ["response: only for a pull-request conversation task - remove it"] if r else []
    if r is None:
        return ['response: required for this conversation task - e.g. {"how": "answered", "text": "..."}']
    if r.how == "no-action" and not item.notice:
        return ["response.how: no-action is only for a bot's comment or review - fix it or answer it"]
    return []


def check_build(result: BuildResult, tree: Worktree, checks: Sequence[str], item: ItemRef | None = None) -> list[str]:
    """Field errors against the observed HEAD and task checks; a non-code reply needs no new commit."""
    errors = _response(result, item)
    if (m := getattr(result, "merge", None)) is not None and bool(m.this) != bool(m.other):
        errors.append(f"merge.{'other' if m.this else 'this'}: empty - say what the product does with that side too")
    reply = (result.response is not None and result.response.how != "fixed") or bool(result.rejected)
    if reply and tree.head == tree.base and not tree.dirty:
        return errors
    if tree.head == tree.base:
        errors.append(
            f"changes: no commit since the task's base {tree.base[:12]}; commit your changes, then submit again"
        )
    if tree.dirty:
        errors.append(f"changes: uncommitted files ({few(tree.dirty)}); commit them, then submit again")
    errors.extend(
        f"checks[{i}].exit_code: {c.exit_code} - fix the failure, commit, run it again, then submit"
        for i, c in enumerate(result.checks)
        if c.exit_code != 0
    )
    errors.extend(
        check_hint.missing(cmd)
        for cmd in checks
        if not any(check_hint.ran(cmd, c.command, checks) for c in result.checks)
    )
    return errors
