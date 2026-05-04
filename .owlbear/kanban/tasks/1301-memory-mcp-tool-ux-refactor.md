---
id: 1301
title: Memory MCP Tool UX Refactor
status: todo
priority: needed
created: 2026-05-04T01:25:41.522821+00:00
updated: 2026-05-04T01:35:23.439268+00:00
tags:
- memory
- mcp
- phase-2
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Brief\n\nSee `.owlbear/briefs/draft-memory-mcp-ux/brief.md` — approved 2026-05-04.\n\nReshape MCP memory tool surface from 5 broken tools to 7 audience-separated tools (2 general + 4 curator + 1 user). Code-enforced state machine (pending→curated→approved), scope model (curator-assigned), state-dependent deletion, per-tool registration, staged rollout (curator-first). 42 design decisions. Start fresh (no migration).\n\n## Objective\n\nDeliver a working MCP memory system that agents can save to and recall from, with curator quality control and user approval.\n\n## Acceptance Criteria\n\n- [ ] 7 MCP tools registered with correct parameter schemas and validation\n- [ ] State machine: auto-promote, auto-downgrade (unconditional), scope gate\n- [ ] State-dependent deletion: hard-delete pending, soft-delete curated/approved\n- [ ] Recall: priority-ordered (approved first, curated fill), body-only, agent-scoped\n- [ ] Access control: per-tool registration in agent .agent.md files\n- [ ] Git: save uncommitted, curator batch-commit, review batch-commit\n- [ ] Consumer updates: agent wiring, skill rewrites, memory-review.prompt.md\n- [ ] Staged rollout: curator → pilot → full → review prompt\n- [ ] All env var access control removed (OWLBEAR_MEMORY_CALLER, MEMORY_TOOLS_EXCLUDE)\n- [ ] Tests: state machine, scope filtering, deletion, recall ordering, validation
\n\n## Planning\n### Decomposition: Memory MCP Tool UX Refactor\n- Tasks created: 14\n- Dependency layers: 6\n- Phase: 2\n\n### Task List\n| ID | Title | Priority | Depends On | Tags |\n|----|-------|----------|------------|------|\n| #1302 | P1-01: RED — Schema model tests | needed | — | phase-2, scope:mcp-memory |\n| #1303 | P1-02: GREEN — Schema models | needed | #1302 | phase-2, scope:mcp-memory |\n| #1304 | P1-03: RED — State machine tests | needed | #1303 | phase-2, scope:mcp-memory |\n| #1305 | P1-04: GREEN — State machine | needed | #1304 | phase-2, scope:mcp-memory |\n| #1306 | P1-05: RED — Mutation tool tests | needed | #1305 | phase-2, scope:mcp-memory |\n| #1307 | P1-06: GREEN — Mutation tools + access control removal | critical | #1306 | phase-2, scope:mcp-memory |\n| #1308 | P1-07: RED — Recall tool tests | needed | #1305 | phase-2, scope:mcp-memory |\n| #1309 | P1-08: GREEN — Recall implementation | needed | #1308, #1307 | phase-2, scope:mcp-memory |\n| #1310 | P1-09: RED — Git integration tests | needed | #1307 | phase-2, scope:mcp-memory |\n| #1311 | P1-10: GREEN — Git integration | needed | #1310 | phase-2, scope:mcp-memory |\n| #1312 | P1-11: Consumer Phase 1 — Curator wiring + skills | needed | #1307 | phase-2, scope:agents |\n| #1313 | P1-12: Consumer Phase 2-3 — All agents + instructions | important | #1312, #1309 | phase-2, scope:agents |\n| #1314 | P1-13: Review prompt | important | #1312 | phase-2, scope:prompts |\n| #1315 | P1-14: Integration test — full lifecycle | important | #1309, #1311 | phase-2, scope:mcp-memory |\n\n### Dependency Graph\n```mermaid\ngraph TD\n  1302[P1-01: Schema tests] --> 1303[P1-02: Schema impl]\n  1303 --> 1304[P1-03: State machine tests]\n  1304 --> 1305[P1-04: State machine impl]\n  1305 --> 1306[P1-05: Mutation tool tests]\n  1306 --> 1307[P1-06: Mutation tools impl]\n  1305 --> 1308[P1-07: Recall tests]\n  1308 --> 1309[P1-08: Recall impl]\n  1307 --> 1309\n  1307 --> 1310[P1-09: Git tests]\n  1310 --> 1311[P1-10: Git impl]\n  1307 --> 1312[P1-11: Consumer Phase 1]\n  1312 --> 1313[P1-12: Consumer Phase 2-3]\n  1309 --> 1313\n  1312 --> 1314[P1-13: Review prompt]\n  1309 --> 1315[P1-14: Integration test]\n  1311 --> 1315\n```
[[2026-05-04]]
## Planning\n\nDecomposed #1301 into 14 subtasks (5 TDD-RED + 5 TDD-GREEN + 3 consumer/content + 1 integration test) across 6 dependency layers.\n\nCritical path: #1302 → #1303 → #1304 → #1305 → #1306 → #1307 (mutation tools — 3 dependents, critical priority).\n\nParallel branch after #1305: recall tests (#1308) can start alongside mutation tool tests (#1306).\n\nParallel branches after #1307: git integration (#1310→#1311), recall impl (#1309), and consumer Phase 1 (#1312) all unblock independently.\n\nAll tasks created at status=research with parent=#1301.