---
approved_at: null
categories: [pitfall, process]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-25T17:12:29.890371Z'
didnt_use_count: 0
id: d2b27234-1dac-49c7-9c68-33040f6864d0
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: reviewer
state: curated
title: Frontend API rewires need normalized-consumer proof
unremarkable_count: 0
updated_at: '2026-07-14T23:31:29.059920+00:00'
---

For a frontend API rewire, endpoint/path proof is insufficient when an affected hook or consumer depends on normalized output. Verify the normalized contract at that boundary; durable tests encoding the retired contract are a blocking regression signal.
