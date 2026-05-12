---
id: c3c10277-8d8c-4e7a-b51b-19f82d2c305d
title: 'Cockpit: PDS component proof surface is host-state, not shadow DOM'
categories:
- domain-knowledge
- process
- pitfall
confidence: 0.88
state: curated
scope_agents:
- reviewer
- builder
- test-writer
source_agent: reviewer
created_at: '2026-05-12T19:40:01.074031Z'
updated_at: '2026-05-12T21:24:50.752232Z'
approved_at: null
---

In Cockpit Vitest tests, PDS component proof surface is host-state (props like `open`, `heading`, `description`, callback handlers like `onDismiss`, `onMutationSuccess`), not raw shadow DOM text content. Reviewer must not fail tests for asserting host-state on PDS components (e.g., p-banner, p-modal) rather than inspecting shadow DOM internals.
