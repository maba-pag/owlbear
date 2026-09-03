---
name: w-test-curation
description: "Workflow: Review and remove low-value tests from current suites"
user-invocable: false
---

# Test Curation

Review current test suites for low-value coverage and remove only what no longer protects
observable behavior. This is a user-invoked maintenance workflow for existing tests, not a
task-archive or acceptance-criteria lifecycle.

The goal is a smaller, clearer suite without sacrificing regression protection. A test's age,
filename, class name, coverage contribution, or passing status is not enough to remove it.

## Scope And Ownership

The user supplies a package, directory, test file, or changed-commit range. If no scope is
supplied, inspect the active test roots and choose one bounded package or suite for review. Do not
claim that the whole repository was reviewed from a collection run alone.

Operate in the current checkout. Do not edit a managed Delivery worktree or a path with unrelated
uncommitted changes. The test-curator may edit test files and scratch files only; production code,
Delivery authority, generated output, and configuration are outside this workflow.

Normal product work keeps its test changes inside the owning Delivery task. Suite-wide maintenance
is a direct user-requested test operation and does not create a parallel Delivery task for every
deletion.

## Step 1 - Bind The Scope

1. Read the supplied scope and inspect `git status --short`, `git diff`, and `git diff --cached`.
2. Identify the owning package and runner from the nearest manifest and the repository test
  configuration. Use `uv run test-root` when the owning boundary is unclear.
3. Protect pre-existing changes unless the user explicitly included those paths.
4. Record the test roots, toolchain, and exclusions used for this curation pass.

Do not use retired task IDs, acceptance-criteria names, legacy manifests, or archive records to
decide whether a current test is removable.

## Step 2 - Discover Current Tests

Use the configured runner and current repository layout to identify the tests in scope:

- Python: configured pytest roots and package-local `tests/` directories;
- Vitest or Jest: the owning frontend package's configured test files;
- Playwright: the owning package's configured E2E specs.

Use collection output, `git log`, `git diff`, and runner-reported timing when available. These are
discovery evidence only. Do not create a persistent inventory, infer value from file age, or treat
coverage as a quality score.

Candidate signals include:

- a one-time structural or migration assertion whose subject no longer exists;
- duplicate assertions at the same or a more expensive test layer;
- a test for an obsolete interface, route, configuration, or implementation branch;
- assertions that cannot distinguish the claimed behavior from an incorrect implementation;
- a slow or complex test with an equivalent, cheaper test that protects the same observable.

Do not nominate a test solely because it is large, old, task-labelled, named unusually, lightly
covered, or difficult to understand. Read its assertions and the behavior they exercise first.

## Step 3 - Apply Durable Test Admission

For every candidate, write a short decision record answering:

1. What observable behavior, public interface, invariant, or risk does this test protect?
2. Which realistic regression would make it fail?
3. Is that behavior protected elsewhere, and at which test layer?
4. Is a cheaper or clearer test able to provide the same protection?

Use these actions:

| Action | Use when |
| --- | --- |
| `keep` | The test protects unique behavior, a non-obvious edge case, or a real risk boundary. |
| `rewrite lower` | The behavior matters, but a focused public-boundary test can replace a brittle higher-level test. |
| `merge` | Multiple tests protect the same observable and a smaller combined set remains clear. |
| `retire` | The test is structural, tautological, obsolete, or demonstrably duplicated. |

Keep standing negative contracts when reintroducing the forbidden behavior would be a real
regression. Remove negative assertions that only prove a completed one-time deletion.

Do not turn flakiness or slowness into a low-value verdict. A flaky test with valuable behavior is
an unhealthy test, not evidence that the behavior no longer matters. Repair it when it is within
the supplied test scope; otherwise retain it and report the health problem.

## Step 4 - Change The Smallest Set

For `keep`, make no edit. For `rewrite lower` or `merge`, preserve the smallest assertions that
distinguish the named behavior and keep the test in its owning canonical suite. For `retire`:

1. Check imports, fixtures, shared helpers, and test references that would make the candidate a
  maintained dependency.
2. Run the narrowest relevant baseline test command when the candidate is shared or the removal is
  uncertain.
3. Remove the file or selected nodes, or replace them with the clearer lower-level test.
4. Re-run the owning test scope.

A green run after removal proves only that no remaining test depended on the removed file, fixture,
or import. It does not prove that the removed test had no unique behavioral value. The decision to
retire must come from the assertion and coverage comparison, not from a green deletion alone.

If removal breaks collection, fixtures, or a maintained test, restore the change and keep the
candidate. If the candidate contains unique behavior that cannot be expressed safely in the
existing suite, keep it rather than inventing a holding directory.

## Step 5 - Verify The Result

Run the affected tests with the owning runner. Use the repository's maintained commands where they
cover the selected scope:

- Python: `uv run test {paths}` or a focused `uv run pytest` command;
- Cockpit unit tests: `npm test` from `serve/cockpit/web`, or the repository path-aware runner;
- Cockpit E2E tests: `uv run test-e2e {specs}` or the package's maintained E2E script.

Run applicable lint, typecheck, build, or browser checks when the edited test surface requires
them. Run the full maintained suite after a batch that changes shared test helpers, package
boundaries, or multiple test layers. A full-suite pass confirms integration; it does not replace
assertion-level value reasoning.

Also run `git diff --check` and inspect the complete diff. Leave unrelated worktree and index
changes untouched.

## Step 6 - Report And Commit

Return one concise decision table for the selected scope. Include the protected behavior or the
reason no behavior remains, the evidence used, and the action taken.

Commit only when the user explicitly requests it. Follow `r-workspace-governance` for the scoped
commit helper and explicit owned paths. Never stage or commit a broad directory, unrelated work,
or a source-file change from this role.

## Output Template

```markdown
## Test Curation
### Summary
- Scope: {package, directory, file, or commit range}
- Tests reviewed: {files and test nodes}
- Retired: {count}
- Merged or rewritten: {count}
- Retained: {count}
- Health findings: {count, or none}

### Decisions
| Test | Protected behavior or reason | Evidence | Action |
|---|---|---|---|
| path::node | named observable or zero-value reason | assertion and neighboring coverage | keep/merge/rewrite lower/retire |
```

## Known Pitfalls

- Current test placement is authoritative; do not move tests into a permanent candidate folder.
- A task label or historical name is not proof that a current test is disposable.
- A passing test may still be the only regression guard for an important behavior.
- A green post-removal run proves lack of coupling, not lack of value.
- Coverage identifies unexamined code; it does not establish test quality or justify deletion.
- Do not replace a source defect with a test deletion, and do not edit production code to make
  curation pass.

## Companion Skills

| Skill | When | Purpose |
| --- | --- | --- |
| `h-python-conventions` | Python test review or edits | Python test admission and assertion conventions |
| `h-vitest-and-linting` | Frontend or E2E review or edits | Frontend test admission and runner proof |
| `r-workspace-governance` | Explicit commit requested | Owned paths and scoped commit rules |
