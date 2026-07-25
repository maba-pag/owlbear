---
id: 2064
title: 'P10-05: Prove successful independent whole-change audit'
status: verify
priority: high
created: 2026-07-25T19:53:45.800696+02:00
updated: 2026-07-25T21:23:33.295033+02:00
tags:
  - phase-10
  - scope:test
  - auditor
  - success
  - proof-checkout
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-014
  - packet:DN-014-PK-005
  - interface:IF-014
  - proof:PROOF-008
parent: 1986
depends_on:
  - 2063
ac:
  - 'AC-1: In a real admitted lifecycle whose declared node set has current accept
    receipts, final public `finish_accept` creates one audit job; public `pick_jobs`
    selects `auditor`, and `start_job` returns matching active identity plus an engine
    exact-commit checkout while writer conflict remains enforced.'
  - 'AC-2: Shipped auditor artifacts in the checkout rehydrate Product Promise, accepted
    decisions, migrations and removals, admitted normal workflows, current accept
    receipts, request absence, and PROOF-008; commands and observations exercise maintained
    boundaries with disclosed allowed replacements, and before and after Git state
    shows no tracked edit.'
  - 'AC-3: `AuditorSuccess` through public `finish_audit` persists a broad impact-closure
    audit receipt at the tested SHA, successful terminal event, archived audit job
    as mechanical change closure, reader release, and checkout cleanup; replay returns
    the persisted receipt, event, and job with byte-identical stores and one terminal
    event.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-014-PK-005`. Resolve behavior from REQ-007, WF-005, IF-014, RISK-008, RISK-009, and PROOF-008.

## Outcome
Maintain the successful exact-commit half of PROOF-008 over the shipped auditor and public lifecycle.

## Envelope
In: completed accepted-node set, terminal audit creation, public dispatch/start, engine checkout, whole-change authority evaluation, successful finish, broad receipt closure, replay, and cleanup.

Out: rejection and failure matrix, new semantics, Cockpit, setup, cutover, and complete-system proof.

Proof guidance: extend one maintained public MCP and native assembled scenario; do not create a parallel harness.

[[2026-07-25T21:23:33+02:00]]
## Builder Notes

Added one maintained public MCP/native assembled PROOF-008 success scenario in `serve/mcp-kanban/tests/test_mcp_acceptance_tools.py`; no production code or parallel harness was added.

### AC Evidence
- AC-1: Reused the real final-accept fixture, then public `pick_jobs` selected exactly one auditor and public `start_job` returned the matching exact-Git checkout. A waiting writer was rejected with `WRITER_CONFLICT` held by the active audit reader.
- AC-2: Checkout evidence inspects the shipped auditor hook/tool boundary and workflow, then public change/job/receipt/request queries rehydrate Product Promise intent/design, accepted decisions, migrations, admitted workflows, every current accepted-job receipt, request absence, PROOF-008, allowed replacements, and clean before/after tracked Git state.
- AC-3: Public `finish_audit` persists the tested SHA, complete accepted receipt closure in authoritative job order, full JSON evidence, and canonical whole-change impact closure over `/` and every admitted graph entity. It archives the audit job, records success, releases the reader, cleans the checkout, and replays with byte-identical stores and exactly one terminal success event.

### Proof
- Isolated scenario: 1 passed.
- Changed MCP interaction file: 12 passed.
- Public MCP plus native and dispatch runtime owners: 73 passed.
- Ruff check and format check: clean.
- Editor diagnostics and diff check: clean.
- Builder challenger: pass; independently reran 12 public tests, 26 audit/accept runtime tests, Ruff, formatting, and diff checks.

During review, the delegated draft was tightened to use current archived-job receipt authority, canonical runtime closure, and explicit archive/reader/event assertions.
