# Delivery implementation audit and improvement plan

**Status:** Active improvement plan. This section supersedes the retired Kanban decomposition
proposal after a source-level review of the current `owlbear-delivery` and `owlbear-delivery-mcp`
implementations on 2026-08-07.

## Why the old proposal no longer applies directly

The retired proposal correctly identified that one 2,738-line `KanbanEngine` and one 1,221-line
`AgentView` concentrated too many responsibilities. Those classes no longer exist. The current
implementation has explicit stores, transactions, runtimes, application orchestration, workspace
coordination, and MCP transport modules.

The historical lesson still applies, but file length is not sufficient evidence for another split.
The current large classes hide real state-machine and Git coordination complexity. Splitting them
into mixins or forwarding-only managers would increase the effective interface without improving
ownership. The more consequential current problems are lifecycle correctness and the coexistence of
active schema-v2 Delivery with retained target-v1 cutover and execution contracts.

## Audit method and baseline

The assessment was challenged independently per proposed measure, then reconciled against direct
source reads, current artifacts, and focused test execution. Reviewer conclusions were not accepted
when their stated interleaving or filesystem guarantee did not match the implementation.

Confidence uses this calibration: `>=0.95` means directly confirmed by exhaustive repository-local
references or a concrete current behavior path; `0.80-0.94` means strongly supported but dependent
on an unresolved design or consumer boundary; `<0.80` means materially dependent on product choice
or external-workspace evidence.

Baseline on 2026-08-07:

- `uv run pytest serve/delivery/tests serve/delivery-mcp/tests -q`: **246 passed** in 28.99 seconds.
- The test baseline is green; the findings below are architectural and latent-behavior findings, not
  explanations for an existing red suite.
- Current source hotspots:

| Class or file | Measured size | Assessment |
| --- | ---: | --- |
| `PortfolioApplication` | 865 class lines, 56 methods | Large, but its acquisition, recovery, projection, and Integration orchestration are real responsibilities. Do not split by line count alone. |
| `ChangeWorkspaceManager` | 805 class lines, 49 methods | Large, but Git/worktree invariants span creation, recovery, proof, and Integration. Remove dead paths before considering extraction. |
| `DeliveryRuntime` | 699 class lines, 35 methods | Cohesive owner of one schema-v2 frontier and its mechanical transitions. Keep intact unless a behavior-driven boundary emerges. |
| `TargetRuntime` | 642 class lines inside a 1,203-line module | Retained target-v1 execution generation, not the active schema-v2 runtime. Its disposition is a cutover/evidence decision, not a decomposition task. |
| `TargetMCPAdapter` | 266 class lines, 35 methods | Explicit transport contract. Repetition preserves typed schemas, tool documentation, annotations, and error mapping. |

Current startup verification measurement for this workspace:

- Retired snapshots: 2,430 files and 38,251,513 bytes.
- `authorize_target_mutation(...)`: approximately 70 ms median after warm-up.
- The checked-out `.owlbear/target-cutover.json` is mode `0644`. Independently of that working-tree
  mode, `_publish_file(..., immutable=True)` publishes by exclusive hard link, which is atomic and
  no-overwrite but does **not** prevent later writes by a user who owns the file.

The timing is evidence about this workspace only. It is not, by itself, a reason to weaken startup
integrity.

## Architecture generations currently present

| Generation | Current role | Main modules |
| --- | --- | --- |
| Active schema-v2 Delivery | Authored package compilation, source-bound admission, outcome stages, claims, task results, Integration, and completed history | `delivery_runtime.py`, `target_contract.py`, `delivery_admission.py`, `portfolio_application.py` |
| Retained target-v1 execution | Job/attempt/review/receipt runtime and semantic authority used by cutover/finalizer and retained public evidence contracts | `target_runtime.py`, `target_authority.py`, the `TargetAuthorityRegistry` half of `target_admission.py` |
| One-time cutover and snapshot retention | Bootstrap source retirement, snapshot verification, receipt publication, and mutation gate | `target_cutover.py`, `snapshot.py`, `setup/finalize.py` |
| Transport | Process configuration/lifespan and explicit MCP adaptation | `delivery-mcp/server.py`, `delivery-mcp/target_server.py`, `delivery-mcp/target_models.py` |

