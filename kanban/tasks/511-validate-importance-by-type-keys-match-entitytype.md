---
id: 511
title: Validate IMPORTANCE_BY_TYPE keys match EntityType enum
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:23.1624031+01:00
updated: 2026-03-07T18:08:00.5525286+01:00
started: 2026-03-06T20:32:11.4744969+01:00
completed: 2026-03-07T18:08:00.5525286+01:00
tags:
    - audit
    - bugfix
    - knowledge
class: standard
---

F-21: IMPORTANCE_BY_TYPE dict keys vs EntityType enum values. See docs/code-quality-audit.md.

## Research Findings (2026-03-06)

1. **Keys currently match.** All 6 dict keys equal the 6 EntityType .value strings. No mismatch exists today.
2. **Dict is dead code.** _apply_temporal_boost calls _compute_recency_score(created_at, decay_rate) without passing importance. Always defaults to 0.5. Never wired up.
3. **Fragility remains.** Raw string keys diverge silently if EntityType changes. Rekey to EntityType members for type safety.

## AC

- [ ] Add `from owlbear.memory.knowledge.models import EntityType` to qdrant.py imports
- [ ] Rekey `IMPORTANCE_BY_TYPE` from raw strings to `EntityType` enum members (e.g. `EntityType.DECISION: 0.9`)  6 entries, one per member
- [ ] Update type annotation from `dict[str, float]` to `dict[EntityType, float]`
- [ ] Add test in `tests/test_qdrant_vector_store.py`: `assert set(IMPORTANCE_BY_TYPE) == set(EntityType)`  validates every member has an entry and no extraneous keys exist
- [ ] All existing tests in `test_qdrant_vector_store.py` continue to pass (no behavior change)

## Architecture Notes

- File: `src/owlbear/memory/knowledge/qdrant.py` lines 35-42
- EntityType is a StrEnum in `src/owlbear/memory/knowledge/models.py`  same package, simple import
- IMPORTANCE_BY_TYPE is currently dead code (not referenced outside its definition). Wiring importance lookup into _apply_temporal_boost is a separate follow-up task.
- Existing test pattern: `TestRecencyScore` class in test_qdrant_vector_store.py  add new test to same class or as standalone function nearby
