---
id: 653
title: Test ReDoS protection for filesystem search content regex
status: done
priority: important
created: 2026-03-07T23:11:28.1431564+01:00
updated: 2026-03-07T23:47:43.9669433+01:00
started: 2026-03-07T23:47:43.9669433+01:00
completed: 2026-03-07T23:47:43.9669433+01:00
tags:
    - audit
    - security
    - tools
    - test
class: standard
---

## Context
Test-first task for #496 (ReDoS protection). Add tests to`tests/test_filesystem_tools.py`.

## Acceptance Criteria

1. **test_search_files_invalid_regex**: Call `_search_files('*', content_regex='[invalid')` -> `ValueError` raised with message containing 'Invalid content_regex'
2. **test_search_files_nested_quantifier_rejected**: Call`_search_files('*', content_regex='(a+)+b')` -> `ValueError` raised with message containing 'nested quantifiers'
3. **test_search_files_regex_too_long**: Call `_search_files('*', content_regex='a' * 1001)` -> `ValueError` raised with message containing 'too long'
4. **test_search_files_valid_regex_still_works**: Call`_search_files('*.py', content_regex='def hello')` -> returns matching file paths (existing test already covers this, but verify not broken)
5. **test_search_files_none_regex_still_works**: Call`_search_files('*.py')` with no content_regex -> works as before
6. All tests use `pytest.raises(ValueError, match=...)` for precise assertion
7. Tests are in the existing `TestSearchFiles` class in`tests/test_filesystem_tools.py`
