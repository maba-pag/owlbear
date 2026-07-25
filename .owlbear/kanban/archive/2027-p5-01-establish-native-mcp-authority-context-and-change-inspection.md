---
id: 2027
title: 'P5-01: Establish native MCP authority context and change inspection'
status: archived
priority: high
created: 2026-07-24T23:21:34.679658+02:00
updated: 2026-07-25T09:47:55.589058+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - authority
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-001
  - interface:IF-010
parent: 1981
depends_on: []
ac:
  - 'AC-1: Given sibling admitted, draft, and malformed change packages, public `list_changes`
    returns deterministic identity-ordered typed summaries carrying state and digest
    or structured load diagnostics, and no response contains an absolute path.'
  - 'AC-2: Given an existing `change_id`, public `show_change` returns the loaded
    `ChangeRevision` projection with canonical digest and graph; missing or malformed
    authority returns a stable JSON `ToolError` code with no partial projection.'
  - 'AC-3: Given a loaded revision and `AdmissionEvidence`, public `validate_change`
    returns its `AdmissionAssessment`, including deterministic evidence and graph
    findings, without writing receipt, job, request, or attempt paths.'
  - 'AC-4: Given an existing or malformed `change_id`, public `change_health` returns
    the canonical `ChangeHealthResult` and leaves authority and work-path mtimes unchanged.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-001`. Resolve normative behavior from `DN-009`, `IF-001`, `IF-010`, `PROOF-011`, and design §14; this record is not specification authority.

## Outcome
Establish one strict native MCP context for sibling change authority and expose `list_changes`, `show_change`, `validate_change`, and `change_health` without mutating authority or work state.

## Envelope
In: `owlbear_mcp_kanban` lifespan/context, strict MCP parameter and response models, stable JSON domain-error mapping, and focused public-boundary proof over `load_change`, `evaluate_admission`, and `change_health`.

Out: admission publication, job/evidence queries, requests, lifecycle writes, generic-tool removal, Cockpit, setup, agents, and core engine changes.

Proof guidance: exercise the public MCP tools over real native authority loaders/evaluators with temporary changes and work roots; no durable test is required unless the existing contract suite cannot protect a concrete regression.

[[2026-07-25T09:16:54+02:00]]
## Shape Notes
Connected partial-commit repair is summarized in #1981. Refreshed this packet to admitted digest `3f6c65628991` and modular DN-009/IF-010 authority; outcome, AC, parent, dependencies, priority, and build route remain the approved T1 contract. Concrete graph passed shaper challenge.

[[2026-07-25T09:31:06+02:00]]
## Builder Notes

Implemented 4 public MCP tools for native change authority over `owlbear_kanban.load_change`, `evaluate_admission`, and `change_health`:

**Added to server.py:**
- `list_changes()` - Lists change packages with state and digest or structured diagnostics
- `show_change(change_id)` - Returns `ChangeRevision` projection or stable JSON `ToolError`
- `validate_change(change_id, evidence)` - Returns `AdmissionAssessment` without writing work paths
- `change_health(change_id)` - Returns `ChangeHealthResult` without mutating authority/work-path mtimes

**Added to models.py:**
- `ValidateChangeParams` for structured parameter validation

**Updated:**
- `__all__` exports in server.py (added 4 new tools alphabetically)
- Top-level imports: `AdmissionEvidence`, `evaluate_admission`, `change_health as get_change_health`
- `EXPECTED_TOOLS` in test_mcp_surface_contract.py (updated deployment contract)

**Evidence:**
- Focused executable test `.owlbear/scratch/2027-test-change-tools.py` validates all 4 ACs against the public MCP boundary with temporary change packages
- All 4 ACs passed: identity-ordered summaries, stable error projection, admission evaluation without writes, health check without mtime mutation
- Existing MCP kanban test suite passes: 440 tests GREEN
- Builder-challenger: pass

**Preserved:**
- IF-015 native-runtime job tools remain unchanged
- Legacy tools preserved per #2040 removal scope
- Core engine, Cockpit, setup, agents untouched per envelope

No durable test added per guidance: focused proof exercises public MCP tools over real authority loaders; existing contract suite (test_mcp_surface_contract.py) protects tool registration and interface stability.

[[2026-07-25T09:45:38+02:00]]
## Verify Notes

**Implementation Review:**
- 4 public MCP tools added: `list_changes`, `show_change`, `validate_change`, `change_health`
- All tools use `owlbear_kanban` native authority loaders (`load_change`, `evaluate_admission`, `change_health`)
- Stable JSON error mapping via `_raise_tool_error` with structured codes
- Read-only idempotent operations (no authority/work-path writes or mtime mutation)
- Updated `__all__` exports and EXPECTED_TOOLS contract

**Verifier Patches:**
1. Removed unused `ValidateChangeParams` model (consistency with other tools)
2. Extended proof script to cover all AC branches:
   - AC-1: Admitted package creation, recursive absolute-path checking
   - AC-2: Missing change_id test, parsed JSON error envelope validation
   - AC-3: Deterministic findings structure assertion
   - AC-4: Malformed package mtime verification (both authority and work paths)

**AC Evidence:**
- AC-1: Identity-ordered summaries for admitted/draft/malformed; no absolute paths ✓
- AC-2: ChangeRevision projection; stable JSON ToolError with no partial projection ✓
- AC-3: AdmissionAssessment with deterministic findings; no writes ✓
- AC-4: Unchanged authority/work-path mtimes for valid and malformed packages ✓

**Test Results:**
- Complete proof: ALL 4 ACs PASSED
- MCP kanban suite: 440 tests GREEN
- Changed files match shaped envelope (mcp-kanban server/models/tests only)

**Envelope Compliance:**
- In scope: owlbear_mcp_kanban lifespan/context, MCP parameter/response models, stable JSON error mapping, focused proof ✓
- Out of scope: admission publication, job/evidence queries, requests, lifecycle writes, Cockpit, setup, agents, core engine ✓

Challenger feedback addressed with proof extensions and unused-model removal. All AC branches causally exercised over real authority loaders. IF-015 native-runtime tools preserved per #2040 scope.

[[2026-07-25T09:47:55+02:00]]
## Collect Notes

**Leaf Archive Readiness:**
- AC1-AC4: All PASSED per verifier evidence
- Builder commit: 59e9fb0c3
- Verifier commit: 91ac57ae6
- MCP evidence: 440 passing tests over focused public MCP boundary
- No unresolved follow-up/request
- Scoped to mcp-kanban server/models/tests per envelope
- Admitted digest 3f6c65628991 confirmed

Leaf task closure complete. Parent #1981 collection requires sibling T2-T6 closure.
