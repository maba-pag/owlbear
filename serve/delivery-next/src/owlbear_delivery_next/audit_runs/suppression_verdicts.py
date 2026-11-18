"""Owner actions over the currently displayed, pinned verdict groups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from owlbear_quality import ledger

from owlbear_delivery_next.audit_runs import suppression_items

if TYPE_CHECKING:
    from owlbear_delivery_next.audit_runs.job import Audits


def read(audits: Audits) -> list[dict]:
    """The last pinned inventory's verdicts, including earlier Changes and owner rulings."""
    state = audits.read("suppressions") or {}
    return suppression_items.groups(audits.store.root, state.get("inventory", []))


def change(audits: Audits, token: str, action: Literal["again", "accept"]) -> list[dict]:
    """A stale line never applies its confirmation to different verdict copies."""
    with audits.lock:
        if audits.busy():
            msg = "An audit is running for this project; wait before changing verdicts."
            raise ValueError(msg)
        group = next((g for g in read(audits) if g["id"] == token), None)
        if group is None:
            msg = "These verdicts changed; reopen Verdicts and confirm the current line."
            raise ValueError(msg)
        if action == "accept" and group["verdict"] != "refused":
            msg = "Only refused suppressions can be accepted."
            raise ValueError(msg)
        if action == "again":
            ledger.set_aside(audits.store.root, group["members"])
        else:
            current = ledger.current(audits.store.root)
            replacements = []
            for member in group["members"]:
                identity, index = member["identity"], member["index"]
                row = next(r for r in current[identity] if r["index"] == index)
                replacements.append(
                    {
                        "identity": identity,
                        "replaces": [index],
                        "verdict": "accepted",
                        "by": "owner",
                        "reason": f"Owner accepted the suppression. Previous refusal: {row['reason']}",
                        "for": "review",
                        "commit": row["commit"],
                        "place": row["place"],
                        "directive": row["directive"],
                    }
                )
            ledger.add(audits.store.root, replacements)
        return read(audits)
