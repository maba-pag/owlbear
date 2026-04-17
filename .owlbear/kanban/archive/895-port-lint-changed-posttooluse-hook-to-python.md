---
id: 895
title: Port lint-changed PostToolUse hook to Python
status: research
priority: critical
created: 2026-04-16T22:53:50.250881+00:00
updated: 2026-04-16T22:53:50.250881+00:00
tags:
- phase-1
- scope:hooks
- type:build
- platform
parent: 890
depends_on:
- 892
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] `.owlbear/hooks/lint-changed.py` created
- [ ] Reads JSON from sys.stdin, extracts file paths from tool_input (filePath, dirPath, replacements[], editFiles[])
- [ ] Filters to existing .py files only, deduplicates
- [ ] Runs `ruff check --ignore INP001` on collected paths via subprocess
- [ ] Returns JSON with systemMessage (user-facing) and hookSpecificOutput (model-facing) containing ruff output
- [ ] Non-zero ruff exit captured but does not crash the hook
- [ ] Fail-open: any exception returns {} with exit 0 (D7, D8)
- [ ] Bug-for-bug fidelity with .ps1 original (D7)
- [ ] All tests from #892 pass (GREEN)

## Files
- `.owlbear/hooks/lint-changed.py` (new)