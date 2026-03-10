---
id: 653
title: Test ReDoS protection for filesystem search content regex
status: archived
priority: important
created: 2026-03-07T23:11:28.1431564+01:00
updated: 2026-03-09T22:53:29.7455772+01:00
started: 2026-03-07T23:47:43.9669433+01:00
completed: 2026-03-09T22:53:29.7455772+01:00
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

[[2026-03-09]] Mon 22:53
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. test_search_files_invalid_regex | Found at test_filesystem_tools.py L325-327. Uses pytest.raises(ValueError, match='Invalid content_regex') with content_regex='[invalid' | PASS |
| 2. test_search_files_nested_quantifier_rejected | Found at L329-331. Uses pytest.raises(ValueError, match='nested quantifiers') with content_regex='(a+)+b' | PASS |
| 3. test_search_files_regex_too_long | Found at L333-335. Uses pytest.raises(ValueError, match='too long') with content_regex='a' * 1001 | PASS |
| 4. test_search_files_valid_regex_still_works | Found at L337-347. Creates temp files, verifies content_regex='def hello' returns matching file | PASS |
| 5. test_search_files_none_regex_still_works | Found at L349-358. Creates temp file, calls _search_files without content_regex, works | PASS |
| 6. All use pytest.raises(ValueError, match=...) | AC1-3 confirmed; AC4-5 don't raise (correct) | PASS |
| 7. Tests in TestSearchFiles class | Class starts L259, last class in file, all tests inside it | PASS |

### Test Results
- pytest (scoped): 37 passed in 2.94s
- pytest (full): 1 unrelated failure (test_context_hydration PermissionError on Windows tmp_path), 2 skipped
- ruff: 3 pre-existing errors in unrelated files (screenshot.py, test_bootstrap_structure.py); test_filesystem_tools.py is clean

### Confidence: .97
### Action: archive
