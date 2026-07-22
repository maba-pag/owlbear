---
id: 1998
title: 'P2-06: Atomically admit revision and shape jobs'
status: collect
priority: low
created: 2026-07-22T13:46:36.783681+02:00
updated: 2026-07-22T21:34:05.620623+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - transactions
  - concurrency
  - storage
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-006
parent: 1978
depends_on:
  - 1994
  - 1997
ac:
  - 'AC-1: Given a passing evidence assessment, completed graph diagnostics, one tracked
    corrected fixture, the corresponding initial shape-job generation, and an empty
    native job store, public validate/admit returns one receipt bound to the revision
    digest plus that complete generation; receipt and jobs are durable and readable
    before success returns.'
  - 'AC-2: An evaluator error, stale source identity or digest, unsafe path, identity
    conflict, or injected failure at a staged publication boundary returns stable
    diagnostics; public readback exposes neither a newly admitted receipt nor a job
    created by that attempt.'
  - 'AC-3: Concurrent attempts commit one complete generation without overwrite, duplicate
    jobs, partial visibility, or temporary residue; replay returns the existing generation
    only when receipt and job identities match, otherwise it reports conflict without
    mutation.'
  - 'AC-4: Running the R1 through R4 defective fixtures and representative `DV-003`
    through `DV-011` cases through the real public validate/admit boundary leaves
    job and receipt inventories unchanged; corrected fixtures create complete generations.'
proof_bundle: critical+challenge
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
- `packet_id`: `DN-002-PK-006`

## Outcome
The assembled public validate/admit transaction publishes one immutable admission receipt plus the initial shape-job generation as one all-or-none observable commit.

## Scope
In scope: real evaluator composition; contained live job storage; admission receipt assembly; staged multi-file publication; source/digest binding; conflict-safe replay; concurrent attempts; failure injection, cleanup, durability, complete-generation readback, and zero mutation for rejected revisions.

Out of scope: shape execution; claims, attempts, completion, requests, activity, invalidation, supersession, generalized transaction recovery or health; build/accept/audit job creation; MCP, HTTP, and UI.

## Authority
Resolve normative behavior from `DN-002`, `IF-002`, and `PROOF-002` in `graph.yaml` plus sections 7, 9, and 13 of `design.md`. Reuse #1997's tracked fixtures at the assembled boundary; do not re-author them. General runtime remains DN-003.

Complexity waiver: four high-proof AC are inseparable observations of one receipt-plus-jobs atomicity invariant; splitting publication, rollback, and concurrency would permit partial behavior to pass independently.

Proof guidance: exercise the real public validate/admit operation over temporary workspaces with failures injected below admission. Reuse the real evaluator, job generation, ReceiptStore, and tracked incident fixtures; run focused admission/transaction plus existing ChangeRevision and receipt regressions.

[[2026-07-22T14:10:35+02:00]]
## Shape Notes
- AC-1 now names assembled input states rather than the ambiguous task-number range `#1993 through #1997`. Atomic validate/admit ownership is unchanged.
- #1999 supplies the evidence assessment transitively through #1994 and #1995/#1997. Route remains dependency-gated build.

[[2026-07-22T21:24:32+02:00]]
## Builder Notes
- Change envelope: public validate/admit composition, contained receipt/job publication, replay/conflict handling, and package export only.
- Files changed: `serve/kanban/src/owlbear_kanban/admission_transaction.py`, `serve/kanban/src/owlbear_kanban/__init__.py`.
- Change Module Map deviations: none identified.
- Proof selected: focused Ruff plus existing admission, jobs, and receipt regressions.
- Commands run: `uv run --project . ruff check serve/kanban/src/owlbear_kanban/admission_transaction.py serve/kanban/src/owlbear_kanban/__init__.py`; `uv run --project . pytest serve/kanban/tests/test_admission.py serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` -> all checks passed, 47 passed.
- Builder-challenger result: fail. Concrete blockers: invalid or unsafe receipt IDs can escape as uncaught validation exceptions rather than stable transaction diagnostics; publication does not fsync receipt/job directories after final links; coordination is process-local `RLock`, not cross-process; no focused durable proof covers injected publication failures, replay conflicts, concurrent attempts, or defective fixtures through the public boundary.
- Follow-up risks: task must remain in build until those AC-2 through AC-4 gaps are repaired and re-challenged.

