"""The owner's actions on decisions and a chat's proposals (TD-419 slice 5a); every write is a `decision_store.save`.

Authority ("Prior decisions by origin"; decision system §2, §4): anyone proposes a draft, only the owner activates,
replaces, withdraws, promotes, records an exception or resolves a conflict. A `decided` decision changes only when
the owner re-decides it. A reversal is a `replaces` link; the reversals of a lineage are counted back through
`replaces` and `promoted_from` to its first decision, so a promotion never resets them, and a second reversal is the
owner's. Each action names the revision the owner (or chat) read: a stale one is refused before anything is written.
A transition's files (a successor and what it retires, a kept decision and its withdrawn rivals) are saved together or
not at all. Every supersession says why: replace, withdraw, promote, keep and activating or proposing a draft that
replaces one need a reason, recorded in the successor's (or withdrawn decision's) rationale.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_decisions import Decision, Link, LinkType, Origin, OwnerWords, Scope, State, new_id
from owlbear_decisions.validate import layers, project_folders, read_layers
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.decision_store import DecisionsUnavailable, Receipt

if TYPE_CHECKING:
    from collections.abc import Mapping

    from owlbear_decisions import Entry
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.decision_store import DataView

OWNER, CHAT = "owner", "chat"
PAGE = "the Decisions page"
RETIRED = (State.REPLACED, State.WITHDRAWN, State.SPENT)
LINEAGE = (LinkType.REPLACES, LinkType.PROMOTED_FROM)
WIDER = {Scope.CHANGE: Scope.PROJECT, Scope.PROJECT: Scope.GLOBAL}
CHANGED, GONE = "Why it changed: ", "Why it was withdrawn: "


class Refused(Exception):  # noqa: N818 - says what happened
    """The action is not the caller's to take, or does not fit the decision; nothing was written."""

    def __init__(self, reason: str, status: int = 409) -> None:
        super().__init__(reason)
        self.status = status


def _now() -> datetime:
    return datetime.now(UTC)


def _line(text: str, limit: int = 200) -> str:
    return " ".join(text.split())[:limit]


def _words(text: str) -> tuple[OwnerWords, ...]:
    return (OwnerWords(text=text, date=_now().date()),) if text.strip() else ()


def _reason(reason: str, action: str) -> str:
    if not (said := reason.strip()):
        msg = f"say why: {action} needs a reason, recorded with the decision"
        raise Refused(msg, 422)
    return said


def _because(rationale: str, label: str, reason: str) -> str:
    """*rationale* with the reason for this change after it, once."""
    line = label + reason
    return rationale if line in rationale else "\n\n".join(filter(None, (rationale.strip(), line)))


def _entry(view: DataView, decision_id: str) -> Entry:
    entry = view.snapshot.get(decision_id)
    if entry is None:
        msg = f"there is no decision {decision_id} in this project's view"
        raise Refused(msg, 404)
    return entry


def _stale(view: DataView, decision: Decision, revision: str) -> list[Receipt]:
    if decision.revision == revision:
        return []
    notice = f"{decision.id} changed since it was read (now {decision.revision[:12]}); reload and decide again"
    return [Receipt(decision.id, saved=False, commit=view.commit, notice=notice)]


def _every(shared: DataRepo | None) -> dict[str, Decision]:
    """Every decision of the data repository by id, every project's included: lineages cross projects."""
    if shared is None:
        return {}
    try:
        entries, _ = read_layers(layers(shared.root, project_folders(shared.root)))
    except OSError as exc:
        msg = f"the decisions in {shared.root} cannot be read: {exc}"
        raise DecisionsUnavailable(msg, decision_store.READ) from exc
    return {e.decision.id: e.decision for e in entries}


def reversals(by_id: Mapping[str, Decision], decision: Decision) -> int:
    """The `replaces` links back from *decision* to its lineage's first decision; one that cannot be read counts."""
    count, seen, at = 0, set(), decision
    while at.id not in seen:
        seen.add(at.id)
        link = next((link for link in at.links if link.type in LINEAGE), None)
        if link is None:
            break
        count += link.type is LinkType.REPLACES
        if (found := by_id.get(link.target)) is None:
            return count + (link.type is LinkType.PROMOTED_FROM)  # an unknown past never resets the count
        at = found
    return count


