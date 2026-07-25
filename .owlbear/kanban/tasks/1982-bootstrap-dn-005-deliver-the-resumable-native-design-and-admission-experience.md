---
id: 1982
title: 'Bootstrap DN-005: Deliver the resumable native design and admission experience'
status: collect
priority: medium
created: 2026-07-22T01:07:06.767745+02:00
updated: 2026-07-25T14:29:26.251629+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-005
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1978
  - 1981
  - 2043
  - 2044
  - 2045
  - 2046
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-005` at the recorded digest
    from modular delivery authority and creates one outcome-cohesive packet DAG whose
    task records reference the same change, digest, and node; verify by task-field
    and dependency audit against `delivery/nodes.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-005` modules, interfaces, risks, and
    `PROOF-004`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-005` and `PROOF-004`, verified
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
- `delivery_digest`: `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`
- `delivery_node_id`: `DN-005`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990|DN-005|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-3f6c65628991.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-005` in `.owlbear/changes/replace-delivery-pipeline/delivery/nodes.yaml` and referenced contracts in `delivery/contracts.yaml` and `delivery/obligations.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: `/ideate` and `/design` operate one durable user-facing session that preserves intent and decisions, delegates evidence and challenge, presents the complete graph, and admits only approved revisions.
- Modules: `MOD-003`
- Produces: `IF-006`
- Consumes: `IF-001`, `IF-002`, `IF-010`
- Risks: `RISK-007`
- Proof: `PROOF-004`
- Delivery dependencies: `DN-002`, `DN-009`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise the real ideate/design prompt and agent contracts over public change tools, including interruption resume, one-question decisions, unresolved-authority refusal, and admitted fixture; only external research response may be replaced below `PROOF-004`.

[[2026-07-25T14:29:26+02:00]]
## Shape Notes
Shaped DN-005 from admitted modular authority at digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`. Refreshed the stale aggregate projection from digest `9387dea789fb` and `graph.yaml` to the current receipt plus `delivery/nodes.yaml`, `delivery/contracts.yaml`, and `delivery/obligations.yaml` before child creation.

Current-source grounding found `/ideate` ending in an OpenSpec handoff and no `/design`, designer role, designer challenger, or native design-session workflow. Public consumed tools are `list_changes`, `show_change`, `validate_change`, and `admit_change`; challenge evidence already uses `AdmissionEvidence` dispositions, so no new tool or schema is introduced.

### Change Module Map
- `share/skills/w-design-session/SKILL.md`: new owner of resumable native designer procedure; #2043.
- `share/agents/`, `share/prompts/`, `share/WIRING.md`: designer, read-only challenger, shared entries, and executable wiring; #2044.
- Durable agent scenario tests: interaction/refusal evidence #2045 and assembled successful admission/replay #2046.

### Product Invariant And Promise Coverage
- One durable session, one-question decisions, full Product Promise, canonical evidence, qualified memory, and adaptive architecture: #2043 AC-1 through AC-3 (`REQ-001`, `KEEP-001`, `KEEP-002`, `KEEP-003`, `KEEP-008`, `KEEP-009`).
- Refusal and admission ordering: #2043 AC-4, proved at the designer boundary by #2045 and #2046 (`IF-006`).
- One designer surface plus independent structured challenge: #2044.
- Required durable `PROOF-004`: #2045 covers resume, decisions, unresolved authority, and one representative failed-assessment route; #2046 covers complete admission and replay.

### Dependency And Scenario Closure
#2043 uses archived DN-002/#1978 and DN-009/#1981 interfaces. #2044 depends on #2043. #2045 depends on #2043 and #2044. #2046 depends on #2045. Admission evaluator-family completeness remains owned by archived DN-002/PROOF-002; DN-005 only proves designer routing on one representative failed assessment. DN-006 planner, DN-012 setup/seed/OpenSpec removal, and product code remain excluded.

Shaper challenge required three corrections: split independent negative proof families, remove duplicate DN-002 evaluator ownership, and refresh the stale parent projection. Final challenge passed after all three were resolved. Board audit confirms four build tasks #2043-#2046, current digest/parent/packet tags, intended dependencies, and #2043 as the sole dependency-ready leaf. Aggregate dependencies now gate collection on all four descendants.
