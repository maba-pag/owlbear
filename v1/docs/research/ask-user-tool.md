# Channel-based ask_user Tool — Research

> **Owning task:** #123 — Channel-based ask_user tool — agent asks, user answers
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear agents need a human-in-the-loop mechanism: ask the user a question and get an answer, over any channel (CLI, Slack, future). Task #122 (done) established the `ChannelPlugin` protocol with `send()` / `receive()`. This research determines how to implement an `ask_user` tool that leverages that protocol, following OwlBear's existing toolset patterns.

**Key questions:**

1. What pattern should the tool follow (FunctionToolset subclass, standalone, deps-injected)?
2. How should timeout, option validation, and error handling work?
3. What prior art exists for agent→user question tools?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI Deferred Tools | <https://ai.pydantic.dev/deferred-tools/> | .50 | `ApprovalRequired` / `DeferredToolRequests` — tool _approval_ gates, different from conversational ask_user |
| PydanticAI FunctionToolset | <https://ai.pydantic.dev/toolsets/> | .90 | `FunctionToolset.add_function()` API — the pattern all OwlBear toolsets follow |
| CrewAI `human_input` | <https://docs.crewai.com/concepts/agents> | .65 | Boolean flag on tasks; uses `input()` for user prompts; no channel abstraction |
| Anthropic Tool Use | <https://platform.claude.com/docs/en/docs/build-with-claude/tool-use> | .70 | Standard tool-call pattern where agent calls tool and gets result inline |
| OwlBear BrowserToolset | `src/owlbear/tools/browser/toolset.py` | .95 | Local pattern: FunctionToolset subclass, constructor injection, `add_function()` registration |
| OwlBear TerminalToolset | `src/owlbear/tools/terminal.py` | .90 | Local pattern: async tool with timeout via `asyncio.wait_for`, configurable max output |
| OwlBear ChannelPlugin | `src/owlbear/channels/base.py` | 1.0 | Protocol with `send()` and `receive(prompt=)` — the I/O interface |
| OwlBear SlackChannel | `src/owlbear/channels/slack.py` | .85 | `receive()` already has timeout via `asyncio.wait_for`, returns `None` on timeout |

## 3. Analysis

### 3.1 Architecture Pattern

| Option | Description | Consistency | Complexity | Testability |
|--------|-------------|-------------|------------|-------------|
| A. FunctionToolset subclass | `AskUserToolset(channel)`, registers `ask_user` via `add_function()` | High — matches Browser, File, Terminal, Skills | Low (~80 LOC) | High — inject mock channel |
| B. Standalone function + thin wrapper | Pure `ask_user()` function; separate toolset wraps it | Medium — Browser uses this internally | Low (~90 LOC) | High |
| C. Deps-injected via RunContext | Channel in `deps_type`, tool accesses `ctx.deps.channel` | Low — agent currently uses `Agent[None, str]`, no deps | Medium — requires agent refactor | Medium |

**Recommendation (.90):** **Option A** — single `AskUserToolset(FunctionToolset)` class. KISS-aligned, matches every other toolset in the codebase. The tool is simple enough that splitting action from toolset (Option B) is unnecessary abstraction. Option C requires changing `OwlBearAgent` to use deps, which is a separate concern (YAGNI).

### 3.2 Timeout Handling

| Strategy | Description | Ergonomics | Risk |
|----------|-------------|------------|------|
| Raise exception on timeout | `AskUserTimeoutError` — agent turn fails | Clear — agent knows user didn't respond | Agent loses context if not handled |
| Return default string on timeout | Return e.g. `"(no response — skipped)"` | Soft — agent can proceed | Agent may act on non-answer |
| Configurable via enum | `TimeoutAction.ABORT` or `TimeoutAction.SKIP` with default string | Flexible — caller chooses | Slightly more config surface |

**Recommendation (.85):** **Configurable enum approach.** Default to `ABORT` (raise). The `TerminalToolset` follows a similar pattern (configurable timeout). Two behaviors cover all use cases without over-engineering.

Implementation: wrap `channel.receive()` in `asyncio.wait_for(timeout=...)`. Both CLIChannel (blocks on readline) and SlackChannel (already has its own timeout) work correctly — `wait_for` adds a second layer for the tool's own timeout, independent of the channel's internal timeout.

### 3.3 Option Validation

| Approach | Description | UX | Complexity |
|----------|-------------|-----|-----------|
| Strict match | Accept only exact text from options list | Rigid — typos fail | Low |
| Index + text, case-insensitive | Accept number ("1") or text ("high"), `.lower()` match | Natural — works for CLI and Slack | Low |
| Fuzzy match | Levenshtein distance | Over-engineered | Medium |

**Recommendation (.90):** **Index + text, case-insensitive.** Format prompt as numbered list: `"[1] high  [2] medium  [3] low"`. Accept either `"1"` or `"high"`. On invalid input, re-ask up to `max_retries` (default 3). After exhausting retries, apply `timeout_action` behavior (abort or skip).

### 3.4 Prompt Formatting

The tool should format the prompt for the channel, not the agent. The agent provides `question` and optional `options`; the tool builds a clean prompt:

```
What priority should this task have?
[1] high
[2] medium
[3] low
Choose [1-3]:
```

For free-text (no options), the prompt is just the question followed by `receive()`.

### 3.5 Integration with OwlBearAgent

Currently, `OwlBearAgent.__init__` accepts `channel: ChannelPlugin | None`. The chat REPL (`_chat_async`) creates the channel and agent separately. The `AskUserToolset` should be created alongside other toolsets during agent setup and passed as a toolset — not coupled to `OwlBearAgent` internals.

```python
channel = CLIChannel()
toolsets = [
    FileToolset(workspace_root),
    TerminalToolset(workspace_root=workspace_root),
    AskUserToolset(channel),            # ← new
]
agent = OwlBearAgent(model=model, toolsets=toolsets, ...)
```

This keeps the channel decoupled from the agent (Option A from daemon-bootstrap-research).

## 4. Recommendation (.88 confidence)

**Single `AskUserToolset(FunctionToolset)` with configurable timeout and option validation.**

- **File:** `src/owlbear/tools/ask_user.py` (~80 LOC)
- **Class:** `AskUserToolset(FunctionToolset)` with constructor params:
  - `channel: ChannelPlugin` — required
  - `timeout_seconds: float = 120.0`
  - `max_retries: int = 3`
  - `timeout_action: TimeoutAction = TimeoutAction.ABORT`
  - `default_response: str = "(no response)"` — used when `SKIP`
- **Tool:** `ask_user(question: str, options: list[str] | None = None) -> str`
- **Custom exception:** `AskUserTimeoutError(TimeoutError)` in same module
- **Enum:** `TimeoutAction(StrEnum)` with `ABORT` and `SKIP`

**Risks and mitigations:**

- **CLIChannel readline blocks forever:** `asyncio.wait_for()` wrapping `channel.receive()` handles this — Python's event loop can cancel the coroutine.
- **Slack message ordering:** User might send unrelated message while ask_user waits. Mitigation: SlackChannel's queue processes messages in order; the prompt clarifies what's expected. Acceptable for MVP.
- **Agent misuse:** Agent may call `ask_user` excessively. Mitigation: rate-limiting is a future concern; for now, the max_retries cap prevents infinite loops within a single ask.

## 5. Follow-up Tasks

1. **Test `AskUserToolset`** — TDD: write tests for free-text, options, invalid input, timeout abort, timeout skip
2. **Implement `AskUserToolset`** — the toolset class with all AC items
3. **Wire `AskUserToolset` into chat REPL** — add to `_chat_async` toolset list in `bearclaw/cli.py`
