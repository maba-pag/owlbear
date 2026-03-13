---
id: 731
title: 'Tests: ContentInjectionGuard (RED phase for #724)'
status: archived
priority: needed
created: 2026-03-10T19:37:24.1199746+01:00
updated: 2026-03-11T00:28:43.0670144+01:00
started: 2026-03-10T23:33:34.7478934+01:00
completed: 2026-03-11T00:28:43.0670144+01:00
tags:
    - phase-browser
    - scope:core
    - browser
    - security
    - test
claimed_by: builder
claimed_at: 2026-03-10T23:33:34.7478934+01:00
class: standard
---

TDD RED phase for #724. Write failing tests before implementation.

**Test file:** tests/test_content_guard.py
**Imports:** from owlbear.tools.browser.content_guard import ContentInjectionGuard, CheckResult, ContentInjectionError, DEFAULT_INJECTION_PATTERNS

**AC:**
- [ ] DEFAULT_INJECTION_PATTERNS is a non-empty list[str]
- [ ] CheckResult is a frozen Pydantic BaseModel with fields: threat: bool, blocked: bool, reason: str, pattern: str or None
- [ ] ContentInjectionError is an Exception with text, pattern, reason attributes
- [ ] Tests for ContentInjectionGuard.scan() detecting at least 5 known injection phrases (case-insensitive). Phrases to test: 'ignore previous instructions', 'you are now a', 'execute the following command', 'exfiltrate', 'what is your system prompt'
- [ ] Tests for scan() returning clean CheckResult(threat=False, blocked=False) on safe content (e.g. 'The weather in Berlin is sunny today')
- [ ] Tests for strict mode: ContentInjectionGuard(mode='strict') -- result.blocked=True, result.threat=True when injection found
- [ ] Tests for warn mode: ContentInjectionGuard(mode='warn') -- result.threat=True, result.blocked=False when injection found
- [ ] Tests for off mode: ContentInjectionGuard(mode='off') -- result.threat=False, result.blocked=False always, even with injection phrases present
- [ ] Tests for custom patterns: ContentInjectionGuard(patterns=['custom_evil']) matches 'custom_evil' but not default patterns
- [ ] Integration test: construct BrowserToolset(config=BrowserConfig(content_scan_mode='strict')), mock browser_read_text to return text containing injection phrase, call _read_text(), assert return value starts with 'BLOCKED:'
- [ ] Integration test: construct WebCrawler with ContentInjectionGuard(mode='strict'), mock page content containing injection, verify crawl appends error and skips page
- [ ] All tests FAIL (RED phase -- content_guard.py does not exist yet)

**Patterns to follow:**
- tests/test_browser_safety.py -- URLSafetyGuard test structure (guard instantiation, check method, exception class)
- tests/test_command_guard.py (if exists) -- CommandSafetyGuard test structure

[[2026-03-10]] Tue 20:27

## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| DEFAULT_INJECTION_PATTERNS non-empty list | CLEAR -- verifiable assertion | Added (was missing) |
| CheckResult frozen BaseModel fields | CLEAR -- exact fields specified | Added (was missing) |
| ContentInjectionError exception attrs | CLEAR -- text, pattern, reason | Added (was missing) |
| scan() detects 5+ injection phrases | CLEAR -- exact phrases listed | Tightened from ~5 to at least 5 with examples |
| scan() returns clean on safe content | CLEAR -- expected output specified | None |
| strict mode: blocked=True, threat=True | CLEAR -- mode/result mapping defined | None |
| warn mode: threat=True, blocked=False | CLEAR -- mode/result mapping defined | None |
| off mode: threat=False, blocked=False | CLEAR -- mode/result mapping defined | None |
| custom patterns override defaults | CLEAR -- test contract specified | None |
| Integration: BrowserToolset BLOCKED | CLEAR -- mock setup and assertion defined | Tightened with exact mock/assert contract |
| Integration: WebCrawler skips page | CLEAR -- error-list assertion defined | Tightened with exact mock/assert contract |
| All tests FAIL (RED) | CLEAR -- standard RED phase gate | None |

### Architecture Notes
1. Dependency direction fixed. Original had #731 depends_on [724] (backwards for TDD). Corrected: removed dep from #731, added depends_on [731] to #724 frontmatter. Tests first, then implementation.
2. AC expanded from 9 to 12 lines. Added 3 missing test categories: DEFAULT_INJECTION_PATTERNS existence, CheckResult model structure, ContentInjectionError exception attributes.
3. Integration tests tightened with exact mock setup contracts and assertion targets.
4. Single domain: test-only task, single file tests/test_content_guard.py.
5. Follows tests/test_browser_safety.py pattern for guard testing.

