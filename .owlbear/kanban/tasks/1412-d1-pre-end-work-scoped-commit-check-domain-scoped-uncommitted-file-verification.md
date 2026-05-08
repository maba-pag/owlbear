---
id: 1412
title: 'D1: Pre-end_work scoped commit check — domain-scoped uncommitted file verification'
status: research
priority: important
created: 2026-05-07T23:16:25.281801+00:00
updated: 2026-05-07T23:18:03.143907+00:00
tags:
- pipeline
- ws-protocol
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

P1: `r-pipeline-protocol` updated with pre-`end_work` commit check requirement
P2: Each agent verifies uncommitted files in its own file domain before calling `end_work`: researcher (`.owlbear/research/`), test-writer (`tests/`), builder (`serve/*/src/`), doc-writer (docs), etc.
P2: Check is domain-scoped — NOT raw `git status --porcelain` (which shows other agents' dirty files in shared worktree)
P2: Protocol specifies the check happens before `end_work`, not as a PostToolUse hook
P3: Verification by diff comparison of modified protocol file

## Scope

**In scope:** Protocol update for scoped commit check in `r-pipeline-protocol`
**Out of scope:** Implementing the check as code/tooling (protocol-level only), PostToolUse hooks