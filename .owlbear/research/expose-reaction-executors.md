# Expose reaction_executors via HookRegistry Attribute

> **Owning task:** #991 — Expose reaction_executors dict from build_hooks
> **Parent research:** `docs/research/retry-executor-wiring.md` (task #985)
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context

Task #985 was SPLIT by the architect into #991, #992, #993. This doc validates
the specific approach for #991: storing the executors dict as an attribute on
`HookRegistry` so `run_daemon()` can access it without changing function
signatures.

## 2. Sources

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Flask `app.extensions` | .90 | Central app object stores extension state as a dict attribute [S1] |
| S2 | Celery `app.tasks` | .85 | App object exposes task registry as dict attribute for late binding [S2] |
| S3 | OwlBear `retry-executor-wiring.md` | 1.0 | Parent research, Option C analysis (.85 confidence) [S3] |
| S4 | OwlBear `hooks.py` HookRegistry | 1.0 | Current `__init__` only sets `_handlers` dict [S4] |
| S5 | OwlBear `bootstrap/hooks.py` build_hooks | 1.0 | Creates local executors dict, passes to router, not exposed [S5] |
| S6 | OwlBear `daemon.py` run_daemon | 1.0 | Already accesses `agent.hooks` at 4 locations (L1034, 1040, 1107, 1154) [S6] |
| S7 | OwlBear `hook_reaction_router.py` | 1.0 | Closures capture `_executors` dict by reference [S7] |

- [S1] <https://flask.palletsprojects.com/en/stable/api/#flask.Flask.extensions>
- [S2] <https://docs.celeryq.dev/en/stable/userguide/application.html>

## 3. Analysis

### 3.1 Prior art: registry-attribute pattern

Both Flask and Celery use the same pattern this task proposes:

| Framework | Attribute | Purpose | Set by | Read by |
|-----------|-----------|---------|--------|---------|
| Flask | `app.extensions` | Extension-specific state dict | Extensions at init | Extension code at request time |
| Celery | `app.tasks` | Task name registry dict | `@app.task` decorator / finalize | Workers at dispatch time |
| OwlBear | `hooks.reaction_executors` | Executor dispatch dict | `build_hooks()` at startup | `run_daemon()` at autonomous entry |

All three share: (a) central object owns the dict, (b) factory/decorator sets
it, (c) consumer reads it later via attribute access. The dict is mutable
by-reference, enabling late-binding replacement. [S1, S2, S3]

### 3.2 Technical feasibility

**Verified facts:**

- `run_daemon()` already accesses `agent.hooks` at 4 call sites [S6]
- `HookReactionRouter._make_handler()` closures capture `self._executors` by
  reference; mutating the dict after construction propagates to all handlers [S7]
- `build_hooks()` creates executors locally and passes to router but does not
  expose it externally [S5]
- The change is 2 lines: one in `HookRegistry.__init__`, one in `build_hooks()` [S4, S5]

**No blockers identified.**

### 3.3 Testing strategy

| Test | Assert | File |
|------|--------|------|
| Default None | `HookRegistry().reaction_executors is None` | `test_hooks.py` |
| Set when configured | `build_hooks()` returns registry with `reaction_executors` dict containing 3 keys | `test_bootstrap.py` |
| None when empty | `build_hooks()` with empty `hook_reactions` config sets attr to None or empty | `test_bootstrap.py` |
| 2-tuple preserved | Existing `TestFromAC_955_BuildHooksReturnContract` continues passing | `test_955*.py` |

### 3.4 Stale dependency

Task #991 has `depends_on: [985]` but #985 is archived (SPLIT). The dependency
should be removed during architect review so the task is not blocked.

## 4. Recommendation (.90 confidence)

Proceed with Option C as specified in the parent research doc. The
registry-attribute pattern is well-established (Flask, Celery). Implementation
is minimal (2 LOC), no signature changes, and `run_daemon()` already has the
access path.

**Risks:** Optional attribute coupling HookRegistry to the reaction concept.
**Mitigation:** Defaults to `None`; only the daemon wiring path uses it.

## 5. Follow-up Tasks

Tasks #992 and #993 already exist at `ideation` (created when #985 was split).
No additional follow-up tasks needed.

- **#992** — `make_retry_executor` and wiring into `run_daemon()`
- **#993** — Emit `outcome: budget_exceeded` from `reconcile_tasks`
