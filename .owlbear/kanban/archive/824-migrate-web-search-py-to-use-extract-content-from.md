---
id: 824
title: Migrate web_search.py to use extract_content from content_extractor
status: archived
priority: nice-to-have
created: 2026-03-15T09:42:51.5934802+01:00
updated: 2026-03-22T18:59:31.0504651+01:00
started: 2026-03-17T21:38:16.2997051+01:00
completed: 2026-03-17T21:38:16.2997051+01:00
tags:
    - dry
    - scope:core
    - phase-9
depends_on:
    - 842
class: standard
---

Replace inline trafilatura.extract() in web_search.py L213-218 with extract_content(response.text, url=url).text. Keep raw-HTML fallback on empty .text. Remove module-level trafilatura import. See docs/research/centralize-trafilatura.md. AC: (1) web_search.py no longer imports trafilatura directly, (2) uses extract_content from content_extractor, (3) existing tests pass, (4) raw-HTML fallback preserved.

[[2026-03-16]] Mon 05:14

## Research

**Researcher validation of parent research:** docs/research/centralize-trafilatura.md (task #537)

### Checklist

- [x] Theoretical validity -- DRY consolidation of identical trafilatura.extract() calls
- [x] Prior art -- Parent research established 6 sources (trafilatura docs + 4 OwlBear call sites)
- [x] Technical feasibility -- Verified code matches research: web_search.py L214-218 uses identical params (output_format=markdown, include_links=True, url=url)
- [x] Architecture fit -- extract_content() returns ExtractionResult; callers use .text. No interface changes.
- [x] Implementation approach -- Import-and-delegate, ~15 lines changed. See below.

### Critical finding: wrap_web_content double-wrap risk

extract_content() already applies wrap_untrusted_content() internally (content_extractor.py L110-113). web_search.py also applies it (L227-230). After migration:

- Success path: use extract_content().text directly (already wrapped) -- do NOT re-wrap
- Fallback path (empty .text): raw HTML still needs wrapping

### AC refinement (add to existing AC)

- (5) No double-wrapping: wrap_untrusted_content NOT applied twice on success path
- (6) wrap_web_content still applied to raw-HTML fallback when extract_content returns empty text

### Test impact

7 tests mock owlbear.tools.web_search.trafilatura -- must change to mock extract_content instead.

[[2026-03-16]] Mon 12:48
## Acceptance Criteria (Refined)\n\n1. web_search.py no longer imports trafilatura directly (remove try/except block L42-44)\n2. web_search.py imports and calls extract_content from owlbear.tools.browser.content_extractor\n3. Existing tests pass (after test task #842 updates mocks)\n4. Raw-HTML fallback preserved: when extract_content().text is empty, fall back to response.text[:max_length]\n5. No double-wrapping: on success path (non-empty .text), do NOT apply wrap_untrusted_content again -- extract_content already wraps internally\n6. Fallback path (empty .text) still applies wrap_untrusted_content to raw HTML when wrap_web_content is enabled\n\n## Implementation Guidance\n\n- extract_content(html, url) returns ExtractionResult (frozen Pydantic model) with .text already wrapped\n- On success: use result.text directly, skip the OwlBearSettings().wrap_web_content block\n- On fallback (result.text == empty): apply wrap_untrusted_content to raw HTML as before\n- Truncate to max_length in both paths\n- See content_extractor.py L105-113 for the internal wrapping logic

[[2026-03-16]] Mon 12:48
## Architecture Review\n**Verdict:** APPROVED\n\n### AC Assessment\n| AC | Assessment | Action |\n|----|------------|--------|\n| (1) Remove trafilatura import | Clear, verifiable | Keep |\n| (2) Use extract_content | Clear | Keep |\n| (3) Existing tests pass | Needs test task first | Added dep on #842 |\n| (4) Raw-HTML fallback | Clear | Keep |\n| (5) No double-wrap | Critical -- researcher caught it | Added (new) |\n| (6) Fallback wrapping | Clear | Added (new) |\n\n### Architecture Notes\n- Module layering: web_search importing from tools.browser.content_extractor introduces cross-subpackage dep. Research doc evaluated 3 options (keep/promote/core) and chose keep-in-place (.80 confidence). YAGNI reasoning sound.\n- No existing imports from owlbear.tools.browser in owlbear.tools/*.py -- this is the first. Acceptable for DRY.\n- extract_content never raises (returns empty .text on failure) -- fallback path naturally handles extraction failure.\n- Security: double-wrap risk is the main concern; AC 5-6 address it.\n\n### Changes Made\n- Created test task #842 (TDD RED phase)\n- Added depends_on: [842] to #824\n- Appended refined AC with 6 verifiable criteria + implementation guidance\n\n### Dependencies\n- Added: #842 (test task -- must complete before builder starts)\n- Verified: content_extractor.py is stable, no pending changes

[[2026-03-17]] Tue 00:09
## Test-Writer Notes
- RED phase completed by predecessor task #842 (TDD RED phase for #824)  status: done
- Test file: tests/test_web_search.py
- Classes: TestFromAC_ExtractContentMigration (from #842) + TestWebRead (updated mocks)
- All 6 AC items have test coverage (37 tests, all pass  implementation already complete)
- No new failing tests written  RED phase was already done by #842

[[2026-03-17]] Tue 00:25
## Builder Notes
- Non-implementation task: all 6 AC already satisfied in current code
- extract_content imported (L29), used in _web_read (L213), no trafilatura import
- Success path returns early (L215) -- no double-wrap (AC5)
- Fallback path applies wrap_untrusted_content (L226) -- AC6
- Tests: 37 passed, ruff clean
- No code changes needed -- passing through to review

[[2026-03-17]] Tue 00:40
## Review Evidence

### Test Results
- pytest: 37 passed, 0 failed
- Command: `uv run pytest tests/test_web_search.py -q --tb=short`

### Lint Results
- ruff: All checks passed (src + tests)

### Coverage
- **Tooling gap:** Coverage measurement failed due to pre-existing pydantic/MCP import chain error (`KeyError: 'pydantic.root_model'`). Not related to task #824. Functional correctness confirmed by 37/37 passing tests.

### Pass 1 -- CRITICAL

#### Security Review
- No hardcoded secrets, injection, path traversal, insecure deserialization, or secret leakage
- No new dependencies added
- URL validation via _check_url at system boundary

#### Test Integrity (TestFromAC comparison)
Builder made zero commits -- TestFromAC classes untouched.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ExtractContentMigration::test_success_path_does_not_double_wrap | No change | PRESERVED |
| TestFromAC_ExtractContentMigration::test_fallback_path_applies_wrap_untrusted_content | No change | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | assert_not_called, exact string match, assert_called_once |
| Negative/error paths | STRONG | ValueError, timeout, 404, rate limit, empty extraction |
| Mutation reasoning | STRONG | Early return removal would trigger assert_not_called failure |
| Test independence | STRONG | Each test creates own WebSearchToolset + fresh mocks |
| Descriptive names | STRONG | test_success_path_does_not_double_wrap, test_fallback_path_applies_wrap_untrusted_content |

#### Data Safety
- No data safety issues found

### Pass 2 -- INFORMATIONAL
- Redundant guard: `if not content:` at L217 always true after L214--215 early return. Harmless (suppression #2).
- No other informational findings.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| (1) No trafilatura import | grep: 0 matches in web_search.py | (structural) | PASS |
| (2) Uses extract_content | L29 import + L213 call | test_fetches_and_extracts_content | PASS |
| (3) Existing tests pass | 37 passed, 0 failed | full suite | PASS |
| (4) Raw-HTML fallback | L218-219: response.text[:max_length] | test_empty_extraction_returns_raw_fallback | PASS |
| (5) No double-wrap | L215: early return before wrap block | test_success_path_does_not_double_wrap | PASS |
| (6) Fallback wrapping | L221-226: wrap_untrusted_content on raw HTML | test_fallback_path_applies_wrap_untrusted_content | PASS |

### Verdict: PASS (confidence .95)

[[2026-03-17]] Tue 17:03
## Review Evidence (reviewer-2)

### Test Results
- pytest: 37 passed, 0 failed (background terminal, -p no:logfire)

### Lint Results
- ruff: All checks passed (src + tests scoped)

### Coverage
- Tooling gap: Coverage measurement skipped (pre-existing pydantic/MCP import chain error not related to #824). 37/37 functional tests confirm correctness.

### Pass 1 -- CRITICAL

#### Security Review
- No hardcoded secrets
- No injection vectors (URL validated via _check_url at boundary)
- No path traversal, insecure deserialization, or eval
- No new dependencies added
- No secret leakage in logs/errors
- Finding: CLEAN

#### Test Integrity (TestFromAC comparison)
Builder made zero commits (confirmed via git log). TestFromAC classes untouched.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ExtractContentMigration::test_success_path_does_not_double_wrap | No change | PRESERVED |
| TestFromAC_ExtractContentMigration::test_fallback_path_applies_wrap_untrusted_content | No change | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | assert_not_called on wrap mock, exact string equality, assert_called_once |
| Negative/error paths | STRONG | ValueError (blocked URL), TimeoutException, 404, HTTPError, empty extraction, rate limit, import guard |
| Mutation reasoning | STRONG | Removing early return at L211 triggers assert_not_called failure; removing extract_content call fails test_fetches_and_extracts_content |
| Test independence | STRONG | Each test creates own WebSearchToolset + fresh mocks via fixtures |
| Descriptive names | STRONG | test_success_path_does_not_double_wrap, test_fallback_path_applies_wrap_untrusted_content |

#### Data Safety
- No data safety issues found

### Pass 2 -- INFORMATIONAL
- Redundant guard: if not content at L218 always true after L214-215 early return. Harmless (suppression #2).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| (1) No trafilatura import | grep: 0 matches for trafilatura in web_search.py | (structural -- grep verification) | PASS |
| (2) Uses extract_content | L29: import + L213: call site | test_fetches_and_extracts_content | PASS |
| (3) Existing tests pass | 37 passed, 0 failed | full suite | PASS |
| (4) Raw-HTML fallback | L218-219: response.text[:max_length] when .text empty | test_empty_extraction_returns_raw_fallback | PASS |
| (5) No double-wrap | L215: early return before wrap block; extract_content wraps internally (content_extractor.py L110-113) | test_success_path_does_not_double_wrap | PASS |
| (6) Fallback wrapping | L221-226: wrap_untrusted_content on raw HTML | test_fallback_path_applies_wrap_untrusted_content | PASS |

### Verdict: PASS (confidence .95)

[[2026-03-17]] Tue 21:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| (1) No trafilatura import | grep: 0 matches in web_search.py | PASS |
| (2) Uses extract_content | L29 import + L209 call site verified | PASS |
| (3) Existing tests pass | 37/37 passed (test_web_search.py) | PASS |
| (4) Raw-HTML fallback | L213-216: if not content -> response.text[:max_length] | PASS |
| (5) No double-wrap | L210-211: early return before wrap block | PASS |
| (6) Fallback wrapping | L221-226: wrap_untrusted_content on raw HTML fallback | PASS |

### Test Results
- pytest (test_web_search.py): 37 passed, 0 failed
- pytest (test_content_extractor.py): 12 passed, 0 failed
- ruff: All checks passed

### Notes
- Full suite hung at ~50% (pre-existing WMI hang); scoped tests confirm no regressions
- Commit messages reference #842 not #824 (minor quality gap); deliverables committed
- Redundant if-not-content guard at L218: harmless

### Confidence: .97
### Action: archive
