---
id: 1990
title: 'Bootstrap DN-013: Prove the complete native delivery system and cutover'
status: collect
priority: high
created: 2026-07-22T01:09:02.449610+02:00
updated: 2026-07-27T19:46:10.914156+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-013
  - scope:core
  - type:shape
  - rigor:thorough
  - corrective-projection
  - digest:6c95c70c81a1
parent: 1968
depends_on:
  - 1978
  - 1988
  - 1989
  - 2071
  - 2073
  - 2077
  - 2078
  - 2079
  - 2094
  - 2095
  - 2096
  - 2097
  - 2098
ac:
  - 'AC-1: Shaper reads DN-013 from the modular authority trio at digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`
    and creates one outcome-cohesive proof DAG whose leaves reference the same change/digest/node;
    Kanban queries verify task fields and dependencies.'
  - 'AC-2: Shaper keeps leaves within DN-013 consumed interfaces, risks, and PROOF-013;
    product defects route to their owning nodes and task/artifact diff inspection
    verifies no final-auditor implementation scope is introduced.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` only after build-ready
    proof leaves and corrected-authority predecessor evidence exist; Collector archives
    only after descendant Verify Notes and SHA-bound PROOF-013 satisfy DN-013. Real
    bootstrap-board retirement remains exclusively DN-015/PROOF-016.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`
- `delivery_node_id`: `DN-013`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9|DN-013|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-6c95c70c81a1.yaml`

## Authority Reference
Resolve DN-013 from modular `delivery/nodes.yaml`; resolve REQ-018, NEG-003, NEG-005, NEG-009, KEEP-005 from `delivery/obligations.yaml`; resolve consumed interfaces, RISK-003/RISK-005/RISK-006/RISK-009 through RISK-012, and PROOF-013 from `delivery/contracts.yaml`.

Outcome: Historical/generic fixtures and a fresh-consumer scenario prove admission, frontier planning, build review, acceptance, correction, audit, Cockpit, setup, snapshot integrity, and absence of legacy execution in shipped product before terminal DN-015 retires the external bootstrap carrier.

## Shaping Boundary
The current shaper turns this aggregate into a bounded complete-system proof DAG only after corrected-authority DN-012 closure. New product implementation discovered here routes to its owning node rather than being patched by final audit.

Proof guidance: exercise public native validation over incident/generic fixtures, then one fresh-consumer design-to-audit workflow through real MCP, engine, writer policy, proof checkout, Cockpit, setup, and legacy snapshot under PROOF-013. Do not execute DN-015's real bootstrap-board finalization here.

## Shape Notes
Historical projection repairs to `bf5edd...` and `8cd277...` remain evidence of earlier admitted revisions.

[[2026-07-27]]
## Shape Notes
FINAL AUTHORITY REPROJECTED: DN-013 now follows append-only admission `admission-6c95c70c81a1` at digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`. DN-015 is a separate non-projected terminal node that consumes DN-013 proof and owns the real carrier retirement through builder mutation plus independent exact-commit acceptance.

[[2026-07-27T19:46:10+02:00]]
## Shape Notes

### Approval And Authority
- User approved the challenged five-leaf DN-013 graph on 2026-07-27 after reviewing status quo, problem, options, pros/cons/risks/confidence, recommendation, and expected outcome.
- Authority: DN-013/REQ-018/WF-007/PROOF-013 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; DN-012 archive commit `9934178bdea966990cf28164edffa86ef49e077f` is current.
- Shaper-challenger decision: pass. It verified authority, public APIs, scenario closure, implementation availability, and T5's real FastAPI/Cockpit boundary. Soft proof wording was tightened before task creation.

