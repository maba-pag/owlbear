# D03 — Recovery Package Plan

## Status and authority

**D03-B: partial implementation checkpoint; not accepted and not a prerequisite for C yet.**
This is the package record required by the [cloud execution guide](delivery-cloud-flight-handoff.md).
D03-P changed only this file. The programme and shared governance remain unchanged.

- Original source inspection: `96f21ec5d87de2a8003d4010281fc4dc47b7d645`, branch `copilot/d03-p`.
- Published package: draft [PR #326](https://github.com/maba-pag/owlbear/pull/326), targeting `dev`.
  Subsequent phases belong on that PR; do not create another package PR.
- At repair start, checkout and reviewed PR head were
  `466b5ea50e8d9569c0e4295941a05b4fb0e84134`; GitHub reported comparison target
  `dev@fd0dec2aaca7831532505573c4d348eaa9012dbb`. These are distinct from the original inspected
  source and from a computed Git merge base. Do not rebase or merge in D03-P.
- D02 prerequisite: accepted source `1ab5ae7e4f56201e3b01dc2a5a88fc8525352806` and acceptance record
  `e45ea3e4bc4e6f7456af8c8ac3c82313a36a3764` are in GitHub's published `dev` history. The checkout
  contains the [accepted checkpoint](change-continuation-delivery-redesign.md#d02-accepted-checkpoint-2026-09-14)
  and the retained-custody implementation described below. D02 was accepted through the preceding
  direct-development procedure, not a newly invented D02 cloud PR gate.
- Prior evidence, **not rerun here**: that checkpoint records independent exact-head Astra PASS,
  837 scoped Python tests, 314 frontend tests, a production build, 22 browser tests and named-host
  dispatch rehearsal. This verifies predecessor acceptance; it is not D03 proof or a claim that
  later dependency updates were tested by that run.
- Specification approval: user [comment 5714163306](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5714163306)
  explicitly approved the presented plan at `6c8c039a05c32ec265e45430d0b8a4e8e05be23c` and requested
  **D03-A only**, implemented by GPT-6 Astra. This is separate from worker-written progress and
  does not authorize B–E, merge or activation.

Repository paths in links resolve from this file. Command paths below use the actual cloud checkout
`/home/runner/work/owlbear/owlbear`; later workers must resolve their own checkout before invocation.

## Contract

### Result, requirements and exclusions

Deliver bounded, preservation-first recovery of failed finalizers, uncertain claim activation and
interrupted engine actions, plus useful read-only diagnosis when coordination/runtime composition is
damaged. Resume the original Change action only after an owning recovery receipt, never after a
diagnostic or elapsed lease. Cover programme **WP3, P05/P10/P11, V06–V10, V13, V18 and V20**.
The controlling requirements are [U1–U8](change-continuation-delivery-redesign.md#11-requirements-from-the-user),
[failure routing](change-continuation-delivery-redesign.md#61-routing-rules-for-failures),
[preservation and repair](change-continuation-delivery-redesign.md#7-preservation-first-worktree-and-code-recovery),
and the [offline boundary](change-continuation-delivery-redesign.md#111-repair-delivery-is-a-proposed-maintenance-entry).

The user supplies meaningful decisions/permission, not tests, Git commands, JSON edits, digests or
manual process killing. Continuation remains Change-scoped; capacity and shared-target fences remain
engine-owned. Preserve independent review and existing admission promises.

Excluded: D04 revision/evidence-applicability machinery; D05 merge authorization or provider merge
implementation; D06 private-input collection; D07 migration/application of offline repairs and
release management; D08 activation. No live state, host services, real provider writes, automatic
successor dispatch, new scheduler, arbitrary shell runner or controller bootstrap. Do not modify
unknown corruption into a valid-looking record, or treat an existing hash as proof of provenance.

### Existing owners and source findings

| Owner | Reuse and required extension |
| --- | --- |
| [Application](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | `acquire_change_action`, `execute_change_action`, `repair` and existing finalization/result routes remain the public authority. `repair` currently handles only a legacy stale-Builder proposal; extend it, not a parallel recovery facade. |
| [Coordinator/workspace](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | `ChangeContinuationAction`, `ChangeFinalizationAttempt`, `PortfolioCoordinator`, `ChangeWorkspaceManager`, publication/acquisition locks and immutable action receipts own custody and Git fences. `process_id` is a string supplied by dispatch, not a verified OS PID. |
| [Runtime](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) | Exact claims, transition/result replay, review repair, finalization invalidation and per-binding retries already exist. `_retry_fingerprint` covers Change/outcome/role/code only; `retry_count` is not an action-wide durable budget. Reuse transitions, but do not assume they close abandoned workers. |
| [Transactions](../../serve/delivery/src/owlbear_delivery/runtime_transaction.py) | Immutable and expected-byte replacement participants, manifests and failure injection support atomic authority publication. Git/provider effects still need intent/readback boundaries; a file transaction does not make them atomic. |
| [Finalization reports](../../serve/delivery/src/owlbear_delivery/finalization_reports.py) | Reports are bounded structural diagnostics, explicitly not authenticated proof. Current schema rejects raw commands/logs and maintained-check paths. Keep that privacy distinction when adding proof-mutation evidence. |
| [Projection](../../serve/delivery/src/owlbear_delivery/work_items.py) and application readiness | Preserve a single readiness basis for cards/acquisition. Add typed recovery/backoff/exhaustion rather than infer readiness in MCP, HTTP or agents. |
| [State publication](../../serve/delivery/src/owlbear_delivery/delivery_state.py), [branch publication](../../serve/delivery/src/owlbear_delivery/change_publication.py), [draft PR](../../serve/delivery/src/owlbear_delivery/draft_pull_request.py) | Reuse exact owner intents/receipts and readback. No generic retry of a provider mutation whose result is unknown. Public snapshots must not acquire private preservation contents or host termination credentials. |
| [Tools package](../../serve/tools/pyproject.toml) | Place the offline entry here, in the consumer-distributed tools boundary. Existing `owlbear_tools/delivery_config.py` imports Delivery; core `owlbear_delivery/diagnostics.py` imports the application. Neither is a safe offline bootstrap import. `owlbear_tools.__init__` is currently inert. |
| [MCP](../../serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py), [HTTP](../../serve/cockpit/src/owlbear_cockpit/routes/target_work.py), [continuation workflow](../../share/skills/w-orchestration/SKILL.md) | Extend strict existing adapters and mechanical dispatch; no transport-owned recovery decisions. The existing `/continue-change` entry already preserves failed custody. |

Important retained states in the inspected source:

1. Failed finalization keeps its writer and attempt even after report retirement; successful
   finalization is refused. `test_continuation_failure_retains_custody_and_blocks_success_and_mutations`
   is the reference negative case.
2. Activation can leave an exact runtime claim with or without a coordinator writer. An error and
   absence of a launch response do not prove the delegate never ran.
3. Engine actions retain immutable `intent.json`, `started.json` and `result.json` under the owning
   Change's `action-receipts`. A blocked result is replayed unchanged; a started action without result
   is not invoked again. D03 must add a linked recovery result, not overwrite those original records.
4. Existing Builder quarantine uses an alternate index and a Git commit, followed by broad reset/clean.
   That is **not** sufficient authority for nonterminal restoration: it neither preserves distinct
   staged bytes as such nor proves authorship, privacy safety or byte identity through Git filters.
5. Constructing `PortfolioCoordinator` creates state and recovers transactions. Offline diagnosis
   must not instantiate it, load `PortfolioApplication`, or import the eager Delivery package.

### A. Exclusion and recovery authority

**Critical T3 contract — not delegated policy invention.**

Accepted evidence is one of:

- **Host-confirmed closed invocation:** an engine-configured, trusted host integration resolves the
  exact issued invocation and confirms termination of the delegate **and all descendant writers and
  outstanding tool jobs**, with no ability to resume that invocation. Bind host instance/generation,
  opaque invocation identity, Change, claim/attempt or engine operation, and the managed resources.
  An acknowledgement of a cancellation *request* is insufficient.
- **Enforced exclusion:** the integration actually prevents every old writer from reaching the
  managed worktree, shared Git metadata/refs and relevant mutation channels. It must remain enforced
  across restart until the old execution is closed. A new directory, token/generation counter,
  revoked MCP permission, advisory lock or branch name alone is not filesystem exclusion.

No supported VS Code termination/exclusion provider was found in the inspected owners. Existing
`host_id`, `session_id`, `process_id`, a diagnostic, `confirmed_lost`, a PID lookup, silence or timeout
cannot be converted into either evidence form. Do not retrofit unverifiable provenance to D02 claims.
An old invocation may be resolved by a trusted host integration only if it can independently match
that exact invocation and all its writers; otherwise it stays contained.

Add one narrow injected host-evidence dependency to `PortfolioApplicationDependencies`, with a
default **unavailable** implementation. It observes/requests closure for an engine-issued identity
and returns `closed`, `excluded`, `still-running`, `unknown` or `unavailable`. Only the configured
owner may produce verifiable evidence; public `repair` accepts an opaque evidence reference at most,
never a caller-authored acknowledgement or boolean that grants release. The core must validate the
reference through the owner, not merely hash/deserialize a caller's fields.

For synchronous engine actions, an owning call that has returned and joined its tool jobs can record
closure evidence itself. A reacquired process lock after a crash does **not** prove a surviving Git
child or outstanding remote request stopped. Unknown outcomes require exact owner readback as well
as exclusion; if either is unavailable, retain custody. Do not build a general process supervisor.

Persist a versioned `RecoveryIntent` and `RecoveryReceipt` in the existing runtime Change directory,
under `recovery-receipts/<recovery_id>/`, implemented in proposed core module `recovery.py`.
The intent binds original custody/intent/report, contract/frontier and coordination byte digests,
heads, branch/worktree registration, supported evidence identity and intended fixed recovery kind.
The receipt records closure/exclusion, preservation and exact owner-effect dispositions separately.
It links the original failure, any resumed action and the immutable intent; it never rewrites a
failure as success. Keep bounded metadata and no file contents/host credentials in public results.

Recovery state is `proposed -> excluded -> preserved (when needed) -> reconciled -> completed`;
`contained`, `stale`, `backoff` and `exhausted` are non-success outcomes. These are recovery stages,
not new Delivery task stages. A failed write cannot skip a stage on replay.

Transaction boundary:

1. Under existing lock ordering, capture/CAS the exact owner and record intent without releasing it.
   Host cancellation/readback must not hold a portfolio-wide lock while waiting.
2. Verify closure/exclusion and reacquire/recheck the same identity before any local mutation.
   Persist evidence; revalidate an ongoing exclusion after restart, rather than trust its timestamp.
3. Reconcile only known owner effects and preserve anything required by the next operation.
4. Atomically publish recovery receipt, exact claim/coordination release and any runtime replacement
   with `RuntimeTransaction` expected-byte participants. Readers must not see free capacity with an
   unfinished recovery. If only one of runtime claim/writer existed after failed activation, release
   exactly that proven owner; a mismatched or malformed record is containment, not reconstruction.
5. A resumed attempt is acquired afresh from the original action's **current** basis after verified
   recovery. Reject the old worker's late submission against retired custody. Preserve the old
   finalizer report/attempt and engine result as history, including checks-not-run.

All entry points touching the same resources must honor this fence, including legacy claim recovery,
Integration recovery, retry transitions, finalization, administrative mutation and acquisition.
Do not leave a caller-confirmation or timeout bypass reachable alongside the new path.

#### Interrupted engine effects

| Original kind | Permitted reconciliation after exclusion |
| --- | --- |
| `reconcile-checkpoint` | Read pending checkpoint/state/branch/draft-PR journals and exact receipts; reconcile the same publication identity through existing owners. Account for a checkpoint-created successor head. Missing or contradictory records remain contained. |
| `sync-target` | Read the existing exact target-sync intent, ref/HEAD and receipt/conflict state. Finish supported interrupted local publication once; a conflict routes bounded Builder repair and fresh review, not reset or force update. |
| `mark-ready` | Read the exact PR/head/draft state and existing ready receipt. Confirm the original authorized effect or invoke an owner-supported idempotent reconciliation; stale head/protection state is not success. |
| `observe-acceptance` | Read the original acceptance/publication/finalization identities and disposition receipts. Waiting is not a merge permission; never manufacture completion or repeat an unknown mutation. |

An owner may replay an effect only where its existing journal/readback contract makes that exact replay
safe. `not-observed` is not automatically `not-applied`. If the owner cannot discriminate, return
`contained / owner-outcome-unknown`. D03-A supplies the closed-worker reference path and recovery
journal; D03-E must cover all four rows before package closeout.

### B. Failure identity, budgets and backoff

Use a versioned runtime-owned retry ledger, proposed module `recovery.py`, with immutable attempt
records and an expected-byte current summary. Store it in the same Change's runtime directory;
update reservations and recovery/action receipts transactionally. Existing per-binding retry counters
must be reconciled into this authority, not become a second allowance.

- Engine semantic key: `(change_id, action_kind, exact_head, target_head, finalization_id)`.
  Exclude new continuation operation IDs, acceptance observations, host/session IDs and error prose.
- Worker/proof key additionally identifies the approved contract, stable outcome/task lineage,
  registered check/procedure or finding class, and original candidate. Do not key on a renamed label.
- A recovery episode links successor repair commits/attempts to the original failure key. A new
  commit, task name, report ID or changed error wording is **not** accepted progress and cannot
  create a fresh allowance for the same failing check. Retain earlier keys; alternating codes must
  not replenish a common action's budget.
- Reset only the affected episode after an engine-accepted result covering its failed claim, or an
  independently recorded, approved new approach bound to that episode. D03 does not invent a generic
  approval API: unsupported new-approach approval remains a decision, not a reset flag.
- Reserve each automatic attempt before dispatch/effect entry; duplicate submission/replay charges
  once. Interrupted reservations remain consumed until exact evidence proves no attempt started.
  Pure observation of readiness neither consumes nor resets the budget.

Proposed programme defaults, made precise for specification review:

| Failure/action | Allowance | Backoff and stop |
| --- | --- | --- |
| Equivalent mechanical or Builder/check repair | At most **two automatic repairs after the original failure** per episode | Earliest next starts at persisted failure time plus 1 second, then 2 seconds; after the second failed repair, `exhausted`. |
| Transient service/read failure | **Three total attempts**, including the first | Retry after 1 second then 2 seconds; third failure exhausts. Unknown writes use readback, not this effect allowance. |
| Repeated acceptance waiting with unchanged semantic key | Yield without merge action; at most three automatic observations before a durable wait | Apply the read backoff between observations; an explicit later continuation can observe once, but does not reset an exhausted failure/repair episode. |
| Active/unknown writer, unsafe preservation, corruption, permission or semantic gap | **Zero automatic destructive repairs** | Named containment/decision/host-needed reason. Read-only diagnostic retries remain bounded separately. |

Use the injected clock; persist timezone-aware `next_eligible_at`, policy version, counts and a fixed
stop code. Early/clock-regressed observations wait; never sleep holding custody locks or poll in an
agent loop. Changing policy version/configuration does not erase accumulated counts. Expose attempts,
next actor, next eligible time and one intelligible stop reason through shared readiness. One exhausted
Change must not prevent independent Changes from using otherwise available capacity.

### C. Preservation, proof failure and resumption

Only the workspace owner applies an exact-path proposal under proven exclusion/no competing Builder
claim and exclusive recovery custody. Bind Change version, actual worktree registration/realpath,
branch/HEAD, reviewed and target heads, raw index digest, complete status/path set, per-path raw-byte
digests/types/modes and maintained-surface/last-write evidence. Whitespace alone proves no ownership.

Classify **before** writing preservation objects:

- Proven disposable, admitted post-proof drift: preserve first, then restore only those exact paths.
- Useful admitted code, generated output or proof-procedure changes: preserve and route existing
  Builder repair with reproduced check/finding, constraints and cumulative review baseline.
- Foreign/ambiguous paths, pre-existing staged changes or private/secret-like material: preserve
  in place and contain, without copying content into Git objects, public state, logs or responses.
  Ask only a meaningful inclusion/preservation/permission question where supported.

Extend the current quarantine representation with a private local raw-byte manifest/object store
under `recovery-receipts/<recovery_id>/preservation/`; do not assume `git add` preserves bytes when
attributes/clean filters or line-ending conversion apply. Raw preservation is authoritative;
existing attempt/quarantine refs may supplement it only for already privacy-qualified content.
No automatic remote publication or inclusion in `DeliveryStateSnapshot`.
Create private directories/files with owner-only permissions; no automatic deletion/garbage
collection of preserved evidence in D03. Public receipts expose opaque references, not content.

**Raw-index owner and v1 boundary:** C adds descriptor-backed capture to `ChangeWorkspaceManager`;
the existing temporary quarantine index is not the managed index. Resolve the index using
`git rev-parse --path-format=absolute --git-path index` in the exact registered worktree. Resolve
that worktree's administration directory and common directory through Git (`--absolute-git-dir`
and `--git-common-dir` with absolute path formatting), not a constructed administrative path.
Reject inherited Git repository/worktree/index/object-directory overrides for these reads; no
caller-supplied index path or `GIT_INDEX_FILE` may select the evidence.

The managed index is outside the worktree content root. Permit only the exact Git-resolved `index`
file directly within that registered worktree's Git-resolved administration directory, itself
verified against the registered repository/common directory. Pin directory descriptors and verify
the worktree registration, directory identities and Git-resolved paths again before applying any
proposal. Reject symlinked ancestors/files, nonregular or multiply linked index files, path swaps,
missing index and an existing index lock; do not delete a lock or initialize/refresh the index.
Use read-only Git inventory with optional locks disabled and no external filters/textconv.

V1 supports only a self-contained full index. Detect split-index dependencies using Git's
`--shared-index-path` and sparse-index entries with `ls-files --sparse --stage -z`; either produces
containment, not index expansion or conversion. Capture all ordinary stage/mode/object/path entries
using `ls-files --stage -z` and compare staged state to the exact HEAD. Reject staged/unmerged content
before copying raw index data. Index paths/extensions may contain private metadata: the entire raw
index, not merely changed paths, must pass the same privacy policy before owner-only preservation.
Unknown extensions whose privacy/independence cannot be established remain contained. The index
counts against the existing per-file/total preservation limits; never include its bytes or entries
in public receipts, Git objects or logs.

Read raw bytes from the pinned descriptor, recording content digest and file/directory identity;
check descriptor metadata and the raw digest again around inventory and before every restoration
step. Disable optional Git index refreshes throughout recovery. V1 restoration changes only selected
worktree content and **never rewrites the index**; therefore the raw index must remain exactly the
recorded preimage on replay, even if Git would consider a different index semantically equivalent.
Any index drift retains custody and preserved evidence without restoring a saved index over newer
staging. Raw capture is recovery evidence, not an authorization to modify Git administration.

Supported v1 inventory: regular/binary files, deletions, rename source/destination, executable modes,
and symlink text without following links. Retain raw index bytes and HEAD/ref metadata; reject
unmerged or pre-existing staged content before mutation. Refuse external symlink traversal, special
files, submodule changes, ambiguous hardlinks and root/registration substitution. Do not traverse
ignored credentials, environments or profiles; refuse a repair that would require touching them.
Use explicit bounded policy: at most 256 changed paths, 16 MiB per file and 64 MiB total raw content;
over-limit/type/privacy rejection is containment, never partial success. No claim of perfect secret
detection: provenance/allowlisted maintained paths plus conservative checks are all required.

Durably write and independently verify **all** preserved content, metadata and the manifest before
the first restore. Recheck the original fences immediately before each exact-path effect. Never use
generic reset/clean or expand the selected paths to make the worktree clean. Persist per-path
before/after identity so restart accepts only the recorded preimage or intended postimage; any third
value stops. Partial restore retains original evidence/error and custody until safely reconciled.
An fsync/disk/receipt failure must not report success or discard the last good snapshot.

Record proof-command before/after fingerprints. A mutation produces `proof-mutated-worktree`, the
registered command/procedure identity and changed paths, even if the command exits zero. Arbitrary
command strings, output and secrets stay out of the structural diagnostic API. A bounded local
proof-attempt record binds a maintained procedure to the fingerprints; its observation is not a
passing review receipt. Extend finalization failure category validation deliberately, not by allowing
free-form logs in `ReportFinalizationFailure`.

Restoring disposable drift preserves reviewed HEAD and resumes the original preflight. A Builder
repair creates a new candidate, invalidates old exact-head finalization through existing runtime
owners, and requires fresh cumulative independent review. Fix a mutating proof procedure before
rerunning it; do not alternate restore/formatter indefinitely. Source defects remain Builder work;
semantic gaps return to Designer/user. No weakened tests or acceptance exemptions.

#### Completed-outcome Builder repair

Current `claimable_outcome_ids`/`claimable_task_ids` exclude completed work, and
`prepare_review_repair` requires an existing successful finalization: neither already supplies the
failed-before-proof Builder route. C must add one fenced runtime operation for that route rather
than ask an unclaimed Builder to edit or use an administrative move that erases prior results.

For a reproduced local finding with one proven owning outcome/task, the engine derives one immutable
`DeliveryTaskDefinition` from that task's admitted maintained surfaces, commitments, constraints,
exclusions and proof boundaries, narrowed to the defect. Append the repair task with an
episode/attempt-bound ID and dependencies on the preserved completed task results; retain every old
task/result unchanged and reopen only that outcome to `implementation`. Bind the derivation and
original continuation action in the recovery intent. No arbitrary caller-authored task or broadened
scope. If the owning scope cannot be established, return a bounded planning/design attention rather
than choosing the first outcome or pretending the repair is dispatchable.

Publish the repair-task addition, exact finalizer/failed-claim release and recovery receipt in the
same fenced transaction. The existing `activate_claim`, `show_build_context`, `submit_result` and
independent exact-commit review then carry that task. Preserve the failure episode when the outcome
completes again; acceptance of an unrelated repair task does not prove the original failed check.
The original action resumes only after the repair result and required review, with the failed
whole-Change check still required. Downstream completed receipts remain historical exact-head
evidence; they are not automatically proof of the new candidate.

If successful finalization/publication authority already exists, use the existing draft/readback and
invalidation owners before admitting the repair; a failed draft transition admits no task. If proof
failed before any successful finalization, no fictitious invalidation ID or provider prerequisite is
created. Reject merged/terminal Changes. C's proof must include both branches, duplicate task
publication after restart, preserved prior results and a semantic/out-of-scope finding rejection.
Include a completed downstream outcome during repair/restart: its old receipt stays intact but
cannot certify the repaired candidate or bypass the required whole-Change proof.

### D. Offline diagnosis

Add `serve/tools/src/owlbear_tools/delivery_diagnostics.py` and a `delivery-diagnose` entry in the
existing tools manifest. Also support direct execution with an already installed supported Python,
without importing `owlbear_delivery`, MCP, Cockpit, runtime parsers or mutating tools commands.
Add `share/prompts/repair-delivery.prompt.md` as the ordinary-session entry; no healthy Delivery claim
or constrained Repairer agent is required.

Fixed v1 operation: `inspect`, with discovered/validated project root, optional Change ID and bounded
text/JSON output. No arbitrary paths/commands, repair/apply flags, user digest, network or provider
calls. Inspect executable/package version metadata, configuration presence/schema, supported persisted
record shapes, pending transaction presence and bounded structural log metadata. Initial known
versions come from this checkout: config 2, frontier 18, coordination 1, state snapshot 2.
Structural recognition is explicitly **not** runtime validity or user-provenance verification.

Use standard-library JSON and filesystem inspection for the bootstrap. YAML transaction manifests
are reported as pending opaque evidence (size/type/locator), not interpreted by a handwritten YAML
parser or replayed. Optional unavailable metadata is reported as unknown rather than initializing
dependencies or state. Read fixed paths below `.owlbear/delivery`, never profile directories.
Bound input to 256 entries, 1 MiB per structured record and 8 MiB total; logs, if recognized, to the
last 64 KiB with an allowlisted structural summary only. Truncation is explicit.

Return versioned status `healthy-structure`, `degraded`, `unsupported` or `unavailable`, fixed
diagnostic codes, safe relative locators, inspected schema/version metadata, bounded counts,
pending-effects indication, `writes_performed: false` and one complete maintenance/continuation
prompt. Never echo raw JSON, exception content, URLs, credentials or arbitrary log lines. Do not
rehash unknown data into authority or call missing provenance “confirmed”.

No mkdir, lock-file creation, transaction recovery, bytecode files, Git refresh/fetch or writes to
the inspected root. Enforce descriptor/realpath containment, no-follow regular-file reads and detect
replacement during inspection; dangling/symlink/FIFO/oversized entries produce bounded diagnostics.
The CLI's read-only promise covers its own writes, not ambient access-time changes. Exit 0 only for
healthy structure, 1 for diagnosed degradation/unsupported state, 2 for unusable invocation/root.
The prompt reports that repair writes/upgrade require D07's supported route; it must not promise an
unimplemented auto-fix or require users to repair files manually.

## Phases and proof

### Execution rules

Run only the requested phase. Sequence **D03-P -> D03-A -> D03-B -> D03-C -> D03-D -> D03-E**;
each implementation successor requires the preceding phase's code, cloud-required proof and
independent review with findings resolved on this PR. D03-D is technically independent of B/C, but
this sequence avoids another writer/scheduling path. Each phase may update only its progress/gaps
here, not silently change approved semantics.

All named new modules/tests below are **planned**, not present or passed. No additional testing
framework or dependency is required. Extend existing test files where their fixtures suffice; new
focused recovery/diagnostic files use the existing pytest setup. T3 owns A/C and acceptance, T2 can
implement settled B/D/E mappings; obtain independent different-family review of implementation.

Every command is scoped. From `/home/runner/work/owlbear/owlbear`, use `uv run --locked pytest` with
explicit paths and `-q -n 1 -m 'not api and not model and not e2e'`; `-n 1` overrides root `-n auto`.
The selections below are inner-loop commands once their planned tests exist. Do not run a bare
pytest, workspace test aggregate, MegaLinter, `quality`, or broad autofix. Runtime for these new
selections is **unmeasured**; record actual duration on first use rather than copying D02 totals.

### Mandatory same-phase companions

- **Central mutation authority (A/B/C):** every added or changed frontier-writing runtime operation,
  including C's repair-task/reopen operation, must participate in `_NORMAL_CHANGE_MUTATIONS` and
  invoke `_require_change_mutable` under the existing policy. Settle any permitted attention state
  explicitly in that owner; no recovery exemption or direct transaction side door. The introducing
  phase owns necessary additions to `tests/test_delivery_worktree_authority.py`, without weakening
  existing assertions. Its focused proof is
  `uv run --locked pytest /home/runner/work/owlbear/owlbear/tests/test_delivery_worktree_authority.py::test_runtime_frontier_writers_use_the_central_mutability_policy -q -n 1 -m 'not api and not model and not e2e'`.
  A/B run this when changing frontier mutation behavior; C must run it for the new reopen operation.
- **Workspace authority (A/C):** when touching registration/removal paths, run the existing
  `test_worktree_registration_has_only_named_lifecycle_callers` and
  `test_worktree_removal_has_only_named_cleanup_caller` nodes in that same file. C's index work
  must run `test_delivery_sources_have_no_git_admin_artifact_path`. No allowlist widening just to
  bypass ownership, and no raw administrative paths in production code or workflow instructions.
- **Readiness mirrors (any introducing phase):** adding a reason/action/status or changing a public
  readiness field requires the corresponding `serve/cockpit/web/src/api/workItems.ts` update in
  that phase, not deferred to E. Its editable companions are the existing readiness consumers
  `pages/WorkPortfolioPage.tsx`, `components/WorkItemDetail.tsx` and
  `__tests__/WorkPortfolio.test.tsx` beneath that frontend source root. Add a focused parity assertion
  for backend reason values versus the TypeScript union to `tests/test_cockpit_boundary.py`, and
  render the newly introduced states in the component test. Use the scoped frontend test/build
  commands in E and the new parity node in the introducing phase; do not repeat unchanged proof.

### D03-A — Exclusion and exact recovery reference path

**Editable sources:** `serve/delivery/src/owlbear_delivery/{recovery.py,portfolio_application.py,
change_workspace.py,delivery_runtime.py,work_items.py,__init__.py}`. Add a loader companion in
`delivery_application_loader.py` only for the default-unavailable dependency, not new host settings.
Use existing transactions; change `runtime_transaction.py` only if an identified missing primitive
is necessary, with its owning test. Tests: owning application/workspace/runtime files plus planned
`serve/delivery/tests/test_recovery.py`.

Export versioned recovery intent/result/evidence-reference contracts and map core readiness together.
No registered executable recovery route yet; current public adapters must remain able to serialize
the bounded rejection described below. Include closure evidence capture at the issuing boundary; never make
existing D02 identity strings into authentication. Close known finalizer/claim failures and one
interrupted engine reference path only when both exclusion and effect reconciliation are proven.
Dirty or damaged unknown state stays contained pending C/D.

**Intermediate public contract (A through D):** retain existing request shapes to produce a truthful
bounded result, not successful recovery from an assertion. `recover_claim`, `repair`/`repair_change`
with a proposal, and legacy `recover_integration_repair_claim` must reject release unless the
engine-configured owner independently verifies exact closure/exclusion and all recovery fences.
`confirmed_lost=true` never contributes evidence, including for non-Builder/legacy claims; a missing
flag is not an alternative release route. A's default-unavailable owner therefore permits **no**
public claim release through these forms. An already completed exact recovery may replay its verified
receipt without another release. Read-only diagnosis and other unaffected valid operations remain
available. Expiry/acquisition and retry transitions cannot bypass this decision.

For a syntactically valid request without verified evidence, raise an engine-owned
`ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED` conflict, mapped to HTTP 409 and the existing MCP diagnostic
envelope with `retry_safe: false`. State that custody/files are unchanged and supported host evidence
is required; neither transport retries nor converts it into “recovered”. Invalid input keeps existing
validation behavior. Add the specific classification before generic runtime-conflict handling.
No new executable public recovery operation is enabled by A.

A's required editable companions are core `diagnostics.py`, MCP `target_models.py`/`target_server.py`,
Cockpit `target_models.py`/`routes/target_work.py`, and `share/skills/w-orchestration/SKILL.md`,
`share/agents/{orchestrator,repairer}.agent.md`. Remove instructions to assert `confirmed_lost=true`
as evidence in the same phase that removes its meaning. Update existing frontend confirmation
wording in `api/workItems.ts` and its corresponding Work detail/portfolio consumers so it cannot
promise that user confirmation stops a worker. Reuse the frontend paths in the mandatory companions
above; no broader role grants or new confirmation UI.

Add A tests in `serve/delivery-mcp/tests/{test_delivery_adapter.py,test_target_server.py}`,
`tests/test_cockpit_work_items.py` and `tests/test_agent_ecosystem_validation.py`: invoke the actual
core with an unavailable/unknown host-evidence owner through each registered recovery route and
assert the same non-retryable rejection, unchanged claim/writer/index/content, and no provider effect.
Cover legacy Planner, Builder and Integration identities, read-only `repair` diagnosis versus rejected
proposal application, exact receipt replay,
and forged/unknown evidence. Keep invalid-input tests. Name new cases `exclusion_required` and run
that selection across the three transport test files with the common pytest flags; include affected
workflow-contract tests and frontend copy tests at A closeout, not only E.

**First discriminating check:** a controlled worker continues writing after lease expiry while a
second application attempts recovery. It must remain the only owner; after a supported close
acknowledgement including child jobs, recovery/restart admits one replacement and no old write can
reach its files/refs. Use a real controlled local process and barriers below the host-evidence port,
not a mocked public recovery method. Test an orphan child separately from its exited parent.

**Negative/replay oracles:** caller-forged receipt, wrong host generation/claim/head, stale proposal,
unknown termination, absent host integration, malformed coordination, failed activation with and
without writer, concurrent recovery, late result, evidence publication failure and crash after each
authority step. No unsupported release; verified evidence and receipt replay survive reopening.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_recovery.py -q -n 1 -k 'exclusion or activation' -m 'not api and not model and not e2e'`.

Closeout adds existing `test_continuation_workers_cannot_be_recovered_by_timeout_or_caller_assertion`,
`test_continuation_live_worker_remains_excluded_after_lease`,
`test_continuation_failure_retains_custody_and_blocks_success_and_mutations`,
`test_engine_result_transaction_recovers_without_repeating_provider` from
`/home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py`, and focused
legacy/Integration/retry bypass cases from the runtime/workspace owners. Do not remove their
unproven-worker rejection assertions to enable the positive path.

### D03-B — Durable retry identity and bounded convergence

**Editable sources:** `serve/delivery/src/owlbear_delivery/{recovery.py,delivery_runtime.py,
portfolio_application.py,work_items.py,__init__.py}`; `delivery_state.py` only for a sanitized durable
budget projection if existing snapshot publication would otherwise reset the allowance on resume.
Tests: planned `test_recovery.py`, existing `test_delivery_runtime.py`,
`test_portfolio_application.py`, and affected snapshot tests if that companion changes.

Implement the B policy table, transactional attempt reservation, stable semantic keys/episode aliases,
backoff, exhausted projection and affected-episode reset. Maintain prior failure records separately
from current presentation. Do not reset a budget when a report is retired or when a new operation ID
is minted for acceptance waiting.

**Oracles:** fake clock at either side of each boundary; restarts between reservation/dispatch/result;
duplicate results charge once; new sessions, task labels, operation IDs and alternating prose/codes
do not replenish attempts; a repair commit still failing the same check exhausts; actual accepted
progress resets only its episode. Exhausted Change A does not block otherwise runnable Change B.
No source-state schema reinterpretation; incompatible persisted metadata fails closed.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_recovery.py -q -n 1 -k 'budget or backoff or fingerprint' -m 'not api and not model and not e2e'`.

Closeout includes owning runtime retry tests and
`test_checkpoint_failure_metadata_survives_reload_and_reanchors_by_head` in
`/home/runner/work/owlbear/owlbear/serve/delivery/tests/test_delivery_runtime.py`, plus an application
acceptance-waiting test proving fresh operation IDs retain the semantic budget.

### D03-C — Nonterminal preservation and proof repair

**Editable sources:** `serve/delivery/src/owlbear_delivery/{recovery.py,change_workspace.py,
portfolio_application.py,delivery_runtime.py,finalization_reports.py,work_items.py,__init__.py}`.
If proof reporting gains a field/category, its strict companions ship in this phase:
`serve/delivery-mcp/src/owlbear_delivery_mcp/{target_models.py,target_server.py}` and
`share/skills/w-change-finalization/SKILL.md`. Tests stay with those contracts:
`test_change_workspace.py`, `test_recovery.py`, `test_finalization_reports.py`,
`test_portfolio_application.py`, and affected MCP report validation tests.

Implement the C exact-path/raw-byte contract and use existing Builder/result/review repair routes.
Do not route D03 through `quarantine_dirty_worktree`'s broad cleanup unchanged. A fixed mechanical
proposal may restore only proven disposable drift; a code/procedure finding issues bounded Builder
work retaining the original action and cumulative review baseline.

**Oracles:** V06 exact formatting bytes/index/HEAD survive preservation then preflight resumes;
binary/deletion/rename/mode/symlink and Git-filter fixtures retain raw identity; V07 any staged,
foreign, secret-like, root/path/head/index drift leaves all affected bytes untouched and unpublished;
V08 a zero-exit mutating proof is not pass, and repairs the procedure before rerun; V13 failures
before/after each preservation, restore and receipt step neither lose data nor falsely free custody.
New Builder commit rejects old proof; interrupted partial restoration rejects third-party edits.
Index-specific cases: linked worktree versus main-checkout index isolation; a different staged blob
from both HEAD and worktree bytes; private paths in an otherwise clean index; inherited Git overrides;
symlink/lock/split/sparse index containment; same-size raw-index edits between proposal and apply and
between partial restore and restart. Assert exact raw index bytes remain unchanged on successful
worktree-only restoration, and newer staging is never overwritten on stale replay. These belong in
the `nonterminal_recovery` selection below, with the mandatory authority checks above.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_change_workspace.py -q -n 1 -k 'nonterminal_recovery' -m 'not api and not model and not e2e'`.

Closeout runs the new `proof_mutated`/`recovery_resume` selections in `test_recovery.py`, plus existing
quarantine replay/changed-byte tests in `test_change_workspace.py` and exact-head review-repair
application tests. Only changed report schema requires its corresponding MCP selection now.

### D03-D — Read-only offline entry

**Editable sources:** proposed `serve/tools/src/owlbear_tools/delivery_diagnostics.py`,
`serve/tools/pyproject.toml`, proposed `serve/tools/tests/test_delivery_diagnostics.py`,
`share/prompts/repair-delivery.prompt.md`; `tests/test_package_boundary.py` and
`tests/test_agent_ecosystem_validation.py` only for this import/prompt contract. No setup, migration
runner, root tooling, live config or general maintenance framework.
The new prompt also requires the existing authority tests in `tests/test_delivery_worktree_authority.py`:
`test_delivery_automation_has_no_special_approval_or_risk_gate`,
`test_delivery_automation_scan_covers_required_roots` and
`test_delivery_sources_have_no_git_admin_artifact_path`. D may add a focused prompt assertion there,
but must preserve the existing scans and constraints.

Implement D's fixed operation and ordinary-session prompt. The entry is distributed through existing
`serve/tools` and `share` sync scopes; no sync-manifest changes are necessary.

**Oracles:** valid synthetic structure; absent MCP; poison imports for the complete Delivery/MCP
packages; malformed frontier/coordination/pending manifest; unsupported versions; missing user
confirmation provenance; unreadable, symlinked, replaced, oversized and special-file fixtures.
Snapshot the disposable tree before/after (including directory membership and contents) and run
against a read-only fixture: no state/lock/bytecode/repair writes, no raw sensitive value in output,
bounded completion and explicit incomplete inspection. Healthy structure must not imply acceptance.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/tools/tests/test_delivery_diagnostics.py -q -n 1 -k 'malformed or no_runtime_import' -m 'not api and not model and not e2e'`.

Closeout runs that focused diagnostic module once, the new offline-boundary test and
`test_prompt_validator_accepts_current_prompt_roots` from
`/home/runner/work/owlbear/owlbear/tests/test_agent_ecosystem_validation.py`.
Direct CLI smoke uses an agent-created disposable root and `python -B` on the new module, with MCP
unavailable; never point it at live Delivery state during this programme.
Run the three authority nodes with
`uv run --locked pytest /home/runner/work/owlbear/owlbear/tests/test_delivery_worktree_authority.py -q -n 1 -k 'delivery_automation_has_no_special_approval_or_risk_gate or delivery_automation_scan_covers_required_roots or delivery_sources_have_no_git_admin_artifact_path' -m 'not api and not model and not e2e'`.

### D03-E — Registered handoff and cumulative package proof

**Editable sources:** existing MCP `target_models.py`/`target_server.py`; Cockpit
`serve/cockpit/src/owlbear_cockpit/{target_models.py,routes/target_work.py}`; core
`portfolio_application.py`, `work_items.py`, `diagnostics.py`, exports and recovery owner only for
required assembled fixes; `share/{agents/orchestrator.agent.md,agents/repairer.agent.md,
prompts/continue-change.prompt.md,skills/w-orchestration/SKILL.md,
skills/w-change-finalization/SKILL.md}`.
Include Builder/conflict skill companions only where the C repair return context needs them:
`share/skills/w-packet-building/SKILL.md` and `share/skills/w-target-conflict-resolution/SKILL.md`.
No replacement workflow or broader role grants.

Ship strict recovery request/result mappings, registrations/annotations and shared error taxonomy.
Keep `repair` the high-level diagnose/apply operation: application discovers exact proposals;
callers forward Change/proposal and, where supported, opaque owner evidence references. Reject
caller-authored preservation paths, commands, budgets, effect receipts and stop assertions.
Keep A's rejection semantics until an exact proposal and independently validated host evidence make
the new registered recovery contract executable. E adds strict proposal/opaque-reference forwarding
and positive recovery tests; it must retain A's negative legacy-call tests and remove any remaining
assertion-based workflow advice. Success compatibility covers verified receipt replay and read-only
requests, never unverified legacy release.
Expose one complete `/continue-change` or `/repair-delivery` prompt in readiness; a new UI control
is unnecessary for U1. Required frontend mirrors ship with each introducing phase; remaining E
presentation changes are limited to `serve/cockpit/web/src/{api/workItems.ts,pages/WorkPortfolioPage.tsx,
components/WorkItemDetail.tsx,__tests__/WorkPortfolio.test.tsx}`, not a UI redesign.

Assembled proof uses real application state and `Client(assemble_target_server(...))`, the existing
HTTP test client and temporary repos; fakes are below host/provider owners, not substitutes for
recovery, workspace or runtime methods. Verify all four interrupted engine rows, finalizer failure
before checks, claim activation both ways, bounded Builder repair, offline degraded entry and a fresh
continuation returning to the original action. Unknown outcomes remain contained throughout every
adapter. Include exact stale/foreign/forged fields, absent host capability and independent Change
progress. Review response copy for checks-not-run, preserved bytes, current owner and next action.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_target_server.py -q -n 1 -k 'registered_recovery' -m 'not api and not model and not e2e'`.

Closeout, split into bounded selections:

- `uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_delivery_adapter.py /home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_target_server.py /home/runner/work/owlbear/owlbear/tests/test_cockpit_work_items.py -q -n 1 -k 'recovery or continuation' -m 'not api and not model and not e2e'`.
- New assembled D03 cases in `test_recovery.py`; run only missing/invalidated V06–V10/V13/V18/V20
  proof from A–D. Existing passed phase evidence remains valid only for unchanged relevant inputs.
- Explicit changed-role/registered-tool tests in `test_agent_ecosystem_validation.py` plus affected
  tests in `test_package_boundary.py` and `test_cockpit_boundary.py`. Full module runs are ceilings,
  not automatic requirements.
- Scoped `uv run --locked ruff check` and `ruff format --check` on explicit changed Python files.
  If frontend types/presentation change, use locked npm dependencies and
  `npm --prefix /home/runner/work/owlbear/owlbear/serve/cockpit/web test -- src/__tests__/WorkPortfolio.test.tsx`,
  then one `npm --prefix /home/runner/work/owlbear/owlbear/serve/cockpit/web run build` for the type/bundle
  contract. Current frontend lint authority is Biome, not the historical ESLint command. No browser
  run is required for an unchanged UI; actual interaction changes need the maintained disposable gate.

### Acceptance allocation

| Claim | Cloud-required proof | Other environment |
| --- | --- | --- |
| V06/V07/V13 | C raw bytes, path/index/head fences, privacy containment and every durable failure boundary | External CI broad regressions |
| V08/V09 | B/C persisted procedure failure, episode budget, restart/backoff/exhaustion and resumed review | External CI broad regressions |
| V10 | A controlled still-writing process and descendant, real owner recovery, restart and late-result rejection; absent host remains blocked | Actual VS Code invocation exclusion/descendant closure must be demonstrated on the host, not inferred from fixture success |
| V18/V20 | D malformed-runtime read-only CLI; E real degraded API/entry and provenance-negative cases | D07 owns supported repair/migration, D08 owns final host acceptance |
| End-to-end repair | E actual registered MCP/HTTP -> core -> workspace/provider fake -> restart/continuation | Named host dispatch/exclusion and external transport in D08-H |

## Progress and verification gaps

| Phase | Implementation revision | Actual proof/review | Remaining |
| --- | --- | --- | --- |
| D03-P | Repaired plan `6c8c039a05c32ec265e45430d0b8a4e8e05be23c` | Independent Claude Opus 5 `d03-p-prerequisite` review PASS, supplied by the coordinating session; all three original findings resolved | Prerequisite satisfied; explicit user approval recorded separately above |
| D03-A | Source `4dff7c0421aca9b0f84330c4fc1c52689158bbb0`, preserving interrupted `ec392dfa91790bd270378e550ab6ed1ca01f1959` and implementing approved `6c8c039a05c32ec265e45430d0b8a4e8e05be23c` | 84 affected closeout tests, 4 authority/parity tests and 3 additional nonclaim restart tests passed; all 18 changed Python files pass Ruff check/format, with scoped recheck after follow-up. Independent Claude Opus 5 review found no blocking in-scope defects at the published source; the latest review also rechecked merged head `43b91fdf0c5707551aaadad1b567173183174b06` and found no actionable A finding. | Ready for review, not acceptance or B authorization. Automated review unavailable; CodeQL timed out. External CI, baseline workflow mismatch and actual host integration remain outstanding. |
| D03-B | Source `3864bafade9a33f2637cdd116b75d0b764cc790f`, following resume repair `0b37ca2dca6c745f1352f060da4e010da27e484b` above `cc11df10b851a145f77912e866ff9eb4ff4d3d48`; user resume comment `5723694522`, approved specification `43b91fdf0c5707551aaadad1b567173183174b06` | Focused repair proof below; independent Opus 5 confirmed the reported source findings fixed at the final source. Earlier counts are not a current phase pass. | Partial: owner/ledger transaction coupling, legacy allowance reconciliation and observation integration block B completion and C. Final CodeQL timed out; automated review unavailable. |
| D03-C | Not started | None | Nonterminal preservation/proof repair |
| D03-D | Not started | None | Offline diagnostics |
| D03-E | Not started | None | Registered/cumulative proof |

### D03-B resumed verification — 2026-09-18

Implementation source: `3864bafade9a33f2637cdd116b75d0b764cc790f`, preserving the interrupted
`cc11df1` work. Approved contract and phase boundaries are unchanged.

- Preserved the interrupted fixed-clock generated-ID repair and proved it. The first discriminating
  application checks failed at the interrupted head: both engine-result crash/replay variants left
  their reservation unaccounted, and acceptance readiness bypassed the first backoff. All three now
  pass through the real application/owner fixtures.
- Exact engine-result replay now reconciles its original reservation without a provider repeat.
  Verified recovery replay reconciles the exact released reservation; a durable finalizer report
  repairs interrupted failure accounting before release. Known failed outcomes retain backoff.
  Accepted-success accounting and its affected-episode reset share one ledger transaction.
- Worker block outcomes, accepted Builder result submission/replay, stable task-lineage matching and
  current claimable-task readiness now use the same budget. Success on another task does not reset
  the failed task. Worker repair heads and explicitly linked task aliases retain the original episode.
  Fractional-second and regressed clocks cannot shorten the persisted delay.
- Automatic acceptance observations stop after three, including across new sessions/operation IDs.
  Exhaustion itself is never authorization. No caller-provided explicit-observation flag is accepted;
  a genuinely admitted later explicit continuation remains an integration gap rather than invented
  authority. The internal ledger's bounded nonautomatic-observation primitive remains tested.
- New real worker and finalizer tests prove three-attempt exhaustion, report retirement/recovery and
  restart persistence, plus independent Change progress. A reservation interrupted before intent
  publication remains consumed and contained; no missing record is treated as dispatch-stop evidence.

Actual environment: initial `uv` was missing, and the frontend test failed because `cross-env` was
missing. Restored uv **0.12.16** after a clean advisory check, the existing locked Python workspace
with available **Python 3.14.7**, and `npm ci --ignore-scripts --no-audit --no-fund`. No manifest or lock
was changed. Node was **22.23.2**, below the declared Node 24 requirement; successful frontend proof
does not replace the pinned-Node external gate. The actual lock resolved Vitest **5.0.1** and Vite
**8.3.0**. All scratch/test roots were inside `.owlbear/scratch/`; `GIT_CEILING_DIRECTORIES` was set
to that directory so a synthetic non-repository fixture could not discover the enclosing checkout.
The uv executable is `.owlbear/scratch/d03-b-tools/bin/uv`; commands used
`TMPDIR=$PWD/.owlbear/scratch/d03-b-temp`, a local `UV_CACHE_DIR` and per-run `--basetemp` beneath
that test root (final run: `pytest-current-proof`). Disposable test repositories and download cache
were removed at handoff; the executable and proof logs remain for the coordinating owner.

Proof (counts overlap and must not be summed):

- One affected Python closeout: `test_retry_ledger.py`, `test_portfolio_application.py`,
  `test_recovery.py`, `test_work_items.py`, the runtime checkpoint-metadata node, readiness parity
  and central-mutability nodes, with `uv run --locked pytest -q -n1 -m 'not api and not model and not e2e'`:
  **456 passed, 3 failed in 114.16s**. One failure exposed a stale immediate-acceptance-retry test
  assumption; its clock now advances while preserving the original assertions. A second exposed
  missing verified-recovery receipt accounting, repaired in the owner. The third was the
  enclosing-Git-repository fixture issue described above. All three passed targeted rechecks.
- Post-repair affected-owner/consumer recheck: **87 passed in 27.66s**, covering the ledger and
  recovery modules, exact application result/recovery/worker consumers, parity and mutability.
  Later lineage and second-task-readiness changes were checked with the final command below:

  ```shell
  uv run --locked pytest \
    serve/delivery/tests/test_retry_ledger.py \
    serve/delivery/tests/test_portfolio_application.py \
    serve/delivery/tests/test_recovery.py \
    -k 'retry_ledger or budget or reservation or engine_result_transaction or submit_result or failed_activation_identity or finalization_replays_atomic or verified_clean_finalizer or interrupted_report_accounting or restart_cannot_use_exclusion' \
    -q -n1 -m 'not api and not model and not e2e' --tb=short
  ```

  **33 passed in 10.42s**.
- `npm test -- --run src/__tests__/WorkPortfolio.test.tsx` in `serve/cockpit/web`:
  **111 passed in 117.34s**; `npm run build` passed (Vite **4.50s**). Scoped Biome checked the four
  existing B frontend files in **164ms**. No frontend source changed during this resume.
- Ruff check and format check passed on the six changed Python files: `recovery.py`,
  `portfolio_application.py`, `__init__.py`, `test_retry_ledger.py`, `test_portfolio_application.py`,
  and `test_recovery.py`. `git diff --check` passed.
- The coordinating session then supplied four Opus findings against committed `cc11df1`. Worker
  readiness identity/current-task matching, inferred explicit observation and ordinary-acquisition
  reservation release were already repaired. Its additional candidate-publication finding was valid:
  `publish_delivery_plan` / `publish_delivery_result` no longer reset anything; only accepted
  `advance` / `submit_result` paths account accepted progress. Real planner/Builder tests now assert
  candidate publication leaves attempts at one and reset count zero, then accepted result replay
  resets exactly once. The final review-driven selection passed **9 tests in 7.76s**; a temporary
  caller flag was removed and strict request validation rejects it. No public authority was expanded.
  After the scoped lint-only return simplification, the three planner/Builder publication cases
  passed again in **4.10s**, and all six changed Python files passed Ruff check/format.
- Final coordinating-owner-requested bounded closeout: **36 passed in 10.78s** on the unchanged
  candidate, using `uv run --locked pytest -q -n1 -m 'not api and not model and not e2e' --tb=short`.
  Scope was the ledger file; the new application budget/reservation/result-replay nodes; finalizer
  budget, interrupted-report and exact-recovery nodes; central mutability and readiness parity;
  plus runtime `test_checkpoint_failure_metadata_survives_reload_and_reanchors_by_head`,
  `test_repeated_retry_exclusion_required_preserves_claim_and_budget` and
  `test_clean_implementation_retry_exclusion_required`. No whole application-file rerun was made.
  A final test-only assertion makes Planner acceptance explicit: candidate publication retains one
  attempt/zero resets, while accepted `advance` yields zero attempts/one reset. That Planner case and
  both Builder submission/replay variants passed **3 tests in 9.90s**, with file-scoped Ruff checks.
- Final scoped re-review repairs above published `0b37ca2`: engine lookup now requires the exact
  semantic key; worker same-lineage repair matching is unchanged. Three ledger cases prove changed
  engine head, target or finalization cannot borrow an exhausted episode's budget. Block bookkeeping
  errors after the durable runtime transition no longer prevent Delivery-state publication; the
  reservation stays consumed, and exact transition replay records one failure without refund.
  These new tests plus affected worker/finalizer/acceptance checks passed **9 tests in 5.74s**.
  Ruff check/format passed for the four changed Python files. This production repair requires
  current-candidate re-review and scanning; the parent's zero-alert CodeQL result for `0b37ca2`
  is prior-source evidence, not a scan of these changes.

**Remaining B integration gaps / review boundary:** reservation, owner receipt and retry accounting
are still distinct durable transactions; supported receipt replay is tested, but no complete
same-transaction owner/accounting proof or safe no-start reservation refund is claimed. Existing
nonzero legacy binding retry counters have not been imported into the new authority. Admitted
explicit-observation entry and automatic background acceptance-observer budget coverage remain
unverified. These are B completion questions, not
permission to start E, reinterpret the approved contract, or enable live services. Independent
current-candidate review, external CI/pinned Node and host proof remain with their existing owners.
The coordinating session inspected the `cc11df1` source, agent, Cockpit and setup CI runs:
all were `action_required`; none is a phase pass. Historical `dev` failure logs were also inspected
and do not provide B proof. The independent current-source recheck is recorded below.
No full suite, MegaLinter, quality aggregate, real provider mutation, live state or activation was run.

#### Resume review and next completion boundary

Independent read-only Claude Opus 5 reviewer `d03-b-audit` compared B against A's reviewed
`43b91fd`, inspected the interrupted checkpoint, then reviewed the repairs and bound its final
source verification to `3864bafade9a33f2637cdd116b75d0b764cc790f`. The reviewer confirmed these
reported defects fixed:

- worker readiness used a different role/task identity from reservation;
- publishing an unaccepted candidate reset the episode;
- exhausted state inferred permission for an extra explicit observation;
- ordinary acquisition cleared containment, and containment discarded persisted backoff;
- resumed matching combined distinct engine heads, targets and finalizations;
- retry bookkeeping failure after a committed block skipped publication.

The latent timestamp-versus-clock-callable error was also corrected. The reviewer ran no tests;
the implementing worker ran the focused checks recorded above. This confirms the specific
repairs, **not B completeness or acceptance**.

Changed-file secret scans passed before both source commits. `parallel_validation` on `0b37ca2`
reported **zero Python CodeQL alerts**. The required rerun after the final source changes at
`3864baf` **timed out**, with an explicit instruction not to retry in this environment. The earlier
scan is not a final-source scan pass. Automated review was unavailable on both calls because its
configured model was absent; the wrapper's success label is not a pass. External verification
must obtain the outstanding final-source security check.

The next B session must resolve these concrete obligations before requesting phase acceptance:

1. Couple owner reservations/receipts and ledger accounting through the existing transaction
   authority, or prove the approved exact reconciliation boundary at every crash point. Retain an
   uncertain reservation; a missing intent is not proof that dispatch never began. Test accepted
   worker/finalizer/engine outcomes across restart without requiring the caller to reconstruct history.
2. Trace and reconcile nonzero legacy per-binding retry counters into the single allowance. A new
   empty ledger must not grant extra attempts for an existing episode; add legacy-state fixtures.
3. Trace every automatic acceptance-observation entry, including background publication observation,
   and apply/prove the persisted three-observation budget and backoff without disabling pure diagnosis.
4. Implement the approved bounded later explicit observation through a supported, distinguishable
   continuation path and its actual registered consumers. It must not reset the failure budget,
   infer authorization from exhaustion, or treat a caller assertion as human approval.

These are **B completion blockers**, not presumed safe containment and not work reassigned to E.
The integration owner must not start C or accept B on the strength of repaired findings alone.
No source changes followed this exact-head review; the final commit updates only this progress record.

### D03-B prior-source verification record — 2026-09-18

- Approval boundary: user comment `5723189457` approves the presented B plan and requests Luna Max,
  with work stopping after B. No commit, progress report, comment, service, live record or provider
  mutation was made by this implementation pass.
- Focused Python proof (all with `UV_PYTHON=3.14.3 uv run --locked` and `pytest -n1`):
  `serve/delivery/tests/test_portfolio_application.py serve/delivery/tests/test_recovery.py -q`
  passed **419 tests in 156.13s**; `serve/delivery/tests/test_retry_ledger.py -q` passed
  **8 in 1.45s**; `serve/delivery/tests/test_delivery_runtime.py -q` passed **66 in 8.84s**;
  `serve/delivery/tests/test_work_items.py tests/test_cockpit_boundary.py -q` passed **37 in
  1.81s** with one pre-existing Starlette deprecation warning. The first post-containment run
  exposed 10 regressions; the final scoped run above passed after preserving active readiness and
  releasing only verified/resolved worker custody without replenishing episode budgets.
- Frontend proof: `npm test -- --run` passed **315 tests in 97.51s**; `npm run build` succeeded
  (Vite reported **3.33s**); pinned scoped Biome
  `serve/cockpit/web/node_modules/.bin/biome check serve/cockpit/web/src/api/workItems.ts
  serve/cockpit/web/src/components/WorkItemDetail.tsx serve/cockpit/web/src/components/workItemPresentation.ts
  serve/cockpit/web/src/__tests__/WorkPortfolio.test.tsx` checked **4 files in 104ms**.
- Static proof: `UV_PYTHON=3.14.3 uv run --locked ruff check
  serve/delivery/src/owlbear_delivery/recovery.py serve/delivery/src/owlbear_delivery/portfolio_application.py
  serve/delivery/src/owlbear_delivery/delivery_runtime.py serve/delivery/tests/test_retry_ledger.py` passed in
  **0.04s**; the same four paths with `ruff format --check` passed in **0.06s**; `UV_PYTHON=3.14.3
  uv run --locked python -m py_compile serve/delivery/src/owlbear_delivery/recovery.py
  serve/delivery/src/owlbear_delivery/portfolio_application.py serve/delivery/src/owlbear_delivery/delivery_runtime.py
  serve/delivery/src/owlbear_delivery/work_items.py serve/delivery/tests/test_retry_ledger.py` passed in **0.22s**.
  `git diff --check` passed. No full suite,
  MegaLinter, quality gate, E2E, external CI, CodeQL, independent B review, real host exclusion
  proof or live activation was run or inferred.

### D03-P verification record

- Scope check: only this plan is changed; no product, programme or live-state edits.
- `git diff --no-index --check` on the new file and committed `git diff HEAD^ HEAD --check` passed.
  Linked files/headings and named existing test nodes were inspected against source; new files and
  test selections are labeled planned. No Markdownlint executable was available; no lint pass is claimed.
- Secret scanning passed for the plan before publication.
- Independent read-only specification review: `d03-plan-review`, Claude Opus 4.8, returned PASS on
  the initial plan with one non-blocking source-attribution correction; the core diagnostics package
  is now qualified explicitly. Its second review returned PASS on the completed-outcome repair
  clarification and privacy refinements against the working diff from the plan checkpoint. The
  non-blocking recommendation to test a completed downstream outcome during repair/restart is
  explicit in C. Those earlier PASS results were superseded by the subsequent PR review below;
  user specification approval remains pending.
- `parallel_validation` was invoked on plan checkpoint `0fbd3b19745c6d796dc482d9053233ea48b27acf`.
  CodeQL skipped this documentation-only change. Its automatic review component could not run
  because its configured model was absent from the model registry; “no comments” is not a review
  pass. The independent specification review is the available substitute, not a claim that the
  unavailable component ran. Product tests/builds are intentionally unrun for P.

### D03-P review repair

Controlling [PR review](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5713893377):
Claude Opus 5 reviewed `466b5ea50e8d9569c0e4295941a05b4fb0e84134` against
`dev@fd0dec2aaca7831532505573c4d348eaa9012dbb` and requested changes. This repair is a proposed
response, **not** a self-issued re-review pass or implementation approval.

| Finding | Plan repair | Verification required of implementation |
| --- | --- | --- |
| 1 — Missing authority-invariant proof (medium) | Mandatory same-phase companions assign central mutation registration/policy and `test_delivery_worktree_authority.py` to A/B/C; C must prove its new reopen operation; D owns the prompt scans. | Exact central-mutability node, applicable workspace-caller nodes and named prompt/admin-path scans; no recovery exemptions. |
| 2 — Intermediate public handoff (low) | A now defines no-evidence rejection, verified receipt replay, read-only diagnosis, error mapping and same-phase transport/workflow/copy companions. Readiness mirrors/parity proof belong to each introducing phase; E adds positive registered recovery without reviving assertion authority. | A's actual registered MCP/HTTP rejection cases and unchanged-state assertions, workflow/copy checks, and reason-union parity; E retains them alongside supported positive cases. |
| 3 — Raw-index capture boundary (low) | C names Git-resolved index/admin-directory discovery, independent containment, descriptor capture, override rejection, index privacy/limits, supported full-index boundary and no-index-write replay. | Linked/main index isolation, staged/private/index-layout negatives and exact raw-byte drift before apply/restart; no restoration over newer staging. |

Repair validation: the six named existing authority-test nodes and affected public contracts were
checked against source; `git diff --check` passed and changed-file inspection confirmed only this
plan differs. Secret scanning passed. Markdownlint is unavailable; no Markdown lint pass is claimed.
No proposed implementation tests were run or claimed to exist or pass. The final repair
commit is identified by the PR publication history; a later reviewer must review that published head,
not reuse the earlier candidate's verdict.
`parallel_validation` was invoked on repair checkpoint `558ad949fd1e7030214ae4308d498994cfc4c706`:
CodeQL skipped the documentation-only change; automated review remained unavailable because its
configured model was absent. No automated review pass or independent re-review is claimed.

### D03-A resumed implementation checkpoint — 2026-09-17

The approved contract is unchanged. The interrupted head `ec392dfa91790bd270378e550ab6ed1ca01f1959`
already contained substantially more than its stale progress description:

- `recovery.py` contains the versioned invocation, intent, evidence/reference and receipt contracts,
  a narrow injected trusted-host port defaulting to unavailable, and immutable bounded journal helpers.
  Invocation registration is captured at claim/finalizer/engine issuance; existing D02 identity strings
  are not authenticated provenance.
- The application captures clean exact claim/finalizer custody or a recorded interrupted `mark-ready`
  effect. It verifies the configured host outside global locks, rechecks original owner/frontier/
  coordination/Git fences and delegates atomic receipt/frontier/custody release to the runtime and
  coordinator. Unknown engine outcomes, dirty workspaces and malformed state remain contained.
  Original failure reports, attempts and engine results remain history; late old results are rejected.
- Public claim recovery, legacy
  Integration recovery and exact repair-proposal application reject without changing custody/files;
  read-only diagnosis and existing input validation remain. Exact already-completed recovery can
  replay only after configured-owner verification. Timeout cannot free a legacy Planner.
- Runtime claim-removal and retry paths reject unsupported release. Central mutation registration
  and `_require_change_mutable` remain intact, with the authority invariant passing.
- Shared diagnostics classify the new code as a non-retryable conflict before generic handling.
  Real-core strict MCP adapter, registered MCP server and HTTP tests preserve exact claim/writer,
  index, worktree bytes and refs, including separately staged/private-untracked fixture bytes.
- Recovery tests cover activation with/without a recorded writer, failed finalizer history,
  interrupted ready-effect readback without repeating the mutation, wrong identity/head/scope,
  malformed coordination, concurrent host waits, late results and transaction failures.
- Workflow, proposal and frontend copy no longer treat user confirmation as worker termination.
  Existing no-evidence positive legacy tests now assert rejection/preservation. No dirty restoration,
  retry ledger, offline entry, provider activation or new public recovery operation is implemented.

This resume fixes and proves the remaining inspected restart defect:

- An `excluded` receipt previously released custody across restart without requiring normal acquisition
  to revalidate ongoing exclusion. Coordination now atomically retains the excluded recovery identities.
  Ordinary custody/frontier mutations and shared readiness fail closed until the application owner has
  freshly verified each identity in that coordinator process. Transaction roll-forward does not bypass
  this guard, and a fork cannot inherit verification through a cached PID. Verification itself remains
  outside global locks; the internal exact recovery/replay path re-establishes permission.
- Exclusion may become confirmed closure during replay or after evidence-journal publication fails.
  Fresh owner evidence may advance `excluded` to `closed`, never reverse closure or change identity;
  original immutable evidence/receipt bytes remain unchanged.
- The controlled parent/orphan process now actually writes a tracked file **and shared Git ref after
  lease expiry and rejected recovery**. No replacement is admitted. The fixture worker restores its
  own synthetic effects, then the host joins its complete job channel before admitting exactly one
  replacement. Old dispatch cannot resume; replacement files/refs stay intact.
- Added backend/TypeScript readiness-reason parity proof. No new readiness enum or frontend source
  change was needed: unverified restarted exclusion uses existing `coordination-unavailable`.

No fake provider is represented as production integration, and no unsupported D02 invocation is
retroactively trusted. This is implementation/proof evidence for independent review, not phase
acceptance. B–E remain unstarted.

Changed file inventory, relative to the inspected absolute checkout
`/home/runner/work/owlbear/owlbear`:

- Core: `serve/delivery/src/owlbear_delivery/recovery.py` (new), `__init__.py`, `change_workspace.py`,
  `portfolio_application.py`, `delivery_runtime.py`, `diagnostics.py`.
- Core tests: `serve/delivery/tests/test_recovery.py` (new), `test_portfolio_application.py`,
  `test_delivery_runtime.py`.
- MCP: `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py`, `target_server.py`;
  `serve/delivery-mcp/tests/test_delivery_adapter.py`, `test_target_server.py`.
- HTTP: `serve/cockpit/src/owlbear_cockpit/target_models.py`, `routes/target_work.py`;
  `tests/test_cockpit_work_items.py`.
- Frontend: `serve/cockpit/web/src/api/workItems.ts`, `components/WorkItemDetail.tsx`,
  `__tests__/WorkPortfolio.test.tsx`.
- Workflow: `share/skills/w-orchestration/SKILL.md`, `share/agents/orchestrator.agent.md`,
  `share/agents/repairer.agent.md`, `tests/test_agent_ecosystem_validation.py`.
- This package progress record: `.owlbear/research/delivery-cloud-d03-plan.md`.
- Resume-only consumer proof: `tests/test_cockpit_boundary.py`.

#### Resume proof and environment

All commands ran from `/home/runner/work/owlbear/owlbear`. The fresh runner lacked `uv`; after
advisory clearance (no vulnerabilities reported), the tooling command was:

```shell
mkdir -p .owlbear/scratch/d03-resume
python -m pip install --disable-pip-version-check \
  --target .owlbear/scratch/d03-resume/tools uv==0.12.15 --quiet
```

Repository-local ignored scratch was used for this writer's disposable tools/state. No manifests
changed. The first `uv run --locked` restored CPython 3.14.7 and 163 locked workspace packages;
the default workspace sync included unrelated workspace dependencies, and was not repeated.
For the following commands, `uv` denotes `.owlbear/scratch/d03-resume/tools/bin/uv`, with
`TMPDIR=$PWD/.owlbear/scratch/d03-resume` and
`UV_CACHE_DIR=$PWD/.owlbear/scratch/d03-resume/cache`.

The first discriminating invocation, before edits, was:

```shell
uv run --locked pytest -n 1 --basetemp=.owlbear/scratch/d03-resume/test-first \
  serve/delivery/tests/test_recovery.py::test_process_exclusion_then_verified_all_jobs_close_admits_one_replacement \
  serve/delivery/tests/test_recovery.py::test_owner_evidence_exclusion_required_without_verified_closure \
  serve/delivery/tests/test_recovery.py::test_recovery_caller_cannot_supply_forged_evidence
```

**6 passed, 3.21 s pytest elapsed**; dependency-install wall time was not measured separately.
After the restart guard edit, the new restart node plus
`test_verified_exclusion_is_revalidated_after_restart`, using
`uv run --locked pytest -q -n 1 -m 'not api and not model and not e2e'` and
`--basetemp=.owlbear/scratch/d03-resume/test-restart`, initially failed **3 cases in 1.58 s**:
the strict coordination model needed its established JSON-array-to-tuple normalizer. The normalizer
fix passed the same nodes (**3 passed, 1.58 s**, `test-restart-fixed` basetemp).
The strengthened controlled-process node passed **2 cases, 1.51 s** (`test-process` basetemp).
After adding evidence-publication crash coverage and exclusion-to-closure evolution, the new
`test_restart_cannot_use_exclusion_receipt_without_current_host_verification` node passed
**3 cases, 1.63 s** (`test-evidence-evolution` basetemp), with the same flags.

Mandatory authority and parity invocation:

```shell
uv run --locked pytest -q -n 1 -m 'not api and not model and not e2e' \
  --basetemp=.owlbear/scratch/d03-resume/test-authority \
  tests/test_delivery_worktree_authority.py::test_runtime_frontier_writers_use_the_central_mutability_policy \
  tests/test_delivery_worktree_authority.py::test_worktree_registration_has_only_named_lifecycle_callers \
  tests/test_delivery_worktree_authority.py::test_worktree_removal_has_only_named_cleanup_caller \
  tests/test_cockpit_boundary.py::test_delivery_readiness_reason_typescript_parity
```

**4 passed, 2.09 s**. The once-only affected closeout used
`GIT_CEILING_DIRECTORIES=$PWD/.owlbear/scratch` and:

```shell
/usr/bin/time -f 'wall=%e s' uv run --locked pytest -q -n 1 \
  -m 'not api and not model and not e2e' --basetemp=.owlbear/scratch/d03-resume/test-closeout \
  serve/delivery/tests/test_recovery.py \
  serve/delivery/tests/test_portfolio_application.py::test_continuation_workers_cannot_be_recovered_by_timeout_or_caller_assertion \
  serve/delivery/tests/test_portfolio_application.py::test_legacy_process_exclusion_required_after_lease \
  serve/delivery/tests/test_portfolio_application.py::test_continuation_failure_retains_custody_and_blocks_success_and_mutations \
  serve/delivery/tests/test_portfolio_application.py::test_engine_result_transaction_recovers_without_repeating_provider \
  serve/delivery/tests/test_portfolio_application.py::test_repair_change_diagnoses_but_exclusion_required_to_apply \
  serve/delivery/tests/test_portfolio_application.py::test_repair_facade_matches_existing_repair_proposal_authority \
  serve/delivery/tests/test_portfolio_application.py::test_acquisition_retains_expired_planning_claim_at_inclusive_boundary \
  serve/delivery/tests/test_portfolio_application.py::test_acquisition_retains_expired_clean_builder_claim_without_relaunch \
  serve/delivery/tests/test_portfolio_application.py::test_expired_claim_recovery_failure_does_not_block_independent_change \
  serve/delivery/tests/test_delivery_runtime.py::test_dirty_implementation_retry_rejects_without_mutating_claim_or_worktree \
  serve/delivery/tests/test_delivery_runtime.py::test_repeated_retry_exclusion_required_preserves_claim_and_budget \
  serve/delivery/tests/test_delivery_runtime.py::test_clean_implementation_retry_exclusion_required \
  serve/delivery/tests/test_delivery_runtime.py::test_integration_repair_claim_is_change_scoped_and_exact \
  serve/delivery/tests/test_change_workspace.py::test_coordinator_recovers_pending_runtime_transaction \
  serve/delivery/tests/test_change_workspace.py::test_restart_recovers_after_git_succeeds_before_writer_release \
  serve/delivery/tests/test_change_workspace.py::test_restart_recovers_from_each_git_interruption \
  serve/delivery/tests/test_change_workspace.py::test_restart_recovers_missing_worktree_at_each_git_interruption \
  serve/delivery-mcp/tests/test_delivery_adapter.py::test_real_core_recovery_exclusion_required \
  serve/delivery-mcp/tests/test_delivery_adapter.py::test_verified_completed_recovery_replay \
  serve/delivery-mcp/tests/test_target_server.py::test_registered_recovery_exclusion_required \
  serve/delivery-mcp/tests/test_target_server.py::test_registered_verified_completed_recovery_replay \
  tests/test_cockpit_work_items.py::test_real_core_claim_recovery_exclusion_required \
  tests/test_cockpit_work_items.py::test_http_verified_completed_recovery_replay \
  tests/test_agent_ecosystem_validation.py::test_recovery_workflows_require_host_exclusion_not_caller_confirmation
```

**84 passed, 19.94 s pytest / 20.72 s wall**, one existing Starlette/AnyIO deprecation warning.
No test assertion was weakened or skipped. Final static invocation:

```shell
mapfile -t paths < <(git diff --name-only 6c8c039a05c32ec265e45430d0b8a4e8e05be23c -- '*.py')
/usr/bin/time -f 'ruff-check wall=%e s' uv run --locked ruff check "${paths[@]}" --output-format concise
/usr/bin/time -f 'ruff-format wall=%e s' uv run --locked ruff format --check "${paths[@]}"
git diff --check
```

**All 18 Python files passed**, check **0.08 s wall**, format **0.06 s wall**; whitespace check passed.
Two initial local line-length findings in the new coordination field/guard were fixed before this run.
Unchanged frontend evidence below is **prior proof, not rerun**, and remains below pinned-Node acceptance.
No full suite, MegaLinter, service, live state, provider mutation or browser acceptance was run.
The coordinating session owns secret scanning, independent review, publication and final validation;
this writer did not commit, publish, approve A, or start B.

The coordinator subsequently requested the missing nonclaim restart oracle, without public-route
expansion. The existing finalizer and interrupted-ready tests now also exercise `excluded` evidence:
after reopening, unavailable host evidence leaves frontier/custody unchanged and mutations blocked;
the internal `_complete_recovery` path verifies the stable reference and re-enables custody after
closure. A finalizer replacement is acquired afresh while old failure authority remains historical.
For ready recovery, the original blocked/missing result stays unchanged and provider mutation count
remains one. No public executable recovery route is added: A–D use the internal owning port;
registered executable handoffs remain E's scope. Providers must retain stable opaque references
across restart, including exclusion-to-closure advancement; lost provenance remains unavailable.

Follow-up command (same environment as above):

```shell
/usr/bin/time -f 'wall=%e s' uv run --locked pytest -q -n 1 \
  -m 'not api and not model and not e2e' \
  --basetemp=.owlbear/scratch/d03-resume/test-nonclaim-revalidation-fixed \
  serve/delivery/tests/test_recovery.py::test_verified_clean_finalizer_recovery_keeps_failed_history \
  serve/delivery/tests/test_recovery.py::test_verified_interrupted_ready_owner_readback_never_redispatches \
  -k excluded
```

**3 passed, 2.47 s pytest / 3.28 s wall**. An initial run also passed all three
(**2.44 s / 3.20 s wall**, `test-nonclaim-revalidation` basetemp); a helper-argument lint finding
was repaired by deriving its runtime root/reference from the already-bound intent/receipt.
Scoped `ruff check` and `ruff format --check` on `serve/delivery/src/owlbear_delivery/recovery.py`
and `serve/delivery/tests/test_recovery.py` then passed (**0.04 s / 0.03 s wall**).
No closeout or unaffected tests were repeated.

#### Earlier partial-checkpoint proof (prior evidence, not rerun)

All Python commands ran from `/home/runner/work/owlbear/owlbear` with:

```shell
export PATH=/home/runner/work/owlbear/owlbear/.owlbear/scratch/d03-tools/bin:$PATH
export TMPDIR=/home/runner/work/owlbear/owlbear/.owlbear/scratch
export UV_CACHE_DIR=/home/runner/work/owlbear/owlbear/.owlbear/scratch/uv-cache
export UV_PYTHON_INSTALL_DIR=/home/runner/work/owlbear/owlbear/.owlbear/scratch/uv-python
```

The first process command failed because `uv` was absent (exit 127, 0.001 s). After advisory DB
clearance, `uv==0.12.15` was installed in the ignored scratch tools directory; locked workspace
dependencies were restored by `uv run --locked` (including CPython 3.14.7). The first two-process-case
run passed in 2.48 s (54.466 s wall including dependency restoration). No manifest/lockfile changed.

The owning closeout command was:

```shell
uv run --locked pytest -n 1 -m 'not api and not model and not e2e' \
  /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py \
  /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_delivery_runtime.py \
  /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_recovery.py \
  /home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_delivery_adapter.py \
  /home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_target_server.py \
  /home/runner/work/owlbear/owlbear/tests/test_cockpit_work_items.py \
  /home/runner/work/owlbear/owlbear/tests/test_delivery_worktree_authority.py \
  /home/runner/work/owlbear/owlbear/tests/test_agent_ecosystem_validation.py \
  -q --tb=short --basetemp=/home/runner/work/owlbear/owlbear/.owlbear/scratch/d03-a-closeout
```

Result: **754 passed, 2 failed**, one existing Starlette deprecation warning; pytest 113.15 s,
wall 114.237 s. Failures were not hidden:

1. `test_delivery_loader_rejects_git_and_state_identity_before_composition`: repository-contained
   scratch allowed Git to discover the enclosing checkout. Rechecked with
   `GIT_CEILING_DIRECTORIES=/home/runner/work/owlbear/owlbear/.owlbear/scratch`; passed.
2. `test_declared_mcp_tools_exist_in_live_registries`: pre-existing expected orchestrator tool set
   omits `acquire_change_action` and `execute_change_action`, both already present in HEAD's agent
   frontmatter. Both baseline files were inspected with `git show HEAD:<path>`; their mismatch is
   unchanged. No permission grant or unrelated allowlist repair was made; this failure remains open.

Focused runs before closeout: application recovery selection **36 passed** (6.16 s / 6.984 s wall);
runtime retry/Integration/central-mutability selection **7 passed** (1.36 s / 2.166 s wall).
The first transport selection had **11 passed, 4 failed** because registered MCP errors include a
framework prefix before the diagnostic JSON. Parsing was corrected without weakening envelope
assertions; the four registered cases then passed (4.52 s / 4.878 s wall), and all passed in closeout.

After the orphan-child extension, the exact process node was rerun:

```shell
GIT_CEILING_DIRECTORIES=/home/runner/work/owlbear/owlbear/.owlbear/scratch \
uv run --locked pytest -n 1 -m 'not api and not model and not e2e' \
  /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py::test_legacy_process_exclusion_required_after_lease \
  -q --tb=short --basetemp=/home/runner/work/owlbear/owlbear/.owlbear/scratch/d03-a-orphan
```

**4 passed**, 2.63 s / 3.532 s wall. Loader/environment and new workflow-contract recheck:
the loader node above plus
`tests/test_agent_ecosystem_validation.py::test_recovery_workflows_require_host_exclusion_not_caller_confirmation`
with the same pytest flags and `--basetemp=.../.owlbear/scratch/d03-a-recheck`:
**2 passed**, 0.96 s / 1.760 s wall.

Frontend commands ran from `/home/runner/work/owlbear/owlbear/serve/cockpit/web`:

```shell
npm test -- /home/runner/work/owlbear/owlbear/serve/cockpit/web/src/__tests__/WorkPortfolio.test.tsx
npm run build
node /home/runner/work/owlbear/owlbear/serve/cockpit/web/scripts/run-biome-check.mjs check \
  /home/runner/work/owlbear/owlbear/serve/cockpit/web/src/api/workItems.ts \
  /home/runner/work/owlbear/owlbear/serve/cockpit/web/src/components/WorkItemDetail.tsx \
  /home/runner/work/owlbear/owlbear/serve/cockpit/web/src/__tests__/WorkPortfolio.test.tsx
```

**110 tests passed** (103.99 s / 104.884 s wall); **build passed** (10.545 s wall);
**Biome passed**, three files (0.226 s wall). Initial focused test failed for absent `cross-env`
(0.141 s); `npm ci --no-audit --no-fund` restored unchanged locked dependencies (7.065 s).
These checks used available Node 22.23.2, below the manifest's Node 24 minimum; npm emitted
`EBADENGINE`. They are actual passing checks, **not pinned-Node acceptance**; external CI must cover
the pinned runtime. No browser or live host check was run.

Ruff `check` and `format --check` passed on all 16 changed Python paths (0.078 s and 0.059 s wall);
initial import/unused-argument/format findings were repaired. Coordinating session owns secret
scanning, publication, independent implementation review and final validation; no such pass is
claimed by this writer.

Final proposal-copy change was checked without repeating the closeout:

```shell
uv run --locked pytest -n 1 -m 'not api and not model and not e2e' \
  /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py::test_repair_change_diagnoses_but_exclusion_required_to_apply \
  /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py::test_repair_facade_matches_existing_repair_proposal_authority \
  '/home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_delivery_adapter.py::test_real_core_recovery_exclusion_required[proposal]' \
  '/home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_target_server.py::test_registered_recovery_exclusion_required[proposal]' \
  -q --tb=short --basetemp=/home/runner/work/owlbear/owlbear/.owlbear/scratch/d03-a-final
```

**4 passed**, 3.65 s / 4.495 s wall. Ruff check/format rechecks on the changed application and its
test passed (0.074 s / 0.055 s wall). `git diff --check` passed. Owned disposable pytest directories
were cleaned; restored dependencies/tooling remain available to the coordinating reviewer.

#### Published source review and validation

The coordinating session published the resume as
`4dff7c0421aca9b0f84330c4fc1c52689158bbb0`. Independent read-only Claude Opus 5 reviewer
`d03-a-audit` reviewed the interrupted A implementation and resumed changes, then confirmed its
consolidated verdict against that exact published source: **no blocking in-scope defects**.
The evidence-evolution finding was resolved by immutable-record adoption and monotonic verified
replay. Two later concerns were withdrawn after checking the approved A boundary: executable
public recovery is deliberately deferred, and unverifiable ongoing exclusion must fail closed.
Additional finalizer/ready restart tests cover the internal route without enabling a public one.
The reviewer did not run tests or substitute its reading for automated security checks.

Secret scanning passed across the cumulative A paths and again on the six resumed paths before
publication. `parallel_validation` ran on the published source with a **non-trivial** CodeQL
assessment. Its automated reviewer could not run because the configured model was unavailable;
the wrapper's success label is **not a review pass**. CodeQL **timed out** and explicitly prohibited
another attempt in this environment. Neither check is claimed to have passed. External verification
must cover those outstanding gates; the successful independent review does not waive them.
The final progress-only documentation commit leaves this reviewed source unchanged.

Non-blocking follow-up notes: historical exclusion identities are reverified after each restart
rather than pruned on closure; their bound matches the recovery-intent limit. E must preserve these
constraints when exposing its approved public route. No B–E implementation or live activation was
started.

### Gaps and decisions

| Gap | Available evidence / reason unrun | Owner/environment and blocking effect |
| --- | --- | --- |
| Actual host termination/exclusion integration | No such provider in inspected source; D02 host rehearsal proves dispatch only | A implements fail-closed port and controlled-process proof. Host owner must supply verifiable exact invocation/descendant closure before enabling that host's recovery. Blocks any unsupported worker release and full V10/product acceptance; does not block B–E with tested fail-closed behavior. Do not call a fixture adapter production support. |
| Unknown engine write outcomes | A's interrupted `mark-ready` reference path has exact receipt/provider readback proof; unrecorded/contradictory effects remain contained | E owns remaining approved owner paths and cumulative coverage. No generic provider retry or fabricated completion is supported. |
| Preservation policy/limits and retry defaults | Concrete proposal above, derived from programme's review-required defaults | Specification reviewer must approve before corresponding implementation; no implicit destructive/privacy permission. New policy expansion needs an explicit decision, not a larger limit or weaker classifier. |
| Offline structure is not semantic integrity | Runtime imports and automatic transaction recovery are deliberately excluded | D's output must label this limit. Unknown corruption remains diagnosed; D07 owns any approved repair. Not a blocker for a truthful read-only entry. |
| Product tests/build/static checks | A's focused Python/consumer/static proof is recorded above; unchanged frontend prior proof used Node 22 rather than pinned Node 24 | External CI owns pinned-Node and broad gates. B–E own their additional proof; no prior count is a new pass. |
| External CI at interrupted head | Coordinating session inspected implementation run `35219983240`: cancelled, zero failed jobs. Source/agent/Cockpit runs at `ec392dfa91790bd270378e550ab6ed1ca01f1959` are `action_required` with no jobs, including source run `35225758084` | Repository/integration owner must obtain completed external checks for the eventual review head. No external acceptance is inferred, and no CI policy/protection change was made. |
| Actual host workflow/stdio and live activation | Not exercised by planning or in-process adapters | D08-H / user-controlled host acceptance; no service start or activation here. |
| Repair re-review | Independent Claude Opus 5 `d03-p-prerequisite` PASS supplied by coordinating session on approved repaired plan | Prerequisite satisfied; separate user approval recorded above. |
| D03-A independent implementation review | Claude Opus 5 `d03-a-audit` found no blocking in-scope defects at `4dff7c0421aca9b0f84330c4fc1c52689158bbb0`; original evidence-evolution finding resolved | Review prerequisite is present; this is not package acceptance, merge approval or authorization to start B. |
| Automated review and CodeQL | Automated review model unavailable; CodeQL timed out at the published source and prohibited a repeat attempt here | External verification/integration owner must obtain the missing checks before package merge. No security-scan pass or waiver is inferred. |
| Existing workflow-registry test mismatch | Baseline orchestrator expected-tool set omits two already-granted D02 continuation tools | Coordinating/integration owner; not hidden by skips or modified role permissions. |

There is no new product permission request to resolve during planning: unavailable exclusion fails
closed under the already required policy. A future request to release unverifiable D02 workers,
include ambiguous/private data, reset exhausted budgets without accepted progress, or broaden
offline repair would be a genuine decision and is **not** authorized by this plan.

### D03-B partial handoff — 2026-09-18

User [comment 5723189457](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5723189457)
approved the presented plan at `43b91fdf0c5707551aaadad1b567173183174b06` for B only.
D03-A's independent current-head review is
[comment 5723179195](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5723179195).
The approved specification above is unchanged. GPT-5.6 Luna Max implemented the partial B checkpoint;
it is not phase completion, package acceptance, or permission to advance.

Published `6c08be1653061a81b34f3d60be9c74c0e873837e` adds the runtime-owned retry ledger,
application reservation/accounting integration, shared readiness budget fields and frontend labels/
rendering, with dedicated `serve/delivery/tests/test_retry_ledger.py` coverage. This checkpoint was
published to preserve work before completion of proof and review repairs.

Independent read-only Claude Opus 5 review of that exact checkpoint confirmed the initially dropped
second-episode defect is fixed and worker/finalizer outcomes now have integration. Remaining review
work at that revision includes exact reconciliation of interrupted reservations/result accounting,
removing the inference that exhaustion itself authorizes an explicit observation, generated-ID
uniqueness after a reset at a fixed clock, and preserving backoff during containment release.
The final code must be checked against these findings rather than treating this interim list as
an acceptance verdict. Ledger correctness alone is not proof of the application/worker paths.

Secret scanning passed before that publication. `parallel_validation` on `6c08be1` reported **zero
CodeQL alerts for Python and JavaScript**. Automated code review was unavailable because its
configured model was absent; its wrapper success label is not a pass. Current pre-B external
source/Cockpit/ecosystem checks were skipped; setup success is not product proof. Prior A tests are
not B tests. No live records, production exclusion integration or C–E implementation is authorized.

**Next request:** `Resume D03-B using .owlbear/research/delivery-cloud-flight-handoff.md and this PR's recorded completion blockers; stop after B.`
Recommended implementation model: **GPT-6 Astra, High**, for the unresolved cross-owner transactional
and observation-authority boundaries, followed by independent Opus 5 review. This recommendation
does not start another session, authorize C, approve a merge, waive host proof or authorize activation.
