---
id: c99d8335-923f-4472-9aae-6adb0d0d614b
title: Visual baselines can ratify unfinished Cockpit UI
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.9
state: approved
scope_agents:
- reviewer
- architect
- test-writer
source_agent: reviewer
created_at: '2026-05-15T20:54:14.906565Z'
updated_at: '2026-05-16T17:51:35.278986Z'
approved_at: '2026-05-16T17:51:35.279005Z'
---

In Cockpit visual-remediation reviews, do not PASS on green screenshot tests alone. Inspect key committed baselines against the governing design-policy/audit docs: a suite can false-green if snapshots simply normalize the pre-remediation UI. Treat policy-mismatching baselines as a blocking review finding, not just a test refresh.
