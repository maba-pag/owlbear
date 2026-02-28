---
id: 152
title: Refactor apply_role_policy to accept AbstractToolset via FilteredToolset
status: archived
priority: important
created: 2026-02-27T16:47:31.1680845+01:00
updated: 2026-02-28T23:53:10.3142062+01:00
started: 2026-02-27T16:48:17.2392215+01:00
completed: 2026-02-28T23:53:10.3142062+01:00
tags:
    - phase-8
    - agent
    - refactor
class: standard
---

Replace custom FilteredToolset usage in apply_role_policy with PydanticAI native .filtered() on any AbstractToolset. Research: docs/pydantic-ai-multi-agent-research.md section 3.2.

## AC
- [ ] Update apply_role_policy() in src/owlbear/core/roles.py: accept AbstractToolset (not just FunctionToolset) as first param
- [ ] Use toolset.filtered(predicate) — already used, but type signature is too narrow
- [ ] Existing tests in tests/test_roles.py continue to pass unchanged
- [ ] Add test: filtering a CombinedToolset (non-FunctionToolset) works correctly
- [ ] Update type imports: remove FunctionToolset, add AbstractToolset to TYPE_CHECKING
- [ ] ruff clean

## Architecture
- Currently apply_role_policy takes FunctionToolset but calls .filtered() which is an AbstractToolset method
- The fix is purely a type-signature widening — the runtime behavior is already correct
- ~10 LOC diff (type annotations only)
- See current code: src/owlbear/core/roles.py lines 84-101
