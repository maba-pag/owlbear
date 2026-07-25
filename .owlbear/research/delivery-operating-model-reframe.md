# Delivery Operating Model Reframe

> **Owning task:** #1968 — Replace OwlBear delivery pipeline with admitted change graphs
> **Date:** 2026-07-25
> **Question:** How should the admitted graph-authoritative design be refined after implementation showed that specification work dominates delivery cost, one-node-at-a-time shaping is sequential, and the monolithic graph is difficult to author?
> **Status:** Authority admitted at `3f6c65628991`; corrective projection planning active

## 1. Context and Question

The graph-authoritative foundation was designed to prevent known product, interface, migration, risk, and proof obligations from entering implementation without an owner. Implementation of DN-001 through DN-004 validates that this foundation is technically viable, but the bootstrap also exposed three operating-model problems:

1. Specification and shaping consume materially more user interaction and context than implementation.
2. The approved one-shaping-session-per-node policy produces a narrow, sequential frontier even when several nodes could be planned coherently from admitted contracts.
3. `graph.yaml` combines admitted delivery authority, long explanatory records, admission metadata, and mutable node plans in one large file.

The user observed roughly 5x more elapsed effort and 20–50x more tokens in shaping than implementation. Local session history does not contain billable token records, so the token ratio cannot be independently verified. It does confirm the direction: the main redesign/shaping thread reached 83 turns and about 329,000 combined user/assistant characters, while recent orchestration sessions generally used 4–12 turns and short prompts.

The question is not whether to discard graph authority. It is how to retain specification completeness and exact evidence while making Delivery proportional to the work that actually requires scheduling, recovery, specialization, or independent proof.

## 2. Sources Studied

| Source | Material finding | Limit |
| --- | --- | --- |
| `.owlbear/changes/replace-delivery-pipeline/intent.md` | Specification and Delivery are peer phases; admitted nodes enter a broad initial planning frontier and predecessor acceptance triggers reconciliation before dependent build. | Describes the selected target, not steady-state measurements. |
| `.owlbear/changes/replace-delivery-pipeline/design.md` §§2, 6–9, 14–15 | Modular authority, isolated plans, engine-owned scheduling, one invocation per job, and read-only final audit now form one coherent target. | Corrective implementation remains pending. |
| `.owlbear/changes/replace-delivery-pipeline/decisions.yaml` DEC-027–DEC-033 | Accepted choices fix invocation scope, peer phases, frontier planning, modular storage, transactional ownership, reconciliation, and `plan` vocabulary. | Superseded decisions remain historical evidence. |
| `.owlbear/changes/replace-delivery-pipeline/graph.yaml` | The monolithic file remains the admitted bootstrap carrier for 14 nodes while MIG-004 owns physical modularization and isolated plans. | This replacement is larger than a typical future change. |
| `serve/kanban/src/owlbear_kanban/change.py` | `load_change()` hard-codes one physical `graph.yaml`; canonical delivery hashing already joins logical sections. | Modular storage requires loader and fixture work. |
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Shape completion round-trips the complete `graph.yaml` to add one `execution.node_plans` entry. | Confirms specification authority and delivery planning share a mutation surface. |
| `.editorconfig` and `.yamllint.yml` | EditorConfig enforces 120 characters globally while yamllint disables line length, creating a cosmetic failure outside schema/admission validation. | A lint exception removes nuisance failures but not graph size. |
| Archived task #2025 | Independent verification repeatedly caught missing assembled proof, exact runner handoff, and causal result routing after inline challengers passed. | A difficult bootstrap integration task, not a representative narrow change. |
| Tasks #1981 and #2027–#2031 | DN-009 planning passed three challenger rounds, then legacy task creation failed on a 500-character AC limit and required partial-graph containment. | Native atomic publication should remove this specific legacy failure. |
| Local Copilot session store | Specification interaction is much larger than orchestration interaction by turn and character proxies. | Local storage has no per-event token accounting. |

No new external source was used.

## 3. Analysis

### 3.1 What remains invariant

Keep these architectural properties:

- one admitted semantic delivery revision;
- stable delivery-node, interface, risk, proof, and requirement identities;
- deterministic admission before implementation;
- separate declarative authority and operational runtime state;
- immutable attempts and receipts with precise invalidation;
- one tracked-file writer in the shared worktree;
- read-only independent node acceptance and final change audit;
- append-only corrective work rather than mutable historical completion;
- engine-selected jobs with one runtime and lifecycle contract;
- one fresh top-level agent invocation per job.

