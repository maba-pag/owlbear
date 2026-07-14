---
id: 1933
title: Close durable-test admission loophole
status: collect
priority: high
created: 2026-07-14T04:21:57.038752+02:00
updated: 2026-07-14T04:32:05.083537+02:00
tags:
  - agent
  - test
  - type:docs
parent:
depends_on: []
ac:
  - Builder requires every new durable test to pass the Rent Test
  - Low-value prescribed tests route back to shape
  - Task-1932 source-string assertions are removed without replacement
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Make the Rent Test mandatory even when a task prescribes a durable test, and remove the low-value source-string assertions added by task 1932.

## Acceptance Criteria
- Builder guidance does not treat task-prescribed test artifacts as an independent admission path.
- Builder and builder-challenger reject prescribed durable tests that fail the Rent Test and route the task back to shape.
- The three task-1932 source-string assertions are removed without replacement.

Proof guidance: no new durable test expected; inspect the authority diff and run the existing focused authority test and agent validator.

[[2026-07-14T04:23:55+02:00]]
## Builder Notes

- Investigation: the canonical Rent Test in `r-pipeline-protocol` already required a concrete uncovered risk; `w-task-decomposition` rejected test-prescriptive proof; Python/frontend conventions rejected source-shape assertions; builder-challenger required Rent justification.
- Root cause: `builder.agent.md` contradicted those authorities by allowing an explicit task requirement as an independent durable-test admission path. Task 1932 also bypassed normal shaping and prescribed assertions.
- Changed `r-pipeline-protocol` so task or AC prescription never waives durable-test admission and low-value prescriptions return to shape.
- Changed builder guidance to require every durable test to protect a concrete uncovered regression and pass the Rent Test.
- Removed the three source-string assertions added by task 1932 without replacement.
- No extra automated policy enforcement added: test value is semantic and already checked at shape, build, and builder challenge; another source-string test would repeat the defect.
- Proof: existing focused authority test 4 passed; Ruff clean; all 23 agent definitions valid; diff check clean.
- Builder challenger: pass; Rule of Two and minimum-change contract satisfied.

[[2026-07-14T04:32:05+02:00]]
## Verify Notes

- Verified builder commit `4e56c2f96` against all three AC.
- Canonical protocol now makes Rent Test admission non-waivable; builder carries one role-level summary; builder-challenger already checks concrete uncovered risk and justification.
- Normal shaping already rejects test-prescriptive proof, so failed admission now routes cleanly back to shape.
- Confirmed test delta only removes three source-string assertions and their unused file read; no replacement test was added.
- Checks: 4 focused tests passed; Ruff clean; all 23 agent definitions valid.
- Additional automated enforcement not recommended: test value is semantic, and a source-string policy test would recreate the removed low-value mechanism.
- Verifier challenger: pass; Rule of Two and proof scope are coherent.
