---
id: 519d1835-1106-403d-8645-cf9347694ca4
title: Omitted-if-empty ACs need negative proof
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.85
state: curated
scope_agents:
- reviewer
- code-reader
- challenger
source_agent: reviewer
created_at: '2026-05-25T22:46:43.189054Z'
updated_at: '2026-05-26T01:23:58.853311Z'
approved_at: null
---

When an AC says a field or text is omitted if empty, do not PASS on a positive-only assertion for the non-empty branch. Require at least one test that would fail if an empty input rendered visible fallback text or otherwise violated the omission clause.
