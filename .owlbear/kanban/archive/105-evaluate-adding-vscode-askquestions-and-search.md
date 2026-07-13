---
id: 105
title: Evaluate adding vscode/askQuestions and search/changes tools to agent 
  toolkits
status: archived
priority: medium
created: 2026-03-28 14:33:43.062943+01:00
updated: 2026-03-29 04:07:09.580660+02:00
started: 2026-03-29 04:07:09.580660+02:00
completed: 2026-03-29 04:07:09.580660+02:00
tags:
- phase-1
- scope:agents
- research
class: standard
archival_reason: completed
archival_refs: []
---

[[2026-03-29]] Sun 00:44
## Research
Duplicate of #95. See docs/research/vs-code-new-tools-evaluation.md. Recommend closing this task.

[[2026-03-29]] Sun 03:49
## Research (Duplicate Verification)
Verified duplicate of #95. Scope comparison:
- #95 covers: search/usages, search/changes, vscode/askQuestions
- #105 covers: vscode/askQuestions, search/changes
- #105 is a strict subset of #95

Research doc: docs/research/vs-code-new-tools-evaluation.md (owned by #95)
Follow-up tasks already created and in-flight:
- #101 Grant vscode/askQuestions (in-progress)
- #102 Add search/changes to reviewer+auditor skills (archived)
- #103 Add search/usages guidance (backlog)

No additional research needed. Closing as duplicate.

[[2026-03-29]] Sun 04:06
## Architecture Review
**Verdict:** Merge (delete as duplicate)

### Duplicate Analysis
- #105 scope: vscode/askQuestions + search/changes
- #95 scope: search/usages + search/changes + vscode/askQuestions (superset)
- #105 is a strict subset of #95

### Follow-up tasks (from #95 research) already in pipeline:
- #101 Grant vscode/askQuestions (in-progress)
- #102 Add search/changes to skills (archived)
- #103 Add search/usages guidance (todo, architect-approved)

Zero unique scope remains. Deleting as redundant.
