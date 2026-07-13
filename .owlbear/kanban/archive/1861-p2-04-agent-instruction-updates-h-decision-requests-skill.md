---
id: 1861
title: 'P2-04: Agent instruction updates — h-decision-requests skill'
status: archived
priority: medium
created: 2026-05-24T20:59:38.739082+02:00
updated: 2026-05-26T03:43:25.839590+02:00
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
archival_reason: completed
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

[[2026-05-26T02:47:42+02:00]]
## Builder Notes
- Files changed: `share/skills/h-decision-requests/SKILL.md`
- Fix applied: corrected lifecycle wording in the Resolve section to match engine behavior.
  - Replaced claim that pending file "moves atomically" with explicit two-step semantics: engine writes `decisions/resolved/{request_id}.md` and then removes `decisions/pending/{request_id}.md`.
- Why: reviewer finding reported source-of-truth mismatch against engine implementation for AC3 lifecycle transition wording.
- Tests: skipped (`proof_bundle: skip`, docs-only task).
- Coverage: n/a (documentation-only change).
- Lint: n/a (documentation-only change).
- Commit: `13d90f1d` — `docs: fix request lifecycle wording in DR skill (#1861, builder)`.
- Evidence summary:
  - Updated lifecycle text now aligns with engine two-step transition semantics cited in review evidence.
  - No behavioral/tool contract changes; only wording correction in handbook content.

[[2026-05-26T03:12:31+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1861 to docs | AC mapped to code and evidence sufficient.
- Review scope: builder-declared docs-only change in share/skills/h-decision-requests/SKILL.md with proof bundle `skip`; no independent quality-runner rerun required.

| AC Line | Code Evidence | Proof Evidence | Status |
|---|---|---|---|
| AC1 | share/skills/h-decision-requests/SKILL.md:29, 34, 52-55, 84, 89, 100-104, 113, 118, 129-131 document the three MCP tools, required vs optional params, and one usage example per tool; signatures and return-shape notes align with serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459-525 and create_request task-blocking behavior aligns with serve/kanban/src/owlbear_kanban/engine.py:1021. | Direct file review of current handbook against MCP server and engine sources; docs-only `skip` bundle does not require executable proof. | PASS |
| AC2 | share/skills/h-decision-requests/SKILL.md:139-178 documents the named top-level fields, option/resolution subfields, model constraints, and kind-specific validation rules; these align with serve/kanban/src/owlbear_kanban/request_models.py:21-34, 37-44, 52-56, 62-83, 87-105, 95-96. | Direct file review found no remaining source-of-truth drift in the model/validation section after the retry. | PASS |
| AC3 | share/skills/h-decision-requests/SKILL.md:180-208 now describes the resolved-file write then pending-file removal, write-back variants, conditional unblock semantics, and `show_request` consumption; this aligns with serve/kanban/src/owlbear_kanban/engine.py:1105-1113, 1164-1176, 1186, 1269-1275 and serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:514-525. | Current retry closes the prior review finding: the lifecycle wording at share/skills/h-decision-requests/SKILL.md:190 now matches the engine's two-step transition semantics. | PASS |

## Observations
- Builder evidence was sufficient for this docs-only `skip` bundle: file list, no-test rationale, and source mappings were internally consistent with the checked code.
- No blocking findings remain after the lifecycle wording correction in share/skills/h-decision-requests/SKILL.md:190.

[[2026-05-26T03:26:42+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A — no update needed | `share/**` maps to `share/README.md` + `share/WIRING.md`. `share/README.md` does not describe individual skills. `share/WIRING.md` references `h-decision-requests` as `companion` / `body-ref` for pipeline agents and architect (lines 177, 205) — role unchanged by this task; only SKILL.md internals were rewritten. No drift in either file. |
| 2 | External attribution | No | N/A — no external attribution needed | Builder sources were internal: `server.py`, `request_models.py`, `engine.py`. No external sources. |
| 3 | Research doc | No | N/A — no research doc linkage needed | No research artifact exists for this task. |
| 4 | Deletion detection | Yes | N/A — no orphaned references | `create_dr` was demoted to legacy note within SKILL.md (not deleted); WIRING.md describes skill by purpose (`companion` / `body-ref`), not by tool names — no orphaned references. |

### Verification Layers
- Layer 1 — grep structural: "atomic"/"atomically" absent from SKILL.md (reviewer finding resolved). `create_request`, `list_requests`, `show_request` confirmed present (15 occurrences). Required two-step lifecycle language ("writes … then removes") confirmed at line 189.
- Layer 2 — LLM editorial: Full file read (214 lines). MCP tool signatures, parameter tables, usage examples, data model, validation rules, lifecycle, agent usage pattern, and important limits are all coherent and internally consistent. No contradictions with review evidence. No pre-existing unresolved issues requiring TODO markers.

### Scratch Cleanup
No `.owlbear/scratch/1861-*` files found — nothing to delete.

[[2026-05-26T03:43:25+02:00]]
## Audit
### Regression Detection
- Domain mapping: share/ maps to skip (docs/config only)
- Only file changed: share/skills/h-decision-requests/SKILL.md (Markdown documentation)
- No code or test files touched; zero regression risk
- Regression verdict: PASS (domain-exempt)

### Intent Verification
- Scope alignment: PASS (single skill file in share/skills/ domain, exactly matching task scope)
- Purpose match: PASS (SKILL.md documents MCP tools, data model, and lifecycle per AC)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC lines name exact tools (create_request, list_requests, show_request), exact fields, and lifecycle phases. Reviewer confirmed precise alignment against server.py, request_models.py, and engine.py. No improvisation required by builder.

### Commit Integrity
- Upstream commit presence: PASS (834be4ec initial rewrite, 13d90f1d lifecycle fix; both attributed #1861, builder)
- Both commits scoped to single deliverable file
- Kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
