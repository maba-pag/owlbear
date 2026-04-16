---
id: 896
title: Port session-context SessionStart hook to Python
status: research
priority: critical
created: 2026-04-16T22:53:50.262201+00:00
updated: 2026-04-16T22:53:50.262201+00:00
tags:
- phase-1
- scope:hooks
- type:build
- platform
parent: 890
depends_on:
- 893
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] `.owlbear/hooks/session-context.py` created
- [ ] Reads JSON from sys.stdin
- [ ] Runs `git branch --show-current` and `git log --oneline -3 --no-decorate` via subprocess
- [ ] Returns JSON with additionalContext containing branch name and recent commit lines
- [ ] Git failure (non-zero exit, git not found) handled gracefully — returns partial or empty context, does not crash
- [ ] Fail-open: any exception returns {} with exit 0 (D7, D8)
- [ ] Bug-for-bug fidelity with .ps1 original (D7)
- [ ] All tests from #893 pass (GREEN)

## Files
- `.owlbear/hooks/session-context.py` (new)