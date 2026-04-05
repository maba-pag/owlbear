# OwlBearError Base Exception Hierarchy

> **Owning task:** #576 — Establish OwlBearError base exception hierarchy
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear has 3 custom exceptions, each inheriting directly from `Exception` (or `TimeoutError`):

| Exception | Base | Defined in | Caught by |
| --- | --- | --- | --- |
| `BlockedCommandError` | `Exception` | `core/command_guard.py:62` | `tools/hooked.py:118`, `core/errors.py:classify_error` |
| `BlockedURLError` | `Exception` | `tools/browser/safety.py:21` | never caught (propagates) |
| `AskUserTimeoutError` | `TimeoutError` | `tools/ask_user.py:43` | never caught (propagates) |

**Problem:** No common base class. Catching all OwlBear-specific errors requires `except Exception`, which also catches stdlib errors, third-party errors, and bugs. An `OwlBearError` base enables `except OwlBearError` for blanket handling without masking unrelated failures.

**Bonus finding:** `classify_error()` in `core/errors.py` classifies `BlockedCommandError` as PERMANENT but does **not** handle `BlockedURLError` at all — it falls through to the default `PERMANENT` return. Works by accident, but should be explicit.

## 2. Sources Studied

| Source | URL | Relevance |
| --- | --- | --- |
| httpx exceptions | `httpx/_exceptions.py` | `.90` — Deep hierarchy: `HTTPError` base → `RequestError` → `TransportError` → leaf types. Gold standard for Python exception trees. |
| PydanticAI exceptions | `pydantic_ai/exceptions.py` | `.85` — Flat hierarchy: `AgentRunError(RuntimeError)` base with `UsageLimitExceeded`, `UnexpectedModelBehavior` etc. No single root — separate trees for different concerns. |
| Python docs — exception hierarchy | `docs.python.org/3/library/exceptions.html` | `.70` — stdlib pattern: all user exceptions inherit from `Exception`; custom bases are standard practice. |

## 3. Analysis

### Should we have a base class at all?

| Option | Pros | Cons | KISS/YAGNI |
| --- | --- | --- | --- |
| **A. Add `OwlBearError` base** | Blanket catch enabled; `classify_error` can use it; future exceptions auto-included | Small refactor; need to decide `AskUserTimeoutError` MRO | KISS-aligned: 1 class, 3 inheritance changes |
| **B. Keep status quo** | Zero changes | Blanket catch requires `except Exception`; every new custom exception is ad-hoc | YAGNI argument — only 3 exceptions today |
| **C. Full hierarchy with subcategories** | `OwlBearSafetyError`, `OwlBearToolError`, etc. | Over-engineering for 3 leaf classes; violates YAGNI | Not KISS — premature hierarchy |

### `AskUserTimeoutError` MRO decision

`AskUserTimeoutError` currently inherits from `TimeoutError`. Two options:

| Option | MRO | `except TimeoutError` still works? | `except OwlBearError` works? |
| --- | --- | --- | --- |
| `AskUserTimeoutError(OwlBearError, TimeoutError)` | Both bases | Yes | Yes |
| `AskUserTimeoutError(OwlBearError)` only | Drops `TimeoutError` | No — breaking | Yes |

**Recommendation:** Use `(OwlBearError, TimeoutError)` multiple inheritance — preserves backward compatibility for any code catching `TimeoutError`.

### Where to define `OwlBearError`

| Location | Pros | Cons |
| --- | --- | --- |
| `core/errors.py` | Co-located with `classify_error`, `ToolError`, `error_to_user_message` | Already imports from `command_guard.py` — adding base here would create import cycle if `command_guard.py` imports from `errors.py` |
| **`core/exceptions.py` (new)** | Zero-dependency leaf module; all exception files import from it; no cycles | New file |

`core/exceptions.py` is the right location — a tiny leaf module with no imports, so `command_guard.py`, `browser/safety.py`, and `ask_user.py` can all import from it without circular dependencies.

## 4. Recommendation (.90 confidence)

**Option A** — Single `OwlBearError(Exception)` base class in `core/exceptions.py`.

- `BlockedCommandError(OwlBearError)` — in `core/command_guard.py`
- `BlockedURLError(OwlBearError)` — in `tools/browser/safety.py`
- `AskUserTimeoutError(OwlBearError, TimeoutError)` — in `tools/ask_user.py`

**Do NOT** create subcategories (`OwlBearSafetyError`, etc.) — YAGNI with 3 exceptions.

Update `classify_error()` to explicitly check `BlockedURLError` alongside `BlockedCommandError`.

### Risks

| Risk | Mitigation |
| --- | --- |
| Multiple inheritance MRO issues | Python MRO (C3 linearization) handles `(OwlBearError, TimeoutError)` trivially. Both inherit from `Exception`. |
| Tests asserting `issubclass(AskUserTimeoutError, TimeoutError)` | MRO preserves this — test passes unchanged. |
| Import cycles | New leaf module `core/exceptions.py` has zero imports — impossible to create cycles. |

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement OwlBearError base exception hierarchy" --status backlog --priority nice-to-have --tags "resilience,scope:core,phase-13" --body "Create `OwlBearError(Exception)` in `src/owlbear/core/exceptions.py`. Update: (1) `BlockedCommandError(OwlBearError)` in `core/command_guard.py`, (2) `BlockedURLError(OwlBearError)` in `tools/browser/safety.py`, (3) `AskUserTimeoutError(OwlBearError, TimeoutError)` in `tools/ask_user.py`. Add `BlockedURLError` to the PERMANENT tuple in `classify_error()`. Add `OwlBearError` to `_SAFE_MESSAGES` or the scrub fallback. Tests: `issubclass` assertions for all 3, `except OwlBearError` catches each, `AskUserTimeoutError` still caught by `except TimeoutError`. See docs/research/owlbear-error-hierarchy.md. AC:\n- [ ] `OwlBearError(Exception)` defined in `core/exceptions.py`\n- [ ] All 3 custom exceptions inherit from `OwlBearError`\n- [ ] `except OwlBearError` catches all 3\n- [ ] `AskUserTimeoutError` still caught by `except TimeoutError`\n- [ ] `classify_error()` explicitly handles `BlockedURLError`\n- [ ] Tests verify hierarchy with `issubclass` assertions\n- [ ] Ruff clean, all tests pass" --depends-on 576
```
