---
id: 329
title: Implement SlackChannel.send_image — file upload via files_upload_v2
status: archived
priority: needed
created: 2026-03-01T11:16:38.4374408+01:00
updated: 2026-03-01T17:10:00.7348313+01:00
started: 2026-03-01T11:21:28.3274141+01:00
completed: 2026-03-01T17:10:00.7348313+01:00
tags:
    - phase-12
    - slack
    - channels
depends_on:
    - 328
class: standard
---

## Acceptance Criteria
- [ ] Add send_image(file_or_bytes: str | Path | bytes, caption: str = '', *, thread_ts: str | None = None) to SlackChannel
- [ ] Wraps files_upload_v2(file=..., channel=self._channel_id, title=caption, initial_comment=caption, thread_ts=...)
- [ ] Accepts str path, Path object, or raw bytes
- [ ] On files_upload_v2 error: log warning, fall back to send(caption) as plain text
- [ ] Method on SlackChannel only — no ChannelPlugin protocol change
- [ ] NOTE: Requires files:write bot scope — document in method docstring

See docs/research/slack-rich-messaging.md S3.4
