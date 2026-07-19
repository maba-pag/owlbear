---
id: 1963
title: Make archived task-test discovery provenance-aware
status: archived
priority: high
created: 2026-07-20T00:33:28.450577+02:00
updated: 2026-07-20T01:03:23.230463+02:00
tags:
  - scope:test-curation
  - agent-ecosystem
  - test-policy
parent:
depends_on: []
ac:
  - 'AC1: `w-test-curation` requires future transient Python suites to include the
    numeric task ID in the filename and explains the durable behavior-name exception,
    verified by artifact inspection.'
  - 'AC2: Legacy discovery checks explicit file-level task provenance such as a module
    docstring naming `#<task_id>`, then confirms that task is archived before triage;
    `TestFromAC_*` class names alone are explicitly insufficient.'
  - "AC3: The workflow's discovery procedure identifies `tests/test_engine_ac.py`
    as a candidate for archived task 1517 without implying deletion, verified by a
    focused static test or deterministic inspection."
  - 'AC4: Ecosystem validators and focused workflow tests pass.'
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Ensure test curation can find archived transient suites even when legacy filenames omit task IDs, without classifying durable `TestFromAC_*` coverage as disposable.

## Scope
- `share/skills/w-test-curation/SKILL.md`
- focused static workflow tests if an existing owning suite exists

## Boundaries
Do not delete or mine product tests in this task. Do not treat `TestFromAC_*` names alone as transient provenance. Future naming and legacy file-level markers must remain distinct signals.



## Implementation Notes

Completed directly without pipeline dispatch. Future transient Python suites now require task IDs in filenames. Legacy discovery accepts only explicit module-header task provenance, verifies archived status, and treats `TestFromAC_*` names alone as insufficient. The procedure explicitly identifies `tests/test_engine_ac.py` through archived task 1517 without deciding deletion.

Evidence: skill validator passed; deterministic marker/archive checks passed; no product tests were deleted or reclassified.
