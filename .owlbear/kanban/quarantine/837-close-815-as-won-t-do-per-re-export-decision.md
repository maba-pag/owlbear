---
id: 837
title: 'Close #815 as won''t-do per re-export decision'
status: archived
priority: nice-to-have
created: 2026-03-16T05:14:48.5919036+01:00
updated: 2026-03-21T04:07:44.7699769+01:00
started: 2026-03-21T04:07:44.7699769+01:00
completed: 2026-03-21T04:07:44.7699769+01:00
tags:
    - audit
    - scope:core
claimed_by: builder
claimed_at: 2026-03-21T04:07:24.1400127+01:00
class: standard
---

Task #815 (add re-exports to tools/browser/__init__.py) is already archived as won't-do per docs/decisions/resolved/813-re-export-feature-gate.md (Option A). This task is board cleanup only: append a one-line closure note to #837 pointing back to #549 and the resolved decision, then archive #837 as a stale closure meta-task. Do not modify src/ or tests/. See docs/research/re-export-closure-meta-tasks.md.

## AC

- [ ] Append a one-line closure note to #837 stating that #815 is already archived and #549 is the source of truth for the re-export workstream
- [ ] The closure note cites docs/decisions/resolved/813-re-export-feature-gate.md
- [ ] Archive #837 after appending the note
- [ ] No src/ or tests/ files are modified

[[2026-03-20]] Fri 13:47

## Research

Doc: docs/research/re-export-closure-meta-tasks.md

Summary: #815 is already archived; #549 already records the final state; #823 shows the same stale closure-task pattern; current repo search still finds 0 package-level browser imports and 217 deep browser import statements. Recommendation (.92): clean up stale closure meta-tasks instead of doing more work on #815.

Follow-up: created #865. Exact create command is recorded in docs/research/re-export-closure-meta-tasks.md. Attribution updated: docs/sources/overview.md.

## Architecture Review

__Verdict:__ APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Append a one-line closure note to #837 stating that #815 is already archived and #549 is the source of truth for the re-export workstream | Verifiable board-only action that removes stale duplicate intent without reopening #815 | Keep |
| The closure note cites docs/decisions/resolved/813-re-export-feature-gate.md | Verifiable provenance requirement that preserves the approved decision trail | Keep |
| Archive #837 after appending the note | Clear terminal state for this stale meta-task | Keep |
| No src/ or tests/ files are modified | Keeps scope in a single board-cleanup domain | Keep |

### Architecture Notes

Current repo evidence still matches the decision: src/owlbear/tools/browser/__init__.py remains a docstring-only stub, and repo search found no package-level browser imports while deep browser imports remain common across src/ and tests. #815 is already archived and #549 already records the final re-export state, so the original task text was redundant rather than actionable.

Reframing #837 as an atomic self-closure task keeps the work precise and verifiable without modifying other tasks. No TDD predecessor is required because this is a closure/verification task with no application code or test changes.

### Changes Made

- Rewrote the task body as a board-cleanup closure task with explicit AC
- kanban\kanban-md.exe edit 837 --body ... --claim fork-moss
- kanban\kanban-md.exe edit 837 --status todo --release

### Dependencies

- Added/Removed/Verified: verified #815 archived, #549 archived, docs/decisions/resolved/813-re-export-feature-gate.md approved; no code dependencies and no TDD task required

[[2026-03-20]] Fri 15:16

## Test-Writer Notes\nNon-implementation task (board-cleanup only, no src/ or tests/ changes per AC and Architecture Review). No tests applicable. Passing through to builder

[[2026-03-21]] Sat 04:07

## Closure Note

Task #815 is already archived as won't-do; #549 is the source of truth for the re-export workstream. See docs/decisions/resolved/813-re-export-feature-gate.md (Option A). No src/ or tests/ files were modified.
