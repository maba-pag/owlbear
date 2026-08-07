---
approved_at: '2026-05-16T23:05:55.399785Z'
categories: [pitfall, tool-usage, domain-knowledge]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-14T06:32:10.008051Z'
didnt_use_count: 19
id: f5ad5e3d-8958-45fc-b8e8-8e20a195dd84
outstanding_count: 0
scope_agents: [builder]
score: 0.86
source_agent: builder
state: approved
title: Verify PButton semantics before role-query proof
unremarkable_count: 0
updated_at: '2026-08-07T00:26:06.204021+00:00'
---

In Cockpit Vitest/jsdom tests, do not assume PDS `PButton` hosts satisfy `getByRole('button')` proof. If an AC requires button semantics, verify the rendered semantics directly; otherwise use a native `<button>` or test the explicit host-element contract the component is meant to provide.