The active and retained generations are isolated at the admission-module boundary. Current
source-bound admission lives in `delivery_admission.py`; `target_admission.py` contains only the
retained Target-era registry and models. The package root still exports both generations while the
Target-era public surface remains supported.

## Reconciliation of the initial assessment

| Initial claim | Validated disposition | Corrected conclusion |
| --- | --- | --- |
| Split `DeliveryRuntime` because it is large | Rejected | The class has one state owner and one transition vocabulary. Extracting claim/binding helpers would mostly expose internal invariants. |
| Split `PortfolioApplication` and `ChangeWorkspaceManager` now | Deferred | First remove obsolete paths and fix live lifecycle defects. Reapply the module deletion test afterward. |
| Merge MCP `server.py` and `target_server.py` | Rejected | `server.py` owns environment resolution, authorization, composition, and lifespan. `target_server.py` owns the typed adapter, error translation, and registration. The provider indirection is required because tools register before lifespan construction. |
| Replace explicit MCP methods with generated wrappers | Rejected | The apparent repetition carries distinct input schemas, output handling, annotations, docstrings, and an auditable allow-list. More metaprogramming would reduce clarity. |
| Delete all target-v1 runtime code immediately | Narrowed | Some old Integration code is dead now. `TargetRuntime` and `TargetAuthorityRegistry` still participate in cutover/finalizer and documented evidence contracts; retire them only through an explicit cutover disposition. |
| Rewrite work projection directly onto schema v2 immediately | Narrowed | A direct native projector is probably the right end state, but first fix the current Design-stage defect and decide which target-v1-only semantics remain product requirements. |
| Add a frontier snapshot API to fix an acquisition race | Rejected as stated | The proposed publish/acquire interleaving ignored active-claim preconditions. Exact-byte OCC already prevents lost updates. A different, confirmed acquisition defect exists: automatic recovery can revoke live claims. |
| Remove Assembly immediately | Decision required | Assembly is unreachable through current compilation and incomplete at MCP, but is intentionally represented in runtime and UI contracts. Choose complete, remove, or explicitly defer it; do not leave it accidentally half-live. |
| Broadly rename all `target_*` modules | Rejected for now | `target` still has a real cutover/activation meaning. Rename only symbols proven stale after target-v1 retirement; do not rename serialized artifact paths for aesthetics. |

## Priority 0 — prevent acquisition from revoking live work

**Finding: confirmed live lifecycle defect. Confidence: 0.98.**

`PortfolioApplication.acquire_frontier_work()` takes the acquisition lock and immediately calls
`_recover_active_claims()`. `_recover_claim()` unconditionally removes Planning and Assembly claims.
It also resets a clean Build claim when writer and Git identities match. None of these paths proves
that the recorded worker has stopped. `DeliveryActiveClaim.process_id` has no lease, heartbeat, or
OS-liveness semantics.

A second acquisition call therefore serializes behind the first call, observes its active claim,
removes or resets it, and may issue a replacement claim while the first worker still runs. The old
worker will eventually fail exact-claim validation, but it can perform expensive work first. A Build
worker can be reset while still alive but before it has dirtied the worktree, after which the old and
new workers can touch the same warm worktree under different claim expectations.

The current regression
`test_acquisition_recovers_interrupted_planning_claim_before_relaunch` proves this behavior in one
application instance; it does not prove that interruption occurred.

**Recommended measure:** remove blanket recovery from `acquire_frontier_work()`. Recovery must be an
explicit exact-claim operation performed only after the owning invocation is known to have failed.
Keep `recover_claim` as the bounded recovery surface, and have orchestration call it with the exact
attempt and claim after a failed dispatch or worker invocation. Acquisition should report occupied
claims and select only genuinely unclaimed work.

