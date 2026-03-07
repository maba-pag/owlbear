---
id: 540
title: 'Align retry max attempts: docs say 5, code uses 3'
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:44.9656782+01:00
updated: 2026-03-07T00:37:34.9277344+01:00
started: 2026-03-07T00:36:40.0707744+01:00
tags:
    - audit
    - resilience
    - docs
class: standard
---

R-5: python.instructions.md says max 5 attempts but all retry code uses stop_after_attempt(3). Either update docs to 3 or code to 5. AC: docs and code agree. See docs/resilience-audit.md.

## Research (trivial alignment)

N/A - trivial alignment. Rationale: every retry site in the codebase uses 3 attempts.

**Evidence (code uses 3 unanimously):**
- providers/copilot.py L62: stop_after_attempt(3)
- core/retry.py L45: stop_after_attempt(3)
- tools/hooked.py L59: _MAX_ATTEMPTS = 3
- daemon.py L45: _TRANSIENT_MAX_RETRIES = 3

**Docs that say 5:**
- .github/instructions/python.instructions.md L34
- .github/copilot-instructions.md L46 (tech stack table)

**Recommendation (.95):** Update both doc files to say 'max 3 attempts'. Code is correct  3 was deliberately chosen (daemon-retry-reconciliation-research.md notes 3x3=9 multiplicative attempts already excessive).

**Implementation:** Change 'max 5 attempts' to 'max 3 attempts' in python.instructions.md L34 and copilot-instructions.md L46.
