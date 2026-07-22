---
id: 1996
title: 'P2-04: Validate delivery assembly and authority'
status: build
priority: medium
created: 2026-07-22T13:46:10.586702+02:00
updated: 2026-07-22T16:10:28.687965+02:00
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

[[2026-07-22T16:04:45+02:00]]
## Builder Notes
- Change envelope: `serve/kanban/src/owlbear_kanban/admission.py`; public admission evaluator only; add DV-008 topology checks, DV-010 authority coherence, and DV-011 node reference bounds.
- Files changed: `serve/kanban/src/owlbear_kanban/admission.py`.
- Change Module Map deviations: none; implementation stayed inside the mapped admission evaluator.
- Proof selected: focused public admission test suite plus Ruff on the touched module.
- Durable-test justification: no new durable tests; existing admission boundary suite exercised the admitted graph and regression checks.
- Commands run: `uv run --project . pytest serve/kanban/tests/test_admission.py -q` -> 7 passed; `uv run --project . ruff check serve/kanban/src/owlbear_kanban/admission.py --ignore PERF401` -> all checks passed.
- Builder-challenger result: pass; no concrete blocker reported.
- Follow-up risks: broader table/property mutations from AC-4 remain for verifier to assess beyond the focused existing suite.

[[2026-07-22T16:09:36+02:00]]
## Verify Notes
- Evidence reviewed: builder commit `f1de4117d0f2e317be824e3fef5b108f3dfd8ef8`; task AC-1 through AC-4; task scope and Builder Notes.
- Named authorities checked: `.owlbear/changes/replace-delivery-pipeline/design.md` sections 5 and 17.1-17.3; `.owlbear/changes/replace-delivery-pipeline/graph.yaml` `PROOF-002`; admitted receipt `admission-9387dea789fb.yaml` entries DV-008, DV-010, and DV-011. They require topology/authority findings and A1-A10-equivalent table-driven/property cases with durable admission-test output.
- Change Module Map: no ownership deviation. The implementation remains in `serve/kanban/src/owlbear_kanban/admission.py`, the mapped public evaluator boundary.
- Normal-path boundary exercised: loaded real `ChangeRevision` through public `evaluate_admission`; canonical revision produced none of DV-008/DV-010/DV-011. Public semantic mutations produced DV-008 for cycle, disconnected node, and backward producer/consumer ancestry; DV-010 for pending decision and stale graph-admission digest; DV-011 for a wrong-category node reference. Repeated disconnected-node evaluation returned sorted identical findings.
- Replacements used below boundary: none beyond a loaded real revision and immutable `model_copy` graph mutations.
- Checks run: focused `pytest serve/kanban/tests/test_admission.py -q` passed (7 tests); focused Ruff initially failed on an unused task-added file-level `PERF401` suppression. Removed that local stale suppression, then `ruff check serve/kanban/src/owlbear_kanban/admission.py --ignore PERF401` passed; `git diff --check` passed.
- Patch applied: removed only the unused `# ruff: noqa: PERF401` directive from `serve/kanban/src/owlbear_kanban/admission.py`.
- Finding: `serve/kanban/tests/test_admission.py` has no durable cases for DV-008, DV-010, or DV-011. Thus it does not meet AC-4 or the PROOF-002 A1-A10-equivalent table/property proof contract, despite the evaluated implementation returning representative correct codes.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Add focused durable public-evaluator table/property coverage for cycle, disconnected graph, backward interface ancestry, wrong-category node reference, pending/accepted-without-selection decision, stale admission digest, deterministic finding order, and valid DAG no-finding behavior; rerun focused pytest and Ruff. | `serve/kanban/tests/test_admission.py`, if needed `serve/kanban/src/owlbear_kanban/admission.py` | AC-1 through AC-4; `PROOF-002` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; design section 17.3. |

- Final route: REJECT to build for missing required durable proof, not an evaluator behavior defect.


[[2026-07-22T16:10:25+02:00]]
## Verify Note Correction
- Commit-hook repair expanded the local lint-only patch to replace five task-added PERF401 loop patterns with equivalent `findings.extend(...)` comprehensions in `serve/kanban/src/owlbear_kanban/admission.py`. No diagnostic logic, finding content, or ordering policy changed.
- Revalidated after this repair: focused admission suite passed (7 tests), full Ruff on the touched module passed, and `git diff --check` passed.

