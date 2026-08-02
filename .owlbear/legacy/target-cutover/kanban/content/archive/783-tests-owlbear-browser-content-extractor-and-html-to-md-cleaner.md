---
id: 783
title: Tests — owlbear_browser content extractor and HTML-to-MD cleaner
status: archived
priority: medium
created: '2026-04-10T12:30:44.046816+00:00'
updated: '2026-04-13T03:04:57.608243+00:00'
tags:
- phase-1
- scope:browser
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify content extraction from HTML string returns structured text
- Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved)
- Tests verify noise removal (nav bars, footers, cookie banners, script tags stripped)
- File: `tests/test_browser_content_775.py`

## Context
- WS-C: Browser Packages
- Scope item 1 (part 2) from #775

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task covering browser content extraction/cleaning |
| Interface clarity | PASS | AC specifies three testable behaviors + target file |
| Dependency correctness | PASS | No deps listed; correct — tests run against existing `owlbear_browser` modules |
| Module layering | PASS | Tests import from public `owlbear_browser.extractor` and `owlbear_browser.cleaner` |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Three focused test concerns, no speculative coverage |
| Premise challenge | PASS | Tests verify public API stability of cleaner/extractor — necessary for regression safety |
| Pattern consistency | PASS | File follows `tests/test_{slug}_{parent_id}.py` pattern; test classes use `TestFromAC_*` naming |
| Security surface | PASS | Test-only task, no new system boundaries |
| Single domain | PASS | Browser domain only |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Tests verify content extraction from HTML string returns structured text | Verifiable — maps to `TestFromAC_ContentExtractor` (8 tests on `extract()`) | None |
| Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved) | Verifiable — maps to `TestFromAC_HTMLCleaner` (10 tests on `clean()`) | None |
| Tests verify noise removal (nav bars, footers, cookie banners, script tags stripped) | Verifiable — maps to `TestFromAC_NoiseRemoval` (8 tests on `clean()`/`strip_noise()`) | None |
| File: `tests/test_browser_content_775.py` | File exists with 60+ tests covering all AC items | None |

### Architecture Notes

- Test file also contains tests for downstream tasks #788 and #828 (trafilatura fallback, SharePoint patterns, content normalization). These were added by the test-writer in merged RED-phase passes — no concern.
- Minor overlap with `tests/test_cleaner_756.py` (header/aside stripping, SharePoint patterns). The #756 tests are complementary (advanced patterns) not duplicative — acceptable.
- Source modules `cleaner.py` (238 lines) and `extractor.py` (73 lines) are implemented and match the test expectations.

### Challenge Results

- Challenger: FALLBACK — challenger agent not available in agent pool
- Architect response: proceeded without challenge; confidence in verdict is high (.93) due to pre-existing tests and implementations matching AC

### Verdict: APPROVE
### Action Taken: Advanced to todo. All AC verifiable, architecture sound, pass-through tag `type:test` present.
[[2026-04-12]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no new tests applicable.
- Passing through to builder.

**Verification:** `tests/test_browser_content_775.py` already exists — 80 tests, all PASS.

**AC coverage (confirmed):**
| AC Line | Coverage |
|---------|---------|
| Tests verify content extraction from HTML string returns structured text | `TestFromAC_ContentExtractor` — 8 tests on `extract()` |
| Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved) | `TestFromAC_HTMLCleaner` — 10 tests on `clean()` |
| Tests verify noise removal (nav bars, footers, cookie banners, script tags stripped) | `TestFromAC_NoiseRemoval` — 8 tests on `clean()`/`strip_noise()` |

The file also contains tests for tasks #788 and #828 merged in prior RED-phase passes. `extractor.py` and `cleaner.py` are fully implemented — tests pass correctly against the live modules.
[[2026-04-12]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
[[2026-04-13]]
## Review Evidence

### Tests
pytest: **80 passed, 0 failed, 0 skipped** — run independently via quality-runner.

### Lint
ruff: **clean** — 0 violations in `tests/test_browser_content_775.py`.

### Coverage
- `owlbear_browser.extractor`: **100%**
- `owlbear_browser.cleaner`: **100%**

### AC Compliance

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| Tests verify content extraction from HTML string returns structured text | `TestFromAC_ContentExtractor` (8 tests) — `test_extract_returns_string`, `test_extract_returns_main_content_text`, `test_extract_paragraph_text_preserved`, noise exclusion, TypeError | Yes — presence/absence checks on exact strings, TypeError assertion | COVERED |
| Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved) | `TestFromAC_HTMLCleaner` (10 tests) — h1/h2 exact markers, bullet regex, numbered regex, hyperlink URL/text, nested headings; table test checks content only | Headings/lists/links: Yes. Table: LAX — content words checked but not `|` pipe structure via `clean()` directly; compensated by `TestFromAC_HtmlToMarkdown.test_html_to_markdown_preserves_table_structure` which checks `|` | COVERED (LAX note on table) |
| Tests verify noise removal (nav bars, footers, cookie banners, script tags stripped) | `TestFromAC_NoiseRemoval` (8 tests) — nav, footer, script, style, cookie-banner by class, cookie-consent by id, surrounding-content preserved, combined all-noise | Yes — positive and negative assertions on exact strings | COVERED |
| File: `tests/test_browser_content_775.py` | File exists | n/a | COVERED |

