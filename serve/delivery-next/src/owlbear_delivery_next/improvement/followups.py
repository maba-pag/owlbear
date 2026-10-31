"""Follow-ups (#716, Improvement design §6): a Retro finding or Spotter record the owner wants worked on, as backlog.

A follow-up is one backlog entry, saved once: an entry already carrying ``followup:<id>`` in its evidence is that
follow-up, and nothing more is made. A Retro finding that a current reviewed proposal of its own already put into
publishable words is saved at once; anything else is minimised by one ``retro-review`` call of a Retro run first. The
text is checked for credentials, emails and home paths before it is saved; an unsafe one is refused, nothing written,
and an unsafe minimised answer is never replayed: the next run asks again. It lands in the backlog seen from the
subject's project, or from none; a synthetic finding's only in the sandbox's.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.improvement import case_review, retro_judge
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.retro_calls import StoppedError, paid
from owlbear_delivery_next.improvement.retro_segments import cut, dumps, masked
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.state_store.backlog import Backlog, BacklogError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_delivery_next.improvement.retro_calls import Work
    from owlbear_delivery_next.state_store.backlog import Entry

MARK = "followup:"
SAVED = "followups.jsonl"  # the entries saved, or found made, at the owner's request rather than by a run
SUBJECT = 6_000  # characters of the subject a minimising message carries
PROMPT = Path(__file__).with_name("followup_prompt.md")
FINDING = ("id", "what", "mechanism", "cost", "steps", "quotes", "cause", "target")
RECORD = ("id", "look", "category", "note", "step")

type Backlogs = Callable[[str], Backlog]  # a project's folder in the shared repository ("" none) -> its backlog view


class Unknown(store.RetroError):
    """No Retro finding or Spotter record has the id asked for."""


def backlog(folder: str) -> Backlog:
    """The shared repository's backlog seen from *folder* ("" from no project).

    Raises:
        RetroError: There is no shared repository.
    """
    shared = data_repo.locate()
    if shared is None:
        msg = "no shared repository: a follow-up is saved to its backlog"
        raise store.RetroError(msg)
    return Backlog(shared, folder)


def subject(fid: str, places: Mapping[str, targets.Place]) -> dict[str, Any]:
    """What follow-up *fid* is about: a Retro finding, else a Spotter record; its project, Change, source and text.

    Raises:
        Unknown: *fid* is neither.
        RetroError: A synthetic finding while the sandbox is not registered.
    """
    found = next((f for f in store.all_findings() if f["id"] == fid), None)
    if found is not None:
        unit, source, provenance = str(found.get("unit") or ""), "retro", str(found.get("provenance") or "real")
        shown = {k: found.get(k) for k in FINDING}
    elif (record := next((r for r in units.records() if r.get("id") == fid), None)) is not None:
        unit, source, provenance = units.unit_of(record), "spotter", "real"
        grades = [{k: g.get(k) for k in ("grade", "reason", "should")} for g in store.grades(record=fid)]
        shown = {k: record.get(k) for k in RECORD} | {"grades": grades}
    else:
        msg = f"no Retro finding or Spotter record {fid}"
        raise Unknown(msg)
    pid = targets.sandbox(places) if provenance == "synthetic" else targets.project(unit, places, store.known())
    if provenance == "synthetic" and not pid:
        msg = f"a synthetic finding's follow-up goes only to the sandbox; register ~/Projects/{targets.SANDBOX}"
        raise store.RetroError(msg)
    change = unit.split(":", 2)[2] if pid and unit.startswith(f"chg:{pid}:") else ""
    folder = places[pid].folder if pid else ""
    return {"id": fid, "source": source, "provenance": provenance, "project": pid, "change": change,
            "folder": folder, "shown": shown}  # fmt: skip


def reusable(fid: str) -> dict[str, str] | None:
    """The publishable text of a current reviewed survivor whose findings are exactly *fid*, if there is one."""
    for snap in props.folded().values():
        current = snap["review_digest"] == snap["evidence"] and snap["verdict"] == "survive"
        if current and snap["findings"] == [fid] and snap["state"] not in {"rejected", "redirected"}:
            shown = snap.get("publishable") or {}
            if shown.get("title") and shown.get("body"):
                return {"title": str(shown["title"]), "body": str(shown["body"])}
    return None


def _entry(e: Entry, view: Backlog) -> dict[str, Any]:
    link = f"https://github.com/{view.repository}/issues/{e.id}"
    return {"id": e.id, "title": e.title, "repository": view.repository, "link": link}


def _made(view: Backlog, fid: str) -> Entry | None:
    return next((e for e in view.read(fresh=True)[0].values() if f"{MARK}{fid}" in e.evidence), None)


def save(subj: Mapping[str, Any], text: Mapping[str, str], backlogs: Backlogs) -> dict[str, Any]:
    """Save *text* as *subj*'s follow-up entry, unless one is saved; the entry.

    Raises:
        RetroError: The text holds a credential, an email address or a home path; nothing was written.
    """
    title, body = str(text.get("title") or "").strip(), str(text.get("body") or "").strip()
    if leaked := case_review.leaks([title, body]):
        msg = f"the follow-up text holds {', '.join(leaked)}: nothing was written"
        raise store.RetroError(msg)
    if not title or not body:
        msg = "the follow-up text has no title or body: nothing was written"
        raise store.RetroError(msg)
    view = backlogs(subj["folder"])
    if (made := _made(view, subj["id"])) is None:
        refs = f"\n\nRefs: {subj['id']}"
        body = f"{body[: retro_judge.BODY - len(refs)]}{refs}" if subj["id"] not in body else body[: retro_judge.BODY]
        made, _ = view.add(title[: retro_judge.TITLE], body, subj["source"], evidence=[f"{MARK}{subj['id']}"])
    return _entry(made, view)


def request(fid: str, by: str, places: Mapping[str, targets.Place], backlogs: Backlogs) -> dict[str, Any]:
    """The owner asks for *fid*'s follow-up: ``{"entry": ...}`` saved (or found), else ``{"queued": rid}``.

    Raises:
        RetroError: *fid* is unknown, its text unsafe, or the backlog cannot be reached.
    """
    subj = subject(fid, places)
    view = backlogs(subj["folder"])
    if (made := _made(view, fid)) is not None:
        return _kept(fid, _entry(made, view))
    if subj["source"] == "retro" and (text := reusable(fid)) is not None:
        return _kept(fid, save(subj, text, backlogs))
    return {"queued": store.request(by, followup=fid)}


def _kept(fid: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Note *fid*'s entry, so its follow-up shows as saved without a run; the answer."""
    with store.locked():
        store.append(SAVED, {"id": fid, "entry": entry, "at": store.now()})
    return {"entry": entry}


