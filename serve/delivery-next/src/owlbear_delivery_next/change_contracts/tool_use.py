"""How agents' calls of each Delivery tool went (C-28 T8), kept on the Change as the activity log drops old events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Mapping


class ToolTally(BaseModel):
    """One tool's calls: refused by a schema or check, refused by lint only, after the step ended, and retried."""

    model_config = ConfigDict(extra="forbid")

    calls: int = 0
    rejected: int = 0
    lint: int = 0
    late: int = 0
    retries: int = 0  # calls whose previous call of the same tool in the step was refused


class ToolUse(BaseModel):
    """Each tool's tally over a Change's sessions."""

    model_config = ConfigDict(extra="forbid")

    tools: dict[str, ToolTally] = Field(default_factory=dict)

    def plus(self, counts: Mapping[str, Mapping[str, int]]) -> ToolUse:
        """Return the total after one run's counts, tool name to tally field to count."""
        tools = dict(self.tools)
        for name, n in counts.items():
            was = tools.get(name, ToolTally())
            tools[name] = ToolTally(**{f: getattr(was, f) + n.get(f, 0) for f in ToolTally.model_fields})
        return ToolUse(tools=tools)
