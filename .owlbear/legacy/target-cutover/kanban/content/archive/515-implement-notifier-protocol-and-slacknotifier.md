---
id: 515
title: Implement Notifier protocol and SlackNotifier (webhook + urllib)
status: archived
priority: medium
created: 2026-04-01 07:07:15.848253+02:00
updated: 2026-04-04 07:10:32.003959+02:00
started: 2026-04-04 07:09:43.371953+02:00
completed: 2026-04-04 07:09:43.371953+02:00
tags:
- phase-3
- scope:notifications
- scope:orchestrator
- type:build
depends_on:
- 514
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Implement the Notifier protocol and SlackNotifier class using Incoming Webhooks + stdlib urllib. Zero new dependencies.
See docs/research/slack-notification-v2.md for design (Option A).

## Acceptance Criteria
- [ ] `Notifier` runtime-checkable Protocol in `packages/orchestrator/src/owlbear/notifications.py` with methods:
  - `async on_dispatch(self, task_id: int, agent: str) -> None`
  - `async on_completion(self, task_id: int, agent: str, *, success: bool) -> None`
  - `async on_decision_request(self, task_id: int, reason: str) -> None`
- [ ] `SlackNotifier` class implementing `Notifier` in the same module
- [ ] Constructor: `SlackNotifier(webhook_url: str)` — stores the URL for Incoming Webhook POSTs
- [ ] HTTP POST via `urllib.request.urlopen` wrapped in `asyncio.to_thread()` to avoid blocking the event loop
- [ ] JSON payload: `{"text": "<mrkdwn message>"}` per Slack Incoming Webhook format
- [ ] Message formats:
  - dispatch: `*Dispatched* #{task_id} to {agent}`
  - success: `*Completed* #{task_id} ({agent})`
  - failure: `*Failed* #{task_id} ({agent})`
  - decision: `*Decision needed* #{task_id} — {reason}`
- [ ] All errors (`URLError`, `OSError`, etc.) caught via broad except, logged with `logging.warning`, never propagate
- [ ] Zero new package dependencies — only stdlib `urllib.request`, `json`, `asyncio`, `logging`
- [ ] All tests from #514 pass
