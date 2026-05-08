---
id: 1414
title: 'E1: legacy-audit.prompt.md — cleanup scan prompt for stale references'
status: research
priority: important
created: 2026-05-07T23:16:25.305798+00:00
updated: 2026-05-07T23:18:03.164466+00:00
tags:
- pipeline
- ws-cleanup
- scope:agents
parent: 1403
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `share/prompts/legacy-audit.prompt.md` created as user-triggered one-shot prompt
P2: Prompt scans for: TODO(#nnnn) where task is archived/done, dead imports and zero-caller functions, mock objects referencing obsolete patterns, test files `test_*_{task_id}.py` where task is archived but test remains, functions/modules with "legacy"/"compat"/"bridge"/"shim" in names
P2: Output is a ranked cleanup report grouped by type
P2: Prompt is not auto-fixable — produces report only, user decides cleanup actions
P3: Verification by artifact inspection of the created prompt file

## Scope

**In scope:** Prompt file creation with scan categories and output format
**Out of scope:** Automated cleanup, pipeline integration, stale test deletion (E2)