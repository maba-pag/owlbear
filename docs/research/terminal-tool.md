# Terminal Tool Research — run_command

> **Owning task:** #121 — Core tool: run_command (terminal execution)
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear agents need to run shell commands (pytest, ruff, git, etc.) as part of the autonomous build pipeline. Task #121 specifies a `TerminalToolset(FunctionToolset)` with a single `run_command` tool that executes commands via `asyncio.create_subprocess_shell`, returns structured results, integrates with the existing `CommandSafetyGuard` hook, and truncates large output.

**Key decisions this research informs:**

- Async subprocess API choice and timeout mechanism
- Output truncation strategy (head, tail, or middle-out)
- Hook integration pattern (direct call vs. emit through `HookRegistry`)
- Result model design (`dataclass` vs `TypedDict` vs Pydantic `BaseModel`)
- `workspace_root` sourcing (constructor param vs config)

## 2. Sources Studied

| Source | URL | Relevance | What |
|---|---|---|---|
| Python asyncio subprocess docs | <https://docs.python.org/3/library/asyncio-subprocess.html> | .95 | `create_subprocess_shell` + `communicate()` + `wait_for()` timeout pattern |
| OpenHands ActionExecutor | <https://github.com/All-Hands-AI/OpenHands> | .80 | `CmdRunAction` → `CmdOutputObservation` pattern with exit codes |
| Aider `run_cmd` | <https://github.com/Aider-AI/aider> | .75 | Simple `subprocess.run` with shell=True, token-aware output handling |
| OwlBear BrowserToolset | `src/owlbear/tools/browser/toolset.py` | .95 | Established `FunctionToolset` subclass pattern in our codebase |
| OwlBear CommandSafetyGuard | `src/owlbear/core/command_guard.py` | .95 | Already lists `"run_command"` in `_SHELL_TOOLS` — ready for integration |
| OwlBear TestVerificationHook | `src/owlbear/core/test_hook.py` | .70 | `TestResult(TypedDict)` pattern for subprocess results |
| PydanticAI Tool class | <https://github.com/pydantic/pydantic-ai> | .65 | Tool timeout support via `asyncio.wait_for`, `sequential` flag |

## 3. Analysis

### 3.1 Subprocess API: async vs sync

| Criterion | `asyncio.create_subprocess_shell` | `subprocess.run` |
|---|---|---|
| Non-blocking | Yes — agent loop stays responsive | No — blocks event loop |
| Timeout | `asyncio.wait_for(proc.communicate(), timeout)` | `timeout` param (raises `TimeoutExpired`) |
| Output capture | `proc.communicate()` returns `(stdout, stderr)` bytes | `capture_output=True` returns `CompletedProcess` |
| Process cleanup | Must `proc.kill()` + `await proc.wait()` on timeout | Automatic on `TimeoutExpired` |
| Windows support | Requires `ProactorEventLoop` (default since 3.8) | Always works |
| Complexity | Medium — need explicit timeout/kill/decode handling | Low — one function call |
| KISS score | Medium | High |

**Verdict:** Use `asyncio.create_subprocess_shell`. The AC explicitly requires it, and it's the right choice because `run_command` will be called inside PydanticAI agent loops which are async. Blocking `subprocess.run` would freeze the agent.

### 3.2 Timeout mechanism

Python's asyncio docs explicitly state: "the `communicate()` and `wait()` methods don't have a timeout parameter: use `wait_for()`." The pattern is:

```python
try:
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
except TimeoutError:
    proc.kill()
    await proc.wait()
    # return timeout result
```

This is well-established and used by multiple agent frameworks. No alternatives needed.

### 3.3 Output truncation strategy

| Strategy | Behavior | Pros | Cons |
|---|---|---|---|
| Head-only | Keep first N bytes | Simple, shows command start | Misses error messages (usually at end) |
| Tail-only | Keep last N bytes | Shows errors/summary | Misses context |
| **Head+Tail** | Keep first N/2 + last N/2 with `[...truncated...]` marker | Shows both context and errors | Slightly more complex |
| Token-based | Count LLM tokens | Precise budget control | Slow, over-engineered for this |

**Verdict (.85 confidence):** Head+tail truncation. Error messages and test summaries appear at the end; command context and early output at the start. A simple `[…truncated {omitted} bytes…]` marker in the middle. This matches VS Code Copilot's own `run_in_terminal` behavior ("Output is automatically truncated if longer than 60KB").

