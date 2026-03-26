---
id: 531
title: Add TypedDict for tool_stats return type
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:36.8877228+01:00
updated: 2026-03-11T21:13:24.7993152+01:00
started: 2026-03-07T00:26:11.7431131+01:00
completed: 2026-03-11T21:13:24.7993152+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

## Research
N/A - trivial TypedDict definition.

### Inner dict keys (from `EventStore.tool_stats()` in `observability.py:119-148`)
- `call_count: int` - incremented per post_tool_use event
- `error_count: int` - incremented when `not e.success`
- `avg_duration_ms: float` - computed average, defaults to 0.0

### Implementation
Define `ToolStats(TypedDict)` in `observability.py`, change return annotation to `dict[str, ToolStats]`.
No logic changes needed - dict literals already match the shape.

### AC
- [ ] `ToolStats` TypedDict defined with 3 keys
- [ ] `tool_stats()` return type is `dict[str, ToolStats]`
- [ ] Existing tests still pass
- [ ] ruff clean

[[2026-03-11]] Wed 10:39
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ToolStats TypedDict with 3 keys | Precise  keys match tool_stats() dict shape (call_count: int, error_count: int, avg_duration_ms: float) | Keep |
| tool_stats() return type is dict[str, ToolStats] | Clear, verifiable annotation change | Keep |
| Existing tests still pass | Correct gate  6 existing tests in TestEventStoreToolStats cover all paths | Keep |
| ruff clean | Standard lint gate | Keep |

### Architecture Notes
- **Pattern match:** TypedDict is established in this codebase (hooks.py has 8 TypedDicts, test_hook.py has TestResult). Following the same pattern.
- **Placement:** Define in observability.py co-located with EventStore that produces the dict  correct. No re-export needed.
- **TDD waiver:** Pure type-annotation change with zero logic delta. Existing tests already cover the dict shape implicitly. A separate RED-phase test task would be YAGNI.
- **Import:** Use `from typing import TypedDict` (already imported in hooks.py, same convention).

### Changes Made
- Moved #531 backlog -> todo

### Dependencies
- None  standalone annotation improvement

[[2026-03-11]] Wed 16:24
## Test-Writer Notes
- Test file: tests/test_tool_stats_typeddict.py
- Classes: TestFromAC_ToolStatsTypedDict, TestFromAC_ToolStatsReturnAnnotation
- Tests per category: happy 3, edge 0, error 0, boundary 1
- Total: 7 tests, all FAIL (ImportError) u{2713}
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| ToolStats TypedDict with 3 keys | test_importable, test_is_typed_dict, test_has_call_count_int, test_has_error_count_int, test_has_avg_duration_ms_float, test_exactly_three_keys | happy, boundary |
| tool_stats() return type dict[str, ToolStats] | test_return_annotation_is_dict_str_toolstats | happy |
| Existing tests still pass | builder gate (no new test) | -- |
| ruff clean | lint gate (no new test) | -- |

[[2026-03-11]] Wed 20:45
## Builder Notes
- Files changed: src/owlbear/core/observability.py
- Added ToolStats TypedDict (3 keys: call_count int, error_count int, avg_duration_ms float)
- Updated tool_stats() return annotation to dict[str, ToolStats]
- Moved timedelta from TYPE_CHECKING to runtime import (needed for get_type_hints resolution)
- Tests: 44 passed (7 new + 37 existing), 100% coverage on observability.py
- Lint: ruff clean
- No TestFromAC classes modified

[[2026-03-11]] Wed 20:49
## Review Evidence

### Test Results
- pytest: 44 passed, 0 failed (7 new + 37 existing)
- Command: `uv run pytest tests/test_tool_stats_typeddict.py tests/test_observability_hook.py -v --tb=short --timeout=30`

### Lint Results
- ruff: All checks passed!

### Coverage
- observability.py: 100%

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Tests check exact types via `typing.get_type_hints`, verify `issubclass(ToolStats, dict)`, exact key count `len(hints) == 3`, and return annotation with `get_origin`/`get_args` |
| Negative/error paths | ADEQUATE | N/A for pure type-annotation task; boundary test (exactly 3 keys) guards against extras |
| Mutation reasoning | STRONG | Removing a key fails `test_exactly_three_keys`; wrong type fails individual key tests; wrong return annotation fails `get_args` check |
| Test independence | STRONG | All tests are stateless, no shared mutable state, no fixtures |
| Descriptive names | STRONG | Names specify scenario: `test_has_call_count_int`, `test_return_annotation_is_dict_str_toolstats` |

### Security Review
- No security issues. Pure TypedDict + annotation change; no user input, no I/O, no deserialization.

### Test Writer vs Builder Comparison
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ToolStatsTypedDict::test_importable | No change | PRESERVED |
| TestFromAC_ToolStatsTypedDict::test_is_typed_dict | No change | PRESERVED |
| TestFromAC_ToolStatsTypedDict::test_has_call_count_int | No change | PRESERVED |
| TestFromAC_ToolStatsTypedDict::test_has_error_count_int | No change | PRESERVED |
| TestFromAC_ToolStatsTypedDict::test_has_avg_duration_ms_float | No change | PRESERVED |
| TestFromAC_ToolStatsTypedDict::test_exactly_three_keys | No change | PRESERVED |
| TestFromAC_ToolStatsReturnAnnotation::test_return_annotation_is_dict_str_toolstats | No change | PRESERVED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| ToolStats TypedDict with 3 keys | observability.py L57-63: `class ToolStats(TypedDict)` with call_count, error_count, avg_duration_ms | test_is_typed_dict, test_has_call_count_int, test_has_error_count_int, test_has_avg_duration_ms_float, test_exactly_three_keys | PASS |
| tool_stats() return type dict[str, ToolStats] | observability.py L126: `-> dict[str, ToolStats]` | test_return_annotation_is_dict_str_toolstats | PASS |
| Existing tests still pass | 37 pre-existing tests in test_observability_hook.py pass | (existing suite) | PASS |
| ruff clean | `uv run ruff check` -> All checks passed | (lint gate) | PASS |

### Verdict: PASS (confidence .97)
- Surgical 4-line diff: TypedDict + annotation change, zero logic delta
- All tests preserved, all passing, 100% coverage
- Clean lint

[[2026-03-11]] Wed 20:50
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure type-annotation change, no behavior/API change |
| 2 | Docstrings complete | Yes | Pass | ToolStats has docstring (L58), tool_stats() docstring present |
| 3 | sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase |
| 6 | No impact | -- | -- | Items 2 verified; rest N/A |

### Files Updated
- None

### Scratch Files Cleaned
- None found

[[2026-03-11]] Wed 21:13
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| ToolStats TypedDict with 3 keys | observability.py L57-63: class ToolStats(TypedDict) with call_count:int, error_count:int, avg_duration_ms:float | PASS |
| tool_stats() return type dict[str, ToolStats] | observability.py L126: -> dict[str, ToolStats] | PASS |
| Existing tests still pass | 44 passed (7 new + 37 existing), 0 failed | PASS |
| ruff clean | ruff check -> All checks passed | PASS |

### Test Results
- pytest: 44 passed, 0 failed
- ruff: All checks passed

### Confidence: .97
### Action: archive
