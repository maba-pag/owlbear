---
id: 866
title: Archive redundant core re-export duplicate-cleanup meta-task
status: archived
priority: nice-to-have
created: 2026-03-20T13:52:02.9848328+01:00
updated: 2026-03-21T04:55:37.4841425+01:00
started: 2026-03-21T04:55:37.4841425+01:00
completed: 2026-03-21T04:55:37.4841425+01:00
tags:
    - audit
    - scope:core
class: standard
---

Board cleanup only. This task retires redundant meta-task #866 without modifying #822. #822 already records the duplicate finding and block reason pointing to archived #812; any future lifecycle change to #822 must happen while working directly on #822. Append a one-line closure note to #866 documenting that relationship, then archive #866. Do not modify any other task files, src/, or tests/. See docs/research/core-init-reexport-stale-task.md.

## AC

- [ ] Append a one-line closure note to #866 stating that #822 already records the duplicate finding, #812 is the source of truth for the shipped core cleanup, and any further lifecycle change to #822 must occur while working directly on #822
- [ ] The closure note cites docs/research/core-init-reexport-stale-task.md
- [ ] Archive #866 after appending the note
- [ ] No other task files, src/, or tests/ are modified

[[2026-03-20]] Fri 15:33

## Research

Doc: docs/research/core-init-reexport-stale-task.md

Summary: Verified that #822 remains a stale duplicate of #812. The current repository still satisfies #822 acceptance criteria: src/owlbear/core/__init__.py contains only the module docstring plus from __future__ import annotations, tests/test_core_init_clean.py enforces absence of __all__ and the old re-exports, and TestFromAC_CoreReExport is absent from tests/test_exception_hierarchy.py.

Live verification: uv run pytest tests/test_core_init_clean.py tests/test_exception_hierarchy.py -q --tb=short -> 34 passed, 2 optional-dependency warnings.

Recommendation (.98): keep #866 as the board-cleanup follow-up and advance it to backlog. No new follow-up tasks are required; attribution is already present in docs/sources/overview.md.

## Architecture Review

See docs/scratch/866-architect.md for full review.

[[2026-03-20]] Fri 17:32

## Test-Writer Notes

- Non-implementation task (board-cleanup only) — no tests applicable.
- Passing through to builder.

[[2026-03-21]] Sat 04:54

## Builder Notes

- Board-cleanup task: appending closure note per AC.
- #822 already records the duplicate finding; #812 is the source of truth for the shipped core cleanup; any further lifecycle change to #822 must occur while working directly on #822. See docs/research/core-init-reexport-stale-task.md.
- No src/ or tests/ files were modified.
- Archiving #866 per AC.