def authorise(old: Decision, *, owner: bool, redecided: bool = False) -> None:
    """Raise `Refused` unless the caller may replace or withdraw *old*: a decided one only when the owner re-decides."""
    if old.origin is Origin.DECIDED and not (owner and redecided):
        how = "confirm that you re-decide it" if owner else f"the owner re-decides it on {PAGE}"
        msg = f"{old.id} is decided: it changes only after the owner re-decides it; {how}"
        raise Refused(msg)


def second(by_id: Mapping[str, Decision], old: Decision, *, decided: bool, owner: bool) -> None:
    """Raise `Refused` when replacing *old* reverses its lineage a second time and the successor is not *decided*."""
    if not decided and reversals(by_id, old):
        how = "confirm that you re-decide it" if owner else "give the owner's own words, or he replaces it on " + PAGE
        msg = f"{old.id} was reversed before: a second reversal is the owner's re-decision; {how}"
        raise Refused(msg)


def redecision(shared: DataRepo | None, view: DataView, draft: Decision) -> bool:
    """Whether activating *draft* is the owner's re-decision: it replaces a decided decision or reverses one again."""
    found = (view.snapshot.get(link.target) for link in draft.links if link.type is LinkType.REPLACES)
    olds = [e.decision for e in found if e is not None]
    if any(old.origin is Origin.DECIDED for old in olds):
        return True
    every = _every(shared) if olds else {}
    return any(reversals(every, old) for old in olds)


def _in_force(decision: Decision, action: str) -> None:
    if decision.state is not State.IN_FORCE:
        msg = f"{decision.id} is {decision.state}: only a decision in force can be {action}"
        raise Refused(msg)


def _retire(shared: DataRepo | None, new: Decision, old: Decision, message: str) -> list[Receipt]:
    """Save *new* and mark *old* replaced in one commit: both or neither, never two rules in force."""
    retired = old.model_copy(update={"state": State.REPLACED})
    return decision_store.save_all(shared, [(new, None), (retired, old.revision)], message=message)


def _new(old: Decision | None, **fields: object) -> Decision:
    base = old.content() if old else {}
    keep = {k: base[k] for k in ("aliases", "topic", "rationale", "consequences", "applies_to") if k in base}
    taken = {"id": new_id(), "created_at": _now(), "conflict": False, "read_back": "none"}
    return Decision.model_validate({**keep, **taken, **{k: v for k, v in fields.items() if v is not None}})


def replace(  # noqa: PLR0913 - the owner's successor and the revision he read
    shared: DataRepo | None, project: str, decision_id: str, revision: str, *,
    title: str, statement: str, rationale: str, words: str, reason: str, redecided: bool,
) -> list[Receipt]:  # fmt: skip
    """The owner's successor, in force and `decided` in his words, keeping the old one's other links; it is replaced."""
    why = _reason(reason, "replacing a decision")
    view = decision_store.load(shared, project)
    old = _entry(view, decision_id).decision
    if stale := _stale(view, old, revision):
        return stale
    _in_force(old, "replaced")
    authorise(old, owner=True, redecided=redecided)  # his successor is decided in his words: no second() needed
    kept = tuple(link for link in old.links if link.type not in LINEAGE)  # exception_to, refines, depends on, related
    new = _new(
        old, title=title.strip() or old.title, statement=statement,
        rationale=_because(rationale or old.rationale, CHANGED, why), scope=old.scope, project=old.project,
        change=old.change, origin=Origin.DECIDED, actor=OWNER, source=PAGE, owner_words=_words(words or statement),
        state=State.IN_FORCE, links=(Link(type=LinkType.REPLACES, target=old.id), *kept),
    )  # fmt: skip
    return _retire(shared, new, old, f"decisions: {new.id} replaces {old.id}: {_line(new.title, 80)}")


def withdraw(  # noqa: PLR0913 - the owner's reason and the revision he read
    shared: DataRepo | None, project: str, decision_id: str, revision: str, *, reason: str, redecided: bool
) -> list[Receipt]:
    """Withdraw a draft, or a decision in force (no longer relevant, no successor); its rationale records why."""
    why = _reason(reason, "withdrawing a decision")
    view = decision_store.load(shared, project)
    old = _entry(view, decision_id).decision
    if stale := _stale(view, old, revision):
        return stale
    if old.state is not State.DRAFT:
        _in_force(old, "withdrawn")
        authorise(old, owner=True, redecided=redecided)
    update = {"state": State.WITHDRAWN, "conflict": False, "rationale": _because(old.rationale, GONE, why)}
    said = f"decisions: withdraw {old.id}: {_line(why)}"
    return [decision_store.save(shared, old.model_copy(update=update), expected_revision=old.revision, message=said)]


