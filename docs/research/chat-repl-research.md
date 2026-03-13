# Chat REPL Research — bearclaw chat Interactive CLI

> **Owning task:** #122 — bearclaw chat — interactive CLI REPL
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

Task #122 requires an interactive `bearclaw chat` command — the first path to a working OwlBear where a user types and OwlBear responds. All core building blocks exist (OwlBearAgent, CLIChannel, SessionStore, ContextManager, SkillRegistry) but have never been wired into a REPL. Key questions: loop structure, multi-line input, signal handling, session naming, toolset wiring, and prerequisites.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| simonw/llm `chat` command | <https://github.com/simonw/llm> (cli.py) | .95 | REPL loop, `!multi`/`!end` multi-line, `readline` bindings, `exit`/`quit` keywords, streaming chunks |
| PydanticAI `clai` CLI | <https://ai.pydantic.dev/cli/> | .90 | `Agent.to_cli()` / `to_cli_sync()`, `/multiline` toggle, `/exit`, `message_history` param |
| PydanticAI chat app example | <https://ai.pydantic.dev/examples/chat-app/> | .80 | `agent.run(prompt, message_history=messages)`, `result.new_messages_json()`, `result.all_messages()` |
| OwlBear daemon-bootstrap-research | `docs/daemon-bootstrap-research.md` | .90 | Loop-outside-agent pattern, `receive → turn → send`, signal handling, error recovery |
| OwlBear existing code | `src/owlbear/`, `src/bearclaw/cli.py` | 1.0 | OwlBearAgent.turn(), CLIChannel, SessionStore, ContextManager, Typer CLI patterns |

## 3. Analysis

### 3.1 Can we reuse PydanticAI's `Agent.to_cli()`?

| Criterion | `Agent.to_cli()` | Custom loop via `OwlBearAgent.turn()` |
|-----------|-------------------|----------------------------------------|
| Session persistence (JSONL) | No — not supported | Yes — `SessionStore` built-in |
| Hook lifecycle events | No — bypasses hooks | Yes — `ON_MESSAGE`, `ON_ERROR`, `SESSION_START` |
| Usage tracking | No | Yes — `UsageTracker` integration |
| Multi-line input | Yes — `/multiline` toggle | Must implement |
| Signal handling | Built-in | Must implement |
| Streaming | Built-in | Requires `agent.run_stream()` (future) |
| KISS | High (zero code) | Medium (~80 LOC) |

**Verdict (.90):** Cannot use `Agent.to_cli()` — it bypasses SessionStore, HookRegistry, and UsageTracker. Write a custom loop that calls `OwlBearAgent.turn()`. This matches the daemon-bootstrap-research recommendation (§3.3 Pattern A: loop outside agent).

### 3.2 Multi-line Input

| Option | Description | Deps | Complexity | Prior art |
|--------|-------------|------|------------|-----------|
| A. `!multi`/`!end` markers | User types `!multi`, enters lines, `!end` to submit | None | Low | simonw/llm |
| B. `/multiline` toggle + Ctrl+D | Toggle mode, Ctrl+D submits | None | Low | PydanticAI clai |
| C. `prompt_toolkit` | Rich readline replacement | New dep | High | ipython, pgcli |
| D. No multi-line (MVP) | Single-line only | None | Minimal | — |

**Recommendation (.80):** Option A (`!multi`/`!end`). Matches established prior art (simonw/llm, 11k stars). No new dependency (KISS). Can upgrade to `prompt_toolkit` later (YAGNI).

### 3.3 Signal Handling

Both prior art projects handle exit signals similarly:

| Signal | Python exception | Behavior |
|--------|-----------------|----------|
| Ctrl+C | `KeyboardInterrupt` | Save session, print goodbye, exit 0 |
| Ctrl+D | `EOFError` / `readline()` returns `""` | Same as Ctrl+C |
| `exit`/`quit` typed | N/A (string match) | Same as Ctrl+C |

`CLIChannel.receive()` already returns `None` on EOF. For `KeyboardInterrupt`, wrap the main loop in try/except. This is the standard pattern in both `simonw/llm` and Python REPL conventions.

