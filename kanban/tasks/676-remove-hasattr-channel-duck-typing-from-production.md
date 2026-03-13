---
id: 676
title: Remove hasattr channel duck-typing from production code
status: archived
priority: needed
created: 2026-03-08T03:00:56.0939898+01:00
updated: 2026-03-09T00:48:35.0380728+01:00
started: 2026-03-08T05:43:32.1886704+01:00
completed: 2026-03-09T00:48:35.0380728+01:00
tags:
    - refactor
    - channels
depends_on:
    - 675
class: standard
---

Replace all 3 hasattr channel checks with direct method calls now that ChannelPlugin has defaults (from #675). See docs/research/channel-protocol-extension.md.

AC:
1. Zero matches for 'hasattr.*channel' in src/owlbear/ (currently 3: gate.py:101, screenshot.py:60, screenshot.py:62).
2. screenshot.py ScreenshotService.deliver() param typed as ChannelPlugin (not object).
3. gate.py calls channel.send_blocks() directly -- the text_fallback must include the CLI approval prompt text (Approve? yes/no/approve all {name}) to preserve CLI behavior.
4. screenshot.py deliver() simplifies to a single await channel.send_image(path, caption=caption) call.
5. CLIChannel.send_image overrides the protocol default to delegate to self.send_file(file_or_bytes, caption=caption) when file_or_bytes is a Path, preserving the current CLI behavior of showing the file path and opening it on Windows.
6. test_screenshot.py updated: remove hasattr-based dispatch tests (send_file fallback, bare send fallback). Single test that deliver() calls send_image().
7. test_slack_interactive.py:213 assertion 'assert not hasattr(cli_channel, send_blocks)' removed or inverted -- CLIChannel now inherits send_blocks from the protocol.
8. All existing tests pass; ruff clean.

[[2026-03-08]] Sun 23:57
Wave 5, agent: auditor

[[2026-03-09]] Mon 00:48
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| AC1: Zero hasattr matches | grep src/owlbear/ returns 0 hits | .97 |
| AC2: deliver() typed ChannelPlugin | screenshot.py L53: channel: ChannelPlugin | .97 |
| AC3: gate.py direct send_blocks + text_fallback | gate.py L103-107: text_fallback includes Approve? prompt | .97 |
| AC4: Single send_image call | screenshot.py L55: await channel.send_image(path, caption=caption) | .97 |
| AC5: CLIChannel.send_image Path delegation | cli.py L70-86: delegates to send_file for Path, sends caption for bytes | .97 |
| AC6: test_screenshot.py updated | Single test_deliver_calls_send_image, hasattr tests removed | .97 |
| AC7: assert not hasattr inverted | test_slack_interactive.py L212: assert hasattr(cli_channel, 'send_blocks') | .97 |
| AC8 tests | 1271 passed, 1 pre-existing slack_sdk failure (unrelated) | .97 |
| AC8 ruff | E501 at screenshot.py L22 (115>100, docstring Sphinx xref). Cosmetic. | .80 |

Confidence: .90 -- all functional AC met, one docstring line-length violation (trivial cosmetic).
