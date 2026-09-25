# D03 — Recovery Package Plan

## Status and authority

**D03-C: resumed partial checkpoint; not accepted. C's remaining recovery/integration blockers
and external gates remain outstanding. D is not authorized.**
This is the package record required by the [cloud execution guide](delivery-cloud-flight-handoff.md).
D03-P changed only this file. The programme and shared governance remain unchanged.

### Current handoff

The current readiness repair starts at **`dbb5751`**, with source
**`6db0fec3cc15c84f36498b39813a12b5cdcda0f6`**, following the
[repair request](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5828310357).
Its bounded scope is shared readiness/acquisition finalization retry identity and
the pending accepted-repair, restart, budget and transaction-crash proof. The prior
[verification request](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5823084965)
established the findings below by inspection, not executable proof.
It preserves the partial repairs from **`9bc8cfb`**, **`d7b8369`** and review baseline
**`4ea5457`**, following the
[existing/missing implementation review](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5803071146)
and [repair request](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5809465434).
It addresses Git environment overrides before admission, durable repair-to-original-action
retry accounting, hard-death proof-store publication replay, and bounded pre-journal
staging artifacts. These repairs do not establish production custody/proof/publication
composition or whole-C resumption. The reviewed identity, admission/no-follow,
intent-publication, post-replacement replay and provenance/index boundaries remain required.
Published source checkpoint **`b6205a6`** closes post-link proof-publication replay,
recovers pending retry transactions before owner-result reconciliation, fences continuation
finalization identity, and extends early Git environment refusal. It also repairs the staging
inventory rejecting its own `intent.json`, without trusting or deleting markerless artifacts.
Final continuation source **`6db0fec`**, following **`e1f59ae`**, adds the previously missing
successful owner-settlement requirement: the exact linked repair attempt must have a durable
successful outcome before a replacement original action can resume. The binding alone is not
authority. Change/action/target/finalization identity fences and the original episode's consumed
budget remain in force. Owner-result reconciliation now inspects settled attempts as well as
pending ones, rejecting contradictory terminal non-success evidence. The application recovers
the linked original episode's finalization identity for continuation after restart.

Prior independent read-only review of **`b6205a6..6db0fec`** and the coupled binding/readiness
paths confirms that the original failed/unaccepted-binding finding is addressed. Pending,
failed, contained or contradictory repair evidence does not authorize original-action resumption.
This supersedes the stale statement that the successful-settlement gate is still unimplemented.
The reviewer did not run tests. Executable verification was blocked at that checkpoint;
neither that review nor the current bounded repair establishes whole-C acceptance.

**Bounded readiness/acquisition repair.** Both finalizer paths now derive their retry identity
through one helper, retaining current receipt, review-repair invalidation and linked original
episode semantics. Readiness no longer silently uses a `None` finalization identity when
acquisition uses the prior episode. Outcome-worker and other engine-action identity selection
remain unchanged. Projection reads repair bindings without completing pending transactions;
mutating callers retain transaction recovery by default. The successful-settlement,
Change/action/target/finalization and consumed-budget fences remain unchanged.

Prior delegated checks at **`6db0fec`**: `compileall` passed for the two changed source modules
and their two test modules using system Python **3.12.3**; `git diff --check` passed and the
checkout remained clean. These are syntax/whitespace checks, not locked-runtime test evidence.
The focused pytest command selected the unaccepted-binding, contradictory-terminal-result,
accepted-repair/budget, application restart and transaction-crash regressions in
`test_retry_ledger.py` and `test_recovery.py`. It could not start because `uv` was absent;
one bounded uv **0.12.18** installation attempt failed DNS resolution. **No pytest cases
were collected or passed.** Scoped Ruff was also blocked. `pytest`, `pydantic` and
`owlbear_delivery` were unavailable, so PR-worktree import provenance could not be verified.
The parent did not rerun delegated checks. Focused executable proof on the locked toolchain
was still required at that checkpoint; do not substitute the older totals below.

Prior delegated proof at **`b6205a6`**: **277 passed** in the focused proof/retry/workspace
selection, **101 passed** in the transaction/recovery selection, **82 passed** in
`serve/delivery/tests/test_recovery.py`, **44 passed** in the portfolio continuation/retry
selection and **4 passed** authority invariant nodes. These selections overlap; do not sum them.
The writer used locked Python **3.14.7**, uv **0.12.18**, and reported `git diff --check` clean.
The temporary uv installation was removed. The parent did not rerun delegated checks.
Older proof below remains evidence only for its named revisions.

Prior parent secret scanning passed before publication. Automated Code Review was **unavailable**
because its configured model was missing; the wrapper's success label is not review evidence.
CodeQL **timed out**; those results are not final-source validation. Source, Cockpit and Agent
ecosystem runs freshly inspected at **`6db0fec`** are **`action_required`**, not passing proof;
no approval or bypass was performed. Historical `dev` failures do not establish a failure in
this final continuation delta. No live services, records or provider effects were activated.
For this documentation-only verification update, secret scanning passed; automated Code Review
was again unavailable because its configured model could not load, and CodeQL skipped the
non-code changes. Neither result supplies final-source executable or security-scan proof.

#### Production and acceptance gaps retained by this repair

- The loader has no production trusted provenance producer; capture/restore have no
  production callers composed with exclusive application recovery custody.
- `ProofAttemptStore` persists captured observations. It does not execute maintained
  procedures, supply a production registry/factory, or detect zero-exit mutation itself.
- Successful-finalization/publication repair, including draft/readback and invalidation,
  remains unimplemented.
- Bounded retry accounting is not proof of a complete new-candidate → cumulative
  independent review → original whole-Change proof/resumption production path.
- Remaining privacy, filesystem, index and restart matrices, the conservative global
  ignored-inventory refusal, actual host exclusion and external CI/static/pinned Node
  acceptance gates remain outstanding. None authorizes D or live activation.

