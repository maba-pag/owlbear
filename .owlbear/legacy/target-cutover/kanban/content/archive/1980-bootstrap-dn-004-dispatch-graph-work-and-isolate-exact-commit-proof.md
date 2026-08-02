---
id: 1980
title: 'Bootstrap DN-004: Dispatch graph work and isolate exact-commit proof'
status: archived
priority: high
created: 2026-07-22T01:06:00.529389+02:00
updated: 2026-07-24T22:22:19.740465+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-004
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1979
  - 2022
  - 2023
  - 2024
  - 2025
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-004` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-004` modules, interfaces, risks, and
    `PROOF-014`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-004` and `PROOF-014`, verified
    through Kanban queries and artifact inspection.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-004`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-004|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-004` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Graph-aware dispatch and orchestrator contracts release engine-selected jobs, serialize shared-worktree writers, recover attempts, replan from current state, and provide crash-safe disposable proof checkouts.
- Modules: `MOD-001`, `MOD-003`, `MOD-009`
- Produces: `IF-004`, `IF-005`
- Consumes: `IF-003`
- Risks: `RISK-002`, `RISK-004`
- Proof: `PROOF-014`
- Delivery dependencies: `DN-003`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise real engine-selected waves, writer leases, claims, structured completion, and disposable proof checkouts; replacements are limited to clock, subagent runner, and temporary repository below `PROOF-014`.

## Shape Notes

Shaped at delivery digest `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8` into compact authority projections:

- #2022 `DN-004-PK-001`: durable global writer coordination in existing `owlbear_kanban.dispatch`.
- #2023 `DN-004-PK-002`: deterministic native wave planning; depends on #2022.
- #2024 `DN-004-PK-003`: contained exact-commit proof checkout; independent of #2022/#2023.
- #2025 `DN-004-PK-004`: graph-aware orchestration and assembled PROOF-014; depends on #2022-#2024.

The challenger rejected and corrected four concrete drifts before passing the graph: modifying frozen IF-003 diagnostics, inventing `dispatch_runtime.py` despite IF-004 module authority, shorthand scenario families, and making writer coordination depend on descendant wave eligibility. Packet records reference canonical authority and do not duplicate node/interface/proof specifications. Board audit confirms parentage, dependency closure, build status, bounded AC, and expected dispatch layers.

[[2026-07-24T16:56:16+02:00]]
## Shape Notes

DN-004 shaping is complete at digest `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`. Created build packets #2022-#2025 with the challenged dependency graph `(#2022 || #2024) -> #2023 -> #2025` where #2025 also directly consumes #2022/#2024. Focused evidence: `uv run pytest -q tests/test_edit_task_contract.py` (2 passed), path-scoped `git diff --check`, MCP parent/dependency/status audit, and final shaper-challenger `pass`. All recalled memories were assessed; no authority expansion or global re-admission is required.

[[2026-07-24T22:22:19+02:00]]
## Collect Notes
- Classification: aggregate.
- Aggregate intent source: `DN-004` and `PROOF-014` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; the parent outcome is graph-aware dispatch, writer serialization, current-state replanning, recovery, and exact-commit disposable proof checkouts.
- Invariant map coverage: #2022 covers global writer coordination, #2023 deterministic dependency-aware native waves, #2024 canonical contained exact-commit proof checkouts, and #2025 the assembled IF-015 MCP/orchestrator flow and PROOF-014.
- Child coverage: `list_tasks(status="archived", parent=1980)` reports #2022, #2023, #2024, and #2025, each archived `completed`. The original parent query had no active children because archival moves them off-board.
- Parent dependency gate: #1979 plus #2022, #2023, #2024, and #2025 are all archived `completed`; the gate is satisfied. #2025 depends on #2022, #2023, and #2024, all completed.
- Latest child verification: each packet has current PASS evidence with no remaining follow-up; historical verifier rejections in #2023, #2024, and #2025 were superseded by their later PASS notes after targeted repairs.
- SHA-linked normal-path proof: #2025 Verify Notes record builder revision `f0bb8c256` and `uv run pytest serve/mcp-kanban/tests/test_mcp_surface_contract.py serve/kanban/tests/test_dispatch_runtime.py serve/kanban/tests/test_proof_checkout.py tests/test_skill_authority_wiring.py tests/test_agentview_ac_params.py -q` passing 48 tests. The scenario drives public IF-015 MCP tools over real `DispatchRuntime`; only the PROOF-014-permitted subagent runner is replaced. `git merge-base --is-ancestor f0bb8c256 HEAD` confirmed the tested revision is an ancestor of the current checkout.
- Residual decisions: no pending or resolved structured requests for #1980.
- Archive rationale: the DN-004 aggregate contract, PROOF-014 normal-path proof, child coverage, dependency closure, and request state are all satisfied.
