---
id: 675
title: Widen ChannelPlugin with send_file/send_blocks/send_image defaults
status: archived
priority: needed
created: 2026-03-08T03:00:47.4844208+01:00
updated: 2026-03-09T00:41:34.8419121+01:00
started: 2026-03-08T03:44:12.94008+01:00
completed: 2026-03-09T00:41:34.8419121+01:00
tags:
    - refactor
    - channels
class: standard
---

Add send_file, send_blocks, send_image to ChannelPlugin protocol in channels/base.py with default implementations that delegate to send(). Make CLIChannel and SlackChannel explicitly inherit ChannelPlugin. AC: (1) ChannelPlugin defines send_file(self, path: Path, *, caption: str | None = None) -> None with default: await self.send(f'[{caption}] {path}' if caption else str(path)). (2) ChannelPlugin defines send_blocks(self, blocks: list[dict], text_fallback: str) -> None with default: await self.send(text_fallback). (3) ChannelPlugin defines send_image(self, file_or_bytes: Path | bytes, *, caption: str | None = None) -> None with default: await self.send(caption or '[image]'). (4) CLIChannel(ChannelPlugin) explicitly inherits -- retains its own send_file override. (5) SlackChannel(ChannelPlugin) explicitly inherits -- retains its own send_blocks and send_image overrides. (6) All existing tests pass; ruff clean. (7) isinstance(CLIChannel(), ChannelPlugin) is True. See docs/research/channel-protocol-extension.md.

[[2026-03-08]] Sun 23:57
Wave 4, agent: auditor

[[2026-03-09]] Mon 00:41
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| AC1: send_file default in ChannelPlugin | base.py L38-49: send_file(self, path: Path, *, caption: str or None = None) -> None with correct default delegation to send() | .97 |
| AC2: send_blocks default in ChannelPlugin | base.py L51-59: send_blocks(self, blocks: list[dict], text_fallback: str) -> None delegates to send(text_fallback) | .97 |
| AC3: send_image default in ChannelPlugin | base.py L61-71: send_image(self, file_or_bytes: Path or bytes, *, caption: str or None = None) -> None delegates to send(caption or '[image]') | .97 |
| AC4: CLIChannel(ChannelPlugin) with send_file override | cli.py L16: class CLIChannel(ChannelPlugin); L53: own send_file override (writes to output, opens on Windows) | .97 |
| AC5: SlackChannel(ChannelPlugin) with send_blocks/send_image overrides | slack.py L33: class SlackChannel(ChannelPlugin); L133: own send_blocks (Block Kit, thread_ts); L179: own send_image (files_upload_v2) | .97 |
| AC6: All existing tests pass, ruff clean | 39/39 channel tests PASS; ruff clean on src/owlbear/channels/ and tests/test_channels.py. Full suite: 1271 passed, 1 failed (pre-existing slack_sdk ImportError in test_bootstrap.py, unrelated) | .95 |
| AC7: isinstance(CLIChannel(), ChannelPlugin) is True | test_channels.py L22-26: test_cli_channel_is_channel_plugin explicitly asserts isinstance, PASSES | .97 |

### Verdict
Confidence: .97 — all 7 AC items verified with evidence. Single pre-existing failure unrelated to task.

### Commit Log
N/A — auditor is read-only; no code changes made.
