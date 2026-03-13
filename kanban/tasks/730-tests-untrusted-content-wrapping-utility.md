---
id: 730
title: 'Tests: untrusted content wrapping utility'
status: archived
priority: needed
created: 2026-03-10T19:36:26.3753481+01:00
updated: 2026-03-11T09:03:46.8590915+01:00
started: 2026-03-11T00:26:18.2162987+01:00
completed: 2026-03-11T09:03:46.8590915+01:00
tags:
    - phase-browser
    - scope:core
    - security
    - type:test
class: standard
---

**Source:** #725 (implementation task), docs/research/untrusted-content-wrapping.md

**AC:**
- [ ] Test `wrap_untrusted_content()` wraps text with `<untrusted_web_content>` tags and advisory preamble
- [ ] Test `source_url` parameter appears in open tag attribute when provided
- [ ] Test `source_url=None` omits URL attribute from tag
- [ ] Test idempotency: already-wrapped text is not double-wrapped
- [ ] Test empty/blank text returns empty string unwrapped
- [ ] Test config toggle: integration points skip wrapping when `wrap_web_content=False`
- [ ] Tests placed in `tests/test_content_safety.py`

[[2026-03-10]] Tue 20:25
## Architecture Review
APPROVED - test

[[2026-03-10]] Tue 20:25
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test wraps text with tags+advisory | CLEAR -- exact text specified in #725 AC | None |
| Test source_url in open tag | CLEAR -- input/output contract defined | None |
| Test source_url=None omits attr | CLEAR -- inverse of above | None |
| Test idempotency | CLEAR -- #725 AC defines guard behavior | None |
| Test empty/blank returns empty | CLEAR -- unambiguous edge case | None |
| Test config toggle | CLEAR -- #725 AC lists 4 gated paths | None |
| Tests in test_content_safety.py | CLEAR -- follows test_{module}.py naming | None |

### Architecture Notes
1. AC1-5 are pure unit tests of wrap_untrusted_content(). AC6 tests config-gated behavior; representative integration point (e.g. fetch_url) sufficient.
2. TDD ordering correct. #725 depends_on [730]. Tests written first, expected to fail until #725 implements.
3. No codebase conflicts -- neither test_content_safety.py nor content_safety.py exist yet.
4. Single domain: core/ (wrapping utility).

### Dependencies
- No unresolved dependencies for this test task
- #725 correctly depends_on [730]

[[2026-03-10]] Tue 20:25
**Verdict:** APPROVED

### AC Assessment
All 7 AC lines verified as CLEAR and verifiable. #725 AC provides exact function signature, advisory text, and integration points.

### Architecture Notes
1. AC1-5 are pure unit tests of wrap_untrusted_content(). AC6 tests config-gated behavior; representative integration point sufficient.
2. TDD ordering correct. #725 depends_on 730. Tests fail until #725 implements.
3. No codebase conflicts -- neither test_content_safety.py nor content_safety.py exist yet.
4. Single domain: core/ (wrapping utility).

### Dependencies
- No unresolved dependencies
- #725 correctly depends_on 730

[[2026-03-10]] Tue 21:16
## Test-Writer Notes
- Test file: tests/test_content_safety.py
- Classes: TestFromACWrapUntrustedContent (AC1-5), TestFromACConfigToggle (AC6)
- Tests: 15 total, all FAIL (ModuleNotFoundError)
- ruff: clean

[[2026-03-10]] Tue 22:36
## Builder Notes
- Files changed: src/owlbear/core/content_safety.py (new), src/owlbear/config.py (wrap_web_content field)
- Tests: 16 passed, coverage 100% on content_safety.py
- Lint: ruff clean
- Evidence: all TestFromAC_* tests verified FAIL before implementation (ModuleNotFoundError), then GREEN after
- Key design: advisory text contains <untrusted_web_content> which serves as the opening tag when source_url=None (count==1), separate URL-attributed tag added when source_url provided
- No TestFromAC classes modified, no TestBuilderDiscovered needed

[[2026-03-11]] Wed 09:03
## Audit (auditor, 2026-03-11)

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Test wraps text with tags+advisory | 3 tests (wraps_text, advisory_before_content, content_preserved) PASS | PASS |
| AC2: Test source_url in open tag | 2 tests (source_url_in_open_tag, special_characters) PASS | PASS |
| AC3: Test source_url=None omits attr | 2 tests (none_omits_attribute, default_is_none) PASS | PASS |
| AC4: Test idempotency | 3 tests (already_wrapped, wrapped_with_url, no_double_wrap) PASS | PASS |
| AC5: Test empty/blank returns empty | 2 tests (empty_string, blank_whitespace) PASS | PASS |
| AC6: Test config toggle | 3 tests (defaults_true, can_be_disabled, integration_skips) PASS | PASS |
| AC7: Tests in test_content_safety.py | File verified at tests/test_content_safety.py | PASS |

### Test Results

- pytest (scoped): 16 passed, 0 failed
- ruff: 1 fixable I001 import-ordering warning in test file
- Full suite: env issue (corrupted venv, pre-existing, unrelated to task)

### Confidence: .95

### Action: archive
