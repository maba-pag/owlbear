---
id: 2072
title: 'P15-02: Re-accept orchestration and exact-commit proof at the candidate digest'
status: archived
priority: high
created: 2026-07-26T01:58:44.920258+02:00
updated: 2026-07-26T02:52:56.318498+02:00
tags:
  - phase-15
  - candidate-reacceptance
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-004
  - scope:core
  - type:test
  - rigor:thorough
  - proof:PROOF-014
parent: 1968
depends_on:
  - 1980
  - 2071
ac:
  - 'AC-1: Given candidate DN-003 outputs, the public orchestrator dispatches graph-selected
    `plan | build | accept | audit` jobs with writer/read-only compatibility and records
    the tested code revision in re-acceptance evidence.'
  - 'AC-2: Given expired claims, competing writers, and disposable proof checkouts,
    PROOF-014 demonstrates recovery, serialization, exact-commit materialization,
    and cleanup without relying on an old delivery digest.'
  - 'AC-3: The task records candidate digest, tested SHA, commands, and results for
    DN-004; a failing invariant produces a scoped corrective implementation before
    re-acceptance rather than a passing evidence note.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; candidate re-acceptance of unchanged `DN-004` under `PROOF-014`.

## Outcome
The existing dispatch, writer serialization, recovery, and proof-checkout implementation is re-proven against the candidate authority after DN-003 administrative controls land.

## Envelope
In: DN-004 contract, IF-004/IF-005/IF-015, PROOF-014, candidate digest, current implementation and durable proof.

Out: new orchestration behavior unless proof exposes a local defect; MCP, Cockpit, frontend, cutover.

Proof guidance: run the existing public orchestration/writer/proof-checkout boundary at a recorded code SHA and inspect authority references; repair only a concrete DN-004 defect.

[[2026-07-26T02:49:02+02:00]]
## Builder Notes
DONE: Re-accepted unchanged DN-004 against candidate digest `bf5edd...` at tested SHA `86322a6ec48a1e690f2f003f08bd2e4550cd9fd3`.

Evidence:
- `uv run pytest -q` over dispatch runtime, proof checkout, MCP surface/acceptance, planner interaction, and builder interaction: 69 passed.
- Builder challenger independently reran the six files unsharded: 69 passed.
- Exact PROOF-014 mapping covers the eight IF-015 tools, real DispatchRuntime waves for plan/build/accept/audit, writer/read-only compatibility, claim/finalize/recovery, checkout setup/rejection/finish/release/recovery cleanup, containment, exact commit, orphan health, and structured planner/builder interactions.
- Product/proof paths remained clean; focused product lint passed.

No product edit was required. Builder memories assessed.

[[2026-07-26T02:52:03+02:00]]
## Verify Notes
PASS: Candidate-bound DN-004 re-acceptance is complete.

Independent evidence at verifier HEAD `7e8762006d6d80602378cfe94f4cf00a8ebdc38d`:
- Tested product SHA `86322a6ec48a1e690f2f003f08bd2e4550cd9fd3` and builder evidence are ancestors.
- High-risk IF-015/DispatchRuntime/proof-checkout subset: 19 passed.
- Full PROOF-014 and independent builder challenge: 69 + 69 passed.
- Focused product lint passed and product/proof paths remained clean.
- Verifier challenger: pass; no missing evidence or scope drift.

AC-1 through AC-3 are tied to candidate digest, exact SHA, commands, and direct public-boundary results. Verifier memories assessed.

[[2026-07-26T02:52:56+02:00]]
## Collect Notes
ARCHIVED: DN-004 candidate re-acceptance is complete. Tested product SHA `86322a6ec48a1e690f2f003f08bd2e4550cd9fd3`, builder evidence `7e8762006d6d80602378cfe94f4cf00a8ebdc38d`, and verifier evidence `50ba1a8287d7eda097f9d8f434df453a4bb21ad7` are ancestors. Full 69-test PROOF-014, independent 69-test challenge, and verifier 19-test high-risk proof passed; no product delta or unresolved finding. Collector memories assessed.
