---
id: d5f21dfe-b336-4081-8bb4-b3d6873eb388
title: Green local tests need tracked ownership proof
categories:
- pitfall
- process
- tool-usage
confidence: 0.86
state: curated
scope_agents:
- verifier
- collector
source_agent: copilot
created_at: '2026-05-17T01:35:57.573353Z'
updated_at: '2026-05-17T01:48:10.824655Z'
approved_at: null
---

Green local test output is not reviewable deliverable evidence when the task test file is untracked or file ownership across retries is unreconstructed. Verify the test file is in HEAD or reconstruct task-related ownership across all relevant commits before accepting runner output.