def activate(  # noqa: PLR0913 - the owner's reason and the revision he read
    shared: DataRepo | None, project: str, decision_id: str, revision: str, *, reason: str = "", redecided: bool
) -> list[Receipt]:
    """Put a proposed draft in force: the owner's approval, or his re-decision; what it replaces is replaced with it."""
    view = decision_store.load(shared, project)
    draft = _entry(view, decision_id).decision
    if stale := _stale(view, draft, revision):
        return stale
    if draft.state is not State.DRAFT:
        msg = f"{draft.id} is {draft.state}: only a draft is activated"
        raise Refused(msg)
    targets = dict.fromkeys(link.target for link in draft.links if link.type is LinkType.REPLACES)  # once each
    olds = [_entry(view, target).decision for target in targets]
    update: dict[str, object] = {"state": State.IN_FORCE, "origin": Origin.APPROVED}
    if olds:
        why = _reason(reason, "activating a draft that replaces one")
        update["rationale"] = _because(draft.rationale, CHANGED, why)
    every = _every(shared) if olds else {}
    in_words = draft.origin is Origin.DECIDED and bool(draft.owner_words)
    for old in olds:
        _in_force(old, "replaced")
        authorise(old, owner=True, redecided=redecided)
        second(every, old, decided=redecided or in_words, owner=True)
    if redecided or draft.origin is Origin.DECIDED:  # the owner's words, or the rule he confirmed re-deciding
        update |= {"origin": Origin.DECIDED, "owner_words": draft.owner_words or _words(draft.statement)}
    retired = [(old.model_copy(update={"state": State.REPLACED}), old.revision) for old in olds]
    said = f"decisions: activate {draft.id}: {_line(draft.title, 80)}"
    return decision_store.save_all(shared, [(draft.model_copy(update=update), draft.revision), *retired], message=said)


def promote(shared: DataRepo | None, project: str, decision_id: str, revision: str, *, reason: str) -> list[Receipt]:
    """A linked successor one layer wider (Change to project, project to Global); the source stays, replaced."""
    why = _reason(reason, "promoting a decision")
    view = decision_store.load(shared, project)
    source = _entry(view, decision_id).decision
    if stale := _stale(view, source, revision):
        return stale
    _in_force(source, "promoted")
    if (scope := WIDER.get(source.scope)) is None:
        msg = f"{source.id} is Global already: nothing is wider"
        raise Refused(msg, 422)
    wider = _new(
        source, title=source.title, statement=source.statement, rationale=_because(source.rationale, CHANGED, why),
        scope=scope, project=source.project if scope is Scope.PROJECT else "", change="", origin=source.origin,
        actor=OWNER, source=f"{PAGE}: promoted", owner_words=source.owner_words, state=State.IN_FORCE,
        links=(Link(type=LinkType.PROMOTED_FROM, target=source.id),),
    )  # fmt: skip
    return _retire(shared, wider, source, f"decisions: promote {source.id} to {scope} as {wider.id}")


def exception(  # noqa: PLR0913 - the owner's departure and the revision he read
    shared: DataRepo | None, project: str, decision_id: str, revision: str, *,
    title: str, statement: str, rationale: str, words: str,
) -> list[Receipt]:  # fmt: skip
    """The owner's exception for this project to a Global decision, which stays in force for every other one."""
    view = decision_store.load(shared, project)
    rule = _entry(view, decision_id).decision
    if stale := _stale(view, rule, revision):
        return stale
    if rule.scope is not Scope.GLOBAL or not project:
        msg = f"{rule.id} is a {rule.scope} decision: a project records an exception to a Global one only"
        raise Refused(msg, 422)
    _in_force(rule, "departed from")
    new = _new(
        None, title=title.strip() or f"Exception to {rule.title}", topic=rule.topic, statement=statement,
        rationale=rationale, scope=Scope.PROJECT, project=project, origin=Origin.DECIDED, actor=OWNER,
        source=PAGE, owner_words=_words(words or statement), state=State.IN_FORCE,
        links=(Link(type=LinkType.EXCEPTION_TO, target=rule.id),),
    )  # fmt: skip
    said = f"decisions: {new.id} is {project}'s exception to {rule.id}"
    return [decision_store.save(shared, new, expected_revision=None, message=said)]


