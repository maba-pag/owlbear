---
id: 828
title: Tests — SharePoint normalization + idempotent output for cleaner
status: archived
priority: needed
created: '2026-04-11T01:38:58.499932+00:00'
updated: '2026-04-12T12:43:22.134361+00:00'
tags:
- phase-1
- type:test
- scope:browser
parent: 775
depends_on:
- 783
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for owlbear_browser.cleaner covering scope unique to #756 (not covered by #783):

1. SharePoint-specific boilerplate removal: breadcrumbs, ms-* web-part wrappers, dynamic timestamps, user avatar containers stripped from output
2. Content normalization: inconsistent whitespace collapsed, mixed line endings normalized, HTML entities decoded, zero-width characters removed
3. Idempotent output: same HTML input → same markdown output (deterministic for hashing via compute_content_hash)
4. Idempotent output through both paths: trafilatura primary path AND cleaner fallback path produce stable output

AC:

- Tests for strip_noise() handling SharePoint-specific patterns (at least 3: breadcrumbs, web-part chrome, dynamic timestamps)
- Tests for whitespace normalization in html_to_markdown() output
- Tests for deterministic output: extracted markdown hashes identically on repeated calls
- All tests FAIL at RED phase (cleaner.py has no SharePoint-specific handling yet)
- File: tests/test_browser_content_775.py (same file as #783, new test class)

Context: From #756 research — items 2-4 not covered by #783. Maps to data-person voice Gaps 1-2 and brief decision D1.
Research: .owlbear/research/756-html-markdown-cleaner-tests.md §3.2
[[2026-04-12]]

## Research

- Research doc: .owlbear/research/828-sharepoint-normalization-idempotent-tests.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Validation pass — proceed to test-writing (confidence: .88)
- Key findings:
  1. All 9 pattern categories (4 SP classes, 3 SP IDs, zero-width chars, \r) genuinely absent from current cleaner.py → all tests will FAIL at RED
  2. Neither test_cleaner_756.py nor test_browser_content_775.py covers these patterns — no duplication risk
  3. AC correction: normalization tests must target clean()/_normalize_content(), not html_to_markdown() (per #829 architect binding AC)
  4. Basic idempotency already passes; meaningful RED test is hash stability with zero-width chars in input
  5. ~12-15 tests across 3 new test classes in test_browser_content_775.py
- Follow-up tasks created: none (GREEN partner #829 already exists at todo)
- Decision requests: none

## Challenge Results

- Challenger: FALLBACK — validation pass of existing research, no new recommendation
- Confidence in original: .88
- Key challenges: self-checked test_cleaner_756.py overlap risk → confirmed no overlap
- Researcher response: N/A — no challenges received
[[2026-04-12]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | RED-phase tests for SharePoint noise removal + normalization. One cohesive test scope |
| Interface clarity | FAIL (corrected below) | AC2 targets wrong function (html_to_markdown vs clean/_normalize_content); AC3 too vague (basic idempotency passes); AC1 lacks pattern specifics |
| Dependency correctness | PASS | #783 archived (done) — established test_browser_content_775.py. Correct dependency |
| Module layering | PASS | Test file only, no production code |
| TDD compliance | PASS | This IS the RED phase |
| KISS/YAGNI | PASS | Minimal scope — tests for specific missing patterns |
| Premise challenge | PASS | Verified: ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField absent from _NOISE_CLASSES; SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow absent from_NOISE_IDS; no zero-width char handling in_normalize_content() |
| Pattern consistency | PASS | Adds new test classes to existing test_browser_content_775.py, follows TestFromAC_ naming |
| Security surface | N/A | Test file, no new boundaries |
| Single domain | PASS | Browser domain only |

### AC Defects Found

| AC Line | Issue | Severity |
|---------|-------|----------|
| "Tests for whitespace normalization in html_to_markdown() output" | Wrong function — normalization is in _normalize_content() called by clean(), not html_to_markdown(). Test-writer would test wrong function | High |
| "Tests for whitespace normalization in html_to_markdown() output" | Missing specifics: which normalization? Research identifies zero-width chars (U+200B/200C/200D/FEFF) and \r as the RED-worthy gaps | High |
| "Tests for deterministic output: extracted markdown hashes identically on repeated calls" | Too vague — basic clean() idempotency already passes. Research finding #4: meaningful RED test requires zero-width chars in input | Medium |
| "All tests FAIL at RED phase (cleaner.py has no SharePoint-specific handling yet)" | Partially wrong — cleaner.py has ms-header, ms-commandBar, ms-pageEditBar, SuiteNavWrapper, ms-site-actions. It lacks the SPECIFIC patterns in AC1 | Low |
| "breadcrumbs, web-part chrome, dynamic timestamps" | Missing user avatar containers (ms-Persona, ms-LivePersona) mentioned in body item 1 | Medium |

### Binding AC (supersedes original AC block)

Test-writer MUST follow these lines, not the original AC:

1. **strip_noise() SharePoint patterns** — Tests that strip_noise()/clean() removes elements with:
   - Classes: `ms-Breadcrumb`, `ms-Persona`, `ms-LivePersona`, `ms-DateTimeField` (at least 4 tests, one per class)
   - IDs: `SuiteNavPlaceHolder`, `O365_NavHeader`, `s4-ribbonrow` (at least 2 tests)
   - Use `<div>` wrappers, not `<nav>`/`<header>`/`<aside>` (those are already in _NOISE_TAGS and would pass trivially)
2. **_normalize_content() normalization** — Tests that clean() strips:
   - Zero-width Unicode chars: U+200B (zero-width space), U+200C (zero-width non-joiner), U+200D (zero-width joiner), U+FEFF (BOM) — at least 3 tests
   - Carriage returns (\r) — at least 1 test
3. **Deterministic output with artifacts** — clean() on HTML containing zero-width chars produces identical SHA-256 hash on repeated calls (zero-width presence ensures RED failure, since _normalize_content() does not strip them yet)
4. All tests FAIL at RED phase (these specific patterns/chars are absent from current cleaner.py)
5. File: `tests/test_browser_content_775.py` — new test class(es), coexisting with #783 classes

### Codebase Evidence

- cleaner.py L22-36: _NOISE_CLASSES has ms-header, ms-commandBar, ms-commandbar, ms-pageEditBar — missing ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField
- cleaner.py L37-44: _NOISE_IDS has SuiteNavWrapper, ms-site-actions — missing SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow
- cleaner.py L198-214: _normalize_content() handles \u00a0, space collapsing, blank-line collapsing — no zero-width char removal, no \r stripping
- test_cleaner_756.py: Tests existing SP patterns (ms-header, ms-commandBar, SuiteNavWrapper, ms-pageEditBar) — no overlap with binding AC patterns
- test_browser_content_775.py: Tests from #783/#788 — clean(), strip_noise(), html_to_markdown() API. No overlap with binding AC patterns
- test_sharepoint_normalization_829.py: #829 test-writer created 25 tests for the GREEN partner covering identical patterns. Pipeline note: #829 ran ahead of #828 (dependency violation), but the RED tests serve specification purpose and coexist

### Alignment with #829 Binding AC

# 829 architect review established binding AC specifying exact patterns (ms-Breadcrumb, ms-Persona, etc.) and zero-width chars. This #828 binding AC aligns with #829 to ensure RED tests match the GREEN implementation spec

### Challenge Results

- Challenger: FALLBACK — challenger agent not in available agent roster
- Self-challenge: (1) Are patterns genuinely absent? YES — verified in cleaner.py L22-44 and L198-214. (2) Will tests actually FAIL? YES for SP patterns and zero-width chars. (3) Overlap with existing tests? NO — test_cleaner_756.py covers different patterns. (4) Architecture risk? NONE — test file only.

### Verdict: APPROVE

### Action Taken: AC has 5 defects (wrong function target, missing specifics, vague idempotency, factual error, missing avatar patterns). Binding AC provided above corrects all defects. Advanced to todo. Test-writer follows binding AC lines 1-5, not the original AC block

[[2026-04-12]]

## Test-Writer Notes

- Test file: tests/test_browser_content_775.py (appended 3 new classes, coexisting with #783/#788 classes)
- Classes:
  - `TestFromAC_SharePointPatterns` — AC1: SP class/ID patterns
  - `TestFromAC_ContentNormalization` — AC2: zero-width chars + \r via _normalize_content()
  - `TestFromAC_DeterministicOutput` — AC3: SHA-256 hash stability with ZW-char artifacts
- Tests per category: happy 0, edge 5, error 0, boundary 9
- Total: 14 tests, all FAIL
- ruff: clean
- Commit: b0132b94

AC coverage:

| Binding AC Line | Tests |
|---|---|
| strip_noise() — ms-Breadcrumb class | test_clean_strips_ms_breadcrumb_class |
| strip_noise() — ms-Persona class | test_clean_strips_ms_persona_class |
| strip_noise() — ms-LivePersona class | test_clean_strips_ms_live_persona_class |
| strip_noise() — ms-DateTimeField class | test_clean_strips_ms_datetime_field_class |
| strip_noise() — SuiteNavPlaceHolder ID | test_clean_strips_suite_nav_placeholder_id |
| strip_noise() — O365_NavHeader ID | test_clean_strips_o365_nav_header_id |
| strip_noise() — s4-ribbonrow ID | test_clean_strips_s4_ribbonrow_id |
| _normalize_content() — U+200B | test_clean_strips_zero_width_space_u200b |
| _normalize_content() — U+200C | test_clean_strips_zero_width_nonjoiner_u200c |
| _normalize_content() — U+200D | test_clean_strips_zero_width_joiner_u200d |
| _normalize_content() — U+FEFF | test_clean_strips_bom_ufeff |
| _normalize_content() — \r | test_normalize_content_strips_carriage_returns |
| Hash stability (U+200B) | test_clean_hash_stable_after_zero_width_space_removal |
| Hash stability (all ZW chars) | test_clean_hash_stable_after_all_zero_width_chars_removed |
[[2026-04-12]]

## Builder Notes

- Files changed: `serve/browser/src/owlbear_browser/cleaner.py` (1 file, 11 insertions)
- Test results: 14/14 new tests pass; 80/80 full file; 0 regressions
- Coverage: cleaner.py 100% (111 stmts, 0 missed)
- Lint: ruff clean
- Commit: ec06a532

### Changes applied

1. `_NOISE_CLASSES` — added 4 new SharePoint patterns: `ms-Breadcrumb`, `ms-Persona`, `ms-LivePersona`, `ms-DateTimeField`
2. `_NOISE_IDS` — added 3 new SharePoint IDs: `SuiteNavPlaceHolder`, `O365_NavHeader`, `s4-ribbonrow`
3. `_normalize_content()` — added zero-width char stripping (U+200B/200C/200D/FEFF) and carriage return (`\r`) removal before existing whitespace normalization

### Evidence

- RED verified: 14 FAILED before implementation
- GREEN verified: 14 PASSED after implementation
- No `TestFromAC_*` classes modified
[[2026-04-12]]

## Review Evidence

### Test Results

pytest: 80 passed, 0 failed, 0 skipped (full test_browser_content_775.py suite)

### Lint

ruff: clean (0 violations)

### Coverage

owlbear_browser.cleaner: 100% (111 stmts, 0 missed)

### AC Compliance Table (Binding AC)

| Binding AC Line | Evidence | Status |
|---|---|---|
| strip_noise() — 4 SP class patterns (ms-Breadcrumb/Persona/LivePersona/DateTimeField), div wrappers | 4 tests in TestFromAC_SharePointPatterns; all `<div>`-wrapped; negative + preservation assertions | COVERED |
| strip_noise() — 3 SP ID patterns (SuiteNavPlaceHolder/O365_NavHeader/s4-ribbonrow), div wrappers | 3 tests in TestFromAC_SharePointPatterns; all `<div>`-wrapped | COVERED |
| _normalize_content() — U+200B/200C/200D/FEFF (≥3) + \r (≥1) | 4 zero-width + 1 \r tests in TestFromAC_ContentNormalization; `assert char not in result` | COVERED |
| Deterministic output — SHA-256 stable with ZW-char artifacts | 2 tests in TestFromAC_DeterministicOutput; `hash_clean == hash_zw`, ZW char injected into input | COVERED |
| All tests FAIL at RED | Builder confirmed 14 FAILED before GREEN; test structure requires absent behavior | COVERED |
| File: tests/test_browser_content_775.py | 3 new classes appended, #783/#788 classes preserved | COVERED |

### TestFromAC_ Integrity

All 14 methods preserved unmodified by builder (b0132b94 → ec06a532). No WEAKENED or REMOVED.

### Assertion Quality: STRONG

- Class/ID tests: negative assertions (`assert "breadcrumb" not in result`) + content preservation
- Normalization tests: direct char presence (`assert "\u200b" not in result`)
- Hash tests: `hash_clean == hash_zw` equality — would fail if stripping absent

### Security

No issues — regex patterns use re.escape(), lxml parses safely, no user-controlled path/eval surface.

### Deductions

None.

### Verdict

Confidence: .97 → PASS
[[2026-04-12]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | copilot-instructions.md contains only branch structure — no browser/cleaner API content. changed behavior is internal to _NOISE_CLASSES/_NOISE_IDS/_normalize_content(), not documented at system level |
| 2 | Module docstrings | Yes | Verified | _normalize_content() docstring correctly enumerates U+200B/200C/200D/FEFF removal and \r removal (cleaner.py L196-214). Module docstring L1-9 says "SharePoint boilerplate removed" — accurate. Pre-existing strip_noise() gap predates #828. |
| 3 | External attribution | No | N/A | Source #8 (Fluent UI v8 class catalog / github.com/Zerg00s/sp-modern-classes) accessed "via #829 research" — already attributed in sources/overview.md line ~3923 under ## SharePoint Normalization + Idempotent Output (Task #829) |
| 4 | CLI changes | No | N/A | Pure test + cleaner implementation task; no CLI surface modified |
| 5 | Research doc | Yes | Verified | .owlbear/research/828-sharepoint-normalization-idempotent-tests.md exists; linked in task body under Research section; follow-up tasks: none required (#829 GREEN partner already existed) |

### Files Updated

None — all checklist items verified accurate or not applicable.

### Scratch Files

No .owlbear/scratch/828-* files found.
[[2026-04-12]]

## Audit

### AC Verification (Binding AC)

| Binding AC Line | Evidence | Status |
|---|---|---|
| strip_noise() — 4 SP class patterns (ms-Breadcrumb/Persona/LivePersona/DateTimeField) | 4 tests in TestFromAC_SharePointPatterns; cleaner.py L34-37 | PASS |
| strip_noise() — 3 SP ID patterns (SuiteNavPlaceHolder/O365_NavHeader/s4-ribbonrow) | 3 tests in TestFromAC_SharePointPatterns; cleaner.py L46-48 | PASS |
| _normalize_content() — U+200B/200C/200D/FEFF + \r | 5 tests in TestFromAC_ContentNormalization; cleaner.py L217-218 | PASS |
| Deterministic output — SHA-256 stable with ZW-char artifacts | 2 tests in TestFromAC_DeterministicOutput | PASS |
| All tests FAIL at RED | Builder confirmed 14 FAILED pre-GREEN (commit b0132b94 then ec06a532) | PASS |
| File: tests/test_browser_content_775.py | 3 new classes appended, #783/#788 classes preserved | PASS |

### Test Results

- pytest (task-scoped): 80 passed, 0 failed (test_browser_content_775.py)
- pytest (full suite): 4022 passed, 314 failed, 8 skipped — failures are pre-existing, none in task scope
- ruff: All checks passed

### Architect Quality: 4/5

Original AC had 5 defects (wrong function target, vague idempotency, missing specifics, factual error, missing patterns). Architect self-corrected with binding AC during architecture review. Binding AC was specific, complete, and correctly guided test-writer and builder.

### Deduction Breakdown

- AC lines with no evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality score <= 3: No (-.00)
- Missing reviewer evidence section: No (-.00)
- Full-suite failures in task scope: 0 (-.00)

### Confidence: 1.00

### Action: archive

### Commits Verified

| Commit | Type | Files | Tasks |
|---|---|---|---|
| b0132b94 | test | tests/test_browser_content_775.py | #828 |
| ec06a532 | feat(browser) | serve/browser/src/owlbear_browser/cleaner.py | #828 |
