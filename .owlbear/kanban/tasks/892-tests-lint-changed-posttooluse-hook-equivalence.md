---
id: 892
title: 'Tests: lint-changed PostToolUse hook equivalence'
status: research
priority: needed
created: 2026-04-16T22:53:29.680503+00:00
updated: 2026-04-16T22:53:29.680503+00:00
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

- [ ] Test file for lint-changed.py PostToolUse hook
- [ ] Tests verify JSON I/O contract: stdin JSON with tool_input containing file paths, stdout JSON with systemMessage and hookSpecificOutput
- [ ] File path extraction tested: filePath, dirPath, replacements[], editFiles[] input formats
- [ ] Ruff invocation mocked or patched — verify correct args passed (ruff check --ignore INP001)
- [ ] Only existing .py files passed to ruff (non-existent paths filtered, non-.py filtered)
- [ ] Deduplication of file paths tested (HashSet equivalent behavior)
- [ ] Malformed input cases: truncated JSON, empty stdin, BOM, binary all return {} with exit 0
- [ ] Tests invoke the .py script via subprocess
- [ ] All tests fail (RED) — no .py implementation exists yet

## Files
- `tests/test_lint_changed_hook.py` (new)