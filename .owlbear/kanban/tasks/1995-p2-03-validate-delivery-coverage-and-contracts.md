---
id: 1995
title: 'P2-03: Validate delivery coverage and contracts'
status: build
priority: medium
created: 2026-07-22T13:45:55.105472+02:00
updated: 2026-07-22T13:45:55.105472+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - validation
  - contracts
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-003
parent: 1978
depends_on:
  - 1993
ac:
  - 'AC-1: Missing or multiply assigned ownership or proof for a requirement, negative
    requirement, or preserved behavior returns `DV-003` for that target; one accountable
    owner or support path produces no `DV-003`.'
  - 'AC-2: Incomplete or contradictory interface producer/consumer inventories, authority,
    failure semantics, migration, or proof return `DV-004`; matching node `produces`
    and `consumes` references plus populated contract fields produce no `DV-004`.'
  - 'AC-3: A migration missing ordered steps, consumer inventory, compatibility, deletion
    owner, or absence proof returns `DV-005`; a risk missing scenarios, disposition,
    owner, or proof returns `DV-006`; completing the named fields clears that category
    finding.'
  - 'AC-4: A proof missing boundary, build-capable owner, method, allowed replacements,
    durable outputs, or an owning predecessor returns `DV-007`; a populated proof
    owned by a delivery predecessor before acceptance or audit produces no `DV-007`.'
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
- `packet_id`: `DN-002-PK-003`

## Outcome
The public admission evaluator rejects incomplete obligation ownership and delivery contracts with the authority-aligned `DV-003` through `DV-007` categories.

## Scope
In scope: accountable requirement, negative-requirement, and preserved-behavior ownership/proof; interface producer/consumer agreement; migration/removal completeness; risk disposition completeness; proof ownership and build-capable predecessor checks; deterministic findings and focused table proof.

Out of scope: evidence gates; topology, reachability, decision coherence, and node-category bounds; historical incident fixtures; receipts, jobs, or persistence.

## Authority
Resolve normative behavior from admission sections 5 and 9 of `design.md`, A1 through A7 in `.owlbear/research/planning-workflow-root-cause-and-redesign.md`, and the `DV-003` through `DV-007` meanings in the admitted receipt. `DV-001` and `DV-002` remain DN-001 loader concerns.

Complexity waiver: four AC share one deterministic contract-completeness algorithm and one public-evaluator table-test mode; splitting by entity type would duplicate traversal and finding semantics.

Proof guidance: exercise the public evaluator over real `ChangeRevision`-derived cases. Run the focused admission suite and Ruff on touched files; no persistence proof belongs here.