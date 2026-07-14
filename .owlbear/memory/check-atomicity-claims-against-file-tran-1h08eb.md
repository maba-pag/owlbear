---
approved_at: null
categories: [pitfall, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-26T00:03:17.919043Z'
didnt_use_count: 1
id: 430e5182-272d-4e09-af07-4a99b934a234
outstanding_count: 0
scope_agents: [verifier, collector]
score: 0.84
source_agent: reviewer
state: deleted
title: Check atomicity claims against file-transition code
unremarkable_count: 0
updated_at: '2026-07-14T20:19:35.510279+00:00'
---

When reviewing documentation that describes filesystem transitions, verify the exact operation pattern. A claim like 'moves atomically' is incorrect if the implementation writes the destination and then deletes the source in separate steps, even when the final behavior otherwise looks correct.
