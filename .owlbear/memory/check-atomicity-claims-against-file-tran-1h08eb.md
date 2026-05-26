---
id: 430e5182-272d-4e09-af07-4a99b934a234
title: Check atomicity claims against file-transition code
categories:
- pitfall
- process
confidence: 0.84
state: curated
scope_agents:
- reviewer
- doc-writer
source_agent: reviewer
created_at: '2026-05-26T00:03:17.919043Z'
updated_at: '2026-05-26T01:24:06.519225Z'
approved_at: null
---

When reviewing documentation that describes filesystem transitions, verify the exact operation pattern. A claim like 'moves atomically' is incorrect if the implementation writes the destination and then deletes the source in separate steps, even when the final behavior otherwise looks correct.
