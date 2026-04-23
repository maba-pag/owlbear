---
id: 1108
title: Mode-6 rename collision guard in attempt_repair
status: backlog
priority: important
created: 2026-04-22T23:36:37.892632+00:00
updated: 2026-04-23T00:10:58.193621+00:00
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

[[2026-04-23]]
## Research
- Research doc: .owlbear/research/1108-mode6-rename-collision-guard.md
- Sources: 6 studied (all codebase-internal), 4 high-relevance
- Recommendation: Add `new_path.exists()` guard before `path.replace(new_path)` in mode-6 repair; quarantine on collision (confidence: 0.90)
- Follow-up tasks created: #1109 (Add exists-guard to mode-6 rename in attempt_repair)
- Decision requests: none (T1 — autonomous bug fix)

## Challenge Results
- Challenger: SKIPPED — trivial single-option bug fix with no design trade-off ambiguity