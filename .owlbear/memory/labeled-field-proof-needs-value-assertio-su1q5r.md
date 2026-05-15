---
id: d37d42b1-0f56-4619-b42a-1bd6f8cbf04a
title: Labeled field proof needs value assertions
categories:
- pitfall
- process
confidence: 0.88
state: approved
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-15T05:49:01.078791Z'
updated_at: '2026-05-15T21:25:00.562453Z'
approved_at: '2026-05-15T21:25:00.562513Z'
---

In review of UI specs, do not PASS tests that only prove field labels and container structure when the AC says the UI contains labeled fields for concrete data. Require proof of rendered values, or at least non-label suffix content, for each named field; otherwise label-only shells can false-green.
