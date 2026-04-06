---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Approve full architecture"
notes: ""
# >> Agent metadata (do not edit)
task_id: 387
agent: researcher
created: 2026-04-01
urgency: blocking
decision_type: feature-gate
impact_tier: 3
---

# Decision: Approve memory-mcp server architecture?

## Context

Task #387 designed a dedicated memory-mcp server for per-agent institutional knowledge. The design builds on DR #428 (resolved, patterns 1/2/4/6 adopted) and #499 research (concrete schema). Full design: `docs/research/memory-mcp-server-design.md`.

This is T3: adds a new MCP server package, new agent capability, and modifies agent pipeline behavior (auto-loading, write mechanism).

## Options

### A: Approve full architecture ← (rec:) recommended

SQLite-backed mcp-memory with 4 tools (get_knowledge, record_learning, list_entries, mark_for_deletion), 4D scoping, single-path configurable storage, pending/approved/deleted workflow.

- Effort: ~5 implementation tasks at ideation
- Trade-off: SQLite is not human-readable (mitigated by list_entries tool)
- Risk: low — follows established MCP server patterns

### B: Approve architecture + add dedup and token budgeting

Same as A, plus: (a) content_hash field for whitespace-normalized dedup (pattern 3 from deer-flow), (b) max_tokens parameter on get_knowledge for token-budgeted injection (pattern 5). These were not in DR #428 but are recommended by #499 research as basic quality controls.

- Effort: same 5 tasks, ~30 LOC additional
- Trade-off: dedup prevents duplicate entries; token budgeting ensures usable response sizes. Requires choosing a tokenizer approach (character estimate or tiktoken dependency).
- Risk: low — additive features

### C: Embed in knowledge-mcp instead of separate server

Extend the existing mcp-knowledge server with a memory_entries table rather than creating a 4th custom MCP server. Avoids new package, new setup.py entry, new MCP connection.

- Effort: ~3 tasks (simpler, fewer moving parts)
- Trade-off: mixes domain knowledge (entities, documents, graph) with agent memory (conclusions, patterns) in one server. Violates separation of concerns stated in #387 task body.
- Risk: medium — scope creep in knowledge-mcp

### D: Defer / do nothing

- Effort: 0
- Trade-off: agents continue using /memories/repo/inbox/ (unscoped, not auto-loaded, not cross-project)
- Risk: none immediate; knowledge accumulation remains manual

## Recommendation

.78 confidence — Option A. The architecture is proven (follows 3 existing MCP servers), addresses all 4 gaps in the current system, and respects DR #428 binding constraints. Option B is a low-cost addition; decision on patterns 3/5 can be made here or deferred to the architect stage.

## Impact of Deferral

Task #387 is blocked. 5 follow-up implementation tasks at ideation cannot proceed. No other tasks are directly blocked. This is T3 — does not auto-resolve.