### Readiness And Contract Authorities
- Canonical loader probe proved the eight existing historical fixtures currently fail as retired physical `graph.yaml` packages, so #2094 owns modular migration plus semantic replay without a production compatibility path.
- Current public sources provide stable DV diagnostics, modular models/digests, public MCP show/validate/admit/pick/start/finish/reject operations, shared dispatch coordination, `RuntimeTransaction`, Git history, exact-commit `ProofCheckoutManager`, public setup, real FastAPI, and the serial desktop/mobile Playwright project.
- No material product/interface decision is missing. A product defect discovered by proof returns to its owning delivery node and #1968; DN-013 does not patch it.

### Approved Graph
- #2094 P17-01: modularize and replay four historical defective/corrected pairs.
- #2095 P17-02: deterministic generated graph admission properties.
- #2096 P17-03: receipt, supersession, invalidation, correction, and transaction recovery properties.
- #2097 P17-04: temporary fresh consumer through public design/admission/MCP plan-build-accept-correct-audit.
- #2098 P17-05: real FastAPI plus desktop/mobile Cockpit over #2097 state and durable DN-015 handoff evidence.
- #2094 through #2097 are parallel; #2098 depends on #2097. This aggregate depends on all five and moves to `collect`.

### Change Module Map
| Module | Planned Change | Owner |
|---|---|---|
| Historical admission fixtures | Replace retired physical fixture layout and replay public admission | #2094 |
| `serve/kanban/tests` proof assets | Add generated graph and runtime-history matrices | #2095, #2096 |
| MCP/Cockpit proof support | Assemble current public setup, MCP, writer, Git, and checkout boundaries | #2097 |
| Cockpit E2E | Observe #2097 state through real FastAPI on desktop/mobile | #2098 |
| Production modules | Read-only dependencies; route defects to owning nodes | aggregate condition |

### Product Invariant And Promise Coverage
| Invariant | Owner | Boundary |
|---|---|---|
| Four historical defect pairs reject/admit semantically | #2094 | public validation/admission |
| Graph validity is not bootstrap-overfit | #2095 | generated canonical load/admission |
| Current receipt and corrective history survive failures | #2096 | public runtime/invalidation/transaction |
| Fresh consumer completes design through audit with one correction | #2097 | public setup/MCP/engine/writer/checkout |
| Operator sees corrective/final state and release proof | #2098 | built SPA plus real FastAPI |

REQ-018 incident, generic graph, generic runtime, complete native workflow, and Cockpit clauses map respectively to #2094, #2095, #2096, #2097, and #2098 ACs. NEG-003/NEG-009 are re-proved by #2097 read-only independent acceptance/audit; NEG-005 and shape-era absence remain admitted predecessor evidence and public plan/build/accept/audit inventory. DEC-036 excludes DN-015/PROOF-016 live finalization from every leaf.

### Dependency And Scenario Closure
- #2094 inputs: present fixture pairs plus modular loader/admission and DV literals.
- #2095 inputs: canonical graph models, digest join, validator, admission publication, topological job generation.
- #2096 inputs: receipt/job/attempt/finding stores, runtime, invalidation, repository-history classifier, shared transaction.
- #2097 inputs: public setup, installed design contracts, public MCP lifecycle, shared writer coordination, Git history, proof checkout.
- #2098 inputs: #2097 completed/corrective consumer, built SPA, real backend/SSE, Playwright.
- Enumerated classes cover four incidents; four valid and eight invalid graph families; five receipt classes, two corrective routes, and three transaction interruption points; fresh setup, authority refusal, normal lifecycle, rejection/correction/re-accept/audit; desktop/mobile request/current-chain/nonblank/error/overflow checks.
- #2097 complexity waiver is approved because splitting the design-to-audit flow would bypass PROOF-013's assembled boundary.

### Board Audit
Kanban queries confirmed #2094-#2098 titles, bodies, ACs, priorities, tags, parent links, proof bundles, build statuses, and unclaimed state. #2098 depends only on #2097; #1990 includes all five dependencies and is intentionally blocked in `collect` until they complete. All 18 recalled shaper memories were assessed.
