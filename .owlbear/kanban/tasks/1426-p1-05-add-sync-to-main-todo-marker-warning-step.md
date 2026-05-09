---
id: 1426
title: 'P1-05: Add sync-to-main TODO marker warning step'
status: in-progress
priority: important
created: 2026-05-08T00:41:08.358257+00:00
updated: 2026-05-09T07:17:48.620575+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
- type:config
parent: 1421
depends_on:
- 1423
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Acceptance Criteria

Add a pre-sync warning step to the sync-to-main GitHub Actions workflow (`.github/workflows/sync-to-main.yml`):

1. Before syncing, grep all `serve/*/README.md`, `README.md`, `README-consumer.md` for `> **TODO:**` markers (td:0)
2. If markers found: print a summary (count + file list) as a workflow warning annotation (td:0)
3. Do NOT fail the workflow — warning only, not a hard gate (td:0)
4. Summary format: "⚠️ {n} unresolved TODO markers in {m} files: {list}" (td:0)

**In scope:** CI workflow step only.
**Out of scope:** Resolving the markers (doc-audit), marker format definition (#1423).

Brief: see parent #1421
[[2026-05-09]]
## Research
- Research doc: .owlbear/research/sync-todo-marker-warning.md
- Sources: 4 studied, 2 high-relevance (GitHub Actions docs, existing workflow)
- Recommendation: single inline bash step using `grep -rn '> \*\*TODO:\*\*'` + `::warning::` annotation (confidence: 0.95)
- Tier: T1 — trivial CI config change, no architecture impact
- Implementation: ~15-line bash step after checkout, before sync. Uses `::warning title=Unresolved TODO markers::` format. Never fails workflow.
- Placement: after "Capture dev metadata" step, before "Validate selected paths"
- No follow-up tasks needed — #1426 is the implementation task itself
[[2026-05-09]]
## Architecture Review

**Verdict:** APPROVED — T1 CI config change, well-scoped AC, follows existing workflow patterns.

### AC Assessment

| AC Line | Assessment | Depth |
|---------|-----------|-------|
| 1. Grep target files for markers | Specific pattern + file list, verifiable | td:0 |
| 2. Print warning annotation | Clear output spec | td:0 |
| 3. Warning only, no failure | Constraint verifiable by inspection | td:0 |
| 4. Summary format | Exact format string | td:0 |

All AC lines td:0 → Test-writer: SKIP

### Architecture Notes

- **Pattern consistency:** Existing workflow uses inline bash steps throughout — this follows the same style.
- **Placement:** After "Capture dev metadata" (line ~134), before "Validate selected paths" (line ~142). Correct — files are checked out by that point.
- **Shell glob:** `serve/*/README.md` is shell-expanded in GHA `run:` — works correctly. Non-matching glob is safe with `2>/dev/null`.
- **Exit code:** grep returns 1 on no-match; research doc correctly notes `|| true` mitigation.
- **No security surface**, no Python code, no test surface.

### Dependency Check

- #1423 (marker format definition): archived/done ✅
- #1421 (parent brief): archived/done ✅

### Challenger

Skipped — all AC lines td:0 per Step 2.1/2.5 rule.

### Tag Added

- `type:config` — enables test-writer pass-through.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `type:config`) — no tests applicable.
- All AC lines annotated `td:0`; architect explicitly flagged SKIP.
- Passing through to builder.