These controls address observed completeness, provenance, recovery, and self-approval failures. Their value does not depend on Kanban being the primary product surface.

### 3.2 Reframed phase model

```text
Phase 1 — Specification
idea -> intent -> design -> decisions -> delivery graph -> admission

Phase 2 — Delivery
plan -> build -> node acceptance -> final audit
```

Delivery nodes belong to Specification because they state required outcomes, dependencies, interfaces, risks, and proof ownership. Implementation packets belong to Delivery because they refine one admitted node into executable work.

Specification and Delivery are peer product phases. Cockpit should not present Changes as supporting context for a primary Kanban surface. Changes owns specification progress and admitted authority; Delivery owns planning plus current work, claims, blocks, attempts, findings, receipts, acceptance, and audit.

### 3.3 Batch node planning

The invariant is one atomic plan, validation result, review disposition, digest, and shape receipt per node. It is not one agent startup per node.

One resumable planner processes every plan-ready node in the eligible frontier while context is warm. Each node is independently validated, challenged, published, digested, transacted, and receipted. Failure for one node must not roll back already published plans or expose a partial plan for the failing node. A material discovery still returns to interactive Specification and re-admission.

Plan readiness and build readiness are distinct. A node may be initially plan-ready from admitted
predecessor contracts even when predecessor implementation is not yet accepted. Predecessor
acceptance makes dependent plans reconciliation-required; dependent builds remain gated until those
reconciled plans and predecessor accept receipts are current.

The planner reconciles downstream nodes when predecessor acceptance receipts make them plan-ready. It may autonomously update implementation detail within admitted authority. One material product or architecture choice becomes a Decision Request; a broader design discussion re-enters interactive Specification. Action Requests remain reserved for operations only the user can perform. Final audit stays read-only and never mutates plans.

### 3.4 Delivery execution boundary

Graph authority and orchestration are independent values, but the execution driver is now fixed:

| Boundary | Selected behavior |
| --- | --- |
| Scheduling | Native engine `pick_jobs` result and lifecycle gates |
| Dispatch | Thin orchestrator invokes the engine-selected profile for one job |
| Build | One fresh builder invocation completes exactly one build job and its inline review |
| Every completed delivery node | Fresh independent acceptor |
| Complete accepted change | Fresh independent auditor |

Do not add cross-job builder continuation. Synchronous `runSubagent` cannot resume an earlier session; continuation inside one call would carry prior-job context, risk compaction of critical initial instructions, complicate orchestrator communication, and duplicate dispatch behavior for limited input-token savings. Cohesive packets may reduce startup overhead, but packet boundaries must follow outcomes, ownership, proof, context, and failure domains rather than an arbitrary target count.

### 3.5 Authority storage and graph usability

The current physical format conflates three concerns:

1. human-readable specification reasoning;
2. machine-validated delivery authority;
3. post-admission node-plan mutation.

Recommended target:

```text
.owlbear/changes/<change-id>/
  intent.md
  design.md
  decisions.yaml
  delivery/
    obligations.yaml
    contracts.yaml
    nodes.yaml
  plans/
    DN-001.yaml
  receipts/
```

`obligations.yaml` owns requirements, negative requirements, preserved behaviors, and workflows. `contracts.yaml` owns modules, interfaces, migrations, risks, and proofs. `nodes.yaml` owns delivery nodes and dependency edges. Each `plans/DN-*.yaml` owns one post-admission implementation plan.

The loader should join these files into the existing logical `DeliveryGraph` model. Canonical delivery hashing remains over the joined logical delivery sections, independent of physical wrapping or filenames. Node plans remain excluded from the delivery digest and gain isolated transaction paths.

As an immediate usability repair, disable EditorConfig line-length enforcement for `.owlbear/changes/**/*.yaml`. Keep YAML syntax, schema, identity, reference, digest, and admission validation strict. Cosmetic wrapping must not invalidate semantic authority.

### 3.6 Amendment radius

