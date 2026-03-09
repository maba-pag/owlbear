---
id: 496
title: Add ReDoS protection to filesystem search content regex
status: done
priority: important
created: 2026-03-04T07:38:10.724342+01:00
updated: 2026-03-08T00:25:39.9642837+01:00
started: 2026-03-06T23:31:38.5259966+01:00
completed: 2026-03-08T00:25:39.9642837+01:00
tags:
    - audit
    - security
    - tools
class: standard
---

## Context
SEC-09 from docs/security-audit.md. `_search_files` in `src/owlbear/tools/filesystem.py` compiles`content_regex` (LLM-provided) via `re.compile()` with no guards. Two vectors:
- Invalid syntax -> unhandled `re.error` crash
- Catastrophic backtracking (e.g. `(a+)+b`) -> CPU hang

## Acceptance Criteria

1. **Compile-time guard**: `re.compile(content_regex)` is wrapped in`try/except re.error`  on failure, raise `ValueError` with message`f'Invalid content_regex: {original_re_error_message}'`   
2. **Nested-quantifier heuristic**: Before compilation, a lightweight check rejects patterns containing nested quantifiers (quantifier `+*?` or`{` applied to a group that itself contains a quantifier). Detected via a`_NESTED_QUANTIFIER_RE` pattern (e.g.`r'\([^)]*[+*?][^)]*\)[+*?{]'` or equivalent). On match, raise`ValueError('content_regex rejected: nested quantifiers risk catastrophic backtracking')`   
3. **Pattern length cap**: Reject `content_regex` longer than 1000 chars with`ValueError('content_regex too long (max 1000 chars)')`   
4. **Validation location**: All three checks occur at the top of`_search_files`, before the glob walk, in order: length -> heuristic -> compile   
5. **No new dependencies**: Use only stdlib `re`  do not add `regex`or other packages   
6. **Existing behavior preserved**: Valid regex patterns continue to work identically  search results unchanged   
7. **Error propagation**: `ValueError` propagates through`HookedToolset` -> `classify_error()` -> `TOOL_SEMANTIC` bucket, giving the LLM a chance to self-correct with a simpler pattern

## Architecture Notes
- Follows existing FileToolset pattern of raising typed exceptions at validation boundaries
- No changes to error taxonomy needed  `ValueError` already maps to `TOOL_SEMANTIC`  
- The heuristic does NOT need to catch all ReDoS patterns  it catches the common catastrophic class. The length cap and compile guard handle the rest
- Keep the `_NESTED_QUANTIFIER_RE` pattern as a module-level compiled constant (like `_MAX_SEARCH_RESULTS`)
