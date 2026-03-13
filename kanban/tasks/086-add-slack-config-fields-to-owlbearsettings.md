---
id: 86
title: Add Slack config fields to OwlBearSettings
status: archived
priority: high
created: 2026-02-27T01:45:01.565478+01:00
updated: 2026-02-27T10:00:39.6110572+01:00
started: 2026-02-27T02:14:19.5091427+01:00
completed: 2026-02-27T10:00:39.6110572+01:00
tags:
    - phase-4
    - comms
    - slack
    - config
depends_on:
    - 85
class: standard
---

Add Slack token config to pydantic-settings. See docs/research/slack-integration.md.

AC:
- Add OWLBEAR_SLACK_APP_TOKEN (SecretStr, optional) to settings
- Add OWLBEAR_SLACK_BOT_TOKEN (SecretStr, optional) to settings
- Add OWLBEAR_SLACK_CHANNEL_ID (str, optional) to settings
- Validation: if any Slack field is set, all three must be set
- Tests for settings validation
