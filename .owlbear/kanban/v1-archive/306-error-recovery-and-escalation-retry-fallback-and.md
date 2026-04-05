---
id: 306
title: Error recovery and escalation — retry, fallback, and human escalation
status: archived
priority: important
created: 2026-03-01T02:54:29.6350075+01:00
updated: 2026-03-03T15:03:06.4728949+01:00
started: 2026-03-01T18:37:24.9049342+01:00
completed: 2026-03-03T15:03:06.4728949+01:00
tags:
    - phase-13
    - agent
    - reliability
class: standard
---

## Context
When agent tasks fail (tool errors, LLM hallucinations, test failures), the system has no structured recovery. Need retry patterns, fallback strategies, and escalation to user.

## Acceptance Criteria
- [ ] RetryPolicy: configurable per-tool retry with exponential backoff (uses tenacity)
- [ ] Fallback: if tool fails N times, try alternative approach (e.g., terminal instead of git tool)
- [ ] Escalation: after retries exhausted, ask_user with error context and options
- [ ] Error classification: transient (retry), permanent (escalate), auth (refresh token)
- [ ] ON_ERROR hook enhanced with retry/escalate logic
- [ ] Agent receives structured error feedback: what failed, what was tried, suggested next steps
- [ ] Error journal: log all errors with resolution for future learning
- [ ] Unit tests for retry, fallback, and escalation paths
