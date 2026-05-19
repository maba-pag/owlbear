---
id: 829
title: Impl — SharePoint normalization + idempotent output for cleaner
status: archived
priority: needed
created: '2026-04-11T01:39:05.631411+00:00'
updated: '2026-04-12T13:32:29.904244+00:00'
tags:
- phase-1
- scope:browser
parent: 775
depends_on:
- 828
- 788
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. Extend owlbear_browser.cleaner with:

1. SharePoint-specific boilerplate handling in strip_noise(): breadcrumb containers, ms-* web-part chrome, dynamic timestamp elements, user avatar containers
2. Content normalization in html_to_markdown(): whitespace collapsing, line ending normalization, HTML entity decoding, zero-width character removal
3. Verify idempotent output through both trafilatura and fallback paths

AC:

- strip_noise() removes SharePoint-specific patterns (breadcrumbs, web-part wrappers, timestamps)
- html_to_markdown() output has normalized whitespace and no encoding artifacts
- Same HTML input produces identical markdown output on repeated extract_content() calls
- All #828 tests pass
- Files: serve/browser/src/owlbear_browser/cleaner.py, serve/browser/src/owlbear_browser/extractor.py

Context: GREEN partner for #828. Maps to data-person voice Gaps 1-2 and brief D1.
Research: .owlbear/research/756-html-markdown-cleaner-tests.md §3.2
[[2026-04-12]]

## Research

