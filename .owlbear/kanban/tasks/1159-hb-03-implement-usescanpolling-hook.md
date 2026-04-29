---
id: 1159
title: '[MERGED into #1157] HB-03: Implement useScanPolling hook'
status: backlog
priority: important
created: 2026-04-28T17:34:42.736707+00:00
updated: 2026-04-28T22:26:49.534404+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:build
parent:
depends_on:
- 1157
blocked: false
block_reason: 'true'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Seed from ideation task #1042 — cockpit health badge feature.
Backend: `POST /api/tasks/scan` returns `list[dict]` with keys `code`, `detail`, `file_path`.
Existing polling pattern: `usePolling` in `serve/cockpit/web/src/hooks/usePolling.ts`.

## Acceptance Criteria

- [ ] Hook polls `POST /api/tasks/scan` at a configurable interval (default 60 seconds)
- [ ] Exposes: `items` (array of `{code, detail, file_path}`), `isLoading`, `error`
- [ ] Handles network failures without throwing unhandled errors
- [ ] Cleans up interval on unmount
- [ ] All #1157 tests pass

## Scope

- **In scope:** `useScanPolling` hook in `serve/cockpit/web/src/hooks/`
- **Out of scope:** UI components, Shell integration

[[2026-04-28]]
## Merged

This task was merged into #1157 during architecture review. The original TDD decomposition (separate test + implementation tasks) was pipeline-incompatible — `type:test` on #1157 caused the builder to implement the hook directly under that task. Implementation committed at `366542ac`, 20/20 tests passed, reviewed and archived.

See #1158 architecture review for the sibling pipeline warning that flagged this pair.

Delete this task when convenient.
[[2026-04-28]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Hook does one thing: poll scan endpoint |
| Interface clarity | PASS | Inputs/outputs well-defined |
| Dependency correctness | FAIL | #1157 already completed full pipeline including implementation |
| TDD compliance | N/A | Redundant — work done under #1157 |
| Premise challenge | FAIL | Task is residual shell; implementation committed at 366542ac under #1157 |

### Challenge Results
- Challenger: **reconsider** (confidence 0.43)
- Key finding: Archived #1158 architecture review explicitly flagged #1157/#1159 pair as merge candidates due to `type:test` double pass-through problem. #1157 builder notes confirm implementation was completed, 20/20 tests passed, reviewed and archived.
- Architect response: **revised** — changed verdict from APPROVE to MERGE

### Evidence
- #1157 archived with builder notes showing `useScanPolling.ts` implemented (commit 366542ac)
- #1158 architect review §Sibling Pipeline Warning: "Tasks #1157/#1159 have the same type:test double pass-through problem"
- #1160 precedent: handled identically as residual merged shell
- Updated #1161 dependency: removed stale dep on #1159 (retains dep on archived #1158)

### Pipeline Warning (forward)
Tasks #1161/#1162 have the same `type:test` double pass-through problem flagged in #1158. Orchestrator should merge this pair before architect review.

### Verdict: MERGE
### Action Taken: Marked #1159 as [MERGED into #1157]. Updated #1161 deps to remove #1159. Residual shell — delete when convenient.

## User comment
Please check task was not only merged but also implemented. User requests this, because this task was marked merged at 22:26, but task #1158 was marked archived around the same time, which could mean it was not acted upon!
