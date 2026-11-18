# owlbear-quality

Deterministic lint execution and suppression inspection, independent of Delivery's Changes and sessions.
Delivery owns its refusal count, activity logging and submit budget.

## Lint command

`owlbear quality lint [--base REF]` runs in the current checkout without the host. It checks files changed
against the merge-base with `REF`, including staged, working and untracked files. The profile's target branch
is the default. Exit codes: 0 passed, 1 lint problems, 2 a tool could not run.

Confirm the root command once with `owlbear profile --confirm 'lint=COMMAND'`. Each nonblank line is one
command parsed into arguments, with changed files appended. In an OwlBear development checkout use:

```shell
owlbear profile --confirm 'lint=uv run quality --no-fix --files'
```

Only owner-confirmed commands run. Otherwise the existing Ruff, Biome and ESLint discovery applies.

## Python API

- `run.plan(root, files, commands=())` returns planned linters and skipped-tool reasons. Confirmed commands are
  argument vectors, run without a shell from the repository root with repository-relative files appended.
  Without commands it discovers configured Ruff, Biome and ESLint installations.
- `run.run(root, linter, timeout=120)` returns `passed`, `failed` or `broken`, output and a failure reason.
- `inspect.suppressions(run, root, base, path)` preserves repairs' diff-based detection of added directives and
  removed terminators. Its matching intentionally includes whole lines, unlike the inventory.
- `inspect.inventory(root, paths)` returns directive copies with their file, line, text, covered code and identity.
  Python directives must be comment tokens. Identities bind the file, directive rules and covered code, not a
  line number. Unknown statement boundaries bind the whole file.
- `inspect.added(run, repo, base, head)` compares immutable commits, not the index. Each addition holds its identity,
  excess copy count and all candidate places in head. Identical copies are interchangeable.
- `inspect.protected(run, repo, base, head, commands=())` returns canonical before/after text, its digest and paths,
  or `None` when no protected configuration changed. Shared manifests are compared as parsed data, including
  the script entries the confirmed commands invoke; dependency-only edits are not protected changes.

- `inspect.configured(root, commands=())` returns each existing protected lint configuration file or parsed table, its content
  and a digest identity. It reuses the protected-change parser.
- `ledger.add(folder, verdicts)` atomically appends copy verdicts to `exceptions.json` in the caller's folder.
  Each identity holds a list with `verdict`, `reason`, `by`, `for`, `at`, `commit`, `place`, `backlog` and `aside`.
  `by` names the judge and model or the owner; `for` names the caller, including a Change slug.
  `ledger.counting(folder, identity, scope=slug)` counts only active verdicts for that Change; omitting `scope`
  returns every active verdict. `ledger.counting_scope(folder, scope)` returns active verdicts across identities.
  `ledger.set_aside(folder, identity, indexes)` preserves entries as history.
  `ledger.current(folder)` reads all counting verdicts with their history indexes in one snapshot.
  `ledger.published(folder, members, number)` writes the Backlog number to the named history rows after publishing.
  Maintenance's Suppression review counts non-chat verdicts against its pinned inventory and sets verdicts aside
  or replaces refusals with owner acceptances, keeping history. Publication receipts also cover detail comments.
  `.exceptions.lock` serializes writers. A ledger that does not exist is empty, so a lost one costs a new
  judgement; unreadable JSON raises with its path and error. A killed writer leaves the earlier ledger intact.

Delivery grants approvals. See the [package map](../README.md) for its consumers.
