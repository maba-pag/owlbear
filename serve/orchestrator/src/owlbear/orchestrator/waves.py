"""Wave assembly for the orchestrator dispatch loop.

Implements the four-bucket algorithm that groups dispatch entries into
parallel execution waves while respecting agent-type compatibility rules.
"""

from __future__ import annotations

import dataclasses
from enum import StrEnum

from owlbear.planner.models import DispatchEntry


class AgentCategory(StrEnum):
    """Compatibility category for wave-assembly bucketing."""

    AUDITOR = "auditor"
    BUILDER = "builder"
    LIGHT_FLEX = "light_flex"
    HEAVY_FLEX = "heavy_flex"


AGENT_CATEGORY: dict[str, AgentCategory] = {
    "auditor": AgentCategory.AUDITOR,
    "builder": AgentCategory.BUILDER,
    "researcher": AgentCategory.LIGHT_FLEX,
    "doc-writer": AgentCategory.LIGHT_FLEX,
    "architect": AgentCategory.LIGHT_FLEX,
    "planner": AgentCategory.LIGHT_FLEX,
    "curator": AgentCategory.LIGHT_FLEX,
    "reviewer": AgentCategory.HEAVY_FLEX,
    "test-writer": AgentCategory.HEAVY_FLEX,
}


@dataclasses.dataclass
class Wave:
    """A single parallel dispatch wave containing one or more entries."""

    entries: list[DispatchEntry] = dataclasses.field(default_factory=list)


def assemble_waves(
    entries: list[DispatchEntry],
    wave_size: int,
    cycle: int,
) -> list[Wave]:
    """Assemble dispatch entries into waves using the four-bucket algorithm.

    Args:
        entries: Priority-ordered dispatch entries from the planner.
        wave_size: Maximum entries per wave.
        cycle: Current loop cycle number (used for periodic curator injection).

    Returns:
        List of Wave objects ready for sequential dispatch.
    """
    auditors = [e for e in entries if AGENT_CATEGORY.get(e.agent) == AgentCategory.AUDITOR]
    builders = [e for e in entries if AGENT_CATEGORY.get(e.agent) == AgentCategory.BUILDER]
    light_flex = [e for e in entries if AGENT_CATEGORY.get(e.agent) == AgentCategory.LIGHT_FLEX]
    heavy_flex = [e for e in entries if AGENT_CATEGORY.get(e.agent) == AgentCategory.HEAVY_FLEX]

    remaining_light = list(light_flex)
    remaining_heavy = list(heavy_flex)
    waves: list[Wave] = []

    # Phase 2 — Auditor waves: one auditor per wave, fill with light flex
    for auditor in auditors:
        slots = wave_size - 1
        fill = remaining_light[:slots]
        remaining_light = remaining_light[slots:]
        waves.append(Wave(entries=[auditor, *fill]))

    # Phase 3 — Builder waves: one builder per wave, light flex first then heavy flex
    for builder in builders:
        slots = wave_size - 1
        light_fill = remaining_light[:slots]
        remaining_light = remaining_light[len(light_fill) :]
        remaining_slots = slots - len(light_fill)
        heavy_fill = remaining_heavy[:remaining_slots]
        remaining_heavy = remaining_heavy[len(heavy_fill) :]
        waves.append(Wave(entries=[builder, *light_fill, *heavy_fill]))

    # Phase 4 — Overflow: remaining flex agents chunked into wave_size batches
    remaining_all = remaining_light + remaining_heavy
    waves += [Wave(entries=remaining_all[i : i + wave_size]) for i in range(0, len(remaining_all), wave_size)]

    # Phase 5 — Periodic curator: inject into last wave with a free slot
    if cycle % 5 == 0 and waves:
        curator_entry = DispatchEntry(task_id=0, agent="curator", target_status="done")
        for wave in reversed(waves):
            if len(wave.entries) < wave_size:
                wave.entries.append(curator_entry)
                break

    # Phase 6 — Consolidation: DEACTIVATED (per task #146 AC). SKIP.

    # Phase 7 — Drop rule: remove solo non-auditor waves unless doing so would
    # leave an empty wave list (exception: keep the first one in that case).
    solo_non_auditor = [
        w for w in waves if len(w.entries) == 1 and AGENT_CATEGORY.get(w.entries[0].agent) != AgentCategory.AUDITOR
    ]
    solo_ids = {id(w) for w in solo_non_auditor}
    non_solo = [w for w in waves if id(w) not in solo_ids]

    if non_solo:
        waves = non_solo
    elif solo_non_auditor:
        waves = [solo_non_auditor[0]]

    return waves
