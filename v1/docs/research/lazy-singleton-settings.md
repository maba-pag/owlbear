# Lazy-Singleton OwlBearSettings in cli.py

> **Owning task:** #536 — Lazy-singleton OwlBearSettings in cli.py
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

DRY-05: `OwlBearSettings()` is instantiated 12 times across `src/bearclaw/cli.py`
(lines 108, 185, 223, 362, 519, 660, 778, 794, 851, 963, 1040, 1082). Each call
creates a new pydantic-settings instance that re-reads env vars and validates.
28 test call sites patch `bearclaw.cli.OwlBearSettings` directly.

**Question:** What is the simplest pattern to construct settings once?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | FastAPI Settings docs — `@lru_cache` singleton | <https://fastapi.tiangolo.com/advanced/settings/> | 1.0 |
| 2 | Typer Callback docs — `@app.callback()` | <https://typer.tiangolo.com/tutorial/commands/callback/> | 0.9 |
| 3 | Typer Context docs — `ctx.obj` | <https://typer.tiangolo.com/tutorial/commands/context/> | 0.8 |
| 4 | Python `functools.cache` docs | <https://docs.python.org/3/library/functools.html#functools.cache> | 0.9 |

## 3. Analysis

### 3a. Approach comparison

| Criterion | `@cache` getter (.90) | Typer callback + `ctx.obj` (.55) | Module-level lazy var (.65) |
|-----------|----------------------|----------------------------------|----------------------------|
| LOC added | ~5 (func + decorator) | ~10 (callback + ctx param on all cmds) | ~8 (var + getter + None check) |
| LOC changed | 12 (call-site swap) | 12+ (add ctx param to every cmd) | 12 (call-site swap) |
| Sub-Typer compat | Works everywhere | Requires `ctx.ensure_object()` per sub-Typer; 5 sub-Typers need wiring | Works everywhere |
| Test impact | Patch `get_settings` instead of class; OR keep patching class (it still works since `@cache` wraps the call) | Major — every test must provide context objects | Patch `get_settings` similarly |
| KISS | High — single decorator | Low — framework plumbing across sub-Typers | Medium — manual None guard |
| Precedent | FastAPI official docs (same author as Typer) | Typer docs (simple apps only) | Common Python pattern |
| Cache clearable | `get_settings.cache_clear()` | N/A | Manual `_settings = None` reset |
| Thread-safe | Yes (stdlib) | Yes (Click context) | No (without lock) |

### 3b. Test migration analysis

Current tests do `patch("bearclaw.cli.OwlBearSettings")` (28 sites). With the
`@cache` approach, tests can either:

- **Option A (zero-change):** Keep patching `OwlBearSettings` and call
  `get_settings.cache_clear()` in a fixture so the patched class is used.
- **Option B (gradual):** Patch `bearclaw.cli.get_settings` to return a mock.
  Cleaner but requires updating 28 sites.

Option A is recommended for initial implementation — zero test changes required
if a `cache_clear()` autouse fixture is added.

## 4. Recommendation (.90 confidence)

**`functools.cache` getter function.** Implementation:

```python
@functools.cache
def get_settings() -> OwlBearSettings:
    return OwlBearSettings()
```

Replace all 12 `OwlBearSettings()` call sites with `get_settings()`. Add an
autouse fixture in `conftest.py` that calls `get_settings.cache_clear()` after
each test to prevent cross-test state leakage.

**Rationale:** Smallest diff, no framework coupling, official FastAPI/Typer
ecosystem pattern (same author), trivially testable, thread-safe. The Typer
callback approach would require threading `ctx.obj` through 5 sub-Typer apps
and modifying every command signature — disproportionate complexity for the
benefit. The module-level lazy var is not thread-safe without extra code.

**Risk:** Low. The only risk is forgetting `cache_clear()` in tests, causing
stale settings across tests. Mitigated by the autouse fixture.

**Interaction with #481 (CLI split):** When cli.py is split into subcommand
modules (#481), `get_settings` stays in the main `cli.py` (or moves to a shared
`bearclaw/_settings.py`). All subcommand modules import it. The singleton
pattern makes the split easier, not harder.

## 5. Follow-up Tasks

Task #536 already exists for the implementation. No new tasks needed — the
existing AC ("settings constructed once, all commands use same instance") is
sufficient. Research is complete; move to backlog for architect review.

```
kanban\kanban-md.exe edit 536 --description "DRY-05: OwlBearSettings() instantiated 12 times in cli.py. pydantic-settings re-reads env vars each time.\n\n**Research complete** — see docs/research/lazy-singleton-settings.md\n\n**Approach:** functools.cache getter (.90 confidence). Add @functools.cache on a get_settings() function, replace 12 call sites. Add autouse cache_clear() fixture for tests.\n\n**AC:**\n- [ ] get_settings() function with @functools.cache in cli.py\n- [ ] All 12 OwlBearSettings() calls replaced with get_settings()\n- [ ] Autouse fixture calls get_settings.cache_clear() after each test\n- [ ] All existing CLI tests pass without modification\n- [ ] ruff clean"
```
