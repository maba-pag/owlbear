---
id: b8ad4bc6-9ceb-42df-bb4a-418a4442a305
title: 'Builder: anchor to executed RED baseline, not AC text'
categories:
- pitfall
- process
confidence: 0.9
state: curated
scope_agents:
- builder
- test-writer
source_agent: memory-curator:file-inbox
created_at: '2026-05-13T04:43:26.005932Z'
updated_at: '2026-05-13T04:43:42.967907Z'
approved_at: null
---

Task AC can claim "all N tests FAIL" while the executed baseline shows most tests already passing. Trust the executed RED run — AC text drifts during task iteration. Implement only for the actual failures found in the live baseline run. In retry-loop tasks, always extract the latest Architecture Review refinement and the latest test-writer section first before reading historical AC notes.
