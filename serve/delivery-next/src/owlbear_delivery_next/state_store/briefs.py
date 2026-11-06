"""Brief drafts: validate and write a new Change, or a new version of a shaping one, awaiting approval."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from itertools import count
from typing import TYPE_CHECKING, Any

from owlbear_decisions import new_id
from owlbear_delivery_next.change_contracts import chat_contract, evidence, tool_schema
from owlbear_delivery_next.change_contracts.models import (
    BriefDecision,
    BriefRecipe,
    Change,
    Criterion,
    Exit,
    Names,
    Outcome,
    PersonCheck,
    StepKind,
    VisualState,
    VisualStep,
    Waiting,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import brief_rounds, brief_tools, shaping_capture
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import identities
from owlbear_delivery_next.state_store.store import LockHeldError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Brief
    from owlbear_delivery_next.change_contracts.shaper_records import SavingChat
    from owlbear_delivery_next.state_store.store import Store

SLUG = 40


def drafted(old: Change | None, d: brief_tools.BriefDraft, slug: str, handle: str, prof: Profile) -> Change:
    """The Change with its new brief draft version, waiting for the owner's approval; criteria and checks versioned."""
    names = Names(branch=f"owlbear/{slug}", target=profile.value(prof, profile.DEFAULT, "main"))
    c = old or Change(slug=slug, handle=handle, profile_version=prof.version, names=names)
    before, criteria = c.brief.criteria, []
    held = {k.id for v in c.brief.approved for k in v.criteria}  # a revert may bring any of them back
    for i, text in enumerate(d.criteria, 1):  # the draft names the nth criterion AC-n, whatever its id (positions)
        prev = before[i - 1] if i <= len(before) else None
        taken = held | {k.id for k in (*before, *criteria)}
        ident = prev.id if prev else next(f"AC-{n}" for n in count(i) if f"AC-{n}" not in taken)
        criteria.append(Criterion(id=ident, text=text, version=prev.version + (prev.text != text) if prev else 1))
    placed = {f"AC-{n}": k.id for n, k in enumerate(criteria, 1)}
    shown_states, v = {s.name: s for s in c.brief.visual}, c.brief.version + 1
    visual = []
    for s in d.visual:
        steps = [VisualStep(do=x.do, target=x.target, text=x.text) for x in d.steps if x.state == s.name]
        prev = shown_states.get(s.name)
        same = prev and (prev.path, prev.expect, prev.steps) == (s.path, s.expect, steps)
        # a new or changed state takes the new brief version: no earlier draft, removed or not, ever had it
        visual.append(
            VisualState(name=s.name, path=s.path, expect=s.expect, steps=steps, version=prev.version if same else v)
        )
    fields = {
        "version": v,
        "title": d.title,
        "outcome": d.outcome,
        "scope": d.scope,
        "criteria": criteria,
        "saving_chat": None,
    }
    c.shaper_notice = None
    owner = [*(placed.get(k, k) for k in d.specified), *(f"screen:{s.name}" for s in d.visual if s.owner)]
    owner += [f"check:{p.name}" for p in d.person_checks if p.owner]
    fields |= {"ui": d.ui, "visual": visual, "non_goals": d.non_goals, "specified": list(dict.fromkeys(owner))}
    fields |= {"recipe": BriefRecipe(**d.recipe.model_dump()) if d.recipe else None, "preparation": d.preparation}
    fields["decisions"] = _decisions(c, d)
    c.brief = c.brief.model_copy(update=fields)
    c.shaped = shaping_capture.requested(c)  # its current pages are captured before approval
    if c.step.mode == brief_rounds.PLANNED:  # a new version waits for its own challenge and approval
        c.step = c.step.model_copy(update={"mode": None})
    ids, paths, shown = [k.id for k in criteria], evidence.coverage(c), {p.id: p for p in c.checks}
    c.checks = []
    for p in d.person_checks:
        prev = shown.get(p.name)
        covers = [placed.get(k, k) for k in p.covers] or ids  # an amendment redoes only the checks it changes
        same = prev and (prev.steps, prev.expect, prev.visual, prev.criteria) == (p.steps, p.expect, p.visual, covers)
        procedure = prev.procedure + (not same) if prev else 1
        fields = {"id": p.name, "criteria": covers, "steps": p.steps, "expect": p.expect, "visual": p.visual}
        c.checks.append(PersonCheck(**fields, paths=paths, procedure=procedure))
    c.outcome = Outcome(
        exit=Exit.PENDING, waiting=Waiting.CHAT, who="you", reason=f"challenge brief v{v}, then approve it",
        at=datetime.now(UTC),
    )  # fmt: skip
    return c


