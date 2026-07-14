---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.96
contested_by_task: null
created_at: '2026-05-17T11:30:09.035171Z'
didnt_use_count: 0
id: a7cb3758-91b0-4ff2-8553-957cb37084b2
outstanding_count: 0
scope_agents: [verifier, builder, shaper]
score: 0.0
source_agent: reviewer
state: deleted
title: PCheckbox onChange does not expose detail.checked
unremarkable_count: 0
updated_at: '2026-07-14T23:57:04.820540+00:00'
---

When reviewing Cockpit PDS checkbox migrations, do not accept handlers or tests that read CustomEvent.detail.checked. In the installed @porsche-design-system/components-react package, CheckboxChangeEventDetail is Event and the wrapper forwards the raw change event; the checked state must be read from the emitted event/host. Unit tests that fire change with detail:{checked:true} can false-green a broken implementation.
