---
name: w-test-curation
description: "Workflow: Remove low-value transient proof tests and preserve durable regressions"
user-invocable: false
---

# Test Curation

Remove transient proof tests that no longer provide project value. Mine useful assertions into durable tests before deleting. The goal is not to reduce test count — it is to stop spending compute on tests whose only purpose was proving one completed change.

**Non-blocking:** Runs on demand via prompt. Never gates Delivery. Coverage may help locate
unexamined code, but it never justifies keeping or adding a test.

## Goal

A transient proof test has **no ongoing value** when:

- Its immutable legacy provenance is complete and the test only proved one change's acceptance
- The test verifies something was *removed* — once removed, the test is tautological
- The test verifies a configuration was *added* — and the configuration is now exercised by product tests
- The test exercises code paths already covered by durable module or integration tests
- The test is a proof-of-concept, benchmark, or visual snapshot tied to a completed investigation

A transient proof test **still has value** when:

- It exercises a code path no other test covers (regression guard)
- It documents an edge case or boundary condition that is hard to re-derive
- It protects against a bug that was actually hit (not hypothetical)

## Discovery

Scan **all** directories listed in `testpaths` (from `pyproject.toml` or equivalent config) plus any package-local test directories (`serve/*/tests/`, `packages/*/tests/`, etc.). Legacy transient tests may use a numeric work identifier in the filename or module header.

### Inventory command

From the repository root, run the read-only inventory before making curation decisions:

```shell
uv run test-curation-inventory --json
```

The inventory reports each candidate's path, discovery signal, task ID, and immutable provenance:

- `verified`: a matching archived or completed manifest record exists and its SHA-256 matches;
- `unverified`: a matching record exists but the preserved bytes do not match;
- `missing`: no matching immutable record was found.

Only `verified` candidates are eligible for deletion or node removal. Protect `unverified` and
`missing` candidates and report them as `skip` until provenance is repaired. The inventory treats
`Mined from #...` as provenance on a durable test, not as a new task-ownership signal.

### Finding transient tests

1. **Python:** Find files matching `test_*_[0-9]*.py` recursively in all test directories. New transient suites must use `test_{behavior}_{task_id}.py`; durable suites use behavior names without task IDs.
2. **Vitest/Jest:** Find files matching `*[._-][0-9][0-9][0-9]*.test.{ts,tsx}` in the frontend test directories.
3. **Playwright:** Find files matching `*[-_][0-9][0-9][0-9]*.spec.ts` in E2E directories.
4. **Legacy Python:** Inspect only each file's module docstring and header comments before the first import for explicit task ownership, such as `RED-phase tests for #1517` or `Task 1517 proof`. Treat the referenced numeric ID as a candidate even when the filename has no ID. For example, this rule discovers `tests/test_engine_ac.py` as a candidate for task 1517.

Adapt filename patterns to the project's naming convention, but preserve the requirement for an
unambiguous numeric task ID. A `TestFromAC_*` class or function name is not task provenance: it may
describe durable behavioral coverage and must never make a file a curation candidate by itself.

### Filtering

1. Start from the inventory output. Record each candidate's path, signal (`filename` or `header`), task ID, and provenance status.
2. Read only the hash-verified immutable legacy snapshot under `.owlbear/legacy/`; require the manifest and preserved record to identify the work as archived or completed.
3. Protect candidates with missing, unverifiable, or nonterminal provenance.
4. Protect files imported or referenced by another maintained test.
5. Treat discovery as a triage input, never a deletion decision; inspect candidate assertions under the Rent Test before mining or deletion.

If no immutable legacy-proof candidates exist across any suite, report "nothing to curate" and stop.

## Triage

For each candidate, answer one question: **does this test provide ongoing project value?**

### Zero-value patterns (delete without mining)

| Pattern | Example | Reasoning |
|---------|---------|-----------|
| Removal proof | Test asserts an old import raises or a deleted file is gone | The thing is gone; the test is tautological |
| Config addition proof | Test asserts a config key exists in a manifest | Config is exercised by the system it configures |
| Structural assertion | Test asserts a file exists or a module exports a name | The code that imports it is the real test |
| Duplicate coverage | Same assertions already exist in durable module tests | Redundant compute |
| Pipeline artifact proof | Test asserts compiler output, DOM budgets, or generated internals | Brittle to implementation details, not product behavior |
| RED-phase scaffolding | Test was written before implementation and never evolved beyond AC parroting | No unique assertions beyond what the implementation naturally tests |

### Negative assertions

Distinguish one-time migration proof from a standing negative contract. Delete an assertion that
only proves a completed implementation was removed, such as an obsolete helper or old file. Keep
an assertion when it protects a rule that must remain true, such as forbidden dependency imports,
excluded HTTP routes, security boundaries, or authority isolation. A negative assertion earns rent
when reintroducing the forbidden behavior would be a real regression.

### Potential-value patterns (read before deciding)

