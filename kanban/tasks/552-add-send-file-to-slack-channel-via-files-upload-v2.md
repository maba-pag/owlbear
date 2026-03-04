---
id: 552
title: Add send_file to Slack channel via files_upload_v2
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:55.0178377+01:00
updated: 2026-03-04T07:38:55.0178377+01:00
tags:
    - audit
    - channels
class: standard
---

INT-17: ScreenshotService.deliver tries send_file but Slack channel doesnt implement it. Silently skips. Add via Slacks files_upload_v2 API. AC: screenshots deliverable via Slack. See docs/integration-audit.md.
