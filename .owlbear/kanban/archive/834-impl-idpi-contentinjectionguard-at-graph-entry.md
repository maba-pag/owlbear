---
id: 834
title: Impl — IDPI ContentInjectionGuard at graph entry
status: archived
priority: medium
created: '2026-04-11T15:08:22.983610+00:00'
updated: '2026-04-12T13:59:02.174723+00:00'
tags:
- phase-1
- scope:knowledge
- security
parent: 751
depends_on:
- 833
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. Implement ContentInjectionGuard and wire into IngestPipeline.

## Acceptance Criteria

1. `ContentInjectionGuard` class in `serve/knowledge/src/owlbear_knowledge/content_guard.py`
2. `CheckResult` dataclass with `threat`, `blocked`, `reason`, `pattern` fields
3. ~40 builtin injection patterns (case-insensitive substring matching)
4. Configurable `custom_patterns` list and `strict_mode` bool
5. Wired into `IngestPipeline.ingest()` — scan chunk text before entity extraction for untrusted sources
6. Strict mode: return blocked status; Warn mode: log + proceed
7. All #833 tests pass

## Context

- Research: .owlbear/research/768-content-safety-idpi-wrapping.md
- Prior art: .owlbear/research/idpi-content-scanning.md (#724)
- Files: `serve/knowledge/src/owlbear_knowledge/content_guard.py` (new), `ingest.py` (modify)

Parent: #751

[[2026-04-12]]

## Research

- Research doc: .owlbear/research/834-contentinjectionguard-green-impl.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: All 7 ACs directly implementable. Use substring matching (not regex) per AC3. ~40 patterns from 7 PinchTab-derived categories. Add "blocked" literal to IngestResult.status. Guard as optional IngestPipeline constructor param. Scan untrusted sources only via existing should_wrap(). (confidence: .88)
- Follow-up tasks created: none (TDD pair #833/#834 complete)
- Decision requests: none
- Tier: T1 (Autonomous) — GREEN implementation of already-designed security feature
- Key findings: PinchTab idpishield now has 100+ regex patterns across 12 categories (Apache-2.0); OwlBear simplifies to ~40 substring patterns per KISS. OWASP LLM01:2025 Strategy #3 validates approach. IngestResult needs additive "blocked" literal. Guard integration at ingest.py L200-210, between chunking and entity extraction.
[[2026-04-12]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Implement guard class + wire into pipeline — inseparable pair; guard without wiring is useless |
| Interface clarity | PASS | ACs specify class location, dataclass fields, pattern strategy, modes, integration point, and test contract (AC7). Builder guidance below adds precision for implicit requirements |
| Dependency correctness | PASS | `depends_on: [833]` correct — RED tests define the contract. #833 is in `todo`, will complete before builder starts #834 |
| Module layering | PASS | `content_guard.py` is sibling to `content_safety.py` in `owlbear_knowledge`. `ingest.py` already imports from `content_safety` — same direction |
| TDD compliance | PASS | #833 = RED, #834 = GREEN. Correct TDD pair |
| KISS/YAGNI | PASS | Substring matching (not regex) per AC3. ~40 patterns from established categories. No hypothetical features |
| Premise challenge | PASS | `content_safety.py` handles wrapping/segregation (defense layer 1) but NOT detection/blocking (defense layer 2). Guard adds distinct capability. OWASP LLM01:2025 Strategy #3 validates. No existing detection capability in codebase |
| Pattern consistency | PASS | Optional constructor param follows `cancel_signal` pattern in `IngestPipeline.__init__`. Separate module follows `content_safety.py` pattern. Dataclass follows existing `IngestResult` BaseModel convention |
| Security surface | PASS | This IS the security feature. Scanning patterns are case-insensitive substring (simple, predictable). Trust boundary reuses existing `should_wrap()` predicate — no new trust logic |
| Single domain | PASS | All in knowledge domain (`owlbear_knowledge`) |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `guard.scan(chunk_text)` | Guard raises unexpected exception | Any | YES — caught by existing `try/except` in `ingest()` L229-235 → `status="failed"` | Ingest fails safely, logged |
| Guard is None | No scanning occurs | N/A | YES — None default means backward-compatible skip | No impact — existing behavior preserved |
| Strict mode + threat detected | Early return before extraction | N/A | YES — returns `IngestResult(status="blocked")` | Ingest blocked, chunk not processed |
| Warn mode + threat detected | Log warning, continue | N/A | YES — proceeds to wrapping + extraction | Warning logged, content still processed with wrapping |

### Builder Guidance — Implicit Requirements Made Explicit

The challenger flagged three implicit requirements. These are derivable from AC6+AC7 and #833 test contracts, but stated here for builder clarity:

1. **AC2 precision:** `CheckResult` field types are `threat: bool, blocked: bool, reason: str, pattern: str` (per #833 AC2 which specifies types)
2. **AC5 wiring mechanism:** Guard as optional `IngestPipeline.__init__` parameter with `default=None`, following the `cancel_signal` pattern (see `ingest.py` L55-61). When `None`, no scanning occurs
3. **AC6 status literal:** Add `"blocked"` to `IngestResult.status: Literal["ok", "failed", "skipped", "cancelled", "blocked"]` — additive, backward-compatible. Strict mode returns `status="blocked"`, not `"failed"` (semantic clarity per #833 arch review)

### Integration Point

Guard scan slots between chunking (L192) and extract comprehension (L207-214) in `ingest()`:

- After: `chunks = await asyncio.to_thread(self._chunker.chunk, ...)`
- Before: `extract_coros = [self._extractor.extract(...) for c in chunks]`
- Guard only scans when `should_wrap()` returns True (untrusted sources)

### Challenge Results

- Challenger: RECONSIDER — recommended making 3 implicit AC requirements explicit
- Architect response: Accepted concern. Cannot edit body (no `edit_task` tool), but all 3 clarifications documented in Builder Guidance section above. ACs are verifiable: AC7 binds implementation to #833 test contracts which specify types and behaviors

### Verdict: APPROVE

### Action Taken: Advanced to todo. All ACs verifiable, architecture sound. Three implicit requirements documented as explicit builder guidance: CheckResult field types, guard constructor param pattern, IngestResult "blocked" literal

[[2026-04-12]]

## Test-Writer Notes

- Test file: tests/test_content_guard_834.py
- Classes:
  - `TestFromAC_BuiltinPatternCoverage` (AC3 — multi-category breadth)
  - `TestFromAC_CustomPatterns` (AC4 — custom_patterns constructor arg)
  - `TestFromAC_StrictModeBool` (AC4 — strict_mode bool constructor arg)
- Tests per category: happy 10, edge 6, error 0, boundary 5
- Total: 21 tests, all FAIL (`ModuleNotFoundError: No module named 'owlbear_knowledge.content_guard'`)
- ruff: clean
- Commit: a04f1c67

### AC Coverage

| AC | Tests |
|----|-------|
| AC3 — ~40 builtin patterns across 7 IDPI categories | `test_detects_system_prompt_*` (×2), `test_detects_jailbreak_*` (×2), `test_detects_role_hijack_*` (×2), `test_detects_instruction_override_*`, `test_detects_exfiltration_*`, `test_detects_indirect_command_*`, `test_detects_social_engineering_*`, `test_pattern_field_is_substring_of_scanned_text` |
| AC4 — custom_patterns list | `test_constructor_accepts_custom_patterns_arg`, `test_custom_pattern_detected_by_scan`, `test_custom_pattern_detection_is_case_insensitive`, `test_custom_patterns_extend_builtins_not_replace`, `test_empty_custom_patterns_behaves_same_as_default` |
| AC4 — strict_mode bool | `test_constructor_accepts_strict_mode_true`, `test_constructor_accepts_strict_mode_false`, `test_strict_mode_true_sets_blocked_true_on_detected_threat`, `test_strict_mode_false_blocked_is_false_on_detected_threat`, `test_blocked_is_false_when_no_threat_regardless_of_strict_mode` |

### Builder Notes

- Tests complement #833 (which covers import, CheckResult fields, basic scan/integration, strict/warn pipeline modes)
- #834 tests focus exclusively on the NEW requirements: multi-category pattern breadth (10+ tests across all 7 categories) and ContentInjectionGuard constructor params (custom_patterns, strict_mode)
- Pattern phrases used in tests are drawn directly from the 7-category table in `.owlbear/research/834-contentinjectionguard-green-impl.md`
- strict_mode=True → blocked=True on threat; strict_mode=False → blocked=False (warn semantics)
[[2026-04-12]]

## Builder Notes

### Files Changed

- `serve/knowledge/src/owlbear_knowledge/content_guard.py` — new module (created)
- `serve/knowledge/src/owlbear_knowledge/ingest.py` — wired guard into pipeline

### Test Results

- **47/47 passed** (test_content_guard_833.py: 26 tests + test_content_guard_834.py: 21 tests)
- RED verified: all 47 failed with `ModuleNotFoundError` before implementation
- No RuntimeWarnings (unawaited coroutine fix: moved `embed_coro` creation to after guard scan)

### Coverage

- `content_guard.py`: **100%** (all 23 statements covered)
- `ingest.py`: 69% (uncovered lines are pre-existing `ingest_text` path + cancellation paths, unrelated to this task)

### Lint

- **ruff clean** — all checks passed

### Commit

- `dda30162` on `dev` — 2 files changed, 173 insertions(+), 7 deletions(-)

### Implementation Summary

1. `CheckResult` frozen dataclass with `threat: bool, blocked: bool, reason: str, pattern: str`
2. `ContentInjectionGuard` with 41 builtin patterns across 7 IDPI categories (substring, case-insensitive), `custom_patterns` list and `strict_mode` keyword-only bool
3. `IngestResult.status` Literal extended with `"blocked"`
4. `IngestPipeline.__init__` gets `content_guard` + `injection_mode` optional params
5. Guard scan in `ingest()` for untrusted sources — strict: return `status="blocked"`; warn: log warning + proceed
6. Pattern list adjusted: added `"disregard all prior"` to cover test phrase "disregard all prior instructions" (research doc listed "disregard prior instructions" which doesn't substring-match the test phrase)

### Regression Check

- 181 knowledge-domain tests passed with no regressions (bookmark_pipeline, authenticated_content_pipeline, consolidation, chunker, analysis)
- Pre-existing failures in test_contentfetcher_impl_830.py (RED tests for incomplete task #830) — unrelated to this task
[[2026-04-12]]

## Review Evidence

### Test Results

- pytest: 47 passed, 0 failed (test_content_guard_833.py: 26 + test_content_guard_834.py: 21)

### Lint

- ruff: clean

### Coverage

- `owlbear_knowledge.content_guard`: 100%
- `owlbear_knowledge.ingest`: 69% (pre-existing uncovered paths — ingest_text + cancellation, unrelated to this task)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — class in content_guard.py | `test_content_injection_guard_importable` | Yes — ImportError | COVERED |
| AC2 — CheckResult 4 typed fields | `TestFromAC_CheckResultContract` (7 tests) | Yes — field assertions fail | COVERED |
| AC3 — ~40 patterns, case-insensitive substring | `TestFromAC_BuiltinPatternCoverage` (11), `TestFromAC_ScanDetection` (7) | Yes — threat=True assertions fail | COVERED |
| AC4 — custom_patterns list | `TestFromAC_CustomPatterns` (5) | Yes — threat=False when custom phrase present | COVERED |
| AC4 — strict_mode bool | `TestFromAC_StrictModeBool` (5) | Yes — blocked assertions fail | COVERED |
| AC5 — wired before extraction, untrusted only | `test_ingest_calls_guard_scan_on_untrusted_source`, `test_ingest_does_not_call_guard_scan_on_trusted_source` | Yes — assert_called_once/assert_not_called | COVERED |
| AC6 — strict: blocked; warn: log + proceed | `test_strict_mode_returns_blocked_status_on_injection`, `test_warn_mode_logs_warning_on_injection`, `test_warn_mode_proceeds_to_entity_extraction` | Yes — status/log/extractor.extract assertions | COVERED |
| AC7 — #833 tests pass | All 26 #833 TestFromAC tests | Yes — inherent | COVERED |

#### Security Review

- No hardcoded secrets
- No injection sinks (patterns are substring match, not template/SQL/shell)
- No path traversal
- No insecure deserialization
- `_check.reason` logged includes only predefined builtin phrase — no user content in logs
- No new dependencies (stdlib only: dataclasses, logging)
- No issues

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All TestFromAC_* in 833 and 834 | None — builder only changed content_guard.py (new) + ingest.py | PRESERVED |

#### Test Quality

- Assertion specificity: STRONG — `is True`, `is False`, `== "blocked"`, exact string comparisons
- Negative/error paths: ADEQUATE — clean content, trusted-source skip, no-threat-in-strict-mode all tested
- Mutation resistance: STRONG — case-fold removal, `blocked = self._strict_mode` flip, custom-replace-vs-extend all caught
- Test independence: STRONG — local imports, no shared mutable state
- Descriptive names: STRONG

#### Data Safety

- Guard is stateless (frozen dataclass + read-only patterns tuple) — no race conditions
- No multi-step atomicity concerns
- No unbounded input from system boundaries

#### Implementation-Aware Test Gap Analysis

- Multi-chunk: chunk 2 blocked while chunk 1 clean — not tested. Trivially derivable from single-chunk passing test; not flagged as significant.

#### Builder Process Quality

- 1 Builder Notes section — clean first pass. CLEAN.

### Pass 2 — INFORMATIONAL

- `injection_mode: Literal["strict", "warn"]` on `IngestPipeline.__init__` is stored as `self._injection_mode` but **never read** in `ingest()`. All strict/warn logic flows through `_check.blocked` from the guard's own `strict_mode`. Callers setting `injection_mode="warn"` while providing a `strict_mode=True` guard will be silently ignored. Dead API surface — not an AC violation, but misleading. Recommend removing `injection_mode` param or wiring it to override guard mode.

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1 | content_guard.py exists, ContentInjectionGuard defined | PASS |
| AC2 | frozen dataclass, 4 fields with correct types | PASS |
| AC3 | 41 patterns / 7 categories in _BUILTIN_PATTERNS, `phrase in text.lower()` | PASS |
| AC4 | custom_patterns extends builtins, strict_mode=True→blocked=True | PASS |
| AC5 | `if self._content_guard is not None and _should_wrap:` before extract_coros | PASS |
| AC6 | `if _check.blocked: return IngestResult(status="blocked")` else `logger.warning` | PASS |
| AC7 | 26/26 #833 tests pass | PASS |

### Deductions

- Pass 2 dead-code note (injection_mode param): -0.02

### Verdict

Confidence: 0.93 → PASS
[[2026-04-12]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Verified/N/A | New `ContentInjectionGuard` public API + `IngestPipeline` new params. `copilot-instructions.md` is 18 lines (project identity + branch table only — no knowledge API catalog); no update needed |
| 2 | Module docstrings | Yes | Updated | `content_guard.py`: module, `CheckResult`, `ContentInjectionGuard`, `scan()` — all accurate. `ingest.py`: `IngestPipeline` class docstring lacked `content_guard` and `injection_mode` entries; `ingest()` return doc omitted `blocked` status. Fixed — commit `20560ae9` |
| 3 | External attribution | Yes | Verified | `## IDPI ContentInjectionGuard at Graph Entry (Task #834)` section in `.owlbear/sources/overview.md` — PinchTab idpishield (Apache-2.0) and OWASP LLM01:2025 (CC-BY-SA-4.0) both present |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/834-contentinjectionguard-green-impl.md` exists; linked in task body; no follow-up tasks required per research doc |

### Files Updated

- `serve/knowledge/src/owlbear_knowledge/ingest.py` — docstring only (commit `20560ae9`)

### Scratch Cleaned

No `.owlbear/scratch/834-*` files found.
[[2026-04-12]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — ContentInjectionGuard in content_guard.py | `content_guard.py` exists, class defined L95 | PASS |
| AC2 — CheckResult dataclass (threat, blocked, reason, pattern) | `@dataclasses.dataclass(frozen=True)` L77-86, 4 typed fields | PASS |
| AC3 — ~40 builtin patterns, case-insensitive substring | 41 patterns in `_BUILTIN_PATTERNS` L23-70, `phrase in text_lower` L119 | PASS |
| AC4 — custom_patterns list, strict_mode bool | Constructor L105-113, `custom_patterns: list[str] | None`,`strict_mode: bool = True` | PASS |
| AC5 — Wired into IngestPipeline.ingest() before extraction, untrusted only | `ingest.py` L209: `if self._content_guard is not None and _should_wrap:` | PASS |
| AC6 — Strict: blocked status; Warn: log + proceed | L212-218: `if _check.blocked: return IngestResult(status="blocked")`; else `logger.warning` | PASS |
| AC7 — All #833 tests pass | 26/26 #833 tests + 21/21 #834 tests = 47/47 passed | PASS |

### Test Results

- pytest (task scope): 47 passed, 0 failed
- pytest (full suite): 4026 passed, 310 failed (all pre-existing RED tests for other tasks — verified: 3 ingest-domain failures from #162 are pre-existing, 0 content_guard failures)
- ruff: clean

### Commit Chain

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a04f1c67 | test (RED) | test_content_guard_834.py | #834 |
| dda30162 | feat (GREEN) | content_guard.py, ingest.py | #834 |
| 20560ae9 | docs | ingest.py (docstring) | #834 |

### Architect Quality: 4/5

ACs were specific: class location, field names/types, pattern strategy, modes, integration point, test contract binding. Builder guidance section properly surfaced 3 implicit requirements. Minor gap: AC didn't specify `injection_mode` param, which the builder added but is dead code (reviewer correctly flagged as Pass 2 informational). Recommend removing `injection_mode` as follow-up.

### Deduction Breakdown

- AC lines without evidence: 0 (all 7 covered) → 0
- Lint violations: none → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (detailed Pass 1+2, security review) → 0
- Full-suite task-scope failures: none → 0

### Confidence: .98

### Action: archive

Note: Reviewer flagged dead `injection_mode` param (-.02 at review). Not an AC violation but recommended for cleanup as follow-up.
