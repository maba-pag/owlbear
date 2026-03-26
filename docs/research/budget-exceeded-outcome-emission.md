# Budget-Exceeded Outcome Emission from reconcile_tasks

> **Owning task:** #993 — Emit outcome budget_exceeded from reconcile_tasks for BudgetExceededError
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #993 (child of archived #985) requires `reconcile_tasks` in `daemon.py` to
emit `outcome: "budget_exceeded"` instead of `outcome: "failure"` when the
exception is a `BudgetExceededError`. Currently all failures emit `"failure"`
unconditionally (daemon.py line 615). The budget check lives only inside
`schedule_task_retry` (daemon.py line 522), which runs AFTER the hook emission.

Question: Is distinguishing budget-exceeded at the outcome level the right
approach, and will it break existing consumers?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Celery task retry docs | .90 | `dont_autoretry_for` excludes exception types from retry; `Task.throws` marks expected errors [S1] |
| S2 | Temporal failure detection docs | .85 | `ApplicationError(non_retryable=True)` bypasses retry; `non_retryable_error_types` in RetryPolicy [S2] |
| S3 | OwlBear `daemon.py` reconcile_tasks | 1.0 | Lines 602-616: emits `"failure"` for all exceptions before calling schedule_task_retry |
| S4 | OwlBear `daemon.py` schedule_task_retry | 1.0 | Lines 521-523: checks `isinstance(error, BudgetExceededError)` internally |
| S5 | OwlBear `audit_map_hook.py` | 1.0 | Line 65: checks `outcome != "success"` — budget_exceeded skipped correctly |
| S6 | OwlBear `retrospective_hook.py` | 1.0 | Line 186: checks `outcome != "success"` — budget_exceeded skipped correctly |
| S7 | OwlBear `hook_reaction_router.py` | 1.0 | Lines 86-89: match predicates on `outcome: "failure"` naturally exclude `budget_exceeded` |
| S8 | OwlBear docs/research/retry-executor-wiring.md | 1.0 | Section 3.2 recommends this exact approach with .85 confidence |

- [S1] <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying>
- [S2] <https://docs.temporal.io/develop/python/failure-detection>

## 3. Analysis

### 3.1 Approach validation

| Criterion | Outcome-level distinction (.85) | Error-type field (.75) | Post-facto check (.30) |
|-----------|--------------------------------|----------------------|----------------------|
| Consumer compat | Existing `!= "success"` checks work | Requires consumers to learn new field | Broken: hook fires before retry |
| Match predicates | `match: {outcome: failure}` excludes naturally | Must add `error_type` to match logic | N/A |
| KISS | 1 isinstance check + 1 string change | New field in TypedDict + all consumers | Complex timing dependency |
| Retry executor | Needs no special logic | Must check error_type field | Must read state.retries |

### 3.2 Consumer compatibility audit

All TASK_COMPLETE consumers were verified:

| Consumer | Check pattern | budget_exceeded behavior | Status |
|----------|--------------|--------------------------|--------|
| AuditMapHook | `outcome != "success"` returns early | Correctly skipped | SAFE |
| RetrospectiveHook | `outcome != "success"` returns early | Correctly skipped | SAFE |
| HookReactionRouter | `match: {outcome: failure}` equality | Naturally excluded from failure rules | SAFE |
| TestTaskCompleteEmitFailure | Uses `RuntimeError` (not budget) | Unaffected | SAFE |
| TestFromAC_ReconcileFailureSideEffects | Uses `ValueError` (not budget) | Unaffected | SAFE |
| test_lint_fail_emits_task_complete_failure_hook | Uses `LintGateError` (not budget) | Unaffected | SAFE |

No consumer positively matches `outcome == "failure"` to trigger behavior. All
filter on `outcome != "success"` or use match predicates for equality.

### 3.3 Implementation sketch

The change is ~5 lines in `reconcile_tasks`:

```
from owlbear.core.errors import BudgetExceededError  # lazy import
outcome = "budget_exceeded" if isinstance(exc, BudgetExceededError) else "failure"
# Then emit with the computed outcome
```

`TaskCompleteData.outcome` docstring updated to document valid values:
`"success"`, `"failure"`, `"budget_exceeded"`.

### 3.4 Dependency status

- #984 (extract schedule_task_retry): DONE — `schedule_task_retry` exists
- #985 (parent): ARCHIVED via SPLIT into #991, #992, #993
- `depends_on: 985` in task frontmatter is a dangling reference (noted in #985
  architecture review); real dependency is #984 which is satisfied
- #993 is independent of #991 and #992 per architecture review

## 4. Recommendation (.90 confidence)

Emit `outcome: "budget_exceeded"` from `reconcile_tasks`. This is the approach
recommended by the parent research (retry-executor-wiring.md section 3.2) and
confirmed by prior art in Celery and Temporal.

**Risk:** Minimal. All existing consumers use `!= "success"` pattern which
naturally handles the new outcome value. No consumer will break.

**Implementation:** ~5 LOC change in `reconcile_tasks` + TypedDict docstring
update. The task AC is well-defined and ready for TDD split by the architect.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #993 itself IS the actionable follow-up
from the #985 research. It has detailed AC and is ready to advance to `backlog`
for architect review and TDD decomposition.

## 6. Research Checklist

- [x] Theoretical validity: Distinguished outcomes for permanent vs transient
  failures is standard in Celery (dont_autoretry_for), Temporal (non_retryable)
- [x] Prior art: 2+ external sources (Celery S1, Temporal S2) + parent research
- [x] Technical feasibility: ~5 LOC, lazy import already available in same file
- [x] Architecture fit: all consumers verified safe, no interface changes needed
- [x] Implementation approach: isinstance check before emit, TypedDict docstring
- [x] Testing strategy: AC5/AC6 cover the two cases; existing tests unaffected
- [x] Findings documented: this document