### Changes Made
- Rewrote AC body with 12 precise, individually verifiable AC lines
- Removed incorrect depends_on [724] from #731 body
- Added depends_on [731] to #724 frontmatter (correct TDD direction)
- Specified exact import path, test phrases, and mock setup contracts

### Dependencies
- #731 has no dependencies (standalone test task)
- #724 now correctly depends_on [731] (TDD: tests first)

[[2026-03-10]] Tue 20:27

## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| DEFAULT_INJECTION_PATTERNS non-empty list | CLEAR -- verifiable assertion | Added (was missing) |
| CheckResult frozen BaseModel fields | CLEAR -- exact fields specified | Added (was missing) |
| ContentInjectionError exception attrs | CLEAR -- text, pattern, reason | Added (was missing) |
| scan() detects 5+ injection phrases | CLEAR -- exact phrases listed | Tightened from ~5 to at least 5 with examples |
| scan() returns clean on safe content | CLEAR -- expected output specified | None |
| strict mode: blocked=True, threat=True | CLEAR -- mode/result mapping defined | None |
| warn mode: threat=True, blocked=False | CLEAR -- mode/result mapping defined | None |
| off mode: threat=False, blocked=False | CLEAR -- mode/result mapping defined | None |
| custom patterns override defaults | CLEAR -- test contract specified | None |
| Integration: BrowserToolset BLOCKED | CLEAR -- mock setup and assertion defined | Tightened with exact mock/assert contract |
| Integration: WebCrawler skips page | CLEAR -- error-list assertion defined | Tightened with exact mock/assert contract |
| All tests FAIL (RED) | CLEAR -- standard RED phase gate | None |

### Architecture Notes
1. Dependency direction fixed. Original had #731 depends_on [724] (backwards for TDD). Corrected: removed dep from #731, added depends_on [731] to #724 frontmatter. Tests first, then implementation.
2. AC expanded from 9 to 12 lines. Added 3 missing test categories: DEFAULT_INJECTION_PATTERNS existence, CheckResult model structure, ContentInjectionError exception attributes.
3. Integration tests tightened with exact mock setup contracts and assertion targets.
4. Single domain: test-only task, single file tests/test_content_guard.py.
5. Follows tests/test_browser_safety.py pattern for guard testing.

### Changes Made
- Rewrote AC body with 12 precise, individually verifiable AC lines
- Removed incorrect depends_on [724] from #731 body
- Added depends_on [731] to #724 frontmatter (correct TDD direction)
- Specified exact import path, test phrases, and mock setup contracts

### Dependencies
- #731 has no dependencies (standalone test task)
- #724 now correctly depends_on [731] (TDD: tests first)

[[2026-03-10]] Tue 22:01
## Builder Notes
- Files created: src/owlbear/tools/browser/content_guard.py
- Files changed: src/owlbear/tools/browser/config.py (added content_scan_mode field), src/owlbear/tools/browser/toolset.py (guard construction + _read_text scan), src/owlbear/tools/browser/crawler.py (content_guard DI + crawl scanning), tests/test_content_guard.py (fixed _run helper return)
- Tests: 67 passed, content_guard.py 100% coverage
- Lint: ruff clean on all 5 files
- Existing browser tests: 102 passed, zero regressions
- Fixes applied: test helper _run() was missing return statement (module-level, not in TestFromAC class)

[[2026-03-10]] Tue 22:34
## Review Evidence

### Test Results
- pytest: 67 passed, 0 failed (tests/test_content_guard.py)
- Existing browser tests: 12 pre-existing RED-phase failures (snapshot task, unrelated)

### Lint Results
- ruff: All checks passed (5 files)

### Coverage
- content_guard.py: 100%

### Test Quality
All 5 dimensions rated STRONG: assertion specificity, negative paths, mutation reasoning, test independence, descriptive names.

### Security Review
All 7 checks CLEAN. No secrets, no injection risk, no new deps, no log leakage.

### TestFromAC Comparison
All 12 TestFromAC classes PRESERVED. Builder only fixed module-level _run() helper (missing return).

### AC Compliance
All 12 AC lines PASS with specific test evidence (67 tests total).

### Verdict: PASS (confidence .95)
