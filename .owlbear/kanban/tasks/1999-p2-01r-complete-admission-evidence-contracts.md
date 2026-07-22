---
id: 1999
title: 'P2-01R: Complete admission evidence contracts'
status: build
priority: medium
created: 2026-07-22T14:10:10.625865+02:00
updated: 2026-07-22T14:10:10.625865+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - evidence
  - diagnostics
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-001R
parent: 1978
depends_on: []
ac:
  - 'AC-1: Given a loaded revision plus challenge dispositions, baseline command results,
    approval, and limits bound to its digest, public `evaluate_admission` returns
    an immutable schema-version-1 assessment containing revision digest, explicit
    limits, and findings sorted by code, target, and detail; repeated JSON serialization
    is byte-identical.'
  - 'AC-2: Challenge input requires one typed disposition with nonblank evidence for
    each requirement, workflow, interface, migration, risk, proof, and node. Missing
    or extra targets, blank evidence, or an error disposition return error `EV-002`;
    a warning disposition returns warning `EV-002`, remains in findings, stays outside
    `errors`, and does not alone make `admitted` false.'
  - 'AC-3: Evidence/revision digest mismatch returns `EV-001`; a baseline command
    with nonzero exit or baseline digest mismatch returns `EV-003`; false or digest-mismatched
    approval returns `EV-004`; empty limits return `EV-005`; complete passing inputs
    produce none of `EV-001` through `EV-005`.'
proof_bundle: behavioral+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-002`
- `packet_id`: `DN-002-PK-001R`

## Outcome
Public `evaluate_admission` validates and projects typed, digest-bound challenge, baseline, approval, and known-limit evidence into one immutable schema-version-1 assessment for later composition by the assembled validate/admit transaction.

## Scope
In scope: typed challenge dispositions for requirements, workflows, interfaces, migrations, risks, proofs, and nodes; typed baseline command results; typed approval; explicit limits; a stable evidence-finding enum; warning/error severity; deterministic ordering and JSON serialization; package exports and focused public-boundary tests.

Out of scope: deterministic graph completeness owned by #1995 and #1996; historical incident fixtures owned by #1997; receipt/job writes and aggregate public validate/admit owned by #1998; subprocess or agent execution; MCP, HTTP, UI, and DN-003 runtime.

## Diagnostic Contract
`DV-001` through `DV-012` remain reserved for deterministic graph categories in the admitted receipt. Evidence gates use `EV-001` revision/evidence digest, `EV-002` challenge, `EV-003` baseline, `EV-004` approval, and `EV-005` limits. Migrate the current conflicting evidence emissions from `DV-010` through `DV-013`; this packet does not change graph-diagnostic meanings.

## Current Baseline
Commits recorded under deprecated task #1993 introduced the public evaluator and partial evidence handling. Retain that source as the implementation baseline. Existing partial graph checks remain for #1995 and #1996; do not broaden, remove, or claim their completion in this packet.

## Boundary Ownership
This packet proves the public side-effect-free evaluator only. It is a prerequisite to #1998 and does not independently satisfy `PROOF-002`; #1998 owns zero mutation on rejection and atomic receipt-plus-job publication.

Proof guidance: exercise public `evaluate_admission` over a real loaded `ChangeRevision` with typed table cases and deterministic serialization checks. Run focused admission and ChangeRevision tests plus Ruff on touched files; no filesystem mutation or aggregate validate/admit proof belongs here.