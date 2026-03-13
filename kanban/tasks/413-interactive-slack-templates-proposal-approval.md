---
id: 413
title: Interactive Slack templates — proposal, approval, progress Block Kit
status: archived
priority: important
created: 2026-03-01T20:20:04.7235129+01:00
updated: 2026-03-03T13:42:49.0368605+01:00
started: 2026-03-01T20:24:03.1356882+01:00
completed: 2026-03-03T13:42:49.0368605+01:00
tags:
    - phase-13
    - slack
    - channels
class: standard
---

From #307 slack-structured-proposals.md. Add format_interactive_proposal_blocks() (option buttons with action_ids), format_approval_blocks() (approve/deny with primary/danger styles), format_progress_blocks() (emoji progress bar) to slack_templates.py. AC: Interactive proposal blocks have clickable option buttons; approval blocks have approve (primary) + deny (danger) buttons; progress blocks render emoji bar with step/ETA; all return valid Block Kit JSON. Depends on #307.
