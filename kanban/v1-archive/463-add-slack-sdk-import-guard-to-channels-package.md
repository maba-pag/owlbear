---
id: 463
title: Add slack_sdk import guard to channels package
status: archived
priority: critical
created: 2026-03-04T07:37:43.9369413+01:00
updated: 2026-03-06T19:28:08.5190068+01:00
started: 2026-03-06T00:25:44.2633407+01:00
completed: 2026-03-06T19:28:08.5190068+01:00
tags:
    - audit
    - bugfix
    - config
    - channels
class: standard
---

## Problem
import owlbear.channels crashes when slack_sdk is not installed because:
- channels/slack.py L9-11 imports slack_sdk at top level without guard
- channels/__init__.py re-exports SlackChannel, triggering the crash

## Approach
Guard slack_sdk imports in slack.py only. Keep __init__.py re-export  matches voice/__init__.py pattern (exports VoiceChannel unconditionally because deps are guarded at module level).

### Pattern (6+ modules use this):
`python
try:
    from slack_sdk.socket_mode.aiohttp import SocketModeClient
    ...
except ImportError:  # pragma: no cover
    SocketModeClient = None  # type: ignore[assignment]
    ...
``nRuntime guard in SlackChannel.__init__ before any sdk usage:
`python
if AsyncWebClient is None:  # pragma: no cover
    msg = 'slack_sdk is not installed. Install with: uv sync --extra slack'
    raise ImportError(msg)
``n
### Why __init__.py needs no change:
from __future__ import annotations is present in slack.py  type annotations
are strings, not evaluated at runtime. With guarded imports, the module loads
cleanly, SlackChannel class is defined, __init__.py import succeeds.
Same pattern as voice/__init__.py exporting VoiceChannel.

### Key references:
- browser/manager.py L20-25, L73-78 (playwright guard)
- voice/tts.py L24-29, L67-72 (pyttsx3 guard)
- voice/channel.py L40-45, L181-190 (sounddevice guard)
- knowledge/qdrant.py L17-23, L108-115 (qdrant-client guard)
- web_search.py L26-37, L138-146 (ddgs + trafilatura guard)
- bootstrap.py L223 imports from owlbear.channels.slack directly (unaffected)

## AC
- [ ] import owlbear.channels succeeds without slack_sdk installed
- [ ] from owlbear.channels import SlackChannel succeeds without slack_sdk (re-export preserved)
- [ ] from owlbear.channels.slack import SlackChannel succeeds without slack_sdk
- [ ] SlackChannel(app_token='x', bot_token='x', channel_id='x') raises ImportError with message containing 'uv sync --extra slack' when slack_sdk missing
- [ ] When slack_sdk IS installed, all existing tests in test_slack_channel.py pass unchanged
- [ ] Guard uses try/except ImportError + # pragma: no cover on except branch + # type: ignore[assignment] on sentinel
- [ ] Only slack.py is changed; channels/__init__.py is NOT modified

## TDD
Builder: write failing tests for AC 1-4 before implementing. Test slack_sdk
absence by patching the import (unittest.mock). See test_slack_channel.py for
existing test patterns.
