# Context-Aware Knowledge Injection — Auto-RAG for Agent Turns

> **Owning task:** #305 — Context-aware research — use knowledge base to improve agent work
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Agents use static `context.md` + `MEMORY.md` (via `ContextManager`) and a one-shot `ContextInjectionHook` on SESSION_START. The knowledge base stores accumulated research, entity graphs, and document embeddings — but agents only access it when they manually call the `query_knowledge` tool. **Can we auto-inject relevant knowledge into the agent's system prompt each turn, based on the user's message?**

Key sub-questions: (a) what injection mechanism fits PydanticAI, (b) how to token-budget the injected context, (c) when to refresh (session-start only vs per-turn), (d) performance cost of embedding the user prompt each turn.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI `@agent.instructions` | ai.pydantic.dev/agents/#instructions | .95 | Dynamic instructions reevaluated per-run; runtime `instructions=` param on `.run()` |
| PydanticAI RAG example | ai.pydantic.dev/examples/rag/ | .90 | Tool-based RAG: agent calls `retrieve` tool explicitly, gets KB results |
| MemGPT (Packer et al., 2023) | arxiv.org/abs/2310.08560 | .85 | OS-inspired hierarchical memory: auto-retrieve from archival → inject into working context per turn |
| LlamaIndex ContextChatEngine | docs.llamaindex.ai | .80 | Auto-retrieves relevant nodes pre-query; prepends to system prompt with top-k + budget |
| OwlBear ContextInjectionHook | src/owlbear/core/context_hook.py | .95 | SESSION_START hook: reads instructions + kanban summary into `data["context"]` |
| OwlBear KnowledgeToolset | src/owlbear/tools/knowledge.py | .95 | `_query_knowledge()`: embed → `search_similar()` → `get_document()` → format |
| OwlBear TextChunker `_token_count` | src/owlbear/memory/knowledge/chunker.py | .90 | Word-split heuristic: `len(text.split())` — no tiktoken dependency |
| OwlBear OwlBearAgent.turn() | src/owlbear/core/agent.py | .95 | Turn loop: emit ON_MESSAGE → load history → `inner.run()` with `message_history` |

## 3. Analysis

### 3.1 PydanticAI Injection Mechanisms

PydanticAI provides three ways to inject instructions:

| Mechanism | When evaluated | Has user prompt? | Per-turn? | Complexity |
|-----------|---------------|-------------------|-----------|------------|
| `Agent(instructions="...")` | Construction | No | No | Trivial |
| `@agent.instructions` decorator | Each `.run()` call | No (only `RunContext.deps`) | Yes | Low |
| `.run(instructions="...")` runtime param | Each `.run()` call | Yes (caller provides) | Yes | Low |

**Key finding:** `@agent.instructions` cannot access the user's current prompt — only `RunContext.deps`. The runtime `instructions=` parameter on `.run()` is the correct mechanism because the caller (i.e., `OwlBearAgent.turn()`) has both the prompt AND knowledge service access.

### 3.2 Prior Art Comparison — Auto-Inject vs Tool-Based RAG

| Pattern | Used by | How it works | Pros | Cons |
|---------|---------|-------------|------|------|
| **Auto-inject** (system prompt prepend) | MemGPT, LlamaIndex ContextChatEngine | Query KB before LLM call, inject results into instructions | Agent always has context; no tool-call overhead | Extra embedding call per turn; may inject irrelevant context |
| **Tool-based** (agent decides when to query) | PydanticAI RAG example, OwlBear KnowledgeToolset | Agent calls `retrieve`/`query_knowledge` tool when it decides to | Agent controls relevance; no wasted tokens | Agent may forget to query; adds tool call round-trip |
| **Hybrid** (auto-inject + tool available) | MemGPT archival + core memory | Auto-inject top-K, agent can also tool-query for deeper search | Best of both worlds | Slightly more complex |

**Recommendation (.85):** **Hybrid** — auto-inject top-K relevant facts into instructions, keep `query_knowledge` tool for deep dives. This matches MemGPT's architecture and LlamaIndex's ContextChatEngine pattern.

### 3.3 Architecture Approaches for OwlBear

| Approach | Description | KISS | Testability | Existing pattern |
|----------|-------------|------|-------------|-----------------|
| **A. Modify `turn()` + runtime `instructions=`** (.85) | Create `KnowledgeQueryService`, call in `turn()`, pass result via `instructions=` | **High** | Mock service in tests | Follows PydanticAI's native API |
| B. ON_MESSAGE hook + deps state | Hook queries KB → stores on `OwlBearDeps.knowledge_context` → `@agent.instructions` reads | Medium | Indirect test path | Extends existing hook pattern |
| C. Extend `ContextInjectionHook` | Add knowledge query to existing hook, fire on ON_MESSAGE too | Low | Bloats existing class | Mixes SESSION_START + ON_MESSAGE concerns |

**Recommendation (.85): Approach A** — most direct, uses PydanticAI's designed-for-this `instructions=` parameter, no shared mutable state, fully testable with mock service.

### 3.4 KnowledgeQueryService Design

Thin, stateless query wrapper — **not** a new toolset, just a service object:

```python
class KnowledgeQueryService:
    """Query the knowledge base and format results for system prompt injection."""

    def __init__(self, vector_store, graph_store, embedding_provider, scopes=None): ...
    def query_for_context(self, prompt: str, *, max_tokens: int = 2000, top_k: int = 5) -> str:
        """Embed prompt, search KB, format + truncate to token budget."""
```