### Security (5.1)
Test-only task — no new system boundaries, no injection surfaces, no secrets, no deserialization concerns. Clean.

### TestFromAC Integrity (5.2)
Builder passed through (no code changes). Zero modifications to any `TestFromAC_*` method. Not applicable.

### Test Quality (5.3)
- **Assertion specificity**: STRONG — assertions check exact string content ("# Page Title", "https://example.com"), regex patterns for bullet/numbered markers, negative assertions for stripped noise. No bare `assert result` patterns.
- **Negative/error-path coverage**: STRONG — noise tests verify absent strings; `test_extract_non_string_raises_type_error` covers the error path; empty input tested throughout.
- **Manual mutation reasoning**: Flipping html_to_markdown heading logic would fail `"# Page Title" in result`. Removing nav stripping would fail `"Home | About | Contact" not in result`. Mutations caught.
- **Test independence**: STRONG — each test constructs own HTML fixture; no shared mutable state.
- **Descriptive names**: STRONG — all names follow `test_{verb}_{behavior}` pattern with docstrings.
- **LAX note**: `TestFromAC_HTMLCleaner.test_clean_preserves_table_cell_content` checks cell text presence only — does not verify markdown `|` pipe structure via `clean()` directly. Compensating coverage exists in `TestFromAC_HtmlToMarkdown.test_html_to_markdown_preserves_table_structure`. No auto-fail per protocol.

### Builder Process Quality (5.7)
Single pass-through from both test-writer and builder. CLEAN — no retries, no loop.

### Deductions
- −0.02: LAX table assertion in `TestFromAC_HTMLCleaner.test_clean_preserves_table_cell_content` (not auto-fail; compensated)
- −0.01: Test-writer/builder both passed through without modification — relies on pre-existing RED-phase work from prior cycles

### Verdict
**Confidence: .97 → PASS**
→ Advanced to docs.
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only pass-through; no behavior, API, or conventions changed |
| 2 | Module docstrings | No | N/A | No Python modules created or modified by this task; builder passed through |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc produced for this task |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/783-*` files found)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Tests verify content extraction from HTML string returns structured text | TestFromAC_ContentExtractor: 8 tests (extract returns string, main content, paragraph, empty, noise-only, TypeError) | PASS |
| Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved) | TestFromAC_HTMLCleaner: 10 tests (h1, h2, ul, ol, table, hyperlink, empty, nested headings) | PASS |
| Tests verify noise removal (nav bars, footers, cookie banners, script tags stripped) | TestFromAC_NoiseRemoval: 8 tests (nav, footer, script, style, cookie-banner class, cookie-consent id, surrounding content, combined) | PASS |
| File: tests/test_browser_content_775.py | File exists, 80 tests all passing | PASS |

### Test Results
- pytest (task-scoped): 80 passed, 0 failed
- pytest (full suite): 337 failed, 4067 passed. All 337 failures are pre-existing regressions in unrelated modules (orchestrator agent renaming, schema v9 bumps, kanban API changes). Zero failures in browser content scope.
- ruff: clean, 0 violations

### Architect Quality: 4/5
AC lines are specific and directly testable. Minor gap: table preservation AC did not specify markdown pipe structure, requiring builder interpretation. Reviewer caught this as LAX with compensating test coverage. Overall solid.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 covered) = 0.00
- Lint violations: none = 0.00
- AC quality 4/5 (above threshold of 3): 0.00
- Reviewer evidence section: present, detailed, PASS at .97 = 0.00
- Full-suite failures in task scope: none = 0.00

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 73ed9072 | test | tests/test_browser_content_775.py | #788 (initial RED) |
| fa39b232 | docs | tests/test_browser_content_775.py | #783 (docstring fix) |
| b0132b94 | test | tests/test_browser_content_775.py | #828 (SharePoint tests) |
| 79c82820 | chore | kanban task + activity | #783 (audit) |