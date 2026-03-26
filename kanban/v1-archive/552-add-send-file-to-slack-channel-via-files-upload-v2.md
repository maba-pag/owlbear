---
id: 552
title: Add send_file to Slack channel via files_upload_v2
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:55.0178377+01:00
updated: 2026-03-22T19:17:42.8212527+01:00
started: 2026-03-07T00:55:28.3918725+01:00
completed: 2026-03-22T19:17:42.8212527+01:00
tags:
    - audit
    - channels
blocked: true
block_reason: 'Resolved duplicate of archived #803; SlackChannel.send_file already exists in source/tests. Keep for traceability or cleanup, not builder flow.'
class: standard
---

INT-17: SlackChannel missing send_file. ScreenshotService.deliver already works via send_image (tier 1), but direct send_file callers skip to send fallback. Add send_file as thin delegate to send_image(path, caption=caption or path.name). Requires files:write scope (already granted). ~5 LOC impl + ~15 LOC tests. See docs/research/slack-send-file.md

AC:
- [ ] SlackChannel.send_file(path, *, caption) exists with same signature as CLIChannel
- [ ] Delegates to files_upload_v2 (via send_image)
- [ ] Caption passed as title + initial_comment when provided
- [ ] No-caption uses path.name as default title
- [ ] Upload failure falls back to channel.send plain text
- [ ] Tests cover: happy path, caption, no-caption default, error fallback

[[2026-03-21]] Sat 02:53
## Architecture Review
**Verdict:** Block

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| `SlackChannel.send_file(path, *, caption) exists with same signature as CLIChannel` | Already satisfied in `src/owlbear/channels/slack.py` via an explicit override matching the protocol/CLI signature. | Do not route to builder; duplicate of shipped behavior. |
| `Delegates to files_upload_v2 (via send_image)` | Already satisfied: `send_file()` delegates to `send_image()`, and `send_image()` is the existing `files_upload_v2` integration point. | Keep `send_image()` as the single upload implementation. |
| `Caption passed as title + initial_comment when provided` | Already satisfied by current `send_image()` behavior and existing Slack upload tests. | No new implementation scope remains. |
| `No-caption uses path.name as default title` | Already satisfied: `send_file()` delegates with `caption=path.name` when caption is omitted or `None`; dedicated tests already exist. | Do not re-implement. |
| `Upload failure falls back to channel.send plain text` | Fallback already lives in `send_image()`. A new fallback in `send_file()` would be the wrong layer and risks double-fallback behavior. | Preserve current layering; do not send this to builder. |
| `Tests cover: happy path, caption, no-caption default, error fallback` | Already satisfied by `tests/test_slack_send_file.py` plus existing `send_image()` tests in `tests/test_slack_channel.py`; archived task `#803` records the RED/green path. | Use archived task and current tests as source of truth. |

### Architecture Notes
Current repo state already implements the task contract. `SlackChannel.send_file()` exists in `src/owlbear/channels/slack.py` as a thin delegate to `send_image()`, which is consistent with the research recommendation in `docs/research/slack-send-file.md` and with the layering guidance in the architecture standards: one upload path, one fallback path.

This backlog card is stale relative to the repo. The real executable contract was captured later in archived task `#803`, whose RED tests now live in `tests/test_slack_send_file.py`. The current backlog task also lacks an explicit TDD dependency, so approving it would send redundant work into the builder flow and create risk of an incorrect second fallback inside `send_file()` instead of keeping fallback behavior centralized in `send_image()`.

### Changes Made
- Verified current source already contains `SlackChannel.send_file()` in `src/owlbear/channels/slack.py`
- Verified dedicated tests already exist in `tests/test_slack_send_file.py`
- Verified existing upload/fallback coverage remains in `tests/test_slack_channel.py`
- Marked `#552` as a blocked ideation task for traceability/cleanup instead of routing it to builder flow

### Dependencies
- Verified: archived task `#803` (tests for `SlackChannel.send_file` delegation)
- Verified: `docs/research/slack-send-file.md`
- Verified current source/tests: `src/owlbear/channels/slack.py`, `tests/test_slack_send_file.py`, `tests/test_slack_channel.py`
