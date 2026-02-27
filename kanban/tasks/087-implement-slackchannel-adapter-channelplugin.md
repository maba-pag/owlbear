---
id: 87
title: Implement SlackChannel adapter (ChannelPlugin)
status: ideation
priority: high
created: 2026-02-27T01:45:07.8739871+01:00
updated: 2026-02-27T01:45:07.8739871+01:00
tags:
    - phase-4
    - comms
    - slack
    - agent
depends_on:
    - 85
    - 86
class: standard
---

Create src/owlbear/channels/slack.py implementing ChannelPlugin protocol. See docs/slack-integration-research.md.

AC:
- SlackChannel class with name='slack' property
- send(message) calls AsyncWebClient.chat_postMessage
- receive() listens for message.im events via SocketModeClient, returns event text
- Connection lifecycle: connect via SocketModeClient, auto-reconnect on disconnect
- Configurable via SlackSettings (app_token, bot_token, channel_id)
- isinstance(SlackChannel(...), ChannelPlugin) compliance
