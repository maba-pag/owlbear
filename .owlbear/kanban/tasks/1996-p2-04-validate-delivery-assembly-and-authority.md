---
id: 1996
title: 'P2-04: Validate delivery assembly and authority'
status: build
priority: medium
created: 2026-07-22T13:46:10.586702+02:00
updated: 2026-07-22T13:46:10.586702+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - validation
  - graph
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-004
parent: 1978
depends_on:
  - 1995
ac:
  - "AC-1: A dependency cycle, disconnected node, unreachable workflow, or interface
    producer outside a consuming node's dependency ancestry returns `DV-008`; a connected
    acyclic producer-before-consumer graph produces no `DV-008`."
  - 'AC-2: A pending material decision, accepted decision without a selected option,
    or graph admission metadata bound to a different revision digest returns `DV-010`;
    accepted decisions and matching admission metadata produce no `DV-010`.'
  - 'AC-3: A node list containing an entity from the wrong authority category, or
    a node proof outside its declared proof reference, returns `DV-011`; node references
    confined to their declared owns, supports, modules, produces, consumes, risks,
    and proof categories produce no `DV-011`.'
  - 'AC-4: Table/property mutations adding one cycle, disconnected node, backward
    interface edge, wrong-category node reference, pending decision, or stale admission
    digest produce deterministically sorted `DV-008`, `DV-010`, or `DV-011`; random
    connected acyclic DAGs with producer-before-consumer edges produce none of those
    codes.'
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
- `packet_id`: `DN-002-PK-004`

## Outcome
The public admission evaluator rejects invalid delivery topology, dependency ordering, accepted-decision coherence, and node reference bounds with `DV-008`, `DV-010`, and `DV-011`.

## Scope
In scope: graph connectivity and cycles; workflow reachability; producer-before-consumer ancestry; accepted-decision coherence; graph admission digest coherence; node reference category bounds; deterministic table/property proof.

Out of scope: raw package identity/reference parsing owned by DN-001; contract completeness owned by #1995; proof-boundary substitution, which remains a repository-grounded per-proof challenger disposition; historical fixtures; persistence.

## Authority
Resolve normative behavior from admission sections 5, 9.1, and 9.2 of `design.md`, A7 through A10 in the planning research, and the admitted receipt's meanings for `DV-008`, `DV-010`, and `DV-011`. `DV-009` remains semantic challenge evidence; native dependency readiness does not reuse bootstrap-only `DV-012`.

Complexity waiver: four AC share one graph-assembly algorithm and one public-evaluator property/table proof mode; splitting topology from node bounds would duplicate graph indexing and deterministic ordering.

Proof guidance: start from a loaded `ChangeRevision`, mutate only semantic graph relationships below the public evaluator, and run focused admission tests plus Ruff. Do not duplicate DN-001 loader cases.