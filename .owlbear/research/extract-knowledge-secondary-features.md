# Extract Knowledge Secondary Features

> **Owning task:** #130 — Extract knowledge secondary features (consolidation, evaluator, bookmark pipeline, refresh)
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #130 extracts 5 remaining v1 knowledge modules not covered by #15/#32/#33/#34:
`consolidation.py`, `evaluator.py`, `bookmark_pipeline.py`, `bookmark_toolset.py`, `refresh.py`.
Key questions: (a) dependency order, (b) how to replace PydanticAI deps with pluggable LLM interfaces,
(c) what additional utilities must be extracted.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| v1 knowledge codebase | Local (`v1/src/owlbear/memory/knowledge/`) | `1.0` — actual modules being extracted |
| v2 knowledge package | Local (`packages/knowledge/src/owlbear_knowledge/`) | `1.0` — existing extraction patterns (Protocol, stub) |
| #15 research doc | `docs/research/extract-knowledge-engine-v1.md` | `.90` — parent extraction analysis, §3.7 |
| Cooperative cancellation research | `docs/research/cooperative-cancellation.md` | `.85` — CancelSignal Protocol design |
| LlamaIndex LLM interface | `github.com/run-llama/llama_index` llms/llm.py (946 LOC) | `.40` — over-engineered counter-example |
| LangChain BaseLanguageModel | `github.com/langchain-ai/langchain` language_models/base.py | `.40` — over-engineered counter-example |

## 3. Analysis

### 3.1 Module Dependency Map

| Module | LOC | PydanticAI? | v2 deps available? | Blocked by |
|--------|-----|-------------|--------------------|----|
| `consolidation.py` | 113 | Agent (text→str) | GraphStore ✓, sqlite3 ✓ | None |
| `evaluator.py` | 166 | Agent (structured output) | — | None |
| `bookmark_pipeline.py` | 265 | No (composed) | BookmarkStore ✓ | #33 (IngestPipeline) |
| `bookmark_toolset.py` | 143 | FunctionToolset | BookmarkPipeline | bookmark_pipeline + MCP |
| `refresh.py` | 331 | No | SourceStore ✓, SourceType ✓ | #33 (IngestPipeline) |

**Critical finding:** bookmark_pipeline and refresh both import `IngestPipeline`/`IngestResult` from the
ingest module, which is scoped to task #33 (currently at `ideation`). These two modules cannot be
extracted until #33 lands.

### 3.2 Additional Utilities Needed

| Utility | v1 location | LOC | Used by |
|---------|-------------|-----|---------|
| `CancelSignal` Protocol + `LinkedCancelSignal` | `cancellation.py` | 30 | bookmark_pipeline, refresh |
| `sandbox_path` | `paths.py` | 14 | refresh (`_handle_file_glob`) |

`CancelSignal` is a 2-method Protocol already designed in `docs/research/cooperative-cancellation.md`.
`sandbox_path` is a 14-LOC security utility preventing path-traversal outside workspace root. Both
belong in `packages/knowledge/` — CancelSignal as `cancellation.py`, sandbox_path as a function in
a new `_paths.py` (private module, not re-exported).

### 3.3 PydanticAI Replacement: LLM Protocol Design

v1 uses PydanticAI `Agent` in two distinct patterns:

| Pattern | v1 usage | Input → Output | v1 module |
|---------|----------|----------------|-----------|
| **Text completion** | `Agent(model, system_prompt=...)` → `.run(prompt)` → `str` | `str → str` | consolidation |
| **Structured output** | `Agent(model, output_type=T, system_prompt=...)` → `.run(prompt)` → `T` | `str → EvaluationResult` | evaluator |

**Existing v2 pattern (extractor.py):** stub class that returns empty results; real LLM wired
at application layer. This works but doesn't satisfy the AC's "pluggable LLM interface" requirement.

**Recommended approach (.85 confidence):** Async callable injection via type aliases. This
matches KISS — no framework, no ABC hierarchy, just typed callables:

```python
from collections.abc import Awaitable, Callable

TextCompletionFn = Callable[[str], Awaitable[str]]
# For evaluator: Callable[[str], Awaitable[EvaluationResult]]
```

ConsolidationService and SourceEvaluator take these callables as constructor args.
Tests inject simple lambdas/AsyncMock. Application layer injects real LLM calls.

**Why not Protocol?** A Protocol adds a class definition for what is effectively a single function
signature. `Callable` type aliases are simpler and equally type-safe. Both LlamaIndex (946 LOC)
and LangChain's approach are vastly over-engineered — we need ~3 lines, not 946.

### 3.4 bookmark_toolset.py → MCP

