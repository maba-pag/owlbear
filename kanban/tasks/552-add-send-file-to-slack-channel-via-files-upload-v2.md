---
id: 552
title: Add send_file to Slack channel via files_upload_v2
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:55.0178377+01:00
updated: 2026-03-07T01:01:45.4497145+01:00
started: 2026-03-07T00:55:28.3918725+01:00
tags:
    - audit
    - channels
class: standard
---

INT-17: SlackChannel missing send_file. ScreenshotService.deliver already works via send_image (tier 1), but direct send_file callers skip to send fallback. Add send_file as thin delegate to send_image(path, caption=caption or path.name). Requires files:write scope (already granted). ~5 LOC impl + ~15 LOC tests. See docs/slack-send-file-research.md

AC:
- [ ] SlackChannel.send_file(path, *, caption) exists with same signature as CLIChannel
- [ ] Delegates to files_upload_v2 (via send_image)
- [ ] Caption passed as title + initial_comment when provided
- [ ] No-caption uses path.name as default title
- [ ] Upload failure falls back to channel.send plain text
- [ ] Tests cover: happy path, caption, no-caption default, error fallback
