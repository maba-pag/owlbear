---
name: w-test-curation
description: "Workflow: Post-archive test lifecycle — promote contract assertions, remove task-scoped tests"
user-invocable: false
---

# Test Curation

Post-archive workflow for the test-curator agent. Processes task-scoped test files (`test_{module}_{task_id}.py`) after a task is archived, promoting contract-level assertions to the module's durable test file (`test_{module}.py`) and removing the transient file.

**Non-blocking:** This workflow never gates the next task dispatch. It runs asynchronously after archival.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body).

Identify the task-scoped test file from the `## Test-Writer Notes` section: `tests/test_{module}_{task_id}.py`.

## Step 1 — Read and Classify Assertions

Read the task-scoped test file. For each `TestFromAC_*` class and its test methods, classify assertions:

### Classification Heuristics

| Classification | Criteria | Examples | Action |
|---------------|----------|----------|--------|
| **Contract-level** | Tests public API surface, documented behavior, AC-derived assertions | Function returns expected type, error raised on invalid input, public method contracts | **Promote** |
| **Implementation-coupled** | Tests internal state, private methods, specific mock configurations, import paths | `_private_method` called N times, specific mock.call_args, internal data structure shape | **Discard** |
| **Ambiguous** | Not clearly contract or implementation | | **Promote** (conservative default) |

**Conservative default:** When in doubt, promote. Missing a durable contract assertion is worse than keeping a borderline one.

### Builder-Discovered Tests

`TestBuilderDiscovered` classes follow the same classification. Promote contract-level, discard implementation-coupled.

## Step 2 — Promote to Module-Level File

For each contract-level assertion:

1. Open or create `tests/test_{module}.py`.
2. Add the assertion to an appropriate test class. Use descriptive class names (not `TestFromAC_` — those are task-scoped naming).
3. Add AC provenance comment: `# From task #{task_id}: AC-{N} — {description}`.
4. Preserve the assertion's intent but adjust imports/fixtures as needed for the module-level context.

**Atomic processing:** Work module-by-module. Each module-batch must leave the full suite green.

## Step 3 — Verify Hard Gates

After promoting assertions for a module:

### Gate 1 — Green Suite

```powershell
uv run pytest tests/ serve/ -n auto -q --tb=short
```

All tests must pass (`failed: []`).

### Gate 2 — Coverage

```powershell
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=90 -q --tb=short
```

Coverage on touched modules must be ≥ 90%.

### Gate Failure — Revert

If either gate fails:

```powershell
git checkout -- tests/test_{module}.py
```

Log the failure in the lifecycle log and skip this module. Do not block — move to the next module.

## Step 4 — Remove Task-Scoped File

After successful promotion and gate verification:

```powershell
git rm tests/test_{module}_{task_id}.py
```

## Step 5 — Lifecycle Log

Append an entry to `.owlbear/scratch/curator-log.jsonl`:

```json
{
  "task_id": 123,
  "module": "bookmark_pipeline",
  "action": "promote",
  "assertions_promoted": 5,
  "assertions_discarded": 3,
  "coverage_before": 88.5,
  "coverage_after": 92.1,
  "timestamp": "2026-04-17T12:00:00Z"
}
```

**Actions:** `promote` (assertions moved to module-level), `discard` (all assertions implementation-coupled, file removed), `skip` (gate failure, no changes).

## Step 6 — Commit and Advance

Commit per `r-project-standards` → Commit Discipline:

```powershell
git add tests/test_{module}.py
git commit -m "test: curate {module} tests from #{task_id} (test-curator)"
```

Advance via `end_work` with curation summary.

## Output Template

```
## Curation
- Task-scoped file: tests/test_{module}_{task_id}.py
- Assertions: {N} promoted, {M} discarded
- Module-level file: tests/test_{module}.py
- Coverage: {X}% → {Y}%
- Suite: green
```
