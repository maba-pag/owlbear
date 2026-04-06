---
name: code-review
description: "Workflow: Code review — evidence-based verification of implementation quality"
user-invocable: false
---

# Code Review

Evidence-based review of a completed implementation task. Run tests, lint, read code, verify AC, and produce a verdict. See `w-code-review` for the full reviewer workflow.

## Quality-Runner Invocation

### Default: Parallel Fan-Out

Dispatch quality-runner and code-reader in parallel for steps 3–5 (tests, lint, coverage) and steps 6–7 (code analysis, AC compliance):

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  coverage_modules: ["{module}"]
  lint_paths: ["serve/{package}/src/", "tests/test_{module}.py"]
```

### Lint Only

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: []
  lint_paths: ["serve/{package}/src/", "tests/test_{module}.py"]
```

### Coverage Only

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  coverage_modules: ["{module}"]
  lint_paths: []
```

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails:

```
end_work(outcome="block", block_reason="Quality-Runner unavailable — cannot run tests, lint, or coverage independently")
```

## Verdict

- **PASS** — All AC verified, tests pass, lint clean, coverage ≥ 90%, no security issues.
- **FAIL** — Any AC gap, test failure, lint error, security finding, or coverage below threshold.

Return Channel A signal with verdict and evidence summary.
