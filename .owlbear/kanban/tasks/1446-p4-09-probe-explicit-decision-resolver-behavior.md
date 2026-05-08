---
id: 1446
title: 'P4-09: Probe explicit decision resolver behavior'
status: todo
priority: needed
created: 2026-05-08T19:32:04.227422+00:00
updated: 2026-05-08T21:33:42.361306+00:00
tags:
- phase-4
- scope:mcp-kanban
- type:test
- verification-probe
- decisions
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
In scope: MCP decision-resolution contract probes and retry-safety inspection.
Out of scope: Cockpit decision UI, agent guidance, and full-suite proof.

## Acceptance Criteria
1. Test-writer records a scratch-board resolve_drs probe where a pending DR with response approved is resolved through the MCP tool, the file moves to decisions/resolved, the linked task is unblocked, and one canonical summary appears in the task body.
2. Test-writer records a retry probe where the same resolve_drs request is repeated and the linked task body receives no second copy of the canonical summary.
3. Test-writer records a needs-info probe where the DR moves to decisions/resolved, the canonical summary is appended once, and the linked task remains blocked.
4. Test-writer records MCP schema inspection showing resolve_drs is a named tool and pick_tasks does not reference DR resolution helpers.
5. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probe notes and MCP schema inspection.
[[2026-05-08]]

## Architect Refinement

**AC1 clarification:** Changed "the MCP tool" → "the resolve_drs MCP tool" for explicitness. The probe specifies expected behavior of the not-yet-existing resolve_drs tool that #1447 will implement.

**Test depth:** All AC lines are td:0 (probe notes, no test code). Test-writer: SKIP (type:test pass-through). Probes serve as contract specification for #1447.

**Refined AC (with test-depth annotations):**
1. Test-writer records a scratch-board resolve_drs probe where a pending DR with response approved is resolved through the resolve_drs MCP tool, the file moves to decisions/resolved, the linked task is unblocked, and one canonical summary appears in the task body. (td:0)
2. Test-writer records a retry probe where the same resolve_drs request is repeated and the linked task body receives no second copy of the canonical summary. (td:0)
3. Test-writer records a needs-info probe where the DR moves to decisions/resolved, the canonical summary is appended once, and the linked task remains blocked. (td:0)
4. Test-writer records MCP schema inspection showing resolve_drs is a named tool and pick_tasks does not reference DR resolution helpers. (td:0)
5. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probe notes and MCP schema inspection. (td:0)
[[2026-05-08]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: define probe specification for decision resolver MCP behavior |
| Interface clarity | PASS (after refinement) | AC1 clarified to name resolve_drs explicitly; AC2-5 clear |
| Dependency correctness | PASS | No dependencies — correct as root probe |
| Module layering | N/A | No source changes |
| TDD compliance | PASS | type:test pass-through; probes serve as contract spec for #1447 |
| KISS/YAGNI | PASS | Minimal scope — notes-only deliverable |
| Premise challenge | PASS | Probes define contract before #1447 implementation; resolve_pending_drs exists in decisions.py but no MCP tool yet, pick_tasks calls it as side effect — both facts confirm probe is needed |
| Pattern consistency | PASS | Follows probe-before-implementation pattern from parent #1437 decomposition (matches #1438 sibling) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | mcp-kanban domain only |
| Failure Mode Map | N/A | No codepaths modified |
| Decision-request verification | N/A | No research doc referenced; parent #1437 has approved direction |
| User-action detection | SKIP | Counter-signal C3: type:test tag present |

### Codebase Context
- resolve_pending_drs: serve/kanban/src/owlbear_kanban/decisions.py L155-210 — handles approved/rejected (unblock+summary+move), needs-info (summary+move, stays blocked)
- pick_tasks side effect: serve/kanban/src/owlbear_kanban/agent_view.py L383-391 — calls decisions.resolve_pending_drs(self.engine) before dispatch
- create_dr MCP tool: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py L319-340 — exists, resolve_drs does not
- canonical_summary: decisions.py L72-77 — returns "## Decision Request\n- response: {response}\n- source: {body}"

### Refinement Applied
- AC1: "the MCP tool" → "the resolve_drs MCP tool" for explicitness

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 per Step 2.1

### Test Depth
- All AC lines: td:0 (probe notes, no test code)
- Max depth: td:0
- Test-writer: SKIP (type:test pass-through)

### Verdict: APPROVE
### Action Taken: Minor AC1 refinement for tool name clarity. Kept type:test tag and notes-based probe format. Advanced to todo.