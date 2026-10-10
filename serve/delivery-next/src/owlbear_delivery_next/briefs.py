"""Brief drafts: validate and write a new Change, or a new version of a shaping one, awaiting approval."""

from __future__ import annotations

import contextlib
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import loop, profile, tools
from owlbear_delivery_next.models import (
    Change,
    Criterion,
    Exit,
    Names,
    Outcome,
    PersonCheck,
    Profile,
    StepKind,
    VisualState,
    Waiting,
)
from owlbear_delivery_next.store import LockHeldError, StoreError

if TYPE_CHECKING:
    from owlbear_delivery_next.store import Store


def drafted(old: Change | None, d: tools.BriefDraft, slug: str, handle: str, prof: Profile) -> Change:
    """The Change with its new brief draft version, waiting for the owner's approval; criteria and checks versioned."""
    names = Names(branch=f"owlbear/{slug}", target=profile.value(prof, profile.DEFAULT, "main"))
    c = old or Change(slug=slug, handle=handle, profile_version=prof.version, names=names)
    before = {k.id: k for k in c.brief.criteria}
    criteria = []
    for i, text in enumerate(d.criteria, 1):
        prev = before.get(f"AC-{i}")
        criteria.append(Criterion(id=f"AC-{i}", text=text, version=prev.version + (prev.text != text) if prev else 1))
    shown_states = {s.name: s for s in c.brief.visual}
    visual = []
    for s in d.visual:
        prev_state = shown_states.get(s.name)
        moved = prev_state and (prev_state.path, prev_state.expect) != (s.path, s.expect)
        version = prev_state.version + bool(moved) if prev_state else 1
        visual.append(VisualState(name=s.name, path=s.path, expect=s.expect, version=version))
    v = c.brief.version + 1
    fields = {"version": v, "title": d.title, "outcome": d.outcome, "scope": d.scope, "criteria": criteria}
    fields |= {"ui": d.ui, "visual": visual}
    c.brief = c.brief.model_copy(update=fields)
    ids, paths, shown = [k.id for k in criteria], loop.coverage(c), {p.id: p for p in c.checks}
    c.checks = []
    for p in d.person_checks:
        prev = shown.get(p.name)
        procedure = prev.procedure + ((prev.steps, prev.expect) != (p.steps, p.expect)) if prev else 1
        c.checks.append(
            PersonCheck(id=p.name, criteria=ids, steps=p.steps, expect=p.expect, paths=paths, procedure=procedure)
        )
    c.outcome = Outcome(
        exit=Exit.PENDING, waiting=Waiting.CHAT, who="you", reason=f"approve brief v{v}", at=datetime.now(UTC)
    )
    return c


def new_slug(title: str, taken: list[str]) -> str:
    """A free slug from the title."""
    base = "-".join(re.findall(r"[a-z0-9]+", title.lower()))[:40].strip("-") or "change"
    return next(s for n in range(1, 1000) if (s := base if n == 1 else f"{base}-{n}") not in taken)


def save_brief(store: Store, body: object) -> tuple[int, dict[str, Any]]:
    """Validate a brief draft and write a new Change, or a new version of a shaping one, awaiting approval."""
    draft, errors = tools.parse(tools.BriefDraft, body)
    errors = tools.check_brief(draft) if draft else errors
    if draft is None or errors:
        return 422, {"errors": errors}
    handles = {}
    for s in (slugs := store.slugs()):
        with contextlib.suppress(StoreError):
            handles[store.read(s).handle] = s
    slug = handles.get(draft.change) if draft.change else new_slug(draft.title, slugs)
    if slug is None:
        return 422, {"errors": [f"change: {draft.change} is not a Change here - leave it empty for a new one"]}
    number = max((int(h[1:]) for h in handles if h[1:].isdigit()), default=0) + 1
    try:
        with store.lock(slug) as lock:
            old = store.read(slug) if draft.change else None
            if old and (old.step.kind != StepKind.SHAPE or old.finished_at):
                return 409, {"errors": [f"change: {draft.change} is approved; ask for changes in the Changes page"]}
            c = drafted(old, draft, slug, f"c{number}", store.read_profile() or Profile())
            store.write(lock, c)
    except (LockHeldError, StoreError) as exc:
        return 409, {"errors": [f"change: {exc}; try again"]}
    return 200, {"change": c.handle, "version": c.brief.version, "slug": slug}
