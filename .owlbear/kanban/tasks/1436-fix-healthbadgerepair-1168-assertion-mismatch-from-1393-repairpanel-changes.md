---
id: 1436
title: 'Fix HealthBadgeRepair_1168 assertion mismatch from #1393 RepairPanel changes'
status: in-progress
priority: needed
created: 2026-05-08T12:04:38.739894+00:00
updated: 2026-05-08T14:17:57.079074+00:00
tags:
- cockpit
- frontend
- scope:cockpit-web
parent: 1363
depends_on:
- 1393
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Task #1393 changed `RepairPanel.tsx` confirmation dialog copy to include detailed irreversible/quarantine wording per AC6. The adjacent test suite `HealthBadgeRepair_1168.test.tsx` has 2 tests in `TestFromAC_RepairConfirmCopyExact` that still assert the old shorter wording.

## Acceptance Criteria

- [ ] AC1: Update the 2 assertion strings at ~L340 and ~L351 in `serve/cockpit/web/src/__tests__/HealthBadgeRepair_1168.test.tsx` to match the new confirmation text from #1393
  - Old: `"Fixed files are restored, unfixable files are quarantined. Continue?"`
  - New: `"Fixed files are restored, quarantined files are moved to the quarantine directory (.owlbear/scratch/quarantine), and failed files remain corrupted. This action can be irreversible and cannot be undone."`
- [ ] AC2: `npm test` passes with no failures in `HealthBadgeRepair_1168.test.tsx`
- [ ] AC3: No other test files broken by the change


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: update 2 test assertion strings |
| Interface clarity | PASS | Old/new strings specified exactly, line refs verified |
| Dependency correctness | PASS | #1393 archived (done) |
| Module layering | PASS | N/A — test file only |
| TDD compliance | PASS | This IS the test fix — no preceding test needed |
| KISS/YAGNI | PASS | Minimal scope: 2 string replacements |
| Premise challenge | PASS | Component text changed in #1393, tests must follow |
| Pattern consistency | PASS | Standard test maintenance |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | cockpit frontend only |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- AC1: (td:0) — mechanical string replacement
- AC2: (td:0) — verification gate
- AC3: (td:0) — no-regression check
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
[[2026-05-08]]
Architecture review complete. All criteria PASS — mechanical 2-line string update in test file to match #1393's RepairPanel.tsx copy changes. All AC are td:0; test-writer SKIP.
[[2026-05-08]]
## Test-Writer Notes
- Depth-zero pass-through — all AC annotated `td:0`; architect verdict: `Test-writer: SKIP`.
- Task is a mechanical 2-string replacement in an existing test file (`HealthBadgeRepair_1168.test.tsx`). No new failing tests applicable.
- AC1/AC2/AC3 are all verification gates for the builder's string update.
- Passing through to builder.