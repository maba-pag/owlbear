# Delivery N04 — Same-Change Requirement Revision and Evidence Reuse

> **Package:** N04 of the
> [execution plan](delivery-redesign-execution-plan.md#n04--same-change-requirement-revision-and-evidence-reuse),
> re-scoped 2026-10-04. Supersedes PR #358 (closed); nothing of its mechanisms is imported.
> **Planned on:** `origin/dev` `d0223e0a1` (N03-A, N09-A2, N02-D merged; N03-B and N03-C not merged;
> frontier 19, format 2). Live state not read; probes used disposable state only.
> **Status:** N04-P in review. Product code is unchanged by this phase. Reviews work in the execution
> plan's [operating context](delivery-redesign-execution-plan.md#19-operating-context).

## 1. Contract

### 1.1 Result

A requirement change on a nonterminal admitted Change runs in four steps, all through existing owners:

1. **Pause.** The Designer pauses the Change (`set_change_intent` defer, N09-A2 drain) and waits for the
   deferral.
2. **Revise.** The Designer revises the package (`revise_design_session`), challenges it, shows the delta
   (changed, new and removed `AC-NNN` criteria; outcomes to replan; confirmations kept or asked again) and
   gets the user's approval in chat, as for a first admission.
3. **Activate.** `admit_change` with the approved package ID activates the revision crash-safely: package
   contract, package snapshot on the reviewed head, then one authority transaction that also resumes the
   Change and records the publication obligation. Restart at any step reaches the old version or the
   replayed new one.
4. **Replan.** Unchanged outcomes keep their bindings and evidence. Changed outcomes and their dependents
   return to Planning; the normal continuation prompt picks up the Planner.

Evidence reuse falls out of N03 identities (N03 plan §1.4, §1.9): an observation covers a criterion only at
an unchanged ID and version; a changed criterion is uncovered and gets new tasks; a person-only confirmation
for a changed criterion is asked again through a new scoped request answered in Cockpit. D03's
retained-handoff Design return becomes readmittable. Completed and abandoned Changes stay immutable;
further work is a successor Change. Cockpit offers **Change requirements** on nonterminal Changes.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | One route for a requirement change on a nonterminal Change: Pause → revise → approve → activate → replan; engine, `w-design-session` and `serve/delivery/README.md` agree | Programme §8.2; #213 |
| R2 | Revision is refused while an active claim, retained non-Design custody, Change attention, Integration repair claim, finalization or ready PR exists; prior finalization never survives a revision | #213; programme §8.2 step 3 |
| R3 | Activation is replayable at every durable boundary; restart reaches the old approved version or the replayed new one; no duplicate snapshot commit, no lost block | Programme §8.3; V21 (activation) |
| R4 | Prior authority retained (revision history); only affected outcomes replanned | V14; programme §8.1 |
| R5 | Evidence for an unchanged criterion (ID and version) still covers it; no new human exercise because a request ID changed | V15; N03 §1.4, §1.9 |
| R6 | A changed criterion is uncovered and shown as such; no silent waiver; a person-only check for it is asked again | V16; N03 §1.9 |
| R7 | D03's retained-handoff Design return is readmittable without losing the Builder's work | Execution plan §2.2; D03 |
| R8 | Completed Changes are immutable; further work is a successor Change | Programme §8.2 |
| R9 | **Change requirements** control in Cockpit with the §1.4 companions | Execution plan §3 (§4.2 controls) |
| R10 | Support baseline; LC where loading changes | Execution plan §1.1, §1.3 |

Excluded (execution plan §5 N04, 2026-10-04): applicability records; foreign-head, fresh-host-replacement and
remote-child routes; signed deterministic child commits; exception tables. Live B1
(`macos-managed-browser-authentication`) is reconciled once at N10-M by an agent-assisted manual step.

### 1.3 Existing owners (on `d0223e0a1`)

| Concern | Owner | Today |
| --- | --- | --- |
| Package revision | `PortfolioApplication.revise_design_session`, `_admitted_design_revision_allowed` (`portfolio_application.py`); `DesignPackageStore.revise` | Admitted Changes may revise only in Design stage with no claim, disposition, repair claim or finalization (P1) |
| Admission and revision | `PortfolioApplication.admit_delivery_change`; `DeliveryAuthorityRegistry.admit`, `_delivery_frontier`, `_invalidated_outcomes`, `_delivery_participants`, `_carry_forward_unresolved_binding` (`delivery_admission.py`) | One `RuntimeTransaction` writes contract, frontier, receipt and `revisions/<old contract digest>/` history; outcome-level invalidation with dependency closure |
| Package snapshot | `ChangeWorkspaceManager.snapshot_design_package`, `_replace_design_package_snapshot` (`workspace_snapshots.py`) | Replacement requires the branch at the previous snapshot head (P2) |
| Pause | `set_change_intent`, `_admit_pause` (`portfolio_application.py`); `_custody_drained`, `_convert_pause_request` (`application_lifecycle.py`); `DeliveryRuntime.defer_change`, `resume_change` | A drained request becomes `change_deferral`; passive handoffs count as drained |
| Mutability | `_require_change_mutable` (`runtime_support.py`); `_NORMAL_CHANGE_MUTATIONS` (`runtime_models.py`) | A deferred Change refuses every runtime mutation except resume and abandon |
| Evidence | `evaluate_acceptance_evidence`, `observation_gaps`, `request_applies` (`evidence.py`); `retained_requests` (`runtime_models.py`) | Stale versions never cover (P3); promotion keeps answered scoped requests |
| Planning with prior results | `_advance`, `_validate_planner_return_plan`, `_return` (`runtime_reads.py`) | Return to Planning keeps completed tasks and results; byte-identical preservation is enforced only on the handoff route |
| Design return | `DeliveryRuntime.settle_builder_invocation` (route `same-outcome-design`); `_return` + `ChangeWorkspaceManager.restart` (`change_workspace.py`); `quarantine_dirty_worktree` (`workspace_snapshots.py`) | The claim-held return preserves the head under `refs/owlbear/attempts/<change>/<attempt>` and resets to the reviewed head; the D03 settlement keeps a passive handoff that blocks admission (P4); `restart` and quarantine refuse passive custody |
| Startup | `_validate_local_snapshot` (`delivery_application_loader.py`) | Local package ID, contract, admission and reviewed head must equal the remote snapshot; a pending marker excuses only the frontier (P5) |
| Review repair | `prepare_review_repair` (application and runtime) | Returns the PR to draft and replaces finalization with a `review-repair` invalidation |

### 1.4 Invariants

- **I1 Paused and published before activation.** Activation requires the deferral, no Pause request, no
  pending state publication, no claim or writer (a retained Design-route handoff is released first, §1.7),
  no Change attention, no Integration repair claim, no finalization or ready receipt, no merged latch.
- **I2 One authority transaction.** After the package snapshot, one `RuntimeTransaction` writes contract,
  frontier, admission receipt, revision history and the pending publication marker. Nothing about the
  revision is written to the runtime after it.
- **I3 Change-level state survives.** The revised frontier is `current.model_copy(...)`: only `bindings`,
  `pending_checkpoint`, `finalization_invalidation` and `change_deferral` change. Publication history,
  target-sync and external-head receipts, operator moves and the published head are kept (today's
  constructor rebuilds the frontier from four fields, P5, and drops the deferral, P2).
- **I4 Identity-based reuse.** Coverage is the N03 evaluator unchanged; N04 decides only which bindings,
  results and requests remain in the frontier.
- **I5 Nothing lost.** No Builder byte is discarded: retained Design-return work is preserved under refs
  before any reset.
- **I6 Recognizable intermediate states.** Each durable step leaves a state that startup accepts as a
  recognized successor of the remote snapshot.

### 1.5 Revision activation (N04-A)

**Entry.** `revise_design_session` on an admitted Change requires I1 except the publication condition, and
it releases a retained Design-route handoff first (§1.7; until N04-B it refuses `custody-retained`);
`_admitted_design_revision_allowed` is replaced by that rule (Design stage alone no longer suffices).
Unadmitted packages behave as today.

**`admit_delivery_change` for a revision** (current authority exists and the Change is paused with a revised
package):

1. Replay this Change's pending state publication (`_replay_pending_state_publications`, existing), then gate
   I1 under the acquisition and checkpoint locks; `expected_package_id`, `expected_frontier_digest` and
   `expected_design_package_snapshot_receipt_id` fence the exact versions (existing fields, now required
   for a revision).
2. Publish the package contract (`_publish_package_contract`, existing).
3. Snapshot the revised package on the **reviewed head**: `_replace_design_package_snapshot` takes
   `coordination.last_reviewed_commit` as the expected head and requires the branch there and a clean
   worktree. Its intent and receipt make it replayable (existing). For a revision, the registry runs step 2
   and step 4 as separate calls so the application snapshots between them; first admission keeps today's
   order.
4. One transaction (I2): `_delivery_frontier` returns the revised frontier (§1.6), with `change_deferral`
   cleared (activation resumes the Change, D4), the review-repair invalidation cleared, and the checkpoint
   for the snapshot head queued by the rule of `record_design_package_snapshot` and
   `queue_explicit_checkpoint` (re-anchor a pending checkpoint with `_checkpoint_with_head`, else queue an
   `EXPLICIT` trigger), extracted into one pure function they share; plus contract,
   admission receipt, history and a `DeliveryPendingStatePublication` marker whose base is the published
   frontier digest. New history entries are keyed `revisions/<previous contract digest>-<previous frontier
   digest>/`, so revise, cancel and revise again never collide (today's key is the contract digest alone).
5. Best-effort publication and checkpoint reconciliation (existing path); a failure leaves the marker for the
   normal replay before any claim.

**Replay.** Calling `admit_change` again with the same request completes steps 2–5. After step 4 the
request's `expected_frontier_digest` no longer matches the live frontier; the replay is recognized when the
history entry keyed by the active-before contract digest and that frontier digest exists and the current
contract is the compiled one, and returns `replayed: true`.

**Cancel.** Before step 4 the user can drop the revision by revising the package back to the approved bytes
and activating it: on a paused Change whose package differs from its snapshot receipt, admission runs steps
1–5 even when the compiled contract equals the active one, and step 4 then keeps every binding. Until
activation, acquisition stays fenced by the package-authority check (`_validate_package_authority`) and by
the deferral.

**Startup recognition (I6)** in `_validate_local_snapshot`, each an exact predicate:

| State after | Local differs from the snapshot in | Accepted when |
| --- | --- | --- |
| `revise_design_session` or step 2 | package ID (and generated authority) | runtime contract, frontier and admission equal the snapshot (or a recognized frontier successor) and the frontier is deferred |
| step 3 | additionally reviewed head and branch | every first-parent commit from the snapshot's reviewed head to the local reviewed head (= branch head) is a Design package snapshot commit of this Change (the message `_commit_design_package_snapshot` writes), and the latest snapshot receipt names the local package |
| step 4 | additionally contract, admission, frontier | the pending marker matches the local frontier; the history entry keyed by the snapshot's contract digest and the marker's base frontier digest holds the snapshot's contract, admission and (normalized) frontier; the step-3 condition holds |

Anything else still fails closed as today.

**Errors.** `DeliveryRevisionError(DeliveryAdmissionConflictError)`, code `ERR_DELIVERY_REVISION`, `reason`:
`change-not-paused`, `pause-pending`, `change-terminal`, `change-merged`, `change-finalized` (remedy:
`prepare_review_repair`, then Pause), `change-attention`, `custody-retained`, `publication-pending`,
`reviewed-head-moved`. MCP maps the code and reason into `TargetDiagnostic`; no new tool.

**Removed.** `preserve_unresolved_outcome_ids`, `_carry_forward_unresolved_binding`,
`RevisionCarryForward.carried_forward_outcome_ids` and the matching MCP field: programme §8.4 replaces the
blanket carried request with replanning, and §1.6 keeps the confirmations that still apply.

### 1.6 Revised bindings and evidence

`_invalidated_outcomes` (outcome projection plus dependency closure) is unchanged. For each outcome:

- **Unchanged:** binding kept byte-identical, with its results and requests. Results that cover a changed
  criterion simply stop covering it (P3).
- **Changed or dependent:** a Planning binding. What it keeps depends on [U1](#u1--evidence-inside-a-replanned-outcome):
  - Retained in every option: resolved scoped requests (`retained_requests`) whose `applies_to.acceptance`
    names only current `(id, version)` pairs; a `return_context` (target Planning, reason "requirement
    revision", locators = changed `AC-NNN` IDs, `source_boundary` = new contract digest) so the Planner sees
    what changed. Requests naming a changed version are dropped; the Builder raises a new scoped request.
  - U1 (b) adds: completed tasks whose `commitment_ids` are still in the revised outcome, and their results,
    minus any task depending on a dropped one. Planning promotion must keep completed tasks byte-identical
    and add at least one task; `_validate_plan` applies this to every binding with results (today only the
    handoff route checks it).

Finalization coverage, the finalization context and the projection then follow N03 unchanged.

### 1.7 Design-return readmission (N04-B)

A D03 Design return leaves the binding in Design with a `same-outcome-design` handoff context and
coordination `writer.kind == "handoff"` with `builder_handoff`, possibly with unreviewed commits and
uncommitted files. Readmission first **releases** that handoff into the plain Design-return shape that the
claim-held `_return` already produces (head preserved under the attempt ref, branch and worktree at the
reviewed head, tasks and results cleared, `return_context.preserved_commit` set). The released state is
portable, so it is published, and §1.5 then applies unchanged.

`release_design_return(change_id)` (new `DeliveryRuntime` mutation, allowed on a deferred Change, joins the
central policy) is invoked by `revise_design_session` on a paused Change that retains a Design-route handoff.
Order:

1. Verify the worktree still matches the handoff metadata (`_capture_builder_handoff_metadata` against
   `metadata_fingerprint`); otherwise refuse `design-return-workspace-changed`.
2. Capture without changing the worktree: if dirty, the quarantine commit (child of the handoff
   `branch_head`) under `refs/owlbear/quarantine/<change>/<attempt>`, extended to passive Design-return
   custody, plus the real index as a tree under `refs/owlbear/quarantine-index/<change>/<attempt>`; the
   head under `refs/owlbear/attempts/<change>/<attempt>`. Unmerged index entries refuse
   `design-return-unmerged-index`.
3. Reset branch and worktree to the reviewed head and `clean -fd` (ignored files stay in place).
4. One transaction: frontier (binding released; pending publication marker) and coordination (`writer` and
   `builder_handoff` cleared).

Replay: the refs are create-or-equal; step 3 runs only when the worktree matches the captured state or is
already clean at the reviewed head. Startup recognizes the state between steps 3 and 4: in
`_validate_local_builder_handoff_workspace`, a Design-route handoff whose attempt ref equals
`context.branch_head`, whose quarantine refs exist when the fingerprint recorded uncommitted content, and
whose worktree is clean at `last_reviewed_commit`. The readiness prompt in `_design_attention_prompt` drops
the "re-admission is unavailable" text and points to the §1.1 route.

### 1.8 Change requirements control (N04-C)

`DeliveryChangeView.revision_prompt: str | None` (engine-authored; `None` for terminal or merged Changes):
`/design <change-id> Change requirements:`, to which the user adds the change. Cockpit renders **Change
requirements** on the Change detail as a copy control with the N09-A1 copy semantics (it copies, says to run
it in Copilot Chat, never claims a launch). Companions: `workItems.ts` mirror, rendering in
`WorkItemDetail.tsx` with a component test, parity in `tests/test_cockpit_boundary.py`, the work E2E.

### 1.9 Decisions

Settled by the planner (2026-10-04), each with one defensible answer in the operating context:

- **D1 Pause is the only entry.** Every revision of an admitted Change starts with Pause, including a
  Design return; one route replaces the Design-stage special case (#213, R1).
- **D2 Outcome-level replanning.** Keep `_invalidated_outcomes`; criterion-level work is decided inside a
  replanned outcome (§1.6), not by new invalidation records.
- **D3 Change-level fields survive** (I3). The probe shows today's revision silently drops the deferral, and
  the constructor drops publication history and target-sync receipts.
- **D4 Activation resumes the Change.** The approval covers continuing (programme §8.2 step 5); this also
  removes any runtime write after the authority transaction. The user can Pause again.
- **D5 Finalized Changes reopen first.** `prepare_review_repair` (existing) returns the PR to draft and
  invalidates finalization; then Pause and revise. Activation clears that invalidation (#213).
- **D6 Publish before, mark after.** Activation requires the current state published and leaves one pending
  marker, so startup needs exactly the three predicates of §1.5.
- **D7 Snapshot from the reviewed head, before the transaction** (P2), so the Change never runs under the
  new authority with the old branch package.
- **D8 Confirmations kept by version** (N03 §1.9); no other request survives into a replanned outcome.
- **D9 Remove the carried-forward gate** (§1.5 Removed); programme §8.4.
- **D10 Release, then readmit** (§1.7). Reuses the attempt ref and quarantine owners; the index tree ref
  keeps staged content that differs from the worktree. The alternative of carrying the handoff into the
  revised outcome would run new authority on an unreviewed branch.
- **D11 No persisted format change.** Only existing record shapes and refs are written; the new history key
  names a directory for new entries and leaves old ones untouched. LC load form for A and B. A phase that
  finds a format change necessary stops for a plan revision (N02 migration contract).
- **D12 Copy control, no new MCP tool** (§1.8).

Open user decisions:

#### U1 — Evidence inside a replanned outcome

- **When:** every requirement change that edits a criterion of an outcome that already has completed tasks,
  likely the common case.
- **Status quo and problem:** revision resets a changed outcome to an empty binding, so its completed tasks
  and their machine evidence disappear, including evidence for criteria of that outcome that did not change.
  The re-scoped N04 says such evidence still covers.
- **(a) Reset the outcome.** Keep only confirmations (§1.6). Pro: smallest code; the Planner plans the
  outcome from scratch. Con: finished work is planned and proven again; contradicts "evidence still covers"
  for siblings of a changed criterion. Risk: low.
- **(b) Keep completed work and replan the delta.** Keep completed tasks and results whose commitments
  survive; the Planner adds tasks for what changed (the rule that a return to Planning already follows).
  Pro: no repeated work; matches R5 literally. Con: more code in `_delivery_frontier` and `_validate_plan`;
  completed task text written for the old requirement stays as history, and the finalization reviewer judges
  whether carried evidence still applies (N03 §1.6). Risk: medium.
- **Recommendation: (b).** Needed before N04-A starts.

## 2. Feasibility Probes

Run in the lane worktree on `d0223e0a1` with `uv run --no-sync pytest -n0 --basetemp=/private/tmp/n04p-probe`
(deleted afterwards). Probe script and logs: `.owlbear/scratch/n04p-replan/` in lane D (unversioned).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | Admit a Change, add a reviewed task commit, Pause through `set_change_intent`, call `revise_design_session` | Pause converts to `DeliveryChangeDeferral` (stage `deferred`); revision refused: "admitted Delivery Changes cannot revise their Design package" | Pause works as the entry; the revision gate must change (§1.5 Entry) |
| P2 | Same Change; revise the package through the store, then `admit_delivery_change` with the current digests; replay once | Contract written, `OUT-001` reset to Planning, **deferral dropped**; then "Design package snapshot branch moved before replacement"; replay fails the same way; nothing acquirable | Today's revision is neither coherent nor replayable mid-Implementation: D3, D4, D7, I2 |
| P3 | `test_evidence.py::test_stale_versions_and_unknown_ids_never_cover_and_are_admissibility_gaps` | Passes: a stale version never covers and is a `stale-acceptance-version` gap | Evidence reuse needs no evaluator change (I4) |
| P4 | `test_portfolio_application.py::test_design_return_revised_admission_refuses_retained_builder_handoff` | Passes: admission refused before any mutation | D03 limit confirmed; §1.7 needed |
| P5 | `test_source_bound_admission.py::test_revision_preserves_unchanged_binding_and_invalidates_changed_dependents`; source read of `_delivery_frontier` and `_validate_local_snapshot` | Unchanged bindings survive byte-identically; the revised frontier is rebuilt from four fields only; startup compares package ID, contract, admission and reviewed head unconditionally | D2, I3; §1.5 startup recognition |
| P6 | Source read of `_return`, `restart`, `quarantine_dirty_worktree`, `_validate_planner_return_plan`, `_require_change_mutable` | The claim-held Design return already preserves and resets; both owners refuse passive custody; deferred Changes refuse runtime mutations | §1.7 design; `release_design_return` must join the central policy |

## 3. Phases

Shared rules: plans name symbols; re-resolve paths at phase start. Opus keeps activation, replay, startup
recognition and the release order; Luna may take the Cockpit companions and skill text after the contract is
fixed (execution plan §1.6). Durable tests are the scenarios below, no more.

### 3.1 N04-A — Revision activation

- **Prerequisites:** N04-P, N03-C; [U1](#u1--evidence-inside-a-replanned-outcome) answered.
- **Editable paths:** `delivery_admission.py` (`DeliveryAuthorityRegistry.admit`, `_delivery_frontier`,
  `_delivery_participants`, replay recognition; remove `_carry_forward_unresolved_binding` and
  `preserve_unresolved_outcome_ids`); `portfolio_application.py` (`revise_design_session`,
  `_admitted_design_revision_allowed`, `admit_delivery_change`); `workspace_snapshots.py`
  (`_replace_design_package_snapshot`); `delivery_runtime.py` (shared checkpoint-queue function);
  `runtime_reads.py` (`_validate_plan`, U1 (b) only);
  `delivery_application_loader.py` (`_validate_local_snapshot` predicates); `delivery-mcp` `target_server.py`
  and `target_models.py` (error mapping, removed field); `owlbear_delivery/__init__.py` and
  `module_surface.json` if exports change; tests in `test_source_bound_admission.py`,
  `test_portfolio_application.py`, `test_delivery_state.py` (loader), `test_target_server.py`;
  `share/skills/w-design-session/SKILL.md` (revision procedure: Pause, wait, revise, delta, approval,
  `admit_change`, report; remove "do not revise the admitted package in place"),
  `tests/test_agent_ecosystem_validation.py` if it pins that text; `serve/delivery/README.md`; this plan's
  progress row; execution plan status row.
- **Companions:** activation is an existing frontier writer; if `tests/test_delivery_worktree_authority.py`
  does not cover admission, add it. No new readiness reason.
- **Positive scenarios:**
  - Paused Change with one promoted task and one unchanged outcome: revise one criterion, activate. The
    unchanged binding is byte-identical, the changed outcome is Planning (per U1), the snapshot commit is a
    child of the reviewed head, publication history and target-sync receipt are kept, the deferral is gone,
    one pending marker exists; the Planner is acquirable.
  - Evidence: an observation covering the unchanged `AC-001` still covers it; the changed `AC-002` is
    uncovered; a retained confirmation for `AC-001` satisfies a new human-confirmed observation; the one for
    `AC-002` is gone.
  - Crash injection after step 2, after step 3 and after step 4: restart loads the Change as available;
    replaying the same `admit_change` request finishes with one snapshot commit and `replayed: true`.
  - Finalized Change: `prepare_review_repair`, Pause, revise, activate; finalization and the invalidation are
    gone.
- **Negative scenarios:** not paused; Pause request pending; active claim; ready PR or finalization
  (`change-finalized`); completed or merged Change; pending publication; reviewed head moved; each refuses
  with its reason and changes nothing.
- **Inner loop:** `env -u PYTHONPATH uv --directory <lane> run pytest serve/delivery/tests/test_source_bound_admission.py -q -n0`,
  then the new `test_portfolio_application.py` and loader cases by `-k revision`.
- **Closeout:** `uv run test --changed --base origin/dev`; scoped ruff; agent-ecosystem tests; LC load form.
- **LC:** load form (startup recognition changes; no format change).
- **Size / risk:** M / high.

### 3.2 N04-B — Design-return readmission

- **Prerequisites:** N04-A.
- **Editable paths:** `delivery_runtime.py` (`release_design_return`); `runtime_models.py`
  (`_NORMAL_CHANGE_MUTATIONS`, Pause class); `runtime_support.py` (`_require_change_mutable`: allowed while
  deferred); `workspace_snapshots.py` (`quarantine_dirty_worktree` for passive Design-return custody; index
  tree ref); `change_workspace.py` (attempt-ref preserve and reset beside `restart`);
  `portfolio_application.py` (`revise_design_session` invokes the release); `delivery_application_loader.py`
  (`_validate_local_builder_handoff_workspace` captured-and-reset state); `application_readiness.py`
  (`_design_attention_prompt`); tests in `test_portfolio_application.py`, `test_change_workspace.py`,
  `test_delivery_state.py`, `test_work_items.py`, `tests/test_delivery_worktree_authority.py`;
  `share/skills/w-packet-building/SKILL.md` (a Design return is preserved and reset at readmission); progress
  and status rows.
- **Companions:** the new mutation joins the central mutability policy and its authority coverage.
- **Positive scenarios:**
  - The `_return_builder` fixture (committed, staged, unstaged and untracked bytes) returns to Design;
    Pause; revise; the release preserves the head and the quarantine and index trees, the worktree is clean
    at the reviewed head, custody is released and published; activation then succeeds and the Planner sees
    `preserved_commit`. Restoring from the refs reproduces every byte, including the staged one.
  - Crash after step 3: restart loads the Change; the next `revise_design_session` finishes the release.
- **Negative scenarios:** worktree changed since the handoff; unmerged index; a same-task or Planning-route
  handoff (`custody-retained` at activation).
- **Inner loop:** the new readmission test, then `-k "design_return or quarantine or restart"`.
- **Closeout:** as N04-A; LC load form.
- **Size / risk:** M / high.

### 3.3 N04-C — Change requirements control

- **Prerequisites:** N04-B.
- **Editable paths:** `application_models.py` (`DeliveryChangeView.revision_prompt`); its projection in
  `portfolio_application.py`; `serve/cockpit/web/src/api/workItems.ts`, `workItemPresentation.ts`,
  `WorkItemDetail.tsx` and its component test; `tests/test_cockpit_boundary.py`; the work E2E spec;
  `setup/operating-owlbear.md` (requirement change); progress and status rows.
- **Positive scenarios:** a nonterminal Change shows **Change requirements**; the copied text starts with
  `/design <change-id>`; the copy confirmation says to run it in Copilot Chat.
- **Negative scenarios:** completed, abandoned and merged Changes show no control.
- **Inner loop:** the component test; `npm test` in `serve/cockpit/web`.
- **Closeout:** `npm test`, `npm run build`, `npm run test:e2e:work`, Biome on changed files,
  `uv run test --changed --base origin/dev`; package closeout: the full `uv run test` once and a cumulative
  challenge of the N04 diff.
- **LC:** not applicable.
- **Size / risk:** S / low.

## 4. Progress

| Phase | PR | Head | Proof | Challenge | Status |
| --- | --- | --- | --- | --- | --- |
| N04-P | this PR | — | Probes P1–P6; docs only | Lead runs the plan gate | in review |
| N04-A | — | — | — | — | — |
| N04-B | — | — | — | — | — |
| N04-C | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence now | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | The three startup predicates (§1.5) accept every intermediate state and nothing else | Not built; P5 is a source read | Loader comparisons on `d0223e0a1` | N04-A crash-injection tests | N04-A merge |
| G2 | `_publish_package_contract` changes the package ID the loader compares | Not probed; the predicate for step 2 covers either answer | `DesignPackageStore.revise` clears generated authority | N04-A first check | N04-A merge |
| G3 | The released Design return publishes as a portable state accepted by the remote snapshot comparison | Not built | `settle_builder_invocation` portability rule; P6 | N04-B | N04-B merge |
| G4 | A real Designer chat follows the revised `w-design-session` route | No host run | Skill text only | N10-H host journey | N10 only |
| G5 | A Builder of a replanned outcome cites a retained confirmation instead of asking again | Workflow behavior | Engine accepts it (N04-A scenario) | N10-H | N10 only |
