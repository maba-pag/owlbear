---
id: 450666b1-90ab-466b-ba9e-f544ff713838
title: Mutation-contract reviews need all write paths
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- reviewer
- builder
- architect
source_agent: copilot
created_at: '2026-05-17T01:36:07.331320Z'
updated_at: '2026-05-17T01:48:10.889105Z'
approved_at: null
---

For mutation-contract tasks, review every path that performs the write, not only the public facade. Builders can update one helper while alternate flows still bypass CAS, rollback, validation, or side-effect guards.
