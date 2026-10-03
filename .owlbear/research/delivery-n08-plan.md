# Delivery N08 — Offline Repair Application, Degraded Cockpit and Distribution

> **Package:** N08 of the
> [execution plan](delivery-redesign-execution-plan.md#n08--offline-repair-application-degraded-cockpit-and-distribution).
> **Planned on:** `origin/dev` `ef622c354` (N02-P merged; N01-B, N01-C and N02-A to N02-D not merged; Python
> 3.14.8; uv 0.12.22). Live state observed read-only: main checkout on `delivery-live`.
> **Builds on:** the approved [N02 plan](delivery-n02-plan.md) (lock, gate, migration engine, `delivery-lc`,
> pinning). N08 symbols for N02 modules are the N02 plan's names; implementation re-resolves them on `dev`.
> **Status:** approved: plan gate `plan-sound` in round 7 of fresh GPT-6.1 Sol challenges (2026-10-03). U1–U3 are pending user confirmation. Product code
> is unchanged by this phase.

## 1. Contract

### 1.1 Result

- `/repair-delivery` keeps D03's read-only bootstrap (`delivery-diagnose`) and adds `delivery-repair`: it classifies
  every finding into exactly one route and, for the catalogued recoverable states, stages a fenced proposal and
  applies it offline under N02's exclusive controller lock, journal, backup and verify. Unknown corruption is
  preserved and only diagnosed.
- Cockpit starts when Delivery refuses to load. It serves memory, ideas and the SPA, shows a degraded Delivery panel
  with the refusal, N02's capability report, a **Repair Delivery** control and a **Retry Delivery startup** control.
  A single Change's invalid state never breaks the portfolio list (V18).
- A reviewed, isolated maintenance route exists for platform code defects (programme §11.2).
- Consumer installations get the same pinned controller, launchers, upgrade and migration flow as this repository
  (P21), with a controller-only release environment.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | Fenced proposals for known recoverable states, applied only under policy and confirmation; unknown corruption preserved and diagnosed | Programme §11.1; WP6 step 2; P19 (application), P20 (offline application); V20; R4 |
| R2 | Repair runs offline below application composition; Delivery core never imports tools | §11.1; WP6 proof note; `tests/test_package_boundary.py:19` |
| R3 | Repair writes share N02's fence and journal; a crash at any durable step restarts to the old or the exact new state; never concurrent with an open migration | V21; N02 I5, D5; §11.3 |
| R4 | No rehash, no blessing, no synthesized user-confirmation provenance, no rewrite of self-identified receipts, packages' admitted identity, revision records or remote snapshots | V20; programme §1.1 bounded recovery; N02 I3, I4 |
| R5 | Cockpit is reachable when the controller refuses to load, and shows the maintenance prompt without a healthy `PortfolioApplication` | V18; programme §4.2 (last paragraph and **Repair Delivery**) |
| R6 | A degraded Change stays visible; per-Change corruption never fails the whole portfolio projection | V18; probe P2 |
| R7 | Degraded Cockpit holds no Delivery lock, starts no supervisor and writes nothing after its refusal (D12's class-L record precedes the gate); it is entered only before the loader's first startup effect; retry runs the full gated startup | N02 I1, I5 |
| R8 | Isolated, reviewed platform-code maintenance route with preserved executable, configuration and state, user-approved upgrade and verified smoke | Programme §11.2; WP6 step 4 |
| R9 | Consumer controller selection and upgrade parity with N02 (pin, launchers, preflight, migrate, switch, verify) | P21; WP6–7 step 3; execution plan §5 N08 |
| R10 | Support baseline: Python 3.14, Chromium Cockpit, macOS and Ubuntu; every platform-dependent path has an Ubuntu test | Execution plan §1.1 |
| R11 | LC: full form for N08-A; load form plus refused-copy check for N08-B; upgrade rehearsal for N08-C | Execution plan §1.3, §5 N08 |
| R12 | Each new health reason or status ships with its `workItems.ts` mirror, rendering, component test and `tests/test_cockpit_boundary.py` parity | Execution plan §1.4 |

N08 owns V18 (Cockpit half) and the application half of V20. It keeps D03's V18/V20 offline-diagnosis proof green.

### 1.3 Invariants

- **I1 One fence.** Repair `apply`, `resume`, `verify` and `abort` take `runtime/controller.lock` exclusively and
  non-blocking through the same helper as `delivery-migrate` (N02-B). A controller that holds it shared refuses
  them. Below format 1 ungated controllers do not take the lock (N02 I5), so each of these four commands first scans
  same-user processes (`psutil_user_processes`) and refuses `repair-controller-running` when one whose cwd is at or
  under the workspace runs a supported form: module `owlbear_delivery_mcp` or `owlbear_cockpit` (`-m`, directly or
  under `uv run` or `uv --project <clone> run`, the seed form), the `cockpit` console script (directly, through its
  interpreter or `uv run cockpit`) or an N02-D launcher `bin/delivery-mcp` or `bin/cockpit`. Uncertainty fails
  closed with `repair-controller-unknown`: no process table, or an unreadable cmdline or cwd of a same-user Python,
  `uv`, `cockpit` or `delivery-mcp` process (P5, G7). `flock` stays the portable fence.
  **Gated exemption.** A matching process is exempt only when positively identified as gated: its record
  `runtime/controller-processes/<pid>.json` (class L, D12) parses and equals its pid, create time and cmdline
  digest. Such a process takes `controller.lock` shared before any Delivery load or write (its only other read is
  N02's stdlib scan, I6), so the exclusive fence excludes it (degraded Cockpit, N08-B). A `uv run` wrapper is
  exempt only when every supported-form descendant is. A command name, a free lock or an absent, unreadable or
  mismatched record never exempts.
- **I2 One open journal.** Migrations and repairs share `runtime/migrations/<id>/journal.json`. At most one journal
  is non-terminal (`backed-up`, `applying`, `applied`, `aborting`); retained migration `verified` history (N02 §3.3)
  never blocks. [Journal states](#journal-states) is the one rule for commands, both gates and routing (C04). A
  repair journal closes through I9, so remaining findings never hold it open and block the next proposal.
- **I3 Repairs never change the format.** Source and target format are equal. A verified or aborted repair journal
  is archived to `.owlbear/delivery-migrations/<id>/` and removed from `runtime/migrations/`; the namespace is then
  removed when empty, so authoritative state at rest has no repair trace and every gated release that accepted the
  state before still accepts it (N02 D3 rollback oracle). N02-A refuses on the namespace alone, even empty (§3.5
  premise 10). **Namespace cleanup** is the last step of repair `verify` and of repair `abort` (after N02 §3.3 step
  5f's archive), under I1's exclusive fence: a no-follow `rmdir` of `runtime/migrations` only when it is a real
  directory with no entry. Any entry, a symlink or a non-directory stays untouched, so a nonempty namespace and
  retained migration history survive. After a crash between archive and cleanup, `delivery-repair verify` of an
  archived verified repair ID, or `delivery-repair abort` of an archived aborted repair ID, runs only the cleanup;
  a repeat is a no-op; the other command on that archived ID refuses without a write
  ([journal states](#journal-states)). Migration `abort` owns the same cleanup for an aborted migration (N02-B
  prerequisite: N02 §3.3 step 5g and D10, amended by this plan) and resumes it only through
  `delivery-migrate abort <archived migration ID>`; repair commands never operate on migration IDs.
- **I4 Exact before-state.** `apply` re-reads every affected path (for C03 also every manifest of every registered
  root and every participant path, absent ones included) and refuses a stale proposal. `resume` and `abort`
  compare each path with its before and after digests; a third digest stops with all copies preserved.
- **I5 Never.** Recompute a stored identity over altered bytes; write request provenance; rewrite receipts,
  revision records, remote snapshots, completion evidence or an admitted package identity; delete authoritative
  bytes (every replaced byte string is in the backup first); call a network or provider, except N08-C's
  `target-ref-fetch` read through N02-C's bounded runner.
- **I6 Degraded Cockpit is read-only.** No Delivery write, lock or supervisor after a refusal. `degraded` follows
  only a refusal before the loader's effect boundary (D5), so state is unchanged; a failure after it is
  `maintenance` with `startup_effects: started`. It reads only the refusal and N02's stdlib capability scan. HTTP
  details are bounded (240 characters) and contain no absolute path or record value.
- **I7 Bootstrap first.** `/repair-delivery` always starts with the stdlib inspector. `delivery-repair` imports only
  the stdlib at module load and imports Delivery inside `main`; any exception there is a C09 finding (class name
  only) routed to maintenance and reported beside the stdlib inspector's findings.
- **I8 One route per finding.** Every finding names exactly one route, its owner and an honest resume condition.
- **I9 Repair verification is scoped and bound to its journal.** Repair `verify J` (offline, under the fence)
  first checks the journal set by [journal states](#journal-states): J is valid (kind `repair`, state `applied`,
  proposal ID, backup manifest); every other journal is a valid migration `verified` journal whose ID and SHA-256
  are in the set that `apply` recorded in J. It checks the addressed postcondition (every affected path at its
  after digest; the owner check: C01 overrides parse, C02 owner model or package verification, C03 no proposal
  manifest left), that every identity outside the affected paths is preserved (record-tree hash against the backup
  manifest), and that `classify` in a verification context bound to J (N02-B's verification-mode gate) returns
  exactly the proposal-time findings minus the addressed one. The context drops only J's
  `state-migration-incomplete` and keeps every unrelated finding. It then marks J `verified`, archives it and runs
  namespace cleanup (I3); remaining findings keep their refusal and route (for example `state-migration-required` →
  `delivery-migrate`).
  A new or changed finding, or any other journal that is non-terminal, invalid, added or changed, stops with
  `repair-verify-mismatch`; J stays `applied` and `abort` remains available. N02-B's migration verification (every
  Change available) is unchanged.

#### Journal states

The one rule for every journal in `runtime/migrations/`, reconciled with N02 §3.3 (states, `aborting`, archive).
"Blocks": `propose` and `apply` of both kinds refuse `repair-journal-open` and name it. J is I9's named journal.

| Kind and state | Commands allowed | Blocks | Normal startup gate (N02-B) | Verification-mode gate, repair `verify J` (I9) | `classify` route |
| --- | --- | --- | --- | --- | --- |
| migration `backed-up`, `applying` | `delivery-migrate resume`, `abort` | yes | refuses `state-migration-incomplete` | refuses | C04 → `delivery-migrate resume` or `abort` |
| migration `applied` | `delivery-migrate verify`; `abort` only before the format marker (N02 §3.3 step 5) | yes | refuses | refuses | C04 → `delivery-migrate verify` |
| migration `aborting` | `delivery-migrate abort` only | yes | refuses | refuses | C04 → `delivery-migrate abort` |
| migration `verified` (retained history) | none needed | no | accepts | accepts when valid and its ID and SHA-256 are in the set `apply` recorded in J; otherwise refuses | no finding |
| migration aborted and archived, cleanup pending (crash after N02 §3.3 step 5f; `runtime/migrations` empty) | `delivery-migrate abort` of that archived migration ID runs only the cleanup (N02 step 5g); a repeat is a no-op; repair commands refuse migration IDs | no | accepts when N02-B ignores an empty namespace (G3); N02-A refuses (§3.5 premise 10) | not entered (no journal) | C04 → `delivery-migrate abort` with the newest archived ID, when it is an aborted migration |
| repair `backed-up`, `applying` | `delivery-repair resume`, `abort` | yes | refuses | refuses (J must be `applied`) | C04 → `delivery-repair resume` or `abort` |
| repair `applied` | `delivery-repair verify`, `abort` (D1); `resume` converges | yes | refuses | accepts only as J; drops only J's `state-migration-incomplete` | C04 → `delivery-repair verify` or `abort` |
| repair `aborting` | `delivery-repair abort` only | yes | refuses | refuses | C04 → `delivery-repair abort` |
| repair `verified`, archive pending (crash after the mark) | `delivery-repair verify` finishes the archive and namespace cleanup idempotently | yes | accepts (N02: any `verified`) | refuses | C04 → `delivery-repair verify` |
| repair archived, cleanup pending (crash after the archive; `runtime/migrations` empty) | `delivery-repair verify` of any archived verified repair ID runs only the cleanup (I3); a repeat is a no-op | no | accepts when N02-B ignores an empty namespace (G3); N02-A refuses (§3.5 premise 10) | not entered (J archived) | C04 → `delivery-repair verify` with the newest archived repair ID, when that repair was verified |
| repair aborted and archived, cleanup pending (crash after the abort archive; `runtime/migrations` empty) | `delivery-repair abort` of any archived aborted repair ID runs only the cleanup (I3); a repeat is a no-op | no | accepts when N02-B ignores an empty namespace (G3); N02-A refuses (§3.5 premise 10) | not entered (J archived) | C04 → `delivery-repair abort` with the newest archived repair ID, when that repair was aborted |
| unreadable or invalid; unknown kind, state or version; a second non-terminal journal | J's digest-checked `abort` (I4); J's `verify` refuses `repair-verify-mismatch`; all else `repair-corruption-stop` | yes | refuses | refuses | C07 (contained) |

Archived journals (`aborted`, N02 §3.3 step 5f; verified repairs, I3) live in `.owlbear/delivery-migrations/<id>/`;
no gate reads them; only repair `verify` (verified) and repair `abort` (aborted) read their own archived repair ID,
and `delivery-migrate abort` its own archived aborted migration ID, to resume cleanup. A verified or aborted repair
or an aborted migration leaves no empty `runtime/migrations/` behind (I3; N02 step 5g); every nonempty
namespace stays. Migration `verify` keeps N02-B's rule and reads
retained `verified` history as accepted, as normal start does (§3.5 premise 8).

### 1.4 Repair catalogue

Derived from probes P1–P2, P9 and the online repair owners in source. Routes: **offline** (`delivery-repair`
operation), **migrate** (`delivery-migrate`, N02-B), **upgrade** (`/upgrade-delivery`, N02-D), **online** (named
MCP tool and Cockpit control; the controller starts because the failure is per-Change), **environment** (exact
agent instruction), **contained** (preserve, report owner), **maintenance** (§11.2 route, N08-C).

| ID | Finding (evidence) | Route | Policy |
| --- | --- | --- | --- |
| C01 `host-local-reset` | `runtime/host.local.json` unreadable or invalid; whole-app refusal (P1) | offline: replace with canonical empty overrides `{"schema_version":1}` after backup | user-confirmed (host tuning returns to `host.json` defaults) |
| C02 `tracked-record-restore` | `config.json`, `runtime/host.json` or a package file invalid in the working tree while its `HEAD` blob verifies with its owner (config/host model; package manifest digests and, for an admitted Change, the admission's package identity) and differs (P1, P2) | offline: write the `HEAD` bytes after backup | user-confirmed (discards uncommitted edits) |
| C03 `transaction-replay` | Pending `RuntimeTransaction` manifests while start is refused, which also blocks `delivery-migrate apply` (N02-B) (P9); offered only when every manifest of every registered root passes its root's owner validator (D1) and every participant precondition holds, otherwise all are C07 | offline: replay exactly the proposal's manifest set, one journaled step per manifest, under the fence (D1); never `recover_all` or `recover_contained` | engine replay |
| C04 | `state-migration-required`, `state-migration-incomplete` (N02) | by [journal states](#journal-states): the open journal's kind and state name `delivery-migrate` or `delivery-repair` and the command; `migration-required` → `delivery-migrate propose/apply/verify`; invalid journal → C07 | per N02-B; repair per U1 |
| C05 | `state-newer-than-controller` | upgrade to a release whose registry includes the format; never a downgrade | user (N02-D procedure) |
| C06 | Per-Change: missing request provenance, quarantined or invalid remote snapshot, local frontier mismatch, out-of-band head, target-sync publication, unknown publication baseline, missing worktree | online: `repair_stranded_frontier`, `repair_quarantined_delivery_state_snapshot`, `repair_delivery_state_snapshot`, `recover_out_of_band_head`, `repair_target_sync_publication`, `recover_publication_baseline`, `recover_change_worktree` | the existing tool's confirmation |
| C07 | Transaction manifest failing its owner validator (P1: untyped `TransactionManifestError`), invalid or second non-terminal journal ([journal states](#journal-states)), invalid self-identified receipt, unknown or unrecognized version, package with no verifying `HEAD`, frontier invalid without a registered repair | contained | none; preserved |
| C08 | Not the primary worktree; Git unavailable; remote, target or GitHub repository mismatch; missing remote-tracking target | environment: rerun `setup/init.py` with the named option; N08-C adds `target-ref-fetch` (bounded read) | agent |
| C09 | Gate passes and typed records validate, but load or composition raises an unregistered exception; or `delivery-repair` cannot import | maintenance | user (U3) |

### 1.5 Interfaces and error cases

| Interface | Behavior |
| --- | --- |
| `owlbear_delivery.state_repair` (new, N08-A) | `classify(workspace_root, change_id=None) -> RepairReport`; `propose(root, finding_id) -> RepairProposal`; `apply`, `resume`, `verify` (I9), `abort` run through `state_migration` with operation kind `repair`. Imports N02's `state_formats` and `state_migration`, `runtime_transaction`, `storage_io` and owner models. Never calls `load_delivery_application` or constructs `PortfolioApplication`. Importing it runs the package `__init__`, which imports the loader and application (`__init__.py:91,226`); `delivery-repair` owns that failure (I7) |
| `RepairFinding` | `finding_id`, `code`, `scope` (`workspace` or a Change ID), safe `locator`, `route`, `operation` (catalogue ID or MCP tool), `owner`, `resume_condition` |
| `RepairProposal` | `proposal_id` = SHA-256 of the canonical (operation, operation version, sorted (path, before digest or `absent`, after digest or `absent`), format, release commit or `checkout`); for C03 also every (manifest path, manifest digest) of every registered root and, per participant, its kind, destination and move source; `policy` (`engine-replay` or `user-confirmed`); `consequence`; staging under `.owlbear/delivery-migrations/<proposal_id>/stage/` |
| `delivery-repair` (new console script in `serve/tools`) | `classify [--change-id] [--format json]`, `propose FINDING`, `apply --proposal ID [--confirm ID]`, `resume ID`, `verify ID`, `abort ID`. Exit 0 healthy or done, 1 findings or refusal, 2 invalid invocation. Never echoes record values or absolute paths. Imports only the stdlib at module load; imports `state_repair` inside `main` and turns any exception there into a C09 finding plus the stdlib inspector's findings, exit 1 (I7) |
| Refusal codes | `repair-controller-running`, `repair-controller-unknown`, `repair-journal-open`, `repair-proposal-stale`, `repair-confirmation-required`, `repair-not-supported` (contained, environment or online finding), `repair-format-unsupported` (newer state), `repair-corruption-stop`, `repair-verify-mismatch` |
| Loader effect boundary (N08-B) | `load_delivery_application` runs lock, gate and a read-only preflight before any effect: `_validate_git_config`, `_load_host_config`, `RuntimeTransaction.read_pending` over every registered root with its owner validator (D1; any invalid manifest refuses `transaction-manifest-invalid` before any replay) and, when none is pending, N02-B's verification-mode composition. Remote restoration, replay and composition follow. `DeliveryApplicationLoadError.effects_started` separates the two; every failure after acquisition releases the controller lock |
| Cockpit `GET /api/delivery/startup` (N08-B) | `mode` (`available`, `degraded`, `maintenance`), `refusal` (`code`, `field`, bounded `detail`, optional `exception_class`), `startup_effects` (`none` or `started`), `capability` (at most 64 non-current records: family, status, safe locator), `repair_prompt`, `retry_allowed`. `maintenance` when the code is `controller-fenced` or `state-migration-incomplete`, or effects started |
| Cockpit `POST /api/delivery/startup/retry` | JSON body required. Re-runs the gated startup under a process lock; on success installs the application and starts the supervisor; `409` when already available |
| Delivery routes while not available | Every `/api/work-items`, `/api/changes`, `/api/design-work` route returns `503` `{"code":"DELIVERY_UNAVAILABLE"}`; `/health/*`, memory and ideas are unchanged |
| `DeliveryHealthReason.PACKAGE_INVALID` (N08-B) | A Change whose package fails verification stays in the projection with this health diagnostic; `list_changes` no longer raises |

### 1.6 Existing owners to reuse

- N02-B `state_migration` (fence, journal, backup, replay, the restartable `aborting` protocol of its §3.3 step 5,
  offline verification-mode load, also used by the loader preflight) and N02-A `state_formats.scan_capability`
  (`CapabilityReport`, "the contract N08 renders in degraded Cockpit", N02 §1.5).
- `RuntimeTransaction` and `TransactionParticipant`/`ReplacementTransactionParticipant`, with both owner validators
  (`_from_manifest`; `_contained_manifest_transaction`, `runtime_transaction.py:274-291`); `storage_io.locked_roots`;
  `worker_stall.psutil_user_processes` and its cwd checks for I1's ungated-controller check.
- `delivery_diagnostics` (stdlib bootstrap) unchanged in role; only its maintenance text changes.
- `DeliveryUnavailableChangeView` and `_unavailable_change` (`application_recovery.py:1520-1553`) for per-Change
  visibility; `CopyCommand.tsx` for the Repair Delivery control.
- N02-D `delivery-controller` (`install --source`, `pin`, launchers, `preflight`, `switch`, `prune`) and
  `/upgrade-delivery`; N02-C `remote_git` for `target-ref-fetch`; `delivery-lc` for LC and rehearsals.
- `setup/init.py` manifest claims (`_write_mcp`, `_merge_claims`) to recognize an unmodified OwlBear-installed entry.
- The maintained E2E seed `serve/cockpit/web/e2e/support/seed-work-portfolio-delivery.py` for degraded fixtures.
- `build-reviewer` (exact-commit review) for the maintenance route.

### 1.7 Exclusions

New online repairs; automatic repair without the route's policy; degraded MCP server (D8); repair of arbitrary
corruption or filesystem loss; Cockpit applying repairs; automatic dirty-worktree recovery; Cockpit **Upgrade**
control (N02 U2); a shared user-level release store; memory-store versioning (`owlbear_memory`); Windows; changes to
`/continue-change` routing when MCP is down (N09 input, see G9).

### 1.8 Decisions

Agent-settled with probe evidence:

- **D1 Repairs reuse N02-B's engine.** A repair is a second operation kind of `state_migration`, not a new journal,
  lock or backup mechanism (I1–I3). This also makes the conflict rule with migrations structural: one journal
  namespace, one open journal, one fence. If N02-B's merged journal cannot express a same-format operation, N08-A
  registers a journal version with a read-upcast in `state_formats.py` (N02 D5) and lists that file (G3).
  Repairs do not inherit the migration commit point (the format marker). A repair commits at `verified` (I9);
  before it, `abort` runs N02-B's restartable `aborting` protocol from `backed-up`, `applying` or `applied` and
  restores the complete before-state from the backup (C03: participant paths, absent ones included, then the
  original manifests), archives the journal `aborted` (N02 §3.3 step 5f) and ends with namespace cleanup (I3);
  after `verified`, `abort` refuses. C03 calls neither recovery boundary; both rediscover manifests
  and delete them after publication (`recover_all`, `runtime_transaction.py:295-302,416`; `recover_contained`,
  `:249-272`, run by `FinalizationReportStore._locked` and `ProofAttemptStore._locked` on every read,
  `finalization_reports.py:537,765`). The root map registers each root with its owner validator: generic
  (`_from_manifest`) or contained (`.yaml` name, size and count bounds, one or two same-root non-move participants,
  reconstructed-manifest equality). `read_pending` and C03 use that validator, never a generic parse, and replay
  contained manifests through the contained publish path under the root's `.storage.lock`. `propose` hashes the
  exact manifest set and every participant before-state; `apply` revalidates that set under the fence, backs up
  the manifests and the before-state, journals one step per manifest and replays it from its verified bytes;
  `resume` replays a manifest still at its digest and accepts a missing one only when all its paths are at their
  after digests. Only C03's `apply` accepts pending manifests, and only its own set. `classify` never opens either
  report store.
- **D2 Catalogue v1 is evidence-bound.** Only C01–C03 write offline. Per-Change states route to the seven existing
  online tools, because P1 shows those Changes stay loadable as unavailable. No new online repair is added.
- **D3 C01 replaces, never deletes.** Canonical empty overrides are a valid `host.local.json`; the original bytes
  live in the backup. C01 and C02 need no absent state. C03 does (created destinations, removed move sources and
  manifests), so its digests allow `absent`, and `abort` removes a path only when its before-state is absent and
  its bytes are in the backup.
- **D4 C02 restores only verifying `HEAD` bytes.** Restoring an unverifiable or foreign version would bless content.
  For a package, the `HEAD` set must verify against its manifest and, if admitted, equal the admission's package ID.
- **D5 The no-write guarantee comes from the loader, not Cockpit's handler.** `_load_target_runtime` catches only
  `RuntimeError` (`main.py:297`); `TransactionManifestError` is a `ValueError` (`runtime_transaction.py:52`) and
  crashed Cockpit with a traceback (P1). A broader catch alone is unsafe: the loader restores remote state before
  composition (`delivery_application_loader.py:2443`), and `PortfolioCoordinator.__init__` replays every manifest
  of its root in order (`change_workspace.py:1871`). N08-B therefore splits the loader at one effect boundary
  (§1.5): lock, gate and a read-only preflight first, then effects. Cockpit is `degraded` only for a refusal
  before the boundary and `maintenance` with `startup_effects: started` after it, never claiming unchanged state.
  It records the exception class, never its text. In-process retry replaces a restart. A Delivery import failure
  still exits Cockpit (`main.py:42-43` import Delivery at module load); `/repair-delivery`'s fallback routes it.
- **D6 Cockpit renders N02's capability report, not the tools inspector.** Cockpit may not import tools
  (`tests/test_package_boundary.py:11`), and the scan is a stdlib leaf in Delivery.
- **D7 Controller-only releases.** `uv sync --locked --no-dev --package owlbear-delivery-mcp --package owlbear-cockpit
  --package owlbear-tools` builds a 50 MB environment in 1 s from cache with every controller import and no
  knowledge, torch or Playwright (P7), against a 1.3 GB full lane venv (P6). This settles N02 U3's "revisit package
  restriction in N08-C"; N08-C adopts it in `delivery-controller install`.
- **D8 MCP stays fail-closed.** The MCP lifespan builds the application before serving tools
  (`server.py:110-118`); a degraded MCP mode adds surface without a user need, because `/repair-delivery` runs without
  MCP and Cockpit shows the prompt.
- **D9 Confirmation is an operator assertion.** The journal records `confirmed: <proposal_id>` for user-confirmed
  operations; it is never written into a Delivery request or used as request provenance.
- **D10 Retire the `D07` references.** The maintenance text (`delivery_diagnostics.py:253`) and the prompt
  (`repair-delivery.prompt.md:22`) name a retired package; N08-A replaces them with the N08 route.
- **D11 This P revision amends execution plan §5 N08** (phase descriptions only; no sequence, prerequisite or
  re-split change): N08-A is a repair kind of N02-B's engine in Delivery with a tools CLI; N08-B also edits Delivery
  core (V18 per-Change containment and the loader effect boundary). Merged under the user's overnight
  authorization of 2026-10-03; explicit confirmation pending. After Sol round 6 it also amends the approved
  N02 plan §3.3 (step 5g: migration `abort` removes the empty namespace; N02 D10) under the same authorization.
- **D12 Gated controllers identify themselves.** After it acquires the shared lock and before the gate, N08-B's
  shared-lock helper publishes `runtime/controller-processes/<pid>.json` (pid, `psutil` create time, cmdline
  SHA-256) descriptor-contained (`read_contained`, `write_contained`). Identical existing bytes are an idempotent
  no-op (a degraded Cockpit's retry). `write_contained` raises on any other bytes unless they are passed as
  `expected` (`runtime_transaction.py:535-539`), so a crash record whose pid is reused would block every start.
  The helper therefore reads the existing bytes (bounded, no-follow) and replaces them with `expected=<those bytes>`
  only when they parse as a record for this pid whose create time differs from this process's: no live process
  holds that identity. Unreadable, oversize, non-regular or malformed bytes, another pid, or this create time with
  another cmdline digest fail closed: nothing is written, the process has no record and is never exempt (I1), and
  startup continues under its shared lock. At exit the record is unlinked only when a contained read still equals
  its own bytes. Records of other pids are never pruned; a stale one never exempts (I1 compares create time). A
  fenced start writes nothing and stays excluded. The record is class L, so tree hashes exclude it (N02 §1.4),
  and degraded Cockpit writes nothing after its refusal (I6). Rejected: release-launcher identity, which unpinned
  workspaces lack (N02 D1, I6); an environment marker, which children inherit.
  Engineering decision (Sol round 4: a reasonable default, not a user question): an unsafe record keeps startup
  available without exemption; the cost is that offline repair waits until that controller stops.

User decisions ([U1–U3](#u-decisions)) are **pending user confirmation**; recommendations are defaults, not
decisions. N08-A needs U1; N08-B needs none; N08-C needs U2, U3 and N02's U1 and U2 as recommended there (any other
N02 answer re-plans N08-C, whose launchers and prompt assume N02 D1 and `/upgrade-delivery`).

#### U decisions

**U1 — Offline repair confirmation policy** (pending user confirmation — required before N08-A starts).
Status quo: D03 offline repair is read-only; each online repair tool requires `confirmed_repair: true`. Problem:
offline writes run while the controller is down, so the policy decides which writes an agent may apply inside
`/repair-delivery`. Options: (a) engine-replay operations (C03, delegated `delivery-migrate resume/verify`) are
applied by the agent after it shows the proposal; operations that replace user-owned or tracked bytes (C01, C02)
need an explicit per-proposal confirmation through `vscode_askQuestions` naming paths, consequence and backup;
(b) every offline write needs per-proposal confirmation; (c) the agent applies every catalogued operation without
confirmation. **Recommended: (a).** It matches programme §1.1 (engine-owned effects with exact identity reconcile
automatically) and keeps every loss of user bytes behind a decision. Stopping the controllers is a user step in
every option.

**U2 — Consumer controller distribution** (pending user confirmation — required before N08-C starts).
Status quo: consumers run `uv --project <OwlBear clone>` for every MCP server (`seed/.vscode/mcp.json:6`) and
`git pull` changes live code; `init.py` keeps any existing server entry (`setup/init.py:406`). Problem: P21 requires
pinning parity, which changes what setup installs and rewrites. Options: (a) `init.py` installs a controller-only
release (~50 MB, D7) from the clone's `HEAD` on first run with a visible notice, points `owlbear-delivery` at the
launcher, and on rerun replaces only an unmodified OwlBear-installed entry (recognized by its manifest claim);
upgrades only through `/upgrade-delivery`; (b) pinning is opt-in (`--pin-controller`), unpinned by default;
(c) a shared user-level store `~/.owlbear/controllers/` deduplicated across projects. **Recommended: (a).**
Parity is the requirement and the measured size removes the reason for (c), whose cross-project pruning is new risk.

**U3 — Platform-defect maintenance releases** (pending user confirmation — required before N08-C starts).
Status quo: no route; a broken controller blocks Delivery until someone edits code. Problem: §11.2 needs a reviewed
fix and an approved upgrade, and the release source is a permission question. Options: (a) this repository: the fix
is a normal reviewed PR to `dev`, and the controller upgrades to the merged commit; pinning a reviewed but unmerged
commit is an emergency that needs the user's explicit approval at that step; consumers: only commits of their
OwlBear clone, local patches unsupported, the route reports the defect upstream; (b) consumers may pin a locally
patched, locally reviewed commit; (c) merged commits only, no emergency path. **Recommended: (a).**

## 2. Feasibility Probes

All probes ran on `ef622c354` in this lane, in disposable directories under the system temp directory. Live state
was only read (P3). Scripts and outputs: `.owlbear/scratch/n08p/` in this lane (unversioned).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | `p1_degraded_matrix.py`: 16 cases on the maintained E2E seed; one corrupted record each; default loader, `list_changes`, Cockpit `load_target_context`, Cockpit process start (port 8521, no browser), stdlib inspector; `.owlbear/delivery` hash before and after | See [P1 matrix](#p1-matrix). Frontier, contract and admission corruption leave the app loadable with the Change unavailable. `host.local.json`, `host.json` and `config.json` refuse the whole app with typed errors; a garbage transaction manifest crashes Cockpit with an untyped `TransactionManifestError` traceback. No load wrote state | C01–C03, C07; D5; V18 per-Change half works except P2 |
| P2 | `p1b_package_manifest.py`: invalid package manifest; tampered `design.md` | Load succeeds; `get_change` works for both Changes; `list_changes` raises `DesignPackageConflictError` for the whole portfolio. Cause: `_portfolio_operating_view` calls `self._package_store.list_verified()` (`application_readiness.py:380`), which raises on the first bad package | R6; N08-B containment; C02 for packages |
| P3 | Lane `delivery_diagnostics.py inspect --project-root <main checkout> --format json` (read-only) | `healthy-structure`, complete, 3 frontiers, 3 coordination, 12 per-Change records, 9 packages, 0 pending transactions | No live state needs repair now; catalogue is fixture-driven; LC copy expects no findings |
| P4 | `p3_lock_process.py`: `flock` on macOS | Two `LOCK_SH` holders coexist; `LOCK_EX\|LOCK_NB` fails while any shared holder lives, also after one holder is killed; succeeds after all holders die (kernel release on `SIGKILL`); succeeds with no holder | I1, I6: degraded Cockpit without a lock never blocks repair; a crashed controller never leaves a stale lock |
| P5 | Same script: `psutil.process_iter` with `cwd()` | Finds a child process by its working directory | I1 ungated-controller check (macOS; Ubuntu in CI, G7) |
| P6 | `p5_release_size.py`: `uv export --frozen --no-dev` for all packages versus `owlbear-delivery-mcp`, `owlbear-cockpit`, `owlbear-tools`; sizes from the lane venv's `RECORD` files | 137 versus 39 third-party distributions; 1,238 MB versus 33 MB; the largest exclusions are torch 524 MB, playwright 138 MB, pyarrow 127 MB | D7 |
| P7 | `p5b_restricted_sync.sh`: `uv sync --locked --no-dev --compile-bytecode` with three `--package` options into a temp environment | Exit 0 in 1 s (cache); 50 MB; imports `owlbear_delivery_mcp.server`, `owlbear_cockpit.main`, `owlbear_tools.delivery_diagnostics`, `owlbear_memory.engine`; `owlbear_knowledge`, `torch`, `playwright` absent; `cockpit` and `delivery-diagnose` scripts present | D7; U2 option (a) cost |
| P8 | `git ls-tree -r --name-only origin/main -- serve/cockpit/dist` | 369 bundle files at `f9c36cbdd` (2026-10-03) | Consumer releases take the bundle from a `main` archive without Node |
| P9 | `pytest serve/delivery/tests/test_runtime_transaction.py -k "recover or manifest"` | 15 passed: recovery and manifest rejection run on bare `tmp_path` roots with no application | C03 runs below composition; C07 for unparseable manifests |
| P10 | Source reads: `main.py:293-299` (`except RuntimeError`, `sys.exit(1)`), `target_context.py:22-38`, `server.py:110-118`, `tests/test_cockpit_launch.py:71` (`SystemExit` on load failure), `setup/init.py:406` (user entries win), `seed/.vscode/mcp.json:6`, `tests/test_package_boundary.py:11,19` | Cockpit and MCP exit on any load failure today; consumers run unpinned; Cockpit may import only Delivery, GitHub provider and memory | D5, D6, D8; U2 |

### P1 matrix

`work-e2e` is the corrupted Change; `publication-e2e` is the control.

| Case | Inspector | Default loader and `list_changes` | Cockpit |
| --- | --- | --- | --- |
| baseline | `healthy-structure` | loaded; both available | context loaded |
| frontier invalid JSON | `FRONTIER_MALFORMED` | loaded; `work-e2e` unavailable `runtime-unavailable`; health `frontier-invalid` | loaded |
| frontier schema 19 | `FRONTIER_UNSUPPORTED` | as above | loaded |
| contract `{}` | `CONTRACT_UNSUPPORTED` | unavailable; health `contract-invalid` | loaded |
| admission `{}` | `ADMISSION_UNSUPPORTED` | unavailable; health `admission-invalid` | loaded |
| state publication `{}` | `STATE_PUBLICATION_UNSUPPORTED` | available; health `state-publication-invalid` | loaded |
| coordination invalid | `COORDINATION_MALFORMED` | available; **no health diagnostic** (G4) | loaded |
| retry ledger invalid | `RETRY_LEDGER_MALFORMED` | available; log "Retry accounting remains contained" | loaded |
| claim issuer invalid | `CLAIM_ISSUER_MALFORMED` | available; no diagnostic | loaded |
| completion display invalid | `healthy-structure` | available | loaded |
| finalization `current.json` invalid | `healthy-structure` | available | loaded |
| package manifest invalid | `healthy-structure` | load ok; **`list_changes` raises** (P2) | context loaded; work list would fail |
| transaction manifest garbage | `PENDING_TRANSACTIONS` | `TransactionManifestError` from `PortfolioCoordinator.__init__` (`change_workspace.py:1871`) | process exit 1 with traceback |
| `host.local.json` invalid | `HOST_LOCAL_MALFORMED` | `DeliveryApplicationLoadError` (`execution_capacity`) | exit 1; message has an absolute path |
| `host.json` invalid | `HOST_MALFORMED` | `DeliveryApplicationLoadError` (`host_config`) labelled "host-local" (`delivery_application_loader.py:314`, G8) | refused |
| `config.json` `{}` | `CONFIG_UNSUPPORTED` | Pydantic `ValidationError` | exit 1 "requires valid Delivery configuration" |

## 3. Phases

### 3.1 Shared rules

- Plans name symbols. Re-resolve files after N01 (`application_*`, `workspace_*`, `runtime_*` mixins) and N02
  (`state_formats`, `state_migration`, `remote_git`, `delivery_controller`, `delivery_lc`) with `grep` before editing.
- N08 never runs a repair, migration or upgrade against live state. All proof uses disposable portfolios and
  `delivery-lc` copies; the first live use is a user-authorized step after N02-D or N10-M.
- Assembled claims use the default loader, the Cockpit HTTP client, `Client(assemble_target_server(...))` and the
  maintained work-portfolio E2E stack. Fakes sit only below the filesystem fault injector, the process lookup and
  the remote Git runner.
- Risky code (fence, journal integration, C02 verification, startup swap, launcher install) stays with Opus. Luna may
  take fixtures, frontend mirrors and rendering, prompt and docs text, each with an exact contract (§1.6).
- Platform paths (process lookup, `flock`, launchers) have tests that run on the Ubuntu CI workers.

### 3.2 N08-A — Offline repair proposals and application

- **Prerequisites:** N08-P, N02-B with its migration-abort namespace cleanup (N02 §3.3 step 5g, D10); U1 confirmed.
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/state_repair.py`
  - `serve/delivery/src/owlbear_delivery/state_migration.py` (N02-B): operation kind `repair`, same-format
    operations, scoped verification and archive-on-verify for repairs (I9), `applied → aborting` and `absent`
    digests for repairs (D1, D3), every [journal-state](#journal-states) rule for both kinds, the retained-history
    set recorded at repair `apply` (I9), a per-manifest
    replay step for C03 (the only `apply` that accepts pending manifests, and only its own set), the process check
    of I1 in all four writing commands with the D12 record reader, the journal-bound classification context (I9),
    `confirmed` field (D9), empty-namespace cleanup after a repair `verify` or `abort` archive and its resume (I3)
  - `serve/delivery/src/owlbear_delivery/state_formats.py`: the transaction root map (each manifest root, its
    allowed participant roots and its owner validator, generic or contained, mirroring every `recover_all` and
    `recover_contained` call site; a source-scan test fails on an unmapped call site of either); the class-L
    `controller_process` family (D12); a journal version and read-upcast only if G3 applies
  - `serve/delivery/src/owlbear_delivery/runtime_transaction.py`: `RuntimeTransaction.read_pending(manifest_root,
    roots)` validates every manifest of a root with its owner validator without publishing and returns each
    transaction with its manifest digest, participant paths and after bytes (also N08-B's preflight); the
    contained validator becomes callable without publication
  - `serve/delivery/src/owlbear_delivery/design_package.py`: a pure verifier of a package byte set against its
    manifest, if none exists without disk side effects (C02)
  - new `serve/tools/src/owlbear_tools/delivery_repair.py`; console script `delivery-repair` in
    `serve/tools/pyproject.toml`
  - `serve/tools/src/owlbear_tools/delivery_diagnostics.py`: `MAINTENANCE_PROMPT` (D10); journal-kind mirror; stays
    stdlib-only
  - tests: new `serve/delivery/tests/test_state_repair.py`, new `serve/tools/tests/test_delivery_repair.py`,
    `serve/tools/tests/test_delivery_diagnostics.py`, `serve/delivery/tests/test_runtime_transaction.py`, the N02-B
    migration tests for the shared journal rule, `tests/test_agent_ecosystem_validation.py`
  - `share/prompts/repair-delivery.prompt.md` (thin entry, `execute/runInTerminal` plus `vscode_askQuestions`);
    new `share/skills/w-delivery-repair/SKILL.md` (classify → present → confirm per U1 → user stops controllers →
    apply → verify → user restarts → report); `share/WIRING.md`
  - this plan's progress row; execution plan status row
- **Positive scenarios:**
  - `classify` on a healthy seed: no findings, `.owlbear/delivery` hash unchanged, exit 0.
  - C01: invalid `host.local.json` → finding → `propose` stages bytes only (tree hash unchanged) → `apply --confirm`
    → canonical empty overrides, original bytes in the backup → `verify` (I9, real `classify`, no stub) → the
    default loader loads every Change, journal archived, `runtime/migrations/` removed (I3).
  - C02: invalid `config.json` with a verifying `HEAD` blob → restored; `git status` clean for that path. Tampered
    `design.md` of an admitted Change whose `HEAD` set verifies and matches the admission → restored;
    `list_changes` works afterwards.
  - C03 with mixed participants (immutable to an absent destination, replacement, move) in two registered roots,
    and the gate refusing `state-migration-required`: `propose` → `apply` (manifests and before-state in the
    backup) → `verify` passes I9 with `state-migration-required` remaining and routed to `delivery-migrate` →
    journal archived → `delivery-migrate propose/apply/verify` proceeds under N02-B's full verification.
  - Two independent startup faults through `delivery-repair` only, real classification: invalid `host.local.json`
    and an invalid `runtime/host.json` with a verifying `HEAD` blob → C01 verified with the C02 finding unchanged
    and no C04 → C02 proposed, applied and verified → the default loader loads every Change.
  - Retained history: `delivery-migrate apply` and `verify` leave the migration journal `verified`; C01 `apply`
    records its ID and SHA-256; `verify` passes with it unchanged; the repair journal is archived, the migration
    journal stays `verified` and the default loader loads every Change.
  - C03 over a contained root (`runtime/finalization-reports/<change>/transactions/`) with a valid manifest:
    replayed through the contained path; verified.
  - Routes: `migration-required` names `delivery-migrate`; a missing-provenance frontier names
    `repair_stranded_frontier`; a newer format names `/upgrade-delivery`; no write in any of them.
  - Supported rollback (I3) on disposable format-0 state: the merged N02-A release's `scan_capability` (subprocess
    from a worktree at its merge commit) accepts it, then refuses `state-migration-incomplete` after an empty
    `runtime/migrations/` is created (premise 10 pinned). After C01 through `verify` the namespace is gone and the
    merged N02-A and N02-B releases each start the default loader on it.
  - Abort rollback (I3) on disposable format-0 state with no `runtime/migrations/`: the first repair, C01, through
    `apply` then `abort`; the merged N02-A `scan_capability` result equals its pre-repair result, the namespace is
    gone and `host.local.json` has its before bytes.
- **Negative scenarios:**
  - `apply` while a controller holds the lock shared → `repair-controller-running`, no write.
  - `apply` or `propose` while a migration journal is open → `repair-journal-open`; `delivery-migrate propose` and
    `apply` while a repair journal is open → refused.
  - Bytes changed after `propose` → `repair-proposal-stale`. A user-confirmed operation without `--confirm` or with
    another ID → `repair-confirmation-required`, no write.
  - Crash injected after backup, after each replacement, after `applied`, during `verify`, during each `abort` step
    → normal start refuses `state-migration-incomplete`; MCP and Cockpit refuse; `resume` converges byte-identically
    with no duplicate; `abort` restores every affected path from the backup; a third digest stops with both copies.
  - C03 drift after `propose` (a manifest added, removed or altered; a participant path changed) →
    `repair-proposal-stale`, no write. C03 crash after the first participant publication, before a manifest's
    deletion and after it, each followed by a fresh-process `resume` (exact after-state) or a fresh-process `abort`
    with a crash after each abort step and `abort` repeated (exact before-state: absent paths, move sources and the
    original manifests). `abort` after `verified` → refused. A finding new after `apply` → `repair-verify-mismatch`,
    journal `applied`.
  - C02 refusals: `HEAD` blob invalid, absent or not matching the admission's package ID → no proposal (contained or
    environment).
  - V20: a receipt whose stored ID does not match its bytes, and a garbage transaction manifest → contained, no
    proposal, bytes unchanged; no path in N08 writes `provenance`.
  - A contained manifest that passes `_from_manifest` but adds an unexpected top-level field → C07, no proposal;
    bytes unchanged. An unmapped `recover_contained` call site fails the source-scan test.
  - Restart with a repair journal `applied` → C04 routes to `delivery-repair`, not `delivery-migrate`. On the
    retained-history fixture, before repair `verify`: a second non-terminal journal (migration `applying` or another
    repair), an unreadable journal, an added `verified` journal or changed retained bytes → `repair-verify-mismatch`,
    J stays `applied` and its `abort` restores. Each [journal-state](#journal-states) row has a fixture asserting
    its allowed and refused commands, both gates and the `classify` route.
  - Crash after the repair journal's `verified` mark, before its archive: normal start loads; `propose` of both
    kinds refuses `repair-journal-open`; `delivery-repair verify` finishes the archive; a repeat is a no-op.
  - Crash after the archive, before namespace cleanup (empty `runtime/migrations/` left): the merged N02-A release
    refuses; `classify` routes to `delivery-repair verify` with the archived ID; the rerun removes the namespace,
    N02-A starts, and a second rerun is a no-op. A crash during the archive move also converges through `verify`.
  - Crash after the abort archive, before namespace cleanup (first C01 repair on format-0 state): N02-A refuses;
    `classify` routes to `delivery-repair abort` with the archived ID; the rerun removes the namespace and N02-A's
    `scan_capability` equals its pre-repair result; a second rerun is a no-op. `verify` of that ID and `abort` of
    an archived verified ID refuse without a write. A crash during the abort archive move converges through `abort`.
  - Crash after a first migration's pre-marker abort archive (N02 step 5f), before its cleanup: `classify` routes to
    `delivery-migrate abort` with the archived migration ID; `delivery-repair verify` and `abort` of that ID refuse
    without a write; after the migrate rerun the namespace is gone and N02-A starts.
  - Preservation: a retained `verified` migration journal, an unrelated entry, a symlink or a non-directory at
    `runtime/migrations` → cleanup after repair `verify` or `abort` leaves it unchanged (tree hash and no-follow
    `lstat`); the retained journal stays readable by the current gate.
  - Newer workspace format → `repair-format-unsupported` before any typed read.
  - Retained format-0 journal and a real process in each supported form of I1 (a stand-in module or script of that
    name that only sleeps; cwd the workspace): `apply`, `resume`, `verify` and `abort` each refuse
    `repair-controller-running` with journal and tree hash unchanged; an unreadable candidate cmdline (fault below
    `psutil`) → `repair-controller-unknown`. The same stand-in with a D12 record of another pid, create time or
    cmdline, or an unreadable record → refused. Runs on macOS and the Ubuntu CI workers.
  - Cold `delivery-repair classify` subprocess with a failing eager import (a meta-path finder raising for
    `owlbear_delivery.portfolio_application`) → exit 1, a C09 finding routed to maintenance plus the stdlib
    inspector's findings, no traceback; the prompt test asserts the `delivery-diagnose` fallback. No `state_repair`
    operation constructs the application (`load_delivery_application` and `PortfolioApplication.__init__` patched
    to fail).
  - Output never contains a record value or an absolute path (fixtures with sentinel strings).
- **Inner loop:** `uv run pytest serve/delivery/tests/test_state_repair.py -q`, then
  `uv run pytest serve/tools/tests/test_delivery_repair.py -q`.
- **Closeout:** `uv run test --changed`; scoped `uv run ruff check` and `ruff format --check`;
  `uv run pytest tests/test_package_boundary.py tests/test_agent_ecosystem_validation.py -q`.
- **LC:** full form with `delivery-lc`. Additionally on the copy: `delivery-repair classify` reports no finding;
  inject an invalid `host.local.json` into the copy, run C01 to `verified`, the candidate loads every live Change,
  `runtime/migrations/` is absent, the previous release (merged N02 head) loads the repaired copy; `compare` shows
  live unchanged.
- **Size / risk:** M / high (offline writes to authority; shared journal with N02).

### 3.3 N08-B — Degraded Cockpit start and the Repair Delivery entry

- **Prerequisites:** N08-A.
- **Editable paths:**
  - `serve/cockpit/src/owlbear_cockpit/target_context.py` (typed startup outcome with mode, refusal, capability),
    `main.py` (`_load_target_runtime`, `run`: no exit on Delivery refusal, no supervisor, retry install),
    `deps.py` (`get_target_context` → `503 DELIVERY_UNAVAILABLE`), new `routes/delivery_startup.py`,
    `target_models.py` (response models)
  - `serve/delivery/src/owlbear_delivery/delivery_application_loader.py`: `load_delivery_application` effect
    boundary and read-only preflight (§1.5, D5), `DeliveryApplicationLoadError.effects_started`, controller-lock
    release on every failure after acquisition, the D12 record publication, stale replacement and exit removal in
    the shared-lock helper
  - `serve/delivery/src/owlbear_delivery/design_package.py` (`list_verified` per-package containment),
    `application_readiness.py` [N01-A] (`_portfolio_operating_view`, health view), `application_recovery.py`
    [N01-A] (`_unavailable_change` prompt → `/repair-delivery <change-id>`), `portfolio_operating.py`
    (`DeliveryHealthReason.PACKAGE_INVALID`)
  - frontend: `serve/cockpit/web/src/api/workItems.ts` (startup types, `503` handling, `package-invalid` mirror),
    `hooks/useWorkItems.ts`, `pages/WorkPortfolioPage.tsx`, `components/WorkItemDetail.tsx` (Repair Delivery for
    unavailable Changes), new `components/DeliveryUnavailablePanel.tsx` and its test, `__tests__/WorkPortfolio.test.tsx`
  - E2E: `web/e2e/work-portfolio.spec.ts`, `web/e2e/support/start-work-portfolio-stack.mjs`,
    `web/e2e/support/seed-work-portfolio-delivery.py` (`--refuse <case>`)
  - tests: new `serve/cockpit/tests/test_degraded_start.py`, `tests/test_cockpit_launch.py` (the `SystemExit`
    expectation at line 71 changes for Delivery refusals; missing `dist/` still exits),
    `tests/test_cockpit_boundary.py`, `tests/test_cockpit_work_items.py`, `serve/delivery/tests/test_design_package.py`,
    `serve/delivery/tests/test_portfolio_application.py`, new `serve/delivery/tests/test_delivery_application_loader.py`
  - `setup/operating-owlbear.md` Cockpit section; this plan; status row
- **Companions:** `package-invalid` and the startup modes in `workItems.ts`, rendered with component tests, with the
  backend/frontend parity assertion in `tests/test_cockpit_boundary.py`. No new frontier-writing operation.
- **Positive scenarios:**
  - For each refusal (invalid `host.local.json`, invalid `config.json`, garbage transaction manifest, N02 newer
    format, `controller-fenced` from a held exclusive lock, `state-migration-incomplete`): the Cockpit process
    serves `/health/live`, the SPA, memory and ideas; `/api/delivery/startup` returns the mode, typed code and
    capability summary; Delivery routes return `503`; the panel shows the refusal, **Repair Delivery** (copies
    `/repair-delivery`) and **Retry Delivery startup**.
  - A real degraded Cockpit (`uv run cockpit`, D12 record) stays up while N08-A's `apply`, `verify` and `abort`
    run on format-0 state; **Retry** then returns `available`, starts the supervisor once and lists every Change.
    Alongside, a stand-in legacy controller without a record still refuses `repair-controller-running`. macOS and
    the Ubuntu CI workers.
  - One Change with an invalid package manifest: `list_changes` returns all Changes; that Change carries
    `package-invalid`; no `500`.
  - An unavailable Change (invalid frontier) shows **Repair Delivery** with `/repair-delivery <change-id>`.
  - E2E (`npm run test:e2e:work`): stack started on `--refuse host-local` shows the panel and copies the prompt;
    the fixture is repaired in place and **Retry** shows the board.
- **Negative scenarios:**
  - While degraded, a non-blocking exclusive acquisition of `runtime/controller.lock` succeeds (I6), and the
    `.owlbear/delivery` hash is unchanged across start, status reads and a failed retry.
  - Gate-current workspace with an earlier replayable pending manifest and a later invalid one: the default loader,
    MCP and Cockpit refuse `transaction-manifest-invalid` before any replay; tree hash unchanged (the earlier
    manifest is not published); Cockpit `degraded`. The same for a contained manifest with an unexpected
    top-level field.
  - Remote restoration followed by an injected composition failure (C09): Cockpit `maintenance` with
    `startup_effects: started`; from then on the tree hash is unchanged across status reads, no supervisor runs and
    an exclusive lock acquisition succeeds. Every loader failure after acquisition, before or after the boundary,
    leaves the controller lock free.
  - Retry while an exclusive holder exists → stays `maintenance`, no write; retry when available → `409`; two
    concurrent retries install one application and one supervisor.
  - Refusal detail never contains the workspace's absolute path (P1 host-local message) or record bytes; an
    untyped exception shows only its class.
  - Cross-origin form POST without a JSON content type cannot trigger retry (`415` or `422`).
  - A coordination record that fails to parse is no longer shown as healthy: the Change shows the existing
    `coordination-unavailable` reason (G4).
  - D12 stale record (the helper in-process and a real start; macOS and the Ubuntu CI workers): the current pid's
    path seeded with an older create time → replaced through `expected` with those bytes; identical bytes → no
    write; malformed, oversize, symlinked or other-pid bytes, or this create time with another digest → unchanged,
    no record, startup continues and N08-A's `apply` refuses `repair-controller-running`. An MCP start refused by
    the gate removes only its own record at exit; a degraded Cockpit retry republishes identically; no record of
    another pid is removed.
  - Missing `dist/` still exits with its message.
- **Inner loop:** `uv run pytest serve/cockpit/tests/test_degraded_start.py -q`; then
  `npm --prefix serve/cockpit/web test -- DeliveryUnavailablePanel`.
- **Closeout:** `uv run test --changed`; scoped Ruff; `npm test`, `npm run build`, `npm run test:e2e:work` and
  Biome on changed files in `serve/cockpit/web`;
  `uv run pytest tests/test_cockpit_boundary.py tests/test_cockpit_launch.py tests/test_cockpit_work_items.py -q`.
- **LC:** load form (startup changes): the candidate Cockpit and loader load the live copy as `available` with every
  Change available; on a copy refused by a synthetic newer format, Cockpit starts degraded with unchanged hashes.
- **Size / risk:** M / high (startup path of every loader caller; one Delivery core containment fix).

### 3.4 N08-C — Distribution, maintenance route and operating docs

- **Prerequisites:** N08-B, N02-D; U2 and U3 confirmed; N02 U1 and U2 answered as recommended there.
- **Editable paths:**
  - `serve/tools/src/owlbear_tools/delivery_controller.py` (N02-D): controller-only package set (D7); maintenance
    launchers `bin/delivery-diagnose`, `bin/delivery-repair`, `bin/delivery-migrate` bound to the pinned release;
    consumer `install --source <clone>` taking `serve/cockpit/dist` from the archive (P8)
  - `serve/tools/src/owlbear_tools/delivery_repair.py`: `target-ref-fetch` (C08) through N02-C's `remote_git`
  - `setup/init.py` (install and pin per U2, launcher entry, claimed-entry upgrade, uninstall of claims and,
    lock free and confirmed, release trees), `seed/.vscode/mcp.json`, `seed/.owlbear/.gitignore` (`controller/`,
    `delivery-migrations/`)
  - `share/prompts/repair-delivery.prompt.md` and `share/skills/w-delivery-repair/SKILL.md` (prefer the pinned
    launchers); new `share/skills/w-delivery-maintenance/SKILL.md` (§11.2 route per U3); `share/WIRING.md`
  - docs: `setup/operating-owlbear.md`, `setup/setup-guide.md`, `setup/sharing-guide.md`, `README-consumer.md`,
    the Delivery section of `README.md`
  - tests: `tests/test_init_scaffold.py`, `tests/test_setup_init_uninstall.py`, `tests/test_setup_init_settings.py`,
    `serve/tools/tests/test_delivery_controller.py`, `serve/tools/tests/test_delivery_repair.py`,
    `tests/test_agent_ecosystem_validation.py`
  - this plan; status row
- **Maintenance route** (`w-delivery-maintenance`, entered from a C09 finding): the user authorizes the issue and the
  maintained surfaces; the agent records the pinned release, `pin.json` and a verified state backup; creates an
  isolated worktree at the pinned commit outside the managed workspace; reproduces the defect on a disposable copy
  (`delivery-lc` or fixture); fixes with focused tests; obtains an independent exact-commit `build-reviewer` pass;
  produces the release per U3; upgrades through `/upgrade-delivery` with the user's approval; verifies startup,
  gate and one continuation read round-trip. It creates no Delivery record and never pushes `dev` or `main`.
- **Positive scenarios:**
  - Fresh disposable consumer project from a `main`-shaped clone: `init.py` installs a ~50 MB release from the
    clone's `HEAD` with its bundle, writes launchers and the `owlbear-delivery` launcher entry; MCP over stdio and
    Cockpit over HTTP run release code; `/repair-delivery` finds `bin/delivery-repair`.
  - Rerun on an unpinned consumer: an unmodified OwlBear-installed entry moves to the launcher; a user-modified
    entry is kept and reported.
  - Consumer upgrade: the clone moves forward; `/upgrade-delivery` installs from `--source`, runs preflight,
    migration and switch; every Change stays available.
  - `target-ref-fetch` restores a missing remote-tracking target over a local bare remote; the loader starts.
  - Maintenance rehearsal: a release with an injected loader defect → C09 → the skill's steps on a disposable
    portfolio → a fixed release pinned through the procedure → smoke passes.
- **Negative scenarios:**
  - Install, switch or uninstall while a controller holds the lock → refused, no change.
  - `install --source` with a ref that is not a commit of the clone, or a dev archive without `dist/` and no
    pinned Node → refused with a message.
  - The maintenance skill never pins an unmerged commit without the U3 approval step and never writes live state
    (agent-ecosystem assertions on the skill text).
  - `target-ref-fetch` against a hung transport → typed timeout, no leftover process, no retry loop.
  - Windows refusal from N00-C unchanged.
- **Inner loop:** `uv run pytest tests/test_init_scaffold.py tests/test_setup_init_uninstall.py -q`; then
  `uv run pytest serve/tools/tests/test_delivery_controller.py -q`.
- **Closeout:** `uv run test --changed`; scoped Ruff; agent-ecosystem tests; package closeout: the full
  `uv run test` once and a cumulative Sol challenge of the N08 diff against this plan.
- **LC:** upgrade rehearsal (N02-D form) from the pinned release to the N08-C candidate built with the
  controller-only set, on a fresh `delivery-lc` copy; live unchanged.
- **Host rehearsal:** one real VS Code window on a disposable consumer project: setup, launcher start from
  *MCP: List Servers*, a forced controller refusal showing VS Code's failure state, `/repair-delivery` and restart.
- **Size / risk:** M / medium, plus the host rehearsal.

### 3.5 Execution-plan deltas and false premises

No re-split: A, B and C keep the §4.2 order and schedule (stage 3: N08-A and N08-B in lane B; stage 4: N08-C).
Package-added prerequisites (allowed by §4.2): U1 before N08-A; U2, U3 and N02's U1/U2 before N08-C. D11 amends
§5 N08's phase descriptions in this PR; the N08-P status row changes at merge. Conflict surfaces under the ready
rule: N08-A lists `state_migration.py`, `state_formats.py` and `runtime_transaction.py`; N08-B lists
`delivery_application_loader.py` (also edited by N02-C and N02-D), `application_readiness.py`,
`application_recovery.py`, `design_package.py` and `portfolio_operating.py`, which N03, N04 and N05 phases also edit.

Premises found false or incomplete on `ef622c354`:

1. Execution plan §5 N08 scopes N08-B to Cockpit. V18's "degraded Change remains visible" fails in Delivery core
   for package corruption: `list_changes` raises (`application_readiness.py:380`, P2). N08-B therefore edits core.
2. N02 §1.5 says Cockpit and MCP "surface the typed refusal". Not every refusal is typed today: a garbage manifest
   raises `TransactionManifestError(ValueError)` (`runtime_transaction.py:52`, raised at `:315` via
   `change_workspace.py:1871`), which `main.py:297` does not catch (P1). N08-B's loader preflight refuses it typed
   before any replay (D5).
3. The prompt and the inspector route writes to "D07" (`repair-delivery.prompt.md:22`,
   `delivery_diagnostics.py:253`), a package of the retired schedule (D10).
4. N02 D1 sizes a release at 1.7 GB; the controller needs 50 MB (P6, P7).
5. A catch at Cockpit's boundary cannot prove no-write: the loader restores remote state before composition
   (`delivery_application_loader.py:2443`), and root-wide replay publishes an earlier valid manifest before a later
   invalid one raises (`runtime_transaction.py:295-302`, called at `change_workspace.py:1871`). N08-B adds the
   loader effect boundary (D5).
6. `owlbear_delivery/__init__.py:91,226` imports the loader and application, so no Delivery submodule imports in
   isolation; `delivery-repair` owns the import fallback (I7).
7. N02-B `verify` requires every Change available (N02 §3.3 step 4); a repair that leaves other findings cannot
   pass it, so repairs verify their own postcondition (I9).
8. N02 retains `verified` migration journals and normal start accepts them (`delivery-n02-plan.md:459`); round-2
   I9 ("finds no other journal") refused every repair after a migration. N02's verification mode accepts "exactly
   the named `applied` journal" (`:437`) and is silent on that history; [journal states](#journal-states) settles
   it for both kinds, and N08-A re-resolves N02-B's merged check (G3).
9. Round-2 D12 assumed a stale process record is harmless, but `write_contained` refuses differing bytes without
   `expected` (`runtime_transaction.py:535-539`); D12 now compares and replaces.
10. N02-A's gate refuses `state-migration-incomplete` whenever `runtime/migrations` exists, without reading it
    (N02-A `state_formats._walk`, `state_formats.py:821-822` in lane B), so an archive-only I3 left every repaired
    workspace refused by N02-A; I3 now removes the empty namespace.
11. N02 §3.3 step 5f archives an aborted journal and removes only `runtime/migrations/<id>/`, so aborting a first
    repair left the same empty namespace while round-4 cleanup ran only in `verify`; repair `abort` now ends with it.
12. The same step 5f left an empty namespace after a first migration's pre-marker abort, and N08's cleanup covered
    repairs only, so N02-A refused with no route. This plan amends N02-B (N02 §3.3 step 5g, D10); C04 routes it.

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N08-P | — | — | Probes P1–P10 | Sol round 1: revision-required (replay custody binding, legacy exclusion for all writers, repair-specific verification, read-only degraded boundary, CLI import fallback) → revised; Sol round 2: revision-required (contained recovery boundary, exact-journal verification context, gated vs legacy exclusion) → revised; Sol round 3: revision-required (retained verified history, stale process record) → consolidated journal-state table; Sol round 4: revision-required (empty migrations namespace cleanup) → revised; Sol round 5: revision-required (abort namespace cleanup) → revised; Sol round 6: revision-required (migration abort namespace; amends N02-B §3.3) → revised; Sol round 7: `plan-sound` | approved (D11 confirmation pending; U1–U3 before their phases) |
| N08-A | — | — | — | — | — |
| N08-B | — | — | — | — | — |
| N08-C | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | VS Code shows a refused Delivery MCP start clearly enough for the user to run `/repair-delivery` | No real window exercised in P | MCP lifespan source (`server.py:110-118`); N02 G3 | N08-C host rehearsal | N08-C merge |
| G2 | The degraded panel works in the built bundle and Chromium | Lane has no `node_modules`; P ran no frontend | Cockpit routing source; P1 process runs | N08-B (`npm run build`, `test:e2e:work`) | N08-B merge |
| G3 | N02-B's journal expresses a same-format operation, `absent` digests, `applied → aborting` and a per-manifest replay step without a schema change, and its verification mode accepts retained `verified` history, and its normal gate ignores an empty `runtime/migrations/` | N02-B is not implemented | N02 plan §3.3 protocol | N08-A first step: re-resolve; otherwise register a journal version (D1) | N08-A start |
| G4 | A malformed coordination record is surfaced in the portfolio projection | P1 shows it listed as available with no diagnostic; the lazy read path was not traced | P1 matrix | N08-B | N08-B merge |
| G5 | Rerunning `init.py` on a real existing consumer upgrades only unmodified entries | Only seed and manifest source were read | `setup/init.py:374-426` claims | N08-C fixtures and host rehearsal | N08-C merge |
| G6 | Cockpit's memory routes (release code) stay compatible with the unpinned memory MCP | Memory-store versioning is outside N08 (N02 G6) | — | `owlbear_memory` owner | Nothing in N08 |
| G7 | `flock` and `psutil` cwd, cmdline and create-time reads behave on Ubuntu as on macOS | P4 and P5 ran on macOS only | Python and psutil documentation; D03 worker-stall tests on CI | N08-A unit tests on the Ubuntu CI workers | N08-A merge |
| G8 | `host.json` load errors are labelled correctly | `delivery_application_loader.py:314` reuses the host-local message; N08 does not edit the loader | P1 | Next loader editor (N02-C or N02-D); N08 classifies by path, not message | Nothing |
| G9 | `/continue-change` tells the user to run `/repair-delivery` when Delivery MCP is down | Continuation prompt routing is N09's | — | N09-P2 | N09-B |
| G10 | N02-A's gate yields a typed refusal for an unparseable transaction manifest | N02-A is not implemented | N02 registry lists `transaction` as class L | N02-A; N08-B's preflight types it either way | Nothing |
| G11 | LC full form and the C01 rehearsal on a live copy | Needs Docker and a quiet live copy | N02 P8 (Docker present); P3 healthy live | N08-A | N08-A merge |