**Pros:**

- Prevents claim stealing across repeated or multi-process MCP acquisition calls.
- Matches the existing exact-claim recovery tool and fail-closed claim identity model.
- Avoids leases or age heuristics that cannot prove process death.
- Makes acquisition idempotence and recovery authority easier to explain.

**Cons:**

- A crashed worker leaves work occupied until orchestration or an operator explicitly recovers it.
- A dead Orchestrator chat can leave a claim occupied indefinitely; Cockpit/operator recovery must
  remain discoverable and usable.
- Orchestration must retain the failed invocation's attempt and claim identity.
- Recovery UI and diagnostics become operationally important rather than a fallback.
- `DeliveryAcquisitionResult.recoveries` no longer carries automatic recovery results and must be
  removed or explicitly retained as an always-empty compatibility-free contract.

**Risk:** Medium. Changing recovery timing can strand claims if orchestration does not forward worker
failure correctly. The current behavior is higher risk because it can revoke healthy work.

**Prerequisites:**

1. Trace every `acquire_frontier_work` caller and document one acquisition owner per invocation.
2. Update `share/skills/w-orchestration/SKILL.md` and `share/agents/orchestrator.agent.md`: acquisition
  is no longer the source of interrupted-claim recoveries; failed dispatch and malformed worker
  results still route to exact `recover_claim`.
3. Define what Cockpit may do: inspect and explicitly confirm lost claims, but never infer death from
   age alone.
4. Decide the public disposition of `DeliveryAcquisitionResult.recoveries` and update the MCP model,
  adapter tests, and orchestration output contract together.

**Acceptance evidence:**

- Two `PortfolioApplication` instances over one target root cannot cause a second acquisition to
  remove the first instance's Planning claim.
- The second acquisition reports no replacement launch for occupied work.
- An explicit `recover_claim` with stale identity fails without mutation.
- An explicit recovery of a confirmed failed Planning or Build claim releases only that claim and
  preserves the existing Build recovery evidence guarantees.
- A `TargetMCPAdapter` sequence proves acquire -> failed worker/dispatch -> exact `recover_claim` ->
  replacement acquire, because orchestration itself is an agent workflow rather than an executable
  test harness.

## Priority 0 — preserve Design stage in work-item projection

**Finding: confirmed user-visible projection defect. Confidence: 0.97.**

`ReturnDelivery(target=DESIGN)` persists `OutcomeAuthorityBinding.stage=DESIGN` and a
`DeliveryReturnContext`. The active projection adapter does not carry either fact into the target-v1
`TargetAuthority`/`WorkItemEvidence` input expected by `WorkItemProjector`. The projector therefore
sees an active outcome whose plan scope is not in `planned_scope_ids` and reports `PLANNING`, agent
attention, and `Inspect progress` instead of Design, user attention, and `Resume design`.

Do not fabricate a `DesignReentryBriefing`: its fields do not correspond exactly to
`DeliveryReturnContext`. Preserve the current schema-v2 stage and return context explicitly.

**Recommended measure:** add a regression at the `PortfolioApplication.list_work_items()` and
`show_work_item()` boundary, then make the read path preserve the binding's canonical stage. The
smallest acceptable implementation may extend the projection evidence input; the eventual native
projector may consume `DeliveryContract` and `DeliveryFrontier` directly. The public read result
should expose typed return context rather than synthesizing target-v1 semantic evidence.

**Pros:**

- Fixes incorrect Cockpit and MCP state immediately.
- Establishes the canonical frontier stage as the progress source of truth.
- Provides a durable acceptance test for the later projector rewrite.

**Cons:**

- A minimal bridge extends an already transitional target-v1 projection interface.
- Exposing return context may require a bounded public-model change.

**Risk:** Low to medium. The fix is read-only, but clients may rely on existing projection fields.

