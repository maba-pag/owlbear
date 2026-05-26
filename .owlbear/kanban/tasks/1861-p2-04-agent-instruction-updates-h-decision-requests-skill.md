---
id: 1861
title: 'P2-04: Agent instruction updates — h-decision-requests skill'
status: in-progress
priority: needed
created: 2026-05-24T20:59:38.739082+02:00
updated: 2026-05-26T02:03:02.332302+02:00
tags:
  - phase-2
  - scope:docs
  - docs
parent: 1850
depends_on:
  - 1855
ac:
  - SKILL.md documents the three MCP tools (create_request, list_requests, 
    show_request) with parameter signatures, required vs optional params, and 
    one usage example per tool.
  - SKILL.md documents the structured data model fields (request_id, task_id, 
    kind, title, summary, agent, options, resolution) with types, constraints, 
    and kind-specific validation rules.
  - SKILL.md documents the resolution lifecycle (pending/ to resolved/ 
    transition, write-back format variants, conditional unblock semantics) so 
    agents consume structured answers via show_request.
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Rewrite `share/skills/h-decision-requests/SKILL.md` for structured model
- Document MCP tool parameters and usage patterns
- Document data model field definitions and validation rules
- Document lifecycle (create → pending → resolved → write-back)
- Document kind-specific behavior (decision vs action)

**Out of scope:**
- Code changes (documentation only)
- Cockpit UI documentation (separate from agent skills)
- Old create_dr tool docs (remove references)

## Test scope
Skip (docs/config only per domain mapping)

[[2026-05-26T00:38:57+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single deliverable: rewrite h-decision-requests SKILL.md |
| Interface clarity | PASS | AC names exact tools, fields, lifecycle phases to document |
| Dependency correctness | PASS | #1855 archived/completed — MCP tools exist in server.py:459-525 |
| Module layering | N/A | Documentation only |
| TDD compliance | PASS | proof_bundle=skip, docs tag → test-writer pass-through |
| KISS/YAGNI | PASS | Documentation matches implemented scope, no speculative content |
| Premise challenge | PASS | Existing SKILL.md documents retired create_dr; new tools (#1855) need agent-facing docs |
| Pattern consistency | PASS | Follows established skill file structure (YAML frontmatter + sections) |
| Security surface | N/A | No system boundary changes |
| Single domain | PASS | scope:docs only |

### Design Diverge
- Trigger: skipped — single clear approach (rewrite SKILL.md from implementation + brief)

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### AC Assessment
| AC | Assessment | Action |
|----|-----------|--------|
| AC1: MCP tool docs (create_request, list_requests, show_request) with signatures, params, examples | Precise — source of truth is server.py:459-525 | None |
| AC2: Data model fields with types, constraints, kind-specific rules | Precise — source of truth is request_models.py (RequestRecord, RequestOption, Resolution) | None |
| AC3: Resolution lifecycle (pending→resolved, write-back, conditional unblock) | Precise — three distinct components named | None |

### Notes
- Builder source material: brief at .owlbear/briefs/draft-decision-request-data-model/brief.md, implementation at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459-525, models at serve/kanban/src/owlbear_kanban/request_models.py
- Task already carries pass-through tag `docs`
- No resolve_request MCP tool exists (resolution is Cockpit-only) — SKILL.md should note this explicitly for agent guidance

### Verdict: APPROVE
### Action Taken: AC verified precise against implemented code. Advanced to todo.

[[2026-05-26T00:55:49+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Tagged `docs` (scope:docs); AC describes SKILL.md documentation only, no testable Python interfaces.
- Passing through to builder.

[[2026-05-26T01:21:57+02:00]]
## Builder Notes
- Implementation: rewrote `share/skills/h-decision-requests/SKILL.md` to document structured request workflows (`create_request`, `list_requests`, `show_request`) and removed obsolete guidance as primary path.
- Tests: skipped by design (`proof_bundle: skip`, docs-only task).
- Coverage: n/a (documentation-only change).
- Lint: n/a (documentation-only change).
- Evidence summary:
  - MCP tool contracts aligned to `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (`create_request`, `list_requests`, `show_request`).
  - Data model and validation rules aligned to `serve/kanban/src/owlbear_kanban/request_models.py` (`RequestOption`, `Resolution`, discriminated `DecisionRequest|ActionRequest`).
  - Lifecycle semantics aligned to `serve/kanban/src/owlbear_kanban/engine.py` (`create_request`, `resolve_request`, `sweep_requests`, write-back formatting, conditional unblock).
  - Explicitly documented that MCP does not expose `resolve_request`; resolution remains Cockpit/user mediated.
- Commit: `834be4ec` — `docs: rewrite decision-request skill for structured MCP model (#1861, builder)`.

### Reflection
- Source-of-truth drift was the main risk: old handbook centered on legacy `create_dr`; resolved by grounding every section in current server/model/engine code paths.
- Most important guardrail was documenting lifecycle behavior from engine semantics (write-back variants + sibling-pending conditional unblock), not from UI assumptions.
- No blockers encountered; scope remained surgical to one skill file.

[[2026-05-26T02:03:02+02:00]]
## Review Evidence
- Verdict: FAIL
- Review scope: builder-declared documentation change in share/skills/h-decision-requests/SKILL.md with proof bundle `skip`.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3: SKILL.md documents the resolution lifecycle (pending/ to resolved/ transition, write-back format variants, conditional unblock semantics) so agents consume structured answers via show_request. | The lifecycle section claims the file "moves atomically" to resolved, but the engine performs two separate operations: it creates the resolved file and then deletes the pending file. The documentation is therefore not aligned to the implemented transition semantics. | share/skills/h-decision-requests/SKILL.md:190; serve/kanban/src/owlbear_kanban/engine.py:1164, 1173, 1176; serve/kanban/src/owlbear_kanban/engine.py:1209, 1268, 1271 | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Correct the pending/resolved transition wording so it matches the actual engine behavior, or restate the guarantee without claiming an atomic move. | share/skills/h-decision-requests/SKILL.md | AC3; share/skills/h-decision-requests/SKILL.md:190; serve/kanban/src/owlbear_kanban/engine.py:1164, 1173, 1176, 1209, 1268, 1271 |

## Observations
- Builder evidence was otherwise sufficient for a docs-only `skip` bundle: the MCP tool signatures and return-shape notes in share/skills/h-decision-requests/SKILL.md:34-135 align with serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459-520.
- The data-model and validation sections in share/skills/h-decision-requests/SKILL.md:142-178 align with serve/kanban/src/owlbear_kanban/request_models.py:21-135 and the resolution guards in serve/kanban/src/owlbear_kanban/engine.py:1234-1250.
- The write-back variants and conditional unblock semantics in share/skills/h-decision-requests/SKILL.md:195-202 align with serve/kanban/src/owlbear_kanban/engine.py:1098-1116 and serve/kanban/src/owlbear_kanban/engine.py:1181-1187 plus 1273-1276.
- No independent quality-runner rerun was needed because the task is documentation-only and the blocking issue is a source-of-truth mismatch in the reviewed file.
