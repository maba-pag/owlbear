# Fix PydanticAI Deprecation Warnings in Tests

> **Owning task:** #556 — Fix PydanticAI deprecation warnings in tests
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

PydanticAI v0.8.1 (2025-08-29, PR #2711 by @DouweM) deprecated passing bare model names (e.g. `"gpt-4o"`) to `Agent()` without a `provider:` prefix. The test suite emits 77 `DeprecationWarning` instances. How should we eliminate them?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PydanticAI changelog v0.8.1 | <https://ai.pydantic.dev/changelog/> | .95 |
| PydanticAI `infer_model()` source | `.venv/.../pydantic_ai/models/__init__.py:1114-1160` (local) | 1.0 |
| OwlBear codebase — bootstrap flow | `src/owlbear/bootstrap.py`, `src/owlbear/config.py` (local) | 1.0 |
| #551 research — hardcoded defaults | `docs/hardcoded-model-defaults-research.md` (local) | .90 |
| Full test output | `docs/scratch/test-output2.txt` line 449+ (local) | 1.0 |

## 3. Root Cause Analysis

`infer_model()` fires a `DeprecationWarning` when model is a string without `:` that starts with `gpt`, `o1`, `o3`, `claude`, or `gemini`. Short-circuits with no warning when model is a `Model` instance or `"test"`.

### Warning breakdown (77 total, 2 files)

| Category | Count | Source | Mechanism |
|----------|-------|--------|-----------|
| Bare `"gpt-4o"` string | 43 | `test_bootstrap.py` (42), `test_knowledge_query_service_expansion.py` (1) | `build_toolsets()` falls back to `settings.chat_model` (bare string) when `chat_model=None`; `_build_knowledge_toolset()` called without `chat_model` |
| MagicMock object | 34 | `test_bootstrap.py` (17 tests x 2) | `bootstrap()` tests mock `create_copilot_model` to return `MagicMock()` (no `spec=Model`), which propagates to `EntityExtractor` → `Agent()` → `infer_model()` |

### Propagation path for bare string warnings

```
build_toolsets(chat_model=None)
  → chat_model or settings.chat_model    # falls back to "gpt-4o" bare string
  → _build_knowledge_infra(chat_model="gpt-4o")
  → EntityExtractor(model="gpt-4o")
  → Agent("gpt-4o")
  → infer_model("gpt-4o")               # DeprecationWarning
```

### Propagation path for MagicMock warnings

```
bootstrap()
  → create_copilot_model()               # mocked → returns MagicMock()
  → build_toolsets(chat_model=MagicMock)
  → _build_knowledge_infra(chat_model=MagicMock)
  → EntityExtractor(model=MagicMock)
  → Agent(MagicMock)                     # NOT patched in knowledge submodule
  → infer_model(MagicMock)              # DeprecationWarning (MagicMock is not a Model)
```

## 4. Fix Options

| Criterion | A: Test-only (pass `"test"` / `spec=Model`) | B: Remove defaults (#551) + test fix | C: Prefix config (`"openai:gpt-4o"`) | D: Suppress via `filterwarnings` |
|-----------|------|------|------|------|
| Warnings fixed | 77/77 | 77/77 | 43/77 (not MagicMock) | 77/77 (hidden) |
| Source changes | 0 files | 4 signatures | 1 config field | 1 pyproject.toml |
| Test changes | ~20 test sites | ~20 test sites | 0 | 0 |
| Risk | None | Tests that forget model param fail loudly | Breaks `OpenAIChatModel(settings.chat_model)` | Masks real deprecation drift |
| KISS | High | Medium | Low (breaks provider) | Low (hides issues) |
| Couples with #551 | No | Yes | No | No |

### Option A detail (recommended, .85 confidence)

Two targeted test-fixture changes, zero source-code edits:

1. **For bare-string warnings (43):** In `TestBuildToolsets*` and the expansion test, pass `chat_model="test"` (or `MagicMock(spec=Model)`) to `build_toolsets()` / `_build_knowledge_toolset()` calls. Since `"test"` triggers PydanticAI's `TestModel` and these tests mock `Agent` anyway, behavior is unchanged.

2. **For MagicMock warnings (34):** In `TestBootstrap*` classes, change `mock_model = MagicMock()` to `mock_model = MagicMock(spec=Model)`. This makes `isinstance(mock_model, Model)` return `True` so `infer_model()` short-circuits. `model_name` attribute still works via `mock_model.model_name = "test-model"`.

### Option B detail (.75 confidence)

Implement #551's recommendation (remove `"gpt-4o"` defaults from 4 function signatures) AND do Option A's MagicMock fix. Cleaner long-term but couples two tasks. Can be done as a follow-up.

### Option C: rejected

`"openai:gpt-4o"` in `config.py` would break `create_copilot_model()` which passes `settings.chat_model` to `OpenAIChatModel(model_name, provider=provider)` — the OpenAI provider expects a bare model name, not a prefixed one.

### Option D: rejected

Suppressing warnings hides future deprecation drift.

## 5. Recommendation (.85 confidence)

**Option A — test-only fix.** Zero production code changes, minimal diff, fully decoupled from #551. After #551 lands (removing redundant defaults), the test callsites that pass `chat_model="test"` will naturally be the required argument.

## 6. Follow-up Tasks

Task #556 itself covers the implementation. No additional tasks needed — #551 already covers the source-code default removal. The builder should:

1. Change `MagicMock()` → `MagicMock(spec=Model)` in 17 bootstrap integration tests
2. Pass `chat_model="test"` to `build_toolsets()` in ~28 test calls and 1 expansion test call
3. Verify: `uv run pytest tests/ -q --tb=short -W error::DeprecationWarning` passes (zero warnings = zero errors)