**Acceptance evidence:**

- Return one outcome from Planning and one from Implementation to Design.
- `list_work_items()` reports `stage=design`, `attention=user`, and
  `next_action="Resume design"` for both.
- `show_work_item()` exposes the exact return reason and locators without leaking owner/process
  identity or inventing a `DesignReentryBriefing`.
- The returned item's own `dependency_ready` is false; this discriminates the corrected
  user-attention state from today's Planning/agent projection.

## Priority 1 — retire the confirmed dead Integration API

**Finding: confirmed source-and-test-only path. Confidence: 0.96 inside this repository.**

The former `ChangeWorkspaceManager.integrate()` implemented an older merge/finding workflow alongside the live
repair-candidate and reviewed-repair admission flow used by
`PortfolioApplication.create_integration_repair_candidate()` and
`PortfolioApplication.admit_reviewed_integration_repair()`.
There were no production callers of the old method or its result types. The old method and its result
types are now removed. This closure also removes the legacy runtime completion-capture and Integration
attention/completion writers; persisted frontier readers and reviewed-repair transformations remain for
compatibility.

The retirement was performed by exact symbol closure, not by an `Integration*` name sweep. Removed
symbols are:

- `IntegrationFinding`
- `IntegrationResult`
- `PortfolioCoordinator.publish_finding`
- `ChangeWorkspaceManager.integrate`
- `ChangeWorkspaceManager._publish_integration_finding`
- `DeliveryRuntime.completion_capture_bytes`
- `DeliveryRuntime.publish_integration_completion`
- `DeliveryRuntime.publish_integration_attention`
- private helpers proven by reference search to serve only that closure

Keep the live symbols:

- `IntegrationContext`
- `IntegrationRepairCandidate`
- `create_integration_repair_candidate`
- `admit_reviewed_integration_repair`
- `publish_integration_repair_authority_attention`
- Integration attention readers and reviewed-repair operations

**Pros:**

- Removed a parallel Integration vocabulary and a substantial portion of
  `ChangeWorkspaceManager` before any decomposition decision.
- Made the candidate/proof/CAS path the single Integration implementation.
- Removed tests specific to unreachable merge/finding behavior after any still-live invariant proof
  has been preserved on the current Integration path.

**Cons:**

- Breaks unobserved external Python callers of a package-root export.
- Removes historical executable proof; history remains available in Git.

**Risk:** Low inside this repository, medium for unknown external direct-library consumers. OwlBear
does not promise backward compatibility, but the surface change must still be explicit.

**Prerequisites:**

1. Completed: add a contention regression for two independently constructed
  `PortfolioApplication.create_integration_repair_candidate()` callers over one runtime root. The
  proof must record disjoint intervals for the shared `integration_lock()` and preserve the separate
  no-target-mutation proof in
  `test_publishes_and_replays_exact_change_branch_without_mutating_target_or_user_checkout`.
2. Closed: neither the historical
  `.owlbear/target/target-runtime/integration-findings/*.json` path nor the current host-local
  `.owlbear/delivery/runtime/claims/integration-findings/**` path exists in this workspace. The current
  runtime is gitignored, `delivery_migration.py` does not migrate either namespace, and no reader
  remains after producer removal. They are inert historical bytes, so no retirement inventory or
  cleanup authority is added; the retirement tool continues to handle only known authoritative paths.

The first prerequisite is now covered by the independent-application contention regression. No local
Integration producer remains; a future GitHub-backed acceptance slice must establish the external
source of any new attention or completion state.

**Acceptance evidence:**

- Exhaustive reference search shows no remaining references to the deleted closure.
- Package-root exports and public-surface tests name only the live Integration vocabulary.
- Current Integration attention, target-CAS loss, replay, cleanup, and reviewed repair tests remain
  green, including the independent-application shared-lock contention proof.

## Priority 1 decision — complete or remove Assembly

