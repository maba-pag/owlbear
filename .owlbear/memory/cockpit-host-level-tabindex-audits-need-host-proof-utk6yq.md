---
id: 98cb083c-b8c9-4f04-b4bf-9f495bee79e4
title: Cockpit host-level tabIndex audits need host proof
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: approved
scope_agents:
- builder
- verifier
source_agent: builder
created_at: '2026-05-15T19:26:50.489934Z'
updated_at: '2026-05-16T20:10:07.894365Z'
approved_at: '2026-05-16T20:10:07.894377Z'
---

For Cockpit AC-7 or Playwright audits that query PDS/custom-element hosts directly, verify host `tabIndex` separately from internal control focusability. A host can expose `tabIndex=-1` even when its internals are usable; remediate the intended interactive host or document a precise exception instead of treating internal focusability as proof.
