---
id: 121
title: 'Core tool: run_command (terminal execution)'
status: archived
priority: critical
created: 2026-02-27T14:54:23.8389627+01:00
updated: 2026-02-28T23:52:47.6296018+01:00
started: 2026-02-27T15:36:33.5473345+01:00
completed: 2026-02-28T23:52:47.6296018+01:00
tags:
    - phase-7
    - tools
    - agent
class: standard
---

Agents need to run shell commands (pytest, ruff, git, etc.). This is the second critical tool after filesystem.

## Research

See `docs/research/terminal-tool.md` for full analysis.

## AC

### Module structure
- [ ] New file: `src/owlbear/tools/terminal.py`
- [ ] `TerminalToolset(FunctionToolset)` subclass following `BrowserToolset` pattern
- [ ] Constructor: `workspace_root: Path = Path(.)` + optional `hooks: HookRegistry | None = None` + optional `max_output_bytes: int = 60_000`
- [ ] Tool registered via `_register_tools()` + async wrapper method

### Result model
- [ ] `TerminalResult` as `@dataclass(frozen=True, slots=True)` with fields: `stdout: str`, `stderr: str`, `exit_code: int`, `timed_out: bool`
- [ ] Defined in same file (`src/owlbear/tools/terminal.py`)

### Tool
- [ ] `run_command(command: str, working_dir: str | None = None, timeout_seconds: int | float = 30) -> TerminalResult`
- [ ] `asyncio.create_subprocess_shell` with `stdout=PIPE, stderr=PIPE, cwd=resolved_working_dir`
- [ ] Timeout via `asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)`
- [ ] On timeout: `proc.kill()` + `await proc.wait()` + return partial output with `timed_out=True`
- [ ] `working_dir` resolves relative to `workspace_root`; if `None`, uses `workspace_root`
- [ ] Decode stdout/stderr as UTF-8 with `errors=replace`

### Output truncation
- [ ] Head+tail strategy: if `len(output) > max_output_bytes`, keep first `N//2` + last `N//2` bytes with `[...truncated {omitted} bytes...]` marker
- [ ] Apply to both stdout and stderr independently

### Hook integration
- [ ] If `hooks` provided, emit `PRE_TOOL_USE` before execution with payload: `{tool_name: run_command, args: {command: cmd}}`
- [ ] `CommandSafetyGuard` already lists `run_command` in `_SHELL_TOOLS` (`command_guard.py` L43) — no changes needed there
- [ ] If no `hooks` provided, skip hook emission (enables lightweight testing)

### Tests (TDD: write tests first, see them fail, then implement)
- [ ] New file: `tests/test_terminal_tools.py`
- [ ] Test successful command (e.g. `echo hello`) — verify stdout, exit_code=0, timed_out=False
- [ ] Test failing command (e.g. `exit 1`) — verify exit_code != 0
- [ ] Test timeout — command that sleeps, verify timed_out=True and process killed
- [ ] Test output truncation — command producing > 60KB, verify head+tail+marker
- [ ] Test hook integration — mock HookRegistry, verify PRE_TOOL_USE emitted with correct payload
- [ ] Test working_dir resolution — verify command runs in specified directory
- [ ] ruff clean on both files

## Implementation Notes
- Use `asyncio.wait_for(proc.communicate(), timeout)` for timeout handling
- Truncation: keep first N/2 + last N/2 bytes with `[truncated X bytes]` marker
- Follow BrowserToolset pattern: `__init__` registers tools via `add_function()`
