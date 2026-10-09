# Delivery N01 — Behavior-Preserving Split of the Large Delivery Modules

> **Package:** N01 of the [execution plan](delivery-redesign-execution-plan.md#n01--behavior-preserving-split-of-the-large-delivery-modules).
> **Planned on:** `origin/dev` `1acba53c5` (D03 merged; Python 3.14.8; uv 0.12.22).
> **Status:** approved: plan gate `plan-sound` in round 3 of fresh GPT-6.1 Sol challenges (2026-10-03).
> Package complete with N01-C (#347): N01-A #344, N01-B #346.

## 1. Contract

### 1.1 Result

`portfolio_application.py`, `change_workspace.py` and `delivery_runtime.py` become thin facades over
cohesive internal modules, each about 2,500 lines or less. The split is a pure move: behavior,
persisted bytes, MCP/HTTP/Cockpit contracts and test assertions stay identical.
`delivery_application_loader.py` is not split (D8).

| Module at `1acba53c5` | Lines | Largest class |
| --- | ---: | --- |
| `portfolio_application.py` | 11,875 | `PortfolioApplication`, 9,753 lines, 327 methods |
| `change_workspace.py` | 9,455 | `ChangeWorkspaceManager`, 6,288 lines, 213 methods |
| `delivery_runtime.py` | 6,847 | `DeliveryRuntime`, 3,907 lines, 145 methods |
| `delivery_application_loader.py` | 2,463 | module functions only |

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | `owlbear_delivery.__all__` is identical | Execution plan §5 N01 |
| R2 | Every `PortfolioApplication` public method and signature is unchanged; N01 extends this to every member (public and private) of the four split classes | §5 N01 |
| R3 | MCP, HTTP and Cockpit sources are untouched; their schemas are byte-identical | §5 N01 |
| R4 | No test assertion changes; only import lines and patch targets move with the code | §5 N01 |
| R5 | No new import cycle; every Delivery module imports in a fresh interpreter | §5 N01 equivalence protocol |
| R6 | Collected node IDs identical (plus only the new structure-test IDs); per-test outcomes identical in the Delivery, MCP, tools, Cockpit and workspace suites | §5 N01 equivalence protocol |
| R7 | The diff is moved blocks plus import edits plus the declared edit classes in [3.2](#32-allowed-edits) | §5 N01 equivalence protocol |
| R8 | LC gate, load form, on each implementation phase | §1.3, §5 N01 |
| R9 | N01-A and N01-B have disjoint editable paths; N05-A paths are disjoint from all N01 phases | §4.2, §4.3 |

N01 owns no programme V-scenario. It must keep the delivered V02–V10 and V13 regressions green.

### 1.3 Invariants

- **I1 One definition per name.** Each moved function, class, constant and method exists exactly
  once. No name is defined in two classes of one facade's MRO.
- **I2 Pure mixins.** Each mixin is a plain class with a docstring, methods moved verbatim at
  their original indentation, and any class-body alias of one of its own methods (B:
  `capture_raw_preservation`, `restore_raw_preservation`). It has no `__init__`, no other class
  attributes, no `super()` use and no state of its own; all state stays in the facade's `__init__`.
- **I3 Layering.** Runtime imports form a DAG: `*_support` → `*_models` → (`workspace_coordination`)
  → mixin modules → facade. A mixin module never imports its facade. The P probe found no runtime
  import cycle in `owlbear_delivery` today (Tarjan SCC over module-level imports outside
  `TYPE_CHECKING`); N01 keeps it acyclic.
- **I4 Consumer surface.** Every name that any file under `serve/*/src`, `serve/*/tests`, `tests` or
  `serve/cockpit/web/e2e/support` imports from one of the four module paths stays importable from
  that path, as the same object. Module `__all__` lists stay unchanged.
- **I5 Patch reach.** Retargeting a module-global patch preserves the behavior that the existing
  patched test controls and asserts. The patch target is the module that holds the reader that test
  exercises. `_timestamp` stays defined once and shared by its production readers in several
  modules; its `application_lifecycle` patch proves the disposition-resolution scenario only, not an
  override across modules. Patches on instances,
  classes and attributes of facade objects stay unchanged. Every method that makes a
  class-qualified call `<Facade>._name(...)` stays in the facade with that line unchanged, so
  `patch.object(<Facade>, "_name", ...)` still reaches it; the callee may move to a mixin and
  resolves through inheritance. Moved code reaches retained methods only through `self`.
- **I6 Pinned symbols.** Structural tests in `tests/test_delivery_worktree_authority.py` identify
  code by enclosing class name and, for the worktree-add and runtime-writer checks, by file. These
  stay where they are:
  - `PortfolioApplication._observe_acceptance_once` (the only `complete_change` call site).
  - `ChangeWorkspaceManager._register_worktree` in `change_workspace.py` (the only `worktree add`),
    and its callers `ensure`, `restart`, `restore_worktree`; the `remove_worktree` callers
    `cleanup` and `recover`.
  - In `delivery_runtime.py`, class `DeliveryRuntime`: every method that calls `self._replace` or
    `_require_change_mutable` (43 writers, 1,743 lines), plus `complete_change`,
    `capture_change_disposition`, `resolve_change_disposition`, `record_resolved_target_sync` and
    `record_target_sync_abort`.
  - The worker-activity walk in `change_workspace.py` (`_ACTIVITY_WALK_MAX_ENTRIES`,
    `_ACTIVITY_WALK_SECONDS`, `_worktree_tree_activity_ns` and their readers), which
    `test_worker_stall.py` patches as `change_workspace` module globals.
- **I7 Logger identity.** Log records keep the logger name `owlbear_delivery.portfolio_application`.

### 1.4 Interfaces and error cases

No interface changes. The three facade classes keep their names, modules (`__module__`),
constructors and every member signature. `PortfolioCoordinator` and the moved models and errors
change `__module__`; the probe proved MCP tool schemas and Cockpit OpenAPI unchanged (no `$defs`
name collision), and no persisted record or test reads a module or class path. Error types and
messages are unchanged because their classes and raise sites move verbatim.

### 1.5 Existing owners to reuse

- `tests/test_delivery_worktree_authority.py` structural guards (unchanged; they prove I6).
- `owlbear_delivery_mcp.server.mcp`, `owlbear_cockpit.main.app` for schema snapshots.
- The default application loader and existing suites; no new fakes.
- The N00-A LC isolation recipe recorded on PR #326.

### 1.6 Exclusions

Behavior changes, renames of public or private symbols, new features, test rewrites, docstring or
comment edits inside moved code, reformatting, import-path churn in consumers, regenerating the
stale advisory `.owlbear/py-index.md`, and splitting `delivery_application_loader.py` or
`recovery.py`.

### 1.7 Decisions

Agent-settled with probe evidence:

- **D1 Mixins, not delegating collaborators.** Collaborators would break 120 method patches on
  facade instances (40 on `PortfolioApplication`, 57 on `ChangeWorkspaceManager`, 23 on
  `DeliveryRuntime`) and need explicit wiring for 327 of 658 distinct method-to-method references
  that cross the proposed groups and for 22 of 30 instance attributes shared across groups, in
  `PortfolioApplication` alone. That is a redesign, not a move. Mixins
  keep every instance, class and `patch.object` target, keep `dir()` and signatures, and let methods
  move verbatim (probe P5).
- **D2 Deterministic mover.** Code is moved by a script that cuts exact AST line spans (with
  decorators and leading comments) and pastes them unchanged. No model retypes moved code. Luna
  runs and adapts the mover; Opus reviews its output with the moved-line check (P6).
- **D3 Re-export block.** Each facade keeps its consumer surface with parenthesized imports headed
  `# Consumer import surface kept at this module path.` and `# noqa: F401` on the opening line
  (probe P7: the redundant-alias form trips `PLC0414`; extending module `__all__` would change it).
- **D4 Patch retargeting follows the reader** (I5). Class-attribute patches reached through a
  module path (`…FinalizationReportStore.retire`, `…time.sleep`, `…os.open`, `…subprocess.run`)
  are retargeted only when the facade no longer binds the intermediate name; their effect is global
  and unchanged.
- **D6 Logger.** `application_support._logger = logging.getLogger("owlbear_delivery.portfolio_application")`
  replaces `getLogger(__name__)`; it is the only logger in the split modules.
- **D7 New modules keep import paths.** New modules copy the original header imports and are pruned
  by Ruff; they import sibling-package names from the same paths as before (for example
  `owlbear_delivery.change_workspace`), so A, B and C never depend on each other's new modules.
- **D8 Loader stays whole.** At 2,463 lines it meets the guideline. Splitting it would move eight
  string patches and eleven private test imports for no size benefit, while N02's startup gate is
  expected to change it next.
- **D9 Permanent structure tests.** N01-A commits `serve/delivery/tests/test_module_structure.py`
  and `serve/delivery/tests/fixtures/module_surface.json`, which check I1–I4 for all three facades.
  Later phases that deliberately change `owlbear_delivery.__all__` or a facade surface update the
  fixture in the same PR.
- **D10 No Python type checker is configured** (Ruff `ALL`, including `TC` and `F821`, is the only
  static gate, locally and in MegaLinter). Mixin attribute access is therefore not statically
  checked before or after N01; see gap G1.

User decision: **U1** in [section 5](#5-verification-gaps) concerns the LC copy.

## 2. Feasibility Probes

All probes ran on `1acba53c5` in the lane worktree (read-only) or in a disposable `git archive`
copy with its own `uv sync --locked` venv (under `/tmp`, deleted afterwards). Probe helpers and
their outputs are in `/Users/GGN7H9Q/Projects/owlbear-dev-lane-a/.owlbear/scratch/n01p/`
(unversioned, advisory).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | AST inventory of all 642 patch calls in `tests/` and `serve/*/tests` | Relevant: 40 method patches on `PortfolioApplication` objects, 57 on `ChangeWorkspaceManager`, 36 on `PortfolioCoordinator`, 23 on `DeliveryRuntime`; 27 module-global patches into the four modules (application 5, workspace 14, loader 8); one `vars(delivery_runtime)` lookup of 7 private receipt models in `serve/tools/tests/test_delivery_diagnostics.py` | D1, D4, I5 |
| P2 | Source-structure scan of all tests | `tests/test_delivery_worktree_authority.py` pins symbols by class name and file (I6); no test reads `__qualname__`, `__module__` or source text of the split modules otherwise | I6, module map |
| P3 | Import inventory of the four module paths across the repository | 59 names imported from `portfolio_application` (only 22 in its `__all__`), 49 from `change_workspace` (no `__all__`), 94 from `delivery_runtime`, 13 from the loader; MCP, Cockpit and the E2E seed script import directly from these paths | I4, D3 |
| P4 | Runtime import graph of `owlbear_delivery` (module level, outside `TYPE_CHECKING`) | Acyclic today; `delivery_runtime` imports `change_workspace`, so C must follow B | I3, phase order |
| P5 | Prototype of the full N01-A map with the mover, then the affected suites | See [P5 results](#p5-results) | D1, D2, A map |
| P6 | Line-multiset moved-check on the P5 diff (old module vs. all new modules, non-import lines) | Non-import residue: 1 facade class header, 5 mixin headers + docstrings, 7 module docstrings, 1 re-export comment; every other code line, including every class-qualified call, matched one-to-one; Ruff format changed no moved line | R7, D2, I5 |
| P7 | Ruff 0.16.5 on re-export forms | `import X as X` → `PLC0414`; parenthesized import with `# noqa: F401` on its opening line → clean | D3 |
| P8 | MCP/Cockpit/export snapshot before and after P5 | 63 MCP tools (input/output schemas), Cockpit OpenAPI (43 paths) and `owlbear_delivery.__all__` (322 names): byte-identical | R1, R3, model `__module__` change is invisible |
| P9 | Mixin hazards in the three classes | No name mangling, `super()`, `__slots__`, `type(self)` or class-attribute state in the large classes; class-qualified calls, all to static methods: `PortfolioApplication` 3 in 2 methods, `ChangeWorkspaceManager` 25 in 15 methods, `DeliveryRuntime` none, none outside the classes; the loader calls 3 `DeliveryRuntime._builder_*` statics, which resolve through inheritance | I2, I5 |
| P10 | Prototype of the N01-B map (alone, then combined with A) | See [P10 results](#p10-results) | B map, A/B independence |
| P11 | Prototype of the N01-C map on top of A and B | See [P11 results](#p11-results) | C map, writer pinning |
| P12 | Type checker configuration (`pyproject.toml`, `.mega-linter.yml`, quality runner) | No pyright/mypy/ty; MegaLinter enables `PYTHON_RUFF` and `PYTHON_RUFF_FORMAT` only | D10 |
| P13 | Class-qualified patch reach (`cq_reach.py`): each class-qualified callee replaced on the facade class by a call-through recorder, as `patch.object(<Facade>, "_name")` would, while the four reach files of [3.3](#33-equivalence-protocol) run | See [P13 results](#p13-results) | I5 |

### P5 results

Baseline on the copy: 3,517 collected (1 deselected); affected suites 3,328 passed, 3 skipped.
After the A prototype (round 1, class-qualified callers retained): Ruff check and format clean;
no mover error; collected node IDs identical; schemas identical (P8); member/kind/signature
snapshot of the four classes identical; consumer surface complete; all 34 module files import in
a fresh interpreter; no import cycle; per-test outcomes identical (3,328 passed, 3 skipped,
0 differing). Four patch strings had to move to `owlbear_delivery.application_lifecycle` (three in
`test_portfolio_application.py`, one in `tests/test_cockpit_work_items.py`). With the old strings
restored, those four tests fail
(three `AttributeError`s, one unpatched reader); the `time.sleep` patch passes either way because
it patches the global `time` module and the facade still binds `time`, so it stays unchanged (D4).
Import time of `owlbear_delivery` did not rise (cumulative `-X importtime`, warm runs: base
181 ms, A 186–188 ms, B 187–188 ms, A+B+C 181–186 ms).

| Module | Lines (P5) |
| --- | ---: |
| `portfolio_application.py` (facade) | 1,851 |
| `application_support.py` | 498 |
| `application_models.py` | 1,518 |
| `application_readiness.py` | 2,106 |
| `application_acquisition.py` | 2,018 |
| `application_publication.py` | 1,635 |
| `application_lifecycle.py` | 832 |
| `application_recovery.py` | 2,104 |

### P10 results

Mover output for the B map: Ruff check and format clean; every new module and the facade import in
a fresh interpreter; residue only headers, docstrings and the re-export comment, with all 25
class-qualified calls unchanged in the 15 retained callers; the two class-body
aliases `capture_raw_preservation` and `restore_raw_preservation` must move with their targets;
`PublicationLock`'s annotations need `PortfolioCoordinator` from the later
`workspace_coordination` module under `TYPE_CHECKING`. The facade keeps `os` and `subprocess`, so
four of the five distinct string-patch targets (`os.open`, `os.close`, `os.fstat`,
`subprocess.run`) stay valid. B alone on a second copy, with the `write_contained` string
retargeted: collected node IDs identical; per-test outcomes identical (3,328 passed, 3 skipped,
0 differing); schema, member and consumer-surface snapshots identical. With the old string
restored, all four parameters of
`test_nonterminal_recovery_capture_failure_keeps_bytes_and_replays` fail (`AttributeError`).

Three mover hazards were found and fixed; each passed Ruff while being wrong, which is why the
fresh-import and surface tests are mandatory:

- Ruff's `TC` fixes moved the facade's `PortfolioCoordinator` import under `TYPE_CHECKING`, which
  dropped it from the runtime consumer surface (`owlbear_delivery/__init__.py` failed to import).
  The re-export step must count runtime bindings only.
- `ruff check --select …,RUF100 --fix` treats every `noqa` for a non-selected rule as unused and
  strips it from moved code. RUF100 may only be fixed under the full rule set
  (`--fix --fixable RUF100`).
- Auto-fixing `TC004` turned annotation-only back references into runtime imports (P11).

| Module | Lines (P10) |
| --- | ---: |
| `change_workspace.py` (facade) | 1,853 |
| `workspace_models.py` | 2,197 |
| `workspace_coordination.py` | 995 |
| `workspace_worktree_state.py` | 1,162 |
| `workspace_preservation.py` | 1,717 |
| `workspace_snapshots.py` | 749 |
| `workspace_target_sync.py` | 1,235 |

### P11 results

The first C map placed `_model_content`, `_receipt_digest`, `_finalization_invalidation_digest`,
`_reference` and the runtime errors above the models that call them; Ruff's `TC004` fix then made
`runtime_models` and `runtime_support` import each other and every module failed to import, with
Ruff still clean. The corrected map below puts those helpers and errors in `runtime_models`: Ruff
clean, all six modules import in a fresh interpreter, no back reference, no class-qualified call.

With A, B and C applied together on one copy (all five A and B patch strings retargeted): Ruff
check and format clean on the 21 touched modules; collected node IDs identical; per-test outcomes
identical (3,328 passed, 3 skipped, 0 differing); schema, member and consumer-surface snapshots
identical; no import cycle; all 45 `owlbear_delivery` module files import in a fresh interpreter.
Moved-check residue for C is the facade class line, two mixin headers, docstrings and the
re-export comment only.

| Module | Lines (P11) |
| --- | ---: |
| `delivery_runtime.py` (facade) | 2,491 |
| `runtime_models.py` | 1,744 |
| `runtime_receipts.py` | 605 |
| `runtime_support.py` | 590 |
| `runtime_settlement.py` | 1,024 |
| `runtime_reads.py` | 809 |

`delivery_runtime.py` stays near the guideline because I6 pins 1,743 lines of writers in
`DeliveryRuntime`.

### P13 results

At `1acba53c5` the class-qualified calls form 25 distinct (caller, callee) pairs: 3 in
`PortfolioApplication` (2 callers) and 22 in `ChangeWorkspaceManager` (15 callers); every callee
is a static method. With the recorder on the facade class, the four reach files (1,004 tests,
all passed) reached 25 of 25 pairs on the base copy and 25 of 25 on the A+B+C copy, each from a
facade method. Negative: rewriting `_exact_task_scope_details` and `_verify_worktree_ancestors`
to their mixins inside the retained callers (the formerly planned rewrite) lost exactly the 6
pairs of those callers while all 1,004 tests still passed, so only this check detects the defect.

## 3. Phases

### 3.1 Shared procedure for N01-A, N01-B and N01-C

**Mover (D2).** Input: the phase's module map (below), the facade class, and the baseline
consumer surface. For each destination it writes the module docstring, the original header imports
(runtime block, then imports of earlier destinations, then the `TYPE_CHECKING` block), the moved
top-level spans in source order and, for a mixin, `class _XMixin:` with its docstring and the moved
method spans. It removes the spans from the facade, imports moved names the facade still uses, adds
the mixins as bases in the order given and writes the re-export block (D3). It fails on any
reference from a destination to a name that stays in the facade, including any class-qualified
`<Facade>._name` reference in a moved method (that method stays in the facade, I5).
A reference to a later destination is allowed only for annotations, under `TYPE_CHECKING`. Then, on
the touched modules only: `ruff check --fix --unsafe-fixes --select F401,F811,PIE790` and
`ruff check --fix --unsafe-fixes --select I001,TC --ignore TC004` (repeated until stable), the
re-export block (counting runtime bindings only), `ruff check --fix --fixable RUF100` under the full
rule set, and `ruff format`. A remaining `TC004` is a map defect, not a fix target. The P probe
mover (`move_tool.py`, `gen_spec_*.py`) implements this; re-verify it against this section.

Moved spans keep their original order inside each destination. Facade class bases are listed in
the order of the destination table.

### 3.2 Allowed edits

Any diff line outside these classes fails the phase:

1. Import statements, including `TYPE_CHECKING` blocks and the D3 re-export block with its comment.
2. New module docstrings; mixin `class` lines and docstrings; the facade `class` line gaining bases.
3. D6 logger line (N01-A only).
4. In tests: patch-target strings or module objects listed for the phase, and import lines.
5. N01-A only: the new files `serve/delivery/tests/test_module_structure.py` and the generated
   `serve/delivery/tests/fixtures/module_surface.json`, exactly as specified in
   [3.4](#34-n01-a--application-facade); no other new test or fixture file.
6. The phase's progress row in this plan and its status row in the execution plan.

### 3.3 Equivalence protocol

`$W` is the lane worktree, `$X` = `$W/.owlbear/scratch/n01-<phase>`, `$H` the probe helpers copied
into `$X`. Run every command from `$W` with `env -u PYTHONPATH`. Run the suite command in a new
session (`$H/detach.py <log> "<command>"`, which `setsid`s) and poll its log: in P, foreground and
`nohup … &` runs were interrupted by the terminal tool near the end and lost their JUnit report.

Before the first edit, on the phase base commit `$B`:

```shell
uv run pytest --collect-only -q -n0 > $X/collect_base.txt
uv run pytest serve/delivery/tests serve/delivery-mcp/tests serve/tools/tests serve/cockpit/tests tests \
  -q --junitxml=$X/junit_base.xml > $X/run_base.txt 2>&1
uv run python $H/schema_dump.py > $X/schema_base.json      # MCP tools, Cockpit OpenAPI, owlbear_delivery.__all__
uv run python $H/members_dump.py > $X/members_base.json    # dir(), kind and signature of the 4 split classes
uv run python $H/reexport_inventory.py . $X/surface_base.json
uv run python -X importtime -c "import owlbear_delivery" 2> $X/importtime_base.txt
```

On the candidate head, the same commands into `*_head` files, then:

| Check | Command | Pass |
| --- | --- | --- |
| Node IDs | `diff <(grep :: $X/collect_base.txt \| sort) <(grep :: $X/collect_head.txt \| sort)` | Only the phase's new test IDs are added |
| Outcomes | `uv run python $H/junit_compare.py $X/junit_base.xml $X/junit_head.xml` | No outcome differs; counts equal plus added tests passed |
| Contracts | `cmp $X/schema_base.json $X/schema_head.json` | Identical (R1, R3) |
| Members | `cmp $X/members_base.json $X/members_head.json` | Identical (R2) |
| Moves only | `uv run python $H/moved_check.py . $B <old module> -- <facade and new modules>` | Residue only in [3.2](#32-allowed-edits) classes, with the expected counts |
| Review view | `git diff --color-moved=dimmed-zebra --color-moved-ws=allow-indentation-change $B -- <paths>` | Opus inspects; no unexplained non-moved block |
| Structure | `uv run pytest serve/delivery/tests/test_module_structure.py tests/test_delivery_worktree_authority.py -q` | Pass (I1–I4, I6) |
| Sizes | `wc -l` on the facade and new modules | Each ≤ 2,500 unless the phase states otherwise |
| Lint | `uv run ruff check <touched>` and `uv run ruff format --check <touched>` | Clean |
| Import time | compare `owlbear_delivery` cumulative µs in `importtime_*.txt` | Informational; explain a rise above 20 % |
| Class-qualified reach | `$H/cq_run.sh <copy> <tag> serve/delivery/tests/test_change_workspace.py serve/delivery/tests/test_worker_stall.py serve/delivery/tests/test_recovery.py serve/delivery/tests/test_portfolio_application.py`, once on a copy of `$B` and once on a copy of the candidate (below) | Every required (caller, callee) pair reached in both copies |
| Closeout | `uv run test --changed` | Pass |

**Class-qualified reach (I5).** For each `<Facade>._name` reference inside a facade method at
`$B`, `$H/cq_reach.py` replaces `<Facade>._name` on the facade class with a call-through recorder
(what `patch.object(<Facade>, "_name", ...)` does), runs the listed files and records which
method called it. Pass: every (caller, callee) pair is reached on `$B` and on the candidate, and on
the candidate the caller is still a `<Facade>` method. The copies come from
`$H/mkcopy.sh <tag> $B [$W]` (a `git archive` of `$B` with its own locked venv, optionally overlaid
with the candidate worktree); `cq_run.sh` activates the recorder through the copy's `conftest.py`,
so `$W` is never edited. Negative: rewriting a retained caller's `<Facade>._name` to
`<Mixin>._name` (the formerly planned rewrite) loses that pair.

**LC, load form (R8), on the committed head of each phase.** Use the N00-A isolation recipe from
PR #326 on a copy of live state ([U1](#5-verification-gaps)). Prove isolation statically (no main
checkout path in any copied worktree `.git` file, `gitdir`, Git config or coordination record;
`git rev-parse --git-common-dir` resolves into the copy). Hash every file under the copy's
`.owlbear/delivery`, run the candidate's `delivery-diagnose`, then a read-only
`load_delivery_application` that calls `list_changes()` and `get_change()` for every Change, and
hash again. Pass: every Change is available, no diagnostic is new, no hash changed. Record the
result on the PR.

**Delegation (§1.6).** Opus fixes the phase's module map and allowed-edit counts before any
dispatch. Luna slices: (1) run the mover for one destination group and report Ruff output and
sizes; (2) retarget the listed patch targets; (3) N01-A only: write the structure tests to
[3.4](#34-n01-a--application-facade)'s specification. Each dispatch names its editable paths, the
checks above it must run, and that it must not commit, push or touch live state. Opus reruns the
moved check, the structure tests and the suites, then commits.

### 3.4 N01-A — Application facade

- **Prerequisites:** N01-P, N00-C (execution plan §4.2).
- **Editable paths:**
  - `serve/delivery/src/owlbear_delivery/portfolio_application.py`
  - new `serve/delivery/src/owlbear_delivery/application_{support,models,readiness,acquisition,publication,lifecycle,recovery}.py`
  - `serve/delivery/tests/test_portfolio_application.py` — three patch strings only (four if the
    facade stops binding `time`)
  - `tests/test_cockpit_work_items.py` — one patch string only
  - new `serve/delivery/tests/test_module_structure.py`, new `serve/delivery/tests/fixtures/module_surface.json`
  - this plan's N01-A progress row; the execution plan's N01-A status row
- **Module map** (method runs in source order at `1acba53c5`; `a .. b` is inclusive):

| Destination | Content |
| --- | --- |
| `application_support.py` | All module constants from `_MAX_PULL_REQUEST_TITLE_LENGTH` through `_INTENT_SUMMARY_HEADING`; `_logger` (D6); `_timestamp`, `_health_detail`, `_health_diagnostic_key`, `_canonical_model_bytes`, and every function from `_failed_required_publication_checks` through `_checkpoint_pull_request_title`; `_publication_identity` |
| `application_models.py` | `_worker_stall_prompt`, `_operator_claim`, `_operator_recovery_attention`, `_operator_integration_attention`; every class from `_ApplicationModel` through `_ReviewRepairAuthority`; the `DeliveryContinuationReason` alias; `DeliveryContinuationResult.model_rebuild()` |
| `application_readiness.py` — `_ReadinessViewsMixin` | `list_integration_attention .. delivery_health` (10); `_delivery_health_view .. _worktree_recovery_view` (43); `_portfolio_snapshots .. _snapshot_dependency_depth` (15) |
| `application_acquisition.py` — `_AcquisitionMixin` | `_recover_expired_claims .. _acquire_selected_candidate` (31); `show_plan_context .. show_build_context` (2); `_candidate_authority .. _acquire_candidate_writer` (12) |
| `application_publication.py` — `_PublicationMixin` | `observe_change_publication_checks .. _validate_provider_supersession` (19); `mark_change_ready .. _replay_review_repair` (9); `_reconcile_finalization_head_locked .. _prepare_checkpoint_head` (10); `_replay_pending_state_publications .. _pending_publication_remote_head` (6) |
| `application_lifecycle.py` — `_LifecycleMixin` | `show_change_checkpoint_publication .. _validate_finalization_report_basis` (29); `resolve_change_disposition .. resume_change` (5); `abandon_change` (1) |
| `application_recovery.py` — `_RecoveryMixin` | `_reconcile_retry_results .. _import_legacy_worker_budgets` (9); `transition_delivery .. _settle_stalled_workers` (19); `repair_delivery_state_snapshot .. _clear_remote_state_reconciliation` (10); `_repair_proposal .. _unavailable_change` (10); `recover_claim .. _readback_recovery_ready` except the two retained callers (18) |
| `portfolio_application.py` (facade) | Header imports, D3 block, `class PortfolioApplication(_ReadinessViewsMixin, _AcquisitionMixin, _PublicationMixin, _LifecycleMixin, _RecoveryMixin)` with `__init__`; `create_design_session .. put_design`; `reconcile_awaiting_acceptance .. _provider_unavailable_outcome` (11); `observe_acceptance .. _publish_attention_best_effort` (5, includes pinned `_observe_acceptance_once`); `read_design_session .. publish_delivery_result` (9); `_reconcile_runtimes .. _observation_detail` (9); `list_completed_changes .. _completed_history` (4); `get_change .. answer` (4); the class-qualified callers `_exact_task_scope` and `_recovery_admission_fields` (2, I5); `_reserve_worker_attempt .. _fail` (22); unchanged `__all__` |

- **Method counts** (mover cross-check at `1acba53c5`): readiness 68, acquisition 45, publication
  44, lifecycle 35, recovery 66, facade 69; total 327.
- **Allowed-edit counts:** 1 D6 line. The 3 class-qualified calls stay unchanged in the facade.
- **Patch retargets** (all to `owlbear_delivery.application_lifecycle`):
  `_ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS` (2: `test_portfolio_application.py`,
  `tests/test_cockpit_work_items.py`), `_timestamp`, `FinalizationReportStore.retire`. The
  `time.sleep` string stays while the facade binds `time`.
  No import line changes: `_required_check_diagnostics` stays importable through the D3 block.
- **Structure tests** (`test_module_structure.py`, generic over the package so B and C need no
  edit):
  - static runtime import graph of `owlbear_delivery` is acyclic; the detector rejects a synthetic
    two-module cycle;
  - each `owlbear_delivery` module imports in a fresh interpreter (parametrized subprocess);
  - `sorted(owlbear_delivery.__all__)` equals the fixture;
  - every fixture surface name of the four module paths resolves (I4);
  - for `PortfolioApplication`, `ChangeWorkspaceManager` and `DeliveryRuntime`: every base other
    than `object` defines no `__init__` and only functions, static methods, class methods and
    properties; member names are pairwise disjoint across the class and its bases (I1, I2).
  The fixture is generated once on the N01-A base: `{"package_all": [...], "surfaces":
  {"portfolio_application": [...], "change_workspace": [...], "delivery_runtime": [...],
  "delivery_application_loader": [...]}}`, sorted, from P3's import inventory plus the 7 private
  receipt models that `vars(delivery_runtime)` reads.
- **Scenarios:**
  - Positive: equivalence protocol passes; default loader, `Client(assemble_target_server(...))`
    and the Cockpit HTTP client run through the moved code in the existing suites; patched-global
    tests pass with the retargeted strings.
  - Negative: with the four retargeted strings restored to the old path, those tests fail (P5); a mixin module importing
    `owlbear_delivery.portfolio_application` makes the cycle test fail; a method duplicated into a
    second mixin makes the disjointness test fail; moving `_observe_acceptance_once` into a mixin
    makes `test_completion_has_one_application_callsite_and_merged_latch_guard` fail.
- **Inner loop:** after the support and models move, `uv run pytest serve/delivery/tests/test_portfolio_application.py -q -k "resolving_change_attention or retire"`;
  after each mixin, `uv run pytest serve/delivery/tests/test_portfolio_application.py serve/delivery/tests/test_recovery.py tests/test_delivery_worktree_authority.py -q`.
- **Closeout:** [3.3](#33-equivalence-protocol) in full; LC load form.
- **Size and risk:** L / medium. Mechanical, but the largest move; the risk is a missed patch reach
  or re-export, both caught by the protocol.

### 3.5 N01-B — Workspace module

- **Prerequisites:** N01-P, N00-C. Runs in parallel with N01-A.
- **Editable paths:**
  - `serve/delivery/src/owlbear_delivery/change_workspace.py`
  - new `serve/delivery/src/owlbear_delivery/workspace_{models,coordination,worktree_state,preservation,snapshots,target_sync}.py`
  - `serve/delivery/tests/test_change_workspace.py` — patch strings only (expected: one)
  - this plan's N01-B progress row; the execution plan's N01-B status row
- **Module map:**

| Destination | Content |
| --- | --- |
| `workspace_models.py` | Every module constant except the two `_ACTIVITY_WALK_*` constants; every top-level definition from `_contains_private_index_metadata` through `ChangeTargetSyncStaleError` (records, receipts, errors, `PublicationLock`, `ChangeCoordination` and the interleaved helpers); module helpers `_directory_identity_tuple .. _reject_symlink_ancestors` and `_open_worktree_parent .. _branch_name` |
| `workspace_coordination.py` | `PortfolioCoordinator` |
| `workspace_worktree_state.py` — `_WorktreeStateMixin` | `_preservation_git .. _state_digest` (21) and `_read_private_staging_state .. _captured_finalization_guard` (13), each without its retained callers |
| `workspace_preservation.py` — `_PreservationMixin` | `capture_finalization_workspace .. require_preservation_environment` without its retained callers (25, plus the class-body aliases `capture_raw_preservation` and `restore_raw_preservation`); `_preservation_object_name .. _state_from_entry` (7) |
| `workspace_snapshots.py` — `_SnapshotMixin` | `prepare_finalization_boundary .. _restore_worktree_files` (12); `observed_change_head .. _quarantine_commit_parent` (14) |
| `workspace_target_sync.py` — `_TargetSyncMixin` | `recover_out_of_band_head` (1); `refresh_integration_target .. validate_finalization_head` (37) |
| `change_workspace.py` (facade) | Header imports, D3 block, the activity-walk family (`_ACTIVITY_WALK_MAX_ENTRIES`, `_ACTIVITY_WALK_SECONDS`, `_ActivityStamp`, `_activity_stamp`, `_ActivityWalkBudget`, `_worktree_tree_activity_ns`, `_directory_activity_ns`), `class ChangeWorkspaceManager(_WorktreeStateMixin, _PreservationMixin, _SnapshotMixin, _TargetSyncMixin)` with `__init__ .. record_reviewed` (23, includes `observe_worktree_activity`, `ensure`, `recover`); `restore_worktree .. _record_cleanup_receipt` (14, includes `_register_worktree`, `cleanup`); the 13 retained class-qualified callers below; `validate_writer_head .. _run_git` (33, includes `restart`) |

- **Retained class-qualified callers (I5):** 15 static methods with 25 `ChangeWorkspaceManager._name`
  calls stay in the facade unchanged. Already in the facade: `_recovery_attention`, `_is_ancestor`.
  Retained from the former preservation runs: `_validate_provenance_states`,
  `_validate_recovery_path_containment`, `require_preservation_environment`. Retained from the
  former worktree-state runs: `_validate_index_extensions`, `_validate_legacy_index_extensions`,
  `_has_ignored_inventory`, `_open_worktree_read_parent`, `_read_worktree_metadata`,
  `_read_worktree_handoff_metadata`, `_read_worktree_state`, `_validate_private_staging_inventory`,
  `_require_private_staging_readback`, `_dirty_paths`.
- **Mover order:** models, coordination, then the mixins in base order; no mixin module imports
  another mixin.
- **Method counts:** worktree state 34, preservation 32 (+2 aliases), snapshots 26, target sync 38,
  facade 83; total 213.
- **Allowed-edit counts:** none beyond imports, headers and docstrings; the 25 class-qualified calls
  stay unchanged in the facade. One `TYPE_CHECKING` import of `PortfolioCoordinator` in
  `workspace_models`.
- **Patch retargets:** `change_workspace.write_contained` → `workspace_preservation.write_contained`
  (all `write_contained` readers, `_write_restoration_record` and `_write_preservation_store`, are
  in that module). `os.open`, `os.close`, `os.fstat` and `subprocess.run` strings stay valid while
  the facade imports `os` and `subprocess`; otherwise retarget to a module that does. No other test
  edit; `test_worker_stall.py` is untouched (I6).
- **Scenarios:**
  - Positive: equivalence protocol; the preservation, quarantine, target-sync and cleanup suites in
    `test_change_workspace.py`, `test_worker_stall.py`, `test_recovery.py` and
    `test_change_publication.py` pass unchanged.
  - Negative: the `write_contained` interruption test fails with the old patch string; moving
    `restart` or `cleanup` into a mixin fails the worktree-registration or removal guard.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_change_workspace.py serve/delivery/tests/test_worker_stall.py tests/test_delivery_worktree_authority.py -q`.
- **Closeout:** [3.3](#33-equivalence-protocol); `test_module_structure.py` exists only once N01-A
  is merged, so before that run its checks from `$H` (cycle, fresh import, surface) and record them;
  LC load form.
- **Size and risk:** L / medium. The moved code includes no-follow file-descriptor reads and Git
  index validation; it is security-relevant and therefore moved verbatim only.

### 3.6 N01-C — Runtime module

- **Prerequisites:** N01-A, N01-B (B because `delivery_runtime` imports `change_workspace`).
- **Editable paths:**
  - `serve/delivery/src/owlbear_delivery/delivery_runtime.py`
  - new `serve/delivery/src/owlbear_delivery/runtime_{models,receipts,support,settlement,reads}.py`
  - tests: none expected; `serve/delivery/tests/fixtures/module_surface.json` is not edited
  - this plan's N01-C progress row; the execution plan's N01-C status row
- **Module map:**

| Destination | Content |
| --- | --- |
| `runtime_models.py` | Constants `_MAX_WORKER_RETRIES .. _SHA256_HEX_LENGTH`; every top-level definition from `DeliveryStage` through `EngineWorkerDisposition` (including `DELIVERY_TRANSITION_ADAPTER` and the settlement failure-code maps); the runtime errors `DeliveryRuntimeConflictError .. DeliveryRuntimeReferenceError`; `_STAGE_ORDER .. _NORMAL_CHANGE_MUTATIONS`; `is_change_terminal`, `derive_change_stage`; the helpers `_model_content`, `_receipt_digest`, `_finalization_invalidation_digest`, `_reference`; the three `model_rebuild()` calls |
| `runtime_receipts.py` | `DeliveryPlanningRetrySettlement .. AdministrativeDeliveryMoveResult` (worker settlements, private settlement receipts, administrative-move models) |
| `runtime_support.py` | The remaining module functions `_find_binding .. _conflict` (includes `_require_change_mutable`, receipt readers and checkpoint helpers) |
| `runtime_settlement.py` — `_SettlementReplayMixin` | `_transitioned_binding .. _planning_pause_replay_path` (36 non-writer methods) |
| `runtime_reads.py` — `_RuntimeReadsMixin` | The remaining non-writer methods not kept below: read queries (`publication_base_digest`, `finalization_readiness`, `checkpoint_publication_state`, `validate_target_sync_conflict`, `completion_receipt`, `integration_repair_claim`, `require_integration_repair_claim`, `require_active_claim`, `claimable_outcome_ids`, `claimable_task_ids`), completed-outcome repair lookups, activation and transition validation (`_validate_builder_handoff_activation`, `_validate_planner_handoff_activation`, `_pending_transition_matches`, `_advanced_builder_handoff`, `preview_administrative_move`, `_require_no_handoff_in_administrative_closure`, `_advance`, `_validate_retry_identity .. _require_builder_transition_exclusion`, `_change_intent_custody_participants`, `_pending_publication_participant`) |
| `delivery_runtime.py` (facade) | Header imports, D3 block (including the 7 private receipt models that `vars(delivery_runtime)` reads), `class DeliveryRuntime(_SettlementReplayMixin, _RuntimeReadsMixin)` with all 43 writers (I6), `__init__`, property accessors, `acknowledge_pending_publication`, `reanchor_pending_publication`, `capture_publication_attention`, `capture_acceptance_attention`, `_capture_existing_change_disposition`, `_target_sync_update`, `_external_head_adoption_update`, `_read`, `_replace`, `_replace_content`, `_validate_frontier`; unchanged `__all__` |

- **Method counts:** settlement 36, reads 30, facade 79 (43 writers); total 145.
- **Allowed-edit counts:** none beyond imports, headers and docstrings; `DeliveryRuntime` has no
  class-qualified call; no back reference.
- **Patch retargets:** none expected. `_NORMAL_CHANGE_MUTATIONS` stays importable from
  `delivery_runtime` through D3.
- **Scenarios:**
  - Positive: equivalence protocol; `test_runtime_frontier_writers_use_the_central_mutability_policy`
    and `test_target_sync_runtime_writers_bind_operation_names_before_replacement` pass unchanged;
    the loader's `DeliveryRuntime._builder_*` calls resolve through inheritance;
    `test_delivery_diagnostics.py`'s `vars(delivery_runtime)` lookup passes.
  - Negative: moving any writer into a mixin fails the mutability-policy guard.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_delivery_runtime.py serve/delivery/tests/test_delivery_state.py serve/tools/tests/test_delivery_diagnostics.py tests/test_delivery_worktree_authority.py -q`.
- **Closeout:** [3.3](#33-equivalence-protocol); package closeout runs the full `uv run test` once;
  cumulative Sol challenge of the N01 diff against this plan; LC load form.
- **Size and risk:** M / medium. The facade lands at about 2,491 lines (P11) because I6 pins the
  writers; any growth from N00-C may push it past 2,500, which is accepted only with that reason
  recorded on the PR.

### 3.7 Parallel safety and N05-A boundary

N01-A and N01-B share no editable path. Neither edits `owlbear_delivery/__init__.py`,
`delivery_runtime.py`, `delivery_application_loader.py`, `pyproject.toml`,
`tests/test_delivery_worktree_authority.py` or `test_worker_stall.py`. Their only shared files are
the status rows ([4.3](delivery-redesign-execution-plan.md#43-ready-rule-and-default-schedule)
companions). B never needs A's modules (D7), so either may merge first; the second rebases and
reruns the protocol. P5 (A alone), P10 (B alone) and P11 (A, B and C together) cover both merge
orders.

**N05-A may edit:** `serve/delivery-github/**`;
`serve/delivery/src/owlbear_delivery/publication_provider.py` and, if its adapter needs them,
`draft_pull_request.py` and `change_publication.py` (no N01 phase edits them; N05-A must not remove
or rename a name that the split modules import); new provider-adapter modules under
`serve/delivery/src/owlbear_delivery/` whose names do not start with `application_`, `workspace_`
or `runtime_`; `serve/delivery-github/tests/**`; new test files for those modules; and the provider
gate in `tests/test_delivery_worktree_authority.py` (N01 does not edit that file).
**N05-A must not edit** while any N01 phase is unmerged: the four split modules, every N01 module
above, `owlbear_delivery/__init__.py`, `test_portfolio_application.py`,
`test_change_workspace.py`, `test_delivery_runtime.py`, `test_worker_stall.py`,
`tests/test_cockpit_work_items.py`, `test_module_structure.py` and its fixture. New public exports
from `owlbear_delivery` wait until N01 is merged, because they change the D9 fixture.

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N01-P | #342 | — | Probes P1–P13 | Sol plan rounds: 1 revision-required (D5, §3.2), 2 revision-required (I5), 3 `plan-sound` | approved |
| N01-A | #344 | `693b6dc3b` | On base `42144f9dc`: G3 none (N00-C changed only `except` formatting; name-based spec equals the P5 spec; counts 68/45/44/35/66/69). Mover + 3.1 Ruff steps clean and stable; node IDs +44 (structure tests only); outcomes 0 differing except `test_continuation_publishes_syncs_finalizes_and_observes_acceptance` (30 s timeout under machine load; alone 5.7–6.2 s head vs 6.1–8.1 s base); schema and members identical; moved-check residue 2 removed / 20 added, all 3.2; sizes ≤ 2,106; Ruff clean; no cycle; import time +1 %; P13 25/25 pairs on base and head (1,004 passed each); negatives: 4 old patch strings → 4 fail, facade import cycle, duplicated mixin method and moved `_observe_acceptance_once` each fail their guard; `uv run test --changed` selected the new JSON fixture as a pytest path (0 items, exit 1; `owlbear_tools.testing` defect), so its 35 test paths ran directly: 2,352 passed (runner fixed in #343). Quiet rerun: 3,375 passed, 3 skipped; 0 existing outcomes differ. LC load form on `693b6dc3b`: healthy, 3 Changes available, 0 record writes, live unchanged | Sol implementation round 1 `implementation-sound` (no repair) | merged |
| N01-B | #346 | `fc4ca75b5` | First on base `42144f9dc` (G3: no method added or renamed since `1acba53c5`): name-based mover, Ruff clean, sizes facade 1,853 / models 2,197 / coordination 995 / worktree state 1,162 / preservation 1,717 / snapshots 749 / target sync 1,235; reach 25/25 pairs on base and head (1,004 passed each); negatives: old `write_contained` string fails 4/4, `restart` or `cleanup` in a mixin fails its guard. Rebased onto `d80724094` (N01-A merged), redundant facade `TYPE_CHECKING` re-import of `PortfolioCoordinator` removed. Serial rerun on that base: 3,381 → 3,387 passed, 0 existing outcomes differ (+6 fresh-import IDs); schema, members and surface identical; moved check residue only 3.2 classes; all 314 definitions (213 methods) text-identical, none missing or duplicated; 25/25 class-qualified calls in the facade; structure and authority tests 89 passed. Earlier loaded-machine timeouts: the 12 tests take 31–45 s on base and 31–32 s on head alone. LC load form on `fc4ca75b5`: healthy, 3 Changes available, 0 record writes, live unchanged | Sol implementation round 1 `blocked` only on exact-candidate binding (its Git reads failed); resolved by the executed binding and per-definition comparison above, no defect found | merged |
| N01-C | #347 | `1ba931191` | On base `4f82812f6` (G3: `delivery_runtime.py` changed since `1acba53c5` only in 5 `except` formatting lines; no method added or renamed; name-based spec equals the P11 spec). Name-based mover, Ruff steps clean and stable, no `TC004`; sizes facade 2,491 / models 1,744 / receipts 605 / support 590 / settlement 1,024 / reads 809; method counts 36/30/79 with all 43 writers (1,743 lines) in `DeliveryRuntime`; no class-qualified call; loader's 3 `DeliveryRuntime._builder_*` statics resolve through `_SettlementReplayMixin`; D3 block carries the 7 private receipt models and `_NORMAL_CHANGE_MUTATIONS`; `__all__` unchanged (69). Serial base/head: 3,387 → 3,392 passed, 0 existing outcomes differ (+5 fresh-import IDs); schema, members and surface identical; moved check residue 1 removed / 11 added, all 3.2; all 270 definitions (145 methods) text-identical, none missing or duplicated; structure and authority tests 94 passed; import time +0.7 % (median of 3). Negatives: `defer_change` or `record_target_sync_abort` in a mixin fails the mutability-policy guard (the latter also the target-sync guard). Package closeout `uv run test`: 3,580 pytest passed, Vitest 331 passed (25 files). Lead check on the commit: 270/270 definitions text-identical, 145 methods (79/36/30), structure and authority 94 passed. LC load form on `1ba931191`: healthy, 3 Changes available, 0 record writes, live unchanged | Cumulative Sol implementation round 1 (N01-C and N01 A+B+C) `implementation-sound`, no repair | merged |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | Mixin attribute access is type-correct | No Python type checker is configured (D10); `F821` covers names, not attributes | Full suites exercise every moved method; Ruff clean | None in N01; whoever adopts a type checker adds a typed host protocol | Nothing |
| G2 | Each phase loads live state unchanged | LC needs a confirmed live copy (U1); not run in P | P8 schema identity; no persisted record carries a module path | N01-A, N01-B, N01-C | That phase's merge |
| G3 | The P probes match the eventual phase heads | N00-C may change these modules before A/B start; the maps name methods, not lines | Name-based runs; the mover fails on an unknown name; Opus assigns any method added since `1acba53c5` before moving | Each phase's Opus lead | That phase |
| G4 | Frontend is unaffected | `npm test`, build and E2E not run (no frontend change; OpenAPI identical) | P8 | N01-C package closeout runs `uv run test`, which includes Cockpit unit tests | Nothing |
| G5 | Import time is unchanged | Measured only as information | `-X importtime` comparison per phase | Each phase | Nothing |

**U1 — LC copy (user).** Status quo: LC needs a copy of live Delivery state taken while no live
Delivery work runs, which the user confirms. Problem: the user is not always present when a phase
reaches closeout, and N01 has three phases. Options: (a) a fresh isolated copy per phase, each
confirmed; (b) one fresh copy confirmed before N01-A/B closeout, kept read-only and duplicated for
each phase's LC run; (c) build the copy from the N00-M backup `~/owlbear-backups/n00m-20261003-015344`
if the user confirms no live Delivery mutation since. Recommendation: (b); N01 changes no format,
so one confirmed snapshot proves load compatibility for all three heads.

**U1 resolved (2026-10-03).** The user stated that no Delivery work runs until the programme is
finished, so live state is static. Each phase takes its own fresh isolated copy at closeout (option
a) without a further confirmation; the agent records the live `delivery_health` result and that no
claim exists before copying.
