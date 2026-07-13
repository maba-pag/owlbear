---
id: 1599
title: 'P1-06: Tests — computeSignal unknown state'
status: archived
priority: medium
created: 2026-05-16T03:35:25.284760+00:00
updated: 2026-05-16T06:52:25.155110+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on: []
ac:
  - "New describe block asserts: computeSignal(null as any, pendingDRIds) returns
    'unknown', computeSignal({} as any, pendingDRIds) returns 'unknown', computeSignal(undefined
    as any, pendingDRIds) returns 'unknown'"
  - Existing 17 test cases in computeSignal.test.ts remain unmodified (no edits 
    to existing describe blocks)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for computeSignal unknown state extension.
Out of scope: Implementation, formatting utilities, token migration.

2026-05-16T04:22:00+00:00


## Research
- AC-1 corrected: function returns a string, not an object; brief confirms `\"unknown\"` state string
- AC-2 corrected: actual 5 states are dr-pending/blocked/claimed/deps-unmet/ready (not green/yellow/red/gray/stale)
- Research doc: .owlbear/research/compute-signal-unknown-state.md
- Sources: 2 studied (brief + codebase), 2 high-relevance
- Recommendation: extend CardSignal union type + guard clause (confidence: 0.90)

[[2026-05-16T06:22:52+02:00]]
## Research
- Research doc: .owlbear/research/compute-signal-unknown-state.md
- Sources: 4 studied (impl, brief, existing tests, stance doc), 4 high-relevance
- Corrected both ACs: (1) function returns string not object, (2) actual state names not color names
- Recommendation: extend CardSignal union + guard clause (confidence: 0.90)
- Challenge: skipped (trivial scope)
- No new follow-up tasks — impl task #1605 already exists
- Commit: 5c9736bc

