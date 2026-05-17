---
name: w-test-curation
description: "Workflow: Test suite curation — coverage-gap mining, task-test cleanup, module-test improvement"
user-invocable: false
---

# Test Curation

Suite-scoped workflow for the test-curator agent. Scans for task-scoped tests with archived tasks, measures durable coverage without them, mines assertions that close coverage gaps, and cleans up the rest.

Supported suites:

| Suite | Task-scoped pattern | Durable target |
|-------|---------------------|----------------|
| Python | `tests/test_{module}_{task_id}.py` | `serve/{package}/tests/test_{module}.py` or legacy `tests/test_{module}.py` |
| Cockpit Vitest | `serve/cockpit/web/src/__tests__/*_{task_id}.test.{ts,tsx}` and `*.{task_id}.test.{ts,tsx}` | Durable frontend tests without task IDs, near the covered component/hook/api module |
| Cockpit Playwright | `serve/cockpit/web/e2e/*[-_]{task_id}.spec.ts` and matching `*.spec.ts-snapshots/` | Stable fast-gate E2E specs or focused durable E2E contracts without archived task IDs |

**Non-blocking:** This workflow never gates task dispatch. It runs on demand via prompt.

## Step 0 — Inventory

1. List task-scoped tests:
   - Python: `tests/test_*_*.py`
   - Cockpit Vitest: `serve/cockpit/web/src/__tests__/*[._-][0-9][0-9][0-9]*.test.ts` and `*.test.tsx`

- Cockpit Playwright: `serve/cockpit/web/e2e/*[-_][0-9][0-9][0-9]*.spec.ts` plus snapshot directories named after archived visual specs

2. For each, extract the task ID and check status via `show_task`. Keep only files whose task is **archived**.

- Protect Playwright/Vitest files for tasks still in backlog, todo, in-progress, review, or docs.
- Also protect archived-looking filenames that active task tests inspect or invoke.

3. Group by suite and durable target: `{suite: {module_or_component: [task_id_1, task_id_2, ...]}}`.
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

### Cockpit Vitest Baseline

For each frontend component/hook/api target in the inventory:

1. Locate durable tests that cover the same target and do **not** include a task ID in the filename.
   - Prefer exact durable names such as `Card.test.tsx`, `Card.signal.test.tsx`, `useBoard.test.ts`, or `tasks.test.ts`.
   - If an active task still inspects an archived task filename, keep that filename protected until the active task is completed.
   - If no durable test exists, mark the target as missing and proceed to Step 3.
2. Run the durable tests from the Cockpit frontend package root:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: test-curation-cockpit-{target}
  test_paths: ["serve/cockpit/web/src/__tests__/{durable-test}.test.tsx"]
  lint_paths: ["serve/cockpit/web/src/__tests__/{durable-test}.test.tsx"]
```

3. Treat passing durable tests as the frontend baseline. Use coverage only when the target has meaningful source-level coverage output; many Cockpit tests are behavioral or CSS/source-contract tests where pass/fail is the useful gate.

## Step 2 — Classify Modules

| Module state | Coverage | Action |
|-------------|----------|--------|
| At or above target (≥ 90%) | Good | **Fast path** — delete all archived task-tests for this module (Step 4) |
| Below target | Gap | **Mine path** — proceed to Step 3 for this module |
| No module-level file (0%) | Missing | **Mine path** — create `serve/{package}/tests/test_{module}.py`, proceed to Step 3 |

For Cockpit Vitest, classify by durable behavioral coverage rather than coverage percentage:

| Target state | Action |
|--------------|--------|
| Durable tests already cover the behavior and pass | **Fast path** — delete archived task-tests |
| Durable tests exist but miss unique assertions | **Mine path** — move the useful assertions into durable tests |
| No durable test exists | **Mine path** — create or extend a durable test near the covered target |
| Task test is an unstable proof artifact with low product value | Delete it after recording rationale; do not preserve bad gates as tech debt |
| Active task depends on a filename | Protect that file until the active task is completed |

For Cockpit Playwright, classify by runtime cost and product value:

| E2E state | Action |
|-----------|--------|
| Stable product smoke/contract behavior | Keep in the fast E2E gate |
| Active task proof | Protect; run scoped with `npm run test:e2e -- e2e/{file}.spec.ts` |
| Archived benchmark, visual snapshot proof, or RED evidence artifact | Delete after recording rationale; do not keep as default CI ballast |
| Archived suite with unique durable behavior | Mine or consolidate into a smaller durable E2E contract, then delete the task-numbered file |
| Archived suite is useful but expensive and not yet mined | Remove it from the default gate and log a follow-up; do not let it block sync or routine agent checks |

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

For Cockpit Vitest targets:

1. Read the archived task-numbered tests and the durable target tests.
2. Mine only assertions that protect product behavior, public contracts, accessibility, API payloads, or stable source contracts.
3. Drop assertions that only prove a temporary pipeline artifact, brittle DOM budgets, generated compiler details, or a one-off implementation detour.
4. Move useful assertions into durable tests with descriptive names and no `TestFromAC_` class/describe naming.
5. Run from `serve/cockpit/web/`; never run frontend Vitest from the repo root.

For Cockpit Playwright targets:

1. Read archived task-numbered specs and identify whether they are product contracts, visual snapshots, benchmark thresholds, or RED evidence.
2. Preserve only durable browser-level behavior that cannot be covered well by Vitest.
3. Prefer a small fast gate over a broad full sweep. The default command is `npm run test:e2e`; intentional full sweeps use `npm run test:e2e:all`.
4. Delete snapshot directories when their owning visual spec is deleted.
5. Keep active task specs runnable by path; do not rename them while their board tasks are active.

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

**Rollback safety:** Before editing a module-level file, record whether it was clean, dirty, or untracked. If it was already dirty or untracked, save a baseline copy under `.owlbear/scratch/test-curation-{module}.baseline` before modifying it. On failure, restore only the curator-created changes; never discard pre-existing edits.

**Gate failure:** Restore the module file to its recorded baseline, log the failure, move to the next module. Do not block. If the curator-created changes cannot be isolated from pre-existing edits, leave the file untouched, keep the task-tests, and log the module as `skip` with a manual follow-up note.

## Step 4 — Clean Up Task-Tests

For each module that passed its gate (or was fast-pathed):

```shell
git rm tests/test_{module}_{task_id_1}.py tests/test_{module}_{task_id_2}.py ...
git rm serve/cockpit/web/src/__tests__/{frontend-task-test}_{task_id}.test.tsx
git rm serve/cockpit/web/e2e/{playwright-task-test}-{task_id}.spec.ts
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

All tests must pass. If the full suite fails, identify the breaking module and apply the same rollback safety contract: restore only curator-created module-file changes, re-add only task-tests removed during this curation pass, and log the failure.

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
- **Active frontend tasks.** Do not rename or delete numbered Vitest tests for tasks still in backlog, todo, in-progress, review, or docs. Some active task-tests inspect other filenames; protect those dependencies until the active task is archived.

## Companion Skills

| Skill | When to load | Purpose |
|-------|-------------|---------|
| `h-quality-runner` | Step 1 (coverage measurement), Step 3 (verify), Step 5 (full suite) | Structured test, lint, and coverage execution |
| `h-python-conventions` | Step 3 (writing tests) | Naming, structure, and style for test code |
| `h-vitest-and-linting` | Cockpit Vitest or Playwright curation | Frontend cwd, Vitest, ESLint, Playwright, and coverage commands |
