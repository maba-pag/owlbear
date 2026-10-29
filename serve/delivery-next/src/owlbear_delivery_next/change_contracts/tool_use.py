"""How agents' calls of each Delivery tool went (C-28 T8), kept on the Change as the activity log drops old events.

The Change's page shows the spend ledger's tally instead (``tool_metrics.of_change``), which also holds stopped runs;
the kept one serves the retro and the Change's data record. A wrong tool choice is a call at the wrong moment
(``order``, a part of a tool's refusals), a guard denial that was no bypass attempt, a turn ended without a result
tool, or a pointless missing-tool report (one of ``WRONG``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Mapping

WRONG = ("denied", "no_result", "missing_pointless")  # the wrong tool choices a run counts beside its tools' tallies


class ToolTally(BaseModel):
    """One tool's calls: refused by a schema or check, refused by lint only, after the step ended, and retried.

    ``invalid``, ``checks`` and ``order`` split ``rejected``: invalid arguments, failed checks and the wrong moment.
    Calls counted before the split leave a remainder of ``rejected`` that none of them holds.
    """

    model_config = ConfigDict(extra="forbid")

    calls: int = 0
    rejected: int = 0
    invalid: int = 0
    checks: int = 0
    order: int = 0
    lint: int = 0
    late: int = 0
    retries: int = 0  # calls whose previous call of the same tool in the step was refused


class ToolUse(BaseModel):
    """Each tool's tally over a Change's sessions, and its sessions' other wrong tool choices by kind."""

    model_config = ConfigDict(extra="forbid")

    tools: dict[str, ToolTally] = Field(default_factory=dict)
    wrong: dict[str, int] = Field(default_factory=dict)

    def plus(self, counts: Mapping[str, Mapping[str, int]], wrong: Mapping[str, int] | None = None) -> ToolUse:
        """Return the total after one run's counts, tool name to tally field to count, and its wrong choices."""
        tools = dict(self.tools)
        for name, n in counts.items():
            was = tools.get(name, ToolTally())
            tools[name] = ToolTally(**{f: getattr(was, f) + n.get(f, 0) for f in ToolTally.model_fields})
        more = dict(self.wrong)
        for kind, n in (wrong or {}).items():
            more[kind] = more.get(kind, 0) + n
        return ToolUse(tools=tools, wrong=more)
