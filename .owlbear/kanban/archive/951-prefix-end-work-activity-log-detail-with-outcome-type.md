---
id: 951
title: Prefix end_work activity log detail with outcome type
status: archived
priority: needed
created: 2026-04-18T09:43:38.688692+00:00
updated: 2026-04-18T11:06:59.243714+00:00
tags:
- cockpit
- engine
- phase-1
parent:
depends_on:
- 923
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Change `end_work()` activity log detail strings to prefix the outcome type, enabling unambiguous session state derivation in `list_sessions()`.

## Context

Research #923 finding F1: `end_work` success and reject both produce identical `"X -> Y"` detail format. `list_sessions()` cannot reliably distinguish completed-pass from completed-rejected without knowing the status order.

## Acceptance Criteria

- [ ] `end_work()` in `engine.py` changes detail format from `f"{old} -> {new}"` to `f"{outcome}: {old} -> {new}"` for success and reject outcomes
- [ ] Fail detail changes from `"outcome=fail"` to `"fail: outcome=fail"` (or stays as-is if parseable)
- [ ] Block detail changes from `"blocked: {reason}"` to `"block: {reason}"` (or stays as-is if parseable)
- [ ] Existing activity.jsonl entries without prefix remain parseable (backward compat in reader)
- [ ] Existing engine tests updated for new detail format
- [ ] No new fields added to JSONL schema

## Files

- `serve/kanban/src/owlbear_kanban/engine.py` (end_work method)
- Existing engine activity log tests

## Research

See `.owlbear/research/923-list-sessions-tests.md` § 3.2 F1
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/951-end-work-detail-prefix.md
- Sources: 4 studied, 4 high-relevance
- Recommendation: Prefix all 4 outcomes in `end_work()` details dict (4 lines), add 1-line backward-compat fallback in `_classify_end_work()` for unprefixed legacy entries (confidence: .90)
- Key finding: `_classify_end_work()` and `test_list_sessions.py` already expect the prefixed format — only the writer is out of sync
- Tier: T1 — autonomous, 5-line surgical change
- Follow-up tasks created: none (task AC already covers full scope)
- Decision requests: none
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: prefix detail strings in `end_work()` writer |
| Interface clarity | FAIL | AC2/AC3 hedging ("or stays as-is if parseable") is non-falsifiable — builder can ship partial implementation and claim compliance |
| Dependency correctness | PASS | #923 archived (research complete), findings referenced |
| Module layering | PASS | Changes within `engine.py` only, no cross-module concerns |
| TDD compliance | PASS | Test-writer will handle RED phase |
| KISS/YAGNI | FAIL | Fail/block prefix changes add zero functional value — both already classify correctly via fall-through in `_classify_end_work()`. Backward-compat fallback introduces misclassification risk (see below) |
| Premise challenge | PARTIAL | Core premise (success/reject prefix) is valid. Extended scope (fail/block + backward compat) is unnecessary |
| Pattern consistency | PASS | Follows existing activity log patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban engine domain only |

### Critical Issues

**1. Overlap with #952 — scope collision**

# 952 ("Fix end_work() detail format for session classification") is a strict subset of #951. #952 changes only success/reject (2 lines), leaves fail/block unchanged, requires no backward-compat fallback. Both are in `backlog`. #952 has cleaner, more focused, fully falsifiable AC

**2. AC2/AC3 non-falsifiable**
`"fail: outcome=fail" (or stays as-is if parseable)` and `"block: {reason}" (or stays as-is if parseable)` — either outcome passes the AC. These lines need to be definitive.

**3. Backward-compat fallback (AC4) introduces data integrity bug**
The research recommends `if " -> " in detail: return "completed-pass"`. Old reject entries (e.g., `"in-progress -> todo"`) contain `" -> "` and would be misclassified as `completed-pass`. This trades misclassifying old successes (current: fall-through to `completed-fail`, conservative) for misclassifying old rejects (proposed: mapped to `completed-pass`, dangerous). False positives (rejected → pass) are worse than false negatives (success → fail) in a dashboard context.

**4. Fail/block prefix changes are YAGNI**

- `"outcome=fail"` → falls through to `completed-fail` ✓ (correct without prefix)
- `"blocked: {reason}"` → falls through to `completed-fail` ✓ (correct without prefix)
- Renaming `"blocked:"` to `"block:"` breaks existing test fixture at `test_list_sessions.py` (uses `"blocked: needs DB migration"`) for zero functional gain.

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| Old unprefixed `"X -> Y"` success entry | Falls through to `completed-fail` | None | Yes (conservative) | Old sessions show as fail — minor |
| Old unprefixed `"X -> Y"` reject entry + proposed fallback | Mapped to `completed-pass` | None | **No** | Old rejected sessions show as passed — **data integrity** |

### Challenge Results

- Challenger: **reconsider** (confidence 0.50)
- Key challenges: (C1) evidence overstated — only success/reject fixtures use prefixed format, fail/block do not; (C2) backward-compat fallback misclassifies old rejects as pass; (C3) AC2/AC3 non-falsifiable; (C4) overlap with #952 not addressed
- Architect response: **accepted** — all 4 challenges validated by codebase evidence

### Recommended Refinement

**Option A (preferred): Supersede #951 with #952**

# 952 has better-scoped, fully falsifiable AC. It fixes the actual bug (success/reject prefix) without unnecessary scope. Close #951 as superseded

**Option B: Reduce #951 scope to match #952**
Strip AC2 (fail prefix), AC3 (block prefix), AC4 (backward-compat fallback). Remaining AC:

