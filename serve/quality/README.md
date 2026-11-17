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
- `inspect.added(repo, base, head)` compares immutable commits, not the index. Each addition holds its identity,
  excess copy count and all candidate places in head. Identical copies are interchangeable.
- `inspect.protected(repo, base, head, commands=())` returns canonical before/after text, its digest and paths,
  or `None` when no protected configuration changed. Shared manifests are compared as parsed data, including
  the script entries the confirmed commands invoke; dependency-only edits are not protected changes.

The package records no verdicts and grants no approvals. See the [package map](../README.md) for its consumers.
