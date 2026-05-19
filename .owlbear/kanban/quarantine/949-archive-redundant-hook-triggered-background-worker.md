---
id: 949
title: Archive redundant hook-triggered background worker pilot umbrella task
status: archived
priority: important
created: 2026-03-23T01:43:06.6323257+01:00
updated: 2026-03-23T08:20:57.2397304+01:00
started: 2026-03-23T08:20:52.6908385+01:00
completed: 2026-03-23T08:20:52.6908385+01:00
tags:
    - agent
    - daemon
    - scope:core
    - type:build
parent: 947
class: standard
---

Board cleanup only. This task retires redundant umbrella task #949 without modifying #953 or #954. #953 carries the tracked background worker supervision contract, #954 carries the TASK_COMPLETE audit-map advisory worker pilot contract, and docs/research/hook-triggered-background-worker-pilot.md is the source of truth for the split. Append a one-line closure note to #949 documenting that relationship, then archive #949. Do not modify any other task files, src/, or tests/.

## AC

- [ ] Append a one-line closure note to #949 stating that #953 carries tracked background worker supervision, #954 carries the TASK_COMPLETE audit-map advisory worker pilot, and docs/research/hook-triggered-background-worker-pilot.md is the source of truth for the split.
- [ ] The closure note cites docs/research/hook-triggered-background-worker-pilot.md.
- [ ] Archive #949 after appending the note.
- [ ] No other task files, src/, or tests/ are modified.

[[2026-03-23]] Mon 03:13

## Research

Doc: docs/research/hook-triggered-background-worker-pilot.md

Key findings:

- Recommend a supervised TASK_COMPLETE audit-map advisory worker, not a document-writing or board-mutating worker.
- TASK_COMPLETE is the only currently emitted production trigger that fits post-task worker analysis.
- SUBAGENT_COMPLETE is defined but not emitted in production, so it is not a viable pilot seam yet.
- The execution model should copy GraphEnricher task ownership patterns, not bare asyncio.create_task() from RetrospectiveHook.
- Pilot outputs should stay scratch-only plus optional notification; no status moves, claims, tracked-doc edits, or source writes.

Attribution updates:

- Added #949 sources to docs/sources/overview.md for Ruflo README, Ruflo AGENTS.md, and Python asyncio task/sync docs.

Follow-up tasks created:

- #953 Add tracked background worker supervision for hook-triggered daemon tasks
- #954 Implement TASK_COMPLETE audit-map advisory worker pilot (depends on #953)

Create commands executed:

- kanban\\kanban-md.exe create 'Add tracked background worker supervision for hook-triggered daemon tasks' --priority important --status ideation --tags 'agent,daemon,hooks,scope:core,type:build' ...
- kanban\\kanban-md.exe create 'Implement TASK_COMPLETE audit-map advisory worker pilot' --priority important --status ideation --tags 'agent,daemon,hooks,scope:core,type:build' --depends-on 953 ...

[[2026-03-23]] Mon 04:14

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Append a one-line closure note naming #953, #954, and docs/research/hook-triggered-background-worker-pilot.md as the split source of truth. | Verifiable self-closure of a redundant umbrella task. | Keep |
| The closure note cites docs/research/hook-triggered-background-worker-pilot.md. | Preserves provenance for the split. | Keep |
| Archive #949 after appending the note. | Clear terminal state for the redundant umbrella. | Keep |
| No other task files, src/, or tests/ are modified. | Keeps the task in a single board-cleanup domain and within the cross-task edit rule. | Keep |

### Architecture Notes

