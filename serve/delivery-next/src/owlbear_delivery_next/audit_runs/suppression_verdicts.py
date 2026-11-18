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
        state = audits.read("suppressions") or {}
        if state.get("state") == "publishing":
            msg = "Finish publishing the previous run before changing verdicts."
            raise ValueError(msg)
        group = next((g for g in read(audits) if g["id"] == token), None)
        if group is None:
            msg = "These verdicts changed; reopen Verdicts and confirm the current line."
            raise ValueError(msg)
        if action == "accept" and group["verdict"] != "refused":
            msg = "Only refused suppressions can be accepted."
            raise ValueError(msg)
        store = audits.store
        running = {s for s in store.slugs() if not store.read(s).finished_at}
        if held := sorted({m["for"] for m in group["members"]} & running):
            msg = (
                f"Running Change {', '.join(held)} holds a verdict that covers these suppressions; "
                "change them after it has finished."
            )
            raise ValueError(msg)
        # Nor are a running Change's other verdicts a removed copy's: they cover copies not on the target yet.
        spare = [
            m
            for m in suppression_items.spare(
                store.root, state.get("inventory", []), {m["identity"] for m in group["members"]}
            )
            if m["for"] not in running
        ]
        if action == "again":
            ledger.set_aside(audits.store.root, group["members"] + spare)
        else:
            current = ledger.current(audits.store.root)
            replacements = []
            for member in group["members"]:
                identity, index = member["identity"], member["index"]
                row = next(r for r in current[identity] if r["index"] == index)
                replacements.append(
                    {
                        "identity": identity,
                        "replaces": [index, *(m["index"] for m in spare if m["identity"] == identity)],
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
