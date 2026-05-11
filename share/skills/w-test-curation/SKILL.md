---
name: w-test-curation
description: "Workflow: Test suite curation — coverage-gap mining, task-test cleanup, module-test improvement"
user-invocable: false
---

# Test Curation

Suite-scoped workflow for the test-curator agent. Scans for task-scoped test files (`test_{module}_{task_id}.py`) with archived tasks, measures module coverage without them, mines assertions that close coverage gaps, and cleans up the rest.

**Non-blocking:** This workflow never gates task dispatch. It runs on demand via prompt.

## Step 0 — Inventory

1. List all `tests/test_*_*.py` files (task-scoped pattern: `test_{module}_{task_id}.py`).
2. For each, extract the task ID and check status via `show_task`. Keep only files whose task is **archived**.
3. Group by module: `{module: [task_id_1, task_id_2, ...]}`.
4. If no archived task-tests exist, report "nothing to curate" and stop.

## Step 1 — Baseline Coverage per Module

For each module in the inventory:

1. Measure coverage using **only** the module-level test file (exclude task-tests):

Resolve the durable test path before invoking Quality-Runner:

- Canonical target: `serve/{package}/tests/test_{module}.py`
- Legacy fallback: `tests/test_{module}.py`
- Package-resolution heuristic: search for `serve/*/tests/test_{module}.py`; if exactly one match exists, use it. If multiple matches exist, choose the package that owns the module under `serve/*/src/` and log the decision. If no canonical match exists, use the root legacy file.

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: test-curation-{module}
  test_paths: ["serve/{package}/tests/test_{module}.py"]  # or ["tests/test_{module}.py"] if only the legacy root file exists
  coverage_modules: ["{module}"]
  lint_paths: ["serve/{package}/tests/test_{module}.py"]
```

2. Record baseline coverage from the Quality-Runner `Coverage` section. If neither canonical nor legacy module-level files exist, baseline is 0%.

## Step 2 — Classify Modules

| Module state | Coverage | Action |
|-------------|----------|--------|
| At or above target (≥ 90%) | Good | **Fast path** — delete all archived task-tests for this module (Step 4) |
| Below target | Gap | **Mine path** — proceed to Step 3 for this module |
| No module-level file (0%) | Missing | **Mine path** — create `serve/{package}/tests/test_{module}.py`, proceed to Step 3 |

## Step 3 — Mine Coverage Gaps

For modules below target:

1. Read the coverage report from Step 1. Identify uncovered lines/branches.
2. Read all archived task-tests for this module.
3. Find assertions in the task-tests that exercise the uncovered paths.
4. Write those assertions into `serve/{package}/tests/test_{module}.py`:
   - Use descriptive class/method names (not `TestFromAC_` — those are task-scoped).
   - Add provenance comment: `# From task #{task_id}: {behavior description}`.
   - Adjust imports/fixtures for the module-level context.
   - Deduplicate against existing assertions in the module file.
5. If no task-test assertions cover the gap, write new tests based on the source code to close it.

**Conservative default:** When unsure whether an assertion covers a gap, include it. Removing a useful test is worse than keeping a borderline one.

### Verify

After writing tests for a module, verify through Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: test-curation-{module}
  test_paths: ["serve/{package}/tests/test_{module}.py"]
  coverage_modules: ["{module}"]
  lint_paths: ["serve/{package}/tests/test_{module}.py"]
```

Gate passes only when tests pass, lint is clean, and the target module coverage is ≥ 90% in the Quality-Runner report.

**Gate failure:** Revert the canonical module file (`git checkout -- serve/{package}/tests/test_{module}.py`), log the failure, move to the next module. Do not block.

## Step 4 — Clean Up Task-Tests

For each module that passed its gate (or was fast-pathed):

```shell
git rm tests/test_{module}_{task_id_1}.py tests/test_{module}_{task_id_2}.py ...
```

Remove all archived task-tests for this module.

## Step 5 — Full Suite Gate

After all modules are processed, run the full suite through Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: full
  task_id: test-curation
```

All tests must pass. If the full suite fails, identify the breaking module and revert it:

```shell
git checkout -- serve/{package}/tests/test_{module}.py
```

Re-add its task-tests and log the failure.

## Step 6 — Lifecycle Log

Append one entry per module to `.owlbear/scratch/curator-log.jsonl`:

```json
{
  "module": "bookmark_pipeline",
  "action": "curate",
  "task_tests_removed": 3,
  "assertions_mined": 5,
  "coverage_before": 72.0,
  "coverage_after": 93.1,
  "fast_path": false,
  "timestamp": "2026-04-17T12:00:00Z"
}
```

**Actions:** `curate` (gaps mined + task-tests removed), `fast_path` (already at target, task-tests removed), `skip` (gate failure, no changes).

## Step 7 — Commit & Advance

**Commit your deliverables** (see `r-pipeline-protocol` → Who Commits What):

```shell
git add {module_test_paths} {removed_task_test_paths} && git commit -m "test: curate module tests — {N} task-tests removed, {M} modules improved (test-curator)"
```

Use exact paths only. Module-level tests may live under `serve/{package}/tests/`, and broad `git add tests/` can miss package-local changes while staging unrelated root tests.

Then return the Channel A signal and Channel B summary. This prompt-run workflow has no kanban lifecycle advance step.

## Output Template

```
## Test Curation
### Summary
- Modules scanned: {N}
- Fast-pathed (already ≥ 90%): {F}
- Gaps mined: {G}
- Skipped (gate failure): {S}
- Task-tests removed: {T}

### Per Module
| Module | Before | After | Task-tests removed | Action |
|--------|--------|-------|--------------------|--------|
| {name} | {X}% | {Y}% | {count} | {curate/fast_path/skip} |
```

## Known Pitfalls

- **Coverage ≠ correctness.** A module at 95% coverage might still lack tests for important edge cases. Coverage is the gate, but read the task-test assertions before discarding — they may test behaviors not visible in line coverage.
- **Shared fixtures.** Task-tests may rely on fixtures defined in `conftest.py` or their own file. When mining assertions, ensure the target module file has access to the same fixtures.
- **Import collisions.** Multiple task-tests for the same module may define identically-named test classes. Dedup when mining.

## Companion Skills

| Skill | When to load | Purpose |
|-------|-------------|---------|
| `h-quality-runner` | Step 1 (coverage measurement), Step 3 (verify), Step 5 (full suite) | Structured test, lint, and coverage execution |
| `h-python-conventions` | Step 3 (writing tests) | Naming, structure, and style for test code |
