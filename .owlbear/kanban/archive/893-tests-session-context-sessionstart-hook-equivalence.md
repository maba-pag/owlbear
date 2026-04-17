---
id: 893
title: 'Tests: session-context SessionStart hook equivalence'
status: research
priority: needed
created: 2026-04-16T22:53:29.692464+00:00
updated: 2026-04-16T22:53:29.692464+00:00
tags:
- phase-1
- scope:hooks
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

- [ ] Test file for session-context.py SessionStart hook
- [ ] Tests verify JSON I/O contract: stdin JSON, stdout JSON with additionalContext containing branch and recent commits
- [ ] Git invocation mocked or patched — verify `git branch --show-current` and `git log --oneline -3 --no-decorate` called
- [ ] Git failure handling: non-zero exit code returns graceful fallback (not crash)
- [ ] Malformed input cases: truncated JSON, empty stdin, BOM, binary all return {} with exit 0
- [ ] Tests invoke the .py script via subprocess
- [ ] All tests fail (RED) — no .py implementation exists yet

## Files
- `tests/test_session_context_hook.py` (new)