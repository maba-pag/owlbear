---
id: 903
title: Verify browser graceful degradation on macOS
status: research
priority: important
created: 2026-04-16T22:54:41.795853+00:00
updated: 2026-04-16T22:54:41.795853+00:00
tags:
- phase-3
- scope:browser
- type:test
- platform
parent: 890
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] playwright_launcher.py reviewed: confirm non-Windows platforms handled gracefully (exception caught, not crash)
- [ ] MCP browser server reviewed: confirm startup on macOS does not crash (may return errors, but should not prevent server from running)
- [ ] Chrome extension path discovery reviewed: confirm macOS paths not attempted (deferred per D3)
- [ ] Evidence documented: file paths, line numbers, exception handling patterns found
- [ ] No code changes needed (verify only) — if changes ARE needed, create follow-up task

## Files
- `serve/browser/` (read only)
- `serve/mcp-browser/` (read only)