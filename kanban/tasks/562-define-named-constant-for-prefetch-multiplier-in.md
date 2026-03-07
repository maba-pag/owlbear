---
id: 562
title: Define named constant for prefetch multiplier in qdrant
status: backlog
priority: someday
created: 2026-03-04T07:39:05.1969981+01:00
updated: 2026-03-07T04:12:01.553661+01:00
started: 2026-03-07T04:12:01.553661+01:00
tags:
    - audit
    - code-quality
    - knowledge
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
