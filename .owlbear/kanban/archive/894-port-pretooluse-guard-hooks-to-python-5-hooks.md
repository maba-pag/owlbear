---
id: 894
title: Port PreToolUse guard hooks to Python (5 hooks)
status: research
priority: critical
created: 2026-04-16T22:53:50.224775+00:00
updated: 2026-04-16T22:53:50.224775+00:00
tags:
- phase-1
- scope:hooks
- type:build
- platform
parent: 890
depends_on:
- 891
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] 5 Python scripts created in `.owlbear/hooks/`: deny-writes.py, deny-code-writes.py, deny-src-writes.py, deny-scratch-only-writes.py, allow-stances-only.py
- [ ] Each reads JSON from sys.stdin, parses with json stdlib, returns JSON to stdout
- [ ] deny-writes: checks tool_name against write_tools list; denies write tools, allows others
- [ ] deny-code-writes: extracts paths from filePath, dirPath, replacements[], editFiles[]; denies paths matching deny-list (serve/, v1/, tests/, setup/, seed/, store/, share/agents/, .git/, .owlbear/hooks/, .owlbear/scripts/, conftest.py)
- [ ] deny-src-writes: inverts to allow ONLY writes to tests/
- [ ] deny-scratch-only-writes: inverts to allow ONLY writes to .owlbear/scratch/
- [ ] allow-stances-only: allows ONLY writes to paths containing /stances/
- [ ] All return hookSpecificOutput with permissionDecision (allow/deny) and reason
- [ ] Fail-open: any exception returns {} with exit 0 (D7, D8)
- [ ] Bug-for-bug fidelity with .ps1 originals (D7)
- [ ] All tests from #891 pass (GREEN)

## Files
- `.owlbear/hooks/deny-writes.py` (new)
- `.owlbear/hooks/deny-code-writes.py` (new)
- `.owlbear/hooks/deny-src-writes.py` (new)
- `.owlbear/hooks/deny-scratch-only-writes.py` (new)
- `.owlbear/hooks/allow-stances-only.py` (new)