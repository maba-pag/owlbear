# Delivery Operating Model Reframe

> **Owning task:** #1968 — Replace OwlBear delivery pipeline with admitted change graphs
> **Date:** 2026-07-25
> **Question:** How should the admitted graph-authoritative design be refined after implementation showed that specification work dominates delivery cost, one-node-at-a-time shaping is sequential, and the monolithic graph is difficult to author?
> **Status:** Recommended design re-entry; user authorized starting the sequence on 2026-07-25

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
| `.owlbear/changes/replace-delivery-pipeline/intent.md` | Product Promise makes Kanban the implementation control surface and creates one shape job per node. | Approved intent predates implementation evidence. |
| `.owlbear/changes/replace-delivery-pipeline/design.md` §§2, 6–9, 14–15 | Authority and work are already separate planes, but shaping is per-node, tracked shaping/building is serialized, and Kanban is the default surface. | Describes the target, not steady-state measurements. |
| `.owlbear/changes/replace-delivery-pipeline/decisions.yaml` DEC-003, DEC-004, DEC-006, DEC-010, DEC-011, DEC-014–DEC-016 | Graph authority, operational-job separation, bounded shaping, one design session, four-file storage, one writer, cohesive packets, and a Kanban-centered package were explicit choices. | Several choices remain sound even if presentation and dispatch policy change. |
| `.owlbear/changes/replace-delivery-pipeline/graph.yaml` | One 1,415-line, 57 KB YAML file stores 24 requirements, workflows, modules, interfaces, migrations, risks, proofs, 14 nodes, admission metadata, and execution plans. | This replacement is larger than a typical future change. |
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
- one runtime and lifecycle contract regardless of execution driver.

These controls address observed completeness, provenance, recovery, and self-approval failures. Their value does not depend on Kanban being the primary product surface.

### 3.2 Reframed phase model

```text
Phase 1 — Definition / Specification
idea -> intent -> design -> decisions -> delivery graph -> admission

Phase 2 — Delivery
node planning -> build -> node acceptance -> final audit
```

Delivery nodes belong to Specification because they state required outcomes, dependencies, interfaces, risks, and proof ownership. Implementation packets belong to Delivery because they refine one admitted node into executable work.

Definition and Delivery are peer product phases. Cockpit should not present Changes as supporting context for a primary Kanban surface. Changes owns specification progress and admitted authority; Delivery owns current work, claims, blocks, attempts, findings, receipts, acceptance, and audit.

### 3.3 Batch node planning

The invariant is one atomic plan, validation result, review disposition, digest, and shape receipt per node. It is not one agent startup per node.

One resumable planning session should process the eligible node frontier while context is warm. Each node remains independently transacted and receipted. A batch failure must not publish partial plans. A material discovery still returns to global design and re-admission.

Shape readiness and build readiness should be distinct. A node may be plan-ready from admitted predecessor contracts even when predecessor implementation is not yet accepted. Build and acceptance remain dependency-gated.

### 3.4 Adaptive delivery execution

Graph authority and orchestration are independent choices. Use the same engine operations, leases, attempts, findings, and receipts through either driver:

| Work topology | Preferred driver |
| --- | --- |
| Narrow serial packet chain with one profile and no wait/block boundary | Persistent builder session with inline challenger |
| Independent ready branches, profile changes, concurrent read-only proof, waits, blocks, or recovery needs | Graph-aware orchestrator |
| Every completed delivery node | Fresh independent acceptor |
| Complete accepted change | Fresh independent auditor |

Direct execution is not a quick lane and does not bypass jobs. It consumes engine-selected work and produces the same durable lifecycle evidence. Automatic selection should wait for measurements from representative native changes; record the contract now, implement after batch planning.

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
    manifest.yaml
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
| Peer Definition and Delivery phases; remove Kanban-central wording | Intent, design, DEC-016 rationale, REQ-009/010, DN-011, Cockpit contract | Small, mostly future work |
| Batch planning of eligible nodes with per-node atomic outputs | DEC-006, REQ-004/024, WF-002, IF-006/007, DN-005/006, PROOF-005 | Medium, about 2 focused packets |
| Separate delivery authority from node plans | DEC-011, IF-001/007, DN-001/006, loader/runtime/health | Medium, about 2–3 packets |
| Modular delivery-authority files | DEC-011, IF-001, DN-001/002, PROOF-001/002, fixtures | Medium, about 3 packets |
| Adaptive direct execution over the same lifecycle | DEC-005/007/014, REQ-022, IF-004, DN-004/007/009, PROOF-014 | Medium, about 2–3 packets; defer implementation |
| YAML line-length exception | `.editorconfig` and seed policy if distributed | Tiny, one focused configuration packet |
| Re-admission and bootstrap projection refresh | All changed semantic authority; #1968 and affected node projections | Small but mechanical |

The modular layout and plan separation overlap. The expected net amendment is about five to seven focused packets, most replacing future DN-005/DN-006/DN-011 work rather than adding an independent program.

## 4. Recommendation, Confidence, And Limits

### Recommendation

Re-enter global design through #1968 now. Do not repair or dispatch contained DN-009 work until the amended authority is admitted.

Sequence:

1. Route #1968 from `collect` to `shape` for material design re-entry.
2. Record user decisions for peer phases, delivery-node/packet boundary, batch planning, and physical authority separation.
3. Add the native-change YAML line-length exception.
4. Reconcile intent, design, decisions, and delivery authority; run deterministic validation and independent challenge.
5. Re-admit the exact amended digest.
6. Assess completed DN-001–DN-004 against changed contracts; invalidate/rebuild only where a concrete contract changed.
7. Refresh #1968 and affected bootstrap projections, preserving DN-009 partial-commit containment until its complete replacement graph is ready.
8. Implement modular authority and isolated plans before DN-005/DN-006 teach agents the interim monolithic format.
9. Implement batch planning in DN-006 and peer Definition/Delivery Cockpit in DN-011.
10. Measure three representative native changes before implementing automatic direct-versus-orchestrated selection.

### Confidence

- Graph authority and peer-phase reframe: **0.94**.
- Delivery nodes in Specification, packets in Delivery: **0.92**.
- Batch planning with per-node atomic evidence: **0.88**.
- Modular delivery authority plus isolated plans: **0.84**.
- Immediate line-length exception: **0.98**.
- Adaptive direct execution contract: **0.82**; automatic selection criteria remain unproven.

### Limits

- The observed change is a self-hosting bootstrap and overstates normal complexity.
- Local session data cannot verify billable token counts.
- The optimal modular file granularity needs a design decision; the proposed three delivery files are a bounded starting point, not an invariant.
- Digest parity and transaction recovery across modular files require executable proof before migration.
- No authority file or board graph was changed by this research. The recommendations become binding only through user decisions, reconciled authority, challenge, and re-admission.