def positions(b: Brief) -> dict[str, str]:
    """Each criterion's id as a draft names it: AC-n for the nth, whatever id an amendment left it (TD-185)."""
    return {k.id: f"AC-{n}" for n, k in enumerate(b.criteria, 1)}


def _decisions(c: Change, d: brief_tools.BriefDraft) -> list[BriefDecision]:
    """The draft's decisions; one asking a question the previous version asked keeps its identity (TD-419).

    Once an answer was approved it is never edited: a changed answer or scope becomes a successor that replaces it.
    """
    now, key = datetime.now(UTC), brief_tools.question_key
    previous = {key(x.question): x for x in c.brief.decisions}
    accepted = {x.id: x for b in c.brief.approved for x in b.decisions if x.id}
    found = []
    for x in d.decisions:
        ident, replaces = _identity(previous.get(key(x.question)), (x.answer, x.scope), accepted, now)
        found.append(BriefDecision(**x.model_dump(), id=ident, replaces=replaces))
    return found


def _identity(
    prev: BriefDecision | None, said: tuple[str, str], accepted: dict[str, BriefDecision], now: datetime
) -> tuple[str, str]:
    """(id, replaces) for a decision whose previous version is *prev* and whose answer and scope are *said*.

    A published project decision keeps its file's layer, so a changed scope is a successor too (TD-453).
    """
    if prev is None or not prev.id:
        return new_id(now), ""
    if prev.id in accepted:  # approved as it stands: kept while its answer and scope are, else a successor
        return (prev.id, prev.replaces) if _said(accepted[prev.id]) == said else (new_id(now), prev.id)
    if (back := accepted.get(prev.replaces)) and _said(back) == said:  # back to the approved answer
        return back.id, back.replaces
    return prev.id, prev.replaces


def _said(d: BriefDecision) -> tuple[str, str]:
    return d.answer, d.scope


def new_slug(title: str, taken: list[str]) -> str:
    """A free slug from the title's whole words within 40 characters; a longer first word is cut."""
    words, base = re.findall(r"[a-z0-9]+", title.lower()), ""
    for w in words:
        if len(f"{base}-{w}" if base else w) > SLUG:
            break
        base = f"{base}-{w}" if base else w
    base = base or (words[0][:SLUG] if words else "change")
    return next(s for n in range(1, 1000) if (s := base if n == 1 else f"{base}-{n}") not in taken)


def _visual_of(c: Change) -> dict[str, Any]:
    """A Change's visual check as draft fields."""
    states = [{"name": s.name, "path": s.path, "expect": s.expect, "owner": f"screen:{s.name}" in c.brief.specified}
              for s in c.brief.visual]  # fmt: skip
    steps = [{"state": s.name} | x.model_dump() for s in c.brief.visual for x in s.steps]
    recipe = c.brief.recipe.model_dump() if c.brief.recipe else None
    return {"ui": c.brief.ui, "visual": states, "steps": steps, "recipe": recipe, "preparation": c.brief.preparation}


def _kept(store: Store, body: object) -> object:
    """A revision that sends no visual check keeps the Change's; the chat's brief tool never sends one."""
    if not (isinstance(body, dict) and body.get("change")) or {"ui", "visual", "steps"} & body.keys():
        return body
    try:
        slug = identities.handles(store).get(body["change"])
        return body | _visual_of(store.read(slug)) if slug else body
    except StoreError:
        return body


def save_brief(
    store: Store, body: object, contract: str | None = None, *, binding: Callable[[], SavingChat] | None = None
) -> tuple[int, dict[str, Any]]:
    """Validate a brief draft and write a new Change, or a new version of a shaping one, awaiting approval.

    A chat of an earlier *contract* than ``chat_contract.CAPTURES`` sends no render recipe; its draft gets no capture.
    """
    draft, errors = tool_schema.parse(brief_tools.BriefDraft, _kept(store, body))
    errors = brief_tools.check_brief(draft, recipe=chat_contract.captures(contract)) if draft else errors
    if draft is None or errors:
        return 422, {"errors": errors}
    draft, errors = _prepared(store, draft)
    if errors:
        return 422, {"errors": errors}
    return _revise(store, draft, binding) if draft.change else _create(store, draft, binding)


