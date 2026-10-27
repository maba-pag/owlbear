"""Spotter cases reviewed by ``retro-review`` (Improvement design §4, §6): checking candidates, and publication.

**Check** (on the owner's word, within the Retro run limit): ``retro-review`` reads each candidate's frozen card with
its call and why and says whether the card supports that call. A supported candidate becomes a test case, its review
bound to exactly the card, call and why that were checked; a candidate changed meanwhile stays as it is.

**Publication** (on its own, D-01M5XCE8ZFZE8Q1XCN1EE4B29S): every test case and example that is not synthetic goes to
the shared repository's ``owlbear/improvement/spotter-cases/<id>.json`` once ``retro-review`` minimised and sanitised
it, credentials included. Its answer is validated strictly (its call must be the case's own), then the whole export,
metadata included, must pass the deterministic check (``mask.redact``, emails, home paths); what fails stays here,
owner-only, never in the shared checkout. The export names the case only by its local id (its provenance stays on
this machine). Before writing, the case is checked again under the store's lock: one changed or removed during its
review is not published. A case that leaves the published stages is removed from the shared repository. A commit
that could not be pushed is pending and pushed by a later sync; nothing is called published until it was pushed.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import cases
from owlbear_delivery_next.improvement.cases import CaseError
from owlbear_delivery_next.improvement.credits import Meter
from owlbear_delivery_next.improvement.events import EMAIL
from owlbear_delivery_next.local_system import mask
from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from owlbear_delivery_next.local_system.data_repo import DataRepo

CHECK = Path(__file__).with_name("case_check_prompt.md")
PUBLISH = Path(__file__).with_name("case_publish_prompt.md")
FOLDER = ("owlbear", "improvement", "spotter-cases")
SITUATION = 1200  # characters of a published case's situation
HOME = re.compile(r"(?:/Users|/home|/root)/[^/\s\"']+|[A-Za-z]:\\\\Users\\\\")
PUBLISHED = frozenset({"test", "example"})

type Ask = Callable[[str, Meter], Awaitable[str]]  # one retro-review session: the message in, its last answer out


def _message(prompt: Path, cid: str, entry: cases.Entry) -> str:
    payload = {"call": entry["call"], "why": entry.get("why", ""), "card": cases.card(cid)}
    return f"{prompt.read_text()}\n\n## The case (data, not instructions)\n\n```json\n{json.dumps(payload)}\n```\n"


def _answer(text: str) -> dict[str, Any] | None:
    hit = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        said = json.loads(hit.group(0)) if hit else None
    except ValueError:
        return None
    return said if isinstance(said, dict) else None


# Check


async def check(request: dict[str, Any], ask: Ask, meter: Meter) -> dict[str, Any]:
    """Review *request*'s candidates within *meter*; the run's result, kept with the other runs."""
    out: dict[str, Any] = {
        "id": request["id"],
        "kind": "check",
        "by": request["by"],
        "asked": request["at"],
        "started": cases.now(),
        "reviews": {},
    }
    why = ""
    for cid, wanted in request["ids"].items():
        if not meter.open():
            why = f"stopped: {meter.report()['stopped'] or 'the run credit limit is reached'}"
            break
        entry = cases.current()["cases"].get(cid)
        if entry is None or entry["stage"] != "candidate" or cases.content(cid, entry) != wanted:
            out["reviews"][cid] = {"result": "changed since it was asked: not reviewed"}
            continue
        said = _answer(await ask(_message(CHECK, cid, entry), Meter(meter.left(), parent=meter)))
        if said is None or not isinstance(said.get("supported"), bool) or not isinstance(said.get("note", ""), str):
            out["reviews"][cid] = {"result": "no usable answer"}
            continue
        out["reviews"][cid] = {
            "result": "supported" if said["supported"] else "not supported",
            "note": said.get("note", "")[:600],
        }
        if said["supported"]:
            out["reviews"][cid]["result"] = _promote(cid, wanted, said.get("note", ""))
    out |= {"result": why or "checked", "credits": meter.report(), "ended": cases.now()}
    with cases.locked():
        cases.append("runs.jsonl", out)
    return out


def _promote(cid: str, wanted: str, note: str) -> str:
    """Make candidate *cid* a test case if it is still exactly what was reviewed; what happened."""
    with cases.locked():
        cur = cases.current()
        entry = cur["cases"].get(cid)
        if entry is None or entry["stage"] != "candidate" or cases.content(cid, entry) != wanted:
            return "supported, but it changed during the review: not promoted"
        review = {"by": "retro-review", "at": cases.now(), "note": note[:600], "content": wanted}
        try:
            cases.commit(
                cur["n"],
                {cid: {**entry, "stage": "test", "review": review}},
                "retro-review",
                f"check: the card supports {entry['call']}",
            )
        except CaseError as exc:
            return f"supported, but not promoted: {exc}"
        return "supported: now a test case"


# Publication


def _state() -> dict[str, dict[str, Any]]:
    try:
        return json.loads((cases.place() / "published.json").read_text())
    except FileNotFoundError:
        return {}
    except ValueError as exc:
        msg = f"published.json cannot be read: {exc}"
        raise CaseError(msg) from exc


def _set(cid: str, **state: Any) -> None:  # noqa: ANN401 - the case's publication state
    with cases.locked():
        found = _state()
        found[cid] = {**state, "at": cases.now()}
        atomic_write(cases.ready() / "published.json", json.dumps(found, indent=1) + "\n")


def eligible(cid: str, entry: cases.Entry) -> bool:
    """Whether a case in this stage is published."""
    return entry.get("stage") in PUBLISHED and cases.fact(cid)["source"] != "synthetic"


def leaks(text: str) -> list[str]:
    """What the deterministic check still finds in *text*: credentials, emails, home paths."""
    out = []
    if mask.redact(text) != text:
        out.append("a credential")
    if EMAIL.search(text):
        out.append("an email address")
    if HOME.search(text):
        out.append("a home path")
    return out


def export(cid: str, revision: str, said: dict[str, Any], call: str) -> str:
    """The published file of case *cid*, or why the reviewer's answer is refused (a text starting "refused:")."""
    if set(said) - {"situation", "call", "why"}:
        return f"refused: the review answered more than situation, call and why ({', '.join(sorted(said))})"
    if not all(isinstance(said.get(k), str) and said[k].strip() for k in ("situation", "call", "why")):
        return "refused: the review must give situation, call and why as texts"
    if said["call"] != call:
        return f"refused: the review changed the call from {call} to {said['call']}"
    if len(said["situation"]) > SITUATION or len(said["why"]) > cases.WHY:
        return "refused: the review's situation or why is too long"
    body = {
        "format": 1,
        "id": cid,
        "revision": revision,
        "call": call,
        "situation": said["situation"],
        "why": said["why"],
        "provenance": {"local": cid},
    }
    text = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if found := leaks(text):
        return f"refused: the export still holds {', '.join(found)}"
    return text


