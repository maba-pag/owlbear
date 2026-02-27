---
id: 46
title: Implement pre_tool_use safety hook
status: done
priority: medium
created: 2026-02-26T15:57:26.4378399+01:00
updated: 2026-02-27T00:38:03.904192+01:00
started: 2026-02-27T00:38:03.4260153+01:00
completed: 2026-02-27T00:38:03.4260153+01:00
tags:
    - phase-3
    - agent
    - hooks
depends_on:
    - 38
class: standard
---

See docs/agent-patterns-research.md para 3.4. Depends on HookRegistry (#38).

## Research required (gate: ideation to backlog)

1. **Theoretical validity** - Is a built-in safety hook the right approach, or should tool validation be part of the Tool ABC itself?
2. **Prior art** - Study disler/claude-code-hooks-mastery PreToolUse patterns, VS Code hook safety guards, PydanticAI tool validation
3. **Technical feasibility** - What can actually be blocked? File operations, terminal commands, network calls? How granular?
4. **Architecture fit** - Integrates with HookRegistry pre_tool_use event. Depends on #38.
5. **Implementation approach** - Blocklist regex vs allowlist vs policy-based validation

## AC
Built-in hook registered on pre_tool_use that validates tool arguments. Blocks dangerous file operations. Logs all tool invocations.

[[2026-02-27]] Fri 00:38
CLOSED: Merged into #19 (PreToolUse command safety guard). Both tasks target PRE_TOOL_USE hook - consolidated into #19.
