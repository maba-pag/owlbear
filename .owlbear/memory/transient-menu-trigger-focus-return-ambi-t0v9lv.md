---
id: 99e06211-10c6-44c7-b6e8-9130f12ab9fa
title: Transient menu trigger focus-return ambiguity
categories:
- pitfall
- process
confidence: 0.9
state: curated
scope_agents:
- reviewer
- architect
source_agent: reviewer
created_at: '2026-05-15T07:16:07.292293Z'
updated_at: '2026-05-15T09:11:22.459734Z'
approved_at: null
---

For reviewer checks on modal/dialog focus return, reject tests that pre-focus a stable ancestor when the modal actually opens from a transient context-menu item that is torn down on selection. If AC says return focus to the triggering element, architecture must clarify the stable target first; otherwise ancestor-containment assertions can false-green.
