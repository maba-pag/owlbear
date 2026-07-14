---
approved_at: null
categories: [pitfall, tool-usage, domain-knowledge]
confidence: 0.91
contested_by_task: null
created_at: '2026-05-25T22:28:47.371485Z'
didnt_use_count: 0
id: 1c73e27f-d353-4fc4-aec2-f03fa840e5cd
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Cockpit PTextarea tests need PDS event path
unremarkable_count: 0
updated_at: '2026-07-14T23:06:18.155400+00:00'
---

In Cockpit reviews, do not accept tests that drive p-textarea like a native textarea. For resolve-notes and similar PDS controls, first verify the host is p-textarea and prefer the documented CustomEvent detail.value path; a fireEvent.change proof can false-localize source defects or create contradictory rerun evidence.
