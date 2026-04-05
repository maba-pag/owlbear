---
id: 360
title: Daemon loop structured recovery with error classification
status: archived
priority: needed
created: 2026-03-01T20:11:43.2030399+01:00
updated: 2026-03-02T09:14:35.7656399+01:00
started: 2026-03-01T20:22:21.3718808+01:00
completed: 2026-03-02T09:14:35.7656399+01:00
tags:
    - phase-13
    - daemon
    - reliability
depends_on:
    - 357
class: standard
---

## Daemon Loop Structured Recovery

Replace bare except in run_daemon() (src/owlbear/daemon.py L253-267) with classified error handling.

### Per-Category Behavior

- TRANSIENT: retry agent.turn(message) with exponential backoff (base=1s, max=30s, jitter), max 3 attempts
- AUTH: refresh token via create_copilot_model(), update model, retry once (max 1)
- PERMANENT: log ERROR, send error to channel, continue loop
- TOOL_SEMANTIC: treat as permanent at daemon level, send error to channel

### Acceptance Criteria

- [ ] run_daemon() uses classify_error(exc) to determine recovery strategy
- [ ] Transient errors: retry with exponential backoff, max 3 attempts
- [ ] Auth errors: token refresh + retry once (preserves existing behavior)
- [ ] Permanent errors: log + send error to channel, never crash daemon
- [ ] Tool-semantic errors: same as permanent at daemon level
- [ ] After transient retries exhausted: send error to channel, continue loop
- [ ] Remove _is_auth_error() — replaced by classify_error() from core.errors
- [ ] Backoff uses jitter (random factor) to prevent thundering herd
- [ ] Daemon never crashes from a single message failure
- [ ] Tests in tests/test_daemon.py (extend existing, TDD)
- [ ] Ruff clean

### Architecture Notes

- Depends on #357 for classify_error() and ErrorCategory
- Layer 4 (outermost) — retry around whole agent turn
- Subsumes existing _is_auth_error + auth retry block (L258-264)
- channel.send(f'Error: ...') will be replaced with ToolError JSON in #363 follow-up
- See docs/research/error-recovery.md section 3.2 (L4) and 4.4
