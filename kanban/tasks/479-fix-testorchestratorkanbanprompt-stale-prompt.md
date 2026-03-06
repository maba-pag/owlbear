---
id: 479
title: Fix TestOrchestratorKanbanPrompt stale prompt assertions
status: archived
priority: needed
created: 2026-03-04T07:37:57.4647199+01:00
updated: 2026-03-06T19:28:26.591476+01:00
started: 2026-03-06T16:45:14.290273+01:00
completed: 2026-03-06T19:28:26.591476+01:00
tags:
    - audit
    - test
class: standard
---

## Research Findings (2026-03-06)

**Status: Already fixed -- close or repurpose as brittleness improvement.**

### Timeline
- 88c718c (Mar 1): Tests and orchestrator.md created together -- all assertions matched.
- 4daceb1 (Mar 4): Agent definitions rewritten with XML structuring -- likely broke prompt transiently.
- f7ba7f9 (Mar 4): Sync commit restored orchestrator.md -- assertions match again.
- 57f9aa0 (Mar 4): Test-quality-audit.md written -- captured the transient failure state.
- Current state: All 6 tests pass. Both 'Kanban Pipeline' and 'kanban_edit' present in prompt.

### Files Examined
- tests/test_kanban_pipeline.py (L218-L273): 6 tests in TestOrchestratorKanbanPrompt
- src/owlbear/agents/orchestrator.md (L68-L108): Kanban Pipeline section with all asserted strings
- docs/test-quality-audit.md: source audit that created this task

### What the Audit Found (no longer true)
Audit reported 2 failures: 'Kanban Pipeline' and 'kanban_edit' missing from orchestrator system prompt. Commit f7ba7f9 restored these strings before the task was created.

### Remaining Value: Brittleness (audit finding M1)
Tests assert exact substrings in prompt. Any future prompt rewording breaks them. Options:
1. Keep as-is (.7) -- tests pass, low maintenance if prompt is stable.
2. Switch to semantic checks (.6) -- test tool names in agent defs tools list instead.
3. Use regex patterns (.5) -- e.g. r'kanban.+pick' instead of exact 'kanban_pick'.

Recommendation (.7): Close this task. If brittleness is a concern, create a separate low-priority task.

### AC
- [x] Tests pass (verified: 6 passed in 0.66s)
- [x] Assertions match current prompt (verified: all strings present)
