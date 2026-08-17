# Wire LLMExtractor into MCP Knowledge Server

> **Owning task:** #876 — P3-07: Wire LLMExtractor into MCP knowledge server
> **Date:** 2026-04-14 **Status:** Complete

## 1. Context and Question

After #874 research (StructuredExtractor replacement) and #875 (LLMExtractor implementation — currently `backlog`), the MCP knowledge server's `app_lifespan()` still creates `EntityExtractor()` with no injected extractor (no-op). Graph builders (`IntraDocGraphBuilder`, `InterDocGraphBuilder`) are not instantiated in `server.py` at all.

**Question:** What is the composition wiring pattern for conditionally activating LLM extraction in `server.py` — env var naming, gating conditions, graph builder placement, and testing strategy?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `server.py` — `app_lifespan()` composition (line 168–215) | Codebase | 1.0 |
| S2 | `extractor.py` — `EntityExtractor(extractor=)` DI pattern | Codebase | 1.0 |
| S3 | `graph_builder.py` — `IntraDocGraphBuilder(extractor=)` (optional) | Codebase | 0.95 |
| S4 | `inter_doc_graph_builder.py` — `InterDocGraphBuilder(extractor=)` (required) | Codebase | 0.95 |
| S5 | `protocol.py` — `StructuredExtractor` protocol definition | Codebase | 0.95 |
| S6 | `qdrant.py`, `intake.py` — conditional import patterns | Codebase | 0.90 |
| S7 | `.owlbear/research/874-structuredextractor-replacement.md` | Research | 0.90 |
| S8 | `.owlbear/research/875-llmextractor-openai-implementation.md` | Research | 0.90 |
| S9 | `.owlbear/research/864-wire-interdocgraphbuilder-pipeline.md` | Research | 0.85 |
| S10 | `serve/knowledge/pyproject.toml` — optional dep groups pattern | Codebase | 0.85 |

## 3. Analysis

### 3.1 Gating Condition

| Option | Condition | Pros | Cons |
|--------|-----------|------|------|
| Import-only | `try: from ..llm_extractor import LLMExtractor` succeeds | Simple | Creates useless client if no API key set |
| Import + key | Import succeeds AND `OPENAI_API_KEY` is set | Avoids spurious init | 1 extra env check |
| Import + model | Import succeeds AND `OWLBEAR_LLM_MODEL` is set | Explicit opt-in | Could miss users who want SDK defaults |

**(rec:) Import + key.** The openai SDK raises `OpenAIError` at call-time if no key is set, but creating `AsyncOpenAI()` without a key is wasteful. Checking for key presence avoids a no-op extractor that fails on every call.

### 3.2 Env Var Naming

| Convention | Vars | Pros | Cons |
|------------|------|------|------|
| A: OWLBEAR_ prefix | `OWLBEAR_LLM_MODEL`, `OWLBEAR_LLM_API_KEY`, `OWLBEAR_LLM_BASE_URL` | Consistent namespace, matches `OWLBEAR_KB_PATH` | Users must duplicate `OPENAI_API_KEY` |
| B: OPENAI_ standard | `OPENAI_API_KEY`, `OPENAI_BASE_URL` + `OWLBEAR_LLM_MODEL` | Works with existing env setups | Mixed naming |
| C: Hybrid fallback | `OWLBEAR_LLM_*` → `OPENAI_*` fallback | Best of both | 3 extra env reads |

**(rec:) Option C — hybrid fallback.** Read `OWLBEAR_LLM_API_KEY` first, fall back to `OPENAI_API_KEY`. The `openai` SDK auto-reads `OPENAI_API_KEY` internally, but explicit reading lets us gate on key presence. Model name uses `OWLBEAR_LLM_MODEL` only (no SDK default). ~3 extra LOC, eliminates user friction.

### 3.3 Graph Builder Placement

| Component | Constructor | Extractor required? | Server.py change |
|-----------|-------------|--------------------|--------------------|
| `EntityExtractor` | `EntityExtractor(extractor=X)` | No (None = no-op) | Replace `EntityExtractor()` → `EntityExtractor(extractor=llm_ext)` |
| `IntraDocGraphBuilder` | `IntraDocGraphBuilder(extractor=X)` | No (None = no-op) | Add instantiation + AppContext field |
| `InterDocGraphBuilder` | `InterDocGraphBuilder(extractor, vs, gs)` | **Yes** (positional) | Only create when extractor exists; add AppContext field |

`IntraDocGraphBuilder` can always be created (no-op without extractor). `InterDocGraphBuilder` must be `None` when no extractor exists — its constructor requires a `StructuredExtractor`.

Both should be added to `AppContext` for downstream use by #864 (refresh pipeline wiring).

### 3.4 Implementation Shape (~20 LOC)

```python
# In app_lifespan(), after vs/gs/emb creation:
structured_extractor: StructuredExtractor | None = None
try:
    from owlbear_knowledge.llm_extractor import LLMExtractor  # noqa: PLC0415

    api_key = os.environ.get("OWLBEAR_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        model = os.environ.get("OWLBEAR_LLM_MODEL", "gpt-4o-mini")
        base_url = os.environ.get("OWLBEAR_LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
        structured_extractor = LLMExtractor(model=model, api_key=api_key, base_url=base_url)
except ImportError:
    pass

extractor = EntityExtractor(extractor=structured_extractor)
intra_builder = IntraDocGraphBuilder(extractor=structured_extractor)
inter_builder = InterDocGraphBuilder(structured_extractor, vs, gs) if structured_extractor is not None else None
```

AppContext gains 3 optional fields: `intra_doc_builder`, `inter_doc_builder`, `structured_extractor`.

### 3.5 Testing Strategy

| Test | Method | Verifies |
|------|--------|----------|
| openai importable + key set | Patch import, set env vars | `LLMExtractor()` created, passed to `EntityExtractor` |
| openai importable, no key | Patch import, unset env vars | Falls back to `EntityExtractor(extractor=None)` |
| openai not importable | Patch import to raise `ImportError` | Falls back, no import error |
| InterDocGraphBuilder gating | Extractor=None | `inter_doc_builder` is `None` |
| InterDocGraphBuilder created | Extractor exists | `inter_doc_builder` receives extractor, vs, gs |
| Env var fallback | Set `OPENAI_API_KEY` only | Reads fallback correctly |

All tests mock `LLMExtractor` — no real API calls. Existing `test_ingest_graph_wiring.py` provides pattern.

### 3.6 Dependency Status

**#875 (LLMExtractor implementation) is at `backlog` — not yet implemented.** `llm_extractor.py` only has the `LLM_EXTRACTION_PROMPT` constant, no `LLMExtractor` class. The `from owlbear_knowledge.llm_extractor import LLMExtractor` in the wiring code will raise `ImportError` until #875 is complete. The `try/except ImportError` pattern handles this gracefully — server operates in no-op mode until #875 lands.

## 4. Recommendation (confidence: .88)

Use the hybrid env var pattern (C) with import+key gating. ~20 LOC in `app_lifespan()`, 3 new `AppContext` fields. The `try/except ImportError` pattern is already established in `qdrant.py` and `intake.py` (S6). All AC items are technically feasible with no architecture changes.

Challenge: FALLBACK — challenger subagent not in available roster.

**Tier classification: T1 — Autonomous.** Composition wiring with existing DI slots. No new architecture, no security policy changes, no user-facing behavior changes. The protocol interface is unchanged; only the server composition gains conditional instantiation.

## 5. Follow-up Tasks

No new tasks needed beyond #876 itself — AC is complete and implementation-ready. #875 (dependency) is already tracked at `backlog`.