**Finding: unreachable/incomplete active capability. Confidence: 0.99 for reachability, 0.65 for
product disposition.**

Assembly exists in `DeliveryStage`, `DeliveryWorkerRole`, `OutcomeAuthorityBinding`, role policies,
candidate selection, work projections, and Cockpit presentation. Current contract compilation never
sets `assembly_required=True`, and the MCP registry intentionally has no Assembly context or
Assembly-specific publication operation. Production admission therefore cannot reach the stage.

This is not an implementation refactor until its product disposition is chosen.

**Option A — complete Assembly end to end.** Add authored composition authority, compiler output,
promotion rules, bounded Assembly context, reviewed output publication, MCP operations, agent
workflow, recovery, and browser-visible proof.

- Pro: preserves the intended distinction between individually reviewed task results and a composed
  outcome claim.
- Con: substantial product and protocol surface for a capability with no current producer.
- Risk: High; partial completion would create executable but unreviewable states.

**Option B — remove Assembly from active schema-v2 Delivery.** Remove the stage, role, field, loader
policy, candidate path, current projection/UI lane, frontend `WorkItemStage`/worker-role unions,
Cockpit E2E seed/spec branches, and active tests. The explicit Cockpit scope includes
`serve/cockpit/web/src/api/workItems.ts`,
`serve/cockpit/web/e2e/support/seed-work-portfolio-delivery.py`, and
`serve/cockpit/web/e2e/work-portfolio.spec.ts`. Retained target-v1 evidence may keep its own
historical assembly/job vocabulary until that generation is retired.

- Pro: removes unreachable state and follows the no-speculative-capability rule.
- Con: a future composition requirement needs a fresh design and schema change.
- Risk: Medium because persisted frontier JSON currently contains `assembly_required=false` and
  strict models reject unknown fields; migrate or recreate current frontier records atomically.

**Option C — short bounded deferral.** Reject `assembly_required=True` at current admission/runtime
boundaries, remove misleading active UI affordance, and record a decision deadline. Do not claim
Assembly is live in README text.

- Pro: smallest immediate behavior change while preserving design space.
- Con: retains dormant code and schema weight.
- Risk: Low short term, high if the deadline is allowed to drift.

**Recommendation:** choose B unless a concrete admitted outcome requires independent composition
proof now. Use C only as a time-bounded bridge.

**Acceptance evidence:**

- The chosen decision is documented with one authoritative definition of composition proof.
- If completed, a real authored package compiles into Assembly and traverses the full MCP workflow.
- If removed, no active source, serialized schema, tool, projector, or Cockpit branch names Assembly.
- If deferred, attempts to create Assembly state fail with a typed diagnostic before publication.

## Priority 1 — prove and remove empty authority reintroduction

**Finding: target-v1 cutover capability remains executable but has no repository-local non-empty
producer. Confidence: 0.91 for this repository, 0.65 for external workspaces.**

The current cutover request names `authorities=[]`. Fresh `setup/init.py` also creates cutover
requests with an empty authority set and uses `TargetAuthorityRegistry` only to smoke-check that the
new target is empty. `setup/finalize.py` still supports non-empty target-v1 authorities and validates
them with `TargetRuntime` before receipt publication.

Do not describe this as wholly dead until external/distributed consumers are inventoried. Split the
work into two decisions:

1. Prove that supported setup and finalization no longer reintroduce target-v1 authorities.
2. Remove that executable half of the cutover contract; separately decide how long raw historical
   snapshot querying remains supported.

**Recommended measure:** make new setup initialize schema-v2 Delivery directly after a receipt-gated
empty target activation. Retire the non-empty `authorities`, classifications, target-v1 state
materialization, registry smoke, and `TargetRuntime` smoke from the supported finalizer. Preserve old
bytes under `.owlbear/legacy/` as immutable historical data if required; historical retention does
not require those records to remain executable.

**Pros:**

- Removes the largest duplicate authority/runtime generation from active code and package exports.
- Simplifies setup, finalization, cutover, and future projection work.
- Separates historical evidence retention from executable compatibility.

