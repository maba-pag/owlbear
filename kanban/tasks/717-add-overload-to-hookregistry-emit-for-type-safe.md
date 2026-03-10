---
id: 717
title: Add @overload to HookRegistry.emit for type-safe dispatch
status: backlog
priority: nice-to-have
created: 2026-03-09T23:01:43.5960953+01:00
updated: 2026-03-09T23:01:48.3651189+01:00
tags:
    - phase-8
    - hooks
    - typing
depends_on:
    - 483
class: standard
---

Phase 2 of typed hook payloads: type-safe event dispatch.\n\n## Acceptance Criteria\n1. @overload signatures on HookRegistry.emit() tying each HookEvent to its TypedDict\n2. Pylance/mypy flags wrong payload type for wrong event at emit() call sites\n3. Runtime behavior unchanged (overloads are purely static)\n4. All existing tests pass; ruff clean\n\n## Architecture Notes\n- Depends on #483 (TypedDict definitions) being complete\n- See docs/research/typed-hook-payloads-research.md section 5 (risk mitigation)
