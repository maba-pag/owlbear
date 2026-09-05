# Delivery System Audit

> **Owning request:** User-requested full Delivery audit, 2026-09-05; no admitted implementation task.
> **Date:** 2026-09-05
> **Baseline:** `5ba3d49aeb91f7b3fd8ddc4a9efaebb07596e8c9` on `dev`; initially clean worktree.
> **Status:** Complete. Thirteen findings plus capability, depth, and follow-up assessments; advisory, not implementation authority.
> **Question:** Does Delivery reliably turn user intent into reviewed, accepted changes, including when agents, processes, Git, or external services fail?

## 1. Scope And Method

Audit the Delivery engine, GitHub provider, MCP interface, active Delivery agents and skills,
and relevant Cockpit backend/frontend. Preserve implementation and live Delivery state; write this
research document incrementally. No live Delivery changes, requests, claims, or repository commits
are created. Maintained tests may create and discard isolated fixture state.

Trace the complete workflow and its failure paths. Distinguish observed source behavior, documented
contracts, executable verification, and inference. Findings use stable IDs, impact, confidence,
source references, and acceptance ideas so later planning can select them independently.

The assessment concerns supervised Delivery with trusted agents and user-owned acceptance. It does
not assume adversarial workers, fully unattended operation, or deployment guarantees. Exact-state
and publication protection are stronger than progress guarantees and cross-session continuity.
Source tracing disconfirmed several preliminary UI and replay concerns; retained findings distinguish
confirmed defects from assurance improvements and policy choices.

## 2. Sources Studied

| Source | Contribution | Limit |
| --- | --- | --- |
| [Delivery README](../../serve/delivery/README.md) | Declares admission, deterministic transitions, custody, checkpoints, acceptance, quarantine, and recovery | Documentation; behavior still to verify |
| [Ecosystem README](../../share/README.md) | Loading model and distinction between guidance and enforcement | Must compare actual frontmatter, hooks, and callers |
| [Earlier redesign research](agent-driven-delivery-redefinition.md) | Intent fidelity, semantic review, two-level acceptance, and semantic-first UI | Historical proposal; not current implementation authority |
| [Agent audit workflow](../skills/w-agent-audit/SKILL.md) | Evidence admission, loading-map analysis, signal quality, and drift criteria | Report-only procedure; user explicitly requested this research artifact |
| [Research workflow](../../share/skills/w-research/SKILL.md) | Source-grounded analysis and durable evidence boundaries | Does not authorize implementation |

## 3. Intended End-To-End Contract

The documented system is a deterministic control plane around agent reasoning:
user intent and Design authority -> admitted contract -> reviewed task plan -> bounded implementation
and exact-commit review -> whole-Change proof -> draft/ready publication -> user-owned pull-request
acceptance -> receipt-backed completed history.

Reliability requires both safety (no false completion, stale authority, or lost custody) and liveness
(a discoverable, bounded route from interruption or failure back to progress). A state that fails
closed but has no usable repair route is safe containment, not successful recovery.

## 4. Findings Register

Severity is relative to supervised delivery, not a measured incident rate. **High** denotes a credible
custody hazard, a core workflow dead end or unbounded failure loop, or a red verification gate.
**Medium** denotes bounded disruption with an operator workaround, or a material assurance/continuity
gap without demonstrated incorrect completion. **Low** denotes local wording or optional-policy debt.
Evidence type and trigger matter as much as the label. Implementation order also considers cost and
dependencies; an inexpensive Low correction can sensibly precede a larger High investigation.

| ID | Severity | Finding Type And Summary | Primary Owner |
| --- | --- | --- | --- |
| D02 | High | Conditional custody risk: live-worker expiry is not fenced | Engine custody/recovery and dispatch |
| D09 | High | Availability defect: unbounded remote Git paths | State publisher and startup loader |
| D13 | High | Workflow defect: wrong transition MCP argument | Orchestration skill and tool-envelope tests |
| D01 | High | Workflow defect: conflicting Design re-entry authority | Designer workflow and canonical Delivery docs |
| D06 | High | Liveness gap: no durable worker retry convergence budget | Runtime retry/acquisition |
| D04 | High, verification | Red serialization gate; production-wide failure not shown | Frontier model/consumers and regression tests |
| D03 | Medium | Scheduling defect: acceptance starvation beyond eight Changes | Acceptance scheduler and Cockpit feedback |
| D05 | Medium | Responsiveness defect: blocking foundational MCP handlers | MCP execution boundary |
| D07 | Medium | Assurance gap: semantically thin finalization context | Finalizer context and review procedure |
| D08 | Medium | Assurance gap: proof verdicts depend on agent interpretation | Evidence models and proof publication |
| D11 | Medium | Continuity gap: PR repair handoff is underspecified | PR-feedback workflow |
| D12 | Low | Wording defect: staged merge resolution called clean | Target-conflict workflow |
| D10 | Low | Policy coupling: optional housekeeping stops acquisition | Orchestration housekeeping policy |

