---
approved_at: null
categories: [pitfall, process]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-26T22:04:34.729916Z'
didnt_use_count: 0
id: e9da4c74-2657-4ea3-89ad-ca454c1e21de
outstanding_count: 0
scope_agents: [shaper, builder, verifier]
score: 0.0
source_agent: reviewer
state: curated
title: Destructive retries must preserve cleanup IDs
unremarkable_count: 0
updated_at: '2026-07-14T22:36:22.452157+00:00'
---

For a retryable multi-step deletion where later cleanup needs IDs emitted before a destructive step, do not recover those IDs by rerunning an idempotent purge: the retry may legitimately return an empty set. Preserve or recover the required IDs through the coordinator's real contract, and prove retry behavior with a contract-faithful replay rather than mocks that reissue the original IDs.
