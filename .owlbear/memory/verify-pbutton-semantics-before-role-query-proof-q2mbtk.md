---
id: f5ad5e3d-8958-45fc-b8e8-8e20a195dd84
title: Verify PButton semantics before role-query proof
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.86
state: approved
scope_agents:
- builder
- verifier
source_agent: builder
created_at: '2026-05-14T06:32:10.008051Z'
updated_at: '2026-05-16T23:05:55.399743Z'
approved_at: '2026-05-16T23:05:55.399785Z'
---

In Cockpit Vitest/jsdom tests, do not assume PDS `PButton` hosts satisfy `getByRole('button')` proof. If an AC requires button semantics, verify the rendered semantics directly; otherwise use a native `<button>` or test the explicit host-element contract the component is meant to provide.
