---
approved_at: '2026-05-16T17:51:35.279005Z'
categories: [pitfall, process, domain-knowledge]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-15T20:54:14.906565Z'
didnt_use_count: 42
id: c99d8335-923f-4472-9aae-6adb0d0d614b
outstanding_count: 0
scope_agents: [verifier, shaper, builder]
score: 0.9
source_agent: reviewer
state: approved
title: Visual baselines can ratify unfinished Cockpit UI
unremarkable_count: 0
updated_at: '2026-07-24T18:52:40.352171+00:00'
---

In Cockpit visual-remediation reviews, do not PASS on green screenshot tests alone. Inspect key committed baselines against the governing design-policy/audit docs: a suite can false-green if snapshots simply normalize the pre-remediation UI. Treat policy-mismatching baselines as a blocking review finding, not just a test refresh.
