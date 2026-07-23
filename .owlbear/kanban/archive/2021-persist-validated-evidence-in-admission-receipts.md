---
id: 2021
title: Persist validated evidence in admission receipts
status: archived
priority: high
created: 2026-07-23T17:45:08.767424+02:00
updated: 2026-07-23T18:35:27.398952+02:00
tags:
  - phase-2
  - scope:core
  - runtime
  - admission
  - receipts
  - evidence
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
parent: 1968
depends_on:
  - 1978
ac:
  - 'AC-1: Given admitted `AdmissionEvidence`, `validate_and_admit` atomically persists
    one admission receipt whose payload contains the evidence `challenge`, `baseline`,
    `approval`, and `limits` unchanged alongside the assessment and generated shape
    jobs.'
  - 'AC-2: Given replay with the same receipt ID, revision, evidence, and generated
    jobs, `validate_and_admit` returns the existing receipt and generation; different
    evidence for that receipt ID returns `ERR_ADMISSION_CONFLICT` without mutation.'
  - 'AC-3: Given interruption after one admission participant publishes, runtime reopen
    recovers the receipt and job generation pair, and the recovered receipt retains
    the validated evidence payload.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
`validate_and_admit` publishes the exact validated challenge, baseline, approval, and limits with the admission assessment and generated shape jobs so an immutable admission receipt proves why one digest was admitted.

## Scope
In scope: `AdmissionEvidence` serialization in the admission receipt payload; exact replay identity; conflict when a receipt ID already names different evidence; focused transaction/recovery proof.

Out of scope: admission evaluation policy, graph validation, task projection, DN-003 receipt currentness, hand-authored replacement receipts, and publication or re-admission of the live `replace-delivery-pipeline` revision.

## Current Foundation And Ownership
`AdmissionTransaction.validate_and_admit` currently validates `AdmissionEvidence` but persists only `assessment` and `generation`. Design sections 9.4 and 9.5 require user approval, repository challenge, baseline, and limits in the immutable receipt. Deepen the existing DN-002 transaction owner; do not create a second admission path. The payload may nest the validated evidence or expose its fields, but exact replay identity must include it; `assessment.limits` alone does not preserve challenge, baseline, or approval.

## Authority
Resolve behavior from `REQ-002`, `IF-002`, `PROOF-002`, design sections 9.4 and 9.5, and the public `AdmissionEvidence` schema in `admission.py`.

## Proof Guidance
Exercise public `validate_and_admit` in a temporary change root with non-empty challenge, baseline, approval, and limits. Assert persisted evidence equality, exact replay, different-evidence conflict, and interrupted receipt/job publication recovery. Actual whole-change re-proof and re-admission remain DN-013/DN-014 work.

[[2026-07-23T18:26:34+02:00]]
## Builder Notes

Change envelope: deepen `AdmissionTransaction.validate_and_admit` so an admitted receipt stores the validated `AdmissionEvidence`, making receipt equality and replay identity cover `challenge`, `baseline`, `approval`, and `limits`; prove persisted evidence, valid changed-evidence conflict without mutation, and interrupted-publication recovery. No admission evaluation-policy or live-change revisions were changed.

Files changed: `serve/kanban/src/owlbear_kanban/admission_transaction.py`; `serve/kanban/tests/test_admission_transaction.py`.

Change Module Map deviations: none. The existing test fixture temporarily constructs required graph admission metadata because the copied draft change has no admission metadata; this is fixture-local and necessary to drive the existing public API through its admitted publication path.

Proof selected: durable transaction coverage passes the Rent Test because immutable receipt identity and recovery are shared, data-integrity boundaries that are difficult to verify manually. No new test module or helper was added.

