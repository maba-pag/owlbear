---
id: 328
title: Test SlackChannel.send_image — mock files_upload_v2 with file and bytes
status: archived
priority: needed
created: 2026-03-01T11:16:26.8919272+01:00
updated: 2026-03-01T17:10:00.1271129+01:00
started: 2026-03-01T11:20:57.458613+01:00
completed: 2026-03-01T17:10:00.1271129+01:00
tags:
    - phase-12
    - slack
    - channels
    - test
class: standard
---

## Acceptance Criteria
- [ ] Test send_image(path) calls files_upload_v2 with file=path, channel, initial_comment
- [ ] Test send_image(bytes_data) calls files_upload_v2 with file=bytes_data
- [ ] Test optional thread_ts is forwarded
- [ ] Test caption param becomes initial_comment and title
- [ ] Test error fallback: when files_upload_v2 raises, falls back to sending caption as text via send()
- [ ] Mock AsyncWebClient.files_upload_v2 to verify exact call params

See docs/research/slack-rich-messaging.md S3.4