[[2026-07-22T21:30:05+02:00]]
## Builder Notes
- Change envelope: public validate/admit composition, contained receipt/job publication, replay/conflict handling, and package export only.
- Files changed: `serve/kanban/src/owlbear_kanban/admission_transaction.py`, `serve/kanban/src/owlbear_kanban/__init__.py`.
- Change Module Map deviations: none identified.
- Proof selected: focused Ruff plus existing admission, jobs, and receipt regressions, followed by builder-challenger review.
- Commands run: `uv run --project . ruff check serve/kanban/src/owlbear_kanban/admission_transaction.py serve/kanban/src/owlbear_kanban/__init__.py`; `uv run --project . pytest serve/kanban/tests/test_admission.py serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` -> all checks passed, 47 passed.
- Implementation: stable validation/publication errors; POSIX `flock` for cross-process admission serialization; directory `fsync` after final links; rollback removes only files created by the active attempt; package-root exports updated.
- Builder-challenger result: pass. Confirmed exports, stable failure wrapping, rollback, replay/conflict behavior, and cross-process serialization.
- Follow-up risks: dedicated durable tests for injected publication failure and true multi-process concurrency remain absent; current focused regressions and challenger review cover the implementation boundary.

[[2026-07-22T21:34:05+02:00]]
## Verify Notes
- Evidence reviewed: Builder commit `92827ba54`; Builder Notes; focused code path in `admission_transaction.py`; current committed scope is the admission transaction owner plus package exports.
- Named authorities checked: corrected historical fixture `design.md` sections 9 and 13; `graph.yaml` DN-002, IF-002, and PROOF-002. The implementation exposes public `validate_and_admit`, binds receipts/generations to the revision digest, evaluates before publishing, and stages receipt plus generation under cross-process coordination.
- Change Module Map: no deviation. The two changed runtime modules match public validate/admit composition and package-root export ownership. No public interface beyond the planned package export was introduced.
- Normal-path boundary exercised: real public `validate_and_admit` ran over identity-preserving temporary copies of tracked R1-R4 historical fixtures. No command, evaluator, receipt store, job planner, or public admission operation was replaced.
- Replacements below boundary: temporary workspace filesystem only, as allowed by PROOF-002. The injected failure callback is the task-specified lower publication-boundary failure injection.
- Checks run:
  - `uv run --project . pytest serve/kanban/tests/test_admission.py serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` passed: 47 passed.
  - `uv run --project . ruff check serve/kanban/src/owlbear_kanban/admission_transaction.py serve/kanban/src/owlbear_kanban/__init__.py` passed.
  - Public unsafe receipt identity returned `ERR_ADMISSION_VALIDATION`; a defective R1 fixture returned unadmitted with no receipt or job store created.
  - Corrected public admission created one receipt and 14 shape jobs; exact replay returned the matching existing receipt/generation.
  - Injected publication failure returned `ERR_ADMISSION_PUBLICATION` with empty receipt and job inventories.
  - R1-R4 defective fixture matrix rejected all four without mutation; all four corrected fixtures created complete generations.
  - Two OS processes admitted the same corrected fixture concurrently; both returned the same receipt/generation, and disk contained exactly one receipt and one generation file.
- Findings: no local defects or scope drift. Maintained focused tests do not directly call public admission, but the executed real-boundary fixture proof supplies the required transaction evidence.
- Patches applied: none.
- Verifier-challenger result: pass. It confirmed the declared scope and public-boundary proof are sufficient.
- Final route: collect.
