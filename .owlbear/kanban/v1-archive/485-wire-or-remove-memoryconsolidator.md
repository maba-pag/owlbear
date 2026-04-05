---
id: 485
title: Wire or remove MemoryConsolidator
status: archived
priority: important
created: 2026-03-04T07:38:01.9660025+01:00
updated: 2026-03-07T18:07:54.330018+01:00
started: 2026-03-06T20:33:45.8926576+01:00
completed: 2026-03-07T18:07:54.330018+01:00
tags:
    - audit
    - yagni
    - scope:core
class: standard
---

Delete all MemoryConsolidator code and tests. No functional behavior changes (code was never wired).

### Files to delete
- [ ] `src/owlbear/memory/consolidation.py` (entire module, ~145 LOC)
- [ ] `tests/test_consolidation.py` (entire test file, ~299 LOC)

### Files to edit
- [ ] `docs/architecture.md` line 120: delete directory listing entry `consolidation.py  # LLM-based memory consolidation`
- [ ] `docs/architecture.md` line 481: delete or rewrite the 'Memory consolidation' bullet under 'Patterns to adopt'  we are explicitly deferring this pattern per YAGNI

### What stays (do NOT delete)
- `SessionStore.last_consolidated` property + `_load_meta`/`_save_meta` in `src/owlbear/memory/session.py`  low-cost plumbing for future re-add
- `docs/research/memory-consolidator.md`  documents the decision rationale
- Line 472 in `docs/architecture.md` (nanobot comparison table)  historical comparison, not a recommendation

### Verification
- [ ] `uv run ruff check src/ tests/` clean
- [ ] `uv run pytest -q --tb=short` all remaining tests pass
- [ ] `grep -r 'MemoryConsolidator' src/` zero matches
- [ ] `grep -r 'from owlbear.memory.consolidation' src/ tests/` zero matches

### Out of scope
Do NOT edit audit/research docs (software-design-audit.md, integration-audit.md, executive-audit-report.md, bootstrap-assembly.md). These are historical records.
Do NOT edit the nanobot comparison table row at line 472 of architecture.md  that describes nanobot's approach, not ours.
