"""What one Change's sessions cost, kept on the Change because the activity log drops old events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Mapping


class ModelSpend(BaseModel):
    """Credits and tokens one model used for a Change; input counts its cache reads and writes."""

    model_config = ConfigDict(extra="forbid")

    credits: float = 0.0
    credits_unread: bool = False  # some session's credits for it were not reported: ``credits`` is a lower bound
    tokens: int = 0
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0


COUNTS = ("tokens", "input", "output", "cache_read", "cache_write")


class Spend(BaseModel):
    """Cumulative usage of a Change's sessions.

    Credits a session did not report are logged and its result still counts; the total is then a lower bound and
    shows as such, never as zero (TD-94).
    """

    model_config = ConfigDict(extra="forbid")

    credits: float = 0.0
    models: dict[str, ModelSpend] = Field(default_factory=dict)
    last: dict[str, Spend] = Field(default_factory=dict)  # each session's high-water marks, per field
    unread: list[str] = Field(default_factory=list)  # the sessions whose credits could not be read

    def plus(self, usage: Mapping[str, Any], session: str = "") -> Spend:
        """Return the total after one session's usage report; a failed report marks only its session unread.

        A session's report is cumulative, so a resumed session adds only its growth over its high-water marks;
        a field a report omits or lowers keeps its mark. A later report with credits clears the session's mark.
        """
        known = "error" not in usage and usage.get("credits") is not None
        others = [s for s in self.unread if s != session]
        unread = others if known or not session else [*others, session]
        if "error" in usage:
            return self._failed(session, unread)
        was = self.last.get(session, Spend()) if session else Spend()
        marks, models = dict(was.models), {k: v.model_copy() for k, v in self.models.items()}
        for name, m in (usage.get("models") or {}).items():
            prior = marks.get(name, ModelSpend())
            marks[name] = high = ModelSpend(
                credits=max(prior.credits, m.get("credits") or 0.0),
                credits_unread=m.get("credits") is None,
                **{f: max(getattr(prior, f), m.get(f) or 0) for f in COUNTS},
            )
            old = models.get(name, ModelSpend())
            models[name] = ModelSpend(
                credits=old.credits + high.credits - prior.credits,
                credits_unread=old.credits_unread or high.credits_unread,
                **{f: getattr(old, f) + getattr(high, f) - getattr(prior, f) for f in COUNTS},
            )
        mark = Spend(credits=max(was.credits, usage.get("credits") or 0.0), models=marks)
        last = self.last | ({session: mark} if session else {})
        for name, total in models.items() if session else ():  # unread while a session's latest report lacks it
            flags = (s.models[name].credits_unread for s in last.values() if name in s.models)
            total.credits_unread = any(flags)
        return Spend(credits=self.credits + mark.credits - was.credits, models=models, last=last, unread=unread)

    def _failed(self, session: str, unread: list[str]) -> Spend:
        """A failed report: the session's models keep their known credits as lower bounds, now marked unread."""
        was = self.last.get(session)
        if was is None:
            return self.model_copy(update={"unread": unread})
        marks = {n: m.model_copy(update={"credits_unread": True}) for n, m in was.models.items()}
        models = {
            n: m.model_copy(update={"credits_unread": m.credits_unread or n in marks}) for n, m in self.models.items()
        }
        last = self.last | {session: was.model_copy(update={"models": marks})}
        return self.model_copy(update={"unread": unread, "models": models, "last": last})

    def shown(self) -> str:
        """The total as text: a lower bound with the unread sessions named, or unknown, never a false zero."""
        if not self.unread:
            return f"{self.credits:.2f} credits"
        n = len(self.unread)
        unknown = f"unknown for {n} session{'s' if n != 1 else ''}"
        return f"{self.credits:.2f}+ credits ({unknown})" if self.credits else f"credits {unknown}"
