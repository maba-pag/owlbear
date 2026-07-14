---
approved_at: null
categories: [pitfall, process]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-17T01:37:35.815638Z'
didnt_use_count: 1
id: 6212a312-b794-43ae-8cc2-5f7345c3e4eb
outstanding_count: 0
scope_agents: [verifier]
score: 0.84
source_agent: copilot
state: deleted
title: Verify the owning regression suite for shared boundaries
unremarkable_count: 0
updated_at: '2026-07-14T23:46:45.853459+00:00'
---

For a changed public or shared boundary, independently identify the nearest owning regression suite rather than treating the builder's file list as exhaustive. Run only the focused suite needed to prove the claimed boundary; do not expand into generic coverage hunting.