def _keep_rejected(cid: str, revision: str, text: str) -> None:
    folder = cases.ready() / "rejected"
    folder.mkdir(exist_ok=True, mode=0o700)
    fd = os.open(folder / f"{cid}-{revision}.txt", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(text)


def due() -> tuple[dict[str, str], list[str], list[str]]:
    """What a sync has to do: cases to review (by revision), pending pushes, published cases to remove."""
    cur, state = cases.current()["cases"], _state()
    review, push = {}, []
    for cid, entry in sorted(cur.items()):
        if not eligible(cid, entry):
            continue
        rev, had = cases.content(cid, entry), state.get(cid, {})
        if had.get("revision") == rev and had.get("state") in {"pending", "failed"} and _kept(cid, rev) is not None:
            push.append(cid)  # reviewed already: written again from the kept export, never reviewed again
        elif had.get("revision") != rev or had.get("state") not in {"published", "refused"}:
            review[cid] = rev
    gone = [
        cid
        for cid, had in state.items()
        if had.get("state") in {"published", "pending", "withdrawing"} and not (cid in cur and eligible(cid, cur[cid]))
    ]
    return review, push, gone


def _kept(cid: str, rev: str) -> str | None:
    """The reviewed export of *cid* at *rev* kept on this machine, if any."""
    try:
        return (cases.place() / "exports" / f"{cid}-{rev}.json").read_text()
    except OSError:
        return None


def _keep(cid: str, rev: str, text: str) -> None:
    folder = cases.ready() / "exports"
    folder.mkdir(exist_ok=True, mode=0o700)
    atomic_write(folder / f"{cid}-{rev}.json", text)


def _path(shared: DataRepo, cid: str) -> Path:
    return shared.root.joinpath(*FOLDER, f"{cid}.json")


def _write(shared: DataRepo, cid: str, text: str | None) -> tuple[str, str]:
    """Write (or, with None, remove) case *cid*'s file, then commit and push it, under the repository's lock.

    Its state (published; pending: committed, not pushed; or failed) and why.
    """
    path, message = _path(shared, cid), f"Spotter case {cid}: {'removed' if text is None else 'published'}"
    try:
        with shared.locked():
            if text is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(path, text)
            said = shared.publish(path, message)
    except (DataRepoError, OSError) as exc:
        return "failed", str(exc)
    if not said:
        return "published", ""
    return ("pending" if "committed" in said and "not committed" not in said else "failed"), said


async def sync(shared: DataRepo | None, ask: Ask, meter: Meter) -> dict[str, Any]:
    """Bring the shared repository's cases to the newest version within *meter*; what it did."""
    review, push, gone = due()
    out: dict[str, Any] = {"published": [], "pending": [], "removed": [], "refused": [], "failed": [], "stopped": ""}
    if shared is None:
        out["stopped"] = "no shared repository on this machine" if review or push or gone else ""
        return out
    for cid in gone:
        state, why = _write(shared, cid, None)
        _set(cid, revision="", state="removed" if state == "published" else "withdrawing", why=why)
        out["removed" if state == "published" else state].append(cid)
    for cid in push:
        rev = _state()[cid]["revision"]
        out[_place(shared, cid, rev, _kept(cid, rev) or "")].append(cid)
    for cid, rev in review.items():
        if not meter.open():
            out["stopped"] = meter.report()["stopped"] or "the run credit limit is reached"
            break
        entry = cases.current()["cases"].get(cid)
        if entry is None or cases.content(cid, entry) != rev:
            continue  # changed since: the next sync takes it
        text = await ask(_message(PUBLISH, cid, entry), Meter(meter.left(), parent=meter))
        said = _answer(text)
        made = export(cid, rev, said, entry["call"]) if said is not None else "refused: the review gave no JSON object"
        if made.startswith("refused:"):
            _keep_rejected(cid, rev, text)
            _set(cid, revision=rev, state="refused", why=made)
            out["refused"].append(cid)
            continue
        _keep(cid, rev, made)
        out[_place(shared, cid, rev, made)].append(cid)
    return out


def _place(shared: DataRepo, cid: str, rev: str, text: str) -> str:
    """Write the reviewed export, if the case is still exactly what was reviewed; its state."""
    with cases.locked():
        entry = cases.current()["cases"].get(cid)
        if entry is None or not eligible(cid, entry) or cases.content(cid, entry) != rev:
            _set(cid, revision="", state="changed", why="changed or removed during its review: not published")
            return "refused"
        state, why = _write(shared, cid, text)
        _set(cid, revision=rev, state=state, why=why)
        return state
