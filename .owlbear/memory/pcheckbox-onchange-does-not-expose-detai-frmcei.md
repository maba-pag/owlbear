---
id: a7cb3758-91b0-4ff2-8553-957cb37084b2
title: PCheckbox onChange does not expose detail.checked
categories:
- pitfall
- domain-knowledge
confidence: 0.96
state: curated
scope_agents:
- verifier
- builder
- shaper
source_agent: reviewer
created_at: '2026-05-17T11:30:09.035171Z'
updated_at: '2026-05-17T13:09:19.022495Z'
approved_at: null
---

When reviewing Cockpit PDS checkbox migrations, do not accept handlers or tests that read CustomEvent.detail.checked. In the installed @porsche-design-system/components-react package, CheckboxChangeEventDetail is Event and the wrapper forwards the raw change event; the checked state must be read from the emitted event/host. Unit tests that fire change with detail:{checked:true} can false-green a broken implementation.
