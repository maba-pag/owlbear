---
id: 508
title: Make openai import conditional in errors.py
status: archived
priority: important
created: 2026-03-04T07:38:19.9842385+01:00
updated: 2026-03-22T18:59:22.4237724+01:00
started: 2026-03-06T16:48:31.9821424+01:00
completed: 2026-03-07T18:07:58.9462884+01:00
tags:
    - audit
    - config
    - scope:core
class: standard
---

## Acceptance Criteria

- [ ] `src/owlbear/core/errors.py` uses `try/except ImportError` for `import openai` at module level
- [ ] When openai is importable: `classify_error(openai.AuthenticationError(...))` returns `ErrorCategory.AUTH` (existing behavior preserved)
- [ ] When openai is importable: `error_to_user_message(openai.AuthenticationError(...))` returns `'Authentication failed'` (existing behavior preserved)
- [ ] When openai is NOT importable: `classify_error()` returns `ErrorCategory.PERMANENT` for auth-like errors (graceful degradation, no crash)
- [ ] When openai is NOT importable: `error_to_user_message()` still works  unknown types fall through to scrub fallback
- [ ] When openai is NOT importable: `import owlbear.core.errors` succeeds without `ImportError`  
- [ ] Test the 'openai missing' codepath via `unittest.mock.patch.dict(sys.modules, {'openai': None})` + `importlib.reload`  
- [ ] All existing tests in `test_error_classification.py` and `test_error_sanitization.py` pass unchanged
- [ ] `uv run ruff check src/owlbear/core/errors.py` passes
- [ ] Diff is ~15 lines in errors.py + ~20 lines of new tests

## Implementation Notes

- Pattern: `try: import openai` / `except ImportError: openai = None`  
- Create `_openai_auth_errors: tuple[type[Exception], ...] = (openai.AuthenticationError, openai.PermissionDeniedError)` when available, `()` when not
- `isinstance(exc, _openai_auth_errors)` short-circuits to False when tuple is empty
- Guard `_SAFE_MESSAGES` entries: `if openai is not None: _SAFE_MESSAGES[openai.AuthenticationError] = ...`  
- New tests go in existing `test_error_classification.py`  add a class `TestClassifyErrorWithoutOpenai` that patches `sys.modules` and reloads