| Change | Primary affected authority/work | Estimated effort |
| --- | --- | --- |
| Peer Specification and Delivery phases; remove Kanban-central wording | Intent, design, DEC-016 rationale, REQ-009/010, DN-011, Cockpit contract | Small, mostly future work |
| Batch planning of eligible nodes with per-node atomic outputs | DEC-006, REQ-004/024, WF-002, IF-006/007, DN-005/006, PROOF-005 | Medium, about 2 focused packets |
| Separate delivery authority from node plans | DEC-011, IF-001/007, DN-001/006, loader/runtime/health | Medium, about 2–3 packets |
| Modular delivery-authority files | DEC-011, IF-001, DN-001/002, PROOF-001/002, fixtures | Medium, about 3 packets |
| One invocation per engine-selected job | DEC-027, builder/orchestrator contracts, agent capabilities | Small; removes rather than adds continuation work |
| Replace `shape` with `plan` lifecycle vocabulary | DN-003 runtime, DN-004 dispatch/IF-015, DN-009 assembled MCP, agents/UI/tests | Material corrective rework; no compatibility alias |
| YAML line-length exception | `.editorconfig` and seed policy if distributed | Tiny, one focused configuration packet |
| Re-admission and bootstrap projection refresh | All changed semantic authority; #1968 and affected node projections | Small but mechanical |

The modular layout and plan separation overlap. The expected net amendment is about five to seven focused packets, most replacing future DN-005/DN-006/DN-011 work rather than adding an independent program.

## 4. Recommendation, Confidence, And Limits

### Recommendation

Complete the active global design re-entry through #1968. Do not repair or dispatch contained DN-009 work until the amended authority is admitted.

Completed design decisions:

1. Specification ends with admitted delivery nodes; packet plans begin Delivery.
2. A resumable frontier planner publishes one atomic, independently reviewed plan per node.
3. Delivery authority is modularized into obligations, contracts, and nodes; plans are separate per-node files.
4. Accepted predecessor nodes trigger autonomous downstream plan reconciliation within admitted authority and block dependent builds until superseding plans are current.
5. Final audit remains independent and read-only.
6. The engine picker owns scheduling; the orchestrator dispatches one fresh agent invocation per job.

Completed amendment work:

1. Accepted DEC-028 through DEC-033 record phase, planning, storage, control-plane, reconciliation, and job-kind choices; DEC-027 records one invocation per job.
2. DEC-006, DEC-007, DEC-011, and DEC-016 remain as superseded history.
3. Intent, design, and all joined graph contracts now describe modular authority, `plan` jobs, frontier planning, acceptance-triggered reconciliation, and peer Cockpit phases.
4. `.editorconfig` and `seed/.editorconfig` exempt native-change YAML from cosmetic line limits.
5. MIG-004 and amended DN-003/DN-004/DN-009 contracts explicitly own the breaking `shape` to `plan` correction and modular-storage migration without compatibility aliases.
6. Initial plan readiness derives from admitted predecessor contracts. Build readiness separately
requires a current plan receipt, authored packet dependencies, and predecessor accept receipts.
`finish_accept` causally marks dependent plans reconciliation-required and blocks dependent builds
until superseding plan receipts are current.
7. MIG-001 through MIG-004 are interface-reachable; MIG-004 owns modular storage and `plan` lifecycle correction across IF-001/003/004/007/015.
8. Exact digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990` is admitted with zero deterministic findings and a passing independent challenge. All 14 nodes are initially plan-eligible from admitted contracts and ordered by delivery topology; implementation still has one dependency root.

Remaining sequence:

1. Publish the challenged corrective graph for DN-001 modular loading, isolated plans, DN-002 plan admission, DN-003 lifecycle/reconciliation, and DN-004 dispatch/MCP routing.
2. Refresh #1968 and affected projections while preserving DN-009 containment until its replacement graph is complete.
3. Implement the corrective graph before DN-009 consumes IF-015 or DN-005/DN-006 teach the interim format.
4. Re-plan DN-009, frontier planning in DN-006, and peer Specification/Delivery Cockpit work in DN-011 against current authority.

### Confidence

- Graph authority and peer-phase reframe: **0.94**.
- Delivery nodes in Specification, packets in Delivery: **0.92**.
- Batch planning with per-node atomic evidence: **0.88**.
- Modular delivery authority plus isolated plans: **0.84**.
- Immediate line-length exception: **0.98**.
- One fresh invocation per engine-selected job: **0.96**.

### Limits

- The observed change is a self-hosting bootstrap and overstates normal complexity.
- Local session data cannot verify billable token counts.
- The selected three-file delivery layout still needs executable loader, digest, and transaction proof.
- Digest parity and transaction recovery across modular files require executable proof before migration.
- Bootstrap projection dispatch remains locked until the exact-digest corrective graph passes read-back audit.
