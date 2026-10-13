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
    tokens: int = 0
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0


COUNTS = ("tokens", "input", "output", "cache_read", "cache_write")


class Spend(BaseModel):
    """Cumulative usage of a Change's sessions."""

    model_config = ConfigDict(extra="forbid")

    credits: float = 0.0
    models: dict[str, ModelSpend] = Field(default_factory=dict)
    last: dict[str, Spend] = Field(default_factory=dict)  # each session's high-water marks, per field

    def plus(self, usage: Mapping[str, Any], session: str = "") -> Spend:
        """Return the total after one session's usage report; a failed report adds nothing.

        A session's report is cumulative, so a resumed session adds only its growth over its high-water marks;
        a field a report omits or lowers keeps its mark.
        """
        if "error" in usage:
            return self
        was = self.last.get(session, Spend()) if session else Spend()
        marks, models = dict(was.models), {k: v.model_copy() for k, v in self.models.items()}
        for name, m in (usage.get("models") or {}).items():
            prior = marks.get(name, ModelSpend())
            marks[name] = high = ModelSpend(
                credits=max(prior.credits, m.get("credits") or 0.0),
                **{f: max(getattr(prior, f), m.get(f) or 0) for f in COUNTS},
            )
            old = models.get(name, ModelSpend())
            models[name] = ModelSpend(
                credits=old.credits + high.credits - prior.credits,
                **{f: getattr(old, f) + getattr(high, f) - getattr(prior, f) for f in COUNTS},
            )
        mark = Spend(credits=max(was.credits, usage.get("credits") or 0.0), models=marks)
        last = self.last | ({session: mark} if session else {})
        return Spend(credits=self.credits + mark.credits - was.credits, models=models, last=last)
