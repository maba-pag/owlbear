---
name: task-verification
description: "Workflow: Exit gate verification — AC evidence, confidence scoring, commit integrity"
user-invocable: false
---

# Task Verification

Step-by-step exit gate process (done → archived). See `w-task-verification` for the full auditor workflow.

## Full Suite via Quality-Runner

Unlike the reviewer (who scopes tests), the auditor runs the FULL suite to catch cross-task regressions:

```
agentName: quality-runner
prompt: |
  mode: full
  task_id: {id}
```

Confirm `failed: []` and `clean: true` from the Quality-Runner report.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/ -m "not api" -q --tb=short
uv run ruff check packages/ tests/
```

See `h-pytest-and-linting` for flags and known pitfalls.

## Confidence Scoring

Start at 1.0, deduct per criterion:

| Criterion | Deduction |
|-----------|-----------|
| AC line with no specific evidence | -.02 each |
| Lint violations | -.05 |
| AC quality score ≤ 3 | -.03 |
| Missing reviewer evidence section | -.02 |
| Full-suite test failures in task scope | -.05 |

| Score | Action |
|-------|--------|
| ≥ .95 | Archive |
| < .95 | Reject to backlog |

## Advance

Append audit section to task body via `edit_task` (with `append_body` and `timestamp=True`), then advance via `end_work`.
