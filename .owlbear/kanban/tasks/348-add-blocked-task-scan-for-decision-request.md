---
id: 348
title: Add blocked-task scan for decision-request notifications
status: backlog
priority: nice-to-have
created: 2026-03-30T20:41:58.3577972+02:00
updated: 2026-04-05T12:53:49.2122975+02:00
tags:
    - phase-3
    - scope:orchestrator
    - scope:notifications
    - type:build
depends_on:
    - 347
class: standard
---

[[2026-04-05]] Sun 12:53
## Research
- Research doc: .owlbear/research/blocked-task-scan-decision-notifications.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: Defer to align with Decision #514 (confidence: .80)
- Follow-up tasks created: #631 (ideation — revisit when notification channel enabled)
- Decision requests: none (T1 — applying existing approved decision)

## Challenge Results
- Challenger: reconsider (confidence in original: .85)
- Key challenges: #514 scope ambiguity; spec-reality gap risk (gate_warned precedent); "zero cost" claim inaccurate for skill-only approach
- Researcher response: accepted — revised from Option C (skill enhancement, .85) to Option A (defer, .80)
- Revised rationale: task falls within #514 deferral scope; existing coverage (bearclaw status, planner pending field, scribe Step 0) fills the gap; building scan without notification consumer is YAGNI
