---
id: 1846
title: 'P2-07: assess_memories MCP tool'
status: research
priority: needed
created: 2026-05-24T19:01:40.081966+02:00
updated: 2026-05-24T19:15:17.429675+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on:
  - 1841
  - 1844
  - 1845
ac:
  - '`assess_memories` MCP tool registered on the memory server accepts `assessments:
    list[{entry_id: str, bucket: str}]` and `task_id: str`. `task_id` is an opaque
    caller-provided string identifying the current task context (not validated beyond
    non-empty). Valid bucket values: outstanding, unremarkable, didnt_use, factually_wrong.
    Invalid bucket value raises ToolError with allowed values listed.'
  - 'For each assessment: validates entry exists and is in voteable state (approved,
    curated, contested); increments the corresponding counter (outstanding_count,
    unremarkable_count, or didnt_use_count); recomputes score via compute_score; triggers
    check_slot_efficiency; for factually_wrong bucket calls record_factually_wrong(entry_id,
    task_id, expected_updated_at=entry.updated_at). Returns list of per-entry results
    with entry_id and success/error.'
  - Non-existent entry_id or non-voteable state produces a failure result for 
    that entry (with error message) without aborting remaining assessments in 
    the batch. Successful entries are persisted to disk atomically per entry.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

New MCP tool that processes batch assessment submissions from agents at end-of-task.

### In Scope
- assess_memories tool definition (server.py + tools.py)
- Input validation (bucket enum, entry existence, voteable state)
- Counter increment + score recomputation
- Slot-efficiency trigger after counter update
- Confirmation cycle trigger for factually_wrong
- Per-entry success/failure response
- Batch semantics (one failure doesn't abort others)

### Out of Scope
- Score computation logic (P2-02, consumed)
- Slot-efficiency logic (P2-05, consumed)
- Confirmation cycle logic (P2-06, consumed)
- Recall slot changes (P2-04)

## Domain
serve/mcp-memory/