def saved() -> dict[str, dict[str, Any]]:
    """Each follow-up saved without a run: its finding's or record's id -> its entry, the newest."""
    return {line["id"]: line["entry"] for line in store.lines(SAVED)}


def _valid(said: Mapping[str, Any]) -> bool:
    """A usable minimised text; an unsafe one is not, so it is kept only as an attempt and the next run asks again."""
    text = [said.get(k) for k in ("title", "body")]
    return all(isinstance(t, str) and t.strip() for t in text) and not case_review.leaks(text)


def run(w: Work, fid: str, places: Mapping[str, targets.Place], backlogs: Backlogs) -> dict[str, Any]:
    """Minimise *fid* in one paid call and save it; the entry.

    Raises:
        StoppedError: The subject is unknown, the answer unusable or unsafe, the run's limit reached or the backlog
            unreachable; nothing saved.
    """
    try:
        subj = subject(fid, places)
        view = backlogs(subj["folder"])
        if (made := _made(view, fid)) is not None:
            return {"followup": _entry(made, view)}
        shown = cut(dumps(masked(subj["shown"])), SUBJECT)
        message = f"{PROMPT.read_text()}\n\n## The subject\n\n```json\n{shown}\n```\n"
        said = paid(w, f"followup:{fid}", message, _valid, "retro-review")
        return {"followup": save(subj, said, backlogs)}
    except store.RetroError as exc:
        msg = f"refused: {exc}"
        raise StoppedError(msg) from exc
    except (BacklogError, ProviderError, OSError) as exc:  # the answer is kept: the next run saves it unpaid
        msg = f"stopped: the backlog could not be reached ({type(exc).__name__}: {exc})"[:300]
        raise StoppedError(msg) from exc
