---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "D: Defer / do nothing"
notes: "No Slack available. Teams integration due to corp policy currently no possible. So defering right now."
# >> Agent metadata (do not edit)
task_id: 514
agent: architect
created: 2026-04-01
urgency: blocking
decision_type: feature-gate
impact_tier: 3
---

# Decision: Slack notification integration approach for v2 orchestrator

## Context

Task #26 (archived) researched Slack notification support for the v2 orchestrator.
The research doc (`docs/research/slack-notification-v2.md`) recommends adding a
`Notifier` protocol with a `SlackNotifier` implementation using Incoming Webhooks
and stdlib `urllib` — zero new dependencies.

This is a **new capability** (T3) that introduces a notification subsystem into the
orchestrator package. Four tasks are queued for implementation: #514 (tests), #515
(impl), #518 (tests for decision-request scan), #519 (decision-request scan impl).
All are blocked pending this decision.

## Options

### A: Incoming Webhook + stdlib urllib ← (rec:) recommended

- Effort: ~2 days, 4 tasks (2 TDD pairs)
- Trade-off: zero new deps (orchestrator stays at 3 deps), but sync urllib requires `asyncio.to_thread` wrapper
- Risk: if threading or message updates are needed later, migrate to slack_sdk
- Config: single env var `OWLBEAR_SLACK_WEBHOOK_URL`
- LOC estimate: ~35

### B: slack_sdk WebhookClient

- Effort: ~2 days, 4 tasks
- Trade-off: native async via `AsyncWebhookClient`, but adds `slack_sdk` (+ transitive deps) to a minimal package
- Risk: dependency bloat for a nice-to-have feature
- Config: single env var `OWLBEAR_SLACK_WEBHOOK_URL`

### C: Bot Token + slack_sdk WebClient

- Effort: ~3 days, 4 tasks
- Trade-off: full Slack API access (any channel, message updates), but adds `slack_sdk` + `aiohttp` (~15+ transitive deps) and requires bot token + channel config
- Risk: over-engineering for fire-and-forget alerts
- Config: 2 env vars (bot token + channel ID)

### D: Defer / do nothing

- Effort: 0
- Trade-off: no Slack notifications; users check the kanban board manually
- Risk: none immediate; notifications are nice-to-have priority

## Recommendation

.85 confidence — Option A. The orchestrator package currently has only 3 dependencies.
Adding `slack_sdk` for a nice-to-have, fire-and-forget notification feature violates
KISS/YAGNI. The `Notifier` protocol isolates the loop from the backend — swap to
`slack_sdk` later if bidirectional Slack is needed. See `docs/research/slack-notification-v2.md`
for the full analysis.

## Impact of Deferral

Tasks #514, #515, #518, #519 are blocked. This is a T3 mandatory decision — no
auto-resolve. The notification feature stays unbuilt until the user approves an approach.
No core functionality is affected (notifications are nice-to-have priority).