Default `max_output_bytes = 60_000` (60KB, matching VS Code Copilot convention).

### 3.4 Result model design

| Option | Type | Pros | Cons |
|---|---|---|---|
| `TypedDict` | Like `TestResult` in `test_hook.py` | Lightweight, dict-compatible | No validation, no methods |
| `dataclass` | Like `SkillMeta` | Lightweight, immutable with `frozen=True` | No Pydantic integration |
| Pydantic `BaseModel` | Standard for structured output | Validation, serialization | Heavier than needed for internal use |

**Verdict (.80 confidence):** `dataclass(frozen=True, slots=True)` — matches `SkillMeta` pattern, lightweight, immutable. This is an internal return type, not API-facing. KISS.

### 3.5 Hook integration: direct vs emit

Two options for invoking `CommandSafetyGuard`:

| Option | Pattern | Pros | Cons |
|---|---|---|---|
| **A: Accept optional `HookRegistry`, emit `PRE_TOOL_USE`** | `await hooks.emit(PRE_TOOL_USE, payload)` | Decoupled, extensible, any hook fires | Requires `HookRegistry` in constructor |
| B: Accept `CommandSafetyGuard` directly | `guard.check_command(cmd)` | Simple, explicit | Tightly coupled, can't add other pre-hooks |

**Verdict (.85 confidence):** Option A — accept optional `HookRegistry`. The `CommandSafetyGuard` already registers itself on `PRE_TOOL_USE`. Emitting through the registry means any registered hook fires (logging, rate limiting, etc.). If no registry is provided, skip the hook — enables lightweight testing.

The payload format matches existing convention: `{"tool_name": "run_command", "args": {"command": cmd}}`.

### 3.6 workspace_root sourcing

`OwlBearSettings` does not currently have a `workspace_root` field. Options:

| Option | Approach | Pros | Cons |
|---|---|---|---|
| **A: Constructor param** | `TerminalToolset(workspace_root=Path("."))` | Explicit, testable, YAGNI | Caller must provide it |
| B: Add to OwlBearSettings | `settings.workspace_root` | Centralized config | Config change for one tool |
| C: Default to `Path.cwd()` | Runtime detection | Zero config | Non-deterministic in tests |

**Verdict (.80 confidence):** Option A — constructor parameter with default `Path(".")`. The `FileToolset` (#120) will need the same parameter; both can accept it from the same caller. Adding to `OwlBearSettings` can happen later when the config-wiring task is done. YAGNI for now.

## 4. Recommendation (.85 confidence)

Implement `TerminalToolset` as a `FunctionToolset` subclass with:

- **One tool:** `run_command(command, working_dir, timeout_seconds)` → `TerminalResult`
- **Async execution:** `asyncio.create_subprocess_shell` with `asyncio.wait_for` timeout
- **Result model:** `@dataclass(frozen=True, slots=True)` with `stdout`, `stderr`, `exit_code`, `timed_out` fields
- **Output truncation:** Head+tail strategy, configurable `max_output_bytes` (default 60KB)
- **Hook integration:** Optional `HookRegistry` in constructor, emit `PRE_TOOL_USE` before execution
- **workspace_root:** Constructor `Path` parameter, default `Path(".")`
- **Process cleanup:** On timeout, `proc.kill()` + `await proc.wait()` + return partial output with `timed_out=True`

**Risk:** Shell injection via `create_subprocess_shell`. **Mitigation:** The `CommandSafetyGuard` blocklist is the first line of defense. The tool description for the LLM should discourage piping user input directly. This is an intentional design choice — agents need shell features (pipes, redirects, env vars) that `create_subprocess_exec` doesn't provide.

**Risk:** Large output OOM. **Mitigation:** `proc.communicate()` buffers in memory; the 60KB truncation happens post-read. For truly enormous output, a streaming approach with `proc.stdout.read(chunk)` could be added later. YAGNI for now — `communicate()` is simpler and the Python docs recommend it over manual stream reading.

## 5. Follow-up Tasks

The AC for #121 is well-scoped. No task splitting needed. Implementation should follow TDD:

1. Write tests first (successful command, failing command, timeout, output truncation, hook integration)
2. Implement `TerminalToolset` + `TerminalResult`
3. Verify ruff clean + all tests pass

No additional tasks beyond #121 are needed at this stage. The `workspace_root` config centralization can be addressed when the full agent wiring task lands.
