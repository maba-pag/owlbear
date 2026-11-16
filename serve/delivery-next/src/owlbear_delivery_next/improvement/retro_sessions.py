"""Change session ownership from exact worktrees, recorded repairs and their replacement chains."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable


def change_sessions(
    lines: list[dict[str, Any]],
    place: str,
    *,
    repair_sessions: Iterable[str] = (),
    repair_places: Iterable[str] = (),
    project: str = "",
) -> list[str]:
    """Owned sessions in manifest-start order, including overwritten repair attempts and replacements."""
    places = {place, f"{place}.ro"} if place else set()
    places.update(repair_places)
    found = set(repair_sessions)
    starts = [d for d in lines if d.get("event") == "started"]

    def own(d: dict[str, Any]) -> bool:
        return (not project or d.get("project") in {None, "", project}) and (
            not d.get("worktree") or d["worktree"] in places
        )

    found.update(d["session"] for d in starts if d.get("worktree") in places and own(d))
    while more := {d["session"] for d in starts if d.get("replaces") in found and own(d)} - found:
        found.update(more)
    ordered = list(dict.fromkeys(d["session"] for d in starts if d["session"] in found))
    return [*ordered, *sorted(found - set(ordered))]
