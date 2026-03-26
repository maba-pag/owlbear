# Wire or Remove EscalationHook

> **Owning task:** #484 — Wire or remove EscalationHook
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

EscalationHook (`src/owlbear/core/escalation.py`, ~131 LOC) prompts the user via
a channel with retry/skip/abort options when an ON_ERROR hook fires. It is fully
implemented and tested but never imported or registered in `bootstrap.py`. Flagged
as YAGNI-02 (software-design-audit) and INT-03 (integration-audit). Should it be
wired into bootstrap or deleted?

## 2. Sources Studied

| # | Source | URL/Path | Relevance |
|---|--------|----------|-----------|
| 1 | EscalationHook implementation | `src/owlbear/core/escalation.py` | 1.0 |
| 2 | EscalationHook tests | `tests/test_escalation.py`, `tests/test_error_recovery.py` | 0.9 |
| 3 | Bootstrap hook wiring | `src/owlbear/bootstrap.py` (build_hooks, lines 155-210) | 1.0 |
| 4 | Daemon error recovery | `src/owlbear/daemon.py` (_recover_from_error, lines 213-320) | 1.0 |
| 5 | Agent ON_ERROR emission | `src/owlbear/core/agent.py` (turn, line 144) | 0.9 |
| 6 | Architecture audit ARC-21 | `docs/architecture-audit.md` (lines 225-230) | 1.0 |
| 7 | Software design audit YAGNI-02 | `docs/software-design-audit.md` (lines 222-233) | 1.0 |
| 8 | Integration audit INT-03 | `docs/integration-audit.md` (line 22) | 0.9 |

## 3. Analysis

### Current error flow (without EscalationHook)

1. `agent.turn()` catches exceptions, emits `ON_ERROR` hook, re-raises
2. `run_daemon()` catches re-raised exception, calls `_recover_from_error()`
3. `_recover_from_error()` applies classified strategy: transient (backoff 3x),
   auth (token refresh + retry), permanent (log + notify user)

### What wiring EscalationHook would cause (ARC-21)

If registered on ON_ERROR, the hook fires **inside** `turn()` before re-raise.
Then `_recover_from_error` runs **after** the exception propagates. The user gets
prompted twice per error. Fixing this requires choosing one error authority.

### Trade-off matrix: Wire vs Delete

| Criterion | Wire (.30) | Delete (.85) |
|-----------|-----------|-------------|
| **KISS** | Low — adds second error path alongside _recover_from_error | High — one authority |
| **YAGNI** | Low — no current consumer | High — removes orphan code |
| **ARC-21 conflict** | Must fix dual-prompt first (extra work) | Eliminates the problem |
| **Data shape fit** | Poor — turn() emits {error, prompt}, hook expects {error, tool_name, attempt} | N/A |
| **Recovery sophistication** | Simple retry/skip/abort only | _recover_from_error already does classified recovery with backoff, auth refresh, journaling |
| **Future value** | Marginal — daemon loop is the right place for user prompts | If needed later, build into _recover_from_error directly |
| **Test maintenance** | Keep ~200 lines of tests for orphan code | Remove test burden |
| **Diff size** | Larger (fix ARC-21 + wire + test integration) | Smaller (delete 2 files) |

## 4. Recommendation (.85 confidence)

**Delete EscalationHook and its tests.**

Rationale:

- `_recover_from_error` is the established error authority. It already classifies
  errors, retries transients with backoff, refreshes auth tokens, logs to
  ErrorJournal, and notifies the user. EscalationHook adds nothing it doesn't
  already cover.
- Wiring it in requires solving ARC-21 (dual prompt conflict) and fixing the data
  shape mismatch — effort with no clear ROI.
- If interactive escalation is ever needed (e.g., "retries exhausted, ask user"),
  it should be added as a step inside `_recover_from_error` — not as a separate
  hook that conflicts with the existing flow.

Risk: minimal. The code is unreachable today. No production behavior changes.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Delete EscalationHook and tests" --priority needed --status todo --tags "yagni,cleanup,hooks,scope:core" --body "Delete src/owlbear/core/escalation.py and tests/test_escalation.py. Remove EscalationHook imports from tests/test_error_recovery.py (TestOnErrorEdgeCases class). Remove EscalationHook reference from docs/architecture.md directory listing. Update copilot-instructions.md Safety row to remove EscalationHook mention. AC: (1) escalation.py deleted (2) test_escalation.py deleted (3) test_error_recovery.py EscalationHook tests removed (4) no import errors (5) ruff clean (6) all remaining tests pass. See docs/research/escalation-hook.md."
```

```powershell
kanban\kanban-md.exe create "Add user-prompt step to _recover_from_error after transient exhaustion" --priority nice-to-have --status ideation --tags "error-handling,scope:core,ux" --body "After transient retries are exhausted in _recover_from_error (daemon.py), consider prompting the user via channel for retry/skip/abort instead of just logging and sending an error message. This would give the user control without the dual-handling conflict of EscalationHook. AC: (1) user is prompted after retries exhausted (2) retry restarts the backoff loop (3) skip continues the daemon loop (4) abort triggers graceful shutdown. Low priority — current behavior (log + notify) is acceptable."
```
