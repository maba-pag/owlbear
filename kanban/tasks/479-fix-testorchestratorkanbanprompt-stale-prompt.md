---
id: 479
title: Fix TestOrchestratorKanbanPrompt stale prompt assertions
status: ideation
priority: needed
created: 2026-03-04T07:37:57.4647199+01:00
updated: 2026-03-04T07:37:57.4647199+01:00
tags:
    - audit
    - test
class: standard
---

H2: 2 failing tests assert exact strings that were changed in orchestrator agent prompt refactor. Update assertions to match current prompt or use semantic checks. AC: tests pass, assertions match current prompt. See docs/test-quality-audit.md.
