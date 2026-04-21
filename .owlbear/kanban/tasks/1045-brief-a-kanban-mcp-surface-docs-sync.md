---
id: 1045
title: Brief A — Kanban MCP Surface + Docs Sync
status: todo
priority: needed
created: 2026-04-21T09:48:09.660203+00:00
updated: 2026-04-21T10:55:18.219366+00:00
tags:
- phase:mcp
- brief:a
- scope:kanban
parent:
depends_on:
- 1044
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief

Source brief: .owlbear/briefs/kanban-mcp-surface-v2/brief.md
Upstream engine contract: parent task 1044 and .owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md

Scope: MCP tool schemas, adapter wiring, response envelopes, docs and skill sync, and MCP-facing tests after the engine/backend contract is stable.

## Planner Source

Decompose from kanban-mcp-surface-v2/brief.md, using Brief B paper-integration.md as the upstream implementation contract.
Include downstream sync work for share/skills/h-mcp-kanban/SKILL.md, serve/mcp-kanban/README.md, and any MCP-facing tests that lock the new surface.

## Notes

- This is the top layer in the implementation chain.
- Do not create cockpit UI/product tasks here.

[[2026-04-21]]
## Planning

### Task Breakdown

| ID | Title | Type | Depends On | Priority |
|---|---|---|---|---|
| #1084 | A-01: RED — MCP boundary models tests | tdd:red | #1066 (Brief B models GREEN) | needed |
| #1085 | A-02: GREEN — MCP boundary models | tdd:green | #1084 | critical |
| #1086 | A-03: RED — read tool adapter tests | tdd:red | #1085 | needed |
| #1087 | A-04: RED — mutation tool adapter tests | tdd:red | #1085 | needed |
| #1088 | A-05: RED — lifecycle tool adapter tests | tdd:red | #1085 | needed |
| #1089 | A-09: RED — guidance + error mapping tests | tdd:red | #1085 | needed |
| #1090 | A-06: GREEN — read tool adapters | tdd:green | #1086 | critical |
| #1091 | A-07: GREEN — mutation tool adapters | tdd:green | #1087, #1090 | critical |
| #1092 | A-08: GREEN — lifecycle tool adapters | tdd:green | #1088, #1091 | critical |
| #1093 | A-10: GREEN — guidance + error mapping | tdd:green | #1089, #1092 | needed |
| #1094 | A-11: docs sync — h-mcp-kanban skill + README | docs | #1093 | needed |

### Dependency Graph

```
#1066 (Brief B models GREEN)
  └─ #1084 (A-01 RED models)
       └─ #1085 (A-02 GREEN models)
            ├─ #1086 (A-03 RED reads)
            │    └─ #1090 (A-06 GREEN reads)
            │         └─ #1091 (A-07 GREEN mutations)
            │              └─ #1092 (A-08 GREEN lifecycle)
            │                   └─ #1093 (A-10 GREEN guidance)
            │                        └─ #1094 (A-11 docs sync)
            ├─ #1087 (A-04 RED mutations) ──→ #1091
            ├─ #1088 (A-05 RED lifecycle) ──→ #1092
            └─ #1089 (A-09 RED guidance) ──→ #1093
```

### Layers
1. **L1** (#1084): MCP boundary models RED — cross-brief gate on Brief B #1066
2. **L2** (#1085): MCP boundary models GREEN — gate for all tool tests
3. **L3** (#1086, #1087, #1088, #1089): 4 RED test tasks — parallelizable
4. **L4** (#1090 → #1091 → #1092 → #1093): 4 GREEN impl tasks — serialized on server.py
5. **L5** (#1094): docs sync — last

### Design Notes
- Cross-brief dependency: #1084 → #1066 (Brief B models GREEN). MCP response envelopes reuse engine projection types (TaskSummary, TaskFull, etc.) so engine models must be implemented and importable before MCP model tests can be written.
- Adapter is a mechanical translator per paper-integration.md §1 ("1:1 signature passthrough", "Adapter is mechanical (O6)"). All business logic in engine via AgentView.
- All adapter tests mock AgentView — no engine integration in Brief A scope.
- GREEN impl tasks serialize on server.py to avoid merge conflicts: reads → mutations → lifecycle → guidance.
- AC13 (edit_task rejects status param) enforced at adapter schema level, not engine.