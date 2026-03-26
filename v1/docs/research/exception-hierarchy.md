# OwlBearError Base Exception Hierarchy

> **Owning task:** #539 — Establish OwlBearError base exception hierarchy
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

The codebase has 3 custom exceptions with no shared base class:

| Exception | Base | Location |
|-----------|------|----------|
| `BlockedCommandError` | `Exception` | `src/owlbear/core/command_guard.py:62` |
| `BlockedURLError` | `Exception` | `src/owlbear/tools/browser/safety.py:21` |
| `AskUserTimeoutError` | `TimeoutError` | `src/owlbear/tools/ask_user.py:43` |

**Problem:** 20+ `except Exception` catches (many with `# noqa: BLE001`) across `bootstrap.py`, `daemon.py`, `cli.py`. No way to catch "all OwlBear errors" without catching third-party errors. This weakens error isolation and makes ruff's BLE001 rule unenforceable.

**Question:** What hierarchy should we establish? How deep? How to handle `AskUserTimeoutError`'s `TimeoutError` heritage?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | httpx exceptions | <https://github.com/encode/httpx/blob/master/httpx/_exceptions.py> | .90 — Single root `HTTPError(Exception)` → deep tree. Canonical Python library hierarchy. |
| 2 | requests exceptions | <https://github.com/psf/requests/blob/main/src/requests/exceptions.py> | .85 — Single root `RequestException(IOError)`. Uses MI for cross-cutting: `ConnectTimeout(ConnectionError, Timeout)`. |
| 3 | Click exceptions | <https://github.com/pallets/click/blob/main/src/click/exceptions.py> | .80 — `ClickException(Exception)` root. `Abort(RuntimeError)` intentionally outside hierarchy. |
| 4 | Django exceptions | <https://github.com/django/django/blob/main/django/core/exceptions.py> | .60 — No single root. Flat, historical. Anti-pattern for new projects. |

## 3. Analysis

### 3.1 Root base class pattern

All 3 libraries with modern design (httpx, requests, Click) use a single root exception. Django is the outlier — and its flat approach is widely cited as a pain point.

**Consensus (.95):** Create `OwlBearError(Exception)` as the root.

### 3.2 Handling AskUserTimeoutError's TimeoutError base

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A: MI** | `AskUserTimeoutError(OwlBearError, TimeoutError)` | `except OwlBearError` catches all 3; `except TimeoutError` still works | MI adds mild complexity |
| **B: Outside** | Leave `AskUserTimeoutError(TimeoutError)` as-is | No MI; simple | `except OwlBearError` misses it; base class loses value |

requests uses MI extensively (`ConnectTimeout(ConnectionError, Timeout)`). httpx does the same. Pattern is well-established and idiomatic for this exact situation.

**Recommendation (.85):** Option A — use MI. The whole point of the base class is blanket catching.

### 3.3 Hierarchy depth

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Flat** | All 3 directly under `OwlBearError` | KISS; minimal change | No grouping for safety errors |
| **One intermediate** | `SafetyError(OwlBearError)` → `BlockedCommandError`, `BlockedURLError` | Enables `except SafetyError` | YAGNI — only 2 exceptions, no current catch-as-group need |

**Recommendation (.90):** Flat. We have 3 exceptions. Adding a `SafetyError` group is YAGNI — revisit when we have 5+ safety-related exceptions.

### 3.4 Proposed hierarchy

```
Exception
└── OwlBearError
    ├── BlockedCommandError
    ├── BlockedURLError
    └── AskUserTimeoutError  (also inherits TimeoutError via MI)
```

### 3.5 Impact on existing code

| Component | Current | After | Breaking? |
|-----------|---------|-------|-----------|
| `classify_error()` | `isinstance(exc, BlockedCommandError)` → PERMANENT | Same — isinstance still matches | No |
| `hooked.py` | `except BlockedCommandError` | Same — catches subclass | No |
| `except TimeoutError` catches | Catches `AskUserTimeoutError` | Still catches — MI preserves it | No |
| `except Exception` catches | Catches everything | Still works; can optionally narrow to `except OwlBearError` | No |
| ruff BLE001 | 20+ `# noqa: BLE001` suppressions | Some can be replaced with `except OwlBearError` | No |

**Zero breaking changes.** All existing `isinstance` and `except` patterns continue to work.

### 3.6 Placement

`OwlBearError` belongs in `src/owlbear/core/errors.py` — the existing error module. The 3 child exceptions keep their current file locations but change their base class via import.

## 4. Recommendation (.90 confidence)

1. Add `class OwlBearError(Exception)` to `src/owlbear/core/errors.py`
2. Re-parent `BlockedCommandError(Exception)` → `BlockedCommandError(OwlBearError)`
3. Re-parent `BlockedURLError(Exception)` → `BlockedURLError(OwlBearError)`
4. Re-parent `AskUserTimeoutError(TimeoutError)` → `AskUserTimeoutError(OwlBearError, TimeoutError)`
5. Export `OwlBearError` from `src/owlbear/core/__init__.py`

**Risk:** Multiple inheritance for `AskUserTimeoutError` — mitigated by established precedent in requests/httpx and simple single-level MI (no diamond problem).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add OwlBearError base class to core.errors" --status backlog --priority nice-to-have --tags "audit,resilience,scope:core" --body "Add class OwlBearError(Exception) to src/owlbear/core/errors.py. Re-parent BlockedCommandError(OwlBearError), BlockedURLError(OwlBearError), AskUserTimeoutError(OwlBearError, TimeoutError). Export from core/__init__.py. See docs/research/exception-hierarchy.md. AC: (1) OwlBearError exists in core.errors (2) all 3 custom exceptions inherit from it (3) except OwlBearError catches all 3 (4) except TimeoutError still catches AskUserTimeoutError (5) all tests pass (6) ruff clean."

kanban\kanban-md.exe create "Narrow except-Exception catches to except OwlBearError where appropriate" --status backlog --priority nice-to-have --tags "audit,resilience,scope:core" --depends-on TBD --body "Audit 20+ except Exception catches in bootstrap.py, daemon.py, cli.py. Replace with except OwlBearError where the intent is to catch OwlBear-specific failures (not third-party/stdlib). Remove noqa: BLE001 suppressions where narrowed. See docs/research/exception-hierarchy.md. AC: (1) BLE001 suppressions reduced (2) no regression in error handling (3) all tests pass."
```
