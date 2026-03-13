# Derive Hardcoded Model Defaults from OwlBearSettings

> **Owning task:** #551 — Derive hardcoded model defaults from OwlBearSettings
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

INT-15 flagged `"gpt-4o"` hardcoded in 3+ places. Should all derive from `OwlBearSettings.chat_model`. Is centralizing correct, and what's the minimal change?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PydanticAI Agent docs | <https://ai.pydantic.dev/agents/> | .85 |
| pydantic-settings docs | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/> | .90 |
| FastAPI Settings pattern | <https://fastapi.tiangolo.com/advanced/settings/> | .80 |
| OwlBear codebase (grep `gpt-4o`) | local | 1.0 |

## 3. Codebase Audit — All 14 `"gpt-4o"` References

### Category A: Redundant defaults on function signatures (4 — actionable)

| File | Line | Signature |
|------|------|-----------|
| `bootstrap.py` | 276 | `_build_knowledge_infra(chat_model="gpt-4o")` |
| `bootstrap.py` | 333 | `_build_knowledge_toolset(chat_model="gpt-4o")` |
| `bootstrap.py` | 431 | `_build_bookmark_toolset(chat_model="gpt-4o")` |
| `agent_registry.py` | 65 | `AgentRegistry.__init__(default_model="gpt-4o")` |

These defaults are **never hit in production** — `build_toolsets()` always passes `chat_model or settings.chat_model` (lines 649/660/672), and `build_agent_registry()` resolves `model if model is not None else settings.chat_model` (line 806). But they violate DRY and could silently use a stale default if a new caller forgets to pass the model.

### Category B: Docstring/usage examples (5 — no change needed)

`core/agent.py:46`, `planning/extractor.py:53`, `evaluator.py:87`, `extractor.py:57`, `graph_builder.py:64`, `inter_doc_graph_builder.py:62` — all in docstring `Usage::` blocks showing standalone instantiation.

### Category C: Lookup tables / data references (3 — no change needed)

`copilot_multipliers.py:18-19` (rate multiplier dict), `usage_cost.py:38` (docstring param example).

### Category D: Settings field — the source of truth (1 — already correct)

`config.py:41` — `chat_model: str = Field(default="gpt-4o")`. This is correct and should remain the single authoritative default.

## 4. Analysis

| Criterion | Remove defaults (make required) | Replace with `None` sentinel | Keep status quo |
|-----------|------|------|------|
| DRY | High — one source of truth | High — one source of truth | Low — 5 copies |
| Safety | High — callers forced to pass | Medium — `None` could propagate | Low — silent stale default |
| Breaking change | Medium — tests calling directly need updating | Low — existing callers unaffected | None |
| KISS | High — simpler signatures | Medium — `None` checks needed | Low — looks simple but hides drift |
| Backwards compat | N/A (project principle: no legacy) | N/A | N/A |

### Prior art

- **PydanticAI**: Agent constructor accepts `model` as a required-ish first positional arg with no built-in settings integration. Configuration is the caller's responsibility. This validates our pattern where `bootstrap()` resolves the model from settings and passes it down.
- **pydantic-settings**: The standard pattern is one `BaseSettings` class as single source of truth, with all consumers reading from that instance. Field defaults live only on the settings class.
- **FastAPI**: Recommends `@lru_cache` singleton settings with all config centralized. Components receive config via dependency injection, never hardcode defaults.

All three sources confirm: **defaults belong in the settings class; consumers should receive the resolved value, not re-declare their own default**.

## 5. Recommendation (.85 confidence)

**Remove the `"gpt-4o"` defaults from the 4 Category A signatures.** Make `chat_model`/`default_model` a required parameter (no default). This is the cleanest approach:

1. `_build_knowledge_infra(chat_model: str | Model)` — remove `= "gpt-4o"`
2. `_build_knowledge_toolset(chat_model: str | Model)` — remove `= "gpt-4o"`
3. `_build_bookmark_toolset(chat_model: str | Model)` — remove `= "gpt-4o"`
4. `AgentRegistry.__init__(default_model: str | Model)` — remove `= "gpt-4o"`

**Risk:** Tests that instantiate these directly without passing a model will break. Mitigation: grep for test callsites and add the model arg. This is a feature, not a bug — it forces explicit model resolution.

**Do NOT change:** docstrings (Category B), lookup tables (Category C), or the settings field (Category D).

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Remove redundant gpt-4o defaults from bootstrap sub-functions" --priority nice-to-have --status backlog --tags "config,scope:core" --body "Remove the default '\"gpt-4o\"' from 3 bootstrap helper signatures (_build_knowledge_infra, _build_knowledge_toolset, _build_bookmark_toolset) making chat_model required. Update any direct test callers. See docs/hardcoded-model-defaults-research.md §5. AC: grep 'gpt-4o' in bootstrap.py returns 0 matches outside docstrings."
```

```
kanban\kanban-md.exe create "Remove redundant gpt-4o default from AgentRegistry.__init__" --priority nice-to-have --status backlog --tags "config,scope:core" --body "Remove the default '\"gpt-4o\"' from AgentRegistry.__init__ default_model parameter, making it required. Update test callers to pass model explicitly. See docs/hardcoded-model-defaults-research.md §5. AC: AgentRegistry.__init__ signature has no hardcoded model default."
```