#### Prior provenance checkpoint

Reviewed source **`92160aa523caa2803bd841d019f5a73a92936755`** completes the bounded repair and
validation of interrupted checkpoint `78b0c16`, whose provenance/index increment starts from
`f9330ffc`. It preserves feature source `4566935` and the reviewed recovery, admission/read-boundary
and intent-publication repairs. User
[comment 5789187453](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5789187453)
requests the exact-path provenance and private-index classification obligation only. Task scope
and content hashes alone must not establish last-writer evidence or permission to discard bytes.
Classification must precede preservation writes, and unknown/private evidence stays contained.
The bounded static repair at `f9330ffc` remains prior proof, not this increment's acceptance.

| Remaining item | Meaning and next action |
| --- | --- |
| C implementation | Complete production provenance composition and the [listed C obligations](#maintained-procedure-authority-increment): exclusive recovery custody, publication repair, trusted procedure production, original-action resumption and remaining matrices. The classification boundary below is not an evidence producer or whole-C acceptance. |
| GitHub proof | Source, Cockpit and Agent ecosystem runs at source `92160aa` are `action_required`, not passing or failed product tests. Required external gates remain outstanding; do not approve obsolete runs or mark ready merely to disguise unfinished C work. |
| Independent acceptance | Narrow reviews cover individual repairs, not completed C. Complete and review C before requesting D; do not automatically advance phases. |
| Host exclusion | Actual host termination/exclusion remains a host acceptance gap, not permission to release a possibly live worker. The existing gap allocation allows B-E work with fail-closed behavior. |

Continue only the current C implementation against the approved contract. Preserve completed
repairs and tests, use focused proof, and keep phase incompleteness distinct from tool unavailability.
No merge, live activation, approval bypass, or successor-phase authorization is implied.

#### Provenance classification increment

The workspace owner now requires a configured trusted provenance provider before raw preservation.
Its default is unavailable: task admission, a digest, a diagnostic string or a `ProofAttemptStore`
observation alone grants no copying or disposal authority. Evidence binds the Change/recovery,
registered worktree, captured fingerprint, task, HEAD, complete raw index and each exact dirty
path's type/content/mode. The configured owner must independently reverify it immediately before
the first preservation write and on replay.
Useful content is retained for Builder repair; only proven disposable paths may be restored.
Foreign, ambiguous, private or stale evidence remains contained before preservation writes.

Index qualification compares parsed mode/object/path/stage entries with Git's inventory and exact
HEAD, validates the checksum and entry padding, and refuses unsupported layouts/extensions rather
than converting or refreshing the index. The entire raw index still needs privacy qualification;
ordinary maintained source filenames are not a generic privacy exemption.
Invalidated Git cache-tree nodes omit their object ID; their declared subtree counts still delimit
the complete extension. Historical receipts retain their original index-extension inspection
boundary without acquiring new capture or restoration authority.

This is a consumer boundary, not a production last-writer journal. Production producer/registration,
exclusive application custody, useful-content Builder routing, publication repair and original-action
resumption remain implementation obligations. The global ignored-inventory refusal remains
conservative and over-restrictive. No live service/state, provider effect or protection was changed.

#### Proof and limits at `92160aa`

- The delegated writer ran the two affected workspace/application test files: **604 passed**.
  This includes provenance refusal/revocation, useful versus disposable paths, index classification,
  invalidated cache-tree grammar, historical inspection and existing recovery/admission regressions.
  The provider fixtures are synthetic trusted authority, not proof of a production producer.

  ```bash
  cd /home/runner/work/owlbear/owlbear
  uv run --locked pytest \
    /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_change_workspace.py \
    /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py -q
  ```

- Writer tooling: uv `0.12.18`, locked Python `3.14.7`, Ruff `0.16.5`. Scoped Ruff comparison against
  `f9330ffc`, covering the workspace owner and the two test files above, found
  **0 increment-added diagnostics** (382 baseline, 370 candidate). Remaining
  baseline-equivalent diagnostics mean this is **not** a clean whole-file lint pass.
  Writer `git diff --check` passed. The parent did not rerun delegated checks.

  ```bash
  uv run --locked ruff check \
    /home/runner/work/owlbear/owlbear/serve/delivery/src/owlbear_delivery/change_workspace.py \
    /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_change_workspace.py \
    /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py \
    --output-format json
  ```

- Independent read-only review confirmed the exact published source and found no significant
  remaining issues in this increment. Its three findings were repaired: legacy extension inspection,
  invalidated cache-tree parsing and provider revalidation before custody. Interrupted hardlink
  cleanup still precedes strict provenance metadata checks.
- Parent validation: secret scans clean; CodeQL Python **0 alerts**. Automated Code Review was
  **unavailable** because its binary was absent, despite the wrapper reporting success. The
  independent review above is separate evidence, not a claim that the unavailable tool ran.
- Inspected source-head runs:
  [Source](https://github.com/maba-pag/owlbear/actions/runs/35915236793),
  [Cockpit](https://github.com/maba-pag/owlbear/actions/runs/35915236797) and
  [Agent ecosystem](https://github.com/maba-pag/owlbear/actions/runs/35915236776) require action.
  No approval, gate bypass, broad suite, live host check or service activation was performed.

The missing production evidence owner/registration and remaining C recovery integration are
**implementation gaps**, not unavailable-tool excuses. Continue C with independently owned
last-writer evidence and production composition; do not derive disposal authority from task scope,
caller-supplied hashes or the test provider. Keep C partial until its full contract and gates hold.

### Authority references

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
| D03-B | Source `7dd03b4de2384edfa77b2b848a784648c3fdd470`, repairing review of `fc557ff`; repair comment `5727705649`, approved specification `43b91fdf0c5707551aaadad1b567173183174b06` | Return accounting finding repaired with same-task backoff/exhaustion, replay and transaction-restart proof. Independent Claude Opus 5 repair review found no significant issues; prior cumulative proof is recorded below. | Ready for re-review, not accepted. Repair-source CodeQL timed out; automated review unavailable; external CI and host gates remain. No C authorization. |
| D03-C | Source `93e8b7062d3aaa14ee9e7fddb382ba7bab2a7bde`, following `9126efc` and `2618a45`; authorized by comment `5728172369` against plan `92e9135` | Scoped preservation and review-repair proof below; independent Claude Opus 5 narrow repair review found no significant issues. Final-source CodeQL timed out; automated reviewer unavailable. | Partial, not accepted. Provenance/classification, exclusive recovery integration, provider gating, registered proof attempts and bounded end-to-end resumption still block C completion and D. |
| D03-D | Not started | None | Offline diagnostics |
| D03-E | Not started | None | Registered/cumulative proof |

### D03-C resumed partial checkpoint — 2026-09-20

#### Review repair — 2026-09-21

User comments `5764113682` and `5765408189` authorize repairs of the D03-C reviews,
not completion of the unfinished phase or D work. The repair checkpoints `65e9846`,
`8cf34bc` and `67febdc` preserve progress; the first was explicitly unverified when
published.

- Legacy finalization reports now validate against the original canonical field set;
  current-C reports retain their existing identities. Legacy recovery intents retain
  their original bytes/IDs, and authority recapture compares every original fence
  without fabricating preservation provenance. Frozen pre-C report/intent fixtures
  cover read/replay, completed recovery, restart exclusion and in-flight recapture.
- Restoration stages privately before exposing an operation-bound worktree name.
  Durable records bind the source inode and intended bytes/type; identical foreign
  files are not accepted by name alone. Cross-filesystem staging fails closed.
  Markerless private partial artifacts are retained, ignored as authority, and not
  garbage-collected. No-effect absent-path durability walks no longer create parents.
- The writer reports 221 affected tests passing, including the earlier 11 focused
  repair cases (overlapping counts), with locked uv 0.12.16 and disposable state.
  These are worker results, not parent reruns or whole-phase proof. Independent
  Opus review found the compatible identity encoding sound. Staging review drove
  fixes for hardlink reads and progressive multi-path journal ordering.
- The `67febdc` post-replacement/private-unlink repair passed the subsequent
  read-only Luna review at PR comment `5765209697`, as did identity compatibility
  and absent-parent behavior. Its 223 earlier affected tests and 48/3 final focused
  selections overlap and remain prior worker evidence. Final-source CodeQL found
  zero Python alerts; automated review was unavailable, not passing.
- That review found one remaining interrupted-publication defect: a killed private
  operation-intent write leaves `.tmp-*` without `intent.json`, and the new scanner
  rejects the nonempty directory before retry can publish the intent. The repair
  tolerates bounded private temporary regular files without reading their contents,
  assigning them authority, or deleting them. Retry publishes the intent from current
  verified receipt/selection data; unauthorized worktree exposure remains blocked.
  Files must be single-link, owner-only regular files; at most 256 entries and 64 MiB
  total are tolerated. Symlinks, hardlinks, loose modes, unknown names and excess
  size/count remain contained.
- Repair proof: a real child SIGKILL immediately before linking `intent.json` failed
  before the fix and passes after it. Replay retains the orphan's exact bytes/inode
  and raw index; unauthorized worktree exposure is rejected before restoration.
  The writer reports **54 nonterminal-recovery cases passed in 19.76 seconds**,
  including **6 focused cases** (overlapping), plus the Git-admin-path authority
  invariant (**1 passed**). No parent reruns or whole-phase proof are claimed.
  Whitespace checks passed. Scoped Ruff still reports 373 diagnostics and two
  unformatted files; these remain explicit static-check failures, not a clean gate.
  No diagnostics were reported on added lines; no fresh baseline delta was run.
  A separate read-only Luna reviewer checked the final source/test diff against
  `67febdc`, including the artifact bounds and retention assertions, with no
  significant issues found. This is narrow repair review, not C acceptance.
  Published repair source is `4ed0be0`. Secret scans passed. Final automated
  validation declined to run because of its time limit and instructed no retry;
  no final-source CodeQL or automated-review pass is claimed. Product CI inspected
  at the baseline remains `action_required`; external and host gates remain open.

Focused commands used locked uv 0.12.16 with Python 3.14.7:

```shell
uv run --locked --python 3.14.7 pytest serve/delivery/tests/test_change_workspace.py -q -n 1 -k nonterminal_recovery -m 'not api and not model and not e2e' --tb=short
uv run --locked --python 3.14.7 pytest tests/test_delivery_worktree_authority.py::test_delivery_sources_have_no_git_admin_artifact_path -q -n 1 -m 'not api and not model and not e2e' --tb=short
```

Broader C provenance/classification, copied-index privacy qualification, application
custody integration, provider/procedure authority and original-action resumption
remain the blockers listed below. No D work or live-state migration occurred.

The user authorized C against the package plan presented at `92e9135`. Published B source and
its cumulative review plus return-accounting repair re-review are the prerequisite evidence;
the earlier table's “No C authorization” described that earlier checkpoint, not this new request.
External CI, pinned-Node and actual host gates remain outstanding and are not waived.

**Published source:** `93e8b7062d3aaa14ee9e7fddb382ba7bab2a7bde`; PR #326 targets
`dev@5ca8b6d`. This resume preserves the earlier C checkpoints through `edc2824`, including
the completed-outcome repair owner/replay, retry admission and proof-mutation consumer companions.
It changes only the workspace owner, its tests and this progress record.

The resume verified the stronger ignored-inventory guard and repaired access-time handling.
New manifests zero the legacy access-time slot; comparison ignores that slot in earlier manifests
without changing their recorded bytes. Reads no longer require `O_NOATIME`. File/index identity,
hardlink, mode/time and raw-content fences remain; the worktree root is fenced by device/inode/mode,
not directory link count, which changes during legitimate nested restoration.

Restoration now writes private immutable operation and per-path intent/result records with
independent readback and fsync before reporting success. Interruptions retain a bounded failure
record for filesystem, fence and Git failures where storage remains writable. Replay re-establishes
postimage durability, leaves the
original manifest/objects untouched, and rejects a third value, newly dirty path or changed raw
index before further restoration. This is a workspace primitive, **not** an application recovery
completion receipt or permission to release custody. Capture/restore still have no production
callers. Missing-manifest sibling captures no longer poison intact receipt lookup; malformed
present manifests still contain. Preservation Git inspections now retain ten-second deadlines
through the `--no-optional-locks` prefix, without changing mutation deadlines.

**Writer-owned proof:** disposable fixtures and
`uv run --locked pytest -q -n 1 -m 'not api and not model and not e2e'`:

- At `9126efc`, `serve/delivery/tests/test_change_workspace.py -k 'nonterminal_recovery or
  stronger_custody_guard or preservation_captures_linked_index'`: **29 passed in 6.32 seconds**.
  Includes before/after raw-object and manifest publication failure; restoration intent,
  post-effect, path-result and final-result interruptions; restart with unchanged paths, changed
  bytes, a new untracked path or same-size raw-index mutation; directory fsync failure; replay
  receipt immutability and owner-only permissions.
- `test_recovery.py::test_completed_outcome_repair_replays_with_retry_authority_and_preserves_result`,
  the two existing quarantine replay/changed-byte nodes, and
  `tests/test_delivery_worktree_authority.py::test_delivery_sources_have_no_git_admin_artifact_path`:
  **4 passed in 2.54 seconds**. These are direct-consumer/authority proof, not completed C integration.
- At `2618a45`, two timeout nodes: **11 passed in 0.85 seconds**; nine failed before repair.
- At `93e8b7`, selections `restores_nested_directory_without_losing_root_fence`,
  `receipt_lookup_contains_incomplete_sibling`, `git_failure_retains_failure_journal`,
  `still_rejects_file_and_index_hardlinks` and `capture_failure_keeps_bytes_and_replays`:
  **12 passed in 2.76 seconds**. Includes nested restoration/replay, root substitution/mode drift,
  file/index hardlinks, orphan versus malformed manifest, Git failure/timeout journaling and
  capture-replay faults. Four reproductions failed before these repairs.
- Four atime/platform reproductions failed before the first repair. These selections overlap;
  they are not an aggregate count or whole-phase proof. Unchanged broad suites were not rerun.
- Test-file Ruff check/format and whitespace checks passed. Source Ruff still fails:
  **267 diagnostics versus 275 at `edc2824`**, with no new code/message diagnostics reported.
  Existing source-format failures remain; no broad autofix or suppression was applied.

**Prior evidence, not rerun:** at `4baee52`, recovery/application/runtime selections reported
50/407/66 passes and four authority checks, with independent Opus review of the earlier repairs.
The `71330f3` consumer increment reported 112 Cockpit tests, build, scoped Biome/Ruff and MCP/parity
checks passing with independent review. Two unrelated `.vscode` Biome failures remain.
The locked environment was restored with advisory-checked uv 0.12.16; manifests were unchanged.

**Review and validation:** independent Claude Opus 5 reviewed cumulative C through `edc2824`,
the `9126efc` restoration checkpoint and `2618a45` deadline fix. Findings drove the root-fence,
orphan-lookup and Git-failure repairs in `93e8b7`. A fresh independent Claude Opus 5 review of
`2618a45..93e8b7` found no significant issues, confirming all three fixes and retained root,
file/index hardlink, malformed-manifest and exception-propagation fences. This is a narrow repair
verdict, not acceptance or a fresh cumulative review of all C.
Secret scans passed before each source publication. CodeQL found zero Python alerts at `9126efc`
and `2618a45`, but **timed out at final source `93e8b7`** and instructed no retry. The automated
reviewer was unavailable because its configured model was absent; it is not a successful review.
GitHub source/Cockpit/ecosystem/dependency/setup runs inspected at `93e8b7` were `action_required`,
not passing. Final-source external CI, pinned-Node and actual host gates remain outstanding.

### D03-C admission-boundary resume — 2026-09-21

The current repair starts at `eca439b`, following interrupted admission repairs
`9196317`/`6cdd129`, partial admission checkpoint `c2bca75`, and the already-published
`dev` merge `416f86c`. The PR comparison base is
`dev@d7d5d2d`. Preserve the merged tooling changes and the reviewed restoration
repairs; neither is admission proof. This repair is limited to completing and
checking the admission boundary, not the remaining C integration below.
The repair review identified missing replay admission and legacy dirty-completion
guards, plus content fingerprinting before path admission. These must be resolved
without changing the index privacy policy or ignored-file containment; an initial
draft's wider policy changes are not acceptance evidence for this slice.
Inspection of `eca439b` also identified an ignored-status shortcut that treats any
ordinary dirty entry as ignored content, bypassing path/scope rechecks and content
fingerprinting. Pending legacy recovery must reject ignored-only dirt, while replay
of an already completed receipt must not depend on later workspace cleanliness.

Admission checkpoint source: `5c8e0e0`, following checkpoints `970368d` and `b2da6be`.
The repair distinguishes actual `!!` ignored entries
from ordinary dirty paths, include admitted untracked bytes in the post-admission
fingerprint, and reject reviewed file/directory scope substitution. Metadata-only
admission does not use the content diff; raw reads follow exact path/scope checks,
and Git content reads use only literal admitted pathspecs. Completed pre-C/A5
receipts replay before pending-workspace cleanliness checks and exclusion-cache
clearing. Pending legacy/no-admission recovery rejects ignored-only dirt as well
as ordinary dirty paths. Admitted capture with any true ignored inventory now
fails closed before content reads, including active-claim/no-current-writer
recovery; it cannot return a weak status-only authority fingerprint.
Historical identities and old preservation containment remain unchanged.

The sole writer reported 163 workspace tests and 83 focused admission/replay tests
passing, plus the Git-admin-path invariant; selections overlap and must not be
summed. Both larger runs used `-q -n 1 -m 'not api and not model and not e2e'`;
the 83-case run selected recovery, portfolio-application and workspace tests with
`-k 'admission or admitted or legacy_incomplete or a5 or fingerprint or nonterminal_recovery'`.
These extend earlier 80/154 and 82-pass checkpoints, not independent parent
reruns. On published `5c8e0e0`, the writer additionally reported **8 passing**
blocking cases using `uv run --locked pytest -q -n 1` with:

- `test_recovery_workspace_rejects_ignored_inventory_before_admission_fingerprint`
  in `test_change_workspace.py`;
- `test_legacy_incomplete_intent_completes_against_current_provenance` and
  `test_a5_incomplete_intent_completes_against_current_provenance` in `test_recovery.py`.

The separate Git-admin-path authority invariant passed (**1**), as did
`git diff --check`. Tests used Python 3.14.7 and synthetic disposable state.
The independent read-only reviewer covered admission changes since `a5e271b`,
excluding merged tooling and the broader C obligations below, and reported no
remaining actionable findings after inspecting the final fail-closed/replay diff.
Its test evidence is writer-reported, not an independent test run.

The subsequent read-only review of `a5e271b..06bb47a` identified two remaining
pre-read boundary defects, superseding the earlier clean admission verdict:
directory-scope admission checked only the scope root, allowing an intermediate
symlink below it to redirect the new raw fingerprint read outside the worktree;
unsupported dirty-path spellings were rejected by intent validation only after
content fingerprinting. The repair requested in PR comment `5782447782` is limited
to these findings and focused regressions. Historical replay/identity compatibility
had no actionable review findings. The reviewed intent-publication scanner and
whole-index privacy rules must remain unchanged.

Follow-up repair source **`a292038`**, following `8ad62e6`, shares canonical path
validation between admission and intent validation, checks the complete admitted
inventory before Git content fingerprinting, and uses descriptor-relative no-follow
traversal for raw worktree reads. Directory identities are checked across the read;
symlink leaf text and absent paths remain supported without following targets or
creating directories. Focused regressions cover intermediate symlinks, unsupported
spellings, ordinary nested/deleted/symlink leaf states and ancestor substitution.
Independent review found two descriptor cleanup gaps during implementation; both
were repaired with descriptor-tracking tests. Final read-only review of the repair
against `06bb47a` found no significant issues. This is not whole-C acceptance.

**Follow-up proof:** the sole source/test writer used Python 3.14.7 and uv 0.12.16
with `uv run --locked pytest -q ... -n1` and synthetic disposable state:

- Scoped recovery regression before the last helper/cleanup refinements: **84 passed**.
- Final workspace impacted selection: **9 passed**; admission/legacy selection:
  **15 passed**. The latter used `serve/delivery/tests/test_recovery.py` with
  `-k 'legacy_recovery_fixture or a5_recovery_fixture or noncanonical or recovery_intent_identity_survives_admitted_authority_fields'`.
- After the final successor-descriptor cleanup, `serve/delivery/tests/test_change_workspace.py`
  with `-k 'closes_successor_on_identity_mismatch or closes_parent_on_missing_intermediate or reader_fences_ancestor_substitution or recovery_workspace_reads_supported or recovery_workspace_rejects_intermediate_symlink_before_git_fingerprint'`:
  **7 passed**.
- `tests/test_delivery_worktree_authority.py -k git_admin`: **2 passed**, including
  the source invariant and its forbidden-artifact fixture test.

Selections overlap; counts are not additive or parent reruns. The writer reported
staged/unstaged fingerprints remain distinct and clean fingerprints stable.
Scoped Ruff remains non-clean (**390 diagnostics versus 399 at `06bb47a`**), with
no new diagnostics reported; `git diff --check` passed. No format check was run.
Parent source inspection confirmed historical encoding/replay, the intent-publication
scanner and index privacy validators are unchanged. Secret scans found no secrets.
CodeQL on final source `a292038` found **0 Python alerts**; automated review could
not load its configured model and is not a passing review. Current-head product CI
at the repair baseline `06bb47a` required action; final external CI, static, pinned-Node
and actual-host gates remain unproved. No live state/services, provider mutations,
whole-suite or MegaLinter run was used.

Parent validation on committed `5c8e0e0`: secret scans found no secrets; CodeQL
found **0 Python alerts**. Automated code review was unavailable because its model
was missing from the registry; the tool's success label is not review evidence.
Earlier Ruff checks were reported non-clean, but exact diagnostics were not retained;
no passing final Ruff/format gate is claimed. The whole suite, MegaLinter, live
services/state and provider mutations were not run. Earlier branch CI at `eca439b`
required action; final-source external
CI, pinned-Node and actual host gates remain unproved. None of this bounded proof
establishes whole-C acceptance.

User comment `5766196814` resumes C from `a5e271b`, preserving the independently
reviewed intent-publication repair (`5765655406`). The next bounded slice is a
necessary pre-copy admission gate: bind the active Builder task and its definition
digest to explicit relative paths, and reject paths outside that authority before
copying. Existing persisted recovery identities and clean A recovery must remain
compatible.

Compatibility does not invent missing admission authority: older dirty pending
recoveries and primitive preservation receipts without admitted paths are contained,
not silently upgraded. This bounded slice supports canonical exact-file scopes and
existing directory scopes through component-boundary containment, persisting only
the exact observed dirty paths. Glob, descriptive and noncanonical scopes remain
unsupported for dirty admission. That restriction must not block clean A recovery.

Admitted scope is **not** last-write evidence, privacy clearance or proof that
bytes are disposable. This slice does not authorize automatic restoration merely
because a path belongs to a task. Whole-index privacy qualification, recorded
procedure provenance, exclusive application custody and original-action resumption
remain required. No filename exception or relaxed private-content screening is
authorized by this resume.

Implementation adds engine-derived task ID/digest and exact admitted scope/path
fields to recovery intents; preservation receipts already bind that intent by its
identity, so their schema and digest remain unchanged. Capture rejects unadmitted
dirty paths before reading their raw contents or publishing preservation objects;
replay checks the same recorded admission. Existing provenance producer values
remain unchanged. Historical pre-C and `a5e271b` intent encodings retain their
identities; only persisted-old to current recapture may omit newly introduced
fields, without ignoring older authority facts.

### Maintained-procedure authority increment

Published source and focused tests: **`4566935`**. C remains partial; this is not phase acceptance.

User [comment 5784139431](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5784139431)
resumes C from `e78f6f7`. The bounded increment adds local storage for maintained-procedure
observations and a fail-closed application consumer. Preserve `a292038`'s read boundaries,
historical identity/replay compatibility and the reviewed interrupted intent-publication repair.
Diagnostic submissions alone must not manufacture procedure-execution authority. The heterogeneous
maintained-check workflow remains supported; no arbitrary shell runner or mandatory proof profile
is authorized.

`ProofAttemptStore` records already-captured observations, not procedure execution. Its read-only
callback must not run a check; no exactly-once execution or durable pre-execution intent is supplied
by this storage seam. The immutable record binds Change/attempt, maintained registration,
contract/frontier, candidate/reviewed heads, before/after fingerprints and changed paths.
Proof-procedure repair requires matching owner evidence through an application-composed store;
ordinary diagnostic reporting is unchanged. Production composition remains unavailable until a
trusted maintained-procedure observer exists. No MCP request can register a procedure or supply
that dependency.

The sole source/test writer reports **32 focused tests passed**, including **2 overlapping
transaction-interruption/restart cases** after first publication and before manifest cleanup.
These use injected transaction failures, not process death. Replays retain the exact observation
without invoking its read callback again. Coverage also includes wrong Change/basis, unconfigured
owner rejection, registration rotation, encoded-size rejection and the frozen historical report.
The parent did not rerun the writer's tests.

Writer tooling: uv 0.12.16 and Python 3.14.7. Reproducible focused selection:

```bash
uv run --locked pytest \
  /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_finalization_reports.py \
  /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py \
  -q -n 1 -k 'proof_attempt or proof_procedure_repair or finalization_report' \
  -m 'not api and not model and not e2e'
```

The 32-case run took 3.61 seconds. The overlapping 2-case run used only
`/home/runner/work/owlbear/owlbear/serve/delivery/tests/test_finalization_reports.py`
with `-k 'proof_attempt_store_recovers_interrupted_publication'` and the same other pytest
flags; it took 0.97 seconds. Disposable test/cache/tool directories were removed.

Proof-owned Ruff checks passed at this checkpoint. The four reported application Ruff findings
and legacy-report formatting failure are resolved by the bounded repair in
[Current handoff](#current-handoff). Independent
read-only review found no significant issues after the exact-basis, encoded-size and historical
registration corrections. Final-source automated validation declined to run because its circuit
breaker had tripped after two timeouts and instructed no retry. No final-source CodeQL or automated
review pass is claimed. Secret scans passed. No authority invariant,
full suite, live service/state or provider mutation was run for this slice; broader C and external
gates remain open. This is not C acceptance.

**C completion blockers (also block D):**

- Exact-path ownership/provenance and disposable/useful/foreign classification before copying.
  Independent review also found whole-index substring screening rejects ordinary tracked names
  such as `custom-tokens.css` and password-component source, blocking capture on this repository.
  Qualify the entire copied index through evidence-backed privacy/provenance policy; do not merely
  exempt names or skip screening. Global ignored-inventory rejection remains over-restrictive.
- Integrate exclusive application recovery custody and primitive receipts with the original action;
  these journals alone are neither recovery completion authority nor a resumption gate.
- Successful-finalization/publication repair branch with draft/readback gating.
- Trusted maintained-procedure observation/registration composition and durable execution boundaries,
  not caller-asserted fingerprints. The local observation store and consumer guard alone do not
  establish zero-exit mutation detection, producer provenance or V08 resumption.
- Builder repair → new candidate → fresh cumulative independent review → original whole-Change
  check/resumption; preserve the original failure budget and historical downstream receipts.
- Complete remaining binary/deletion/rename/filter, private/staged/foreign, split/sparse/lock
  and restart matrices. Current focused fixtures do not establish the whole supported surface.
- Repeated per-effect inventory/index scans have bounded but potentially high cost. Do not hoist
  away the approved per-effect drift checks merely to improve runtime.

No public recovery API, live record, provider mutation, A exclusion rule or B retry budget was
introduced or relaxed. Do not relabel unfinished C work as E. C is partial; D has not started.

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

**Prior B integration gaps / review boundary:** the four blockers below were outstanding at
`3864baf`. The current resume candidate addresses them through exact owner-result reconciliation,
legacy failure import and shared automatic/explicit observation accounting, as recorded below.
Reservations and custody publication remain separate; missing owner evidence never refunds a
reservation. This is not permission to start E, reinterpret the approved contract, or enable live services. Independent
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

The prior checkpoint left these concrete obligations, addressed by the current resume below:

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

These were **B completion blockers**, not presumed safe containment or work reassigned to E.
The integration owner must assess their implementation and proof, not repaired findings alone.
No source changes followed that exact-head review in its session; the later candidate below requires new review.

### D03-B current handoff — resume comment 5726865466

Based on checkout `3e2932cfed8f41e441671eaa1ce4188e0ec89913` (source `3864baf`), stopping after B.
Published source: `f119cd60595905e18a3b6e8d1611442d754270dd`, then final repair
`a2006e320a502c55234030e988520c0be1005093`. No approved contract changed.

- **Owner/accounting boundary:** accepted Planner/Builder transitions and finalization publish an
  immutable attempt-bound result participant in their existing authority transaction. Application
  restart and continuation reconcile these records, original engine intent/results, finalizer
  failure reports and completion-bound attempt results without original caller replay. Existing Builder
  claim receipts and finalization receipts also reconcile without the new companion; mismatched or
  absent evidence does not. Startup skips busy Changes rather than waiting on their execution locks.
  Reservations without
  exact outcome evidence stay consumed; there is no speculative refund or custody release.
- **Legacy allowance:** nonzero binding failure counts are imported at restart and before clearing,
  resolving, returning, administratively resetting or accepting binding authority, as well as before
  dispatch. Existing issued claims are accounted from runtime identity, not granted another dispatch.
  An existing unreset ledger uses an idempotent imported-count projection. Import conservatively
  starts a two-second backoff where legacy failure time is unavailable; three failures exhaust.
  Non-accepted block clearing, blocking, return and administrative reset retain unimported counters.
  Refused legacy acquisition reports the shared budget/backoff reason, not a failed worker activation.
- **Automatic observations:** background reconciliation and engine continuation use the same semantic
  ledger. Background merged readback uses its single observed snapshot, not a second unbudgeted read.
  Awaiting-merge readiness uses cached evidence only; ledger reads do not recover transactions.
- **Explicit later observation:** the existing registered `observe_acceptance` operation and HTTP
  acceptance-observe route distinguish an explicit request from automatic continuation/background
  work. After three automatic observations they permit one later read, with no reset on waiting,
  no exhaustion-derived automatic permission and no new approval flag. Real-core MCP/HTTP tests cover it.

Cloud proof used pinned **CPython 3.14.7**, current locked dependencies and uv **0.12.16** (restored
after `uv: command not found`; advisory check clean). No dependency manifests changed. All pytest
commands used `uv run --locked pytest`, `-q -n 1 -m 'not api and not model and not e2e'`, and
repository-local `--basetemp=.owlbear/scratch/d03-b-pytest`.

- First discriminating legacy ledger selection: **4 passed, 0.92s**. Bounded closeout:
  **111 passed, 26.64s**, including registered consumers, central mutation and TypeScript parity.
  It covers three-point Planner/finalizer transaction crashes, accepted Builder transaction versus
  pre-acceptance workspace interruption, missing owner reservations, exact historical receipt matching,
  mixed automatic/background budgets, provider evidence/backoff, and explicit later observation.
  Two existing acceptance scenarios now advance their fake clocks through the enforced backoff;
  provider/custody assertions remain intact. Intermediate fixture failures were repaired and rerun.
- Scoped `ruff check` and `ruff format --check` passed for all **8 changed Python files**.
  One existing Starlette/AnyIO deprecation warning remains. No frontend source/dependency change:
  prior frontend evidence is not rerun or upgraded to pinned-Node acceptance.
- The subsequent pre-mutation legacy-import refinement is production code, not merely retained
  counters: tests prove import before block clearing and before accepted advancement erases legacy
  fields, including crash/restart of an already-issued legacy claim. Real registered MCP/HTTP
  operations cover backoff and one later read, then fresh applications/clients cannot read again.
  The real HTTP polling route also remains bounded across repeated polls and restart. These nodes
  passed **11 tests, 7.05s**. Impacted ledger/application closeout then passed **54 tests, 8.79s**
  with `-k 'legacy or retry or planner_accepted or submit_result_promotes or continuation_finalization_replays_atomic or existing_builder_receipt or existing_finalization_receipt or block_accounting or worker_budget_survives or worker_and_finalizer_reservations'`;
  all eight Python files passed Ruff check/format again. The 111-test run is the preceding bounded
  closeout, supplemented by these changed-path checks, not a rerun on this final refinement.
- Final exact-isolation check: completion publishes its attempt result in the completion transaction;
  restart does not reset other episodes merely because head/finalization match. A different-target
  pending episode stays consumed while the completed observation reconciles without caller replay.
  The application acceptance selection plus central-mutability node passed **28 tests, 15.39s**;
  eight-file Ruff check/format passed again.
- Review follow-up: legacy import now retains an existing stop/containment and later backoff,
  preserves its failure timestamp and rejects incompatible failure classes. Targeted ledger/legacy
  and owner-restart proof passed **29 tests, 5.20s**; both changed files passed Ruff check/format.
  The suggested missed-recovery gaps do not apply to this candidate: runtime mutation entry calls
  `_read()` (transaction recovery), and startup calls `runtime.bindings()` through legacy import
  before scanning owner results. Engine/direct/background target identity uses the same
  `observed_target_head()` owner; provider failure codes are `StrEnum`.
- **D03-B repair finding → fix → proof (`7dd03b4`, comment `5727705649`):** the subsequent
  cumulative review of `fc557ff` found that `ReturnDelivery`
  previously cleared Builder custody without an owner-result participant or application failure
  accounting, leaving the consumed attempt `reserved` across return → same-task replan. The
  existing transaction now records nonaccepted `worker-returned` evidence and the application
  records the matching failure; no refund, recovery release, exclusion weakening or C behavior
  changed. The pre-fix application reproduction left the Builder episode unresolved; current
  proof is **10 passed** focused application accounting/replan/replay cases, **6 passed** runtime
  Return/Block neighbor cases, **9 passed** ledger/recovery containment cases, and **3 passed**
  owner-transaction crash/restart cases (`before-publication`, `after-first-publication`,
  `before-manifest-cleanup`). Scoped Ruff check and format check pass for all 3 changed Python
  files. Counts are separate selections and may overlap; they are not a whole-phase rerun.

Repair environment: Python **3.14.7**, advisory-checked locked uv **0.12.15**, restored at
`.owlbear/scratch/d03-repair-tools/bin/uv` because `uv` was absent from PATH.
No dependency manifest/lock, frontend, service or live state changed. The regression reproduced
with the production repair reverted: restart left `last_status="reserved"` and no outcome.
The restored repair passed the following focused commands, with `TERM=xterm` and the restored
tool directory on PATH:

```sh
uv run --locked pytest serve/delivery/tests/test_portfolio_application.py -q -n1 -m 'not api and not model and not e2e' --tb=short -k 'return_accounting or returned_builder_replan or return_owner_result or block_accounting or planner_accepted_retry or acceptance_retry_budget'
uv run --locked pytest serve/delivery/tests/test_delivery_runtime.py -q -n1 -m 'not api and not model and not e2e' --tb=short -k 'implementation_nonadvance or dirty_implementation_retry or repeated_retry_exclusion_required or clean_implementation_retry_exclusion_required'
uv run --locked pytest serve/delivery/tests/test_retry_ledger.py serve/delivery/tests/test_recovery.py -q -n1 -m 'not api and not model and not e2e' --tb=short -k 'duplicate_reservation or unresolved_reservation or legacy_failures or finalizer_recovery_reconciles_interrupted_report_accounting or evidence_owner_failure_and_forged_completed_receipt_never_release'
uv run --locked pytest serve/delivery/tests/test_portfolio_application.py -q -n1 -m 'not api and not model and not e2e' --tb=short -k test_return_owner_result_reconciles_after_transaction_restart
uv run --locked pytest tests/test_delivery_worktree_authority.py::test_runtime_frontier_writers_use_the_central_mutability_policy -q -n1 -m 'not api and not model and not e2e' --tb=short
```

The final mandatory central-mutability node passed **1 test in 2.15s** on unchanged `7dd03b4`.
Independent Claude Opus 5 `d03-b-return-review` reviewed the repair diff from `fc557ff`
(the source published as `7dd03b4`): **no significant issues found**. It traced consumed-attempt
idempotency, atomic nonaccepted evidence, restart without caller replay, same-task budget isolation,
and unchanged advance/block/exclusion behavior. It ran no tests. This scoped repair review does not
replace the earlier cumulative review or confer phase acceptance.
Secret scanning passed before publication. Repair-source CodeQL **timed out** and prohibited a
repeat; automated review was unavailable because its configured model was absent. Neither is a pass.
External source/Cockpit/dependency checks at the inspected baseline remained `action_required`.
Final-source security validation, required CI, pinned-Node and host gates remain with their owners;
no gate is waived and C was not started.

Exact bounded-closeout pytest selection (the restored uv executable was
`.owlbear/scratch/d03-b-tools/bin/uv`; `TMPDIR` pointed to that repository-local directory):

```sh
uv run --locked pytest \
  serve/delivery/tests/test_retry_ledger.py \
  serve/delivery/tests/test_portfolio_application.py \
  serve/delivery/tests/test_delivery_runtime.py \
  serve/delivery-mcp/tests/test_target_server.py \
  tests/test_cockpit_work_items.py \
  tests/test_delivery_worktree_authority.py::test_runtime_frontier_writers_use_the_central_mutability_policy \
  tests/test_cockpit_boundary.py::test_delivery_readiness_reason_typescript_parity \
  -q -n 1 \
  -k 'retry or acceptance or legacy_budget or planner_accepted or existing_builder_receipt or existing_finalization_receipt or worker_and_finalizer_reservations or engine_result_transaction or engine_executor_excludes or continuation_finalization_replays_atomic or submit_result_promotes or continuation_plans_builds or block_accounting or checkpoint_failure_metadata or requestless_unblock or administrative_move or implementation_block or central_mutability_policy or typescript_parity' \
  -m 'not api and not model and not e2e' --basetemp=.owlbear/scratch/d03-b-pytest
```

All four listed completion blockers now have source and focused cloud proof. Counts above overlap
and must not be summed; later focused runs validate refinements to the earlier closeout.
Independent read-only Claude Opus 5 (`d03-b-completion-review`) reviewed `f119cd6` and rechecked
`a2006e3`: no open findings. The legacy containment/backoff finding was fixed and tested;
suspected transaction-recovery and worker-key divergence findings were withdrawn after source tracing.
The reviewer ran no tests; execution evidence belongs to the implementation worker.

Secret scans passed before both source publications. CodeQL reported **zero Python alerts at
`f119cd6`**; its rerun on final source `a2006e3` **timed out**, with a tool instruction not to retry.
That earlier scan is not a final-source pass. Automated review was unavailable in both calls because
its configured model was absent, despite the wrapper's success label. The integration owner must
obtain final-source security review and required external checks before package merge; none is waived.
At session inspection, checkpoint `3e2932c` source/ecosystem/dependency/setup workflows were
`action_required`, not passing. Historical `dev` dependency failure `33903819070` was unrelated.
Pinned-Node acceptance and actual host exclusion/live activation remain external gates.

Status: **ready for review**, not phase acceptance, merge permission or authorization for C.
No C/D/E implementation, full suite, MegaLinter, live service/state or real-provider mutation occurred.

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

### D03-B historical partial checkpoint — 2026-09-18

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

**Next request:** `Resume D03-C using .owlbear/research/delivery-cloud-flight-handoff.md and this PR's recorded completion blockers; stop after C.`
Recommended implementation model: **GPT-6 Astra, High**, for the remaining cross-owner provenance,
custody and resumption boundaries, followed by independent Claude Opus 5 review. This recommendation
does not dispatch another session, authorize D, approve a merge, waive host proof or authorize activation.
