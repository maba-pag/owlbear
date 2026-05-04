---
id: 1311
title: 'P1-10: GREEN — Git integration (batch commit for curation runs and review
  sessions)'
status: research
priority: needed
created: 2026-05-04T01:32:27.341678+00:00
updated: 2026-05-04T01:34:54.299860+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1310
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] save_memory creates file on disk without git add or git commit\n- [ ] Batch commit mechanism: groups mutations from a curation session into a single commit\n- [ ] Batch commit mechanism: groups mutations from a review session into a single commit\n- [ ] Hard-deleted pending files are never staged or committed (removed before commit)\n- [ ] Soft-delete state changes included in batch commits\n- [ ] Commit messages follow project format conventions\n- [ ] All #1310 tests pass\n\n## Scope\n\n- In: git integration module, batch commit triggers, file staging logic\n- Out: tool handlers (done in #1307/#1309), consumer wiring, agent files