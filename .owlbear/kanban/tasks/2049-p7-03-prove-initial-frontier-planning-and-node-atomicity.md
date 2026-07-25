---
id: 2049
title: 'P7-03: Prove initial frontier planning and node atomicity'
status: verify
priority: high
created: 2026-07-25T15:09:42.182016+02:00
updated: 2026-07-25T15:35:21.682752+02:00
tags:
  - phase-7
  - scope:test
  - planner
  - frontier
  - atomicity
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-006
  - packet:DN-006-PK-003
  - interface:IF-007
  - proof:PROOF-005
parent: 1983
depends_on:
  - 2048
ac:
  - 'AC-1: Given the real admitted modular fixture, public `pick_jobs` selects initial
    plan jobs in stable authored topology before predecessor acceptance; the scenario
    dispatches the shipped planner contract for at least two selected nodes and obtains
    a fresh public pick after each completion.'
  - 'AC-2: Given one complete reviewed packet DAG, public `start_job` and `finish_plan`
    produce one plan receipt, node-plan digest, build jobs, and dependency-gated accept
    job bound to the target and digest, and an identical retry returns persisted artifacts
    without duplication.'
  - 'AC-3: Given a second selected node whose plan references an authority target
    outside its admitted node, public `finish_plan` returns `ERR_FINISH_NODE_PLAN_INVALID`,
    publishes no plan, receipt, or downstream jobs for that node, and preserves the
    earlier completed node bytes.'
  - 'AC-4: The scenario derives target-only planning, reviewer gate, structured success
    fields, and the fresh-pick loop from shipped planner, workflow, and orchestration
    artifacts; replacing the public pick, start, or finish calls or the planner with
    a fixture adapter makes the scenario fail.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-006-PK-003`. Resolve normative behavior from `DN-006`, `IF-007`, `WF-002`, `NEG-008`, `RISK-007`, and `PROOF-005`; this record is not specification authority.

## Outcome
Maintain the initial-frontier half of `PROOF-005` over shipped planner artifacts and public native tools, including stable topology, independent per-node publication, replay, and authority-escape isolation.

## Envelope
In: one durable planner scenario over the real admitted modular fixture and public `pick_jobs`, `start_job`, and `finish_plan`; repository search results may be replaced below the planner.

Out: reconciliation/invalidation scenarios, engine semantic changes, setup/seed work, and alternate MCP adapters.

Proof guidance: exercise the shipped planner/orchestration boundary and public native tools; a fixture-only planner or direct store mutation does not prove this packet.

[[2026-07-25T15:35:21+02:00]]
## Builder Notes

### Change Envelope
Added one durable initial-frontier PROOF-005 interaction scenario over the real modular admitted change and public `admit_change`, `pick_jobs`, `start_job`, and `finish_plan`. Repaired the existing public `finish_plan` adapter to parse JSON `impact_closure` into the strict native model, matching the existing build/accept/audit adapter boundary. No native engine semantics, reconciliation/invalidation, setup/seed, or alternate adapter changes.

### Files Changed
- `serve/mcp-kanban/tests/test_planner_interaction.py`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

### Observed Local Defect
The exact shipped `PlannerSuccess` contract includes top-level `impact_closure`. `FinishPlanParams` accepts its JSON mapping, but `finish_plan` forwarded list-backed JSON directly into strict tuple-backed `FinishPlanRequest`, producing `ERR_PARAM_VALIDATION`. The adjacent `_finish_job` adapter already established `parse_impact_closure` as the public-to-native normalization. The repair applies that same existing contract to `finish_plan`.

### Proof Selected
The durable scenario copies the real admitted modular authority and declared research, admits it through the public boundary, derives stable dependency topology, validates actual planner/reviewer/workflow/orchestration artifacts for each selected node, and invokes only public MCP lifecycle tools. Byte snapshots distinguish plan publication/replay from second-node claim mutation and invalid-finish atomicity.

### Durable-Test Justification
PROOF-005 explicitly requires a durable planner scenario. It protects stable frontier topology, exact public planner payload transport, per-node atomic publication, idempotent replay, authority-escape rejection, and preservation of prior completed artifacts. These assembled risks were not covered by existing lower-level tests; the scenario exposed a real MCP adapter defect.

### Commands Run
- Focused scenario: 1 passed.
- Full `serve/mcp-kanban/tests`: 68 passed.
- Native runtime and dispatch regressions: 39 passed.
- Focused Ruff check and format check: pass.
- Pre-commit hooks for both changed files: pass.
- `git diff --check`: pass.
- VS Code diagnostics: none.

### AC-to-Evidence Map
- AC-1: Public admission and `pick_jobs` return all initial planner jobs in deterministic admitted dependency topology before predecessor acceptance. The scenario dispatches shipped planner contracts for two selected nodes and obtains a fresh public pick after first completion, preserving remaining topology.
- AC-2: Public start/finish produces one receipt with admitted digest, target, typed closure, and node-plan digest plus target/digest-bound build and dependency-gated accept jobs. Exact retry returns the persisted receipt/event, creates no duplicate jobs, and leaves the publication snapshot byte-identical.
- AC-3: The second selected node receives a dynamically escaped authority target. Public finish returns `ERR_FINISH_NODE_PLAN_INVALID` naming it, publishes no node plan/receipt/downstream IDs, mutates no publication bytes, and preserves all five first-node transaction artifacts byte-identically.
- AC-4: The planner dispatch helper reads the actual planner and reviewer frontmatter plus `w-frontier-planning` and `w-orchestration`, verifies the reviewer gate and structured handoff, and directly calls public pick/start/finish. Only repository search below planner is synthesized from the admitted graph.

### Challenger
`builder-challenger`: pass. It independently reviewed the two-file diff and reran all 68 MCP Kanban tests.

### Follow-up Risks
Acceptance-triggered reconciliation and invalidation remain independently owned by #2050.
