---
id: 163
title: Test GitLocalToolset — subprocess git operations
status: archived
priority: important
created: 2026-02-27T20:46:31.8753355+01:00
updated: 2026-02-28T23:53:17.0699799+01:00
started: 2026-02-27T21:28:15.5316641+01:00
completed: 2026-02-28T23:53:17.0699799+01:00
tags:
    - phase-8
    - tools
    - github
    - test
class: standard
---

Test task for GitLocalToolset. Write tests first (TDD).

## AC
- [ ] File: tests/test_git_local.py
- [ ] Test git_status: mock asyncio.create_subprocess_exec, verify --porcelain flag, parse output
- [ ] Test git_diff: mock subprocess returns diff text (staged and unstaged variants)
- [ ] Test git_add: mock subprocess called with correct path args
- [ ] Test git_commit: verify HookEvent.PRE_TOOL_USE emitted before subprocess call
- [ ] Test git_branch: create branch via mock subprocess
- [ ] Test git_log: mock subprocess returns --oneline log, verify -n count param
- [ ] Test git_push: verify HookEvent.PRE_TOOL_USE emitted before subprocess call
- [ ] Test error handling: non-zero exit code returns error string (not exception)
- [ ] Test constructor: workspace_root stored, hooks optional
- [ ] ruff clean

## Architecture
- Follow test_terminal_tools.py pattern for subprocess mocking
- Use pytest-asyncio for async test methods
- Mock asyncio.create_subprocess_exec (not shell)