Commands run:
- `uv run pytest serve/kanban/tests/test_admission_transaction.py -q` -> 3 passed in 1.05s.
- `uv run ruff check serve/kanban/src/owlbear_kanban/admission_transaction.py serve/kanban/tests/test_admission_transaction.py && uv run ruff format --check serve/kanban/src/owlbear_kanban/admission_transaction.py serve/kanban/tests/test_admission_transaction.py` -> passed; 2 files already formatted.
- VS Code diagnostics for both changed files -> no errors.

Builder-challenger: pass. It independently reran the focused tests (3 passed in 1.03s) and scoped Ruff checks; no concrete blockers.

Follow-up risks: the live `.owlbear/changes/replace-delivery-pipeline` graph remains draft/unadmitted and fails evaluation with `DV-010`; this task deliberately uses in-memory fixture metadata and does not publish or re-admit that live revision.

[[2026-07-23T18:33:56+02:00]]
## Verify Notes
- Evidence reviewed: builder commit `5adf8f460874c92c5b5515d56d854546a7dc9e95`; AC-1 through AC-3; Builder Notes and scoped implementation/test diff.
- Named authorities checked: `.owlbear/changes/replace-delivery-pipeline/graph.yaml` `REQ-002`, `IF-002`, and `PROOF-002`; design sections 9.4 and 9.5. They require a public validate/admit boundary that atomically emits an immutable receipt tied to one delivery digest and retains repository challenge, clean baseline, user approval, and explicit limits.
- Change Module Map: no deviation. Receipt assembly remains in the existing `AdmissionTransaction.validate_and_admit` owner; focused proof remains in its dedicated transaction test module.
- Normal-path boundary exercised: public `validate_and_admit` with a temporary copied real change and non-empty `challenge`, `baseline`, `approval`, and `limits`. The receipt stores serialized evidence alongside assessment and generation; exact replay returns the existing receipt/generation; changed evidence raises `ERR_ADMISSION_CONFLICT`; recovery after interruption retains the stored evidence when `load_change` reopens the runtime.
- Replacements used below that boundary: temporary filesystem change root and fixture-local immutable graph metadata only; no admission command, receipt transaction, or recovery behavior was replaced.
- Checks run: `uv run pytest serve/kanban/tests/test_admission_transaction.py -q` passed, 3 tests in 1.09s. `uv run ruff check serve/kanban/src/owlbear_kanban/admission_transaction.py serve/kanban/tests/test_admission_transaction.py` passed. `uv run ruff format --check serve/kanban/src/owlbear_kanban/admission_transaction.py serve/kanban/tests/test_admission_transaction.py` passed, 2 files already formatted.
- Findings: none.
- Patches applied: none.
- Prior same-AC rejection check: no earlier Verify Notes or resolved requests for task 2021.
- Verifier-challenger result: pass; it found AC-1 through AC-3 covered with no unresolved scope drift.
- Final route: PASS to collect.

[[2026-07-23T18:35:27+02:00]]
## Collect Notes
- Classification: leaf. No child tasks were returned by `list_tasks(parent=2021)`; the task has no aggregate title, tag, or aggregate intent.
- Latest verification evidence: newest `## Verify Notes` records PASS to collect for AC-1 through AC-3, with focused public-boundary proof: `uv run pytest serve/kanban/tests/test_admission_transaction.py -q` (3 passed), Ruff check, and Ruff format check.
- Intent and invariant coverage: task Outcome/Scope require immutable receipt persistence and replay/recovery identity for `challenge`, `baseline`, `approval`, and `limits`; the verifier records persisted evidence, exact replay, different-evidence conflict without mutation, and interruption recovery.
- Parent/dependency gate: not applicable to leaf collection. The declared dependency `#1978` has already allowed this task to reach collect (`dep_status: null`).
- Structured requests: `list_requests` found no pending or resolved requests for #2021.
- Residual decisions: none. The live-change limitation is explicitly out of scope and delegated to DN-013/DN-014, not an unresolved follow-up for this task.
- Archive rationale: latest verifier PASS is complete and no later request or follow-up blocks closure.
