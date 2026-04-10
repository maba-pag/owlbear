---
id: 140
title: Upstream update scanner — monitor inspiration repos for relevant changes
status: archived
priority: nice-to-have
created: 2026-02-27T14:58:23.6475863+01:00
updated: 2026-02-28T23:53:06.0615672+01:00
started: 2026-02-28T01:09:39.0515379+01:00
completed: 2026-02-28T23:53:06.0615672+01:00
tags:
    - phase-10
    - research
    - tooling
class: standard
---

Monitor repos listed in docs/sources.md for new releases and significant changes. Periodically: check for new tags/releases, fetch changelogs, use LLM to judge if changes are relevant to OwlBear, create kanban tasks for worth-adopting updates.

This is a data-intake agent specialization. Could be a cron job once the scheduler exists (#149).
