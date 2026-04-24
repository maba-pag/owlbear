---
id: 1120
title: 'B-XX: Archived-task metadata edit persistence path'
status: backlog
priority: important
created: 2026-04-24T23:12:27.011812+00:00
updated: 2026-04-24T23:22:13.530274+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-24]]
Placeholder — created by architect during #1070 review. Needs edit_task to populate body, tags, deps, status.
[[2026-04-24]]
## Research
- Research doc: .owlbear/research/archived-edit-persistence.md
- Sources: 7 studied, 5 high-relevance (all internal codebase and brief authority)
- Recommendation: Option A -- _find_task_path archive fallback + write_task target_dir param (confidence: 0.85)
- Follow-up tasks created: #1121 (RED tests), #1122 (GREEN fix) at research
- Decision requests: none (T1 autonomous -- persistence bug fix, no arch change)

## Challenge Results
- Challenger: FALLBACK -- trivial persistence bug fix, no architecture alternatives to challenge

## Key Findings
Two independent defects block archived-task edit persistence:
1. Core edit_task calls _find_task_path(task_id, self._tasks_dir) which only searches tasks/, not archive/
2. write_task in storage.py always writes to tasks/, never archive/
Both MCP server and Cockpit consumers are affected. Validation paths work correctly (26 tests GREEN), only the success path is broken. D7 vs R5 scope tension resolved in favor of R5 (full edit access on archived tasks subject to S4).