---
id: 1310
title: 'P1-09: RED — Git integration tests (save uncommitted, curation batch commit,
  review batch commit)'
status: research
priority: needed
created: 2026-05-04T01:32:27.314281+00:00
updated: 2026-05-04T01:34:54.292585+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1307
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] Tests assert save_memory does NOT create a git commit (file exists uncommitted)\n- [ ] Tests assert curation batch: multiple curate/delete operations produce single batch commit\n- [ ] Tests assert review batch: multiple approve/curate/delete operations produce single batch commit\n- [ ] Tests assert hard-deleted (pending) files never appear in git history\n- [ ] Tests assert soft-deleted entries are included in batch commit\n- [ ] Tests assert batch commit message follows project commit format\n- [ ] All tests fail (RED state)\n\n## Scope\n\n- In: git commit behavior per operation type, batch semantics\n- Out: tool handler logic (done in #1307/#1309), consumer wiring