---
id: 891
title: 'Tests: PreToolUse guard hooks equivalence (5 hooks)'
status: research
priority: needed
created: 2026-04-16T22:53:29.635169+00:00
updated: 2026-04-16T22:53:29.635169+00:00
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

- [ ] Parameterized test file covering all 5 PreToolUse guard hooks: deny-writes, deny-code-writes, deny-src-writes, deny-scratch-only-writes, allow-stances-only
- [ ] Each hook tested with: valid allow input, valid deny input, edge-case paths
- [ ] deny-writes: tool_name in write_tools list returns deny; non-write tool returns allow
- [ ] deny-code-writes: paths matching deny-list (serve/, tests/, setup/, etc.) return deny; other paths return allow; multiple input formats tested (filePath, dirPath, replacements[], editFiles[])
- [ ] deny-src-writes: paths outside tests/ return deny; tests/ paths return allow
- [ ] deny-scratch-only-writes: paths outside .owlbear/scratch/ return deny; scratch paths return allow
- [ ] allow-stances-only: paths without /stances/ return deny; /stances/ paths return allow
- [ ] Malformed input cases: truncated JSON, empty stdin, BOM prefix, binary data all return {} with exit 0 (fail-open)
- [ ] Tests invoke the .py scripts via subprocess (same as VS Code would) to verify full I/O contract
- [ ] All tests fail (RED) — no .py hook implementations exist yet

## Files
- `tests/test_pretooluse_hooks.py` (new)