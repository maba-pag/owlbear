---
id: 298
title: Progress reporting — periodic status updates to user
status: archived
priority: needed
created: 2026-03-01T02:53:05.7572768+01:00
updated: 2026-03-01T17:09:23.8802091+01:00
started: 2026-03-01T09:57:11.3946391+01:00
completed: 2026-03-01T17:09:23.8802091+01:00
tags:
    - phase-12
    - daemon
    - channels
class: standard
---

## Context
During long-running tasks (research, code generation, test runs), the user has no visibility into what OwlBear is doing. Need a mechanism to push progress updates.

## Acceptance Criteria
- [ ] ProgressReporter class that emits status updates at configurable intervals
- [ ] Hooks into HookEvent.POST_TOOL_USE to track tool execution progress
- [ ] Sends via active channel: 'Working on X... (step 3/7, last tool: run_command)'
- [ ] Configurable update interval (default: 30s) and detail level (brief/detailed)
- [ ] Integrates with task completion hooks (TASK_COMPLETE event)
- [ ] Does NOT interrupt agent's tool loop — updates are async/non-blocking
- [ ] Unit tests with mock channel verifying update cadence