### 3.4 Session Naming and Persistence

| Option | Path | Description |
|--------|------|-------------|
| A. User-provided `--session NAME` | `~/.owlbear/sessions/{NAME}.jsonl` | Explicit, resumable |
| B. Auto-generated from timestamp | `~/.owlbear/sessions/{timestamp}.jsonl` | No collision, but hard to resume |
| C. Last-used default | `~/.owlbear/sessions/default.jsonl` | Simplest, one session at a time |

**Recommendation (.85):** Option A with fallback to B. `--session` flag names the session; if omitted, generate `chat-{YYYYMMDD-HHMMSS}`. This matches `simonw/llm`'s conversation model.

### 3.5 OwlBearAgent Toolset Gap

Current `OwlBearAgent.__init__` creates `Agent(model, instructions=...)` — no `toolsets` parameter. The AC requires "FileToolset + TerminalToolset + SkillRegistry". Two blockers:

1. **OwlBearAgent doesn't accept toolsets.** Needs a `toolsets` kwarg forwarded to the inner `Agent(... toolsets=[...])`.
2. **FileToolset (#120) and TerminalToolset (#121) don't exist yet** — both are in `ideation`.

| Approach | Description | Risk |
|----------|-------------|------|
| A. Block #122 on #120, #121 | Wait for toolsets to exist | Delays first working chat |
| B. Add toolsets to OwlBearAgent, wire chat without tools first | chat works now, tools added later | Low — tools are additive |
| C. Hardcode skip | Don't pass toolsets at all for MVP | Simplest but AC-noncompliant |

**Recommendation (.90):** Option B. Split into two sub-tasks: (1) add `toolsets` param to `OwlBearAgent`, (2) wire `bearclaw chat` with `toolsets=[]` (SkillRegistry only, since it exists). Wire FileToolset/TerminalToolset when #120/#121 are done. This unblocks the first working chat ASAP.

### 3.6 CLI Command Pattern

Existing `bearclaw` commands use `asyncio.run()` to bridge sync Typer with async code (see `auth login`, `browser status`). The chat command follows the same pattern:

```python
@app.command()
def chat(model: str = ..., session: str | None = None, workspace: str = ".") -> None:
    """Start an interactive chat session."""
    asyncio.run(_chat_async(model, session, workspace))
```

This is consistent with every other async command in the CLI.

### 3.7 Startup Banner

Both `simonw/llm` and `clai` print a banner on start. Recommended format:

```
OwlBear chat — model: gpt-4o | session: ~/.owlbear/sessions/chat-20260227-143000.jsonl
Type 'exit' to quit, '!multi' for multi-line input.
```

## 4. Recommendation (.88 confidence)

Implement `bearclaw chat` as a thin Typer command (~30 LOC) calling an async loop function (~60 LOC). The loop lives outside the agent (daemon-bootstrap-research §3.3 Option A). Start without FileToolset/TerminalToolset (add when #120/#121 complete). Add `toolsets` parameter to `OwlBearAgent` as a prerequisite sub-task.

**Risks and mitigations:**

- **Copilot token not available:** catch auth error, print message, exit with code 1.
- **Long conversations exceed context window:** defer to future task (session truncation/summarization). PydanticAI handles this at the model level.
- **No streaming for MVP:** `agent.turn()` returns full response. Add streaming later via `agent.inner.run_stream()`.

## 5. Follow-up Tasks

1. **Add `toolsets` param to OwlBearAgent** — forward to inner `Agent(... toolsets=[...])`. ~10 LOC diff. Prerequisite for #122.
2. **Implement `bearclaw chat` command** — Typer command + async loop. ~90 LOC new code. Depends on sub-task 1.
3. **Test `bearclaw chat`** — startup/shutdown cycle, message round-trip with mocked agent, Ctrl-C/D, multi-line input. ~100 LOC tests.
4. **Wire FileToolset when #120 completes** — add to chat command's toolsets list.
5. **Wire TerminalToolset when #121 completes** — add to chat command's toolsets list.
6. **Add streaming support** — use `agent.inner.run_stream()` for token-by-token output. Nice-to-have.
