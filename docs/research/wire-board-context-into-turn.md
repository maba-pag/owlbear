# Wire BoardContextProvider into agent turn() instructions

> **Owning task:** #771 — Wire BoardContextProvider into agent turn() instructions
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

Task #770 introduces `BoardContextProvider` — a TTL-cached subprocess wrapper
that runs `kanban-md list --compact` and returns ~220 tokens of board state.
This task (#771) wires that provider into `OwlBearAgent.turn()` so board state
reaches the LLM as part of the system prompt.

Key questions: (a) how does PydanticAI's runtime `instructions=` parameter
work with multiple context sources? (b) what's the minimal `turn()` change?
(c) what config setting is needed? (d) what bootstrap wiring is required?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PydanticAI — Instructions (runtime) | <https://ai.pydantic.dev/agents/#instructions> | .95 |
| PydanticAI — Agent.run() API | <https://ai.pydantic.dev/api/agent/> | .90 |
| OwlBear `agent.turn()` | `src/owlbear/core/agent.py` | .95 |
| OwlBear `KnowledgeQueryService` | `src/owlbear/memory/knowledge/query_service.py` | .90 |
| OwlBear `OwlBearSettings` | `src/owlbear/config.py` | .85 |
| OwlBear `bootstrap/__init__.py` | `src/owlbear/bootstrap/__init__.py` | .85 |
| MC generate-context.ts (prior art) | `docs/research/compact-board-context.md` S3.1 | .70 |

## 3. Analysis

### 3.1 PydanticAI Runtime Instructions Behavior

PydanticAI `Agent.run(instructions=...)` accepts `str`. Runtime instructions are
**appended** to static + dynamic instructions in order. Passing `None` skips
the runtime instructions entirely. This means a single `instructions=` string
works as the merge point for both knowledge context and board context.

### 3.2 Concatenation Strategy

| Strategy | Pros | Cons | KISS |
|----------|------|------|------|
| A: Two separate `instructions=` calls | Impossible — `run()` takes one string | N/A | N/A |
| B: Concatenate in `turn()` before passing | Simple, explicit, testable | ~5 LOC | **High** |
| C: `@agent.instructions` decorator | Per-run dynamic eval; cleaner API | Requires deps wiring, harder to test | Medium |
| D: Compose providers into a pipeline | Extensible | Over-engineered for 2 sources | Low |

**Strategy B** is the clear winner. Concatenate board context and knowledge
context into one string, separated by a clear delimiter, before passing to
`inner.run(instructions=...)`.

### 3.3 turn() Change Shape

Current flow in `turn()`:

1. Call `_knowledge_service.query_for_context(prompt)` → `str | None`
2. Pass result as `instructions=` to `inner.run()`

Proposed flow:

1. Call `_board_context_provider.get_context()` → `str` (empty on failure)
2. Call `_knowledge_service.query_for_context(prompt)` → `str | None`
3. Merge non-empty results: `"\n\n".join(filter(None, [board_ctx, knowledge_ctx]))`
4. Pass merged string (or skip `instructions=` if both empty) to `inner.run()`

Board context goes **first** because it's static situational awareness (~220
tokens), while knowledge context is prompt-specific (~2000 tokens). LLMs
weight earlier instructions more heavily in some architectures.

### 3.4 Config Setting

Follow existing pattern (e.g. `condenser_enabled`, `knowledge_graph_expansion`):

```
board_context_enabled: bool = Field(default=True, ...)
```

Default `True` — this is a quality-gate feature (board awareness improves
agent decisions), not an experimental flag. Follows architecture-standards
convention: quality gates default on, feature flags default off.

### 3.5 Bootstrap Wiring

In `bootstrap/__init__.py`, construct `BoardContextProvider` when
`settings.board_context_enabled` is True, pass it to `OwlBearAgent(...)`.
Follow the `knowledge_service=` constructor pattern.

## 4. Recommendation (.85 confidence)

**Strategy B — concatenate in `turn()`** with these specifics:

- New `board_context_provider` optional parameter on `OwlBearAgent.__init__`
- In `turn()`, call provider first (graceful degradation), then knowledge
  service, merge non-empty results, pass as `instructions=`
- Config: `board_context_enabled: bool = True` in `OwlBearSettings`
- Bootstrap: construct provider when enabled, pass to agent constructor

**Risks:**

- Depends on #770 (BoardContextProvider must exist first)
- Token budget: ~220 (board) + ~2000 (knowledge) = ~2220 tokens per turn,
  well within context window limits

## 5. Follow-up Tasks

No new follow-up tasks needed — #771 itself is the implementation task.
The AC below refines the task body for the builder.

### Refined AC for #771

```
AC:
1. OwlBearAgent.__init__ accepts optional board_context_provider parameter
2. turn() calls board_context_provider.get_context() before knowledge service
3. Board context and knowledge context concatenated into single instructions= string
4. Graceful degradation: provider exception → log WARNING, continue without board context
5. No instructions= kwarg when both sources return None/empty
6. Config: board_context_enabled bool in OwlBearSettings (default True)
7. Bootstrap: construct BoardContextProvider when enabled, pass to OwlBearAgent
8. Unit tests: provider None, provider returns string, provider raises, both sources,
   neither source, provider + no knowledge service
```

## 6. Testing Strategy

Mirror `TestOwlBearAgentKnowledgeInjection` test class pattern in
`tests/test_agent.py`. Mock `BoardContextProvider` (it's a simple protocol
with `get_context() -> str`). Test matrix:

| Board ctx | Knowledge ctx | Expected instructions= |
|-----------|--------------|----------------------|
| None provider | None service | not passed |
| None provider | returns str | knowledge only |
| returns str | None service | board only |
| returns str | returns str | board + knowledge |
| raises | returns str | knowledge only (warning logged) |
| returns "" | returns str | knowledge only |
