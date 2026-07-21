---
id: 1977
title: 'Bootstrap DN-001: Establish native change authority and semantic identity'
status: collect
priority: medium
created: 2026-07-22T01:05:17.126803+02:00
updated: 2026-07-22T01:59:42.890914+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-001
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1991
  - 1992
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-001` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-001` modules, interfaces, risks, and
    `PROOF-001`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-001` and `PROOF-001`, verified
    through Kanban queries and artifact inspection.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-001`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-001|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-001` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Strict four-file ChangeRevision loading, stable IDs/digests, immutable receipt storage, path safety, and health diagnostics replace OpenSpec artifact resolution.
- Modules: `MOD-001`
- Produces: `IF-001`
- Consumes: none
- Risks: `RISK-004`
- Proof: `PROOF-001`
- Delivery dependencies: none

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: shape from the admitted node and run the cheapest public ChangeRevision loader/receipt-store checks plus downstream path-safety impact; packet proof may replace only the temporary workspace filesystem below `PROOF-001`.

[[2026-07-22T01:59:42+02:00]]
## Shape Notes

### Authority And Approval
- Shaped `DN-001` from `.owlbear/changes/replace-delivery-pipeline/graph.yaml` at delivery digest `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; no change-authority file was edited.
- The live `owlbear_kanban` source confirmed reusable containment, YAML, atomic-write, strict-model, exclusive-create, and non-mutating-health patterns. No existing `serve/kanban` edit overlaps this graph.
- `shaper-challenger` returned `decision: pass` with no blocking finding and confirmed the draft could be presented without board mutation.
- User approved the exact two-packet graph and immediate implementation of packet 1.
- MCP runs from the admitted stable sibling carrier; that checkout reports baseline Dev-Ref `e27786f3`, while authority, board, and product work remain in `owlbear-dev` at admission commit `040d6ae5`.

### Brief Readiness
- Product outcome and invocation: public four-file `ChangeRevision` loader and receipt store defined by `IF-001` and `PROOF-001`.
- Existing-system fit and authority: `serve/kanban/src/owlbear_kanban/` with `_naming.py`, `yaml_rt.py`, `storage_io.py`, `models.py`, `engine.py`, and package exports read directly.
- Normal-path proof: public loader, digest, receipt-store, and change-health boundaries over a temporary workspace; no injected completed workflow.
- Completion contract: strict authority identity, immutable receipt persistence, path safety, and read-only health; admission semantics, receipt-chain validity, jobs, MCP, HTTP, and UI remain excluded.

### Contract Authorities
| Claim | Authority | Evidence State | Confidence |
|---|---|---|---|
| Four-file envelope and `delivery-v1` | `design.md` sections 3 and 4 | documented and source-grounded | 0.98 |
| Node scope and proof boundary | `graph.yaml` `DN-001`, `IF-001`, `RISK-004`, `PROOF-001` | admitted | 1.0 |
| Containment and atomic-write reuse | `_naming.py`, `storage_io.py` | observed | 0.98 |
| Health and exclusive-create precedent | `models.py`, `engine.py` | observed | 0.96 |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owner |
|---|---|---|---|---|
| Native change authority modules in `owlbear_kanban` | new | add strict revision models, loader, identity index, and digest | new `IF-001` | #1991 |
| Receipt and change-health modules in `owlbear_kanban` | new | add immutable receipt I/O and read-only diagnostics | new public store and health boundaries | #1992 |
| `_naming.py`, `yaml_rt.py`, `storage_io.py` | shared safety and persistence primitives | reuse; modify only for a required shared guard | none expected | #1991 or #1992 by behavior |
| `__init__.py` | package exports | expose packet-owned public boundaries | additive | #1991 and #1992 |
| `serve/kanban/tests/` | package behavioral proof | add public-boundary loader, digest, receipt, health, and path cases | none | matching packet |

### Product Invariant Map
| Product Invariant | Owner | Normal Boundary | Proof / Allowed Replacement |
|---|---|---|---|
| Four files produce one semantic revision and digest | #1991 | public loader and digest | package pytest; temporary filesystem only |
| Unsafe or partial packages return no authority | #1991 | public loader diagnostics | table-driven path/parse cases |
| Receipt IDs are immutable and contained | #1992 | public receipt store | exclusive-create and path cases |
| Authority and receipt corruption is observable without mutation | #1992 | public change health | byte and mtime comparison |

### Decomposition And Audit
- #1991 `DN-001-PK-001`: load canonical native change revisions; `build`, ready, no dependency.
- #1992 `DN-001-PK-002`: persist immutable change receipts and diagnose authority health; `build`, depends on #1991.
- Both tasks are parented to #1977, reference the admitted change, digest, node, and packet identity, and use `existing+challenge` proof.
- #1977 depends on #1991 and #1992 and is routed to dependency-gated `collect`.
- Existing primitive proof: 17 focused tests passed for atomic-write and task-health behavior.