### D01 - Design Re-Entry Has Conflicting Active Authority

**Severity:** High workflow defect. **Evidence:** Observed source and conflicting required guidance.
**Confidence:** High.

The engine explicitly permits revising an admitted package when the Change has returned to Design,
has a Design binding, and has no active claim, disposition, repair claim, or finalization:
[revision guard](../../serve/delivery/src/owlbear_delivery/portfolio_application.py#L3265).
The Designer's required workflow instead says not to revise an admitted package in place and that
semantic changes require a new or superseding Change:
[admission instructions](../../share/skills/w-design-session/SKILL.md#L248).
The [Delivery README](../../serve/delivery/README.md#L138) repeats the blanket prohibition.

**Failure path:** A legitimate runtime Design return reaches a Designer instructed to reject the
same-Change repair that the engine supports. This can strand work or needlessly fork its identity.
The engine's guarded revision path remains available; the defect is contradictory routing guidance,
not absence of readmission support. No full VS Code Designer journey was executed.
**Recommendation:** Choose and document one semantic re-entry contract. If current engine behavior
is intended, explicitly route quiescent returned Changes through revision, re-challenge, approval,
and readmission while preserving already-reviewed work only when carry-forward rules permit it.
**Acceptance idea:** Exercise plan/build -> Design return -> resumed Designer -> revised admission
-> resumed work, including concurrent-claim rejection and invalidated prior approval.

### D02 - Expiry Does Not Fence A Still-Running Builder

**Severity:** High conditional custody risk. **Evidence:** Observed recovery path; concurrent-agent consequence inferred.
**Confidence:** High on missing fence; no destructive live reproduction performed.

[Expiry](../../serve/delivery/src/owlbear_delivery/portfolio_application.py#L4399) uses only persisted
`started_at`; a subsequent acquisition automatically recovers expired claims. The default timeout is
one hour, but expiry is lazy: crossing that age does not independently interrupt a running worker.
The hazardous trigger is another acquisition while an expired Builder still runs, such as an
overlapping or restarted session whose earlier child has not stopped. A single sequential
Orchestrator waiting for its child does not create this overlap merely by exceeding the timeout.

There is no heartbeat renewal or worker-stop acknowledgement in this path.
[Dirty recovery](../../serve/delivery/src/owlbear_delivery/change_workspace.py#L2948) preserves a
snapshot and executes reset/clean before releasing custody. Exact claim validation rejects stale
publication, and quarantine preserves captured bytes; neither fences subsequent editor or terminal
writes. A stale worker could interfere with recovery or contaminate the replacement's work, even
though its own result cannot be promoted. Later review may catch that interference but is not writer
exclusion. Batch acquisition followed by
[sequential dispatch](../../share/skills/w-orchestration/SKILL.md#L40) also starts claim clocks before
later workers begin, increasing exposure if another acquisition occurs. Existing expiry tests prove
recovery of presumed abandoned work, not live-writer exclusion. The High rating reflects destructive
reuse under this specific trigger, not a demonstrated frequent incident.

**Recommendation:** Separate timeout suspicion from relinquishment. A minimal safe route is typed
attention until worker termination is established; automatic recovery can instead use an enforceable
writer fence or a reliable stop protocol. Renewal reduces false expiry but alone cannot exclude a
stale writer. Consider dispatch-time claims only if queued-age exposure remains relevant. Do not
require an OS sandbox or solve this by just raising the timeout.
**Acceptance idea:** A worker running past the lease boundary cannot write after replacement custody
is granted; queued launches do not expire before dispatch; genuine crashes still recover preserved bytes.

### D03 - Acceptance Reconciliation Starves Changes Beyond The First Eight

**Severity:** Medium scheduling defect. **Evidence:** Source plus successful in-memory reproduction.
**Confidence:** High.

[Batch selection](../../serve/delivery/src/owlbear_delivery/portfolio_application.py#L2406) sorts eligible
Changes and repeatedly takes `eligible[:8]` without a cursor or rotation. Eight open PRs retain their
eligibility indefinitely, so a ninth merged PR is never observed automatically. A probe using the real
selector and nine in-memory eligible runtimes observed Changes 01-08 twice; Change 09 returned
`ERR_DELIVERY_RECONCILIATION_LIMIT` twice. No provider or live state was involved.

[Cockpit reconciliation](../../serve/cockpit/web/src/hooks/useWorkItems.ts#L130) submits the complete
eligible set repeatedly; only `provider-unavailable` outcomes become visible errors. A manual exact
acceptance check remains a workaround, but normal automatic completion is not fair. This requires
more than eight eligible Changes and affects observation/history freshness, not whether GitHub can
merge the PR or whether an incorrect head is accepted. The defect is deterministic under that
fixture; its bounded scope and manual route support Medium severity for supervised use.
**Recommendation:** Keep bounded batches but rotate/cursor them and expose overdue/skipped observation.
**Acceptance idea:** With nine awaiting-merge Changes, the ninth is checked within two batches even
when the first eight stay open; provider failures and busy locks cannot monopolize every batch.

### D04 - The Current Serialization Verification Gate Is Red

**Severity:** High verification issue; runtime impact not established. **Evidence:** Executed tests.
**Confidence:** High.

The selected engine/MCP/Cockpit/ecosystem run reported **491 passed, 35 failed**. A representative
failure independently reproduced with `uv run pytest serve/delivery/tests/test_delivery_runtime.py::test_publication_history_refreshes_one_pr_and_appends_successors -q --tb=short -n 0`.
`DeliveryFrontier.model_validate_json(runtime.frontier_bytes())` rejects JSON arrays/datetimes under
the installed Pydantic 2.13 environment. The internal frontier reader explicitly uses `strict=False`,
and an isolated round-trip probe accepted the same JSON with `strict=False` while rejecting it with
`strict=True`. A four-file engine rerun reported **275 passed, the same 35 failed**. This is a
reproduced validation-contract problem, not 35 independently diagnosed defects, a demonstrated
production restart failure, or evidence of an upstream Pydantic regression. The root cause still
needs isolation before choosing between model, consumer, dependency, or test corrections.
**Recommendation:** Establish the canonical strict JSON round-trip contract, resolve the affected
model/consumer behavior, and restore a green required gate before relying on these recovery tests.
**Acceptance idea:** Current locked dependencies pass canonical frontier round trips, terminal receipt
round trips, restart/restore tests, and the affected integration assertions without weakening semantic validation.

### D05 - Foundational MCP Calls Block The Async Server Loop

**Severity:** Medium responsiveness defect. **Evidence:** Observed source. **Confidence:** High.

[Admission and reads](../../serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py#L311) and
[acquisition](../../serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py#L465) call synchronous
application code directly from async handlers. Admission reaches Git, locks, branch publication, and
provider operations. Other operations already use `asyncio.to_thread`. A slow foundational call can
therefore delay unrelated tool requests and cancellation handling on the same MCP event loop.
No concurrent MCP latency test was run; the source establishes the blocking boundary, not observed
service-wide outage duration. This can be a high implementation priority without High severity.
**Recommendation:** Apply one consistent blocking-call boundary, preserve lock semantics, and define
how a cancelled transport observes a possibly completed mutation before retrying it.
**Acceptance idea:** A deliberately blocked admission or acquisition does not block unrelated health
and status requests; cancellation followed by reconciliation never duplicates the mutation.

### D06 - Worker Retry Has No Durable Convergence Budget

**Severity:** High liveness gap. **Evidence:** Observed transition and dispatch contracts; repeated-loop consequence
inferred. **Confidence:** High.

[Runtime retry](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py#L3156) clears the active
claim/candidate and leaves the same work eligible. It retains no retry reason, failure fingerprint,
attempt budget, or next-eligible time in this transition. [Orchestrator](../../share/skills/w-orchestration/SKILL.md#L128)
continues acquiring and forwarding fresh workers. Local agent loop rules do not accumulate reliably
across those fresh invocations. A persistent local failure can repeatedly consume work without
progress, with the eventual stop determined by the host/session rather than Delivery policy.
Checkpoint retry counters and backoff exist, but govern checkpoint publication, not worker attempts.
Local loop instructions, explicit block/return routes, and user intervention mitigate this risk;
they do not impose a durable bound on a sequence of fresh workers returning retry. No long-running
failure loop was induced. High severity concerns repeated resource consumption without convergence,
not lost custody or false completion.
**Recommendation:** Persist failure identity and bounded retry policy at the engine/dispatch boundary;
distinguish transient backoff, local repair exhaustion, authority return, and operator attention.
Do not make a tool outage into a fabricated user decision or ask Orchestrator to reinterpret results.
**Acceptance idea:** Repeated identical worker failures converge to typed attention after a configured
budget while independent Changes continue; successful progress resets only the appropriate budget.

### D07 - Finalization Context Is Exact But Semantically Thin

**Severity:** Medium assurance gap. **Evidence:** Observed context and required procedure.
**Confidence:** High on the loading gap; missed-outcome frequency is unmeasured.

[DeliveryFinalizationContext](../../serve/delivery/src/owlbear_delivery/portfolio_application.py#L752)
contains heads, worktree, readiness, and publication identities, but no admitted promise, outcomes,
acceptance criteria, commitments, task results, or explicit diff baseline. The
[finalization workflow](../../share/skills/w-change-finalization/SKILL.md#L57) requires relevant checks
and independent exact-commit review, but does not explicitly require whole-Change acceptance coverage.
Its reviewer receives the same thin context. Prior task acceptance/review, maintained checks, and
manual source discovery are real safeguards. They do not guarantee assembled outcome coverage,
and the required procedure does not establish a reliable semantic loading path comparable to
Planner and Builder. A thin context is not itself a defect; the missing explicit connection to
whole-Change acceptance is the concern. No accepted-but-wrong Change was demonstrated.
**Recommendation:** Start with canonical source links and a required read of admitted acceptance
authority, plus a defined diff boundary. Require the existing finalizer/reviewer to explain coverage
of assembled outcomes and relevant preserved behavior. Avoid copying the whole Design package,
inventing a universal check list, or adding another reviewer role. Context expansion is justified
only where this smaller loading contract is insufficient.
**Acceptance idea:** All task tests pass but the assembled Product Promise is unmet; finalization
identifies that gap from supplied authority and routes it to the correct earlier boundary.

### D08 - Proof Verdicts Depend On Agent Interpretation

**Severity:** Medium assurance gap. **Evidence:** Source and schema-only executable probe.
**Confidence:** High on the schema boundary; no false completion demonstrated.

[DeliveryObservation](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py#L330) stores
`exit_status_or_artifact_locator` as an arbitrary non-empty string. With matching identities, the
canonical factories and `FinalizeDeliveryChange` accepted a command observation with value `1`.
[Finalization](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py#L2277) checks completed
tasks, authority ordering, and Change identity, not command success or coverage of required criteria.
This proves schema permissiveness, not that the normal workflow accepts a failed check. The
finalization workflow explicitly produces no request after a failed check and requires a passing
independent exact-commit review. Those are meaningful safeguards in this trusted-agent system.

The remaining gap is that a recorded result and its acceptance verdict are not distinguished, so
the engine cannot reject an accidentally contradictory pass submission. Receipt hashes establish
content integrity, not execution authenticity; adversarial attestation is not an established requirement.
Nor is every nonzero exit a failed observation: a negative test can deliberately expect that result.
**Recommendation:** If strengthening this boundary, distinguish command result, expected outcome,
explicit verdict, and artifact reference. Reject explicitly failed or unmet required proof; preserve
expected nonzero results and manual observations. Use D07 to establish acceptance coverage obligations
before expanding the schema. Keep semantic judgment with the existing agents and reviewer.
**Acceptance idea:** An explicitly failed observation cannot support finalization; an expected nonzero
result can pass when its expectation and evidence are recorded. Missing required proof is visible.

### D09 - Some Remote Git Operations Have No Time Bound

**Severity:** High availability defect. **Evidence:** Observed subprocess paths. **Confidence:** High.

Change-branch publication has a Git timeout, and the GitHub CLI provider has a timeout. In contrast,
[portable-state Git](../../serve/delivery/src/owlbear_delivery/delivery_state.py#L548) and
[startup Git](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py#L870) call
`subprocess.run` without a timeout; these paths include remote `ls-remote`, fetch, and push.
An unreachable/hung transport or credential helper can stall startup or checkpoint work while its
locks remain held. Retry/backoff cannot help until the original call returns. Combined with D05,
some stalls also block unrelated MCP traffic.
No hung remote was induced. Existing provider reconciliation and local crash replay still protect
identity/state; this finding is about bounded availability, not proof of unrecoverable writes.
**Recommendation:** Apply consistent bounded Git execution with noninteractive authentication,
typed read-timeout versus write-outcome-unknown semantics, and post-timeout remote reconciliation.
Reuse the existing bounded branch-publication pattern; do not introduce blind mutation retries.
**Acceptance idea:** Simulated hung remote reads/writes return within the configured bound; uncertain
pushes are read back before retry; sibling status/recovery remains usable.

### D10 - Non-Delivery Housekeeping Can Stop Healthy Delivery

**Severity:** Low policy coupling. **Evidence:** Documented active workflow. **Confidence:** High.

[Orchestrator Step 5](../../share/skills/w-orchestration/SKILL.md#L103) periodically invokes memory
curation. A tool-layer dispatch error stops acquisition after the current batch, whereas a child
internal failure permits continued acquisition. Thus healthy Delivery work depends on an optional
institutional-memory capability and the layer at which its failure is reported.
This is an explicit stop policy, not a broken state transition: the current batch is handled first,
failure is reported, and work remains available to a later invocation. It reduces convenience and
continuity without demonstrating a custody or completion defect.
**Recommendation:** Keep memory maintenance outside Delivery readiness/termination policy. Prefer the
existing explicit maintenance route or a non-blocking scheduled attempt; report its failure separately.
Preserve all active-claim handling before stopping for a genuine Delivery safety failure.
**Acceptance idea:** Missing curator capability does not stop independent claimable Delivery work;
the maintenance failure remains visible and does not trigger Delivery recovery.

### D11 - PR Feedback Repair Has An Underspecified Durable Handoff

**Severity:** Medium continuity gap. **Evidence:** Observed workflow contract; interruption consequence inferred.
**Confidence:** Medium.

[PR feedback repair](../../share/skills/w-address-pr-feedback/SKILL.md#L77) creates an internal thread
record, then stops for a separate finalizer invocation and later `mode=resume`. The output includes
classification, commit, and proof, but the workflow names no durable storage/reload contract for that
ledger. Source commits preserve repairs; GitHub preserves original threads. Neither necessarily
preserves the rationale for `no-change`, `duplicate`, or `stale`, the complete thread-to-commit map,
or whether an uncertain reply mutation already succeeded.
Same-chat output can carry the record, and a fresh agent can reconstruct some decisions from code
and threads. However, `resume` skips triage while requiring previously recorded decisions. The
missing reload/reconstruction contract can block a fresh session or cause repeated analysis/replies;
it is not evidence that repairs disappear or that threads were incorrectly resolved.
**Recommendation:** Define the smallest reliable handoff: name an existing durable record and reload
contract, or explicitly permit bounded evidence reconstruction when it is absent. Add a small
exact-PR/head-bound artifact only if existing storage is insufficient. Re-observe replies before
retrying an uncertain response. Keep external comments as evidence, not Design authority.
**Acceptance idea:** Resume in a fresh chat after repair, finalization, or a lost reply response;
retain classifications, do not repeat a repair, and do not duplicate a thread reply.

### D12 - Conflict Resolution Confuses Staged Resolution With A Clean Worktree

**Severity:** Low wording defect. **Evidence:** Conflicting procedural wording and executable preconditions.
**Confidence:** High.

[Conflict workflow](../../share/skills/w-target-conflict-resolution/SKILL.md#L47) asks for a
clean-worktree check after staging, before the engine creates the merge commit; its pitfalls also
say the worktree must be clean before that commit. Resolved staged changes normally make Git status
nonempty. The [engine](../../serve/delivery/src/owlbear_delivery/change_workspace.py#L2505) correctly
requires no unresolved paths and no unstaged/untracked changes before committing, then requires a
fully clean worktree afterward. Literal adherence to the skill can stop a legitimate resolution.
The engine has the correct safeguards and an experienced agent may interpret the wording correctly;
there is no demonstrated incorrect merge. The wording still deserves a small, direct correction.
**Recommendation:** Name these two different preconditions and their timing precisely. Preserve the
engine-owned commit, parent checks, and fresh-finalization handoff.
**Acceptance idea:** A staged resolved conflict passes preflight, the engine commits it, and only then
must full Git status be empty; unstaged/untracked or unresolved content still blocks.

### D13 - Orchestrator Forwards The Wrong MCP Argument Name

**Severity:** High workflow defect. **Evidence:** Required workflow, source schema, and live tool schema.
**Confidence:** High.

[Orchestrator Step 3](../../share/skills/w-orchestration/SKILL.md#L68) instructs calling
`transition_delivery` with the worker mapping as `request`. The registered tool and
[TransitionDeliveryParams](../../serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py#L729)
require `transition`; the adapter then passes `params.transition` to the application. `request` is
the Python adapter method's local parameter, not the flattened MCP argument. A schema-following
model may compensate, but literal workflow execution is invalid. The workflow's schema-error route
can then recover a valid worker claim instead of promoting its completed result.
An in-memory strict-model probe accepted the `transition` envelope and rejected `request` with
`transition: missing` and `request: extra_forbidden`; no live transition was called.
**Recommendation:** Align the workflow with the registered MCP envelope and test a representative
serialized worker handoff through the real tool schema. Keep the worker mapping itself unchanged.
**Acceptance idea:** Planner and Builder pass results reach `transition_delivery(change_id,
transition=...)` unchanged; wrong-envelope errors are caught before claim acquisition/dispatch.

### Verified Strengths And Rejected Leads

- Acceptance checks bind repository, PR number/node, target branch, and exact finalized head;
  completion replay reads the existing durable receipt inside the checkpoint lock:
  [acceptance owner](../../serve/delivery/src/owlbear_delivery/portfolio_application.py#L2528).
- Checkpoint publication has a live-host retry supervisor, rather than relying only on a user retry:
  [supervisor](../../serve/delivery/src/owlbear_delivery/checkpoint_supervisor.py#L65).
- Provider-unknown draft-state writes are followed by provider reads; exact replay and generated-summary
  preservation have dedicated tests. Do not replace this with blind retries or a second receipt scheme.
- Transaction participants use content validation, immutable/replacement semantics, durable manifests,
  filesystem locks, and fsync; interrupted local publication is explicitly replayable.
- Current Cockpit includes dedicated Design rows/details, unavailable-runtime handling, stale-data
  warnings, and acceptance-provider retry controls. Earlier research is not proof these are missing.
- Ordinary bounded polling lag is not loss of lifecycle evidence. Do not add faster polling or
  streaming merely to make every transient state visible.
- Preliminary claims of missing acceptance head checks, missing completion replay, missing Design
  rendering, unreaped `subprocess.run` children, and permanently held OS locks were rejected.

## 5. Coverage And Verification

- Initial Git status was clean; audit baseline recorded above.
- The advertised `.owlbear/instructions/research-docs.instructions.md` is absent from the checkout.
  The available research workflow is used instead; no missing-file content is assumed.
- Prior research was located and sampled; retained historical claims were checked against current code.
- Four read-only component reviews were used as leads. Their claims require direct verification;
  unsupported findings and historical defects contradicted by current source are excluded.
- Focused engine, MCP, Cockpit backend, and ecosystem run: 491 passed, 35 failed. Representative
  serialization failure reproduced directly; failure-family counts are recorded below.
- Nine-Change in-memory acceptance-selection probe passed its starvation assertions.
- Corrected schema-only probe accepted command exit text `1` with valid finalization identities.
  Its first attempt correctly failed an identity mismatch, which was corrected before interpreting results.
- Additional admission revision, draft-PR, GitHub provider, and supervisor tests: **107 passed**.
- Frontend portfolio/polling unit tests: **105 passed** using the maintained npm script after VS Code's
  test adapter found no frontend tests. Assembled Delivery browser suite: **22 passed**, including build,
  desktop/mobile, focus restoration, history, route refresh, and dismissal checks in a temporary workspace.
- Desktop and mobile screenshots from that browser run were inspected; no obvious overlap was observed.
- Agent/skill/prompt validators exited successfully; agent and prompt output reported 13 and 19 files.
- Live MCP `delivery_health()` returned `healthy` with no diagnostics. This is a point-in-time health
  observation, not proof of absence of latent defects or of behavior at a different deployed revision.
- Source registry contains **52 MCP operations**. Live `transition_delivery` schema agrees with the
  source `transition` field and exposes the workflow mismatch in D13.
- The 35 initial failures all report Pydantic ValidationError: runtime (8), portfolio application (13),
  Delivery state (13), checkpoint regression (1). They are not 35 independently diagnosed defects.
- Completed source coverage includes admission/readmission, claims/recovery, transitions, local
  transactions, portable state/bootstrap, publication/acceptance, MCP models/handlers, GitHub provider,
  core Delivery workflows, advanced repair skills, Cockpit service/projections/hooks/components,
  and representative invariant/unit/browser tests. Full bodies were read for core/repair workflows
  and selected roles; large engine/UI modules were read at controlling paths, not exhaustively.
- Across the two non-overlapping Python selections: **598 passed, 35 failed**. The independent
  four-file engine rerun returned **275 passed, 35 failed**; these overlap the initial selection and
  are not added to that total. The strict/non-strict round-trip probe isolated validation behavior,
  not its ultimate cause. Frontend and browser totals are separate and were not rerun for prose edits.
- Report validation: 31 local Markdown links resolve; stable finding IDs D01-D13 are present;
  editor diagnostics are clear. The non-mutating Markdownlint pre-commit hook could not initialize:
  Node environment download failed TLS certificate verification. No TLS checks were bypassed and
  no globally installed Markdownlint executable was available.
- Git checks retained the baseline commit. The audit document is untracked; unrelated source-index
  edits and a separate browser audit were present during validation and left untouched. Maintained
  browser tests generated normal ignored build/test outputs and used temporary fixture state.

## 6. Big-Picture Assessment

**Verdict:** Delivery is a substantial, thoughtfully bounded supervised delivery system, not merely
an agent prompt chain. Its strongest feature is exact authority/custody/publication provenance. Its
weakest area is bounded progress across agent, transport, and recovery boundaries. It can reach its
intent on supported paths, with substantial executable evidence and meaningful human/agent review
safeguards. Concrete workflow contradictions, conditional writer-reuse risk, and availability gaps
still warrant repair. Proof semantics and fresh-session continuity warrant targeted strengthening,
not a claim that current reviews or receipts provide no value. Unattended operation under arbitrary
interruption is neither established by this audit nor assumed to be the product's present promise.

These are qualitative ratings of the audited design, not measured reliability percentages:

| Dimension | Rating | Judgment |
| --- | --- | --- |
| Intent and semantic authority | Strong foundation | Manifest-bound Design, approval, outcomes, and carry-forward exist; D01 breaks the prescribed re-entry path. |
| Local state integrity and replay | Strong foundation; verification caveat | Content checks, CAS, transactions, fsync, exact receipts, and preserved refs earn their complexity. The red strict-serialization gate limits verified confidence; the internal permissive reader works in the probe. |
| Worker safety and liveness | Needs strengthening | Exact claims and quarantine protect important boundaries; overlapping acquisition can reclaim an unfenced writer, and fresh-worker retry has no durable convergence limit. |
| External publication identity and replay | Strong foundation | Provider reconciliation, generated-summary preservation, exact PR identity, and user-owned merge are coherent. This rating does not cover transport availability. |
| Outage behavior and fairness | Needs strengthening | Unbounded Git operations, uneven async boundaries, and the eight-item starvation defect undermine progress. |
| Proof of user value | Mixed | Task ACs, failed-check stop rules, and independent reviews are valuable. Whole-Change acceptance loading is incomplete; proof verdicts remain agent-interpreted, not evidence of observed false completion. |
| Cockpit interaction quality | Strong tested baseline | Current Design/Delivery/history, recovery controls, responsive layout, and focus behavior have executable browser proof. |
| Operator diagnosis and recovery | Mixed | Rich typed state and precise actions exist, but some advanced recovery remains prompt-only and progress/freshness guarantees are not summarized. |
| Complexity and maintainability | Mixed | Most authority boundaries are justified; mechanical obligations and cross-layer mirrors expose too much detail to agents and maintainers. |

### Effective End-To-End Ownership

| Step | Semantic owner and required loading | Deterministic owner | Human/operator boundary |
| --- | --- | --- | --- |
| Ideate and Design | Designer -> `w-design-session`; conceptual and Design challengers | Package store, compiler, admission registry | Material choices and final admission approval |
| Plan | Planner -> `w-frontier-planning`; planner-challenger | Exact launch, task validation, candidate promotion | Requests or Design return for missing meaning |
| Build | Builder -> `w-packet-building`, governance, orientation; build-reviewer | Worktree/claim custody, result validation, reviewed boundary | Bounded request; no silent scope expansion |
| Dispatch and recover | Orchestrator -> `w-orchestration` | Portfolio acquisition, transitions, exact recovery | Typed unresolved attention; not reviewer prose |
| Finalize | Finalizer -> `w-change-finalization`; build-reviewer | Head/cleanliness checks, canonical receipts, checkpoint obligation | User invokes finalization; no automatic target merge |
| Publish and accept | Engine/publisher; Cockpit controls | Change branch, draft PR, checks, ready receipt, exact merged observation | User owns PR ready/merge decisions |
| Repair | Attention, PR-feedback, and target-conflict skills | Exact repair/adoption/sync/cleanup operations | Explicit decision and confirmation for material/destructive remedies |
| Retain history | Completed-history catalog and Cockpit | Receipt-backed completion and retained branch/worktree policy | Completion is observed merge, not deployment or production success |

### Capability Inventory

| Capability | Present? | What Is Still Needed |
| --- | --- | --- |
| Durable intent, design, explicit admission | Yes | Align supported readmission with Designer instructions. |
| Task planning, dependencies, independent challenge | Yes | Preserve semantic rigor without lexical or format-driven inflation. |
| Task execution, exact review, maintained proof | Yes | Consider explicit expected-result/verdict semantics; execution attestation is not an established requirement. |
| Whole-Change finalization | Yes | Reliable loading of admitted acceptance and assembled-workflow coverage, initially through source links and procedure. |
| Claims, abandoned-work preservation, cleanup | Yes | Establish writer termination or exclusion before reuse; bound repeated worker failure. |
| Requests, blocks, defer/resume/abandon | Yes | Keep these distinct from transient infrastructure failures. |
| Draft publication, user-owned acceptance, history | Yes | Fair acceptance scheduling and consistent time bounds. |
| Head drift, external adoption/promotion, target conflicts | Yes | Clearer guided routes and precise pre/postconditions; not a missing integration agent. |
| Remote checkpoint recovery | Yes, checkpoint-based | Publish explicit recovery-point/recovery-time expectations and periodically prove fresh-clone restoration. |
| End-to-end operational telemetry | Partial | Last progress, last external observation, next retry, retry reason/count, oldest pending work, and degraded supervisor state. |
| Cross-session PR repair continuity | Partial | Explicit reload or reconstruction of thread decisions, plus reply reconciliation. |
| Production rollout/rollback and post-merge verification | Outside current contract | Decide explicitly whether Delivery stops at merge; do not silently redefine completion as deployment success. |

No additional general-purpose planner, builder, reviewer, or integration agent is required to fix
the identified gaps. Add capabilities to their existing owners first. An autonomous recovery agent
would be premature while the underlying safe recovery contract still has D02/D09 gaps.

## 7. Where To Deepen Or Reduce

### Deepen

- **Reliability contract:** Define bounded time to attempt/retry/attention and a maximum recovery
  point for published state. Distinguish safe containment from restored progress.
- **Adversarial system proof:** Exercise interruption between durable steps, live-worker expiry,
  slow Git/provider calls, more than eight pending acceptances, schema round trips, and new-chat
  semantic re-entry. Run these through normal boundaries with replacements below the boundary.
- **Outcome traceability:** Link promise -> outcome acceptance -> task evidence -> whole-Change
  observation -> merged receipt using existing authority first. Do not require a new schema for
  every link. Keep the operator summary small, with exact evidence drill-down.
- **Operational visibility:** Extend existing health/portfolio views with last successful observation,
  overdue work, retry reason/next retry, and a specific recovery owner. D03 shows why a healthy
  endpoint and a waiting row alone do not prove automatic progress.
- **Recovery rehearsal:** Test process restart and a fresh clone using published package/state
  branches. Explicitly distinguish locally preserved rejected/quarantined bytes from remotely
  recoverable checkpoints and unadmitted drafts.
- **Review quality evaluation:** Use a small set of technically-valid-but-wrong candidates to measure
  whether existing reviewers find real defects. Structural validators cannot establish this.

### Reduce Or Consolidate

| Surface | Disposition | Evidence And Conservation Boundary |
| --- | --- | --- |
| Agent-authored receipt mechanics | Move behind an existing engine/tool boundary where practical | Builder and finalizer import factories, assemble receipts, serialize them, and forward nested envelopes. D13 is a concrete wiring defect; D08 is an interpretation boundary, not proof hashing failed. Retain exact IDs, commit binding, independent review, replay, and evidence. |
| Optional orchestration housekeeping | Move or make non-blocking | Step 5 is about 223 words, loaded by one regular consumer, and can stop Delivery. Remove that dependency without weakening claim cleanup or Delivery error reporting. |
| AC quantifier word ban | Compress | The B3 block is about 61 words plus validation-table references. It bans seven common words unless exhaustively enumerated. Prefer explicit testable scope, including canonical-set references, over lexical rewriting. Keep boundary, concrete input/output, and falsifiability. |
| Large application ownership | Consolidate behavior behind small private responsibilities, not another framework | `portfolio_application.py` is 5,190 lines and mixes scheduling, proof, provider reconciliation, health, history, and operator recovery. The concrete cross-layer defects justify improving locality, not a line-count-driven split. |
| Transport/UI contract mirroring | Derive/check mechanical mirrors | MCP has 52 operations, a 993-line model module, and a 1,061-line adapter. Several calls use different async wrappers; the agent envelope drifts. Generate/check schemas and representative call envelopes before adding more prose. |
| Detailed operator machinery | Keep available, hide until relevant | Current collapsible technical/lifecycle detail is useful. Do not flatten distinct heads, disposition IDs, adoption versus promotion, or destructive confirmation into a generic Repair button. |
| Phase-specific independent review | Keep | Design, task planning, exact task result, and finalization ask different questions. Reduce repeated mechanical narration, not independent semantic judgment. |
| PR feedback commit granularity | Reconsider when evidence warrants | One commit per independent thread is precise but may overconstrain tightly coupled repairs. Prefer coherent independently provable fixes with thread mappings; duplicates are already handled. This is an option, not a confirmed defect. |

Measured text sample: nine Delivery-related agent files plus five core workflows and the challenger
protocol total **13,158 whitespace-delimited words**. This is not one invocation's prompt size and
excludes transitive/contextual loading. The Builder agent/workflow pair is 2,619 words before its
other required readings; Designer's pair is 2,917; Orchestrator's pair is 1,801. Size alone is not a
finding. Keep custody triage, exact identity, clean-head rechecks, user choices, typed failure routes,
and independent review even when compressing their explanation.

## 8. Suggested Follow-Up Order

These are research-to-planning candidates, not admitted tasks or authorization to implement.

1. **Repair concrete contract mismatches:** D13 transition envelope, D01 Design re-entry, D12 staged
   conflict preconditions. Add normal-boundary workflow/tool tests; the structural validators alone
   passed despite these conflicts.
2. **Restore a green serialization gate:** D04. Establish model behavior under the locked environment
   before relying on the failing restart/completion assertions as release evidence.
3. **Close execution safety and progress gaps:** D02 worker fencing, D09 bounded Git, D05 async
   responsiveness, D03 fair acceptance, D06 retry convergence. Keep each change independently testable.
4. **Strengthen whole-Change assurance:** D07 source-linked acceptance loading and coverage, then D08
  explicit proof verdicts where useful. Define minimal obligations before expanding schemas; retain
  expected negative-test results and the current independent review safeguards.
5. **Improve recovery continuity and simplify:** D11 PR handoff, D10 housekeeping isolation, operator
   freshness/next-action indicators, then measured mechanical-text and adapter consolidation.

For each selected finding, retain its stable ID, trigger, affected authority, intended observable
outcome, current safeguard, and negative scenario. Do not turn the complete audit into one large
rewrite or a task per source file.

## 9. Confidence And Limits

High confidence in the cited code/procedure mismatches, the reproduced batch starvation, the
canonical observation schema behavior, and the reported test results. Concurrent live-writer harm,
unbounded network stalls, and fresh-chat continuity failures are source-grounded risks, not incidents
induced against this user's workspace. Schema acceptance of result text `1` demonstrates no execution
verdict enforcement; it does not demonstrate false finalization. Severity is engineering judgment
based on triggers, safeguards, and supervised use, not observed frequency or agreement among reviewers.

Coverage is broad end-to-end and deep at selected authority/failure boundaries, not a line-by-line
review of every Delivery function or a formal state-space proof. Component review reports were
used as navigation only where their claims survived direct checking. No live GitHub mutation,
real worker termination, host-loss test, multi-machine race, or full VS Code agent journey was run.
The assembled browser suite uses an isolated seeded workspace; it does not prove a live agent's
semantic judgment or real remote recovery. Green live health does not contradict latent defects.

All source, agent, skill, configuration, and live Delivery authority remain unchanged. Only this
requested research document is intended as the persistent audit change. No implementation plan was
admitted, no live claims acquired, and the repository HEAD was not changed. Findings are task-specific
research, not institutional memory; no memory entry was created.
