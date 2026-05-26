---
id: 1c73e27f-d353-4fc4-aec2-f03fa840e5cd
title: Cockpit PTextarea tests need PDS event path
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.91
state: curated
scope_agents:
- reviewer
- test-writer
- builder
source_agent: reviewer
created_at: '2026-05-25T22:28:47.371485Z'
updated_at: '2026-05-26T01:23:58.818475Z'
approved_at: null
---

In Cockpit reviews, do not accept tests that drive p-textarea like a native textarea. For resolve-notes and similar PDS controls, first verify the host is p-textarea and prefer the documented CustomEvent detail.value path; a fireEvent.change proof can false-localize source defects or create contradictory rerun evidence.
