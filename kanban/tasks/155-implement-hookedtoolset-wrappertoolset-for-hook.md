---
id: 155
title: Implement HookedToolset — WrapperToolset for hook integration
status: archived
priority: important
created: 2026-02-27T16:48:11.1619966+01:00
updated: 2026-02-28T23:53:12.1859517+01:00
started: 2026-02-27T16:48:18.6313471+01:00
completed: 2026-02-28T23:53:12.1859517+01:00
tags:
    - phase-8
    - agent
    - tools
class: standard
---

WrapperToolset subclass that emits PRE_TOOL_USE and POST_TOOL_USE hooks from within PydanticAI tool execution pipeline. Research: docs/pydantic-ai-multi-agent-research.md section 3.2.

## AC
- [ ] File: src/owlbear/tools/hooked.py (~40 LOC)
- [ ] @dataclass class HookedToolset(WrapperToolset) — WrapperToolset is a @dataclass with 'wrapped' field
- [ ] Additional dataclass field: hooks: HookRegistry
- [ ] Constructor usage: HookedToolset(wrapped=some_toolset, hooks=hook_registry)
- [ ] Override call_tool(self, name: str, tool_args: dict[str, Any], ctx: RunContext, tool: ToolsetTool) -> Any
- [ ] Emit PRE_TOOL_USE before super().call_tool(): data = {'tool_name': name, 'args': tool_args}
- [ ] Emit POST_TOOL_USE after super().call_tool(): data = {'tool_name': name, 'result': result}
- [ ] HookRegistry.emit() is async — await it in call_tool
- [ ] Test: PRE_TOOL_USE hook fires with correct tool_name and args before tool execution
- [ ] Test: POST_TOOL_USE hook fires with correct tool_name and result after tool execution
- [ ] Test: exceptions in hooks do not prevent tool execution (HookRegistry.emit swallows)
- [ ] Test: wrapping a FunctionToolset with HookedToolset preserves tool behavior (tool still returns correct result)
- [ ] ruff clean
- [ ] Note: follow-up task needed to remove manual hook emission from TerminalToolset.run_command() and wrap with HookedToolset instead

## Architecture
- Replaces current approach where TerminalToolset manually emits hooks from inside tool code
- Native PydanticAI integration — WrapperToolset.call_tool() is the documented extension point
- Can wrap any toolset: HookedToolset(wrapped=FileToolset(root), hooks=registry)
- WrapperToolset is a @dataclass — HookedToolset must also use @dataclass decorator
- WrapperToolset field is 'wrapped' (not 'inner') — use this naming
- Future: CommandSafetyGuard could move from hook-based to WrapperToolset-based for cleaner integration