Flow: `embed(prompt)` → `search_similar(embedding, top_k, embedding_type="document")` → resolve doc IDs via `get_document()` → format as "You have access to these relevant facts from past research:" → truncate to `max_tokens` using `_token_count()`.

### 3.5 Token Budget Strategy

| Strategy | MemGPT | LlamaIndex | Proposed |
|----------|--------|------------|----------|
| Budget unit | Characters | Tokens (tiktoken) | Words (`len(text.split())`) |
| Default | ~2000 tokens | Configurable | 2000 words (~2600 tokens) |
| Truncation | Per-memory-tier caps | Per-node, drop lowest score | Per-result, drop lowest score first |

Using the existing `_token_count()` heuristic (word count) avoids a tiktoken dependency — KISS. The ~1.3x word-to-token ratio means 2000 words ≈ 2600 tokens, well within budget.

**Truncation algorithm:**

1. Sort results by similarity score descending
2. Iterate, appending formatted result text
3. Stop when cumulative `_token_count()` exceeds `max_tokens`
4. Return assembled string (may be empty if no results)

### 3.6 Per-Turn vs Session-Start Refresh

| Strategy | Latency | Relevance | Token cost |
|----------|---------|-----------|------------|
| Session-start only | One-time ~50ms | Stale after first turn | Fixed |
| **Per-turn** (.80) | ~50ms per turn | Always relevant to current prompt | Proportional to turns |
| Every N turns | Variable | May miss topic changes | Reduced |

**Recommendation (.80): Per-turn**, matching the AC requirement. The ~50ms embedding call (BGE-M3 on GPU/CPU) is negligible vs LLM round-trip time (~2-10s). If knowledge service is unavailable, gracefully skip (empty instructions string → PydanticAI ignores it).

### 3.7 Performance Assessment

| Operation | Latency (BGE-M3 loaded) | Latency (cold start) |
|-----------|------------------------|---------------------|
| Embed single query | ~20-50ms | ~3s (model load) |
| Qdrant search (top-5) | ~5-10ms | Same |
| GraphStore.get_document (×5) | ~1-5ms | Same |
| Format + truncate | <1ms | Same |
| **Total per-turn overhead** | **~30-70ms** | **~3s first turn** |

Cold start only happens once per daemon lifecycle (BGE-M3 lazy-loads). After that, per-turn overhead is <100ms — invisible compared to LLM latency.

### 3.8 Integration into OwlBearAgent.turn()

```python
# In OwlBearAgent.turn():
async def turn(self, prompt: str) -> str:
    await self.hooks.emit(HookEvent.ON_MESSAGE, {"prompt": prompt})
    history = self.session.load()

    # Knowledge context injection (per-turn)
    runtime_instructions: str | None = None
    if self._knowledge_service is not None:
        runtime_instructions = self._knowledge_service.query_for_context(prompt)

    result = await self.inner.run(
        prompt,
        message_history=history or None,
        deps=self._deps,
        instructions=runtime_instructions,  # PydanticAI runtime instructions
    )
    ...
```

### 3.9 Config Integration

One new setting in `OwlBearSettings`:

```python
knowledge_context_tokens: int = 2000  # max word-count for auto-injected knowledge context
```

## 4. Recommendation (.85 confidence)

**Build `KnowledgeQueryService` + modify `OwlBearAgent.turn()` to auto-inject per-turn knowledge context via PydanticAI's `instructions=` parameter.**

- `KnowledgeQueryService` at `src/owlbear/memory/knowledge/query_service.py` (~60 LOC)
- Modify `OwlBearAgent.__init__` to accept optional `knowledge_service` (~5 LOC)
- Modify `OwlBearAgent.turn()` to call service and pass `instructions=` (~8 LOC)
- Wire in `bootstrap.py`: create service alongside `KnowledgeToolset` (~10 LOC)
- Add `knowledge_context_tokens` config setting (~2 LOC)
- Keep `query_knowledge` tool available for deep dives (hybrid approach)

**Risks:**

- **Irrelevant context injection:** Mitigated by similarity threshold — only inject results above score 0.3.
- **Empty knowledge base:** Service returns `None` → PydanticAI ignores `instructions=None`.
- **Embedding latency on cold start:** ~3s first turn. Mitigated by existing lazy-load + idle timeout.
- **Token bloat:** Capped at configurable `max_tokens` (default 2000 words).

## 5. Follow-up Tasks

1. **Implement `KnowledgeQueryService`** — `src/owlbear/memory/knowledge/query_service.py`: embed query → search → format → truncate. TDD. ~60 LOC.
2. **Add `knowledge_context_tokens` config** — `OwlBearSettings.knowledge_context_tokens: int = 2000`. TDD. ~5 LOC.
3. **Integrate into `OwlBearAgent.turn()`** — Accept optional `knowledge_service`, query per-turn, pass via `instructions=`. TDD. ~15 LOC. Depends on task 1.
4. **Wire `KnowledgeQueryService` in bootstrap** — Build alongside `KnowledgeToolset` in `_build_knowledge_toolset()`, pass to agent constructor. ~15 LOC. Depends on tasks 1-3.
5. **Move #305 to backlog** — Research complete, ready for architect review.