**Cons:**

- Existing pre-cutover workspaces with non-empty authority requests can no longer use the finalizer.
- Any structured historical query requiring target-v1 models needs an archive reader or an explicit
  decision that Git/raw JSON is sufficient.

**Risk:** High until consumer inventory and evidence-retention policy are explicit; medium after the
absence proof. The project explicitly does not require backward compatibility, but silent evidence
loss remains unacceptable.

**Acceptance evidence:**

- Search all setup seeds, fixtures, current workspaces, and documented commands for non-empty
  `TargetCutoverRequest.authorities` producers.
- Fresh setup and setup-finalization tests pass without importing `TargetAuthorityRegistry` or
  constructing `TargetRuntime`.
- `target_cutover._initialize_target` and `_verify_staging` no longer create or validate target-v1
  authority/runtime paths for supported cutovers.
- Historical snapshots remain byte-verifiable by the chosen retention mechanism.
- Package root and README clearly distinguish active Delivery from archived evidence.

## Priority 2 — make startup authorization a pure steady-state gate

**Finding: current startup authorization mixes gate, audit, and replay cleanup. Confidence: 0.95.**

Both MCP and Cockpit call `authorize_target_mutation()` during startup and discard its returned
`TargetMutationAuthority`. The call validates the request and receipt, checks retired-source
absence, verifies target authority and snapshot contents, repairs/removes retired source remnants,
and removes a pending marker. It is therefore not currently a read-only authorization check.

Do not simply skip snapshot verification. First give mutation and cleanup distinct owners.

**Recommended measure:**

1. Finish rollback/replay cleanup in the one-shot setup/finalizer cutover command.
2. Make the steady-state gate read-only and bounded: validate request/receipt identity, target
   manifest identity, configured target path, adapter reference, and absence of active retired
   sources. It must not delete or rewrite files.
3. Keep full `verify_legacy_snapshot` as an explicit audit/health operation only if archived snapshot
   integrity remains a product requirement.
4. State the process topology: Cockpit and MCP may each construct an application over one shared
   target root; mutation safety comes from filesystem locks and exact-byte OCC, not from startup
   authorization or an in-memory singleton.

**Pros:**

- Removes migration mutation and archive traversal from ordinary process startup.
- Makes startup deterministic and easier to test for side effects.
- Separates live mutation authority from historical archive health.

**Cons:**

- Archive corruption is no longer detected on every startup.
- A separate audit command or health surface must own retained-history verification if required.

**Risk:** Medium to high until cleanup ownership and retention policy are defined. A writable receipt
does not provide adversarial tamper resistance; the current guarantee is drift/corruption detection,
not a cryptographic trust root.

**Acceptance evidence:**

- A startup-gate test snapshots directory entries, contents, and mtimes and proves no mutation.
- Missing/mismatched request, receipt, target manifest, adapter reference, or source absence fails
  closed with stable diagnostics.
- Interrupted cutover tests prove the one-shot command still completes or rolls back every cleanup
  stage.
- Explicit snapshot audit detects altered archive bytes.
- MCP and Cockpit startup contract tests pass against the pure gate.

## Priority 2 — replace the transitional work-item projection

**Finding: active code depends on a lossy schema-v2-to-target-v1 conversion. Confidence: 0.88.**

After the Design-stage defect is fixed and the Assembly decision is made, replace the active
projection adapter. Current-only inputs are `DeliveryContract` and one coherent `DeliveryFrontier`;
target-v1-only concepts include authority status/supersession, `DesignReentryBriefing`, semantic
updates, completion summaries, and change-level assembly scopes. The current active adapter does not
populate those concepts, so their presence in generic projector tests does not prove that they are
live Delivery behavior.

