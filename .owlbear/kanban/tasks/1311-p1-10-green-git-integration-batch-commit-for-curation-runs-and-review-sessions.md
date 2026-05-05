---
id: 1311
title: 'P1-10: GREEN — Git integration (batch commit for curation runs and review
  sessions)'
status: research
priority: needed
created: 2026-05-04T01:32:27.341678+00:00
updated: 2026-05-05T21:36:04.746460+00:00
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