def _prepared(store: Store, d: brief_tools.BriefDraft) -> tuple[brief_tools.BriefDraft, list[str]]:
    """The draft with the test preparation its capture runs on: the one named, else the project's only one.

    Without a declared option the draft keeps none, and its capture ends saying so (D-01M6Q56RXK85C5T4AG7R051X6N).
    """
    if not (d.ui and d.visual and d.recipe):
        return d, []
    declared = [o.id for o in store.settings().preparations]
    if d.preparation:
        known = d.preparation in declared
        return d, [] if known else [f"preparation: {d.preparation} is not declared - use one of {declared or 'none'}"]
    if len(declared) > 1:
        return d, [f"preparation: empty while the project declares several - name one of {', '.join(declared)}"]
    return d.model_copy(update={"preparation": declared[0] if declared else ""}), []


def unrevisable(c: Change) -> str:
    """Why the shaper may not save a new brief version of *c* now, or ""."""
    if c.step.kind != StepKind.SHAPE or c.finished_at:
        return f"{c.handle} is approved; ask for changes in the Changes page"
    return brief_rounds.saving(c)


def _revise(
    store: Store, draft: brief_tools.BriefDraft, binding: Callable[[], SavingChat] | None = None
) -> tuple[int, dict[str, Any]]:
    if (slug := identities.handles(store).get(draft.change)) is None:
        return 422, {"errors": [f"change: {draft.change} is not a Change here - leave it empty for a new one"]}
    try:
        with store.lock(slug) as lock:
            old = store.read(slug)
            if why := unrevisable(old):
                return 409, {"errors": [f"change: {why}"]}
            c = drafted(old, draft, slug, old.handle, store.read_profile() or Profile())
            c.brief.saving_chat = binding() if binding else None
            store.write(lock, c)
    except LockHeldError as exc:
        return 409, {"errors": [f"change: {exc}; try again"]}
    except StoreError as exc:
        return 409, {"errors": [f"change: {failure(exc)}; try again"]}
    return 200, {"change": c.handle, "version": c.brief.version, "slug": slug}


def _create(
    store: Store, draft: brief_tools.BriefDraft, binding: Callable[[], SavingChat] | None = None
) -> tuple[int, dict[str, Any]]:
    try:
        prof = store.read_profile() or Profile()
        caller = binding() if binding else None

        def made(number: int, taken: list[str]) -> Change:
            c = drafted(None, draft, new_slug(draft.title, taken), f"c{number}", prof)
            c.brief.saving_chat = caller
            return c

        c = identities.publish_new(store, made)
    except StoreError as exc:
        return 409, {"errors": [f"change: {failure(exc)}; try again"]}
    return 200, {"change": c.handle, "version": c.brief.version, "slug": c.slug}


def save_visual(
    store: Store, body: object, contract: str | None = None, *, binding: Callable[[], SavingChat] | None = None
) -> tuple[int, dict[str, Any]]:
    """Set a shaping Change's UI flag, states and steps as a new brief version; the rest of its brief stays."""
    draft, errors = tool_schema.parse(brief_tools.VisualDraft, body)
    if draft is None:
        return 422, {"errors": errors}
    if (slug := identities.handles(store).get(draft.change)) is None:
        return 422, {"errors": [f"change: {draft.change} is not a Change here - use a handle from show_status"]}
    try:
        c = store.read(slug)
    except StoreError as exc:
        return 409, {"errors": [f"change: {failure(exc)}"]}
    owner, placed = set(c.brief.specified), positions(c.brief)
    checks = [{"name": p.id, "steps": p.steps, "expect": p.expect, "covers": [placed.get(k, k) for k in p.criteria],
               "visual": p.visual, "owner": f"check:{p.id}" in owner} for p in c.checks]  # fmt: skip
    brief = {"change": draft.change, "title": c.brief.title, "outcome": c.brief.outcome, "scope": c.brief.scope}
    brief |= {"criteria": [k.text for k in c.brief.criteria], "person_checks": checks, "ui": draft.ui}
    brief |= {
        "non_goals": c.brief.non_goals,
        "decisions": [x.model_dump(exclude={"id", "replaces"}) for x in c.brief.decisions],
    }
    brief |= {"specified": [placed[k.id] for k in c.brief.criteria if k.id in owner]}
    brief |= {"visual": [s.model_dump() for s in draft.states], "steps": [s.model_dump() for s in draft.steps]}
    brief |= {"recipe": draft.recipe.model_dump() if draft.recipe else None, "preparation": draft.preparation}
    return save_brief(store, brief, contract, binding=binding)
