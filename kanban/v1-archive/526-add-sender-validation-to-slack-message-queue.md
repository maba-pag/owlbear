---
id: 526
title: Add sender validation to Slack message queue
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:33.3312171+01:00
updated: 2026-03-22T19:17:37.7673657+01:00
started: 2026-03-07T00:16:19.9599646+01:00
completed: 2026-03-22T19:17:37.7673657+01:00
tags:
    - audit
    - security
    - channels
blocked: true
block_reason: 'Stale research parent: child tasks #795/#796/#797 and RED predecessors #801/#802/#804 are archived, and the Slack sender validation, rate limiting, and logging behavior already exists in the repo; do not redispatch.'
class: standard
---

SEC-15: Messages from Slack DMs fed to agent as prompts with no sanitization. Inherent to design, but mitigate: validate messages come from expected user IDs, add rate limiting, log all incoming messages. See docs/security-audit.md.

Research complete: see docs/research/slack-sender-validation.md. Recommendation: (1) Config allowlist with slack_allowed_user_ids (.85 confidence), (2) Sliding window rate limiter (.80), (3) Structured INFO logging (.85). Follow-up implementation tasks created.

## AC

- [x] Research doc at docs/research/slack-sender-validation.md
- [x] Recommendation with confidence scores (.80-.85)
- [x] Follow-up implementation tasks created

[[2026-03-21]] Sat 04:15
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Research doc at docs/research/slack-sender-validation.md | Exists and was sufficient to decompose the work, but it is not builder work | Keep as traceability only; do not dispatch parent card |
| Recommendation with confidence scores (.80-.85) | Research already split the recommended concerns into separate atomic tasks | Use child tasks as implementation contracts |
| Follow-up implementation tasks created | Already true: #795/#796/#797 plus RED predecessors #801/#802/#804 are archived | Parent card is stale in backlog and should be removed from dispatch flow |

### Architecture Notes
- This card is a completed research umbrella, not an implementation task. Its AC verifies research deliverables, not code changes.
- The recommendations span three distinct concerns: sender allowlist, rate limiting, and audit logging. Approving #526 to `todo` would violate atomicity by sending a multi-concern parent card into builder flow.
- The codebase already contains the resulting architecture in src/owlbear/config.py, src/owlbear/bootstrap/channel.py, and src/owlbear/channels/slack.py.
- `slack_allowed_user_ids` and `slack_rate_limit_per_minute` exist in config, `create_channel()` wires them into `SlackChannel`, and `_handle_socket_event()` performs subtype filtering, allowlist checks, rate limiting, and safe logging.
- TDD compliance already exists at the child-task level via archived RED tasks #801, #802, and #804.
- Existing source-of-truth contracts are the archived child tasks, not this parent card.

### Changes Made
- Claimed #526 as architect.
- Appended this architecture review.
- Blocking the stale parent card so it cannot be redispatched into builder flow.

### Dependencies
- Verified archived child tasks: #801 -> #795, #802 -> #796, #804 -> #797.
- Verified repo implementation exists in src/owlbear/config.py, src/owlbear/bootstrap/channel.py, and src/owlbear/channels/slack.py.
- No missing prerequisite remains on this parent card; the work has already been decomposed and delivered.
