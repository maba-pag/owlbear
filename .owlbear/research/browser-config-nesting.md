# Nest BrowserConfig into OwlBearSettings

> **Owning task:** #553 — Nest BrowserConfig into OwlBearSettings
> **Date:** 2026-03-07  **Status:** Complete

## 1. Context and Question

INT-18 from the integration audit: `BrowserConfig` is a standalone frozen `BaseModel`
at `src/owlbear/tools/browser/config.py`. It is always constructed with defaults
(`BrowserConfig()`) — users cannot configure browser behavior via `OWLBEAR_` env vars.

**Question:** Should we nest `BrowserConfig` into `OwlBearSettings` to enable
env-var configuration, or keep it separate with its own prefix?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| pydantic-settings docs — nested models | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#parsing-environment-variable-values> | 1.0 |
| pydantic-settings test suite — `test_nested_env_complex_values` | <https://github.com/pydantic/pydantic-settings/blob/main/tests/test_settings.py> | 0.9 |
| OwlBear codebase — `config.py`, `bootstrap.py`, `tools/browser/config.py` | Local | 1.0 |

## 3. Analysis

### Option comparison

| Criterion | A: Nest into OwlBearSettings (.85) | B: Separate BaseSettings (.40) | C: JSON env var only (.30) |
|-----------|-------------------------------------|--------------------------------|---------------------------|
| Per-field env vars | Yes: `OWLBEAR_BROWSER__CDP_PORT=9223` | Yes: `OWLBEAR_BROWSER_CDP_PORT=9223` | No — must set entire JSON blob |
| Single source of truth | Yes — one settings object | No — two settings objects | Partial |
| Existing pattern fit | Matches `OwlBearSettings` pattern | New pattern to maintain | Already works without changes |
| Breaking changes | None — env vars are new (didn't exist) | None | None |
| frozen preservation | BrowserConfig stays frozen BaseModel | Must drop frozen or add workaround | N/A |
| Complexity | Add 3 lines to model_config + 1 field | New BaseSettings subclass + env prefix mgmt | Zero changes |
| KISS/YAGNI | Simple, standard pydantic-settings idiom | Over-engineered for one nested model | Too limited for individual fields |

### Option A details: `env_nested_delimiter='__'`

pydantic-settings supports nested `BaseModel` fields via `env_nested_delimiter`.
With `OWLBEAR_` prefix and `__` delimiter:

| Env var | Maps to |
|---------|---------|
| `OWLBEAR_BROWSER__HEADLESS=true` | `settings.browser.headless` |
| `OWLBEAR_BROWSER__CDP_PORT=9223` | `settings.browser.cdp_port` |
| `OWLBEAR_BROWSER__CDP_ENDPOINT=http://localhost:9222` | `settings.browser.cdp_endpoint` |
| `OWLBEAR_BROWSER__TIMEOUT_MS=60000` | `settings.browser.timeout_ms` |
| `OWLBEAR_BROWSER__AUTO_LAUNCH=false` | `settings.browser.auto_launch` |
| `OWLBEAR_BROWSER__BROWSER_EXECUTABLE=C:\chrome.exe` | `settings.browser.browser_executable` |
| `OWLBEAR_BROWSER__ALLOWED_URLS=["https://.*"]` | `settings.browser.allowed_urls` |
| `OWLBEAR_BROWSER__BLOCKED_URLS=[".*evil.*"]` | `settings.browser.blocked_urls` |

**Collision risk:** Existing flat fields use single `_` (e.g. `OWLBEAR_COPILOT_TOKEN_PATH`).
The `__` delimiter requires double underscore, so no existing env vars are affected.

**Partial updates:** `nested_model_default_partial_update=True` ensures setting
`OWLBEAR_BROWSER__HEADLESS=true` alone keeps all other BrowserConfig defaults.
Without it, all unset fields would revert to their type defaults (losing custom
defaults like `cdp_port=9222`).

### Current code: 3 independent `BrowserConfig()` constructions

All in `bootstrap.py` — always with defaults:

1. `_build_hooks_and_reporters`: `URLSafetyGuard(config=BrowserConfig())`
2. `_build_web_search_toolset`: `config = BrowserConfig()` for URL lists
3. `build_toolsets`: `BrowserToolset(config=BrowserConfig())`

After nesting, all three use `settings.browser` — single config instance, DRY.

### Risks and mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| `env_nested_delimiter` affects all fields globally | Low | `__` delimiter has zero collision with existing single-`_` field names |
| BrowserConfig `frozen=True` incompatible with settings | None | Nested BaseModel stays frozen — only the parent is BaseSettings |
| `screenshot_mode` already in OwlBearSettings, not in BrowserConfig | Low | Keep where it is — moving it is a separate cleanup task |
| Test changes needed | Low | Tests construct `BrowserConfig()` directly — still works, just also configurable via settings |

## 4. Recommendation (.85 confidence)

**Option A: Nest `BrowserConfig` into `OwlBearSettings`.**

Concrete changes:

1. **`src/owlbear/config.py`** — Add to `model_config`:
   - `env_nested_delimiter='__'`
   - `nested_model_default_partial_update=True`
   - Add field: `browser: BrowserConfig = BrowserConfig()`
   - Add import: `from owlbear.tools.browser.config import BrowserConfig`

2. **`src/owlbear/bootstrap.py`** — Replace 3× `BrowserConfig()` with `settings.browser`:
   - `_build_hooks_and_reporters`: pass `settings.browser` to `URLSafetyGuard`
   - `_build_web_search_toolset`: accept `settings` param, use `settings.browser`
   - `build_toolsets`: `BrowserToolset(config=settings.browser)`

3. **Tests** — Add test verifying `OWLBEAR_BROWSER__CDP_PORT` sets `settings.browser.cdp_port`.

BrowserConfig stays a frozen `BaseModel` at its current location — no structural
change to the browser module itself. The nesting is purely additive.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Nest BrowserConfig into OwlBearSettings" --priority nice-to-have --tags "config,browser,phase-12" --status todo --description "Add env_nested_delimiter='__' and nested_model_default_partial_update=True to OwlBearSettings.model_config. Add browser: BrowserConfig field. Replace 3x BrowserConfig() in bootstrap.py with settings.browser. Add test for OWLBEAR_BROWSER__CDP_PORT. See docs/research/browser-config-nesting.md. AC: (1) OWLBEAR_BROWSER__HEADLESS=true correctly sets settings.browser.headless. (2) All 3 bootstrap BrowserConfig() calls use settings.browser. (3) Existing tests pass. (4) New test for env var override."
```

Note: Task #553 itself becomes this implementation task once moved to backlog.
No separate follow-up task needed — update #553 body with refined AC.
