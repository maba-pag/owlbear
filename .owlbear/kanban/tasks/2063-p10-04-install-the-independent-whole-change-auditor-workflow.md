---
id: 2063
title: 'P10-04: Install the independent whole-change auditor workflow'
status: build
priority: high
created: 2026-07-25T19:53:37.879721+02:00
updated: 2026-07-25T19:53:37.879721+02:00
tags:
  - phase-10
  - scope:agent-config
  - auditor
  - orchestrator
  - read-only
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-014
  - packet:DN-014-PK-004
  - interface:IF-014
parent: 1986
depends_on:
  - 2062
ac:
  - 'AC-1: The shipped auditor role accepts only an orchestrator-started audit result
    with engine checkout, has read, query, and proof capabilities but no lifecycle
    or tracked-write capability, uses the terminal read-only hook, and loads the whole-change
    audit workflow; validators and wiring inspection show declaration and derived
    map agreement.'
  - 'AC-2: The workflow rehydrates matching change, job, checkout, accepted-node receipt
    set, Product Promise, accepted decisions, migrations and removals, admitted workflows,
    request state, IF-014, PROOF-008, allowed lower replacements, and before and after
    Git state; stale, incomplete, contradictory, unsafe, or unavailable authority
    returns `AuditBlocked` without mutation.'
  - 'AC-3: The workflow defines `AuditorSuccess` fields mapped unchanged to `finish_audit`
    and `AuditRejected` fields mapped unchanged to `reject_audit`; cross-node integration
    and implemented migration absence use `implementation-defect` with `whole-change-integration`,
    admitted authority or proof omission uses `planning-omission` with `admitted-design-authority`,
    and a tracked edit cannot pass.'
  - 'AC-4: `w-orchestration` dispatches only the engine-selected auditor with the
    complete start and checkout result and maps `AuditorSuccess` to `finish_audit`,
    `AuditRejected` to `reject_audit`, and `AuditBlocked` to unchanged-identity `release_job`
    and halt; malformed output uses crash recovery, and the orchestrator performs
    no proof, classification, evidence assembly, or correction.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-014-PK-004`. Resolve behavior from REQ-007, WF-005, IF-014, NEG-003, NEG-009, RISK-008, RISK-009, PROOF-008, and the shipped acceptor precedent.

## Outcome
Install the hard-read-only auditor role, whole-change audit workflow, and exact orchestrator disposition routing.

## Envelope
In: engine-started audit identity and checkout, native read queries, admitted whole-change authority, success/rejection/blocked dispositions, orchestration mapping, write guard, and derived wiring.

Out: runtime semantics, Cockpit, setup, cutover, and complete-system proof.

Proof guidance: run agent and skill validators plus ecosystem and write-guard regressions; inspect exact orchestration mappings.