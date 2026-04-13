---
id: 783
title: Tests — owlbear_browser content extractor and HTML-to-MD cleaner
status: review
priority: needed
created: '2026-04-10T12:30:44.046816+00:00'
updated: '2026-04-12T22:40:55.064713+00:00'
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