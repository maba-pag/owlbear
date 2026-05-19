---
id: 952
title: Add priority-routed notifications for daemon and pipeline events
status: archived
priority: nice-to-have
created: 2026-03-23T01:43:14.8008034+01:00
updated: 2026-03-24T04:05:31.0104054+01:00
started: 2026-03-24T04:05:16.9184301+01:00
completed: 2026-03-24T04:05:16.9184301+01:00
tags:
    - agent
    - scope:core
    - scope:cli
    - slack
    - type:build
parent: 947
class: standard
---

See docs/research/ruflo-analysis.md section 5. AC: classify notifications by priority and route urgent events differently from informational events across CLI and Slack channels.

[[2026-03-24]] Tue 03:06

## Research

- Doc: docs/research/priority-routed-notifications.md

- Recommendation (.82 confidence): Two-tier priority routing (urgent + info) using separate NotificationHook instances in build_hooks()

- Key finding: existing HookReactionRouter provides event+match routing but NotificationHook currently treats all events identically with one backend chain

- Urgent tier (on_error, budget_warning, question_pending) -> Slack + sound + bell

- Info tier (task_complete) -> bell only

- New backend needed: SlackNotificationBackend (~40 LOC, uses AsyncWebClient)

- WindowsToastBackend deferred to separate optional-extra task

- Dedup with #963 handled at wiring layer: events under hook_reactions notify action excluded from tier lists

- Follow-up tasks created: #977 (config), #978 (SlackNotificationBackend), #979 (bootstrap wiring)

- Sources: Grafana notification policies (S1), Prefect automations (S2), plus 6 internal OwlBear sources

[[2026-03-24]] Tue 03:13

## Architecture Review

**Verdict:** SPLIT (acknowledged — researcher decomposed into #977, #978, #979)

### AC Assessment

| AC Line | Assessment | Action |

|---------|------------|--------|

| Classify notifications by priority | Multi-domain: spans config, core, bootstrap | Covered by #977 + #979 |

| Route urgent events differently from informational | Requires new backend + wiring | Covered by #978 + #979 |

| Across CLI and Slack channels | Introduced SlackNotificationBackend | Covered by #978 |

### Architecture Notes

Task #952 spans three domains (config, core, bootstrap) per architecture-standards domain taxonomy. The researcher correctly decomposed this into three single-domain children:

- #977: config domain (OwlBearSettings tier fields)

- #978: core domain (SlackNotificationBackend in notification_hook.py)

- #979: bootstrap domain (build_hooks two-tier wiring)

Research doc at docs/research/priority-routed-notifications.md is thorough (8 sources, trade-off matrix, .82 confidence). Option A (two-tier config with separate NotificationHook instances) follows existing patterns — NotificationHook already supports configurable event lists and backend chains at src/owlbear/core/notification_hook.py:86-95 and src/owlbear/bootstrap/hooks.py:55-58.

Dedup with #963 is correctly scoped to the wiring layer (#979), not the runtime.

### Dependency Gap

- #979 depends_on should include #977 (needs config fields) and #978 (needs SlackNotificationBackend), in addition to #955. Children at ideation — their architect reviews will refine AC and fix deps.

### Changes Made

- Moved #952 to done as completed research parent (no remaining impl work).

- Children #977, #978, #979 remain at ideation for their own pipeline.

### Dependencies

- Verified: #955 (schema + router) is in docs status, nearly complete.

- Noted: #979 missing depends_on #977 and #978 — to be corrected at child architect review.

[[2026-03-24]] Tue 04:04

## Audit

### AC Verification

| AC Line | Evidence | Status |

|---------|----------|--------|

| Classify notifications by priority | Research doc section 3.1 maps 7 events to urgent/info/silent tiers with rationale | PASS |

| Route urgent events differently from informational | Option A analysis (section 3.2-3.3) with trade-off matrix; follow-up tasks #977 (config), #978 (Slack backend), #979 (bootstrap wiring) decompose implementation | PASS |

| Across CLI and Slack channels | Section 3.4 specifies SlackNotificationBackend; #978 implements it | PASS |

| Research doc exists | docs/research/priority-routed-notifications.md: 8 sources, trade-off matrix, .82 confidence recommendation | PASS |

| Follow-up tasks created at ideation or higher | #977 (backlog), #978 (todo), #979 (ideation) — all reference parent research doc | PASS |

| Architect reviewed | Architecture Review section: SPLIT verdict, dependency gap noted for #979 | PASS |

### Test Results

- pytest full suite: 4103 passed, 98 failed, 20 skipped. All 98 failures are pre-existing from other in-progress tasks (age-threshold RED #921/#925, board-fixtures module #925, daemon-fallback #809, etc.). None related to #952.

- ruff: pre-existing warnings in other files; #952 produced no source code, only docs/research/priority-routed-notifications.md.

### AC Quality Score: 4/5

- AC was adequately specific for a research task — stated what to classify, the routing distinction, and target channels.

- Minor gap: AC did not specify what classify means operationally (tiers vs. labels vs. scores). Researcher filled this sensibly with two-tier model.

### Upstream Commit Gap

- Research doc was untracked (not committed by researcher). Committed by auditor: 00ef77a.

### Confidence: .97

### Action: archive

## Commits

| Commit | Type | Files | Tasks |

|--------|------|-------|-------|

| 00ef77a | docs | docs/research/priority-routed-notifications.md | #952 |
