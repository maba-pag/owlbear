---
id: 2050
title: 'P7-04: Prove acceptance-triggered planning reconciliation'
status: collect
priority: high
created: 2026-07-25T15:09:49.416616+02:00
updated: 2026-07-25T15:49:32.854825+02:00
tags:
  - phase-7
  - scope:test
  - planner
  - reconciliation
  - invalidation
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-006
  - packet:DN-006-PK-004
  - interface:IF-007
  - proof:PROOF-005
parent: 1983
depends_on:
  - 2049
ac:
  - 'AC-1: Given accepted predecessor implementation evidence, `finish_accept` atomically
    creates or releases the declared dependent reconciliation plan jobs, and previously
    generated dependent builds remain blocked with source-declared stale-authority
    diagnostics until superseding plans publish.'
  - 'AC-2: Given the engine-selected reconciliation job, the shipped planner contract
    folds the current predecessor accept receipt and evidence into a superseding node
    plan, `finish_plan` records predecessor receipt IDs and a new node-plan digest,
    and only new digest-bound builds become startable.'
  - 'AC-3: Given invalidation of that predecessor accept receipt through the existing
    corrective and invalidation runtime, the dependent reconciled plan receipt and
    build closure become stale while a disjoint node plan remains byte-identical.'
  - 'AC-4: The maintained `PROOF-005` suite covers initial topology, per-node atomic
    failure, accepted-evidence fold-in, blocked dependent builds, and predecessor-accept
    invalidation through real planner and runtime boundaries; only repository-search
    results are replaced.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-006-PK-004`. Resolve normative behavior from `DN-006`, `IF-007`, `REQ-025`, `WF-002`, and `PROOF-005`; this record is not specification authority.

## Outcome
Complete `PROOF-005` with acceptance-triggered reconciliation, accepted-evidence fold-in, stale dependent-build blocking, superseding plan publication, and predecessor-accept invalidation.

## Envelope
In: shipped planner contract over real native runtime transactions and public tools where exposed; repository search results may be replaced below the planner.

Out: new runtime semantics, acceptance implementation, planner workflow changes, setup/seed work, and unrelated invalidation classes.

Proof guidance: exercise the current `finish_accept`, reconciliation plan, `finish_plan`, readiness, and invalidation owners; direct store mutation cannot replace the claimed lifecycle boundary.

[[2026-07-25T15:47:27+02:00]]
## Builder Notes

DONE. Adopted and completed the interrupted #2050 diff within the shaped envelope.

### Changed Files
- `serve/mcp-kanban/tests/test_planner_interaction.py`: added the maintained acceptance-triggered reconciliation and invalidation scenario through shipped planner artifacts, public MCP lifecycle tools, real native runtime transactions, and the existing corrective invalidation owner.
- `serve/kanban/src/owlbear_kanban/native_runtime.py`: supplied the current node-plan token to the existing OCC replacement path so reconciliation can atomically publish superseding plans.
- `serve/kanban/src/owlbear_kanban/receipt.py`: canonicalized immutable receipt evidence before node-plan digest hashing.

### AC Evidence
- AC-1: the assembled scenario proves `finish_accept` creates the completed DN-002 dependent reconciliation job and releases the still-active DN-003 plan identity; old DN-002 build 17 is blocked by reconciliation job 19.
- AC-2: engine-picked job 19 is dispatched through the shipped planner contract with the predecessor accept receipt/evidence, publishes a distinct digest and predecessor receipt ID, diagnoses old build 17 with `ERR_RECEIPT_NODE_PLAN_DIGEST_STALE`, and starts new build 20.
- AC-3: corrective invalidation of the predecessor accept stales the reconciled receipt and jobs 19/20/21 while DN-009 plan and receipt bytes remain identical.
- AC-4: the two maintained PROOF-005 scenarios jointly cover initial topology, atomic publication/replay and invalid-next-node isolation, accepted-evidence fold-in, build blocking, superseding publication, and predecessor-accept invalidation through real boundaries.

### Validation
- Exact reconciliation scenario: 1 passed.
- Complete planner interaction module: 2 passed.
- Complete `serve/mcp-kanban/tests`: 69 passed.
- Native runtime, dispatch, invalidation, receipt, and node-plan storage suites: 161 passed.
- Ruff check and format: clean for all three changed Python files.
- VS Code diagnostics: no errors in changed files.
- Path-scoped pre-commit: all applicable hooks passed.
- Live modular-delivery digest remains `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.
- Builder challenger: `pass`; independently reran the assembled scenarios, MCP suite, and static checks and found the runtime repairs narrow and required.

[[2026-07-25T15:49:32+02:00]]
## Verify Notes

PASS at builder commit `75db1c280e4ac7a848c3fef56f98df46ac82a6bf`.

### Independent AC Verification
- AC-1: the public assembled scenario verifies all direct-dependent create-or-release identities, reconciliation predecessor linkage, and old-build blocking before superseding publication.
- AC-2: the engine-picked reconciliation job runs through shipped planner artifacts, embeds the predecessor accept receipt/evidence, records predecessor receipt linkage and a changed digest, rejects the old build as digest-stale, and starts the replacement build.
- AC-3: existing corrective/invalidation owners stale the reconciled receipt and jobs 19/20/21 while disjoint DN-009 plan and receipt bytes remain unchanged.
- AC-4: the maintained two-scenario module exercises initial topology, atomic success/replay, invalid next-node isolation, reconciliation, evidence fold-in, blocking, supersession, and invalidation through real planner and runtime boundaries.

### Verification Evidence
- Exact committed code paths had no drift from HEAD.
- `git show` confirmed commit `75db1c280e4ac7a848c3fef56f98df46ac82a6bf` contains only the #2050 task record and three owned code paths.
- Planner interaction plus native runtime, invalidation, receipt, and node-plan storage suites: 154 passed.
- Complete `serve/mcp-kanban/tests`: 69 passed.
- Ruff check and format: clean for all changed Python files.
- Verifier challenger: `pass`; no implementation defect or missing proof blocks collection.
