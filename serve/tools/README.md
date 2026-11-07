# owlbear-tools — Workspace Utilities

Workspace commands for the OwlBear project: quality checks, test routing, dependency
synchronization and repository helpers. `uv run help` lists them.

**Use this guide when:** you need to run or change a workspace command or synchronize local
dependencies.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

```bash
# List the workspace commands
uv run help

# Run the tests that a change affects
uv run test --changed
```

## Configuration

The commands use the repository checkout and do not require environment variables.

### Test selection and limits

`uv run test` runs the full maintained Python suite. `uv run test --changed` selects tests from
the branch's merge-base diff, working changes and untracked files; use `--base REF` to name the baseline.
A Delivery Python source change uses checkout-local testmon data. Its first run records the eligible
package tests; later runs select tests that executed changed code. Tests testmon cannot observe,
importing consumer tests and invariants still run.

Changed checks disable only pytest's aggregate session timer, including with `--coverage` or full-suite
fallback. They can take longer than the ordinary session limit. Individual-test timeouts and all failures
remain enforced; plain full-suite and explicit-path runs keep the limits in the root `pyproject.toml`.
The runner supplies `-o session_timeout=` with an empty value: numeric zero expires after the first test
and is not a disabling value.

Known root tooling configs (pre-commit, EditorConfig, Biome, npm manifests, `.nvmrc`, Markdownlint and
Renovate) and the existing CI workflow filenames run their config-consuming regression modules and
invariants. Their scopes are combined with Python and page changes rather than replacing those scopes.
The exact filename-to-test table is `_CONFIG_TESTS` in `src/owlbear_tools/testing.py`.
Root Python dependency/pytest/workspace configuration (`pyproject.toml`, `uv.lock`, `.python-version`
and `conftest.py`), unknown paths and unrecognised workflow filenames still select the full suite.
The root npm routes apply to this checkout's tooling-only Node package, not arbitrary application packages.

### Dependency environment

Use `uv run dep-sync` to reconcile the checked-out manifests and lockfiles with the local Python and root npm environments, after checking the running Node against `.nvmrc`. Use `uv run dep-status` for a read-only check; it also supports `--verbose` (`-v`) and `--json` (`-j`).

These commands consume the dependency versions already selected in the checkout. Hosted Renovate remains responsible for selecting updates and opening pull requests; synchronization never edits manifests or lockfiles.

### Dependency profile

The dependency commands cover the uv workspace and the repository-root npm package, which holds Biome.
