---
id: 510
title: Add prefix-stripping tests to copilot_multipliers
status: archived
priority: important
created: 2026-03-04T07:38:21.6998228+01:00
updated: 2026-03-07T18:08:00.0015261+01:00
started: 2026-03-06T20:57:21.0274949+01:00
completed: 2026-03-07T18:08:00.0015261+01:00
tags:
    - audit
    - test
class: standard
---

M2: copilot_multipliers.py at 80% coverage -- prefix-stripping loop body never exercised. No test calls get_premium_requests('openai:gpt-4o') or get_premium_requests('copilot:o1'). Trivial fix.

## Research (trivial)
Research checklist: N/A -- trivial test-only change. Rationale: adding 2-3 test cases for an already-tested function.

**Findings:**
- src/owlbear/providers/copilot_multipliers.py lines 47-50: for/if/break strips 'openai:' and 'copilot:' prefixes before dict lookup
- tests/test_copilot_multipliers.py: 7 tests across 3 classes, all use bare model names
- Gap: zero tests exercise the prefix path
- Fix: add a TestPrefixStripping class with cases for openai:gpt-4o (1.0), copilot:o1 (10.0), and optionally openai:unknown-model (1.0 default)
- No production code changes needed

## Acceptance Criteria
- [ ] Test exists calling get_premium_requests('openai:gpt-4o') asserting 1.0
- [ ] Test exists calling get_premium_requests('copilot:o1') asserting 10.0
- [ ] Test exists calling get_premium_requests with prefixed unknown model asserting 1.0
- [ ] Coverage of copilot_multipliers.py reaches 100%
- [ ] All existing tests still pass
- [ ] ruff clean