v1's `BookmarkToolset` is a PydanticAI `FunctionToolset` wrapping 2 tool functions:
`bookmark_source` and `list_bookmarks`. These are thin wrappers around `BookmarkPipeline.process()`
and `BookmarkStore.list()`. The toolset has zero domain logic of its own.

**Recommendation (.90 confidence):** Do not extract bookmark_toolset.py. Register these as MCP
tools in the `mcp-knowledge` server (already exists at `packages/mcp-knowledge/`). Task #55
("Add ingest and graph tools to mcp-knowledge") is the natural home.

### 3.5 UsageTracker Dep in evaluator.py

evaluator.py imports `UsageTracker` and `record_agent_usage` from `owlbear.memory.usage`.
This is a v1-specific cost tracking mechanism tied to PydanticAI result objects.

**Recommendation (.90 confidence):** Drop UsageTracker. YAGNI — v2 doesn't have the usage
tracking infrastructure, and adding it is out of scope. If needed later, it can be re-added
as an optional callback.

### 3.6 Dependency-Based Task Split

| Group | Modules | Deps on #33? | Can start now? |
|-------|---------|--------------|----------------|
| **A** | cancellation, consolidation, evaluator, sandbox_path | No | Yes |
| **B** | bookmark_pipeline, refresh | Yes (IngestPipeline, IngestResult) | After #33 |
| **C** | bookmark_toolset → MCP tools | Yes (BookmarkPipeline) | After Group B |

## 4. Recommendation (.85 confidence)

Split #130 into two implementation tasks along the dependency boundary:

**Task A (no blockers):** Extract CancelSignal protocol, sandbox_path utility, ConsolidationService,
and SourceEvaluator. Replace PydanticAI Agent with async callable injection. Drop UsageTracker.

**Task B (depends on #33):** Extract BookmarkPipeline and RefreshOrchestrator. Wire CancelSignal
and IngestPipeline protocols. Add bookmark MCP tools to mcp-knowledge (replaces bookmark_toolset.py).

**Risks:**
- Group B cannot start until #33 completes. #33 is at `ideation` — timeline unknown.
- `sandbox_path` needs a home. Putting it in `packages/knowledge/_paths.py` is expedient but it's
  a general utility. If other packages need it, extract to a shared utils package later.
- The LLM callable approach is minimal but means tests use AsyncMock rather than protocol instances.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Extract CancelSignal, sandbox_path, consolidation, and evaluator into knowledge package" --priority nice-to-have --status ideation --tags "phase-1,scope:knowledge,type:build" --body "## Objective\nExtract Group A modules from v1 that have no IngestPipeline dependency.\n\n## Acceptance Criteria\n- [ ] Extract CancelSignal Protocol + LinkedCancelSignal from v1 cancellation.py into packages/knowledge/src/owlbear_knowledge/cancellation.py\n- [ ] Extract sandbox_path from v1 paths.py into packages/knowledge/src/owlbear_knowledge/_paths.py\n- [ ] Extract ConsolidationService with async callable LLM injection (replace PydanticAI Agent)\n- [ ] Extract SourceEvaluator + EvaluationResult with async callable LLM injection (drop UsageTracker)\n- [ ] Unit tests for all extracted modules (in-memory SQLite, AsyncMock for LLM)\n- [ ] Update packages/knowledge __init__.py exports\n\n## Context\nSplit from #130 (Group A — no #33 dependency). See docs/research/extract-knowledge-secondary-features.md §3."

kanban\kanban-md.exe create "Extract bookmark pipeline, refresh orchestrator, and bookmark MCP tools" --priority nice-to-have --status ideation --tags "phase-1,scope:knowledge,type:build" --body "## Objective\nExtract Group B modules from v1 that depend on IngestPipeline (#33).\n\n## Acceptance Criteria\n- [ ] Extract BookmarkPipeline (bookmark_pipeline.py) with CancelSignal and IngestPipeline protocol deps\n- [ ] Extract RefreshOrchestrator (refresh.py) with sandbox_path, CancelSignal, and IngestPipeline deps\n- [ ] Register bookmark_source and list_bookmarks as MCP tools in mcp-knowledge (replaces bookmark_toolset.py)\n- [ ] Unit tests for BookmarkPipeline and RefreshOrchestrator\n- [ ] Do NOT extract bookmark_toolset.py as a module — MCP tools replace it\n\n## Context\nSplit from #130 (Group B — depends on #33 IngestPipeline). See docs/research/extract-knowledge-secondary-features.md §3.\n\n## Dependencies\n- Depends on #33 (entity extraction + graph builders — provides IngestPipeline/IngestResult)\n- Depends on Group A task (provides CancelSignal, sandbox_path, SourceEvaluator)"
```