- `end_work(outcome="success")` writes `f"success: {old} -> {new}"`
- `end_work(outcome="reject")` writes `f"reject: {old} -> {target}"`
- Existing `_classify_end_work()` works without modification
- Integration tests verify round-trip classification
- No existing tests broken
Then mark #952 as duplicate.

Either option resolves the overlap. Backward-compat fallback can be a separate task if later needed.

### Verdict: REFINE

### Action Taken: Kept in backlog. AC needs tightening: remove hedging on AC2/AC3, resolve #952 overlap, drop or redesign backward-compat fallback (AC4) which introduces misclassification risk

[[2026-04-18]]

## Architecture Review (Retry)

### Decision: SUPERSEDE — #951 rejected in favor of #952

### Rationale

Prior REFINE identified 4 critical issues. This retry resolves them via Option A (supersede):

1. **Non-falsifiable AC2/AC3** — hedging ("or stays as-is if parseable") allows any implementation to pass. Not fixed in body because #952 eliminates these AC lines entirely.
2. **Scope collision with #952** — #952 is a strict subset with fully falsifiable AC targeting only the 2-line bug (success/reject prefix). Both tasks change the same lines in `engine.py` L900-904.
3. **YAGNI scope** — fail/block prefix changes add zero functional value. `_classify_end_work()` L55-62 already correctly classifies `"outcome=fail"` and `"blocked: ..."` via fall-through to `completed-fail`.
4. **Backward-compat fallback (AC4) is dangerous** — proposed `if " -> " in detail: return "completed-pass"` would misclassify old reject entries (`"in-progress -> todo"`) as `completed-pass`. False positives worse than false negatives in dashboard context.

### Evidence

- `_classify_end_work()` at [engine.py L55-62](serve/kanban/src/owlbear_kanban/engine.py#L55) — already handles fail/block correctly without prefix
- `end_work()` detail dict at [engine.py L900-904](serve/kanban/src/owlbear_kanban/engine.py#L900) — only L901 (success) and L904 (reject) need prefix
- `test_list_sessions.py` L151,175,187,199 — fixtures already use prefixed format for success/reject, unprefixed for fail/block

### Action

- #951 → research (superseded, archive candidate)
- #952 remains in backlog — fully scoped, falsifiable AC, ready for architecture review
- Backward-compat fallback deferred to separate task if later needed

### Verdict: REJECT (superseded by #952)

[[2026-04-18]]

## Research (Supersession Validation)

Validated architect's SUPERSEDE verdict. #951 is fully superseded by #952.

### Evidence Summary

| Criterion | #951 | #952 |
|-----------|------|------|
| Scope | 4 outcomes + backward-compat fallback | 2 outcomes (success/reject only) |
| AC quality | AC2/AC3 non-falsifiable ("or stays as-is if parseable") | Fully falsifiable — exact format strings |
| YAGNI | Fail/block prefix = zero functional value | Only changes what's broken |
| Risk | Backward-compat fallback misclassifies old rejects as pass | No fallback, no misclassification risk |
| Status | research (superseded) | todo (architect-approved) |

### Codebase Verification

- `_classify_end_work()` engine.py L55-62: expects `startswith("success:")` / `startswith("reject:")`, falls through correctly for fail/block
- `end_work()` engine.py L900-904: only L901 (success) and L904 (reject) need prefix — confirmed bug
- Test fixtures in `test_list_sessions.py`: already use prefixed format for success/reject, unprefixed for fail/block
- Zero existing tests assert old unprefixed format

### Disposition

- #951 → done (superseded, archive candidate)
- #952 at todo — fully scoped replacement, ready for test-writer
- No follow-up tasks needed
- No decision requests needed
[[2026-04-18]]

## Audit

### Disposition: Superseded by #952

Task #951 was correctly identified as over-scoped and superseded by #952 during architecture review. No code deliverables — resolution is the supersession itself.

### Supersession Verification

| Claim | Evidence | Status |
|-------|----------|--------|
| #952 covers success/reject prefix (AC1) | #952 AC1-AC2 specify exact format strings; 11 RED tests committed (3f66e9a2) | PASS |
| Fail/block prefix is YAGNI (AC2/AC3) | `_classify_end_work()` engine.py L50-55: falls through to `completed-fail` correctly for `"outcome=fail"` and `"blocked: ..."` | PASS |
| Backward-compat fallback is dangerous (AC4) | `if " -> " in detail` would misclassify old reject entries (`"in-progress -> todo"`) as `completed-pass` — false positives worse than false negatives | PASS |
| Research doc exists | `.owlbear/research/951-end-work-detail-prefix.md` present | PASS |
| #952 is progressing | #952 status: in-progress, 11 tests committed, architect-approved | PASS |

### Test Results

- pytest: Not run — zero code deliverables, no regression surface
- ruff: Not run — no code changes
- Quality-Runner: Not available (only Explore agent accessible); N/A for superseded task with no code changes

### Architect Quality: 2/5

Original AC had non-falsifiable hedging (AC2/AC3 "or stays as-is if parseable"), YAGNI scope (fail/block prefix), and a dangerous backward-compat fallback (AC4). The architect review process caught all issues and self-corrected via supersession — system worked as designed. No follow-up task created; architect demonstrated calibration by catching own issues.

### Deduction Breakdown

- AC quality ≤ 3: -.03
- No reviewer evidence section: -.02 (expected — no code was written/reviewed)

### Confidence: .95

### Action: archive
