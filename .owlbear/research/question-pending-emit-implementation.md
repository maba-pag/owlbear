# QUESTION_PENDING Emit Implementation Plan

> **Owning task:** #967 — Emit QUESTION_PENDING from AskUserToolset and ApprovalGateToolset
> **Date:** 2026-03-23 **Status:** Complete

## 1. Context and Question

Task #967 requires `AskUserToolset` and `ApprovalGateToolset` to emit
`HookEvent.QUESTION_PENDING` immediately before awaiting human input. The
parent research (#962, `docs/research/question-pending-default-hook-surface.md`)
identified these two toolsets as the correct human-wait seams. This doc
validates the implementation approach, payload design, and testing strategy.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Celery signals guide | .85 | `before_task_publish` / `task_prerun` emit once per lifecycle boundary, not on retry [S1] |
| S2 | Prefect event-driven docs | .80 | Events fire at state transitions (Paused, Pending) not on every poll or retry [S2] |
| S3 | OwlBear `src/owlbear/core/hooks.py` | 1.0 | Existing TypedDict payloads, HookEvent enum, emit overloads, `emit_pre_tool_use` helper [S3] |
| S4 | OwlBear `src/owlbear/tools/ask_user.py` | 1.0 | No `hooks` param; 3 receive sites (`_receive_with_timeout`, `_receive_option` loop) [S4] |
| S5 | OwlBear `src/owlbear/safety/gate.py` | 1.0 | Already has `hooks: HookRegistry`; single `channel.receive()` site at L112 [S5] |
| S6 | OwlBear `src/owlbear/bootstrap/toolsets.py` | 1.0 | `AskUserToolset(channel)` at L305 — no hooks wired [S6] |
| S7 | OwlBear `docs/research/typed-hook-payloads.md` | .90 | Lists QUESTION_PENDING as "not yet emitted, TBD" payload [S7] |

## 3. Analysis

### 3.1 Emit location options

| Option | Description | Emits per question | Verdict |
|--------|-------------|--------------------|---------|
| A: Before every `channel.receive()` | Emit in `_receive_with_timeout`, `_receive_option` loop | 1–N (re-asks counted) | Noisy; prior art fires once per boundary [S1, S2] |
| B: Once in `ask_user()` / `call_tool()` | Emit once before any receive | 1 | Matches PRE_ pattern; KISS [S1, S2, S3] |
| C: Helper function like `emit_pre_tool_use` | New `emit_question_pending()` module-level helper | 1 | Over-engineered for 2 call sites; YAGNI [S3] |

### 3.2 Hook injection for AskUserToolset

| Option | Change | Pros | Cons |
|--------|--------|------|------|
| Add `hooks: HookRegistry \| None = None` to `__init__` | ~3 LOC in ask_user.py, ~1 LOC in bootstrap | Minimal, optional, backward-compatible [S4, S6] | None significant |
| Pass hooks via method arg | Clutters public `ask_user()` signature | — | Breaks API; AskUserToolset is a FunctionToolset [S4] |

### 3.3 QuestionPendingData payload design

Follow existing TypedDict conventions from `hooks.py` [S3, S7]:

```python
class QuestionPendingData(TypedDict):
    source: str  # "ask_user" or "approval_gate"
    question: str  # prompt text sent to the user
    tool_name: NotRequired[str]  # approval gate: tool being gated
```

Rationale: `source` differentiates the two emitters; `question` gives the
prompt for notification/observability; `tool_name` is relevant only for
approval gate context. [S3, S5, S7]

### 3.4 Files requiring changes

| File | Change | LOC estimate |
|------|--------|:------------:|
| `src/owlbear/core/hooks.py` | Add `QuestionPendingData`, add emit overload, export | ~15 |
| `src/owlbear/tools/ask_user.py` | Add `hooks` param, emit in `ask_user()` | ~8 |
| `src/owlbear/safety/gate.py` | Emit before `channel.receive()` in `call_tool()` | ~5 |
| `src/owlbear/bootstrap/toolsets.py` | Pass `hooks` to `AskUserToolset` | ~1 |
| `docs/research/typed-hook-payloads.md` | Update TBD row | ~1 |

### 3.5 notification_events default

The AC explicitly states "without reintroducing dead defaults." The default
remains `["task_complete", "on_error"]`. Users can opt in to `question_pending`
via explicit config. A potential follow-up could propose restoring the default
now that the event is live. [S3, S6]

## 4. Recommendation (.90 confidence)

**Option B** — emit once in `ask_user()` and `call_tool()` before the first
receive boundary:

- Add optional `hooks: HookRegistry | None = None` to `AskUserToolset.__init__`
- Add `QuestionPendingData` TypedDict and emit overload to `hooks.py`
- Emit `QUESTION_PENDING` in `ask_user()` before branching to receive
- Emit `QUESTION_PENDING` in `ApprovalGateToolset.call_tool()` before `channel.receive()`
- Wire hooks in `build_toolsets` bootstrap
- Do NOT change `notification_events` default

**Risk**: Low. Changes are additive (new emit calls, new TypedDict). Existing
tests remain valid. Hook emit is fire-and-forget with exceptions swallowed.

## 5. Follow-up Tasks

Task #967 is already the implementation task. No additional follow-up tasks
needed — the AC is concrete and implementable.

Optional future task (not blocking): restore `question_pending` to
`notification_events` default now that it is live.
