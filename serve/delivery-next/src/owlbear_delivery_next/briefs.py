"""Brief drafts: validate and write a new Change, or a new version of a shaping one, awaiting approval."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import brief_rounds, brief_tools, evidence, profile, tool_schema
from owlbear_delivery_next.models import (
    BriefDecision,
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
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.store import HANDLE, LockHeldError, StoreError

if TYPE_CHECKING:
    from owlbear_delivery_next.store import Store

SLUG = 40


def drafted(old: Change | None, d: brief_tools.BriefDraft, slug: str, handle: str, prof: Profile) -> Change:
    """The Change with its new brief draft version, waiting for the owner's approval; criteria and checks versioned."""
    names = Names(branch=f"owlbear/{slug}", target=profile.value(prof, profile.DEFAULT, "main"))
    c = old or Change(slug=slug, handle=handle, profile_version=prof.version, names=names)
    before = {k.id: k for k in c.brief.criteria}
    criteria = []
    for i, text in enumerate(d.criteria, 1):
        prev = before.get(f"AC-{i}")
        criteria.append(Criterion(id=f"AC-{i}", text=text, version=prev.version + (prev.text != text) if prev else 1))
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
    fields = {"version": v, "title": d.title, "outcome": d.outcome, "scope": d.scope, "criteria": criteria}
    owner = [*d.specified, *(f"screen:{s.name}" for s in d.visual if s.owner)]
    owner += [f"check:{p.name}" for p in d.person_checks if p.owner]
    fields |= {"ui": d.ui, "visual": visual, "non_goals": d.non_goals, "specified": list(dict.fromkeys(owner))}
    fields["decisions"] = [BriefDecision(**x.model_dump()) for x in d.decisions]
    c.brief = c.brief.model_copy(update=fields)
    if c.step.mode == brief_rounds.PLANNED:  # a new version waits for its own challenge and approval
        c.step = c.step.model_copy(update={"mode": None})
    ids, paths, shown = [k.id for k in criteria], evidence.coverage(c), {p.id: p for p in c.checks}
    c.checks = []
    for p in d.person_checks:
        prev = shown.get(p.name)
        changed = (prev.steps, prev.expect, prev.visual) != (p.steps, p.expect, p.visual) if prev else False
        procedure = prev.procedure + changed if prev else 1
        fields = {"id": p.name, "criteria": ids, "steps": p.steps, "expect": p.expect, "visual": p.visual}
        c.checks.append(PersonCheck(**fields, paths=paths, procedure=procedure))
    c.outcome = Outcome(
        exit=Exit.PENDING, waiting=Waiting.CHAT, who="you", reason=f"challenge brief v{v}, then approve it",
        at=datetime.now(UTC),
    )  # fmt: skip
    return c


def new_slug(title: str, taken: list[str]) -> str:
    """A free slug from the title's whole words within 40 characters; a longer first word is cut."""
    words, base = re.findall(r"[a-z0-9]+", title.lower()), ""
    for w in words:
        if len(f"{base}-{w}" if base else w) > SLUG:
            break
        base = f"{base}-{w}" if base else w
    base = base or (words[0][:SLUG] if words else "change")
    return next(s for n in range(1, 1000) if (s := base if n == 1 else f"{base}-{n}") not in taken)


def _handles(store: Store) -> dict[str, str]:
    """Each issued handle and its Change; an unloadable Change still holds its number."""
    handles = {}
    for s in store.slugs():
        try:
            handles[store.read(s).handle] = s
        except StoreError:
            if raw := store.raw_handle(s):
                handles.setdefault(raw, s)
    return handles


def _visual_of(c: Change) -> dict[str, Any]:
    """A Change's visual check as draft fields."""
    states = [{"name": s.name, "path": s.path, "expect": s.expect, "owner": f"screen:{s.name}" in c.brief.specified}
              for s in c.brief.visual]  # fmt: skip
    steps = [{"state": s.name} | x.model_dump() for s in c.brief.visual for x in s.steps]
    return {"ui": c.brief.ui, "visual": states, "steps": steps}


def _kept(store: Store, body: object) -> object:
    """A revision that sends no visual check keeps the Change's; the chat's brief tool never sends one."""
    if not (isinstance(body, dict) and body.get("change")) or {"ui", "visual", "steps"} & body.keys():
        return body
    try:
        slug = _handles(store).get(body["change"])
        return body | _visual_of(store.read(slug)) if slug else body
    except StoreError:
        return body


def save_brief(store: Store, body: object) -> tuple[int, dict[str, Any]]:
    """Validate a brief draft and write a new Change, or a new version of a shaping one, awaiting approval."""
    draft, errors = tool_schema.parse(brief_tools.BriefDraft, _kept(store, body))
    errors = brief_tools.check_brief(draft) if draft else errors
    if draft is None or errors:
        return 422, {"errors": errors}
    handles, slugs = _handles(store), store.slugs()
    slug = handles.get(draft.change) if draft.change else new_slug(draft.title, slugs)
    if slug is None:
        return 422, {"errors": [f"change: {draft.change} is not a Change here - leave it empty for a new one"]}
    number = max((int(h[1:]) for h in handles if HANDLE.fullmatch(h)), default=0)
    number = max(number, store.issued()) + 1
    try:
        with store.lock(slug) as lock:
            old = store.read(slug) if draft.change else None
            if old and (old.step.kind != StepKind.SHAPE or old.finished_at):
                return 409, {"errors": [f"change: {draft.change} is approved; ask for changes in the Changes page"]}
            if old and (why := brief_rounds.saving(old)):
                return 409, {"errors": [f"change: {why}"]}
            if old is None:
                store.issue(number)  # reserved before the Change file holds it
            c = drafted(old, draft, slug, f"c{number}", store.read_profile() or Profile())
            store.write(lock, c)
    except (LockHeldError, StoreError) as exc:
        return 409, {"errors": [f"change: {exc}; try again"]}
    return 200, {"change": c.handle, "version": c.brief.version, "slug": slug}


def save_visual(store: Store, body: object) -> tuple[int, dict[str, Any]]:
    """Set a shaping Change's UI flag, states and steps as a new brief version; the rest of its brief stays."""
    draft, errors = tool_schema.parse(brief_tools.VisualDraft, body)
    if draft is None:
        return 422, {"errors": errors}
    if (slug := _handles(store).get(draft.change)) is None:
        return 422, {"errors": [f"change: {draft.change} is not a Change here - use a handle from show_status"]}
    try:
        c = store.read(slug)
    except StoreError as exc:
        return 409, {"errors": [f"change: {exc}"]}
    owner = set(c.brief.specified)
    checks = [{"name": p.id, "steps": p.steps, "expect": p.expect, "visual": p.visual,
               "owner": f"check:{p.id}" in owner} for p in c.checks]  # fmt: skip
    brief = {"change": draft.change, "title": c.brief.title, "outcome": c.brief.outcome, "scope": c.brief.scope}
    brief |= {"criteria": [k.text for k in c.brief.criteria], "person_checks": checks, "ui": draft.ui}
    brief |= {"non_goals": c.brief.non_goals, "decisions": [x.model_dump() for x in c.brief.decisions]}
    brief |= {"specified": [k.id for k in c.brief.criteria if k.id in owner]}
    brief |= {"visual": [s.model_dump() for s in draft.states], "steps": [s.model_dump() for s in draft.steps]}
    return save_brief(store, brief)
