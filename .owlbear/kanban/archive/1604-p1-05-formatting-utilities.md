---
id: 1604
title: 'P1-05: Formatting utilities'
status: archived
priority: important
created: 2026-05-16T03:36:07.011240+00:00
updated: 2026-05-16T08:55:18.485051+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1598
ac:
  - 'utils/format.ts exports null-safe formatters for: relative time, priority label,
    status label, signal description'
  - No formatter output appears in any fetch() or mutation call path 
    (canonical/display partition C8)
  - 'PRIORITY_LABELS hardcoded map is removed from utils/format.ts — formatPriority
    delegates to toTitleCaseWords (C7: no fixed priority vocabulary in formatter module)'
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1590.

Canonical/display value partition (C8): formatted display values never feed mutation APIs. Config-driven enum vocabularies (C7): statuses and priorities come from board API.

Scope: Formatting utilities only.
Out of scope: Token migration, component migration, layout.

[[2026-05-16T09:07:40+02:00]]
## Research
- Research doc: .owlbear/research/formatting-utilities.md
- Sources: 7 studied (all codebase-internal), 5 high-relevance
- Recommendation: Remove stale `PRIORITY_LABELS` hardcoded map from format.ts — contains phantom values (low, normal) not in backend, misses real values (someday, nice-to-have). `toTitleCaseWords` fallback produces correct output for all backend priorities. Retain `SIGNAL_LABELS` (signals aren't board API enums, semantic labels not derivable from title-casing). (confidence: 0.80)
- Challenge: Challenger scored original at 0.47, caught vocabulary drift between map and backend topology — this STRENGTHENED removal recommendation. Revised confidence to 0.80.
- AC1/AC2 already satisfied by #1598 builder (format.ts exists, 37 tests pass, guardrail enforced). AC3 fix: remove PRIORITY_LABELS.
- Tier: T1 autonomous — redundant stale code removal
- No follow-up tasks needed — inline formatter consolidation already scoped to Batch 2 (#1609-#1618)

[[2026-05-16T09:21:36+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: remove stale PRIORITY_LABELS map from format.ts |
| Interface clarity | PASS (after REFINE) | AC3 refined: names PRIORITY_LABELS, formatPriority, toTitleCaseWords, format.ts |
| Dependency correctness | PASS | #1598 archived/completed — format.ts exists, 37 tests pass |
| Module layering | PASS | Pure utility, no upward imports |
| TDD compliance | PASS | Existing proof scope covers contract; no new behavior to TDD |
| KISS/YAGNI | PASS | Removing redundant stale code |
| Premise challenge | PASS | Research confirmed vocabulary drift — map is redundant AND stale (phantom low/normal, missing someday/nice-to-have) |
| Pattern consistency | PASS | formatPriority will match formatStatus pattern (direct toTitleCaseWords delegation) |
| Security surface | PASS | No system boundary |
| Single domain | PASS | Frontend only |

### Challenge Results
- Challenger: reconsider (0.73)
- Findings: (1) AC3 used banned quantifier \"all\"; (2) C7 contract narrowing concern; (3) de-escalation needs justification; (4) AC2 minor overclaim on inline formatters
- Architect response: ACCEPTED finding 1 — rewrote AC3 without banned words. REBUTTED findings 2-4: (2) formatter-level C7 = no hardcoded vocabulary; broader component→API wiring is Batch 2 scope (#1609-#1618); (3) removing PRIORITY_LABELS produces zero behavioral change for any input — map entries output identically via toTitleCaseWords, so no test can distinguish; AC3 is verified by code inspection at review; (4) AC2 scopes to mutation call path, which the 13-file guardrail covers; inline component formatters are Batch 2 consolidation scope.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing (de-escalated)
- De-escalation rationale: AC1/AC2 already satisfied by #1598. AC3 is structural (code deletion) with zero observable behavior change — toTitleCaseWords produces identical output for every PRIORITY_LABELS entry. No test can distinguish map-present vs map-removed. Verification is by code inspection.
- Existing proof scope: serve/cockpit/web/src/__tests__/format_1598.test.ts (37 tests)
- Test-writer: SKIP

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC3 for precision (removed banned quantifier, named concrete artifacts), de-escalated proof bundle from behavioral to existing. Advanced to todo.

[[2026-05-16T09:37:28+02:00]]
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Architect de-escalated from behavioral: AC1/AC2 already satisfied by #1598 (format.ts exists, 37 tests pass, guardrail enforced). AC3 is structural code deletion (removing PRIORITY_LABELS map) with zero observable behavior change — toTitleCaseWords produces identical output for every map entry, so no test can distinguish map-present vs map-removed. Verification is by code inspection at review.
- Existing proof scope: serve/cockpit/web/src/__tests__/format_1598.test.ts (37 tests).
- Passing through to builder.

[[2026-05-16T09:53:36+02:00]]
## Builder Notes
- Implementation: removed `PRIORITY_LABELS` from `serve/cockpit/web/src/utils/format.ts`; `formatPriority` now delegates directly to `toTitleCaseWords(...)` with existing null fallback.
- Files changed: serve/cockpit/web/src/utils/format.ts
- Tests (existing proof required): `serve/cockpit/web/src/__tests__/format_1598.test.ts` via quality-runner — 37 passed, 0 failed, 0 skipped.
- Lint: clean (eslint clean on touched source + proof test file).
- Coverage: not required for `proof_bundle: existing`; no behavioral delta expected.
- Evidence summary: AC3 satisfied by code inspection and proof run; no formatter output introduced into mutation paths; change is surgical and vocabulary hardcoding is removed.
- Commit: 15b5a1cc (`refactor: remove stale priority map (#1604, builder)`).

[[2026-05-16T10:12:44+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1604 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: existing-proof bundle; builder reported `serve/cockpit/web/src/__tests__/format_1598.test.ts` via quality-runner with 37 passed, 0 failed, 0 skipped, plus eslint clean on the touched source and proof test file; commit `15b5a1cc` is present in git logs.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1. `utils/format.ts` exports null-safe formatters for relative time, priority label, status label, and signal description | `serve/cockpit/web/src/utils/format.ts:22`, `:37`, `:45`, and `:53` export the four formatters. Null fallbacks remain explicit at `:24`, `:39`, `:47`, and `:55`; signal fallback path remains at `:58`. | `serve/cockpit/web/src/__tests__/format_1598.test.ts:43`, `:48`, `:78`, `:83`, `:113`, `:118`, `:153`, and `:158` assert exact null/undefined fallbacks; builder reported the full proof file passing (37/37). | PASS |
| 2. No formatter output appears in any fetch/mutation call path (C8) | Sampled canonical mutation files remain payload-oriented and formatter-free: `serve/cockpit/web/src/api/tasks.ts`, `serve/cockpit/web/src/hooks/useTaskMutation.ts`, and `serve/cockpit/web/src/components/TaskFieldsEditor.tsx`. Workspace search for `utils/format` under `serve/cockpit/web/src/**` returned only the proof test import. | `serve/cockpit/web/src/__tests__/format_1598.test.ts:184` defines the mutation graph, `:204` defines the import guard regex, and `:206-210` assert every listed mutation-path file does not import `utils/format`; builder reported the proof file passing. | PASS |
| 3. `PRIORITY_LABELS` is removed from `utils/format.ts`; `formatPriority` delegates to `toTitleCaseWords` (C7) | `serve/cockpit/web/src/utils/format.ts:12` defines `toTitleCaseWords`; `serve/cockpit/web/src/utils/format.ts:37-42` shows `formatPriority` now delegates directly to that helper with the existing null fallback. Workspace search for `PRIORITY_LABELS` under `serve/cockpit/web/src/**` returned no matches. | Structural AC; proof-by-inspection is consistent with the architect/test-writer de-escalation to `proof_bundle: existing`. Existing formatter proof remains green per builder evidence. | PASS |

- Blocking findings: none.
- Safety/security check: no new input handling, auth, storage, or external-integration surface was introduced; sampled mutation-path files continue to serialize canonical request payloads only.

## Observations
- The de-escalation to existing proof is justified by the actual implementation: removing the stale priority map changes structure, not observable formatter output.
- Independent editor diagnostics on `serve/cockpit/web/src/utils/format.ts` and `serve/cockpit/web/src/__tests__/format_1598.test.ts` are clean.

[[2026-05-16T10:24:23+02:00]]
## Docs Gate

**Verdict: PASS — no documentation changes required.**

| Item | Status | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | `serve/cockpit/README.md` contains zero references to `format.ts`, `PRIORITY_LABELS`, `formatPriority`, `toTitleCaseWords`, or any formatting utility. README documents external HTTP API surface; internal utility modules are out of scope. Layer 1 grep: clean. Layer 2 editorial: coherent, no contradictions. |
| 2. External Attribution | N/A | All 7 sources codebase-internal per task body; no external attribution needed. |
| 3. Research Doc | PASS | `.owlbear/research/formatting-utilities.md` exists and is linked from task body. |
| 4. Deletion Detection | N/A | No files deleted; only `format.ts` modified (map removed, function simplified to delegate). |

**Pre-existing TODO:** `serve/cockpit/README.md` contains a pre-existing `> **TODO:** stale — view.cleanup()...` [#1571] marker — outside this task's scope, pass-through only.

**Scratch cleanup:** No `1604-*` scratch files found.

[[2026-05-16T10:55:18+02:00]]
## Audit

### Regression Detection
- quality-runner mode full: environment error (474 phantom failures from stale session state). Fallback: direct execution per pipeline-protocol env fallback.
- Python full suite: 15 passed, 1 failed. Single failure: test_cockpit_pds_build_compat.py (meta-test wrapping vitest) is pre-existing (last touched by ruff format commit 414444b9, not by #1604). Vitest itself: 116 files, 1895 passed, 11 skipped, 0 failed.
- Regression verdict: PASS. No regressions caused by #1604.

### Intent Verification
- Scope alignment: PASS. Only file changed: serve/cockpit/web/src/utils/format.ts (frontend utility domain, matching frontend/pds/phase-1 tags).
- Purpose match: PASS. PRIORITY_LABELS map removed; formatPriority now delegates to toTitleCaseWords with null fallback. Matches AC3 intent exactly.
- Extraneous scope: none. Single-file change, 9 deletions 1 addition.
- Boundary check: function-level behavior verification deferred to reviewer.

### Architect Quality: 4/5
AC lines are specific, naming concrete artifacts (PRIORITY_LABELS, formatPriority, toTitleCaseWords, format.ts) and referencing design constraints (C7, C8). Minor gap: AC3 needed refinement during arch review to remove banned quantifier, but was caught and corrected by architect. De-escalation to existing proof well-justified with explicit rationale.

### Commit Integrity
- Upstream commit presence: PASS. Builder commit 15b5a1cc ("refactor: remove stale priority map (#1604, builder)") confirmed. 1 file changed, scope matches AC.
- Research doc: .owlbear/research/formatting-utilities.md exists and is linked from task body.

### Deduction Breakdown
No deductions applied:
- Regression detection: PASS (0)
- Intent verification: PASS (0)
- Architect quality: 4/5 (0)
- Commit integrity: PASS (0)
- Reviewer evidence section: present and detailed with per-AC mapping (0)

### Confidence: 1.00
### Action: archive
