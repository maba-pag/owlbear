---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.8
contested_by_task: null
created_at: '2026-09-13T03:57:14.785461+00:00'
didnt_use_count: 0
id: aaeeb1e4-429f-4a5c-afd9-2a922f5fcc1a
outstanding_count: 0
scope_agents: [builder, finalizer]
score: 0.8
source_agent: builder
state: curated
title: Re-establish Delivery worktree context in new terminals
unremarkable_count: 0
updated_at: '2026-10-08T21:00:49.703624+00:00'
---

New async VS Code terminals in a Delivery lane can start in the primary checkout, including after delegated execution. `run_in_terminal` may strip a leading `cd <worktree> &&`; issue `cd <absolute-worktree>` as a separate command and verify `pwd` and `git rev-parse HEAD` against the launch/source before proof or writes. Use `git -C` or absolute paths where useful. Preserve the delegated terminal ID and collect its completion; a scope-empty `test --changed` from the primary checkout is not proof.
