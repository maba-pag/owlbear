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

### CI dependency evidence for task checks

Full Linux CI test runs also collect pytest-testmon's native test-to-code block fingerprints, with
`--testmon --testmon-noselect` and the classic coverage tracer. This does not shorten CI, change its
shards or loosen its limits. Each existing test-results artifact includes `dependencies.json` with
the checkout/run/shard identity, tracked input hashes, collected/completed/skipped tests and footprints.
It contains no environment contents or transcripts. Identical-input cache hits create no new map.

Task selection reads complete successful CI maps at ancestors of the explicit integration target,
using read-only `gh` queries and downloads into this checkout's `.owlbear/scratch/dependency-maps/`.
All required shards share a run, attempt and checkout. Historical inputs are checked against Git
objects; current task-reachable test modules, helpers, fixtures, production callers and platform/skipped consumers
supplement those observations. Earlier unrelated test/helper edits do not enter a later task's check.
Explicit and retained consumers remain required; a changed selected test module runs in full.
Footprints are compared with both task-before and current code, so
restoring a mapped version does not erase the task's checked scope. Source-reading, subprocess and
invariant selectors supplied by the task runner remain in the union.
Unobserved changes follow the names read by current callers to their executed function blocks, rather
than selecting every importer through a shared fixture or import-time global block. Missing observations
use named current tests and requested conftest fixtures. Platform branches and recorded skips remain
independent supplements at test-function/node scope, including guarded production callers even when
Linux observed the changed function through another test.
Internally, `test_impact.RequiredScope` separates full task paths and required explicit/invariant/configuration
targets from automatic router candidates, so page, source-reader and child-process candidates narrow
to named consumers. Documentation-only inputs retain the ordinary router's exclusion in mixed tasks;
Markdown test fixtures and package runtime resources remain consumer inputs.
Runtime-resource package fallbacks are candidates, not required whole-package tests; resource-only
tasks also use reader discovery, and each runtime resource must resolve readers independently.
Runtime readers follow owned source references (or direct full-path test references) into current
named/native consumers, not unrelated temporary corpora that merely glob the same filename suffix.
Source-relative paths and literal `importlib.resources.files(...).joinpath(...)` readers match
the exact resource, not an unread sibling with the same filename.
Computed package filenames retain their fixed path prefixes and suffixes. Module constants,
direct assignments and single-return path helpers resolve against the same tracked package roots;
an unrelated unrooted string pattern cannot claim a runtime resource.
Path constructors join every resolved argument, not only the first.
Literal tuple/list filename assignments resolve each named target separately. A declared but unresolved
filename does not become a dynamic wildcard reader. Reader and path-helper local bindings shadow
module bindings in the same resolution.
Helper free names retain their defining scope rather than inheriting the caller's locals.
Computed path wildcards match one path component, not descendant files under a returned directory.
Each helper expansion removes its definition from both active and module-resolution contexts;
recursive helper cycles cannot abort unrelated resource discovery.
Direct path aliases follow local assignments and imports; import-time loaded values retain their named consumers.
Observed runtime readers select their own native footprints, with current/platform supplements;
unobserved readers use named current consumers rather than expanding every unchanged importer.
Page consumers follow served HTML and relative module imports to their real browser
navigation routes, including the root Changes page and shared assets. Unresolved page consumers raise an error.
Required web inputs resolve independently before their selectors are combined; explicit configuration
checks do not acquire a separate file-reader requirement.
Reflective module readers (`getattr`/`hasattr`/`vars`) retain named consumers, including computed attribute names.
Changed test modules remain required and also feed dependency analysis for their imported helpers and fixtures.
Deleted test modules cannot supply observed coverage; unresolved current consumers fail explicitly.
Named browser/HTTP navigation consumers with an indirect, unresolved route remain selected;
destination URL assertions also retain link-driven navigation. Dictionary lookups are not navigation.
Users of source inventories that combine a wildcard with a
filename-suffix filter also remain selected.
Test-data-only changes follow named readers, imported test helpers and fixtures, not a mandatory whole-package fallback.
Module/class autouse fixtures and module-level fixture marks retain their implicitly affected tests within
the correct scope, including fixtures imported from pytest under another name.
Computed data filenames match their constant prefixes/suffixes and retain their reader users.
Automatically selected parametrized consumers run their current function's cases, so a production inventory
change cannot retain a removed case or omit a new one. Literal caller-selected case IDs remain exact.
Literal test-module, directory or pytest-node targets selected by the Planner stay in the bound command and
remain required even when the task has no edited paths. For example,
`uv run test --changed serve/tools/tests/test_todo.py --task-base OLD --target TARGET`
unions that module with the task's affected checks. Positional targets with ordinary `--changed`
still require task context rather than silently replacing branch scope.
Kept tasks also compare their original `OLD..NEW` source versions, even when their bytes were
restored before the current task began. The span's own paths use the same target-import exclusions
as task Git scoping, and the selected consumers execute on the current tree.
Rebuilds freeze retained task-review and current-plan final-review repair spans before clearing task records;
undone repairs and earlier-plan final repairs do not enter those kept checks.
Each rebuild recomputes that scope from current ownership, not older frozen flags inherited by a plan or repair task.
When several tasks are rebuilt, their undone originals are excluded; the last task and its repair witness bind the
earlier tasks' newly completed spans only when those new spans exist.

`owlbear_tools.test_impact.select(root, paths, context, candidates, required_scope)` receives a frozen task context with
the base, integration target, optional candidate map directory and original kept spans.
An explicit map directory supports disposable candidate
proof before merge. It prints **candidate evidence**, not installed acceptance; the default loader
never automatically accepts an unmerged map. Missing, incompatible or unresolved evidence raises
an error instead of bootstrapping the full suite or returning an empty passing check.
Block observations are not line or branch coverage, and Linux maps alone do not prove macOS behavior.
Repair witnesses recognize the root selector and its in-package imports from unchanged source.
A repair that changes this selection machinery cannot prove itself with its altered check alone;
it retains the existing owner hold rather than being applied automatically.

### Dependency environment

Use `uv run dep-sync` to reconcile the checked-out manifests and lockfiles with the local Python and root npm environments, after checking the running Node against `.nvmrc`. Use `uv run dep-status` for a read-only check; it also supports `--verbose` (`-v`) and `--json` (`-j`).

These commands consume the dependency versions already selected in the checkout. Hosted Renovate remains responsible for selecting updates and opening pull requests; synchronization never edits manifests or lockfiles.

### Dependency profile

The dependency commands cover the uv workspace and the repository-root npm package, which holds Biome.
