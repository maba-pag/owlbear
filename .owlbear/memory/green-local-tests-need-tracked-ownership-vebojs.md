---
approved_at: null
categories: [pitfall, process, tool-usage]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-17T01:35:57.573353Z'
didnt_use_count: 0
id: d5f21dfe-b336-4081-8bb4-b3d6873eb388
outstanding_count: 0
scope_agents: [verifier, collector]
score: 0.0
source_agent: copilot
state: deleted
title: Green local tests need tracked ownership proof
unremarkable_count: 0
updated_at: '2026-07-14T23:38:35.230055+00:00'
---

Green local test output is not reviewable deliverable evidence when the task test file is untracked or file ownership across retries is unreconstructed. Verify the test file is in HEAD or reconstruct task-related ownership across all relevant commits before accepting runner output.
