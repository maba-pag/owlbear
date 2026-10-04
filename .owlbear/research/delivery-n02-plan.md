# Delivery N02 — Controller Pinning, Versioned State and Migration Core

> **Package:** N02 of the [execution plan](delivery-redesign-execution-plan.md#n02--controller-pinning-versioned-state-and-migration-core).
> **Planned on:** `origin/dev` `42144f9dc` (N00-C merged; Python 3.14.8; uv-locked Pydantic 2.13).
> Live controller observed read-only: main checkout on `delivery-live` at `881b500fe` (D03).
> **Status:** approved: plan gate `plan-sound` in round 4 of fresh GPT-6.1 Sol challenges (2026-10-03).
> D9 merged under the user's overnight authorization of 2026-10-03 ("do whatever is necessary to keep
> work going … merging") and was confirmed on 2026-10-03 (listed to the user without objection).
> U1 (a), U2 (a) and U3 (default) were decided on 2026-10-03.
> Product code is unchanged by this phase.

## 1. Contract

### 1.1 Result

- Every persisted Delivery record family is registered once, with its path, owner model, mutability
  class, current version and accepted read versions. Startup classifies on-disk versions with raw,
  bounded reads and refuses unsupported, unknown or newer (downgrade) state before any typed read,
  remote bootstrap or write.
- Frontier JSON has one strict canonical parser; tests read frontiers strictly again (#215).
- Registered migrations run copy-first and fenced (propose into staging outside authoritative state →
  apply under the exclusive controller lock → offline verify), with a backup, a journal that
  replays at every durable boundary, and refusal of unknown corruption. Normal start accepts only
  a verified (or absent) migration journal.
- Remote Git is bounded and noninteractive, with typed unknown-write readback (#220). Target-sync
  fetch no longer runs under the portfolio-wide lock (L5).
- This repository's live Delivery MCP and Cockpit run an immutable, pinned controller release
  (per [U1](#u-decisions) (a), decided 2026-10-03). Merges into `dev` no longer change live behavior. Upgrades
  follow a rehearsed drain → stop → preflight → backup → migrate → switch → restart → verify
  procedure.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | Pin one controller executable and schema capability set per active session; the dev checkout never hot-replaces it | Programme §11.3; WP6 step 3; P20 |
| R2 | Unsupported or newer state is refused before it is read or mutated | §11.3; WP6 step 5; V24; V20 refusal half |
| R3 | Registered, versioned migrations; no runtime compatibility paths by default | §11.3; P19 |
| R4 | Migration is fenced and copy-first, with backup and replay at every durable boundary; restart reaches the old version or the replayed new coherent version | V21; P19 |
| R5 | Unknown corruption and missing user-confirmation provenance are preserved and diagnosed, never rehashed or blessed | V20; §11.1; WP6 risk |
| R6 | Upgrade with active work drains or fences actions; invalid upgrade is refused or safely reverted; existing records resume | V24; WP6 steps 3–5 |
| R7 | One canonical strict frontier round-trip; malformed, extra or identity-mismatched state still rejected | #215 |
| R8 | Every remote Git read/write is bounded, noninteractive, typed; uncertain writes are read back before retry; locks stay usable after timeout | #220 |
| R9 | An unreachable remote cannot stall all target syncs; current exclusion of local state is preserved | L5 (programme Departure table, D07) |
| R10 | Delivery core does not depend on tools; offline diagnosis stays a stdlib bootstrap | WP6 proof note; `tests/test_package_boundary.py` |
| R11 | LC gate: load form for N02-A; full form from N02-B; from N02-D it is the upgrade rehearsal | Execution plan §1.3, §5 N02 |
| R12 | Absorbs the live `frontier-serialization-contract` Change's scope (PR #314); that Change is abandoned in N10-M | Execution plan §2.6, §5 N10 |

### 1.3 Invariants

- **I1 Gate first.** On every controller start (MCP, Cockpit, application loader callers), the
  controller lock (I5) and then the capability scan run immediately after path derivation, before
  `_validate_git_config`, `_load_host_config`, `_bootstrap_remote_state`, contract discovery and
  composition. Typed record
  parsing and every write (remote restore, frontier canonicalization in `DeliveryRuntime._read`,
  retry-ledger import in `PortfolioApplication.__init__`) happen only after it passes.
- **I2 No silent format change.** A model change that alters a registered family's JSON schema
  without a version bump and a registered read-upcast or rewrite fails a test. D03 baseline records
  round-trip byte-identically through their owner parser (the 7c05d377 `_omit_when_none` lesson).
- **I3 Stored identity is never recomputed over altered content.** Records whose ID is a digest of
  their own bytes (receipts, snapshots, packages) are immutable on disk: schema evolution is a pure
  read-upcast that verifies the stored ID over the stored bytes, derives a *new* ID for the upcast
  form and records the stored ID as provenance (precedent: `parse_delivery_state_snapshot`,
  `delivery_state.py:835-861`, derives a new `snapshot_id` and sets `migrated_from_snapshot_id`).
  Only mutable families may be rewritten, and only by a fenced migration.
- **I4 Historical and opaque records are never parsed by the gate or a migration.** Revision
  records, preservation objects and restoration stages keep shape-only inspection, as in
  `delivery_diagnostics`.
- **I5 One fence, from N02-A.** Every N02-A-or-later controller holds the workspace controller lock
  `runtime/controller.lock` shared (`flock LOCK_SH`, non-blocking) from before the gate until the
  application closes or the process exits, and refuses `controller-fenced` without reading or
  writing when it cannot. Migration `apply`, `resume`, `verify` and `abort` (N02-B) and upgrade
  preflight, `switch` and `prune` (N02-D) take it exclusively and non-blocking. The D03 controller
  does not take it, so the first upgrade also verifies that no controller process runs.
- **I6 Code origin follows the pin.** On a pinned workspace, a controller whose code is not the
  pinned release refuses to start (N02-D). Unpinned workspaces (tests, disposable portfolios,
  consumers until N08-C) keep today's behavior.

### 1.4 Persisted record families

Verified against source at `42144f9dc`, the offline inspector, and live state read-only (local
`.owlbear/delivery` and `origin/owlbear/delivery-state` at `228956b2f`). "Live" lists observed
counts and versions. Mutability: **M** mutable (rewrite allowed by migration), **R** append-only or
self-identified receipt (read-upcast only), **H** historical, **O** opaque, **T** tracked in Git
(rewrite is a working-tree edit; prefer read tolerance), **L** lock or transient. Tree hashes in
this plan exclude L-class files, since every controller start creates `runtime/controller.lock`.

| Family (registry ID) | Path under `.owlbear/delivery/` | Owner model (module) | Version | Class | Identity over bytes | Live |
| --- | --- | --- | --- | --- | --- | --- |
| `config` | `config.json` | `DeliveryStartupConfig` (loader); also `owlbear_tools.delivery_config` | 2 | T | none | 1 × v2 |
| `host` | `runtime/host.json` | `DeliveryHostConfig` (loader) | 1 | T | none | 1 × v1 |
| `host_local` | `runtime/host.local.json` | `_DeliveryHostConfigOverrides` (loader) | 1 | M | none | absent |
| `coordination` | `runtime/coordination/changes/<change>.json` | `ChangeCoordination` (workspace) with nested target-sync, adoption, promotion, baseline, out-of-band, quarantine receipts | 1 (nested receipts 1–2) | M | nested receipts self-identified | 3 × v1 |
| `frontier` | `runtime/changes/<change>/frontier.json` | `DeliveryFrontier` (runtime) with nested bindings, finalization (v2), disposition, deferral, abandonment, publication history | 18; reads 17 (canonicalized and rewritten by `DeliveryRuntime._read`) | M | nested receipts self-identified | 3 × v18 |
| `contract` | `runtime/changes/<change>/contract.json` | `DeliveryContract` (target_contract) | 2 | R | contract digest | 3 × v2 |
| `admission` | `runtime/changes/<change>/admission.json` | `DeliveryAdmissionReceipt` (admission) | 1 | R | `receipt_id` | 3 × v1 |
| `state_publication` | `runtime/changes/<change>/state-publication.json` | `DeliveryPendingStatePublication` (runtime) | 1 | M | none | 2 × v1 |
| `revision_record` | `runtime/changes/<change>/revisions/<id>/{contract,frontier,admission}.json` | historical copies | any | H | — | 4 files; one frontier v17 that current `parse_delivery_frontier` rejects (free-text resolution without user-confirmed provenance) |
| `result_receipt` | `…/result-receipts/<outcome>/<digest>.json` | runtime result binding | none | R | `digest` | none |
| `action_intent`/`started`/`result` | `…/action-receipts/<continue-op>/{intent,started,result}.json` | engine action receipts (application) | none | R | operation ID | none |
| `recovery_*` | `…/invocations/*.json`, `…/recovery-receipts/<id>/{intent,evidence,receipt}.json` | `RecoveryInvocation`, `RecoveryIntent`, `RecoveryEvidence`, `RecoveryReceipt`, `CompletedOutcomeRepairReceipt` | 1 | R | `*_id` | none |
| `preservation_*` | `…/recovery-receipts/<id>/preservation/{manifest.json,objects/*.raw,restoration/**}` | `WorktreePreservationReceipt` and restoration records (workspace) | 1 | R/O | `receipt_id` | none |
| `retry_*` | `…/retry-ledger/{current.json,attempts,outcomes,repair-bindings,owner-results}` | `RetryLedgerSummary` (M), `RetryAttempt`, `RetryAttemptOutcome`, `RetryRepairBinding`, `RetryOwnerResult` (R) (recovery) | 1 | M/R | `episode_id`, `binding_id` | none |
| `planning_*`, `builder_*` | `…/planning-{pause,retry}-receipts/**`, `…/builder-{invocation,plan-promotion,request-resolution}-receipts/*`, `…/builder-handoff-change-intent-receipts/<id>/{head.json,<id>.json}` | `_DeliveryPlanningPauseReplay`, `_DeliveryPlanningRetrySettlementReceipt`, `_DeliveryBuilder*` (runtime) | 1 | R (head M) | settlement/promotion/receipt IDs | none |
| `claim_issuer` | `…/claim-issuers/<attempt>.json` | `DeliveryClaimIssuer` (worker_stall) | 1 | R | none | none |
| `transaction` | `runtime/transactions/*.yaml` and nested `transactions/` under changes, packages, finalization-reports, proof-attempts | `RuntimeTransaction` manifest | 1–2 | L | — | 0 pending |
| `finalization_report` | `runtime/finalization-reports/<change>/{reports/<id>.json,current.json}` | `FinalizationReport` (R) and the `_CurrentReport` pointer `current.json` (M, replaced on each report and on retire) (finalization_reports) | unversioned: implicit baseline, covered by `format.json` (D3) | R / M | `report_id` (pointer: none) | none |
| `proof_attempt` | `runtime/proof-attempts/<change>/attempts/<id>.json` | `ProofAttempt` (finalization_reports) | unversioned: implicit baseline, covered by `format.json` (D3) | R | `attempt_id` | none |
| `finalizer_settlement` | `runtime/finalizer-settlements/<change>/<sha256(attempt_id)>.json` | `FinalizerSettlementReceipt` (finalization_reports; embeds an unversioned `FinalizationReport`), written and read by `PortfolioApplication._finalizer_settlement_receipt_path` callers [N01-A] | 1 | R | `receipt_id` | none |
| `completion` | `runtime/completions/<change>/{<id>.json,display.json}` | `CompletionEvidence`, `CompletionDisplayMetadata` (acceptance) | 1 | R | `completion_id`, `display_id` | 3 + 3 × v1 |
| `branch_publication` | `runtime/publications/change-branches/operations/<sha256(operation_id)>.json` (supersessions: `sha256("supersession:" + operation_id)`) | `_PublicationOperation`, `_SupersessionOperation` (change_publication); branch receipts are returned to the caller, not stored here | 1 | R | file name over operation ID | 13 × v1 |
| `pull_request_publication` | `runtime/publications/pull-requests/{operations,supersession-operations,summary-operations,draft-state-operations}/<change>--<op>.json` | `_DraftPullRequestOperation`, `_DraftPullRequestSupersessionOperation`, `_GeneratedSummaryOperation`, `_DraftStateOperation` (draft_pull_request) | 1 | R | file name over Change and operation ID | 13 × v1 (4 operations, 9 summary) |
| `pull_request_receipt` | `…/pull-requests/{supersession-receipts,summary-receipts,draft-state-receipts}/<change>--<op>.json` | `DraftPullRequestSupersessionReceipt`, `GeneratedPullRequestSummaryReceipt`, `PullRequestReadyReceipt`/`PullRequestDraftReceipt` (draft state) | 1 | R | `receipt_id` | 9 × v1 summary |
| `pull_request_current` | `…/pull-requests/receipts/<change>.json`, `…/publication-history/<change>.json` | `DraftPullRequestPublicationReceipt` (current, replaced on supersession), `DraftPullRequestPublicationHistory` (append-rewrite) | 1 | M | `receipt_id`, `history_id` | 3 × v1 receipts; history absent |
| `pull_request_observation` | `…/pull-requests/{check-observations,pull-request-observations}/<change>/<evidence_digest>.json` | `PublicationCheckObservationReceipt`, `PublicationPullRequestObservationReceipt` | 1 | R | `observation_id`; file named by evidence digest | 14 × v1 PR observations; check observations absent |
| `acceptance_cursor` | `runtime/claims/acceptance-reconciliation/cursor.json` | `_AcceptanceReconciliationCursor` (application) | 1 | M | none | absent |
| `package` | `packages/<change>/{manifest.json,authority.json,intent.md,design.md}` | `DesignPackageManifest` (v1); `authority.json` holds `DeliveryContract` v2 bytes or is empty for an unadmitted Design | 1 / 2 / empty | T, R | `package_id` | 9 packages; 7 × v2 authority, 2 empty |
| `snapshot` (remote) | branch `owlbear/delivery-state`: `.owlbear/delivery/state/<change>/snapshot.json` | `DeliveryStateSnapshot` (delivery_state) embedding a typed frontier | 2; reads 1 (pure upcast: new `snapshot_id`, stored ID kept as `migrated_from_snapshot_id`) | R | `snapshot_id` | 2 × v2/frontier 18; 1 × **v1/frontier 17** (`frontier-serialization-contract`) |
| locks | `runtime/controller.lock` (N02-A, I5), `**/.storage.lock`, `coordination/target-sync-lock/`, `claims/**`, `publications/pull-requests/locks/<change>/` | `storage_io.locked_roots` | — | L | — | present |
| `migration_journal` (N02-B) | `runtime/migrations/<id>/journal.json`; staging and backup outside authority in `.owlbear/delivery-migrations/<id>/` | `state_migration` journal | 1 | M | `proposal_id` | absent |

Registry hygiene (N02-A test): every `owlbear_delivery` model with a `schema_version` field is
either a family owner, nested in a registered family, or listed as non-persisted (for example the
completed-history `_Cursor` API token and `CapacityLedger` if it has no file).
`delivery-diagnose` currently versions only `config`, `frontier`, `coordination`, `snapshot`,
`host`, `host_local` and per-Change records; completions, publications, finalization reports,
proof attempts, finalizer settlements and packages are not version-checked offline today.
Unversioned families (finalization reports, their pointer, proof attempts) stay unversioned in
N02: the fingerprint test (I2) pins their schema, and any change needs a registered version and
upcast or rewrite under the format marker.

### 1.5 Interfaces and error cases

| Interface | Behavior |
| --- | --- |
| `owlbear_delivery.state_formats` (new, stdlib-only leaf, imports no Delivery module) | `FAMILIES` registry; `scan_capability(workspace_root) -> CapabilityReport` (raw `schema_version` reads with no-follow, size and entry bounds; no Pydantic, no writes, no network); `require_capability(report)` |
| `CapabilityReport` | Per record: `current`, `readable-legacy` (registered read-upcast), `migration-required` (registered rewrite, N02-B), `newer`, `unknown-version`, `unrecognized`, `unreadable`; workspace `format` (N02-B marker); safe locators only. This is the contract N08 renders in degraded Cockpit |
| `DeliveryStateVersionError(DeliveryApplicationLoadError)` | `field="state_version"`; codes `state-newer-than-controller`, `state-version-unknown`, `state-migration-required`, `state-migration-incomplete` (N02-A: any `runtime/migrations/` journal; N02-B: any journal not `verified`), `controller-not-pinned` (N02-D) |
| Loader | `load_delivery_application` takes the controller lock and runs the gate first (I1, I5); lock failure raises a `DeliveryApplicationLoadError` with code `controller-fenced`; a refused load releases the lock. MCP `app_lifespan` and Cockpit `load_target_context` surface the typed refusal and stop, as today for load errors; they also check the raw config version before their typed config parse. `DeliveryCheckpointSupervisor` is constructed only after a passed load, so it never runs on refused state |
| Remote snapshots | A snapshot newer than supported yields health reason `remote-state-version-unsupported` for that Change: no restore, no publication, not eligible for `repair_quarantined_snapshot` (today an unknown version becomes `snapshot-invalid` and is repairable — an older controller could overwrite a newer host's snapshot) |
| `parse_delivery_frontier(content)` | One boundary: JSON object and version check, legacy 17 key rewrite, `DeliveryFrontier.model_validate_json(..., strict=True)`, canonical bytes. Same pattern for `parse_delivery_state_snapshot` and the other `strict=False` readers listed in [N02-A](#32-n02-a--registry-gate-and-strict-frontier) |
| `owlbear_delivery.state_migration` (N02-B, below composition) | `propose`, `apply`, `resume`, `verify`, `abort`; CLI `delivery-migrate` in `owlbear_tools`. `verify` is the offline verifier: it never starts the normal controller (no MCP, Cockpit, remote bootstrap or supervisor) |
| `owlbear_delivery.remote_git` (N02-C) | `run_remote_git(repo, args, kind, timeout)` with `kind` read or write; typed `RemoteGitTimeout`, `RemoteGitFailed`, `RemoteGitWriteUnknown`; readback helpers |
| `delivery-controller` (N02-D, `owlbear_tools`) | `install`, `pin`, `list`, `preflight`, `switch`, `verify`, `prune` |
| `delivery-lc` (N02-B, `owlbear_tools`) | `prepare`; `run --candidate SHA --form FORM` with `FORM` load or full; `compare` |

### 1.6 Existing owners to reuse

- `delivery_diagnostics` (stdlib bootstrap): its version tables stay a mirror of the registry,
  pinned by a parity test (it may not import Delivery: `test_delivery_diagnostics_is_a_stdlib_bootstrap`).
- `RuntimeTransaction` (atomic replace, manifest recovery) and `storage_io.locked_roots` for
  migration writes; `write_contained`/`read_contained` for no-follow access.
- `change_publication.ChangeBranchPublisher._run_git` (30 s, `GIT_TERMINAL_PROMPT=0`) and
  `DeliveryStatePublisher._push_snapshot` readback (`ls-remote` after push) as the bounded/readback
  pattern to generalize.
- The N00-A LC recipe (`.owlbear/scratch/n00a-lc/` in the main checkout: `prepare.sh`, `inside.sh`,
  `lc_load.py`, `compare.sh`).
- `WindowHostIdentity`/issuer records, `release_stuck_worker`, retry-ledger pending attempts and
  action receipts for drain classification.
- `Client(assemble_target_server(...))`, the Cockpit HTTP client, the default loader and the
  maintained disposable E2E stack for assembled proof.

### 1.7 Exclusions

Repair proposals for abnormal states, degraded Cockpit start, the Repair Delivery entry and
consumer distribution of pinning (N08); Cockpit upgrade controls; memory-store versioning
(`owlbear_memory` owns it); migrating remote snapshots in place; rewriting packages or receipts;
automatic rollback after the format marker is written; Windows.

### 1.8 Decisions

Agent-settled with probe evidence:

- **D1 Pinning by workspace-local immutable releases and generated launchers** (P4, P5). A release
  is `.owlbear/controller/releases/<commit>/`: `git archive <commit>` + `uv sync --locked
  --compile-bytecode` + the Cockpit bundle (built from the archive with the pinned Node, or taken
  from a `main` archive) + `RELEASE.json` (commit, format range), then made read-only.
  `delivery-controller pin` writes `.owlbear/controller/pin.json` and the launchers
  `.owlbear/controller/bin/delivery-mcp` and `bin/cockpit`, each `exec`-ing the release's realpath.
  The tracked `.vscode/mcp.json` runs `${workspaceFolder}/.owlbear/controller/bin/delivery-mcp`
  (cwd defaults to the workspace folder). `.owlbear/controller/` is gitignored. The controller still
  manages the primary worktree because the loader derives the workspace from the cwd, not from the
  code location (P5). `uv run cockpit` or `uv run python -m owlbear_delivery_mcp` in the checkout
  then runs checkout code and is refused by I6 with a message naming the launcher. A clone without
  an installed release shows `owlbear-delivery` as failed to start until
  `uv run delivery-controller install --pin <commit>` runs. Seed and `setup/init.py` stay
  unchanged: consumers keep `uv --project <OwlBear clone>` (unpinned) until N08-C applies the same
  layout; `install --source <OwlBear clone>` already supports that.
  Rejected: a linked or detached Git worktree (shares the main checkout's `.git` administration, is
  mutable, registers in `git worktree list`, and its `.git` file holds absolute main-checkout paths
  that complicate LC copies); a `current` symlink in `mcp.json` (P5: switching it under a running
  process redirects lazy imports to the other release); `uv run --project` as launcher (resolves
  and may sync an environment at each start; no gain over a locked venv); a shared
  `~/.owlbear/controllers` store (deduplicates disk, but needs `${userHome}`; deferred to N08-C).
- **D2 Registry in Delivery, mirror in tools.** `state_formats` is the single source; the
  stdlib-only inspector keeps a copy of version tables plus the new classification, pinned by a
  parity test. Tools never become a Delivery dependency (R10).
- **D3 Downgrade refusal is complete from N02-B.** N02-A refuses newer versions of versioned
  families and any `runtime/format.json` whose format is above 0. N02-B introduces that marker
  (format 1) as its first migration and the commit point of every later migration; unversioned
  families and new layouts are covered by the marker. N02-A also refuses any `runtime/migrations/`
  journal, so an N02-A controller cannot start on a crashed N02-B apply. Protection exists only for
  gated controllers: rollback below N02-A is unsupported, and no ungated (D03) controller is started
  on migrated state. **Rollback versus downgrade:** a gated release whose registry includes the
  state's format and every family version must load it with every Change available (supported
  rollback; N02-C and N02-D add no format, so the N02-B and N02-C releases accept format 1). A
  release lacking them must refuse it with a typed version diagnostic and unchanged hashes
  (unsupported downgrade: N02-A against format 1; any release against a synthetic newer format).
  No format is bumped only to make a refusal observable.
- **D4 #215 root cause** (P1, P2): `parse_delivery_frontier` validates `json.loads` output with
  `DeliveryFrontier.model_validate(payload, strict=False)`. Strict *Python-mode* validation rejects
  JSON arrays for the model's tuple fields (`tuple_type` on `bindings`, `operator_moves`,
  `change_publication_history.publications`), so the reader turned strictness off for the whole
  frontier, and tests followed with `model_validate_json(..., strict=False)`. That also accepts
  lax scalar coercions everywhere. Strict *JSON-mode* validation accepts arrays and ISO datetimes:
  every live frontier and every frontier validated by the exercised tests round-trips under it.
  Fix: one strict JSON parser per family; no global relaxation.
- **D5 Two migration kinds.** *Read-upcast*: pure, registered, never rewrites stored bytes; it
  verifies the stored identity and, for digest-identified families, derives a new identity with the
  stored one as provenance (snapshot 1→2: new `snapshot_id`, `migrated_from_snapshot_id` = stored
  ID); for immutable, Git-tracked and remote families (snapshot 1→2, frontier 17→18 in snapshots).
  *Rewrite*: fenced, journaled, local mutable families only. The existing implicit rewrite of a
  non-current frontier in `DeliveryRuntime._read` becomes the registered rewrite
  `frontier-17-to-18` in N02-B; the gate then reports `migration-required` instead of writing
  during load.
- **D6 Drain uses an offline preflight after stop.** The first upgrade leaves the D03 controller,
  which has no drain mode and must not change. The upgrade therefore stops both controllers and
  runs `delivery-controller preflight` from the target release against the stopped workspace,
  where nothing can change. A read-only preflight through the running controller precedes the stop
  so the user can settle blocking custody first.

| Custody (D03) | Upgrade rule |
| --- | --- |
| Running claim with a live or unknown issuer window | Blocks. Let the worker return and settle, or the user confirms `release_stuck_worker`. Host-lost claims settle automatically |
| Started engine action without `result.json` | Blocks; the old controller's replay turns it into the next row, so it never drains by itself |
| Engine result `kind=blocked`, `engine-action-interrupted`, with retained custody (the coordination continuation stays unfinished: `finish_continuation_action(release=False)`, `change_workspace.py:2185-2192`; `_continuation_journal_readiness`, `portfolio_application.py:7276-7314`) | Blocks: the owner result is unknown and a descendant writer may still run. Needs the owner's verified host/worker closure and settlement first. Other blocked results with retained custody (`engine-action-failed`, `-incomplete`) have known effects and count as attention (last row) |
| Pending state publication, pending checkpoint, unreceipted PR or branch publication operation, pending `RuntimeTransaction` | Blocks; drained by the old controller's supervisor. A remote outage leaves the upgrade blocked and reported |
| Migration journal not `verified` | Blocks normal start; only `delivery-migrate resume`, `verify` or `abort` |
| Passive Builder handoff, Planner pause, unanswered request, report-backed Finalizer attention, retry backoff/exhaustion | Allowed; durable records must load after migration (LC full form proves it) and resume |

- **D7 L5 design** (P7): fetch the exact target into a private ref
  `refs/owlbear/target-sync/<sha256(change_id + "\0" + operation_id)>` with `--refmap=` and the
  bounded runner, outside the portfolio lock. The hashed key is always a valid ref name, even for
  legal IDs such as `sync..1`, `sync.` and `sync.lock`, and two Changes that reuse one operation ID
  get distinct refs. Requests and receipts keep the original ID. Then compare with
  `expected_target`, and take the existing portfolio and per-Change locks only for the local merge,
  receipt and a compare-and-swap `update-ref` of the shared remote-tracking ref. The portfolio lock
  no longer spans network I/O.
  **Stale-target observation, amended after Sol round 3, §1.5 contract review, and after Sol round 4
  (2026-10-04, under the overnight authorization; confirmation pending).** Rounds 1–3 each found
  material defects in the observation mechanism, so its contract was re-derived instead of repaired
  again. A stale fetch never moves `refs/remotes/<remote>/<target>`. The engine learns the fetched head
  from one advisory recording `refs/owlbear/target-observation/<sha256(target ref)>/<base>/<generation>`
  naming it, where `<base>` is the shared ref's value when that fetch began and `<generation>` is a fresh
  random token created in the same transaction. The generation gives each recording its own identity:
  a later recording of the same head under the same base is a different ref, so compare-and-swap checks
  distinguish it (round 4: name and head alone could not, so an exact sync deleted a newer re-recording
  and an overlapping stale fetch overwrote it). The engine target is the recording's head while the
  shared ref equals `<base>`, otherwise the shared ref. Each recording write and each engine move of the
  shared ref runs under the existing target-sync lock as one `update-ref --stdin` transaction,
  compare-and-swapped on the shared value and on the recordings it replaces; the fetch-start snapshot of
  the shared value and recordings is also read under that lock (local reads only), so it never mixes
  refs from another sync's half-applied transaction. A stale result replaces
  exactly the recordings read before its fetch, or is dropped when the shared ref or that set changed
  (among overlapping fetches the first writer wins; a fetch that starts after a recording may replace
  it). An exact sync moves the shared ref, deletes only the recordings read before its fetch (older than
  its result) and carries one recorded after its fetch began to the new shared value, all in one
  transaction. If that transaction is refused because a ref changed concurrently, the exact sync replans
  from the new state (at most three attempts, then it raises; a concurrent shared-ref move keeps its
  value and the receipt stays exact); a refusal with no observable change (including an external Git
  process briefly holding a ref lock) raises before the merge and receipt, and the sync can be retried,
  so progress is never silently lost and a failed cleanup never leaves the engine selecting the head that
  cleanup should have removed. Only
  `update-ref --stdin`, `for-each-ref` and `rev-parse` are used (all present in Git 2.43, the Ubuntu
  24.04 package); no reflog and no new object types. Rejected: the reflog marker (`git reflog write` is
  absent in Git 2.43, and its head ref and marker were two unlocked writes); re-fetching at the point of
  use (readiness and custody reads would do network I/O and could change between two reads of one
  decision); a recording that points at a generated commit (needs `commit-tree` and a parent read for
  no gain over a generation in the ref name). Accepted residuals: (1) an external return of the shared
  ref to the exact base (A→C→A) revives the recording. It is a hint, never authority: only an exact
  fetch merges, and the next fetch starts after the recording and replaces it, so the cost is one stale
  round. (2) Engine target reads take no lock and Git applies a multi-ref transaction ref by ref, so a
  read that overlaps a recording or exact-sync transaction can briefly miss a recording being replaced
  or carried and select the shared value instead; the next read after the transaction sees its result.
  (3) Overlapping fetches carry no record of when each read the remote: the first writer under the lock
  wins, a stale fetch that read the remote before an exact fetch but records after that exact fetch
  began is carried as if newer, and engine moves of the shared ref A→C→A between one fetch's start and
  its lock are indistinguishable from no move, so that older fetch may still move or record. Each case
  costs one stale round; the next fetch replaces the result. (4) Refs written in the round-3 format
  `<sha256(target ref)>/<base>` are not read and conflict with the new names; none exist outside
  disposable test repositories (no legacy support).
  **Merged with N09-A2 (#357):** the direct `sync-target` marker (N09 §1.11 K2/K3) is committed in
  the first, publication-locked block after the receipt replay and start checks, before the fetch
  snapshot and the unlocked fetch; the merge phase re-checks replay and start but starts no marker.
  The application checkpoint lock still spans the whole call (K5).
- **D8 Bounded runner kills the process group** (P6): `subprocess.run(timeout=…)` returns on time
  but leaves the transport helper running; the runner starts Git in a new session and kills the
  group on timeout.
- **D9 This P revision amends execution plan §1.3** (plan gate passed; the user approval that execution
  plan §1.1 requires was recorded on 2026-10-03: listed to the user without objection). The mount-based
  LC recipe keeps absolute main-checkout paths in receipts,
  worktree `.git` files and coordination records byte-identical, so the former static rule "no
  main-checkout path remains" could not hold without rewriting bytes. Revised §1.3: record and
  receipt bytes are preserved; isolation is proven affirmatively by mount information (the copy is
  the only mount at or under the live path; the real checkout is not mounted), the copy marker, and
  `git rev-parse --git-common-dir` of the copy and each worktree resolving inside the copy; live
  record hashes are unchanged after the run.
- **D10 Migration `abort` removes the empty namespace** (amended by N08-P after its Sol round 6,
  under the user's overnight authorization of 2026-10-03; confirmed 2026-10-03, listed to the user
  without objection). N02-A's `state_formats._walk` refuses whenever `runtime/migrations` exists, even
  empty, so step 5f alone
  left a first pre-marker abort refused by N02-A although D3 requires it to load the restored
  format 0. §3.3 step 5g removes only a real empty directory; `abort <archived id>` resumes it.

User decisions ([U1–U3](#u-decisions)) were decided on 2026-10-03 as engineering decisions with one
defensible answer, listed to the user without objection: U1 (a), U2 (a), U3 default. U1 is required
before N02-D starts; U2 before the phase that ships the prompt (N02-D). N02-A to N02-C depend on
neither answer: the lock, gate,
migration, LC tool and bounded Git are needed under every option. U3 is an engineering default.

#### U decisions

**U1 — Pin this repository's live controller** (decided 2026-10-03: (a); required before N02-D).
Status quo: live runs D03 from the frozen main checkout on `delivery-live`; any checkout there
becomes live code on restart. Problem: the freeze blocks normal use of the main checkout until
N10-M, and an unpinned controller makes every merge a
potential live change. Options: (a) pin with D1 at N02-D and end the freeze; (b) keep the freeze
until N10-M and pin only then; (c) pin with a linked Git worktree on a dedicated branch.
**Decision (2026-10-03): (a).** It is the mechanism N10-M and consumers need anyway, and it is
rehearsed on a copy first. Any other answer re-plans N02-D before it starts (its H step,
`.vscode/mcp.json` edit and freeze note assume (a)).

**U2 — Upgrade UX** (decided 2026-10-03: (a); required before N02-D, which ships the prompt).
Options: (a) a maintenance prompt `/upgrade-delivery` that drives
`delivery-controller` and `delivery-migrate`, asking the user only to stop and restart the MCP
server in VS Code and to confirm the switch; (b) a Cockpit **Upgrade** control (Cockpit is itself a
controller and would have to stop and restart itself mid-request); (c) CLI only.
**Decision (2026-10-03): (a)**, with Cockpit showing the pinned release read-only; any Cockpit
control is N08/N09 scope. Under (b) or (c) the prompt drops from N02-D's editable paths.

**U3 — Release retention** (engineering default, recorded 2026-10-03; no user decision needed). A release measured
1.7 GB by `du` (1.6 GB venv; APFS clones from the uv cache use less real disk). Options: keep
current and previous (rollback) and prune older on upgrade; keep all; restrict the venv to the
controller packages. **Decision:** keep two, prune on upgrade; revisit package restriction
in N08-C.

## 2. Feasibility Probes

All probes ran on `42144f9dc` in the lane worktree (read-only) or in disposable directories under
`/private/tmp`. Live state was only read. Helpers and outputs:
`/Users/GGN7H9Q/Projects/owlbear-dev-lane-c/.owlbear/scratch/n02p/` (unversioned).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | `p215.py`: every live `frontier.json` and revision frontier through `parse_delivery_frontier`, then strict JSON, lax JSON and strict Python validation of the canonical and `model_dump_json` bytes | Strict JSON: all current and one revision frontier pass and compare equal. Strict Python on `json.loads` output: `tuple_type` on `bindings`, `operator_moves`, `change_publication_history.publications`. The schema-17 revision frontier of `macos-managed-browser-authentication` is rejected by the current parser: free-text request resolution without user-confirmed provenance | D4; I4; V20 live example |
| P2 | `strict_plugin.py` (pytest plugin, no repo edit): wraps `DeliveryFrontier.model_validate[_json]` to try strict JSON on the same input, then runs the original call; 4 Delivery test files, `-n 4` | First run, cut by the 900 s session timeout after 502 tests (one per-test timeout from machine load, not a strict failure): 47,341 frontier validations, all strict-JSON-valid except 4 deliberate model-validator rejections (`value_error`, rejected in both modes). Second run with a longer session timeout: see [P2 second run](#p2-second-run) | D4; strict tests are feasible |
| P3 | `delivery-diagnose inspect` (lane code) on the live root; raw tree walk of live `.owlbear/delivery` (excluding worktrees); `git show` of every remote snapshot | Inspector: healthy, 0.46 s, 20 records. Tree and remote: see [1.4](#14-persisted-record-families); remote holds one snapshot v1 with frontier v17; two empty `authority.json` drafts; no D03 receipt families yet | Inventory; gate must accept registered legacy reads and empty draft authority |
| P4 | Loader source read: `load_delivery_application`, `_derive_paths`, `_validate_git_config`, `_bootstrap_remote_state`, `DeliveryRuntime._read`, `PortfolioApplication.__init__`; MCP `app_lifespan`, Cockpit `_load_target_runtime`/`load_target_context`, seed `.vscode/mcp.json` | Workspace = `Path.cwd()`; primary-worktree check compares that root with `git worktree list` entry 0. Startup writes: remote restore (packages, branches, worktrees, runtime files), frontier canonicalization, retry-ledger legacy import. Consumers already run code from the OwlBear clone (`uv --project <clone>`) against their own cwd | I1 placement; D1 viability |
| P5 | `pin_probe.sh`: disposable primary-worktree repository with a local bare remote (`url.<bare>.insteadOf`), release from `git archive 42144f9dc` + `uv sync --locked --compile-bytecode` (35 s) + copied bundle, `chmod -R a-w`; generated launchers; MCP client over stdio; Cockpit over HTTP; negatives | MCP via launcher: 63 tools, `delivery_health` healthy, `list_changes` empty; `owlbear_delivery`, `pydantic` and `sys.prefix` all inside the release; read-only release, no files written into it. Cockpit via launcher: `/api/work-items` 200, `index.html` byte-identical to the release bundle, process maps release files. Same launcher with cwd = linked worktree: refused "Delivery must start from the primary Git worktree". `uv --project <lane>` from the workspace runs lane code (code origin follows the launcher). `current` symlink switched while a process ran: a later lazy import loaded the other release | D1; I6 need; VS Code `${workspaceFolder}` and cwd default confirmed in VS Code's MCP configuration reference |
| P6 | `p220_hang.py`: `git fetch` over an `ext::` transport that never answers | Both `subprocess.run(timeout=2)` and `Popen(start_new_session=True)` + `killpg` raise after 2.0 s; afterwards one transport helper was still running, which can only be the `run()` variant's because `killpg` kills its whole group | D8 |
| P7 | `pl5_fetch.sh`: two concurrent fetches into private per-operation refs from a bare remote; `update-ref` CAS | Without `--refmap=` Git also updates `refs/remotes/origin/dev` and the concurrent fetches race on it (`cannot lock ref`). With `--refmap=` both succeed and the shared ref is untouched; CAS `update-ref new old` succeeds once and refuses a stale old value; fetch by exact commit works locally | D7 |
| P8 | Docker availability for the LC recipe | Docker 29.4.0, `ubuntu:24.04` present; N00-A's container recipe is runnable | N02-B `delivery-lc` |

### P2 second run

Command:
`pytest -o 'pythonpath=… .owlbear/scratch/n02p' -o session_timeout=5400 -o timeout=180 -p strict_plugin -n 4`
on `test_delivery_state.py`, `test_checkpoint_publication_regressions.py`,
`test_portfolio_application.py`; output `strict_out2.txt`.

Result (2026-10-03): 650 passed in 867 s. About 61,000 frontier validations also passed strict
JSON validation. The only 4 strict failures are `value_error`, raised by model validators, which
reject in lax mode too; they are the same deliberate rejections as in run 1. No strict-only
(type-coercion) failure exists in these suites. Settles G1 for N02-A.

## 3. Phases

### 3.1 Shared rules

- Plans name symbols. After N01, re-resolve each symbol's file with `grep`; N01 moved
  `PortfolioApplication` methods into `application_*` mixins, `ChangeWorkspaceManager` methods into
  `workspace_*` mixins and `DeliveryRuntime` helpers into `runtime_*` modules
  ([N01 plan](delivery-n01-plan.md#3-phases)). Writers pinned by I6 of N01
  (`DeliveryRuntime._replace`, `_read`, the 43 frontier writers) stay in `delivery_runtime.py`.
- All N02 phases follow N01-C (execution plan §4.2) and edit N01 modules; no N02 phase can run in
  parallel with an unmerged N01 phase. N03-A, N05-B and N08-A need N02-B; N08-C needs N02-D.
- Every new health reason ships with its `serve/cockpit/web/src/api/workItems.ts` mirror,
  rendering and the parity assertion in `tests/test_cockpit_boundary.py`. Every new
  frontier-writing operation joins the central mutability policy and
  `tests/test_delivery_worktree_authority.py`.
- Assembled claims use the default loader, `Client(assemble_target_server(...))` and the Cockpit
  HTTP client on disposable repositories with local bare remotes. Fakes sit only below the remote
  Git runner and host probes.
- Risky code (gate, migration, replay, remote Git, pinning) stays with Opus. Luna may take the
  inventory fixtures, strict-read test rewrites, frontend mirrors and docs, each with an exact
  contract (execution plan §1.6).

### 3.2 N02-A — Registry, gate and strict frontier

- **Prerequisites:** N02-P, N01-C.
- **Editable paths** (N01 overlap in brackets):
  - new `serve/delivery/src/owlbear_delivery/state_formats.py`
  - `storage_io.locked_roots` (a shared mode; today it takes `LOCK_EX` only, `storage_io.py:33`)
    and the controller lock (I5); `checkpoint_supervisor.py` (stops before the lock is released)
  - `delivery_application_loader.py`: `load_delivery_application`, `DeliveryApplicationLoadError`
    (new subclass), `_read_local_snapshot_frontier`, `_read_local_pending_publication`,
    `_read_planner_handoff_pause_receipts`
  - `delivery_runtime.py` / `runtime_*` [N01-C]: `parse_delivery_frontier`,
    `DeliveryRuntime.pending_state_publication`, `acknowledge_pending_publication`,
    `reanchor_pending_publication`, `_planning_pause_replay_result`,
    `_planning_pause_receipt_matches`
  - `delivery_state.py`: `parse_delivery_state_snapshot`, `_portable_frontier`,
    `_snapshot_validation_code`, `DeliveryStatePublisher.publish`, `read_snapshot_inventory`,
    `repair_quarantined_snapshot`
  - `application_*` [N01-A]: `PortfolioApplication.admit_delivery_change`,
    `repair_delivery_state_snapshot` (frontier reads through the one parser)
  - `recovery.py`: `RetryLedger.read`, `RetryLedger._read_with_bytes` (strict JSON)
  - `portfolio_operating.py`: `DeliveryHealthReason.REMOTE_STATE_VERSION_UNSUPPORTED`
  - `serve/delivery-mcp/.../server.py`: `load_delivery_config`, `app_lifespan`;
    `serve/cockpit/.../target_context.py`: `load_target_context`
  - `serve/tools/.../delivery_diagnostics.py`: version tables and classification (`newer`,
    `readable-legacy`), stdlib only
  - tests: new `serve/delivery/tests/test_state_formats.py` and fixtures
    (`fixtures/state_formats.json` schema fingerprints; golden D03 records per family);
    strict reads in `test_delivery_runtime.py`, `test_delivery_state.py`,
    `test_portfolio_application.py`, `test_checkpoint_publication_regressions.py`;
    `serve/tools/tests/test_delivery_diagnostics.py`; `serve/delivery-mcp/tests`,
    `serve/cockpit/tests` startup refusal
  - companions: `workItems.ts`, the health rendering in `WorkPortfolioPage.tsx` with a component
    test, `tests/test_cockpit_boundary.py`; this plan's progress row; execution plan status row
- **Positive scenarios:** the gate classifies the live copy and every D03 fixture family as
  `current` or `readable-legacy` with no writes (tree hash unchanged); each golden record
  round-trips byte-identically; schema-17 frontiers still read; a schema-1 snapshot reads with its
  stored ID verified, a newly derived `snapshot_id` that differs from it,
  `migrated_from_snapshot_id` equal to it and its remote bytes unchanged; all four test files read
  frontiers strictly and pass; MCP and Cockpit start together on one disposable portfolio (both
  hold the lock shared); the inspector and registry agree (parity test).
- **Negative scenarios:** a local frontier 19, coordination 2, config 3, claim issuer 2 or
  `runtime/format.json` with format 1 → `DeliveryStateVersionError` from the default loader before
  `_bootstrap_remote_state` (a remote rewritten to an unreachable path produces no diagnostic) and
  with identical tree hashes; an unknown lower version → `state-version-unknown`; a remote
  snapshot v3 → `remote-state-version-unsupported` for that Change, no restore, `publish` refuses
  without pushing, `repair_quarantined_snapshot` refuses; MCP startup and Cockpit startup fail with
  the typed detail; a frontier with a lax-only value (string for an integer, number for a string
  datetime) is rejected where `strict=False` accepted it; changing a registered model without a
  version and fingerprint update fails the fingerprint test (self-test with a synthetic model);
  an unregistered `schema_version` model fails the hygiene test; a test holder of the exclusive
  controller lock (the N02-B `apply` contract) makes the default loader, MCP and Cockpit refuse
  `controller-fenced` with identical tree hashes; while a controller runs, a non-blocking
  exclusive acquisition fails; a refused load releases the lock; a `runtime/migrations/` journal
  → `state-migration-incomplete`.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_state_formats.py -q`, then
  `uv run pytest serve/delivery/tests/test_delivery_runtime.py serve/delivery/tests/test_delivery_state.py -q`.
- **Closeout:** `uv run test --changed`; scoped Ruff; `npm test`, `npm run build`, Biome on changed
  frontend files; `uv run pytest tests/test_package_boundary.py tests/test_cockpit_boundary.py -q`.
- **LC:** load form with the N00-A recipe; additionally record the gate report of the copy. A live
  record that only the old `strict=False` parsing accepted stops the phase for a user decision
  (registered read-upcast, or an N08 repair proposal); strictness is never relaxed to pass.
- **Size / risk:** M / high (startup path of every controller; strictness may surface real
  defects in fixtures, which are fixed, not relaxed).

### 3.3 N02-B — Fenced migration, format marker and LC tool

- **Prerequisites:** N02-A.
- **Editable paths:** new `owlbear_delivery/state_migration.py`; `state_formats.py` (marker family,
  `frontier-17-to-18` rewrite, journal family); `delivery_application_loader.py`
  (`state-migration-incomplete` for any journal not `verified`; the offline verification mode used
  only by `verify`); `DeliveryRuntime._read` [N01-C] (no rewrite of a non-current version;
  canonical-bytes rewrite of current versions stays);
  `.owlbear/.gitignore` (`delivery-migrations/`); new `owlbear_tools/delivery_migration.py`,
  `owlbear_tools/delivery_lc.py` and their console scripts in `serve/tools/pyproject.toml`;
  `delivery_diagnostics.py` (marker and journal mirror); tests (`test_state_migration.py`,
  `serve/tools/tests/test_delivery_migration.py`, `test_delivery_lc.py`); this plan; status row.
- **Protocol:**
  1. `propose` (no write to authoritative state, no journal): gate scan; for each record needing a
     rewrite, the registered pure function writes new bytes to the staging area
     `.owlbear/delivery-migrations/<proposal_id>/stage/`, outside `.owlbear/delivery/`; no gate,
     loader or controller reads it. Each staged record must parse with the target release's strict
     parser. `proposal_id` = SHA-256 of the canonical list of (path, before digest, after digest),
     source and target format and controller release.
  2. `apply`: take the controller lock exclusively without blocking (refuse if any controller
     runs or any `RuntimeTransaction` manifest is pending); re-verify every before digest (stale →
     refuse); copy affected records and a full record-tree hash manifest to
     `.owlbear/delivery-migrations/<id>/backup/`; create the journal
     `runtime/migrations/<id>/journal.json` (`backed-up → applying → applied → verified`, or
     `aborting` from `backed-up` or `applying`, step 5); replace records through
     `RuntimeTransaction` in bounded batches, recording each batch's migration-owned transaction
     ID in the journal before its commit; write `runtime/format.json` last (commit point).
  3. `resume` after a crash: per record, current digest = after → done; = before → replace;
     otherwise stop as unknown corruption, preserving both copies (never rehash). Refused once
     the journal is `aborting`.
  4. `verify` (offline, under the exclusive lock, never starts the normal controller): the gate in
     verification mode accepts exactly the named `applied` journal at the target format; a
     verification-mode load (no remote bootstrap, remote Git, supervisor or write) lists and
     reads every Change as available; the record-tree hash is unchanged by that load; then journal
     `verified`. MCP and Cockpit cannot select verification mode.
  5. `abort` before the marker; after it, refuse (restoring the backup is a user decision,
     preserve-before-restore). It uses durable state only, never `RuntimeTransaction.abort`,
     which needs the committing process's in-memory `_abort_snapshot`
     (`runtime_transaction.py:165-175`), and is restartable:
     (a) verify the backup against its hash manifest (mismatch → corruption stop);
     (b) journal `aborting`;
     (c) move every migration-owned transaction manifest named in the journal to
     `.owlbear/delivery-migrations/<id>/retired-transactions/`, so no `recover`/`recover_all`
     rolls it forward over restored bytes (`_publish_replacement` rewrites a record still at its
     before bytes, `runtime_transaction.py:737-751`);
     (d) per record: after digest → write the backup bytes; before digest → keep; otherwise
     corruption stop with both copies preserved;
     (e) verify every affected record against its backup digest and the record-tree hash against
     the backup manifest (excluding L-class files and `runtime/migrations/`);
     (f) archive the journal as `aborted` beside the backup, then remove `runtime/migrations/<id>/`;
     (g) still under the exclusive lock, remove `runtime/migrations` only when it is a real
     directory with no entry, without following links; any entry, a symlink or a non-directory is
     preserved (D10: N02-A refuses on the namespace alone; D3 requires it to load format 0).
     A crash before (f) completes leaves the journal in place, so normal start still refuses and
     `abort` repeats the digest-checked steps. After (f), `abort <archived aborted migration id>`
     reads only that archived journal and runs only (g); a repeat is a no-op, and `resume` or
     `verify` of an archived ID refuses without a write. Backup, staging, retired manifests and
     archived journal are kept.
  Normal start accepts no journal or only `verified` ones: propose → apply → verify → start; an
  `aborting` journal accepts only `abort`.
- **Refusals:** immutable receipts, packages, remote snapshots and historical revisions are never
  rewritten; a record invalid at its declared version with no registered rewrite is reported as
  corruption (the live schema-17 revision frontier is the reference example); missing
  user-confirmation provenance is never synthesized.
- **First migration (format 0 → 1):** verify all records are baseline, rewrite any current
  frontier at v17 to v18, write the marker. On today's live state it writes only the marker.
- **`delivery-lc`:** formalizes N00-A. `prepare` copies the main checkout's `.git` and
  `.owlbear/delivery` (excluding `.venv`, `node_modules`, `dist`, caches) to a stage and hashes
  live records; from N02-D it also copies the pin state (`.owlbear/controller/pin.json`, `bin/`
  launchers, each release's `RELEASE.json`, not the platform-specific release trees) and
  `.vscode/mcp.json`. `run` starts an `ubuntu` container whose only bind mount is the stage, at the
  live absolute path; the real checkout is not mounted. Isolation is by mount-namespace path
  resolution, not rewriting: linked-worktree `.git` files, `gitdir` files and coordination records
  keep their absolute main-checkout paths byte-identical, and inside the container those paths
  resolve into the copy. Before loading, `run` proves isolation as revised execution plan §1.3
  requires (D9): `/proc/self/mountinfo` shows the stage as the only mount at or under the live
  path (and under `/Users`) and no mount of the real checkout, the copy marker is present at that
  path, and `git rev-parse --path-format=absolute --git-common-dir` of the copy and of every
  copied worktree resolves to the copy's `.git`. `run` then points `origin` to a local bare remote
  via `url.<bare>.insteadOf`, checks out the candidate, syncs, and runs `delivery-diagnose`, the
  gate report and the read-only application load; from N02-D it rebuilds the copied pinned release
  and the candidate from their commits with `delivery-controller install` (release venvs are
  platform-specific), checks them against the copied `pin.json`/`RELEASE.json` and starts
  controllers through the copied launcher layout; **full form** adds: unmigrated copy refused with
  a typed version diagnostic and unchanged hashes, `delivery-migrate propose/apply/verify` on the
  copy, migrated copy loads, the previous release (the merged predecessor phase head; from N02-D
  the pinned previous release) meets the D3 oracle on the migrated copy (accepts it when its
  registry includes the format, refuses it otherwise), and the candidate refuses a synthetic
  newer-format copy; `compare` proves live records unchanged. Receipt bytes are never rewritten to
  make a copy load.
  Amended in N09-A2: the oracle implements D3's family-version rule (refusal exactly at newer-family records).
- **Positive scenarios:** propose/apply/verify on a disposable D03-format portfolio with each
  custody shape (passive Builder handoff, Planner pause, report-backed Finalizer attention,
  completed Change) → every Change available after; LC full form on a live copy.
- **Negative scenarios (V21, parameterized):** crash injected after backup, after each record
  replacement, before and after the marker, before `verified` → restart refuses
  `state-migration-incomplete`; at `applied`, `verify` succeeds offline while MCP and Cockpit
  still refuse, and before it `verify` refuses; `propose` leaves the `.owlbear/delivery` tree hash
  unchanged and its staged bytes are never loaded as authority; `resume` converges to identical
  bytes with no duplicate; `apply`, `verify` or `abort` while a controller holds the lock →
  refused, no write; stale proposal → refused; a third digest →
  corruption stop with both copies preserved (V20); downgrade: an N02-A controller refuses the
  format-1 workspace; pre-marker abort: crash after the first replacement
  (`after-first-publication`, migration manifest pending), `abort` from a fresh process with a
  crash injected after each abort step and `abort` repeated, then a normal restart → every
  affected record equals its backup bytes, no migration transaction manifest is pending and the
  restart's `recover_all` rewrites nothing, `runtime/migrations` is absent, and the backup and
  archived `aborted` journal remain; `resume` on an `aborting` journal → refused. Namespace (D10),
  first migration on format-0 state with no `runtime/migrations`: the merged N02-A release's
  `scan_capability` (subprocess from its merge commit) after a pre-marker abort equals its
  pre-migration result; crash after (f) → N02-A refuses, then `abort <archived id>` runs twice:
  the first removes the namespace and N02-A's result equals the pre-migration one again, the
  second writes nothing; `resume` or `verify` of the archived ID → refused, no write; an
  unrelated entry, a symlink or a non-directory at `runtime/migrations`, injected after (f),
  survives `abort <archived id>` unchanged (no-follow `lstat`) and N02-A still refuses.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_state_migration.py -q`.
- **Closeout:** `uv run test --changed`; scoped Ruff; LC full form via `delivery-lc`.
- **Size / risk:** L / high (first persisted format change; crash and replay logic).

### 3.4 N02-C — Bounded remote Git and target-sync fetch

- **Prerequisites:** N02-B.
- **Editable paths:** new `owlbear_delivery/remote_git.py`; `delivery_state.py`
  (`DeliveryStatePublisher._run_git` remote calls, `_push_snapshot`, `_refresh_remote_head`,
  `_remote_head`); `delivery_application_loader.py` (`_run_loader_git` remote calls,
  `_remote_branch_head`, `_fetch_remote_snapshot_change_head`, `_fetch_snapshot_change_head`);
  `workspace_target_sync` [N01-B]: `ChangeWorkspaceManager.sync_with_target`, `_fetch_target`,
  `_fetch_external_head`; `change_publication.py` (`ChangeBranchPublisher._run_git` → shared
  runner); tests (`test_remote_git.py`, state, loader, workspace, publication suites); this plan;
  status row.
- **Contract:** environment `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, `GIT_ASKPASS` and
  `SSH_ASKPASS` disabled, SSH `BatchMode=yes` unless the user set `GIT_SSH_COMMAND` (amended in N02-C
  under overnight authorization; confirmation pending: a `core.sshCommand` from any scope, including
  the operation's own `-c`/`--config-env`, is kept, and a direct `ssh` program gets `-o BatchMode=yes`
  as its first option because OpenSSH keeps the first value; other wrappers run unchanged), and
  `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` cleared; new session and group kill on timeout (D8);
  read timeout → `RemoteGitTimeout` (retry-safe); write timeout or transport failure →
  `RemoteGitWriteUnknown`, then a bounded `ls-remote` readback before any retry (intended head →
  success; expected old head → retry-safe failure; other → conflict; readback failure →
  `DeliveryStateResponseUnknownError` with the pending publication intent kept). Local Git
  commands keep their current behavior. Target sync follows D7.
- **Positive scenarios:** two Changes sync concurrently against one remote; a slow fetch of one
  does not block the other's merge; snapshot push whose response is lost but which a slow
  `pre-receive` hook on the bare remote accepts → readback success, no second push.
- **Negative scenarios:** hung read (ext transport or injected runner) → typed timeout within the
  bound, no leftover process, target-sync, checkpoint and publication locks acquirable afterwards;
  hung write → unknown outcome, readback, no blind retry; a prompt-requiring remote fails instead
  of waiting; private-ref head differs from `expected_target` → `ChangeTargetSyncStaleError`, shared
  ref unchanged; stale CAS on the shared ref → shared ref left as is, receipt still exact;
  operation IDs `sync..1`, `sync.` and `sync.lock` sync successfully (valid hashed private refs);
  two Changes syncing concurrently with the same operation ID get distinct private refs, correct
  returned heads, and an unchanged shared ref until the CAS step.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_remote_git.py serve/delivery/tests/test_delivery_state.py -q`.
- **Closeout:** `uv run test --changed`; scoped Ruff; LC full form (the N02-B release accepts the
  migrated copy: supported rollback, D3).
- **Size / risk:** M / high (publication readback and lock behavior).

### 3.5 N02-D — Controller pinning and upgrade procedure

- **Prerequisites:** N02-C; the user's confirmation of U1 and U2.
- **Editable paths:** new `owlbear_tools/delivery_controller.py` and console script;
  `owlbear_tools/delivery_lc.py` (pin-state capture and in-container release rebuild); pin
  enforcement in `state_formats.py` / loader (`controller-not-pinned`, I6); `.vscode/mcp.json`
  (`owlbear-delivery` → launcher; other servers unchanged); `.owlbear/.gitignore` (`controller/`);
  `.vscode/settings.json` (exclude `.owlbear/controller` from search and watchers); new
  `share/prompts/upgrade-delivery.prompt.md` (U2) and its agent-ecosystem tests; `setup/operating-owlbear.md`
  and the Delivery sections of `README.md`; tests (`serve/tools/tests/test_delivery_controller.py`,
  loader pin tests); this plan; execution plan status row and the factual §1.2/§2.6 note that the
  freeze ended. Seed and `setup/init.py` stay unchanged (N08-C).
- **Upgrade procedure** (extends N00-M's live-activation steps):
  1. Read-only preflight through the running controller; the user settles blocking custody (D6).
  2. The user stops `owlbear-delivery` (*MCP: List Servers* → *Stop*) and Cockpit; the tool
     verifies no controller process and that the controller lock is free; steps 3–6 each take it
     exclusively and refuse if a controller holds it.
  3. `delivery-controller preflight` from the target release (offline, D6); stop on any blocker.
  4. Back up `.owlbear/delivery` (excluding worktrees) and the Delivery refs outside the
     repository; verify file count and hashes.
  5. `delivery-migrate propose/apply/verify` from the target release.
  6. `delivery-controller switch <commit>`: atomically replace the launchers and `pin.json`.
  7. The user starts the server (*MCP: List Servers* → *Start*) and Cockpit with the launcher.
  8. Verify: `delivery_health`, `list_changes`, `get_change` for every Change (all available),
     the Cockpit bundle of the release, and one idempotent engine round-trip chosen in N02-D.
  9. Failure: stop, copy the current state to a second directory, report. Switching back to the
     previous release is automatic only when the gate of that release accepts the state
     (supported rollback, D3); otherwise restoring the backup is a user decision.
- **Positive scenarios:** install, pin and launch in a disposable workspace (MCP over stdio and
  Cockpit over HTTP serve release code); upgrade rehearsal from a release of the N02-C head to the
  N02-D candidate on an LC copy with passive custody present, which resumes afterwards; after an
  injected post-switch failure, step 9 switches back to the N02-C release, which loads the
  format-1 state with every Change available (supported rollback, D3); `prune` keeps current and
  previous.
- **Negative scenarios:** a controller from the dev venv on a pinned workspace → `controller-not-pinned`
  before any read; `switch` or `prune` while a controller holds the lock → refused; preflight with
  a running claim, a started action without result, an `engine-action-interrupted` result with
  retained custody or a pending publication → blocked, nothing changed; a release lacking the
  state's format (N02-A on format 1; any release on a synthetic newer format) → refused by its
  gate with unchanged hashes (V24 downgrade, D3); a release
  directory modified after install (digest in `RELEASE.json`) → `verify` fails.
- **First-upgrade rehearsal (D03 → N02-D, LC, before the H step):** on a fresh `delivery-lc` copy
  of live state taken while no Delivery work runs, the container runs the D03 `delivery-live`
  commit from the checkout as live does, then the procedure: step 1 through the D03 MCP, stop,
  steps 3–8 from the N02-D candidate release, with the copy switched to the candidate commit as the
  H step switches the main checkout. Passes when: step 1 and the offline preflight agree, both
  reporting no blocker; the proposal lists only the marker and registered rewrites, `apply` and `verify`
  reach `verified`, and every other record is byte-identical to the copy (hash manifest); MCP over
  stdio and Cockpit over HTTP start through the launcher from release code, `delivery_health` is
  healthy and every live Change is available; the step-8 round-trip passes; an injected failure
  after `switch` runs step 9 with neither automatic switch-back nor restore (D03 is ungated and
  is not started on the migrated copy, D3); `compare` shows live unchanged. The H step
  uses the rehearsed release commit and proceeds only if its live proposal names the same (path,
  before digest) set; otherwise it stops for a fresh rehearsal.
- **Host rehearsal:** two real VS Code windows on a disposable portfolio, as in D03: launcher start,
  stop and restart from *MCP: List Servers*, no automatic restart when a release is installed,
  `chat.mcp.autostart` behavior noted.
- **H step (user present):** pin the live controller. Install the release of the merged N02-D
  commit; run the procedure with the D03 controller as "previous"; switch the main checkout from
  `delivery-live` to `dev` while both controllers are stopped (the tracked `mcp.json` now names the
  launcher); restart; verify the three live Changes. This ends the freeze of execution plan §1.2.
  From then on live code changes only through this procedure; N10-M uses it.
- **Closeout:** `uv run test --changed`; scoped Ruff; agent-ecosystem tests; LC full form as the
  upgrade rehearsal; package closeout: full `uv run test` once and a cumulative Sol challenge of
  the N02 diff against this plan.
- **Size / risk:** M / high, plus the live H step.

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N02-P | — | — | Probes P1–P8 | Sol plan round 1: revision-required (findings 1–8) → revised; Sol round 2: revision-required (abort contract, rollback vs downgrade oracle, §1.3 delta) → revised; amends execution plan §1.3 (D9); Sol round 3: revision-required (D7 private-ref key) → revised; Sol round 4: `plan-sound` | approved (D9 confirmed 2026-10-03; U1–U3 decided 2026-10-03) |
| N02-A | #348 | `f225ad508` | Candidate on base `58c4d928b`: `test_state_formats.py` 72 passed (registry hygiene, fingerprints, 44 golden records, gate, lock, strict frontier); inner loop and companions 608 passed; all `serve/delivery/tests` 1629 passed before two lock-assertion updates; `uv run test --changed` 2901 pytest passed and Vitest 332 passed; scoped Ruff check and format clean (24 files); Vitest 332 passed, `npm run build` passed, Biome clean (3 files); disposable live copy: 114 records, no gate refusal, 92 strict owner parses, live hashes unchanged, remote schema-1 snapshot upcast with `migrated_from_snapshot_id` equal to its stored ID; Sol implementation round 1: repair-required (5) → repaired (uncommitted on `c9d4a15b7`): absent or non-integer versions refuse `state-version-unknown` (absence left to the owner only where it requires the field: config, host); the configuration is read only inside the fence through `load_configured_delivery_application` (MCP, Cockpit); local schema-17 frontiers reconcile by canonical upcast bytes, stored bytes kept for publication digests; the inspector version-checks 21 runtime and package kinds under a bidirectional registry guard; the gate charges entries while enumerating. Proof: `test_state_formats.py` 83 passed; affected suites 699 passed; `uv run test --changed` 3696 pytest passed and Vitest 332 passed (EXIT 0; a first run failed 2 loader tests that expected an absent-version admission and a null host-local version to pass the gate, now aligned); scoped Ruff clean (13 files); disposable live copy: gate 124 records, no refusal; inspector `healthy-structure`, complete, 76 runtime records supported; Sol implementation round 2: repair-required (config/host missing-version gate bypass) → repaired (`f225ad508`): the owner exemption is removed, so an absent config or host `schema_version` refuses `state-version-unknown` in the gate (typed `version_absent`) before Git validation, host loading, remote bootstrap and composition, including when the core loader is given a supplied config object; MCP translates only the config absent-version refusal to `ERR_DELIVERY_STARTUP_UNCONFIGURED` (`schema_version`). Proof: falsifiers for supplied-config and host bypass (no startup stage or subprocess, hashes unchanged, lock released) and the MCP lifespan translation; `test_state_formats.py` 85 passed; MCP server and Cockpit startup 131 passed; state, diagnostics, config and loader tests 351 passed; `uv run test --changed --base origin/dev --py` 3699 passed (EXIT 0); scoped Ruff check and format clean (5 files). Lead: `uv run test --changed` EXIT 0 on `c9d4a15b7` and `e6ed5bb31`; LC load form PASS on `c9d4a15b7`, `e6ed5bb31` and `f225ad508` (healthy, 3 Changes available, only `runtime/controller.lock` created, live unchanged); Biome-reformatted goldens regenerated and excluded from Biome and editorconfig | Sol implementation rounds: 1 repair-required (5), 2 repair-required (1), 3 `implementation-sound` | merged |
| N02-B | #352 | `7500600c7` | Candidate (own runs): `test_state_migration.py` 35 passed (first migration writes only the marker; fresh-workspace stamp; `frontier-17-to-18` rewrite with staged bytes never authority; corruption never synthesized; runtime refuses an unmigrated frontier; crash at 9 apply boundaries + fresh-process `resume` converging with no duplicate batch; offline `verify` while the MCP/Cockpit loader refuses; verification mode needs the exclusive lock and the named `applied` journal; lock-held, stale and pending-manifest refusals with no write; third digest stops `resume` and `abort`; crash before the journal keeps a superseded backup; N02-A (vendored merge-commit gate, blob `f28b5f51`) refuses the migrated format-1 workspace; pre-marker abort from fresh processes with a crash after each of steps a–f, repeated, then restart: records equal the backup, no pending manifest, `recover_all` rewrites nothing, no namespace, N02-A result equals the pre-migration one; D10 step g: crash after f, `abort <archived id>` twice, archived `resume`/`verify`/`apply`/`propose` refused, entry/symlink/file preserved; custody shapes (Planner pause, Builder handoff, report-backed Finalizer attention, completed) available after migration with only the marker changed); gate and inspector suites `test_state_formats.py` 85 passed and `test_delivery_diagnostics.py` 138 passed (format/journal mirror parity with the gate); tools `test_delivery_lc.py` + `test_delivery_migration.py` 15 passed (isolation proof positive/negative, copy/compare, container command, stdlib-only import, in-process full form with the N02-A oracle); MCP/Cockpit refusal tests passed; `uv run test --changed --base origin/dev` 2857 pytest passed, Vitest 332 passed (25 files), EXIT 0; scoped Ruff check and format clean; editorconfig ≤ 120 in changed non-test source; disposable live copy (114 records, worktrees excluded): proposal = marker only, `apply` 114/114 records byte-identical, container `verify` (copy at the live path, isolation proof clean) `verified`, every Change available, no record changed by verify+load, live hashes unchanged. LC full form via `delivery-lc run` not yet run (lead); Sol implementation round 1: repair-required (6 + LC TLS) → repaired (uncommitted on `eae65e532`): (1) `verify` refuses pending manifests, then runs every verification read in `storage_io.read_only_state` (transaction recovery, current-frontier canonicalization and retry reconciliation disabled; `RuntimeTransaction` commit/recover/abort, contained and atomic writes raise `ReadOnlyStateError` before any byte); a pretty-printed v18 frontier and a legacy `retry_count` binding keep their bytes and only the journal changes; (2) stage, backup and superseded-backup renames fsync their parent, and each new directory fsyncs its parent, before any journal or record write; (3) every readable registered baseline record (not H/O/L, unread or ownerless) is strictly owner-parsed before staging and again under the apply lock: config `{"schema_version":2}`, a field-less admission and a malformed v18 frontier refuse `record-corrupt` at `propose` and, introduced after it, at `apply`, with no write; (4) the LC D3 oracle needs the typed `state-newer-than-controller` refusal at `runtime/format.json` with unchanged hashes for a downgrade, and for a rollback a load of every Change by the previous release installed from its commit (`git archive`, `uv sync --locked`); (5) the isolation proof keeps mount source and type and rejects the checkout or any ancestor mounted at any point (`/Users` at `/host-users`, Docker Desktop `/run/host_mark` shares), exempting only the container root and pseudo filesystems; (6) load and full forms run the candidate `delivery-diagnose inspect` and require agreement (complete `healthy-structure` with no diagnostic when loaded; only `*_MIGRATION_REQUIRED`, the format one exactly when the gate refuses the marker, when migration-refused); (7) the container trusts the system store (`UV_NATIVE_TLS=1`, `SSL_CERT_FILE`) plus an optional `--ca-bundle`. Proof: `test_state_migration.py` 42 passed (each of the 3 new migration falsifiers fails with its repair undone in-process), `test_delivery_lc.py` 34 and `test_delivery_migration.py` 3 passed (both insufficient oracle shapes, ancestor mounts and inspector disagreement fail), `test_state_formats.py` 85 and `test_delivery_diagnostics.py` 138 passed; `uv run test --changed --base origin/dev` 2886 pytest passed, Vitest 332 passed (25 files), EXIT 0; scoped Ruff check and format clean (10 files); editorconfig ≤ 120 in changed non-test source; `delivery-lc run --form full --dry-run` wrote the container command and `inside.sh`. Container LC full form not yet run (lead). Round-2 repairs (uncommitted on `326b6d7cc`): the isolation proof exempts only the overlay container root `/`, kernel pseudo filesystems under `/proc`, `/sys`, `/dev`, and fresh tmpfs instances (root `/`) under those trees and `/run`; any other overlay or tmpfs bind is inspected like any mount; the load and full forms read through `load_read_only_application` (shared lock, normal gate, no remote bootstrap, provider or stamp, composed and queried in `read_only_state`), and every read phase (inspector, gate, load; unmigrated, migrated, load form) compares the complete record tree (additions, deletions, rewrites; L-class locks excluded) and fails on any change; the previous release's rollback load keeps the normal composition, last. Proof: `test_delivery_lc.py` 45 passed (overlay/tmpfs ancestor binds at `/host-work`, `/dev/shm` and `/run` fail; an ordinary Docker Desktop mount table passes; pretty-printed frontier left byte-identical by the load form, while the normal composition canonicalizes it and fails both forms; addition and deletion fail, lock files ignored); `test_state_migration.py` 42 passed; `uv run test --changed --base origin/dev --py` 2897 passed, EXIT 0; scoped Ruff check and format clean (3 files); ≤ 120 in changed non-test source. Round-3 repairs (uncommitted on `ff64ac049`): tmpfs is exempt only at the exact runtime-created points (`/dev`, `/dev/shm`, `/proc/acpi`, `/proc/asound`, `/proc/scsi`, `/sys/firmware`, `/sys/devices/virtual/powercap`) with `root` `/`, an anonymous source (`tmpfs`, `shm`, `none`) and no second mount at the same point; `/run` and every other tmpfs is inspected like a bind, and because `root` is relative to its own filesystem any mount whose host path is a trailing component sequence of the checkout or an ancestor fails closed; `verify` first validates the backup and requires the record tree (L-class and `runtime/migrations/` excluded) to equal the backup manifest with every proposed entry at its target digest, else `verify-tree-mismatch` with no write and the journal left `applied`. Proof: `test_delivery_lc.py` 52 passed (host tmpfs `/home` at `/run/host-home` with `root` `/`, a host tmpfs subdirectory, a named tmpfs at a runtime point and a second `/dev/shm` fail for live `/home/user/repo`; fresh-looking tmpfs at `/run` fails; ordinary Linux Docker Engine and Docker Desktop mount tables pass); `test_state_migration.py` 44 passed (an altered retry-accounting frontier and an added record after apply are refused as `verify-tree-mismatch` with unchanged hashes and an `applied` journal; restoring the tree verifies); `uv run test --changed --base origin/dev --py` 2906 passed, EXIT 0; scoped Ruff check and format clean (4 files); ≤ 120 in changed non-test source; round-4 repairs (own runs): `delivery-lc run` now `docker create`s, validates `docker inspect` launch provenance (only the stage-root bind at the live path, the control bind at `/lc` and the optional local named uv-cache volume; no other bind, volume, tmpfs, device, `VolumesFrom`, privilege, capability or host PID/IPC) and records it in `launch.json` before `docker start -a`, always removing the container; the in-container proof exempts runtime tmpfs only at points the validated launch shows unmounted; the uv cache must be a named volume (paths refused before any Docker call) whose `docker volume inspect` is `local` with no options or a bind clear of the checkout, checked before create and again after; `_exposes_checkout` also rejects descendants; `test_delivery_lc.py` + `test_delivery_migration.py` 89 passed, including validation of a recorded real `docker inspect` (Docker 29.4.0, dummy stage `/private/tmp/n02b-prov`, fixture `serve/tools/tests/fixtures/delivery_lc/docker_create_inspect.json`); real-Docker launch probe: plain named volume validated, bind-backed cache into a fake checkout refused before create, no containers, volumes or stage left; `uv run test --changed --base origin/dev --py` 2940 passed, EXIT 0; scoped Ruff check and format clean; ≤ 120 in changed non-test source. Lead: full container LC (`delivery-lc run --form full --previous 8d2176927`) PASS on `326b6d7cc`, `ff64ac049`, `0599a3860` and `7500600c7` (launch provenance validated; proposal only `runtime/format.json`; verified; 3 Changes available; inspector healthy; N02-A refuses format 1; read phases unchanged; live unchanged) | Sol implementation round 1: repair-required (6 + LC TLS) → repaired; Sol implementation round 2: repair-required (overlay/tmpfs isolation, read-only LC loads) → repaired; Sol implementation round 3: repair-required (tmpfs provenance, applied-tree verification) → repaired; Sol implementation round 4: repair-required (launch provenance, cache backing) → repaired; Sol implementation round 4: repair-required (launch provenance, cache backing) → repaired; round 5 `implementation-sound` | merged |
| N02-C | #355 | `411590913` | Own runs, macOS, Git 2.56.0: first check (`.owlbear/scratch/n02c/first_check.py`): `subprocess.run(timeout=1)` returns at 1.00 s but leaves the `ext::` helper alive; `run_remote_git(timeout=1)` raises `RemoteGitTimeout` at 1.01 s with the helper gone (D8 confirmed); `test_remote_git.py` 16 passed (noninteractive environment, hung read and write killed by group, detached descendant holding the pipes, rejected write keeps its result, prompt-requiring HTTP remote fails without `GIT_ASKPASS`/`core.askPass`, SSH `BatchMode=yes` unless the user set a command); `test_remote_git.py` + `test_change_publication.py` 153 passed, then with the authority gate 192 passed (`sync..1`/`sync.`/`sync.lock`; private head ≠ `expected_target` → `ChangeTargetSyncStaleError`, the fetch leaves the shared ref unchanged; stale CAS keeps the concurrent value and an exact receipt; two Changes with one operation ID → distinct private refs, correct heads, shared ref unchanged until CAS; a gated slow `ext::` fetch does not block another Change's merge; hung fetch bounded, locks free, retry succeeds; hung branch push read back once, no second push); `tests/test_delivery_worktree_authority.py` 40 passed (fetch gate now reads tuple vectors passed to the runner and admits only `refs/remotes/` and `refs/owlbear/target-sync/` destinations); inner loop `test_remote_git.py` + `test_delivery_state.py` 112 passed (slow `pre-receive` accepts after the lost response → readback success, one push; hung state push → retry-safe, one push; push and readback lost → `DeliveryStateResponseUnknownError`, pending `state-publication.json` kept, restart replays; hung loader bootstrap → retryable `remote-state-unavailable`; loader branch observation bounded), 27 passed again after the `read_remote_ref` refactor; `test_portfolio_application.py -k "target or engine_target or hung"` 55 passed (hung application target sync releases checkpoint, target-sync and publication locks; engine stale-then-sync drift); `uv run test --changed --base origin/dev --py` 2661 passed, EXIT 0 (a prior run on the pre-repair candidate failed the two engine drift cases noted above); scoped Ruff check and format clean (11 files); non-test source ≤ 120 chars. LC full form not run here (lead) | Sol implementation round 1: repair-required (stale shared ref, rewind CAS, SSH config precedence) → repaired (`fa4a73026`): a stale fetch leaves `refs/remotes/<remote>/<target>` unchanged and records the fetched head atomically in `refs/owlbear/target-observation/{head,base}/<remote>/<target>`; `observed_target_head` selects it only while the shared ref still holds the recorded base, so any later shared-ref move (exact sync CAS, operator fetch) supersedes it; the exact-sync CAS ignores ancestry (remote rewind rewinds the engine target) and clears a consumed observation; the runner reads `core.sshCommand` (bounded local `git config`) and keeps it: a configured `ssh` program gets `-o BatchMode=yes` appended, any other wrapper runs unchanged, still with no controlling terminal and askpass disabled; `GIT_SSH_COMMAND` from the user stays untouched. Proof: `test_remote_git.py` + `test_change_publication.py` + `tests/test_delivery_worktree_authority.py` 201 passed (stale private head: shared ref unchanged, engine target = fetched head, exact follow-up sync advances the shared ref and clears the observation; a later operator fetch supersedes an observation; remote rewind → stale → exact sync rewinds the shared ref; configured `ssh` command keeps `-i`/`ProxyCommand` and gains `BatchMode=yes`, a configured wrapper keeps its own options, neither gets a controlling terminal, both fail without waiting); `test_portfolio_application.py -k "target or engine"` 119 passed (engine drift stale-then-sync with the shared ref unchanged after stale; engine rewind sync selects the rewound target with no lingering stale readiness); `uv run test --changed --base origin/dev --py` 2670 passed, EXIT 0; scoped Ruff check and format clean (6 files); non-test source ≤ 120 chars. LC not run here (lead); Sol round 2: repair-required (observation ABA, -c sshCommand, effective BatchMode) → repaired (uncommitted on `fa4a73026`): a stale fetch records the fetched head in `refs/owlbear/target-observation/<remote>/<target>` and appends a value-unchanged marker entry naming it to the shared ref's reflog (`git reflog write`); `observed_target_head` selects the observation only while that marker is the newest reflog entry and its value equals the shared ref. Git appends a reflog entry for every later move of a ref whose reflog exists (also with `core.logAllRefUpdates=false`), so the first move after the marker supersedes the observation for good and an A→C→A move cannot revive it, also after restart; an interrupted recording, a concurrent shared-ref move, a lost or expired marker or a Git without `reflog write` select the shared ref (fail closed); every exact sync deletes the observation, also when the shared ref did not move. The runner reads `core.sshCommand` with the operation's own Git global options (`-c k=v`, valueless `-c k`, `--config-env` in both forms, `-C`, `--git-dir`, `--work-tree`, `--namespace`), returns unset only for `git config` exit 1 (a set empty or valueless command is left to Git, other lookup failures are typed), and inserts `-o BatchMode=yes` straight after a direct `ssh` program token with the remaining shell text verbatim (OpenSSH keeps the first value). Proof (outputs in `.owlbear/scratch/n02c/r2_*.txt`): `test_remote_git.py` 36 passed (every scope — repository, global, system, `GIT_CONFIG_COUNT`, `-c k=v`, `--config-env` in both forms — runs the chosen command with `-o BatchMode=yes` first and its quoted options intact while an outranked repository command never runs; valueless `-c core.sshCommand` fails with Git's own `missing value` and runs no command; real `ssh -G` resolves `batchmode yes` for a configured `BatchMode=no` and `batchmode no` for the user's `GIT_SSH_COMMAND`); `test_change_publication.py` + `tests/test_delivery_worktree_authority.py` 184 passed, then the observation/stale/rewind subset 10 passed after the concurrent-move case was added (ABA by fetch and by `update-ref`, `core.logAllRefUpdates` true and false, before and after restart → shared head; replacement; interrupted recording; exact sync without a shared-ref move clears the observation; a shared-ref move during the stale fetch → shared value, and its later rewind does not revive the observation); `test_portfolio_application.py -k "target or engine or hung"` 119 passed; uncertain-write subset `test_delivery_state.py` + `test_change_publication.py -k "unknown or readback or lost or hung"` 10 passed (lost response → readback success with one push; hung push → retry-safe; push and readback lost → `DeliveryStateResponseUnknownError` with the pending intent kept; hung bootstrap retryable; hung fetch and branch push bounded); inner loop `test_delivery_state.py` + `test_remote_git.py` 132 passed; detached `uv run test --changed --base origin/dev --py` 2690 passed, EXIT 0; scoped Ruff format and check clean (5 files); changed files ≤ 120 chars. LC not run here (lead). Round-2 closeout, builder re-run on the same tree after the session interruption (outputs in `.owlbear/scratch/n02c-r2/`): `test_remote_git.py` + `test_change_publication.py` + `test_change_workspace.py` + `test_delivery_state.py` + `tests/test_delivery_worktree_authority.py` 534 passed, none skipped (the real `ssh -G` case ran); `uv run test --changed --base origin/dev --py` 2690 passed, EXIT 0; scoped Ruff check and format clean (5 files); touched source ≤ 120 chars; committed as `38942a515`. LC full form on `38942a515` (`delivery-lc run --form full --previous 7e6510de4`, the N02-B merge; stage `/private/tmp/n02c-lc3`, `ubuntu:24.04`, uv cache `n00a-uv-cache`; outputs `.owlbear/scratch/n02c-r2/lc_*.json`): launch provenance validated, in-container isolation proof `isolated` with no failure; 132 live records copied; unmigrated copy refused `state-migration-required` with hashes unchanged; `apply` → `applied`, `verify` → `verified`, only `runtime/format.json` changed; migrated gate no refusal, load 3 Changes with none unavailable, inspector `healthy-structure` complete with no diagnostic, no record changed by the reads; N02-B gate on the migrated copy (format 1) no refusal and its release loads the same 3 Changes (supported rollback, D3); synthetic newer format refused `state-newer-than-controller`; `passed: true`, exit 0; `compare`: live records unchanged (132); Sol implementation round 3: repair-required (P2 `git reflog write` is absent in Git 2.43, the Ubuntu 24.04 package, and its failure was ignored, so stale-then-sync progress was silently lost; P2 the observation ref and reflog marker were written separately outside the sync lock and every exact sync deleted observations unconditionally, so concurrent syncs could lose a newer observation; an empty or non-ssh `core.sshCommand` without `BatchMode` accepted under the amended contract) → §1.5 contract review, because the observation produced material findings in all three rounds → D7 amended and repaired (`f3642d6a0`): the reflog marker is removed; a stale fetch records one advisory ref `refs/owlbear/target-observation/<sha256(target ref)>/<base>` for the shared value at fetch start; every observation write and engine shared-ref move runs under the existing target-sync lock as one `update-ref --stdin` transaction compare-and-swapped on the fetch-start shared value and observation set (first writer wins among overlapping fetches; an exact sync deletes only older observations and carries a later one to its new shared value); an unexplained transaction failure raises instead of reporting stale; an external A→C→A return revives the hint, accepted as one stale round. Proof (outputs in `.owlbear/scratch/n02c/r3_*.txt`): `test_change_publication.py` observation/stale/lock subset 39 passed; `test_remote_git.py` + `test_change_publication.py` + `test_change_workspace.py` 401 passed (round 1: stale shared ref, rewind CAS, SSH precedence; round 2: operation-scoped `sshCommand`, `BatchMode`; ABA now proves the revived hint is refused by the exact fetch without a merge and replaced; new: overlapping stale fetches keep the first recorded observation and a later-starting fetch replaces it; recording blocks while a test holds the target-sync lock; an exact sync that began before a stale recording carries it to its new shared value and the follow-up exact sync consumes it; stale-then-exact progress with a PATH Git that rejects `reflog write` and logs no reflog call; an injected `update-ref --stdin` failure raises `newer target head could not be recorded` with refs and worktree unchanged); Ubuntu 24.04 container, Git 2.43.0: `reflog write` fails with 128, and the record, both CAS refusals, move-with-carry and delete transactions behave as specified (`r3_git243_probe.txt`); the same 39-test observation/stale/lock subset of the archived `f3642d6a0` tree, run in that container with Git 2.43.0 and `uv sync --locked`, 39 passed (`r3_git243_tests.txt`); `uv run test --changed --base origin/dev --py` 2693 passed, EXIT 0 (`r3_changed.txt`); scoped Ruff check and format clean (3 files); touched source and test lines ≤ 120 chars. LC full form on `f3642d6a0` (lane-b tool copy, `delivery-lc run --form full --previous 7e6510de4`, stage `/private/tmp/n02c-r3-lc`, `ubuntu:24.04`, uv cache `n00a-uv-cache`; outputs `.owlbear/scratch/n02c/r3_lc_*.json`): launch provenance validated, isolation proof `isolated` with no failure; 132 live records copied; unmigrated copy refused `state-migration-required` with hashes unchanged; `verify` → `verified`, only `runtime/format.json` changed; migrated gate no refusal, load 3 Changes with none unavailable, inspector `healthy-structure`, no record changed by the reads; N02-B gate on the migrated copy (format 1) no refusal with hashes unchanged, and its release loads the same 3 Changes (supported rollback, D3); synthetic newer format refused `state-newer-than-controller`; `passed: true`, exit 0; `compare`: live records unchanged (132); Sol implementation round 4: repair-required (HIGH: a recording was identified only by its ref name `<base>` and head, so an exact sync deleted a newer re-recording of the same head after a C→B remote rewind and selected C, and overlapping stale fetches could both "win"; MEDIUM: exact-sync `_update_refs()` results were ignored and cleanup was a second transaction, so a failed cleanup still merged and receipted while the engine kept selecting the removed head; the D7 residual overstated unlocked reads) → D7 amended after Sol round 4 and repaired (`7e67db129`, `a9ca102ec`): each recording is `refs/owlbear/target-observation/<sha256(target ref)>/<base>/<generation>` with a fresh random generation created in the same `update-ref --stdin` transaction, so compare-and-swap checks distinguish a later recording of the same head; the exact sync plans one transaction (shared-ref move + carry of a later recording + deletion of the fetch-start recordings), replans when a ref changed concurrently (at most three attempts) and otherwise raises `engine target could not be advanced to the exact fetched head` before the merge and receipt; the fetch-start snapshot is read under the target-sync lock (own independent read-only review, MEDIUM: an unlocked snapshot could capture another sync's half-applied transaction); D7 now states that unlocked engine-target reads can briefly miss a recording being replaced or carried, and lists overlapping-fetch ordering (first locked writer wins; an engine A→C→A between a fetch's start and its lock is indistinguishable from no move) and round-3-format refs as accepted residuals. Proof (outputs in `.owlbear/scratch/n02c-r4/`): `test_remote_git.py` + `test_change_publication.py` + `test_change_workspace.py` 406 passed (`focused2.txt`; new: a C→B rewind during an exact fetch with a pre-existing A→B recording keeps B as a distinct newer generation carried to C and the engine selects B; an overlapping stale fetch of C yields to a later same-base recording of the rewound head B; a shared-ref move between plan and transaction is replanned to `verify` with an exact receipt; with the PATH Git shim failing `update-ref --stdin`, exact syncs that rewind and that advance raise before merging with worktree, coordination, shared ref and engine target unchanged, then succeed after the failure clears; the lock test now also proves the fetch-start snapshot waits for the target-sync lock, `locktest2.txt` 1 passed); Ubuntu 24.04 container, Git 2.43.0, archived `a9ca102ec`, `uv sync --locked`: observation/stale/lock subset 44 passed, GIT243_EXIT=0 (`git243_tests_a9ca102ec.txt`; 44 passed on `7e67db129` before the snapshot-lock repair); `uv run test --changed --base origin/dev --py` 2697 passed, 1 failed, EXIT 1 (`changed_final.txt`): `test_target_server.py::test_registered_loader_contains_unknown_custody_without_repeating_effects[sync-target]` hit the 30 s pytest timeout inside a test helper's `git rev-parse` while the LC container and other lanes' suites loaded the host; that test alone, all 3 parameters, 3 passed in 18 s (`rerun_target_server.txt`); scoped Ruff check and format clean (3 files). LC full form on `a9ca102ec` (lane-b tool copy, `delivery-lc run --form full --previous 7e6510de4`, stage `/private/tmp/n02c-r4-lc`, removed afterwards, `ubuntu:24.04`, uv cache `n00a-uv-cache`; outputs `.owlbear/scratch/n02c-r4/lc_*.json`, `lc_isolation.json`): launch provenance validated, isolation proof `isolated` with no failure; 132 live records copied; unmigrated copy refused `state-migration-required` with hashes unchanged; `apply` → `applied`, `verify` → `verified`, only `runtime/format.json` changed; migrated gate no refusal, load 3 Changes with none unavailable, inspector `healthy-structure` complete with no diagnostic, no record changed by the reads; N02-B gate on the migrated copy (format 1) no refusal with hashes unchanged, and its release loads the same 3 Changes (supported rollback, D3); synthetic newer format refused `state-newer-than-controller`; `passed: true`, exit 0; `compare`: live records unchanged (132). Round-3 stages `/private/tmp/n02c-r3-lc` and `/private/tmp/n02c-r3-src` removed; Sol implementation round 5 on `0df74092c`: `implementation-sound`. Merged `origin/dev` `141795676` (N09-A2 #357) as `9cd489b74` (merge, not rebase): the only conflict was `sync_with_target`; the direct `sync-target` marker (`start_direct_operation`) is committed in the first, publication-locked block after the receipt replay and `_require_target_sync_start`, before the fetch snapshot and the unlocked `_fetch_target`; `_merge_fetched_target` re-checks replay and start but starts no marker; `411590913` adds `test_direct_sync_crashed_at_its_fetch_replays_after_restart_then_converts` (crash at the unlocked fetch leaves the marker `started` with no receipt; restart, Pause, identical replay merges, finishes the marker, converts). Proof on `411590913` (`.owlbear/scratch/n02c-merge/`): `test_remote_git.py` + `test_change_publication.py` + `test_change_pause.py` + `tests/test_delivery_worktree_authority.py` 308 passed (`focused.txt`); `uv run test --changed --base origin/dev --py` 2980 passed, exit 0 (`changed.txt`); Ruff check and format clean (2 files). LC full form on `9cd489b74` (lane-b tool, `--previous 141795676`, stage `/private/tmp/n02c-merge-lc` removed afterwards, uv cache `n00a-uv-cache`; `lc_run.json`, `lc_compare.json`): launch validated; unmigrated copy refused `state-migration-required` with hashes unchanged; `apply` → `applied` (format marker plus 3 coordination records), `verify` → `verified`; migrated gate no refusal, 3 Changes loaded, inspector `healthy-structure` complete; the previous release (`141795676`, D3 family-version oracle) refuses before migration, accepts after with hashes unchanged and loads the same 3 Changes; synthetic newer format refused `state-newer-than-controller`; `passed: true`, exit 0; `compare`: live records unchanged (132). Merge resolution awaits review | candidate ready |
| N02-D | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | Every test-created frontier validates under strict JSON | Only the three heaviest Delivery suites were probed, not every consumer suite | Run 1: 47,341 validations; run 2 (complete): about 61,000, no strict-only failure | N02-A (restoring strict reads across all suites proves it) | N02-A merge |
| G2 | The audit's historical 35 failures came from this cause | The 2026-09-05 environment was not recreated | P1/P2 mechanism; baseline note's test-side `strict=False` analysis | None; N02-A proves the current contract | Nothing |
| G3 | VS Code restarts and autostart behave as assumed with the launcher | Not exercised in a real window during P | VS Code MCP configuration reference (`${workspaceFolder}`, cwd default, *List Servers* actions, `dev.watch` only on request) | N02-D host rehearsal | N02-D merge |
| G4 | A release built from a `dev` commit builds its Cockpit bundle reproducibly | P5 copied the live bundle | N00-M rebuilt the bundle with the pinned Node | N02-D | N02-D merge |
| G5 | The offline preflight sees every blocking custody shape, including `engine-action-interrupted` with retained custody | Classification designed from D03 docs and source, not executed | D03 completion ledger; inspector already reports pending effects | N02-D tests on disposable custody fixtures | N02-D merge |
| G6 | Cockpit memory routes stay compatible when Cockpit runs release code while the memory MCP runs checkout code | Memory store versioning is outside N02 | — | `owlbear_memory` owner; noted for N08-C | Nothing in N02 |
| G7 | Multi-host: a newer host's remote snapshot never gets overwritten by an older host | Only one host exists | N02-A refusal tests on a bare remote | N02-A | N02-A merge |
| G8 | `delivery-lc` container run is exercised in CI | Needs Docker and a live copy | Unit tests of isolation proof and report parsing; PR-recorded runs | N02-B | Nothing (recorded per phase) |
