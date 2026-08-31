# Current-Only Erasure Plan

> **Owning task:** none - project-wide legacy and migration erasure planning
> **Date:** 2026-08-28
> **Question:** What can OwlBear erase now that the product supports only the current authority,
> runtime, and artifact formats, with no legacy, migration, or backwards-compatibility contract?
> **Status:** Revised after a fresh, unconfigured Claude Opus 5 challenge; Slice 1 is implemented
> and committed separately. Remaining slices are proposed only.

## 1. Context And Question

OwlBear has completed several transitions into the current Delivery, Cockpit, Knowledge, Memory,
and agent-ecosystem shape, but the repository still contains both current implementation and
transition machinery. The current product policy is deliberately stricter: there is only one present
contract. Old workspaces, old runtime schemas, retired target stores, historical completion paths,
migration journals, and compatibility aliases are not supported inputs.

The decision matters because the remaining transition code has real operational consequences. It
keeps old paths writable or readable, expands public models and MCP contracts, preserves obsolete
tests and setup instructions, and makes it difficult to tell whether a file is current authority or
historical evidence. The plan must therefore identify the complete removal graph, not only delete
the two Delivery journals discussed previously.

The target state is:

- Current source formats are the only accepted persisted formats.
- Current `.owlbear/delivery/runtime/**` state is authoritative; old roots are absent, not migrated.
- Normal startup does not inspect or repair old paths.
- Current crash recovery, atomic transactions, claim fencing, receipts, and user-controlled
  correction remain intact.
- Historical documentation and archives are removed from the working product tree rather than
  presented as supported history.
- Present-day platform support, database evolution needed by current installations, and browser
  test prerequisites remain unless separate evidence changes those policies.

The implementation is intentionally staged. The current checkout has four active managed Change
worktrees, including `delivery-capacity-consolidation`, so a destructive runtime reset is not part
of the first implementation slice. The current-only policy authorizes erasing historical product
compatibility, but it does not by itself authorize discarding active Changes, unmerged commits, or
completion receipts.

## 2. Sources Studied