**Recommended measure:** define one Delivery-native work-item projection boundary. Either let the
projector consume `DeliveryContract` plus a single frontier value directly, or define a narrow
immutable read model that preserves canonical stage, return context, block/request attention, task
progress, dependency state, and completion. The narrow model is justified only if it hides these
representations from more than one caller.

Retain the target-v1 projector only behind an actual historical-evidence consumer. Delete it with
the target-v1 generation if no such consumer remains.

**Pros:**

- Removes duplicate authority vocabulary from the active path.
- Prevents future stage inference from diverging from canonical runtime state.
- Simplifies eventual target-v1 retirement.

**Cons:**

- Couples projection more directly to current Delivery semantics.
- Requires an explicit disposition for old-only fields rather than inheriting them accidentally.

**Risk:** Medium. Work-item models are consumed by Cockpit and MCP and require exact contract tests.

**Acceptance evidence:**

- Existing list/show work-item outputs remain stable except for intentional defect corrections.
- Design return, Planning, Implementation, block/request, dependency waiting, completion, and the
  selected Assembly disposition are covered through `PortfolioApplication`.
- Active projection imports no target-v1 authority or evidence models.
- No test claims active behavior solely by constructing a target-v1 projector fixture.

## Priority 2 — validate supported concurrency before adding new lock abstractions

**Finding: repeated frontier reads exist, but the initially claimed stale-publication race was not
valid. Confidence: 0.84.**

Candidate selection calls `active_claims`, `change_stage`, `claimable_outcome_ids`, `show_binding`,
and `claimable_task_ids`, each of which reads the frontier. Exact-byte OCC prevents a stale writer
from silently replacing newer frontier bytes. Also, normal plan/result publication and worker
transition require an already-active exact claim, while acquisition excludes a runtime with active
claims. These facts invalidate the original example in which an unclaimed Planning outcome
concurrently publishes a plan.

Do not add a snapshot API or expand the global acquisition lock based only on repeated reads. First
test the supported topology after automatic claim stealing is removed.

**Pros of testing first:** avoids serializing independent worker publication or introducing a broad
snapshot model without a demonstrated behavior gap.

**Cons:** does not reduce repeated I/O by itself.

**Risk:** Low.

**Acceptance evidence:**

- Two application instances racing acquisition produce at most one active claim.
- Concurrent same-claim publication/transition either replays identically or yields a typed OCC
  conflict; no update is lost.
- Acquisition concurrent with request resolution, administrative movement, and admission fails
  closed or observes a coherent successor.
- Measure actual frontier-read cost before proposing an optimization.

## Priority 3 — reassess naming and decomposition after deletion

Do not broadly rename `target_*` or split the three large active classes while both architecture
generations remain present. Today `target` has at least three meanings: the activated filesystem
root/cutover authority, retained target-v1 semantic execution, and stale names on active Delivery MCP
adapter files. A mass rename would hide those distinctions rather than resolve them.

After target-v1 retirement and dead Integration removal:

1. Inventory every remaining `target_*` symbol by meaning.
2. Keep names that refer to the activation target or serialized target paths.
3. Rename only active Delivery transport or contract symbols whose `target` prefix no longer names a
   real boundary.
4. Reduce package-root `__all__` to intentionally supported consumer contracts; require direct
   submodule imports for specialized internals.
5. Remeasure classes and apply the module deletion test. Extract only a component that owns state or
   hides a complete transaction/lifecycle behind a smaller interface. Do not introduce mixins,
   internal forwarding managers, or a new seam solely to reduce LOC.

**Pros:** naming and module boundaries will reflect the surviving architecture rather than an
intermediate migration state.

**Cons:** delays cosmetic cleanup.

**Risk:** Low. Confidence: 0.90.

**Prerequisites:** complete the dead Integration closure removal and target-v1 retirement measures;
otherwise the current overloaded names still describe materially different generations.

**Acceptance evidence:**

- Every remaining public export has at least one intended consumer and documented ownership.
- No rename changes persisted artifact paths unless a separate migration requires it.
- Any extracted module passes the deletion test: removing it would force hidden complexity back into
  multiple callers, not merely remove one forwarding hop.

