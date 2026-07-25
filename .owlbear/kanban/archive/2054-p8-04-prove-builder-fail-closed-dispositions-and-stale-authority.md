---
id: 2054
title: 'P8-04: Prove builder fail-closed dispositions and stale authority'
status: archived
priority: high
created: 2026-07-25T16:14:38.333700+02:00
updated: 2026-07-25T17:03:39.982540+02:00
tags:
  - phase-8
  - scope:test
  - builder
  - findings
  - stale-authority
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-007
  - packet:DN-007-PK-004
  - interface:IF-008
  - proof:PROOF-006
parent: 1984
depends_on:
  - 2053
ac:
  - "AC-1: Given `unforeseeable-discovery`, `planning-omission`, or `scope-change`,
    the shipped builder returns `SpecificationReentry` with the typed class, target,
    finding, and evidence; the orchestrator releases the claim, halts native mode,
    and publishes no build receipt. The scenario enumerates the three literals and
    preserves prior receipt bytes; `implementation-defect` remains P8-03's repair
    case."
  - 'AC-2: Given scoped commit failure, the shipped builder returns `CommitFailed`
    with command, error, and bounded changed-path evidence; the orchestrator releases
    the matching claim and halts before fresh dispatch, and no build receipt is published.
    A deterministic runner scenario verifies the failed commit cannot become success.'
  - 'AC-3: Given reviewer context missing authority, diff or changed paths, proof,
    or commit identity, the reviewer output is malformed and the builder returns `BuildBlocked`;
    declaration checks and the assembled scenario verify reviewer write denial, identity-preserving
    release, and no receipt.'
  - 'AC-4: Given a build job whose node-plan digest differs from current authority,
    public `start_job` returns `ERR_START_AUTHORITY_STALE` with `ERR_RECEIPT_NODE_PLAN_DIGEST_STALE`
    before builder dispatch; the scenario verifies no claim, commit, reviewer call,
    or receipt mutation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-007-PK-004`. Resolve normative behavior from `IF-008`, `NEG-009`, `RISK-003`, `RISK-008`, and `PROOF-006`; this record is not specification authority.

## Outcome
Complete PROOF-006's material contradiction, commit failure, malformed review, and stale digest matrix, covering the four canonical finding classes across warm repair and specification re-entry.

## Envelope
In: assembled shipped builder dispositions, identity-preserving public release, no-receipt assertions, stale start diagnostics, and preservation of prior receipts. A sample module and deterministic runner may replace lower layers.

Out: new finding persistence or corrective-job operations, runtime semantics, acceptor or auditor work, and setup or seed propagation.

Proof guidance: exercise shipped builder and orchestrator contracts plus public start, release, receipt, and diagnostic boundaries.

[[2026-07-25T16:59:17+02:00]]
## Builder Notes

Completed the fail-closed half of PROOF-006 in `serve/mcp-kanban/tests/test_builder_interaction.py` without changing runtime semantics or shipped declarations.

- AC-1: three parameterized material-finding cases preserve exact `SpecificationReentry` fields, use the live shipped workflow/orchestrator routing contracts, release unchanged public claim identity, preserve prior receipt bytes, and issue no build receipt.
- AC-2: a deterministic rejecting Git hook makes scoped `commit_owned_paths` fail; HEAD remains unchanged, the packet path remains visible and uncommitted, exact `CommitFailed` evidence is preserved, public release occurs, and no receipt is issued.
- AC-3: five cases remove authority, diff, changed paths, proof, or commit identity from generated valid review context; the live malformed-review and `BuildBlocked` declarations are checked, reviewer write denial executes, unchanged identity releases, and no receipt appears.
- AC-4: an isolated node-plan revision makes the generated build stale; public `start_job` returns `ERR_START_AUTHORITY_STALE` with `ERR_RECEIPT_NODE_PLAN_DIGEST_STALE` before claim. Attempt history, product commit, job claim identity, and receipt bytes remain unchanged.

Evidence: assembled builder module 11 passed; complete MCP-Kanban package 80 passed; focused repository lint passed; VS Code diagnostics reported no errors. Builder challenger decision: pass.

[[2026-07-25T17:03:11+02:00]]
## Verifier Notes

PASS after one local verifier repair at builder commit `8bc8e044545ffbcae9cbff6e05e49c1f01a76218`.

Exact committed delta review confirmed the three specification re-entry classes, deterministic actual commit failure, public unchanged-identity releases, byte-preserved prior receipts, absent build receipts, and stale-authority pre-claim diagnostic all remain within DN-007-PK-004.

Initial verifier challenge found failure key `malformed-context-causality`: tests removed required reviewer fields but manually constructed `BuildBlocked`. Repaired the same test slice by adding a declaration-backed assembled context classifier. It validates the live shipped reviewer malformed-input contract, traverses authority, diff, changed paths, proof, and scoped commit requirements, returns exact `BuildBlocked` only from the actually malformed context, and returns no block for valid context. Each case now asserts that derived disposition before public release and write-denial observations.

Post-repair evidence: complete builder module 11 passed; complete MCP-Kanban package 80 passed; focused lint passed; editor diagnostics reported no errors. Verifier rechallenge decision: pass and explicitly closed `malformed-context-causality`. All recalled memories were assessed.

[[2026-07-25T17:03:39+02:00]]
## Collector Notes

Leaf packet closure is complete with no descendants or unresolved follow-up keys. All four ACs are covered by current committed evidence: builder commit `8bc8e044545ffbcae9cbff6e05e49c1f01a76218` and verifier repair commit `e5005471a67d05c3de57faf77103c15edd7bd76d`. The initial verifier challenge's sole failure key, `malformed-context-causality`, was repaired and explicitly passed on rechallenge. The complete assembled PROOF-006 module has 11 passing cases and the owning package has 80 passing tests; lint and diagnostics are clean. Archive reason: completed.
