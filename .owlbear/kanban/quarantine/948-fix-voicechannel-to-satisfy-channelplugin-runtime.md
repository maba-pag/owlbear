---
id: 948
title: Fix VoiceChannel to satisfy ChannelPlugin @runtime_checkable Protocol
status: archived
priority: nice-to-have
created: 2026-03-23T01:04:09.9951816+01:00
updated: 2026-03-26T15:59:43.8717144+01:00
tags:
    - audit
    - scope:core
    - type:build
    - voice
class: standard
---

isinstance(VoiceChannel(), ChannelPlugin) returns False because VoiceChannel does not define send_file, send_blocks, or send_image. ChannelPlugin is a @runtime_checkable Protocol; Python's structural isinstance check requires these attributes to be present on the concrete class.\n\n**Root cause found during #521 review cycle.**\n\n## AC\n1. VoiceChannel defines or inherits send_file, send_blocks, send_image (either by inheriting from ChannelPlugin as an ABC or by adding concrete method implementations).\n2. isinstance(VoiceChannel(), ChannelPlugin) returns True.\n3. tests/test_voice_channel.py::TestVoiceChannelProtocol::test_isinstance_channel_plugin passes.\n4. No existing VoiceChannel behavior is broken.

## Architecture Review

**Verdict:** BLOCK -> ideation

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| VoiceChannel defines or inherits send_file, send_blocks, send_image | Already satisfied. VoiceChannel subclasses ChannelPlugin (channel.py line 48) and inherits defaults from base.py lines 38-71. | No work needed |
| isinstance(VoiceChannel(), ChannelPlugin) returns True | Already True. Verified via runtime check and pytest. | No work needed |
| test_isinstance_channel_plugin passes | Already passes (1 passed, 0.10s). | No work needed |
| No existing VoiceChannel behavior is broken | No changes required, so nothing to break. | No work needed |

### Architecture Notes

The task premise is incorrect. VoiceChannel already explicitly subclasses ChannelPlugin via class VoiceChannel(ChannelPlugin) at src/owlbear/voice/channel.py:48. Because ChannelPlugin defines default implementations for send_file (base.py:38), send_blocks (base.py:51), and send_image (base.py:62), VoiceChannel inherits them automatically. The isinstance check returns True because VoiceChannel is a direct subclass.

Evidence:

- uv run python -c verified isinstance=True, hasattr for all three methods=True, callable=True
- uv run pytest tests/test_voice_channel.py::TestVoiceChannelProtocol::test_isinstance_channel_plugin -> 1 passed

The root-cause analysis from the #521 review cycle appears to have been incorrect, or the issue was resolved by a subsequent change that added the default implementations to ChannelPlugin.

### Changes Made

- Blocked task to ideation: no implementation work exists.

[[2026-03-26]] Thu 15:59

## Research

**Verdict:** Non-bug (already fixed by #521).

### Findings

The task premise was valid when created (2026-03-23T01:04) but the fix landed 4 hours later via commit 329ef64 (builder, #521). That commit changed `class VoiceChannel:` to `class VoiceChannel(ChannelPlugin):` and added the import, giving VoiceChannel full inheritance of the default `send_file`, `send_blocks`, and `send_image` methods.

### Independent Verification (2026-03-26)

- `isinstance(VoiceChannel(), ChannelPlugin)` returns `True`
- `hasattr` for send_file, send_blocks, send_image all `True`
- `pytest tests/test_voice_channel.py::TestVoiceChannelProtocol::test_isinstance_channel_plugin` -> 1 passed (0.86s)
- MRO confirms ChannelPlugin in VoiceChannel's inheritance chain

### Root Cause of False Positive

Race condition in the task pipeline: #948 was created from #521's review findings, but #521's builder committed the fix before #948 was triaged. The architect correctly identified this on review and blocked the task.

### Disposition

No follow-up tasks needed. All 4 AC lines are already satisfied. Recommend archival as resolved-by-#521.