[[2026-05-16T06:50:33+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for one function's defensive-input extension |
| Interface clarity | PASS | AC specifies exact calls, cast patterns, and expected returns |
| Dependency correctness | PASS | No deps needed — function and test file exist |
| Module layering | PASS | Test imports from ../utils — standard direction |
| TDD compliance | PASS | This IS the RED phase task; paired with GREEN #1605 |
| KISS/YAGNI | PASS | Minimal: 3 new assertions + no-modification constraint |
| Premise challenge | PASS | null/undefined crash, {} returns false-positive 'ready' — real bug |
| Pattern consistency | PASS | Follows existing describe/it/makeTask pattern in computeSignal.test.ts |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend utils only |

### Challenge Results
- Challenger: reconsider (0.62)
- Issues raised: AC-2 vagueness (valid — refined), RED/GREEN mismatch with #1605 (noted for downstream), undefined case omitted (valid — added to AC-1), evidence count minor error
- Architect response: accepted AC refinements, rebutted contract-scope concern (signature widening is #1605's job, tests use `as any` per standard RED practice), noted #1605 stale AC for correction at its own arch review

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### AC Refinements Applied
- AC-1: Added `undefined` case (same crash class as null); specified `as any` cast pattern for type safety bypass in RED phase
- AC-2: Reworded from vague "existing behavior unchanged for valid inputs" to verifiable "existing 17 tests remain unmodified"

### Notes for Downstream
- Paired impl task #1605 has stale AC (mentions "object" return and color names) — will be corrected at its architecture review
- Test-writer should add new describe block at end of computeSignal.test.ts, not modify existing blocks
- Tests will fail RED because: (1) 'unknown' not in CardSignal union type, (2) function crashes on null/undefined

### Verdict: APPROVE
### Action Taken: Refined AC for precision, advanced to todo

[[2026-05-16T07:06:41+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/computeSignal.test.ts (new describe block appended; existing file per architect guidance)
- Classes: TestFromAC_ComputeSignalUnknownState
- Tests per category: happy 3 (null/undefined/{} → 'unknown'), boundary 3 (same inputs with non-empty pendingDRIds), edge 0, error 0
- Total: 6 tests, all FAIL (confirmed by quality-runner)
  - null/undefined → TypeError: Cannot read properties of null/undefined (reading 'id')
  - {} → AssertionError: expected 'ready' to be 'unknown'
- Lint: clean (eslint exit 0)
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC-1: null/undefined/{} → 'unknown' | 6 tests (3 happy + 3 boundary) |
  | AC-2: existing 17 tests unmodified | structural — 17 existing tests are the direct regression guards; no new failing tests possible without duplicating direct coverage |
- Commit: 993a0b7d

[[2026-05-16T07:31:08+02:00]]
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/utils/computeSignal.ts
- Implementation summary:
  - Extended `CardSignal` union to include `"unknown"`.
  - Added an early guard in `computeSignal(task, pendingDRIds)` to return `"unknown"` when input is invalid (`null`, `undefined`, or missing numeric `id`).
  - Preserved existing precedence logic for valid tasks (`dr-pending > blocked > claimed > deps-unmet > ready`).
- RED verification (before code change):
  - quality-runner scoped on `src/__tests__/computeSignal.test.ts`
  - Result: 17 passed, 6 failed (all in `TestFromAC_ComputeSignalUnknownState`)
  - Failures matched expected behavior gap:
    - TypeError on `null`/`undefined` (`reading 'id'`)
    - `{}` returned `"ready"` instead of `"unknown"`
- GREEN verification (after code change):
  - quality-runner scoped tests: `src/__tests__/computeSignal.test.ts`
  - Result: 23 passed, 0 failed
  - Lint scoped paths:
    - `src/utils/computeSignal.ts`
    - `src/__tests__/computeSignal.test.ts`
  - Lint result: clean
  - Coverage (module): `computeSignal.ts` = 100%
- AC evidence mapping:
  - AC-1 (`null`/`undefined`/`{}` => `"unknown"`): satisfied by 6 passing `TestFromAC_ComputeSignalUnknownState` assertions.
  - AC-2 (existing 17 tests unmodified): preserved; full file run now green with 23/23 passing.
- Commit:
  - `a6e26299` — `fix: return unknown for invalid computeSignal input (#1599, builder)`

[[2026-05-16T08:06:48+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1599 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped GREEN proof in task body reports `src/__tests__/computeSignal.test.ts` at 23 passed / 0 failed, scoped lint clean, and `computeSignal.ts` coverage at 100%. Builder commit `a6e26299` and test-writer commit `993a0b7d` are present in `.git/logs/refs/heads/dev:3076` and `.git/logs/refs/heads/dev:3070`.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1: `computeSignal(null as any, pendingDRIds)`, `computeSignal({} as any, pendingDRIds)`, and `computeSignal(undefined as any, pendingDRIds)` return `'unknown'` | `serve/cockpit/web/src/utils/computeSignal.ts:1` widens `CardSignal` to include `'unknown'`; `serve/cockpit/web/src/utils/computeSignal.ts:11-12` guard invalid input and return `'unknown'` | `serve/cockpit/web/src/__tests__/computeSignal.test.ts:165-201` adds 6 explicit assertions covering `null`, `undefined`, and `{}` with empty and non-empty `pendingDRIds`; builder GREEN evidence shows the full file at 23/23 | PASS |
| AC-2: Existing 17 test cases in `computeSignal.test.ts` remain unmodified | Current file structure is consistent with append-only change: legacy suite starts at `serve/cockpit/web/src/__tests__/computeSignal.test.ts:40`; the new task block starts at `serve/cockpit/web/src/__tests__/computeSignal.test.ts:165` after the existing suite/comment boundary at `serve/cockpit/web/src/__tests__/computeSignal.test.ts:160` | Test-writer notes state a new describe block was appended; builder notes report only `serve/cockpit/web/src/utils/computeSignal.ts` changed in GREEN and the complete `computeSignal.test.ts` file passes at 23/23 | PASS |

- Proof sufficiency: the new tests are specific equality assertions (`toBe('unknown')`), and the boundary variants with populated `pendingDRIds` would fail if precedence logic ran before the invalid-input guard.
- Safety/security: no new injection, credential, or persistence surface is introduced. Editor diagnostics report no errors in `serve/cockpit/web/src/utils/computeSignal.ts`, `serve/cockpit/web/src/components/Card.tsx`, `serve/cockpit/web/src/utils/format.ts`, or `serve/cockpit/web/src/__tests__/computeSignal.test.ts`.
- Challenger result: `proceed` (0.82). Main concern was adjacent five-state consumer assumptions, but direct inspection shows safe fallback rather than a hard break.

## Observations
- `serve/cockpit/web/src/components/Card.tsx:52` and `serve/cockpit/web/src/components/Card.tsx:158` still only render explicit cue chips for `blocked`, `claimed`, `deps-unmet`, and `dr-pending`, and `serve/cockpit/web/src/components/Card.css:89-101` has no dedicated `[data-signal="unknown"]` selector. This is not blocking for task #1599 because the AC is limited to `computeSignal()` invalid-input behavior, but it is a reasonable future-proofing target if `unknown` becomes intentionally user-visible.
- `serve/cockpit/web/src/utils/format.ts:2`, `serve/cockpit/web/src/utils/format.ts:61`, and `serve/cockpit/web/src/utils/format.ts:66` already provide graceful string fallback for unknown signal labels.
- Independent `quality-runner` rerun was not needed because builder evidence was complete and internally consistent under the reviewer trust-the-builder model.

[[2026-05-16T08:16:41+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | No | N/A | `computeSignal` / `CardSignal` absent from `serve/cockpit/README.md` (grep confirmed, 0 matches). Internal utility; not a documented public API surface. No task-caused drift. |
| 2 | External attribution | No | N/A | All sources cited in task body are internal (impl, brief, existing tests, stance doc). No external attribution needed. |
| 3 | Research doc | Yes | PASS | `.owlbear/research/compute-signal-unknown-state.md` exists; line 3 carries owning-task ref `#1599`. Task body cites the file in both research sections. |
| 4 | Deletion detection | No | N/A | No files deleted. `computeSignal.ts` modified in-place; `computeSignal.test.ts` appended. No orphaned references possible. |

### Verification Layers
- Layer 1 — grep: `computeSignal|CardSignal` → 0 matches in `serve/cockpit/README.md`. No stale references exist and none are required.
- Layer 2 — LLM editorial: README documents launch commands, frontend surface, and feature verifications. None reference `computeSignal` or `CardSignal`. The utility's invalid-input guard is an implementation detail. No coherence issues, no contradictions.

### Scratch Cleanup
No `.owlbear/scratch/1599-*` files found. Nothing to delete.

[[2026-05-16T08:52:25+02:00]]
## Audit

### Regression Detection
Python full suite: 4618 passed, 239 failed, 14 skipped, 9 errors. All failures in unrelated domains (test_cockpit_view, test_engine_accessor_migration, test_server, test_ideation_diagram, test_cockpit_pds_build_compat) — pre-existing background noise. Vitest computeSignal.test.ts: 23/23 passed. No task-caused regressions.

### Intent Verification
Changed files: computeSignal.ts, computeSignal.test.ts, compute-signal-unknown-state.md — all within cockpit frontend utils domain. Guard clause for invalid inputs returning 'unknown' matches stated AC purpose. No extraneous scope.

### Architect Quality
Score: 4/5. ACs specific (exact calls, cast patterns, expected returns). AC-2 refined from vague wording to verifiable "existing 17 tests remain unmodified" during arch review. Minor refinement needed but solid overall.

### Commit Integrity
- 5c9736bc — research doc (researcher)
- 993a0b7d — failing tests (test-writer)
- a6e26299 — implementation fix (builder)
All properly attributed with task ref #1599.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
