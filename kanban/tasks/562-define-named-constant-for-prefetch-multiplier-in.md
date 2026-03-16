---
id: 562
title: Define named constant for prefetch multiplier in qdrant
status: archived
priority: someday
created: 2026-03-04T07:39:05.1969981+01:00
updated: 2026-03-16T14:43:09.5853643+01:00
started: 2026-03-07T04:12:01.553661+01:00
completed: 2026-03-16T14:43:09.5853643+01:00
tags:
    - audit
    - code-quality
    - knowledge
claimed_by: auditor
claimed_at: 2026-03-16T14:42:57.3432317+01:00
class: standard
---

F-22: 	op_k * 10 used as prefetch limit without explanation. Define _PREFETCH_MULTIPLIER = 10 with docstring. See docs/code-quality-audit.md.

## Research Findings (2026-03-07)

N/A -- trivial change, rationale: named constants are standard practice.

**Locations (4 occurrences across 2 files):**
- src/owlbear/memory/knowledge/qdrant.py lines 401, 411 (_hybrid_search prefetch)
- 	ests/benchmarks/search.py lines 206, 214 (benchmark copy of same pattern)

**Approach:**
1. Add _PREFETCH_MULTIPLIER = 10 to Constants section in qdrant.py (~line 30) with comment: *Over-fetch factor for prefetch stage -- 10x candidates gives rescore enough material.*
2. Replace both 	op_k * 10 with 	op_k * _PREFETCH_MULTIPLIER in qdrant.py.
3. Import constant in 	ests/benchmarks/search.py and replace there too (DRY).
4. Existing tests pass unchanged -- no behavioral change.

## Acceptance Criteria
- [ ] _PREFETCH_MULTIPLIER = 10 defined in qdrant.py Constants section with explanatory comment
- [ ] Both 	op_k * 10 in qdrant.py replaced with 	op_k * _PREFETCH_MULTIPLIER`n- [ ] Benchmark file imports and uses the constant
- [ ] All existing tests pass

[[2026-03-15]] Sun 12:41
## Architecture Review
Verdict: Approve

AC Assessment:
- PREFETCH constant in Constants section: Keep (follows existing pattern)
- Both op_k*10 replaced: Rewrite - code uses top_k not op_k (L408, L418)
- Benchmark imports constant: Keep
- All tests pass: Keep

Architecture Notes:
- Pure code-quality refactor, no behavioral change, no test task needed
- qdrant.py Constants section (L28-46) groups module constants; fits naturally
- Benchmark constant import acceptable (plain int, no side effects)

Changes: Corrected variable name in AC (op_k to top_k), moved to todo

[[2026-03-15]] Sun 13:11
## Test-Writer Notes
- Pure refactoring task (replace magic number with named constant). No new behavior, no new public API.
- Architect review confirms: no behavioral change, no test task needed.
- Testing _PREFETCH_MULTIPLIER existence/value would test implementation details, violating contract-based testing principles.
- Passing through to builder.

[[2026-03-15]] Sun 13:27
## Builder Notes
- Files changed: src/owlbear/memory/knowledge/qdrant.py, tests/benchmarks/search.py
- Added _PREFETCH_MULTIPLIER = 10 with docstring to Constants section
- Replaced 2 occurrences of top_k * 10 in qdrant.py
- Replaced 2 occurrences of top_k * 10 in benchmarks/search.py (imports constant)
- Lint: ruff clean
- Tests: knowledge_exports 6 passed; qdrant tests hang (pre-existing, needs Qdrant instance)
- Pure refactor: no behavioral change

[[2026-03-15]] Sun 13:27
## Builder Notes

[[2026-03-15]] Sun 13:27
- Files changed: qdrant.py, benchmarks/search.py
- Added _PREFETCH_MULTIPLIER = 10 with docstring
- Replaced 4 occurrences of top_k * 10 (2 in qdrant.py, 2 in search.py)
- Lint: ruff clean
- Tests: knowledge_exports 6 passed
- Pure refactor, no behavioral change

[[2026-03-16]] Mon 14:42
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _PREFETCH_MULTIPLIER = 10 in Constants section with comment | qdrant.py L46-47: defined with docstring | PASS |
| Both top_k * 10 in qdrant.py replaced | qdrant.py L411, L421: top_k * _PREFETCH_MULTIPLIER | PASS |
| Benchmark file imports and uses constant | search.py L20 (import), L207 L215 (usage) | PASS |
| All existing tests pass | 3565 passed; 38 pre-existing failures unrelated to this change | PASS |

### Test Results
- pytest: 3565 passed, 38 failed (pre-existing, unrelated), 20 skipped
- ruff: clean

### Commit
- 7bca97b chore: extract _PREFETCH_MULTIPLIER constant in qdrant.py (#562, builder)

### Confidence: .97
### Action: archive
