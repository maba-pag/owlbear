---
id: 19
title: 'P3-04: PreToolUse command safety guard'
status: archived
priority: medium
created: 2026-02-24T15:11:32.1221629+01:00
updated: 2026-02-27T10:00:01.536765+01:00
started: 2026-02-27T00:39:19.8496979+01:00
completed: 2026-02-27T10:00:01.536765+01:00
tags:
    - phase-3
    - hooks
depends_on:
    - 16
    - 38
class: standard
---

PydanticAI PRE_TOOL_USE hook that blocks dangerous commands. Merged from #19 + #46.

## AC
- CommandSafetyGuard class in src/owlbear/core/hooks/ registered on PRE_TOOL_USE
- Blocks dangerous shell commands: rm -rf /, git push --force, pip install (without uv), format C:, del /s /q, sudo rm
- Blocks dangerous file operations: writing to .env files, deleting project root
- Configurable blocklist via regex patterns (like URLSafetyGuard.blocked_urls)
- Follows URLSafetyGuard pattern: __call__(data), check_command(cmd), register(hooks)
- Raises BlockedCommandError (like BlockedURLError) with command + matching pattern
- Logs all tool invocations at DEBUG level
- Error isolation: guard exceptions are handled by HookRegistry
- Tests: register, block dangerous commands, allow safe commands, configurable patterns, logging
- Depends on HookRegistry (#38, done)
- Also absorbs #46 (pre_tool_use safety hook)
