---
id: 732
title: 'Research: LLM cost tracking per operation'
status: backlog
priority: nice-to-have
created: 2026-03-10T19:53:20.222927+01:00
updated: 2026-03-10T19:53:20.222927+01:00
tags:
    - research
    - scope:core
    - phase-research
class: standard
---

**Source:** #597 edgequake-research S3.3
EdgeQuake tracks per-operation LLM costs. OwlBear has no cost visibility.

**AC:**
1. Survey OwlBear LLM call sites.
2. Evaluate token-counting + cost-accumulator patterns.
3. Propose minimal cost tracker for httpx transport.
4. Document in docs/research/llm-cost-tracking-research.md.
5. Create follow-up implementation tasks if warranted.
