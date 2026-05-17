---
id: 29daadae-79b4-4a98-8764-10a926a8825f
title: Widely consumed API refactors need regression gates
categories:
- pitfall
- process
confidence: 0.84
state: curated
scope_agents:
- architect
- planner
- reviewer
- builder
source_agent: copilot
created_at: '2026-05-17T01:36:52.142915Z'
updated_at: '2026-05-17T01:48:10.950861Z'
approved_at: null
---

For refactor tasks that change a widely consumed API, acceptance criteria should include a full-suite or domain-wide regression gate and name the suites or consumers that must be updated. Scoped green evidence can miss broad breakage across old call sites.
