---
id: 1312
title: 'P1-11: Consumer updates Phase 1 — Curator agent wiring + skill rewrites (h-mcp-memory,
  h-memory-structure, w-mem-curation)'
status: in-progress
priority: needed
created: 2026-05-04T01:32:27.358510+00:00
updated: 2026-05-05T09:12:55.023406+00:00
tags:
- phase-2
- scope:agents
- memory
- mcp
- agent
parent: 1301
depends_on:
- 1307
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] memory-curator.agent.md tools: include ob-memory/list_memories, ob-memory/read_memory, ob-memory/curate_memory, ob-memory/delete_memory (td:0)
- [ ] vscode/memory removed from memory-curator.agent.md (td:0)
- [ ] h-mcp-memory skill fully rewritten: 6 tool names, parameters, descriptions, usage patterns, examples (td:0)
- [ ] h-memory-structure skill updated: new fields (source_agent, approved_at), renamed categories, state model (td:0)
- [ ] w-mem-curation skill updated: new MCP tool names, auto-state logic documentation, guidance hints (td:0)
- [ ] Curator can exercise full lifecycle: list -> read -> curate -> delete via MCP tools (td:0)

## Scope

- In: curator agent file, 3 skill files (h-mcp-memory, h-memory-structure, w-mem-curation)
- Out: general pipeline agents (Phase 2-3, task #1313), review prompt, instruction stubs
[[2026-05-05]]
## Research

**Key findings:** MCP memory server (#1307) shipped 6 tools (save_memory, list_memories, read_memory, curate_memory, delete_memory, approve_memory) replacing the old 5-tool API. Three category values renamed (knowledge→domain-knowledge, tool→tool-usage, context→env-context). Two new schema fields (source_agent: required/frozen, approved_at: nullable). Auto-state logic: pending→curated when scope_agents added, approved→curated on any edit. Hard vs soft delete by state.

**Trade-off matrix:** N/A — mechanical mapping, no design choices.

**Confidence:** 0.92 — direct rewrite against stable shipped implementation.

**Research doc:** .owlbear/research/consumer-updates-p1-curator-memory.md

**Follow-ups:** None needed — task #1312 itself is the implementation unit.
[[2026-05-05]]

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All 4 files serve one purpose: align memory curator ecosystem with shipped MCP API |
| Interface clarity | PASS | AC names exact tool paths, fields, and behaviors (after 7→6 refinement) |
| Dependency correctness | PASS | #1307 (MCP memory server) archived/done; recall (#1309) correctly excluded |
| Module layering | PASS | Agent/skill markdown files — no import structure |
| TDD compliance | PASS | Non-implementation task, all td:0 |
| KISS/YAGNI | PASS | Mechanical mapping, no abstraction introduced |
| Premise challenge | PASS | Skills referencing old 5-tool API will mislead agents — update necessary |
| Pattern consistency | PASS | Tool naming follows `ob-memory/{tool_name}` per VS Code MCP conventions |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Memory domain only |

### AC Refinement
- AC3: "7 tool names" → "6 tool names" — `recall_memory` exists in tools.py but is NOT registered in server.py; task #1309 (recall GREEN) is in-progress and not a dependency. Document shipped tools only: save_memory, list_memories, read_memory, curate_memory, delete_memory, approve_memory.
- AC6 ("Curator can exercise full lifecycle") is a functional correctness statement verifiable by reading the wired tools list — retained as-is.
- Added `agent` pass-through tag for test-writer pipeline routing.

### Challenge Results
- Challenger: SKIPPED — all AC lines are td:0 (documentation-only task)

### Test Depth
- AC1: (td:0) — agent file tool list edit
- AC2: (td:0) — agent file tool removal
- AC3: (td:0) — skill rewrite (markdown)
- AC4: (td:0) — skill field/enum updates (markdown)
- AC5: (td:0) — skill tool name + logic docs (markdown)
- AC6: (td:0) — verifiable by reading AC1 tool list against w-mem-curation workflow
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC3 (7→6 tools), added `agent` pass-through tag, advancing to todo.
[[2026-05-05]]
Architecture review complete. Refined AC3 (7→6 tool names — recall_memory not yet registered in server.py). Added `agent` pass-through tag for test-writer routing. All criteria PASS. Challenger skipped (all td:0). Advancing to todo.
[[2026-05-05]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All 6 AC lines are annotated (td:0): agent file tool list edits and skill markdown rewrites only.
- Passing through to builder.