---
approved_at: null
categories: [pitfall, process, tool-usage]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:38:39.918124Z'
didnt_use_count: 0
id: bdea220c-04d5-48d9-abe3-9fd2d40902b7
outstanding_count: 0
scope_agents: [builder, verifier, collector]
score: 0.0
source_agent: copilot
state: deleted
title: Verify working tree after delegated git commands
unremarkable_count: 0
updated_at: '2026-07-14T23:51:53.181717+00:00'
---

Quality-runner or other delegated agents may run git commands that alter the working tree. After delegated git operations, verify `git status` or equivalent state before relying on subsequent evidence.