def rivals(view: DataView, kept: Decision, shared: DataRepo | None = None) -> list[Decision]:
    """The other in-force successors (replacing or promoting) of what *kept* succeeds: the conflict to resolve.

    With *shared*, rivals in other projects count too: a Global decision's successors may lie in any project.
    """
    targets = {link.target for link in kept.links if link.type in LINEAGE}
    pool = _every(shared).values() if shared else [e.decision for e in view.snapshot.entries]
    return [
        d
        for d in pool
        if d.id != kept.id
        and d.state is State.IN_FORCE
        and targets.intersection(link.target for link in d.links if link.type in LINEAGE)
    ]


def keep(
    shared: DataRepo | None, project: str, decision_id: str, revisions: Mapping[str, str], *, reason: str
) -> list[Receipt]:
    """Resolve a flagged conflict in one commit: *decision_id* stays in force, its competing successors withdrawn."""
    why = _reason(reason, "resolving a conflict")
    view = decision_store.load(shared, project)
    kept = _entry(view, decision_id).decision
    others = rivals(view, kept, shared)
    if not (others or kept.conflict):
        msg = f"{kept.id} is in no conflict"
        raise Refused(msg)
    for decision in (kept, *others):
        if stale := _stale(view, decision, revisions.get(decision.id, "")):
            return stale
    _in_force(kept, "kept")
    gone = [
        (r.model_copy(update={"state": State.WITHDRAWN, "conflict": False,
                              "rationale": _because(r.rationale, GONE, f"{kept.id} was kept: {why}")}), r.revision)
        for r in others
    ]  # fmt: skip
    cleared = (kept.model_copy(update={"conflict": False}), kept.revision)
    said = f"decisions: {kept.id} stays in force; conflict resolved: {_line(why)}"
    return decision_store.save_all(shared, [cleared, *gone], message=said)


def read_back(  # noqa: PLR0913 - who answered and the revision read
    shared: DataRepo | None, project: str, decision_id: str, revision: str, *, answer: str, by: str
) -> list[Receipt]:
    """Record the owner's read-back today; the decision, its origin included, stays as it is."""
    view = decision_store.load(shared, project)
    decision = _entry(view, decision_id).decision
    if stale := _stale(view, decision, revision):
        return stale
    if decision.state in RETIRED:
        msg = f"{decision.id} is {decision.state}: only a draft or a decision in force is read back"
        raise Refused(msg)
    read = decision.model_copy(update={"read_back": _now().date().isoformat()})
    said = f"decisions: read back {decision.id} ({by}): {_line(answer)}"
    return [decision_store.save(shared, read, expected_revision=decision.revision, message=said)]


def propose(  # noqa: PLR0913 - the proposal's fields
    shared: DataRepo | None, project: str, *, title: str, topic: str, statement: str, rationale: str, words: str,
    replaces: str, reason: str = "",
) -> list[Receipt]:  # fmt: skip
    """A chat's draft for this project: `decided` with the owner's words, else `autonomous`; never in force."""
    if not project:
        msg = "decisions are proposed for a project; this host serves none"
        raise Refused(msg, 422)
    links: tuple[Link, ...] = ()
    if replaces:
        old = _entry(decision_store.load(shared, project), replaces).decision
        _in_force(old, "replaced")
        if old.scope is Scope.GLOBAL:
            msg = f"{old.id} is Global: a project departs from it only by an exception the owner records"
            raise Refused(msg, 422)
        authorise(old, owner=False)
        second(_every(shared), old, decided=bool(words.strip()), owner=False)
        rationale = _because(rationale, CHANGED, _reason(reason, "a draft that replaces a decision"))
        links = (Link(type=LinkType.REPLACES, target=old.id),)
    draft = _new(
        None, title=title, topic=topic, statement=statement, rationale=rationale, scope=Scope.PROJECT,
        project=project, origin=Origin.DECIDED if words.strip() else Origin.AUTONOMOUS, actor=CHAT, source=CHAT,
        owner_words=_words(words), state=State.DRAFT, links=links,
    )  # fmt: skip
    said = f"decisions: proposed {draft.id}: {_line(title, 80)}"
    return [decision_store.save(shared, draft, expected_revision=None, message=said)]
