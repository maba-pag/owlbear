---
approved_at: '2026-05-16T20:10:07.894377Z'
categories: [pitfall, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-15T19:26:50.489934Z'
didnt_use_count: 1
id: 98cb083c-b8c9-4f04-b4bf-9f495bee79e4
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.84
source_agent: builder
state: approved
title: Cockpit host-level tabIndex audits need host proof
unremarkable_count: 0
updated_at: '2026-07-17T15:35:46.174198+00:00'
---

For Cockpit AC-7 or Playwright audits that query PDS/custom-element hosts directly, verify host `tabIndex` separately from internal control focusability. A host can expose `tabIndex=-1` even when its internals are usable; remediate the intended interactive host or document a precise exception instead of treating internal focusability as proof.