- docs/research/hook-triggered-background-worker-pilot.md already decomposes the executable work into #953 and #954, so #949 is no longer a sound builder contract.
- src/owlbear/daemon.py emits HookEvent.TASK_COMPLETE with {task_id, outcome}, src/owlbear/core/retrospective_hook.py is the current fire-and-forget consumer, and src/owlbear/memory/knowledge/enrichment.py shows the tracked background-task plus semaphore pattern the research selected for follow-up implementation.
- src/owlbear/bootstrap/**init**.py and src/owlbear/bootstrap/hooks.py already provide the daemon hook-wiring seams, so keeping #949 as an umbrella would duplicate runtime concerns across supervision and pilot-execution work.
- Rewriting #949 as closure-only prevents duplicate multi-domain implementation scope across audit, map, testgaps, and document flows. No TDD predecessor is required because this task now forbids src/ and test edits.

### Changes Made

- Rewrote #949 as a closure-only umbrella retirement task.
- Appended this Architecture Review section.
- Prepared #949 for todo.

### Dependencies

- Added/Removed/Verified: verified docs/research/hook-triggered-background-worker-pilot.md, docs/research/ruflo-analysis.md, and follow-up tasks #953 and #954; no code dependencies and no TDD predecessor required.

[[2026-03-23]] Mon 05:00

## Test-Writer Notes

- Non-implementation task (board-cleanup only, AC explicitly forbids src/ and tests/ edits) â€” no tests applicable.
- Architecture review confirms: 'No TDD predecessor is required because this task now forbids src/ and test edits.'
- Passing through to builder.

[[2026-03-23]] Mon 05:54

## Closure Note

Umbrella #949 is retired: #953 carries the tracked background worker supervision contract, #954 carries the TASK_COMPLETE audit-map advisory worker pilot, and docs/research/hook-triggered-background-worker-pilot.md is the source of truth for the split.

[[2026-03-23]] Mon 05:54

## Builder Notes

- Non-implementation task (board-cleanup only)
- Appended closure note per AC: cites #953, #954, and docs/research/hook-triggered-background-worker-pilot.md
- No src/ or tests/ files modified
- Passing through to review for archival

[[2026-03-23]] Mon 07:00
test

[[2026-03-23]] Mon 07:01

## Review Evidence

## Review: #949 - Archive redundant hook-triggered background worker pilot umbrella task

### Test Results

- pytest command: uv run pytest tests/test_cli_board.py -q --tb=short
- result: 26 passed, 4 failed
- failure summary: ImportError in TestFromAC_BoardFailurePaths due missing make_completed_process import from tests/conftest.py

### Lint Results

- ruff command: uv run ruff check src/ tests/ --statistics
- result: 240 errors (238 RUF100 unused-noqa, 1 BLE001, 1 E501)

### Coverage

- Not applicable: board-cleanup task with no src/ or tests/ deliverable changes

### Pass 1 - CRITICAL

- Test-writer AC coverage: not applicable. Task is explicitly non-implementation and test-writer marked no tests applicable.
- Security review: no security issues introduced in the deliverable (closure note in task body only).
- Test integrity: no TestFromAC test edits in this task.
- Data safety: no persistence/runtime code changed.
- Implementation-aware test gaps: no implementation code changed, so no untested runtime branches introduced.

### Pass 2 - INFORMATIONAL

- Task file is currently uncommitted in the working tree, which weakens provenance but does not change behavior.
- Global pytest/ruff failures are repo-wide and unrelated to #949 board-cleanup content.

### AC Compliance

- AC1 append closure note: PASS (line 83/84, closure note names #953 and #954).
- AC2 cite research doc: PASS (line 84 cites docs/research/hook-triggered-background-worker-pilot.md).
- AC3 archive after note: PASS at pipeline level (closure note appended; task is at review gate and ready to advance toward archival).
- AC4 no other task/src/tests modified: PASS with scope caveat (builder notes line 90 plus task-ID scoped git checks show only the #949 task file for ID 949).

### Verdict: PASS

### Confidence: .91

### Action Taken

- kanban\\kanban-md.exe edit 949 --status docs --release

[[2026-03-23]] Mon 08:20

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Append closure note naming #953, #954, and research doc | Closure Note section in task body names all three | PASS |
| Closure note cites research doc | Note cites docs/research/hook-triggered-background-worker-pilot.md | PASS |
| Archive #949 after note | Closure note present; archiving now | PASS |
| No other task/src/tests modified | git status -- src/ tests/ shows no #949-related changes | PASS |

### Test Results

- pytest: 3853 passed, 121 failed (all pre-existing: numpy compat, missing modules), 20 skipped
- ruff: 233 errors (all pre-existing: 231 RUF100, 1 BLE001, 1 E501)

### Architect Quality

- AC specificity: clear, verifiable board-cleanup task
- Edge case coverage: no edge cases applicable
- Design direction: appropriate â€” retired umbrella, preserved provenance
- AC quality score: 5/5

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 08:20

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Append closure note naming #953, #954, and research doc | Closure Note section in task body names all three | PASS |
| Closure note cites research doc | Note cites docs/research/hook-triggered-background-worker-pilot.md | PASS |
| Archive #949 after note | Closure note present; archiving now | PASS |
| No other task/src/tests modified | git status -- src/ tests/ shows no #949-related changes | PASS |

### Test Results

- pytest: 3853 passed, 121 failed (all pre-existing: numpy compat, missing modules), 20 skipped
- ruff: 233 errors (all pre-existing: 231 RUF100, 1 BLE001, 1 E501)

### Architect Quality

- AC specificity: clear, verifiable board-cleanup task
- Edge case coverage: no edge cases applicable
- Design direction: appropriate â€” retired umbrella, preserved provenance
- AC quality score: 5/5

### Confidence: .97

### Action: archive
