---
id: 2047
title: 'P7-01: Define the resumable frontier planning workflow'
status: archived
priority: high
created: 2026-07-25T15:09:25.843626+02:00
updated: 2026-07-25T15:16:36.488562+02:00
tags:
  - phase-7
  - scope:agent
  - planner
  - workflow
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-006
  - packet:DN-006-PK-001
  - interface:IF-007
parent: 1983
depends_on: []
ac:
  - 'AC-1: Given one engine-started initial or reconciliation `plan` job, `w-frontier-planning`
    rehydrates the current `show_change`, `show_job`, relevant receipts, target-node
    contract, source evidence, and prior node plan before proposing changes, processes
    only the selected target, and requires a fresh `pick_jobs` result after each atomic
    completion; artifact inspection verifies ordering and resume/checkpoint rules.'
  - 'AC-2: Given an admitted target node, the skill emits one complete packet DAG
    whose packets name outcome, obligations, in/out scope, modules/interfaces, dependencies,
    acceptance scenarios, canonical impact closure, proof/outputs, profile, and context
    budget, while enforcing REQ-024 outcome cohesion and admitted-node subset rules;
    artifact inspection maps the packet contract to IF-007.'
  - 'AC-3: Given a proposed interface, migration, risk, proof, or outcome expansion,
    an unresolved material assumption, or a non-pass independent plan review, the
    skill forbids a success payload, preserves prior completed plans, and routes one
    material choice through a Decision Request or broader expansion to Specification
    re-entry; artifact inspection maps NEG-008 and RISK-007 failure semantics.'
  - 'AC-4: Given a reviewed node plan, the skill returns one structured planner success
    payload containing the source-declared public `finish_plan` inputs `receipt_id`,
    `code_revision`, `evidence`, `evidence_ids`, `impact_closure`, `node_plan`, `build_job_ids`,
    and `accept_job_id`, and never calls lifecycle completion itself; artifact inspection
    verifies orchestration ownership and field identity.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-006-PK-001`. Resolve normative behavior from `DN-006`, `IF-007`, `REQ-004`, `REQ-024`, `REQ-025`, `NEG-005`, `NEG-008`, `KEEP-004`, `RISK-007`, `RISK-011`, and `PROOF-005`; this record is not specification authority.

## Outcome
Define `w-frontier-planning` as the canonical warm-session procedure for engine-selected initial and reconciliation plan jobs, target-bounded packet DAGs, independent review, structured completion, and material-discovery refusal.

## Envelope
In: the workflow skill and its exact structured planner result contract.

Out: agent/orchestrator wiring, engine or MCP schema changes, proof scenarios, builder behavior, and Specification authority edits.

Proof guidance: inspect the assembled workflow against current public query/request tools, `FinishPlanParams`, admitted packet/refinement rules, and the fresh-pick requirement; no model-response substitute proves this packet.

[[2026-07-25T15:14:41+02:00]]
## Builder Notes
Added the canonical `w-frontier-planning` workflow as the only product change. No agent, orchestrator, runtime, MCP, test, setup, seed, or admitted-authority file changed.

### AC Evidence
- AC-1: The authority boundary and Steps 1, 2, and 7 require the orchestrator-supplied active plan-job identity; current `show_change`, `show_job`, target entities, relevant receipts, prior target plan, and focused source evidence are re-read for each initial or reconciliation job. Contradictions fail closed, and another job requires a fresh public pick after reported atomic completion.
- AC-2: Step 4 defines a complete outcome-cohesive packet contract covering identity, outcome, obligations, in/out scope, modules/interfaces, dependencies, acceptance scenarios, canonical impact closure, proof, required outputs, profile, and context budget. Steps 3 and 5 enforce admitted target subsets, boundary-valid proof, acyclicity, ownership coverage, and bounded builder context.
- AC-3: Step 3 exhaustively distinguishes legal refinement from unadmitted outcome/interface/ownership/failure/migration/security/lifecycle/workflow/proof/dependency expansion. One researched material choice creates a Decision Request and returns `RequestCreated`; broader authority change returns `SpecificationReentry`; stale/malformed/review failures return `PlanBlocked`. None can return success or roll back completed plans.
- AC-4: Step 6 defines `PlannerSuccess` with precisely the eight planner-owned public `finish_plan` inputs and states that the orchestrator supplies immutable dispatch identity and completion time. The planner is forbidden to pick, start, finish, release, or directly write authority, plans, jobs, or receipts.

### Validation
- Skill validator: pass.
- Focused lint and Markdown validation: pass; unrelated repository TODO warnings only.
- Mechanical payload/model comparison: `PlannerSuccess` keys equal the expected eight fields and all exist in public `FinishPlanParams`.
- Applicable ecosystem regressions: 7 passed.
- `builder-challenger`: pass after independently rerunning the same checks.

[[2026-07-25T15:16:01+02:00]]
## Verify Notes
Verified committed builder revision `39ce9cdaa509782d4577994a327bfa738fdb72d9` against DN-006, IF-007, REQ-004/024/025, NEG-005/008, RISK-007/011, and the public runtime contracts without further code changes.

### AC Evidence
- AC-1: The committed skill treats orchestrator-started job identity as immutable and rehydrates current change digest, projected job contract, graph entities, receipts, prior target plan, and source for every selected job. Initial plans consume admitted predecessor contracts without acceptance; reconciliation additionally consumes accepted implementation evidence; another target requires a fresh pick and full rehydration.
- AC-2: The complete packet table and validation gate cover all required semantic metadata while remaining compatible with NodePlanStore's JSON-shaped persistence and NativeRuntime's canonical ID, DAG, closure, and admitted-target enforcement.
- AC-3: Legal refinement and unadmitted expansion are explicitly separated. Decision Request, Specification re-entry, and blocked routes are structured non-success dispositions; non-pass review, stale authority, or material expansion cannot complete lifecycle work or roll back persisted prior plans.
- AC-4: The eight `PlannerSuccess` keys match public `FinishPlanParams`; lifecycle tools and direct authority/plan/job/receipt writes remain outside planner authority, with execution identity and completion time owned by the orchestrator.

### Validation
- `git show --check` on the builder revision: clean.
- Skill validator: pass.
- Focused lint and Markdown checks: pass; unrelated repository TODO warnings only.
- Applicable ecosystem regressions: 7 passed.
- Mechanical PlannerSuccess-to-FinishPlanParams field comparison: pass.
- `verifier-challenger`: pass; all AC, source fidelity, metadata compatibility, initial/reconciliation semantics, and lifecycle ownership are supported.

[[2026-07-25T15:16:36+02:00]]
## Collect Notes
Archived after confirming committed builder revision `39ce9cdaa509782d4577994a327bfa738fdb72d9`, committed verifier record `7630324a20d400ca044f8b858491cc6433c93860`, direct evidence for all four AC, clean skill and lint validation, seven applicable ecosystem regressions, exact public-model field alignment, and both mandatory challenger passes. No adjacent runtime, agent, wiring, test, or authority scope was introduced.
