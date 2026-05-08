---
id: 1452
title: 'P4-15: Probe create_dr guidance and pipeline integration'
status: todo
priority: needed
created: 2026-05-08T19:32:26.111021+00:00
updated: 2026-05-08T21:42:28.970409+00:00
tags:
- phase-4
- scope:agents
- type:test
- verification-probe
- create-dr
- guidance
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
In scope: pipeline-agent guidance and MCP create_dr contract probes.
Out of scope: resolve_drs implementation, Cockpit decision UI, docs, and full-suite proof.

## Acceptance Criteria
1. Test-writer records MCP schema inspection showing create_dr is registered with task_id, agent, request_type, and body inputs plus a structured created/path response. (td:0)
2. Test-writer records a scratch-board create_dr probe where the tool creates a pending file under decisions/pending/, records task_id in file frontmatter, and blocks the referenced task with reason "DR pending" — without manual file writes by the caller. (td:0)
3. Test-writer records guidance inspection showing (a) the runtime block guidance message names create_dr, and (b) the h-decision-requests handbook lists the required fields (task_id, agent, request_type, body). (td:0)
4. Test-writer records instruction inspection showing pipeline agents (researcher, architect, builder, reviewer, auditor, test-writer) are told to use create_dr for decision or action requests instead of writing files under decisions directories. (td:0)
5. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probes, MCP schema inspection, and guidance artifact inspection. (td:0)

[[2026-05-08]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused on probing create_dr guidance and pipeline integration only |
| Interface clarity | PASS | Refined: linkage mechanism specified (frontmatter + blocks), guidance surfaces named (runtime + handbook) |
| Dependency correctness | PASS | Root probe, no dependencies — correct for pre-implementation verification |
| Module layering | N/A | Verification probe, no implementation code |
| TDD compliance | PASS | Tagged type:test for pass-through; AC5 explicitly scopes evidence to probes |
| KISS/YAGNI | PASS | Minimal scope — inspect and record, nothing more |
| Premise challenge | PASS | create_dr exists (server.py:310-341, decisions.py:89-150), guidance references exist (h-decision-requests, r-pipeline-protocol, 6 agent files), probe validates integration surface before #1453 |
| Pattern consistency | PASS | Follows verification-probe pattern of sibling root probes (1438, 1440, 1442, 1444, 1446, 1448, 1450, 1454) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | scope:agents only |

### AC Refinements Applied

| AC | Change | Reason |
|----|--------|--------|
| AC2 | "links it to the requested task" → "records task_id in file frontmatter, and blocks the referenced task with reason 'DR pending'" | Challenger: ambiguous linkage claim |
| AC3 | Added (a) runtime block guidance message and (b) h-decision-requests handbook as explicit targets | Challenger: multiple guidance surfaces not disambiguated |
| AC4 | Scoped "pipeline agents" to six named agents | Challenger: unscoped agent surface |

### Challenge Results
- Challenger: reconsider (0.56)
- Key concerns: td routing consistency, guidance contract mismatch, ambiguous linkage, agent scope
- Architect response: accepted and addressed — td:0 applied to all lines (consistent with sibling probes, AC5 prohibits test execution); guidance "mismatch" was scribe agent vs MCP tool layers (not contradictory); AC2 and AC4 refined for precision
- Post-refinement assessment: concerns resolved, approve stands

### Test Depth
- All AC lines: td:0
- Max depth: 0
- Test-writer: SKIP (non-impl pass-through via type:test tag)

### Verdict: APPROVE
### Action Taken: Refined AC2/AC3/AC4 for precision, annotated td:0, advanced to todo