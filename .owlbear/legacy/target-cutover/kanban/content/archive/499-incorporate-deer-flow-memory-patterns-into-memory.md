---
id: 499
title: Incorporate deer-flow memory patterns into memory-mcp design (#387)
status: archived
priority: medium
created: 2026-03-31 13:40:21.370194+02:00
updated: 2026-04-04 07:30:43.137471+02:00
started: 2026-04-04 07:30:33.235830+02:00
completed: 2026-04-04 07:30:33.235830+02:00
tags:
- research
- scope:agents
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Research #428 identified 6 transferable patterns from deer-flow's memory system for OwlBear's memory-mcp (#387). Pending approval of DR: docs/decisions/pending/428-adopt-deer-flow-memory-patterns.md

Patterns to incorporate:
1. Fact schema: id/content/category/confidence/createdAt/source
2. Confidence threshold gating (0.7 default, configurable per scope)
3. Whitespace-normalized content deduplication
4. Max-capacity pruning (drop lowest confidence when limit exceeded)
5. Token-budgeted injection (MCP tool returns token-counted set)
6. Category taxonomy: preference/knowledge/context/behavior/goal

See docs/research/deer-flow-memory-subagent-deep-dive.md sections 3A-3C and 4.

## Acceptance Criteria
- [ ] All 6 patterns documented as concrete schema/interface definitions in #387 design
- [ ] Adaptation notes for OwlBear's 4D scoping model (how deer-flow categories map)
- [ ] Any deviations from deer-flow patterns justified with rationale

depends_on: #387

[[2026-03-31]] Tue 14:28
## Research
Doc: docs/research/deer-flow-memory-patterns-schema-definitions.md

Key deliverables:
- Concrete MemoryEntry schema with 12 fields (deer-flow 6 + OwlBear 6 extensions)
- 4D scope resolution via nullable scope_agent/scope_project matrix
- Confidence gating spec (0.7 default, configurable per scope)
- Soft-delete pruning per DR customization (no permanent delete by agents)
- Category taxonomy mapping to OwlBear agent contexts
- MCP tool interface: get_knowledge, record_learning, list_entries, mark_for_deletion
- Gap flagged: DR omits patterns 3 (dedup) and 5 (token-budgeted injection), recommend adopting both

Tier: T1 (executing on approved DR, no new capability decisions)

[[2026-04-01]] Wed 01:54
## Researcher Update (Decision Resolution)
DR resolved (docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md). User approved custom subset:

Approved patterns (binding constraints for #387 design):
1. Fact schema (id/content/category/confidence/createdAt/source) -- adopt unchanged
2. Confidence threshold gating (0.7 default) -- adopt unchanged
4. Max-capacity pruning -- CUSTOMIZED: mark for deletion and hide from output, but only user may actually delete (no automatic permanent deletion)
6. Category taxonomy (preference/knowledge/context/behavior/goal) -- adopt unchanged

NOT approved (do NOT incorporate):
3. Whitespace-normalized content dedup -- not selected
5. Token-budgeted injection -- not selected

AC should be read against approved patterns only, not all 6.