- Research doc: .owlbear/research/829-sharepoint-normalization-cleaner.md
- Sources: 10 studied, 6 high-relevance
- Recommendation: Option A — add specific Fluent UI class/id patterns + zero-width char stripping (confidence: .82)
- Key findings:
  1. Most AC items already implemented (clean(), _normalize_content(), basic SharePoint classes)
  2. Missing: ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField classes; SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow IDs
  3. Critical gap: zero-width chars (U+200B/200C/200D/FEFF) not stripped — survive both _normalize_content() and compute_content_hash()
  4. extract_content() idempotency AC satisfied trivially (same input → same output) — normalization not needed in that path
  5. SharePoint CSS class instability confirmed (sp-dev-docs#6380) — Fluent UI v8 ms-* prefixes are the stable target
- Follow-up tasks created: none (implementation is mechanical, no decomposition needed)
- Decision requests: none
[[2026-04-12]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extends cleaner with SharePoint patterns + normalization fixes. One cohesive responsibility |
| Interface clarity | FAIL | AC misattributes normalization to `html_to_markdown()` (belongs in `_normalize_content()`); omits zero-width char stripping; omits user avatar patterns from AC line 1; includes `extractor.py` in file list despite no changes needed |
| Dependency correctness | PASS | #828 (RED tests) and #788 (base implementation) are both valid dependencies. Neither is done yet — correct for backlog stage |
| Module layering | PASS | All changes within `owlbear_browser` package. No cross-namespace deps |
| TDD compliance | PASS | #828 is the RED-phase partner |
| KISS/YAGNI | PASS | Research recommends Option A (exact class matching) — minimal, follows existing pattern |
| Premise challenge | PASS | Research §3.1 confirms gaps exist (breadcrumbs, personas, timestamps, zero-width chars) |
| Pattern consistency | PASS | Adds strings to existing `_NOISE_CLASSES`/`_NOISE_IDS` frozensets. Extends `_normalize_content()` regex/replace chain |
| Security surface | PASS | No new boundaries. Same lxml HTML parsing. Output is plain markdown string |
| Single domain | PASS | Browser domain only |

### AC Defects Found

| AC Line | Issue | Severity |
|---------|-------|----------|
| "strip_noise() removes SharePoint-specific patterns (breadcrumbs, web-part wrappers, timestamps)" | Omits user avatar containers (`ms-Persona`, `ms-LivePersona`) mentioned in body item 1 | Medium |
| "html_to_markdown() output has normalized whitespace and no encoding artifacts" | Wrong function — normalization is in `_normalize_content()` called by `clean()`, not in `html_to_markdown()`. Builder would modify wrong function | High |
| "html_to_markdown() output has normalized whitespace and no encoding artifacts" | Missing zero-width char stripping requirement (U+200B/200C/200D/FEFF) — the critical gap from research §3.3 | High |
| "Same HTML input produces identical markdown output on repeated extract_content() calls" | Trivially true (deterministic functions). Not wrong but adds no value — research finding #4 confirms | Low |
| "Files: cleaner.py, extractor.py" | Research confirms no changes to `extractor.py`. Listing it invites unnecessary modification | Medium |

### Binding AC (replaces original on next pass)

1. **strip_noise()** — `_NOISE_CLASSES` adds: `ms-Breadcrumb`, `ms-Persona`, `ms-LivePersona`, `ms-DateTimeField`. `_NOISE_IDS` adds: `SuiteNavPlaceHolder`, `O365_NavHeader`, `s4-ribbonrow`. Existing patterns preserved.
2. **_normalize_content()** — additionally strips `\r` characters and zero-width Unicode (U+200B, U+200C, U+200D, U+FEFF) before existing whitespace normalization.
3. **Idempotent output** — `clean(html)` called twice on identical input produces byte-identical output (verified by test). `extract_content()` on identical input produces identical output (verified by test).
4. All #828 tests pass.
5. File: `serve/browser/src/owlbear_browser/cleaner.py` only — no changes to `extractor.py`.

### Challenge Results

- Challenger: skipped (REFINE verdict — optional per protocol)
- Self-challenge: Research is thorough (.82 confidence). Implementation is mechanical. Only issue is AC precision, not design.

### Verdict: REFINE

### Action Taken: AC has structural defects (wrong function attribution, missing zero-width requirement, missing avatar patterns). Binding AC provided above. Task stays in backlog for re-processing with corrected AC. Task remains claimed — orchestrator should release stale claim before re-dispatch

[[2026-04-12]]

## Architecture Review (Pass 2 — Retry after REFINE)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extends cleaner with SharePoint patterns + normalization fixes. One cohesive responsibility |
| Interface clarity | PASS (was FAIL) | Binding AC from pass 1 corrects all defects: correct function attribution (`_normalize_content` not `html_to_markdown`), complete SharePoint pattern list incl. avatars, zero-width chars specified, `extractor.py` removed from file scope |
| Dependency correctness | PASS | #828 (research) — RED-phase test partner, correct dep. #788 (review/blocked) — base implementation, correct dep. Neither done yet — correct for backlog stage |
| Module layering | PASS | All changes within `owlbear_browser` package. No cross-namespace deps |
| TDD compliance | PASS | #828 is the RED-phase partner |
| KISS/YAGNI | PASS | Option A (exact class matching) — minimal, follows existing `_NOISE_CLASSES`/`_NOISE_IDS` frozenset pattern |
| Premise challenge | PASS | Research §3.1 confirms gaps exist; codebase verified — no `ms-Breadcrumb`, `ms-Persona`, `ms-LivePersona`, `ms-DateTimeField` in current `_NOISE_CLASSES`; no zero-width handling in `_normalize_content()` |
| Pattern consistency | PASS | Adds strings to existing frozensets. Extends `_normalize_content()` replace/regex chain. Same mechanism as existing noise removal |
| Security surface | PASS | No new boundaries. Same lxml HTML parsing. Output is plain markdown string |
| Single domain | PASS | Browser domain only |

### Binding AC (from pass 1 — confirmed as the authoritative AC)

The binding AC in the prior Architecture Review section supersedes the original AC block at the top of the body. Builder must follow these 5 lines:

1. **strip_noise()** — `_NOISE_CLASSES` adds: `ms-Breadcrumb`, `ms-Persona`, `ms-LivePersona`, `ms-DateTimeField`. `_NOISE_IDS` adds: `SuiteNavPlaceHolder`, `O365_NavHeader`, `s4-ribbonrow`. Existing patterns preserved.
2. **_normalize_content()** — additionally strips `\r` characters and zero-width Unicode (U+200B, U+200C, U+200D, U+FEFF) before existing whitespace normalization.
3. **Idempotent output** — `clean(html)` called twice on identical input produces byte-identical output (verified by test). `extract_content()` on identical input produces identical output (verified by test).
4. All #828 tests pass.
5. File: `serve/browser/src/owlbear_browser/cleaner.py` only — no changes to `extractor.py`.

### Codebase Evidence

- `cleaner.py` L22-36: `_NOISE_CLASSES` frozenset — currently has `ms-header`, `ms-commandBar`, `ms-commandbar`, `ms-pageEditBar`. Binding AC adds 4 more strings.
- `cleaner.py` L37-44: `_NOISE_IDS` frozenset — currently has `SuiteNavWrapper`, `ms-site-actions`. Binding AC adds 3 more strings.
- `cleaner.py` L198-214: `_normalize_content()` — handles `\u00a0`, space collapsing, blank-line collapsing. Binding AC adds `\r` stripping and zero-width Unicode removal before existing chain.
- `extractor.py`: imports `strip_noise`, `html_to_markdown` from cleaner. No modification needed — confirmed by research §3.4.

### Challenge Results

- Challenger: FALLBACK — challenger agent not in available agent roster
- Self-challenge: (1) Can builder implement without interpretation? YES — binding AC specifies exact class names, Unicode codepoints, and target function. (2) Architecture risk? NONE — string additions to existing frozensets + regex extension. (3) Missing deps? None. (4) Conflict with #788? No — #788 established the base implementation; #829 extends it.

### Verdict: APPROVE

### Action Taken: All pass-1 AC defects resolved by binding AC. Interface clarity now PASS. Advanced to todo. Builder follows binding AC lines 1–5 (in Architecture Review section), not the original AC block

[[2026-04-12]]

## Test-Writer Notes

- Test file: tests/test_sharepoint_normalization_829.py
- Classes: TestFromAC_StripNoiseSharePointClasses, TestFromAC_StripNoiseSharePointIds, TestFromAC_NormalizeContentZeroWidth, TestFromAC_IdempotentOutput
- Tests per category: happy 14, edge 6, error 0, boundary 5
- Total: 25 tests, all FAIL
- ruff: clean

**AC coverage:**

| AC Line | Tests |
|---------|-------|
| AC1 — _NOISE_CLASSES: ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField | 8 tests in TestFromAC_StripNoiseSharePointClasses |
| AC1 — _NOISE_IDS: SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow | 5 tests in TestFromAC_StripNoiseSharePointIds |
| AC2 — zero-width Unicode (U+200B/200C/200D/FEFF) stripped | 8 tests in TestFromAC_NormalizeContentZeroWidth |
| AC2 — \\r stripped | 1 test via &#13; HTML entity (confirmed failing — lxml preserves U+000D from char refs) |
| AC3 — byte-identical output, artifact-free | 3 tests in TestFromAC_IdempotentOutput (failing via zero-width assertions) |

**Note on AC3 extract_content idempotency:** `extract_content(html, url) == extract_content(html, url)` is trivially true for any deterministic function — no RED-phase test possible. Builder verifies during GREEN via the AC3 tests that combine hash stability with zero-width absence checks.

**Note on existing patterns (AC1 preservation):** Regression tests for ms-header, SuiteNavWrapper, etc. were intentionally excluded — those already pass (existing behavior). Builder must not break them.

**Commit:** 19069337 — only tests/test_sharepoint_normalization_829.py staged.
[[2026-04-12]]

## Builder Notes

### Files Changed

- None — implementation was fully delivered by #828 builder (commit `ec06a532`).
- Test file `tests/test_sharepoint_normalization_829.py` committed by test-writer (commit `19069337`).

### What Was Already Done (by #828)

`serve/browser/src/owlbear_browser/cleaner.py` already contains:

- `_NOISE_CLASSES`: `ms-Breadcrumb`, `ms-Persona`, `ms-LivePersona`, `ms-DateTimeField`
- `_NOISE_IDS`: `SuiteNavPlaceHolder`, `O365_NavHeader`, `s4-ribbonrow`
- `_normalize_content()`: strips U+200B/200C/200D/FEFF and `\r` before whitespace normalization

### Test Results

- `tests/test_sharepoint_normalization_829.py`: 25/25 passed (all TestFromAC_* classes)
  - TestFromAC_StripNoiseSharePointClasses: 8 passed
  - TestFromAC_StripNoiseSharePointIds: 5 passed
  - TestFromAC_NormalizeContentZeroWidth: 8 passed (incl. `\r` via &#13;)
  - TestFromAC_IdempotentOutput: 4 passed

### Coverage

- `cleaner.py` with both test files (829 + 756): **92.4%** (107/111 statements, ≥ 90% threshold met)

### Lint

- `ruff check cleaner.py tests/test_sharepoint_normalization_829.py`: **clean**

### AC Verification

1. ✅ `_NOISE_CLASSES` adds ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField
2. ✅ `_NOISE_IDS` adds SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow
3. ✅ `_normalize_content()` strips zero-width Unicode + `\r`
4. ✅ All 25 #828/829 tests pass
5. ✅ Only `cleaner.py` modified (no `extractor.py` changes)
[[2026-04-12]]

## Review Evidence

### Test Results

- pytest (test_sharepoint_normalization_829.py + test_cleaner_756.py): **63 passed, 0 failed**
- Quality-Runner ran independently — builder self-report not relied upon.

### Lint

clean: true (ruff, both cleaner.py and test file)

### Coverage

owlbear_browser.cleaner: **96%** (threshold: 90% — met)

### Source Control

- `cleaner.py`: present in changed files (uncommitted #828 changes)
- `test_sharepoint_normalization_829.py`: NOT in changed files — committed in 19069337 (test-writer commit). Builder made no further modifications.

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Tests | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — _NOISE_CLASSES: ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField | TestFromAC_StripNoiseSharePointClasses (8 tests) | YES — each asserts specific text absent after strip_noise(); would remain in output if class missing | COVERED |
| AC1 — _NOISE_IDS: SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow | TestFromAC_StripNoiseSharePointIds (5 tests) | YES — asserts specific text absent; present if ID missing from frozenset | COVERED |
| AC2 — zero-width Unicode (U+200B/200C/200D/FEFF) stripped | TestFromAC_NormalizeContentZeroWidth (8 tests) | YES — `assert "\u200b" not in result` etc. would fail if chars not stripped | COVERED |
| AC2 — \r stripped | test_clean_strips_cr_via_html_entity | YES — `assert "\r" not in result` | COVERED |
| AC3 — clean() byte-identical on repeated calls + zero-width absent | TestFromAC_IdempotentOutput (3 tests) | YES — hash comparison fails on non-determinism; zero-width assertions fail if not stripped | COVERED |
| AC4 — All #828 tests pass | All 25 TestFromAC_* tests | YES — entire test file is the #828/828 RED-phase artifact | COVERED |
| AC5 — only cleaner.py modified | Builder notes + get_changed_files | Builder made no changes; test file committed unchanged | COVERED |

Note: AC3 extract_content() idempotency sub-claim has no direct test. Test-writer explicitly documented this is trivially true (deterministic pure function) and unverifiable at RED phase. Not a gap — acknowledged and justified.

#### 5.1 Security

- No new external boundaries or inputs
- Same lxml HTML parsing (established library)
- No hardcoded secrets, no injection surfaces, no path ops
- Pure string replacement/regex in _normalize_content()
- **No issues**

#### 5.2 Test Integrity — TestFromAC Comparison

Builder claims no file modifications (confirmed by get_changed_files: test file not in changed list). TestFromAC_ classes are unchanged from test-writer commit 19069337. **All PRESERVED.**

Minor note: Builder self-report lists TestFromAC_NormalizeContentZeroWidth=8, TestFromAC_IdempotentOutput=4 — actual file has 9+3=12. Counting error in notes only; test count is 25 per quality-runner.

#### 5.3 Test Quality

- **Assertion specificity**: STRONG — `assert "specific text" not in result` / `assert "expected text" in result`. No lazy `assert result` patterns.
- **Negative/error-path**: ADEQUATE — functions are pure transforms with no error paths to cover; omission is correct.
- **Mutation resistance**: STRONG — removing any frozenset entry fails the corresponding class/ID test; removing zero-width strip fails eight tests.
- **Test independence**: STRONG — each test constructs its own HTML literal.
- **Test names**: STRONG — all names are descriptive and specific.

#### 5.4 Data Safety

No LLM output persistence, no shared mutable state, no multi-step atomicity requirements. **No issues.**

#### 5.5 Implementation-Aware Test Gap Analysis

- `_remove_cookie_elements()` handles multi-class elements — covered by test_element_with_multiple_classes_including_ms_persona_is_stripped (line ~140).
- Existing patterns (ms-header, SuiteNavWrapper) not regression-tested here — intentional per test-writer; test_cleaner_756.py covers base behavior (38 tests, all pass).
- `html_to_markdown()` and `strip_noise()` empty-string guards have no new code paths — covered by existing test_cleaner_756 tests. No gap.

#### 5.6 Necessity

No new dependencies. N/A.

#### 5.7 Builder Process Quality

One `## Builder Notes` section. Builder correctly identified implementation was pre-delivered by #828. CLEAN.

---

### AC Compliance Table

| AC Line | Implementation Evidence | Test Evidence | Status |
|---------|------------------------|---------------|--------|
| AC1 _NOISE_CLASSES | cleaner.py L25-36: ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField present in frozenset | 8 tests pass | PASS |
| AC1 _NOISE_IDS | cleaner.py L37-44: SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow present in frozenset | 5 tests pass | PASS |
| AC2 zero-width stripping | cleaner.py _normalize_content(): `text.replace("\u200b","")..."\u200c"..."\u200d"..."\ufeff"` | 8 zero-width tests pass + 1 CR test pass | PASS |
| AC2 \r stripping | cleaner.py _normalize_content(): `text.replace("\r", "")` | test_clean_strips_cr_via_html_entity passes | PASS |
| AC3 idempotent output | Deterministic call chain clean()→strip_noise()→html_to_markdown()→_normalize_content() | 3 hash/artifact tests pass | PASS |
| AC4 all #828 tests pass | N/A (test file AC) | 25/25 TestFromAC_* tests pass | PASS |
| AC5 only cleaner.py | get_changed_files: test file committed, no builder changes | N/A | PASS |

---

### Deductions

- None (no FAIL-triggering findings)

### Verdict

**PASS — confidence .96**

Deductions: 0. All binding AC lines covered by passing tests. Implementation matches binding AC exactly. Lint clean. Coverage 96% on target module (≥90% threshold met). TestFromAC_ tests unmodified. No security issues. Builder process clean.
[[2026-04-12]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | All changes are internal to existing public API (`strip_noise`, `_normalize_content`). No new public functions or signatures. `copilot-instructions.md` covers project structure only — no browser/cleaner entry exists; no update needed. |
| 2 | Module docstrings | Yes | Updated | `strip_noise()` docstring omitted SharePoint boilerplate (said "cookie-banner/consent divs" only). Updated to include breadcrumbs, web-part chrome, timestamp fields, user avatar containers (ms-* Fluent UI classes and SP IDs). `_normalize_content()`, `html_to_markdown()`, `clean()` docstrings accurate — verified. Module-level docstring already correct. |
| 3 | External attribution | Yes | Verified | `sources/overview.md` §"SharePoint Normalization + Idempotent Output (Task #829)" present (lines 3918–3924) — sp-dev-docs#6380 and Fluent UI v8 catalog attributed. Already complete. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/829-sharepoint-normalization-cleaner.md` exists. Linked in task body under `## Research`. |

### Files Updated

- `serve/browser/src/owlbear_browser/cleaner.py` — `strip_noise()` docstring corrected (commit `3d25412c`)
  - 63 tests pass post-commit (test_sharepoint_normalization_829.py + test_cleaner_756.py)

### Scratch Files Cleaned

- None (no `.owlbear/scratch/829-*` files found)
[[2026-04-12]]

## Audit

### AC Verification (Binding AC from Arch Review Pass 2)

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 _NOISE_CLASSES: ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField | cleaner.py L34-37: all 4 present in frozenset; 8 tests pass | PASS |
| AC1 _NOISE_IDS: SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow | cleaner.py L45-47: all 3 present; 5 tests pass | PASS |
| AC2 zero-width + \r stripping | cleaner.py L221-222: replace chain for U+200B/200C/200D/FEFF and \r; 9 tests pass | PASS |
| AC3 idempotent output | Deterministic call chain; 3 hash/artifact tests pass | PASS |
| AC4 all #828 tests pass | 25/25 TestFromAC_* pass | PASS |
| AC5 only cleaner.py modified | Commits ec06a532, 3d25412c, 19069337 — no extractor.py changes | PASS |

### Test Results

- pytest (task scope): 63 passed, 0 failed (test_sharepoint_normalization_829.py + test_cleaner_756.py)
- pytest (full suite): 4025 passed, 311 failed — all failures pre-existing, unrelated to #829 (fetcher module not implemented, tool annotations, kanban/knowledge/orchestrator modules)
- ruff: clean

### Architect Quality: 2/5

Original AC had 2 High defects (wrong function `html_to_markdown` vs `_normalize_content`, missing zero-width char requirement) and 2 Medium defects (missing avatar patterns from body item 1, `extractor.py` in file scope despite no changes needed). Architecture review REFINE pass caught and corrected all — binding AC was excellent (5/5). But the original AC would have sent the builder to the wrong function. Follow-up task needed for architect calibration.

### Deduction Breakdown

- Starting: 1.00
- AC quality ≤ 3 (score 2): -.03
- Reviewer evidence: present, detailed, PASS at .96 — no deduction
- Lint: clean — no deduction
- Task-scope failures: 0 — no deduction

### Confidence: .97

### Action: archive
