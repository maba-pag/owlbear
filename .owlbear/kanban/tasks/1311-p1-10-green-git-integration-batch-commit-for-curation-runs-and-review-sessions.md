---
id: 1311
title: 'P1-10: GREEN — Git integration (batch commit for curation runs and review
  sessions)'
status: review
priority: needed
created: 2026-05-04T01:32:27.341678+00:00
updated: 2026-05-06T05:05:10.505381+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
- merged
parent: 1301
depends_on:
- 1310
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] save_memory creates file on disk without git add or git commit
- [ ] Batch commit mechanism: groups mutations from a curation session into a single commit
- [ ] Batch commit mechanism: groups mutations from a review session into a single commit
- [ ] Hard-deleted pending files are never staged or committed (removed before commit)
- [ ] Soft-delete state changes included in batch commits
- [ ] Commit messages follow project format conventions
- [ ] All #1310 tests pass

## Scope

- In: git integration module, batch commit triggers, file staging logic
- Out: tool handlers (done in #1307/#1309), consumer wiring, agent files
[[2026-05-05]]


## Merged
This task has been merged into #1310. The builder implemented both tests and the git.py module under #1310 during its first cycle. The architect consolidated scope here during cycle 2 review (2026-05-05). No further work needed on this task — advance to done when triaged.

[[2026-05-06]]
## Research

Merged task — no independent research needed.

- #1310 (archived/done) implemented all git integration scope: batch commit with scoped staging, soft-delete handling, commit message conventions.
- Tests: `tests/test_memory_git_integration_1310.py` passes (verified in session).
- Implementation: `serve/mcp-memory/src/owlbear_mcp_memory/git.py`.
- Architect consolidated scope during cycle 2 review (2026-05-05).

No follow-up tasks needed — all AC delivered under #1310.
[[2026-05-06]]
## Architecture Review

**Verdict:** MERGE (already completed) — advance to done.

Task was merged into #1310 during cycle 2 (2026-05-05). All scope delivered under #1310 (now archived/done):
- Implementation: `serve/mcp-memory/src/owlbear_mcp_memory/git.py` — confirmed on disk.
- Tests: `tests/test_memory_git_integration_1310.py` — confirmed on disk.

No independent work remains. Closing as redundant merged task.
[[2026-05-06]]
## Test-Writer Notes
- Non-implementation task (tagged `merged`) — no tests applicable.
- All AC delivered under #1310 (archived/done): `serve/mcp-memory/src/owlbear_mcp_memory/git.py` + `tests/test_memory_git_integration_1310.py`.
- Architect verdict: MERGE (already completed) — advance to done.
- Passing through to builder.
[[2026-05-06]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Scope was merged into #1310 and already implemented there (`serve/mcp-memory/src/owlbear_mcp_memory/git.py`, `tests/test_memory_git_integration_1310.py`).
- Verification evidence in task body indicates #1310 tests already pass for this scope.
- Passing through to review.