## Reviewed and retained — Delivery MCP module split

No improvement measure is currently justified for the split between
`owlbear_delivery_mcp.server` and `owlbear_delivery_mcp.target_server`.

**Review confidence:** 0.92. **Change risk:** no-action risk is low; merging or generating methods
would have medium maintainability and protocol-audit risk. **Revisit prerequisite:** one module must
gain or lose a material responsibility, or a second transport adapter must establish real variation.

- `server.py` owns process configuration, target authorization, application construction, lifespan,
  and the live provider.
- `target_server.py` owns request validation, application delegation, structured serialization,
  error-to-`ToolError` translation, tool annotations, and registry assembly.
- `TargetMCPAdapter.from_provider()` resolves the application after lifespan starts while allowing
  tools to be registered at module import time.
- Explicit tool methods are preferable to generated methods for this public protocol.

Revisit only if one responsibility changes materially; do not merge files to reduce file count.

## Recommended execution order

1. Stop automatic recovery of active claims during acquisition; add multi-instance regression proof.
2. Fix Design-return work-item projection through the public application boundary.
3. Decide Assembly: complete, remove, or time-bound fail-closed deferral.
4. Delete the exact dead Integration API closure.
5. Prove and remove empty target-v1 authority reintroduction from supported setup/finalization.
6. Make steady-state startup authorization a pure gate and assign one-shot cleanup explicitly.
7. Replace the active target-v1 projection adapter with a Delivery-native projector.
8. Decide whether historical snapshot querying remains a product surface; retire remaining target-v1
   runtime/models when it does not.
9. Add broader multi-instance OCC/concurrency tests and optimize reads only if measurements justify it.
10. Reassess names, exports, and class boundaries against the reduced implementation.

Each item should be admitted as its own bounded Delivery change when it becomes executable. Do not
combine the lifecycle fixes, cutover retirement, projector rewrite, Assembly decision, and naming
cleanup into one migration.

## Memory

- allow searching for memory IDs in cockpit

## Code index — push detail into file headers, keep the index thin

### Status quo

`serve/tools` already generates navigation indexes (`uv run indexes` → `doc-index`, `py-index`,
`ts-index`), and `h-codebase-orientation` already tells agents to use them as wayfinders. Two
problems in practice:

- **The indexes are too long to read.** `.owlbear/py-index.md` is ~3,000 lines, `ts-index.md` ~1,100,
  `doc-index.md` ~1,100. An agent looking for one module pays to scan thousands of lines — the
  index costs nearly as much attention as searching the source it was meant to replace.
- **Nothing regenerates them.** They are not wired into any hook or CI step, so they drift silently.
  As of 2026-08-02 the newest `serve/` change was 2026-08-02 while `py-index.md` was last
  regenerated 2026-07-14.

### Proposal

Invert where the detail lives, the way a C/C++ header declares an interface next to the code it
belongs to:

- **Full detail moves into an auto-generated header block at the top of each source file** — roughly
  the first 20 lines: what the module is for, what it exports, what it depends on. An agent that
  opens the file gets the summary immediately, with zero index lookup.
- **The index file shrinks to a routing table** — one line per file: path plus a one-sentence
  purpose. Enough to pick the right file, nothing more.

Generation stays a script, not an agent, so it costs no tokens and cannot drift into opinion.
Regeneration should run as part of the linter pass so headers and index are always current.

**Open questions:**

- Is there an existing standard or tool for generated per-file header summaries worth adopting
  instead of hand-rolling one? Check before building.
- Header blocks are generated content inside human-edited files — needs a stable delimiter and a
  check that regeneration never eats hand-written content below it.
- Does the same treatment fit `doc-index`, or is that one already short enough to leave alone?

**Expected outcome:** An agent finds the right file from a short index, then gets that file's full
structure from its own first lines. No 1,000-line index reads, no stale indexes.
