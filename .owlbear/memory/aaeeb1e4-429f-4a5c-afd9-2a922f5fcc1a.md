---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.8
contested_by_task: null
created_at: '2026-09-13T03:57:14.785461+00:00'
didnt_use_count: 0
id: aaeeb1e4-429f-4a5c-afd9-2a922f5fcc1a
outstanding_count: 0
scope_agents: []
score: 0.8
source_agent: builder
state: pending
title: Re-enter managed worktrees after delegated execution
unremarkable_count: 0
updated_at: '2026-09-13T03:57:14.785461+00:00'
---

In TASK-001 delivery-action-readiness, execution_subagent left a timed-out test process running in its terminal. The next run_in_terminal call started in the main checkout rather than the managed worktree and `test --changed --base <source>` exited with 'No test scope matched'. After delegated execution, explicitly cd to the supplied managed worktree and verify HEAD before running more exact-commit proof; a scope-empty exit is not test evidence. Preserve the returned terminal ID to collect the original process's completion.
