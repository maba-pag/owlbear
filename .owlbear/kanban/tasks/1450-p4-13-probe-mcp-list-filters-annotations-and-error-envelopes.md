---
id: 1450
title: 'P4-13: Probe MCP list filters, annotations, and error envelopes'
status: todo
priority: needed
created: 2026-05-08T19:32:15.603480+00:00
updated: 2026-05-08T21:47:29.024006+00:00
tags:
- phase-4
- scope:mcp-kanban
- type:test
- verification-probe
- filters
- errors
- annotations
- deployment-readiness
parent: 1437
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: MCP and agent-view contract probes for filters, status-destination validation, tool annotations, descriptions, and error envelopes.
Out of scope: source changes, Cockpit UI, agent guidance, docs, and full-suite proof.

## Acceptance Criteria
1. Test-writer records a list_tasks probe where ids=[] returns an empty tasks list and no missing_ids entry for a scratch board containing tasks.
2. Test-writer records an archival_reason probe where list_tasks with archival_reason=duplicate and no status argument searches archive storage and returns archived tasks with that reason.
3. Test-writer records contract inspection showing status-changing entrypoints use one destination-validation helper for move_task and end_work destination handling.
4. Test-writer records MCP schema inspection showing move_task is not idempotent, pick_tasks is read-only and idempotent, and descriptions match the post-remediation side effects.
5. Test-writer records MCP error-envelope inspection where invalid status, invalid priority, malformed ID, and stale write errors surface code and message fields instead of raw traceback text.
6. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probes and MCP schema inspection.
[[2026-05-08]]


## Architecture Review

### AC Refinements

Original AC3 claimed "one destination-validation helper" — this is an internal structural claim, not an externally observable contract. Scope says "contract probes" and "out of scope: source changes." Revised to focus on MCP boundary behavior.

Original AC4 included "descriptions match post-remediation side effects" — layer mismatch: the DR-resolution mention is in AgentView's internal docstring, not the MCP tool description. Dropped docstring check; focused on schema annotations.

Original AC5 assumed all error paths use `_map_kanban_error()`. Challenger identified that `parse_task_id()` raises raw `ToolError(msg)` without structured {code, message} envelope. Probe correctly captures this gap as a TDD RED assertion.

### Refined AC (supersedes original)
1. Test-writer records a list_tasks probe where ids=[] returns an empty tasks list and no missing_ids entry for a scratch board containing tasks. (td:2)
2. Test-writer records an archival_reason probe where list_tasks with archival_reason=duplicate and no status argument searches archive storage and returns archived tasks with that reason. (td:2)
3. Test-writer records a contract probe asserting that both move_task(status=invalid) and end_work(outcome='reject', move_to=invalid) reject unrecognized destination values with a structured error envelope containing code and message fields. (td:2)
4. Test-writer records MCP schema inspection asserting: (a) move_task annotation has idempotentHint=False, and (b) pick_tasks annotations have readOnlyHint=True and idempotentHint=True. (td:1)
5. Test-writer records MCP error-envelope inspection where invalid status, invalid priority, malformed ID, and stale write errors each surface a JSON payload with code and message fields rather than raw text or traceback strings. (td:2)
6. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probes and MCP schema inspection. (td:0)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All AC lines probe MCP contract aspects |
| Interface clarity | PASS | Refined AC3/AC4 are externally observable |
| Dependency correctness | PASS | Root probe, no dependencies |
| Module layering | PASS | Probes only, no implementation |
| TDD compliance | PASS | This IS the test task (type:test) |
| KISS/YAGNI | PASS | Focused scope |
| Premise challenge | PASS | Parent #1437 approved direction justifies probes |
| Pattern consistency | PASS | Follows sibling probe pattern (1438, 1440, etc.) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:mcp-kanban only |

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Challenger Notes
- Challenger verdict: reconsider (confidence 0.46)
- Key concerns addressed: (1) AC3 structural claim revised to behavioral contract, (2) AC4 layer mismatch corrected by dropping docstring check, (3) malformed-ID envelope gap acknowledged in AC5, (4) existing test_tool_annotations_494.py conflict noted — implementation task #1451 updates those tests, not this probe
- Architect response: accepted all four substantive concerns and revised AC3, AC4, AC5 accordingly. Remaining blind spot about existing engine-level tests is acceptable — probe targets MCP boundary format, not engine validation logic.

### Verdict: APPROVE
### Action Taken: Refined AC3 (behavioral contract), AC4 (annotations only), AC5 (malformed-ID gap). Advanced to todo.
[[2026-05-08]]
Architecture review complete. Refined AC3 (behavioral contract instead of structural helper claim), AC4 (annotations only, dropped docstring layer mismatch), AC5 (acknowledged malformed-ID envelope gap). Challenger concerns accepted and incorporated. All 10 criteria PASS. Test-writer: PROCEED (max td:2).