| Pattern | Action |
|---------|--------|
| Tests a non-obvious edge case | Mine into durable test |
| Tests error handling / boundary validation | Mine into durable test |
| Tests integration between two modules | Mine if not covered elsewhere |
| Tests a bug fix (regression guard) | Mine — these are high-value |

**Decision rule:** Uncertainty alone is not evidence of value. Inspect the public behavior and nearby
durable coverage; if no plausible ongoing regression can be named, delete the test. Use `skip` only
when concrete missing context prevents a responsible decision.

### Mixed-file verdicts

Not every transient suite is a whole file. Record one of these explicit actions per candidate:

- `delete file`: every test is zero-value proof;
- `remove nodes`: delete only zero-value tests from a mixed module;
- `mine in place`: retain a meaningful guard in the same durable module with a descriptive name;
- `keep`: the candidate is a durable regression or standing contract;
- `skip`: provenance, fixture context, or ownership is unavailable.

## Mining

When a task-test has assertions worth preserving:

### Python

1. Identify the durable test target — the module-level or package-level test file covering the same source module. If none exists, create one.
2. Move assertions in with descriptive names (not `TestFromAC_*`).
3. Preserve only the smallest assertion set that distinguishes the named regression.
4. Add provenance: `# Mined from #{task_id}: {behavior}`.
5. Adjust imports/fixtures for the durable context.

The `Mined from` marker records history only; it must not make the durable file a future candidate.

### Frontend (Vitest/Jest)

1. Identify the durable test covering the same component, hook, or API module.
2. Move assertions that protect product behavior, public contracts, or API payloads.
3. Drop assertions about compiler output, DOM budgets, or implementation details.
4. Run from the frontend package root — never from the repo root.

### E2E (Playwright)

1. Keep only durable browser-level contracts that unit tests cannot cover.
2. Prefer a small fast gate over comprehensive sweeps.
3. Delete snapshot directories alongside their spec files.

## Verify & Delete

After mining (or for zero-value tests, directly):

1. **Run affected tests** to confirm nothing breaks. Run the relevant command directly (pytest for Python, vitest/jest for frontend, playwright for E2E).
2. **Run applicable static gates** for touched surfaces: `git diff --check`, focused Ruff or the
 configured Python lint, and for Cockpit frontend changes `uv run typecheck-cockpit`, the package
 build, and the configured frontend lint. These prove file and type contracts that unit tests do
 not cover.
3. **Delete or edit** according to the mixed-file verdict. Do not delete a whole module when only
 selected nodes are transient.
4. **Rollback** on failure: if durable tests or static gates break after mining, restore the durable
 edit and keep the task-test. Log as `skip`.

## Full Suite Gate

After all deletions or node removals, run the full configured suite. If failures appear, identify
which decision caused the break, restore that task-test or durable edit, and log it. Re-run
`git diff --check` after any formatter or repair.

## Commit

Commit only when the user explicitly requests a commit. Never use `git add -A`, `git commit -a`,
or a broad directory path. Inspect the complete diff and commit only the owned paths with the
repository helper:

```shell
uv --project {owlbear-root} run commit-owned \
  -m "test: curate {N} task-tests — {D} deleted, {M} mined (test-curator)" \
  -- {owned_path_1} {owned_path_2}
```

Verify the resulting commit's path list and leave unrelated staged or unstaged work untouched.

## Output

```
## Test Curation
### Summary
- Candidates found: {modules} modules / {nodes} test nodes (Python: {py}, Frontend: {fe}, E2E: {e2e})
- Removed zero-value nodes: {D}
- Durable guards mined or retained from candidates: {G}
- Pre-existing durable tests untouched: {U}
- Skipped (protected/uncertain): {S}

For Channel A, `G` means candidate assertions deliberately preserved or mined, not every test
currently collected in a touched module.

### Decisions
| File | Legacy provenance | Nodes reviewed | Verdict | Protected behavior / reason |
|------|-------------------|----------------|---------|-----------------------------|
| test_core_removal_1234.py | #1234 (verified archived) | 3 | delete file | removal proof; no ongoing behavior |
| test_engine_edge_1200.py | #1200 (verified archived) | 4 | mine in place | malformed input remains atomic |
| Shell.tab-routing_1639.test.tsx | #1639 (verified archived) | 2 | keep | standing route contract |
```

## Known Pitfalls

- **Package-local tests.** Task-tests in package test directories mine into the same directory's durable files, not into a different location.
- **Shared fixtures.** Task-tests may use fixtures from their local `conftest.py` or setup file. Verify fixture availability in the durable target.
- **Maintained dependencies.** Protect any candidate imported or referenced by another maintained test.
- **Coverage ≠ value.** A module at 95% coverage may still benefit from a mined edge-case test. Read the assertions before deleting.

## Companion Skills

| Skill | When | Purpose |
|-------|------|---------|
| `h-python-conventions` | Mining Python assertions | Naming and structure |
| `h-vitest-and-linting` | Frontend/E2E curation | Frontend tooling commands |