| Source | Load-bearing fact | Evidence limit |
| --- | --- | --- |
| [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | `PortfolioCoordinator` now owns `runtime/coordination/changes`, `capacity-ledger.json`, and current writer custody, but still contains `_legacy_coordination_root`, `_legacy_ledger_path`, `_migrate_legacy_coordination()`, and `_migrate_legacy_ledger()` for old runtime names. | Proves the old-name shim is live code; it does not prove whether any external consumer still requires it. The user decision in this task supplies the current-only policy. |
| [`runtime_transaction.py`](../../serve/delivery/src/owlbear_delivery/runtime_transaction.py) | `RuntimeTransaction` publishes recoverable YAML manifests under `transactions/`, while `_migrate_legacy_directory()` still accepts `.runtime-transactions`. | Current transaction recovery is required; only the old-directory migration branch is removable. |
| [`delivery_migration.py`](../../serve/tools/src/owlbear_tools/delivery_migration.py) and [`delivery_integration_retirement.py`](../../serve/tools/src/owlbear_tools/delivery_integration_retirement.py) | The tools move `.owlbear/target` and `.owlbear/worktrees`, archive them under `.owlbear/legacy/delivery-state-migration`, journal interruption in `migration.json` and `integration-retirement.json`, and retire old Integration state. | Proves an explicit one-way migration/retirement subsystem exists. It does not prove all live installations have already been reset; the current-only decision means reset is a prerequisite to deletion. |
| [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py) | Startup rejects migration and retirement journals and nonempty old Delivery roots before composing current owners. | These checks are only useful while old-state recovery is supported; current startup validation itself remains required. |
| [`completed_history.py`](../../serve/delivery/src/owlbear_delivery/completed_history.py) | `CompletedHistoryCatalog` combines current completion receipts with `LegacyCompletedChangeRecord`, reads `.owlbear/legacy/completed`, and traverses a configured `legacy_source_ref`. | Receipt-backed current history must remain; the legacy branch and its public union can be removed only after archived records are intentionally discarded. |
| [`delivery_runtime.py`](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) and [`delivery_contract_discovery.py`](../../serve/delivery/src/owlbear_delivery/delivery_contract_discovery.py) | Current frontier parsing accepts schema versions `2` through `16`, transforms schema `1`, rejects legacy Integration completion/finalization, and exposes `DeliveryRuntimeMigrationError`. | Current schema `17` and current discovery diagnostics remain. The old-format branches can be removed after current state is reinitialized. |
| [`target_authority.py`](../../serve/delivery/src/owlbear_delivery/target_authority.py), [`target_admission.py`](../../serve/delivery/src/owlbear_delivery/target_admission.py), and [`target_runtime.py`](../../serve/delivery/src/owlbear_delivery/target_runtime.py) | The Target-era kernel is isolated in its own modules. The current source-bound `DeliveryAuthorityRegistry`, `DeliveryAdmission*` models, and exception hierarchy moved to `delivery_admission.py` in `38806a2e5`. | The split is complete. Remove the Target-era modules only as a later, separately validated deletion after import, public-contract, and test inventory. |
| `snapshot.py` (removed in Slice 1) | `LegacySnapshot*`, `LegacyDisposition`, and descriptor-safe inventory/publication implemented immutable snapshots of old stores; local import search found only the package re-export and `test_snapshot.py`. | This was migration/data-preservation machinery, not current transaction recovery. It was the smallest independently credible deletion slice and is now implemented. |
| [`__init__.py`](../../serve/delivery/src/owlbear_delivery/__init__.py) | The package root exports current admission from `delivery_admission.py` and the retained Target-era APIs separately. | Export removal must follow implementation removal and MCP/Cockpit contract updates. |
| [`setup/init.py`](../../setup/init.py), seed templates, and setup guides | Setup removes old ignore lines, preserves old stores, seeds old-path exclusions, and documents `migrate-delivery-state` recovery. | Setup remains current; only old-state preservation, cleanup, and migration instructions should be removed. |
| [`serve/tools/pyproject.toml`](../../serve/tools/pyproject.toml) and [`serve/tools/README.md`](../../serve/tools/README.md) | The tools package registers and documents `migrate-delivery-state` and `retire-delivery-integration`. | Other index, quality, and dependency tools are current and remain. |
| [`serve/cockpit/README.md`](../../serve/cockpit/README.md), Delivery MCP models/server, and Cockpit tests | Current-facing docs and transport surfaces expose Integration attention and completed-history variants. Integration attention is produced by current publication/sync paths and its tools are declared by current agents and skills. | Keep the Integration attention model and its two tools as current operations. No replacement is planned; only the misleading old classification needed removal. |
| `snapshot.py` (removed in Slice 1) and [`runtime_transaction.py`](../../serve/delivery/src/owlbear_delivery/runtime_transaction.py) | Snapshot publication and runtime transactions both used careful path, digest, fsync, and interruption handling. | Removing the snapshot subsystem does not justify removing current transaction safety; the transaction module remains current. |
| [`serve/knowledge/`](../../serve/knowledge/) and [`serve/memory/`](../../serve/memory/) | Database setup contains schema evolution/backfill behavior for current local stores. | A schema upgrade from an installed current database is not automatically backwards compatibility; remove only branches proven unreachable by current storage creation and supported upgrade policy. |
| `serve/cockpit/web/scripts/run-e2e*.mjs`, Playwright config, and setup docs | Chromium and PDS checks support the current browser test/toolchain. | These are present-day environment compatibility and remain outside this erasure unless a separate browser policy changes. |
| Live checkout and Git history | `HEAD` includes the current runtime-path work and currently has four managed Change worktrees with unmerged commits. This checkout now contains canonical `coordination/changes`, `transactions`, and `capacity-ledger.json` state; the old runtime names are absent, while `.owlbear/legacy` still contains 3,200 tracked files. | The path shims have run here, but other installations may still need a deliberate current-state decision. Verify canonical state before removing them; do not reset active Changes as an implicit cleanup step. |

No external source was needed. The question is answered by the repository's local ownership graph
and the explicit current-only product policy.

## 3. Analysis

### 3.1 Erasure boundary

The word “legacy” currently covers three different things. They must be treated differently:

| Category | Examples | Current-only action |
| --- | --- | --- |
| Historical product-state compatibility | `.owlbear/legacy/**`, `.owlbear/target/**`, old completed packages, schema `1-16` frontier adapters, Target-era runtime | Erase after a deliberate state reset and caller/test removal. No replacement reader is needed. |
| One-way migration and retirement machinery | `delivery_migration.py`, `delivery_integration_retirement.py`, journals, old-path setup cleanup, migration CLI and tests | Erase as part of the same current-only cutover. Do not leave a partial command or journal reader. |
| Current durability and environment support | `RuntimeTransaction` current `transactions/`, current receipts, current frontier/claim recovery, Knowledge/Memory current schema upgrades, Chromium/PDS checks, Python support floor | Retain. These solve present failures or current installation requirements, not old product-state compatibility. |

The current-only policy changes the handling of old state from “migrate or preserve” to “reject as
unsupported and require a fresh current workspace.” That is a product decision with destructive
implications. The cutover must be explicit and observable; a silent startup deletion would make data
loss hard to attribute. It is not, however, a prerequisite for deleting an already-proven orphaned
module such as `snapshot.py`, nor does it authorize deleting four active Changes.

### 3.2 Erase now: historical repository artifacts

The entire `.owlbear/legacy/` tree is a candidate for deletion. The live checkout contains roughly
3,200 files:

| Subtree | Approximate files | Meaning | Action |
| --- | ---: | --- | --- |
| `.owlbear/legacy/target-cutover/` | 2,431 | Retired Kanban/cutover authority and task history | Delete |
| `.owlbear/legacy/target-cutover-incidents/` | 327 | Incident snapshots and reappeared-source evidence | Delete |
| `.owlbear/legacy/briefs/` | 225 | Superseded drafts and ideation artifacts | Delete |
| `.owlbear/legacy/target-delivery-cutover-runtime/` | 134 | Retired target runtime snapshots | Delete |
| `.owlbear/legacy/delivery-state-migration/` | 39 | Archived old Delivery target state | Delete |
| `.owlbear/legacy/openspec-final/` | 23 | Historical OpenSpec publication | Delete |
| `.owlbear/legacy/completed/` | 14 | Old completion packages | Delete |
| Remaining diagrams/design archives | 7 | Historical diagrams and cutover design | Delete |

The archive is not current authority: active source uses `.owlbear/delivery/packages/**`, current
runtime state, current completion receipts, and current GitHub evidence. The archive should not be
copied elsewhere by the implementation; deleting it is the requested policy. Git history remains
the repository's ordinary recovery mechanism if the user later changes this policy.

Also remove the standalone historical prompt and research artifacts whose only purpose is to
coordinate or explain old systems:

- `share/prompts/legacy-audit.prompt.md`;
- legacy/migration-specific research records such as `legacy-kanban-md-exe-cleanup.md`,
  `1414-legacy-audit-prompt.md`, `mcp-knowledge-legacy-removal-b2.md`, and
  `knowledge-legacy-deletion.md`;
- any current research document sections that describe old paths as supported behavior.

Not every historical word in `.owlbear/research/` warrants deletion: research that explains a
current design decision can be rewritten to describe only the current model. The implementation
task should delete obsolete records, not mass-rewrite unrelated durable research.

### 3.3 Erase after current-state reset: Delivery filesystem state

Before deleting path-migration code, perform one explicit current-only reset from the canonical
workspace root. This is not a migration and must not preserve an archive. It is a separate,
destructive operation and is not required for Slice 1 or the other source-only slices that do not
touch live runtime state:

1. Stop Delivery MCP, Cockpit, and any other process using the workspace.
2. Capture the names and status of current Changes, then obtain explicit user confirmation that all
   current runtime state, in-progress claims, worktrees, receipts, and old archives may be removed.
3. Remove `.owlbear/delivery/runtime/**`, `.owlbear/delivery/worktrees/**`, `.owlbear/target/**`,
   `.owlbear/worktrees/**`, `.owlbear/legacy/**`, and any migration/retirement staging directories.
4. Recreate only current empty roots through setup/current initialization: tracked `host.json`,
   current `config.json`, `packages/`, `runtime/`, and no active claims, transactions, worktrees, or
   completion receipts.
5. Verify a new current Delivery application starts and creates only the current path set.

The reset must remove old runtime names rather than invoke the current compatibility shims. In
particular, erase `capacity.json`, `.runtime-transactions`, `claims/changes`, and all archived
`target-runtime` data. Current runtime state after reset is `coordination/changes`, `transactions`,
`capacity-ledger.json`, `changes`, `claims` lock namespaces, `publications`, and `completions`.

### 3.4 Erase current source compatibility branches

After the reset, remove the old-state branches in dependency order.

#### Phase A: path and transaction shims

In `serve/delivery/src/owlbear_delivery/change_workspace.py`:

- remove `_legacy_coordination_root`, `_legacy_ledger_path`,
  `_migrate_legacy_coordination()`, and `_migrate_legacy_ledger()`;
- remove conflict constructors and diagnostics that exist only for old/new filename coexistence;
- keep `CapacityLedger` only if the current writer ledger remains part of the current contract; if the
  current capacity ledger is also removed by a separate capacity decision, delete its model and
  tests together;
- make `PortfolioCoordinator` initialize only `coordination/changes` and
  `capacity-ledger.json` (or the final current capacity design).

In `serve/delivery/src/owlbear_delivery/runtime_transaction.py`:

- keep current `transactions/{transaction-id}.yaml` publication, replay, abort, locking, digest,
  and path validation;
- remove `_migrate_legacy_directory()` and all `.runtime-transactions` handling;
- keep manifest schema validation for any format still emitted by the current code. If current
  manifests are deliberately frozen at one schema, simplify the v1/v2 branch only after checking
  every current participant kind.

This phase is gated, not first. The active checkout currently has four live coordination records in
the old location and a live old capacity ledger; first observe or explicitly reset those records,
then remove the shims in a separate scoped commit. A concurrent `delivery-capacity-consolidation`
change also owns nearby capacity behavior and must be coordinated before editing that file.

#### Phase B: old Delivery migration and Integration retirement

Delete the one-way tools and registrations after confirming the current-only reset has completed:

- `serve/tools/src/owlbear_tools/delivery_migration.py`;
- `serve/tools/src/owlbear_tools/delivery_integration_retirement.py`;
- their `serve/tools/tests/` suites;
- `migrate-delivery-state` and `retire-delivery-integration` entries in
  `serve/tools/pyproject.toml` and any command/help registries;
- migration/retirement sections from `serve/tools/README.md`, setup guides, and operator docs;
- `migration.json`, `integration-retirement.json`, and `.runtime-migration`/
  `delivery-integration-retirement` ignore rules.

Remove loader checks for interrupted migration/retirement journals and old `.owlbear/target` /
`.owlbear/worktrees` roots. Replace them with current-root validation only. A current startup should
not know that those paths ever existed.

#### Phase C: historical completed-history reader

In `completed_history.py`:

- remove `_LEGACY_COMPLETED_ROOT`, `_HISTORICAL_COMPLETED_ROOT`, `_LegacyTaskResult`,
  `_LegacyRuntimeBinding`, `_LegacyRuntimeFrontier`, `_LEGACY_RESULT_HISTORY`, and
  `_verify_legacy_runtime_capture()` / `_require_legacy_capture_shape()`;
- remove `LegacyCompletedChangeRecord` and change `CompletedChangeRecord` to the current
  receipt-backed record only;
- replace `legacy_source_ref` with the current receipt/history source contract, or remove it if the
  current receipt catalog does not require a Git source ref;
- remove Git traversal for `.owlbear/legacy/completed` and old completion paths;
- retain bounded pagination, search, missing/malformed/stale diagnostics, and receipt-set cursor
  validation for current completion receipts.

Update Cockpit API models and UI projections that expose `historical_completion_locator` or
`record_kind = legacy-package`. Current completed history should show current receipt identity and
acceptance evidence only.

#### Phase D: frontier and dormant target-era compatibility

In `delivery_runtime.py` and discovery:

- make `parse_delivery_frontier()` accept only `_FRONTIER_SCHEMA_VERSION` (`17` at the time of
  this audit);
- remove `_PREVIOUS_FRONTIER_SCHEMA_VERSIONS`, `_CHECKPOINT_BACKFILL_SCHEMA_VERSIONS`,
  `_normalize_frontier_schema()`, `_normalize_schema_one_bindings()`,
  `_normalize_legacy_integration_completion()`, `_reject_legacy_finalization()`,
  `_backfill_checkpoint_state()`, `DeliveryRuntimeMigrationError`, and migration-only arguments
  such as `migration_reviewed_head` and `require_checkpoint_backfill`;
- preserve current frontier validation, claim identity, lifecycle transitions, and exact recovery.

The current-admission split is complete in `38806a2e5`. `target_admission.py` is now Target-only;
inventory its remaining consumers before deleting the dormant Target-era modules:

- `target_authority.py` target semantic model extras that are not used by current Delivery;
- the target-era remainder of `target_admission.py`: target admission registry, candidate/challenge,
  target receipts, and target runtime admission APIs;
- `target_runtime.py` TargetJob/TargetAttempt/TargetRequest/TargetReceipt and its runtime kernel;
- associated `TargetAdmission*` and `TargetRuntime*` exports, MCP protocol types, tests, fixtures,
  and package-boundary/index entries.

This phase must be evidence-led. Current Delivery uses `target_contract.py`, `delivery_runtime.py`,
`delivery_admission.py`, and `PortfolioApplication`; the Target-era modules remain public exports
and test subjects. Do not delete them based on filenames alone; first prove no current MCP/Cockpit
route or public import relies on them, then remove the exports and rewrite the Target-era fixtures.

#### Phase E: immutable old-store snapshot subsystem

The orphaned snapshot slice was implemented in `bb2eeb33a` and its plan references were repaired in
`ad4a7cdeb`. Local import inventory found no active consumer beyond the removed package re-export
and test. No further snapshot work is planned; this did not touch live runtime state.

Do not remove `runtime_transaction.py`, `storage_io.py`, or current receipt stores. Snapshotting an
old tree and recovering a current interrupted transaction solve different problems.

### 3.5 Setup, seed, lint, and generated-surface cleanup

Update the current setup contract after source deletion:

- `setup/init.py`: remove `_RETIRED_OWLBEAR_GITIGNORE_LINES`, `retired_lines`, old-path cleanup,
  “existing legacy stores remain untouched,” and migration-specific initialization branches;
- `seed/.owlbear/.gitignore` and root `.owlbear/.gitignore`: remove old target/worktree,
  migration-journal, retirement-journal, and legacy archive rules; retain current runtime and
  worktree ignore rules;
- `setup/setup-guide.md`, `setup/sharing-guide.md`, and `setup/operating-owlbear.md`: remove
  migration troubleshooting, legacy inventory, Integration-retirement, old target/worktree, and
  historical compatibility instructions; document the current paths and the explicit destructive
  reset prerequisite where appropriate;
- remove tests that assert old ignore-line cleanup or legacy-state preservation, replacing them with
  current initialization assertions;
- remove `.owlbear/legacy`, `.owlbear/target`, and migration entries from Markdownlint, yamllint,
  ESLint JSON, pre-commit, and MegaLinter exclusions only when the paths themselves are gone;
- regenerate `.owlbear/doc-index.md`, `.owlbear/py-index.md`, and `.owlbear/ts-index.md` after
  source/docs deletion. Generated indexes are outputs, not hand-edited authority.

Keep exclusions for current generated runtime, node modules, scratch, test results, and current
generated PDS assets. Removing a legacy exclusion is not permission to lint historical artifacts
before they are deleted.

### 3.6 Whole-project domain review

The user asked for the whole project, so each domain needs an explicit disposition:

| Domain | Candidate | Plan |
| --- | --- | --- |
| Delivery | Migration/retirement modules, old paths, old ledger/coordination shims, schema adapters, historical completion reader, dormant Target-era kernel, snapshot subsystem | Erase in Phases A-E after current-only reset and caller inventory. |
| Delivery runtime | Current `transactions/`, atomic recovery, current coordination, claims/locks, publications, completions, current frontier and claim fencing | Retain. These are present-day durability and lifecycle behavior. |
| Delivery docs/research | Old-path support prose, migration plans, historical compatibility claims | Delete obsolete records or rewrite current design docs to remove support claims. Preserve only research that explains current behavior. |
| Delivery setup/seed | Old root cleanup/preservation and migration instructions | Remove after the reset; keep current config, host baseline/local overlay, and current ignores. |
| Cockpit | Misleading Integration-attention labels, legacy completed-history fields, old target-context routes if any | Remove only the historical completed-history variants with their core/API types. Keep current Integration attention, operator recovery, backward outcome movement, browser/PDS behavior, and receipt-backed completion. |
| Delivery MCP | Integration attention and repair tools are declared by current agents and skills and are backed by current runtime state. | Keep as current operations; remove the misleading historical classification. No replacement is planned. |
| Knowledge | Existing-database schema evolution/backfill such as `vectors_synced` and pending-delete state | Retain until storage policy proves all current databases are freshly created. These are current installation upgrades, not old product-state compatibility. Then simplify in a separate data-schema task if desired. |
| Memory | Schema/version fields and current score/state migrations | Retain unless a focused source/test audit proves a branch handles a retired product format rather than current database durability. Do not delete based on the word “migration” alone. |
| Browser/PDS | Chromium installation/checks, Playwright compatibility config, PDS asset/runtime checks | Retain. These describe current supported tooling and environment compatibility, not historical OwlBear state. |
| Python/runtime floor | Python 3.12/3.14 declarations and checks | Retain. This is a current supported-version policy. |
| Agent ecosystem | `legacy-audit.prompt.md` and instructions that route old migration workflows | Delete obsolete prompt/workflow assets; retain current structural, review, and recovery instructions. |
| Historical archive | `.owlbear/legacy/**`, historical fixtures and cutover incidents | Delete under the explicit current-only policy, but separate the 3,200-file archive deletion from source/API changes. Do not archive it into a second path. |

## 4. Recommended Implementation Order

1. **Authorize and record the destructive boundary.** Confirm separately whether active Changes,
  current receipts, and two legacy completed-history records may be discarded. “Only now” does not
  infer that authorization for active work.
2. **Delete the provably orphaned source slice.** Remove `snapshot.py`, its test, exports, and the
  stale write-guard entry. This is the smallest independently credible first commit and does not
  touch runtime state.
3. **Delete historical repository data.** Remove `.owlbear/legacy/**`, legacy prompts, and obsolete
   migration research records. This prevents the source and docs from continuing to advertise old
   authority.
4. **Delete migration/retirement tools and setup guards.** Remove CLI registrations, journals,
   staging paths, old-root loader checks, and setup/seed cleanup rules together.
5. **Verify or reset live runtime state.** Observe that canonical coordination/ledger/transaction
  paths contain the intended current records, or perform the explicit destructive reset. Do not run
  this step while active Changes are still required.
6. **Remove runtime path shims.** Delete old ledger/coordination and transaction-directory migration
   code; validate only current paths.
7. **Collapse current APIs.** Remove historical completed-history records, migration-specific frontier
  parsing, and dormant Target-era APIs after import inventory. Keep current Integration attention
  unless a replacement is designed.
8. **Clean all callers and proof.** Update MCP/Cockpit models/routes, tests, fixtures, docs, package
   exports, package boundary checks, and generated indexes.
9. **Review Knowledge/Memory separately.** Retain current database upgrade paths unless a focused
   audit proves they are old product-format compatibility. Remove only proven dead branches.
10. **Run current-only verification.** Prove no old path, symbol, command, public field, or archive
   remains, then run current package suites and initialization from a clean temporary project.

## 5. Acceptance Scenarios And Validation

### Current-only behavior

1. A fresh setup creates only current config, host, package, runtime, lock, transaction, publication,
   completion, and worktree roots.
2. After the explicit reset and source cleanup, startup does not inspect or mutate `.owlbear/legacy`,
   `.owlbear/target`, `.owlbear/worktrees`, `migration.json`, `integration-retirement.json`,
   `capacity.json`, `.runtime-transactions`, or `claims/changes`; those paths are unsupported and
   absent.
3. Current coordination is written only to `runtime/coordination/changes/{change-id}.json`.
4. Current transaction manifests are written only to `runtime/transactions/{transaction-id}.yaml`
   (and any explicitly injected current store root that is still part of the current design).
5. After frontier cleanup, current frontier parsing rejects schema versions other than the current
  version.
6. Current completed history contains only receipt-backed records and no historical locator fields.
7. MCP and Cockpit expose only the intentionally retained current Integration attention operations
  and no historical completed-record variants after their separate API decision.

### Safety that must survive

8. Interrupted current transactions replay or abort deterministically, preserving path containment,
   digest validation, locking, and cleanup.
9. Current claim recovery preserves exact identity, dirty/mismatched worktree custody, and current
   writer fencing.
10. Current completion receipts, publication observations, and acceptance evidence remain readable.
11. Knowledge and Memory current stores continue to open and maintain their current schema policy.
12. Chromium/PDS current tests and Python supported-version checks remain unchanged unless separately
   re-scoped.

### Structural proof

13. After all slices, repository search finds no active references to `delivery_migration`,
   `delivery_integration_retirement`, `migrate-delivery-state`, `retire-delivery-integration`,
   `.owlbear/legacy`, `.owlbear/target`, `.owlbear/worktrees`, `migration.json`,
   `integration-retirement.json`, `capacity.json`, `.runtime-transactions`, `claims/changes`,
   `LegacyCompletedChangeRecord`, `LegacySnapshot`, `DeliveryRuntimeMigrationError`, or deleted
   Target-era APIs outside intentionally retained Git history or unrelated third-party dependencies.
14. Package exports, MCP schemas, Cockpit schemas, setup templates, command help, and generated
   indexes contain only current symbols and paths.
15. The current-only reset and fresh setup test pass without creating an archive or migration journal.

### Suggested validation commands

```text
uv run pytest serve/delivery/tests serve/delivery-mcp/tests serve/tools/tests tests -q --tb=short
uv run ruff check serve setup tests
uv run ruff format --check serve setup tests
uv run git diff --check
uv run test-root
uv run indexes <project-root>
```

Use the repository's routed `uv run test` command for the complete current suite. Run Cockpit's
maintained Vitest/build/E2E gates when its API or frontend surfaces change. Run Knowledge and Memory
database tests if their schema code is touched. Do not use a passing grep as proof that current
runtime safety survived; pair structural absence checks with package behavior tests.

## 6. Risks, Decisions, And Limits

| Risk or decision | Required treatment |
| --- | --- |
| Destructive reset loses current claims, worktrees, receipts, and unfinished Changes | Require explicit user confirmation and stop all clients before reset. The current checkout has four active Changes, so reset is not part of the first slice. |
| Deleting `.owlbear/legacy` removes the only checked-out copy of historical decisions and incidents | Accepted by the current-only policy. Git history is the only remaining recovery source. |
| `target_admission.py` mixes current and dormant APIs; deleting it wholesale breaks current admission | Split current admission first, then run import, package-boundary, MCP, Cockpit, and full Python tests before deleting the target-era remainder. |
| Frontier/transaction schema simplification may reject current files generated before the reset | Reset current runtime and regenerate only current artifacts first; confirm no current branch or package embeds an older schema. |
| Knowledge/Memory database migrations may be needed by installed current users | Treat database opening/upgrades as current installation durability. Do not erase without a separate database inventory and explicit reset policy. |
| “Compatibility” can describe browser, Python, PDS, or dependency support | Keep present-day environment compatibility unless the user changes those support policies. This plan targets historical OwlBear product state. |
| Generated indexes and linter exclusions can retain stale names | Regenerate indexes after deletion and run exact path/symbol audits across source, setup, tests, docs, and seeds. |
| Existing current runtime has old residue and four active worktrees | Observe or reset it explicitly before removing path shims; do not silently discard active work. |

Confidence is high that `snapshot.py` is removable now and that Delivery migration/retirement and
archive surfaces are removable after an explicit current-state decision. Confidence is medium for
deleting Target-era modules, historical completed records, and frontier/schema branches until their
complete import and state inventories are executed. Confidence is low for any deletion that would
alter present-day browser, Python, or database support without a separate product decision.

The most important boundary is simple: “only now” authorizes deleting historical product-state
compatibility, not deleting the mechanisms that make the current system crash-safe.
