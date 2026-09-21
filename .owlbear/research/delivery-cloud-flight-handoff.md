# Delivery Cloud Execution Guide

## Agent Start Here

Read this section and **Common Rules** in full. Then read **only the requested Action** and
**the matching Package section**. Follow their links into the programme and source as needed;
do not load every package, the entire programme history or previous chats by default.

- `D04-P` means plan package D04; `D04-A` means implement its A phase. IDs are case-insensitive.
- `Review D04-A`, `Repair D04-A` and `Resume D04-A` select the corresponding action, not new work.
- A phase ID without an action means **Plan** for suffix P and **Implement** for other suffixes.
- H is host-only: do not execute `D08-H` in a cloud session.
- The only user-supplied work selector is the phase ID. Discover the repository/PR context,
  revisions, package plan, source paths and commands yourself. Ask for a PR link only if the
  intended PR cannot be identified; never ask the user to retrieve hashes or assemble a test command.

| Read | Purpose |
| --- | --- |
| [Common Rules](#common-rules) | Scope, safety, cloud tools, verification and handoff. Always read. |
| [Actions](#actions) | Read Plan, Implement, Review, Repair or Resume as selected. |
| [Packages](#packages) | Read only D03, D04, D05, D06, D07 or D08 matching the ID. |
| The selected package plan | Plan: reuse if present. Review/repair P: inspect the proposed plan. Implementation: approved specification and prerequisite progress required. Resume: use the interrupted action's requirements. |
| [Operator Quick Start](#operator-quick-start) | Human launch/approval instructions; not additional agent work. |
| [References](#references) | Consult only for a platform or tool question. |

## Common Rules

### Scope and Authority

Repository: **maba-pag/owlbear**. Package order: **D03 -> D04 -> D05 -> D06 -> D07 -> D08**.
Verify the requested package's prerequisites and current phase in published source, its package
record and the PR. Reuse completed work; neither this guide's examples nor an old handoff determines
what remains to do. Resolve stale or contradictory progress against the actual commits and reviews.

The [Delivery programme](change-continuation-delivery-redesign.md) owns product requirements and
acceptance. This guide owns the cloud execution procedure, not product status. Read the programme's
current execution status and direct-development decision, common user requirements in section 1,
and the WP/P/V sections named by your Package. Search section 0 for the selected package's current
handoff or unresolved prerequisite; do not load its entire historical progress record. Follow a
historical reference only when it resolves a concrete contract question.
Follow applicable repository instructions and coding conventions; read them as repository files.

Use GitHub's normal cloud branch, commit and PR publication. New package planning starts from the
selected `dev` checkout and opens one draft package PR targeting `dev`. Subsequent phases run on
that PR through PR comments; do not start another task from `dev` for each phase. A reviewer may
use a separate read-only session with the PR attached. Run one writer at a time. No automatic
successor dispatch, cross-package work, merge or changes to repository protections.

For a user-requested cloud job, this cloud procedure replaces the local direct-`dev`/user-only-push
procedure. Publication is part of the cloud job; no special local commit helper is required.
Do not execute native Delivery admission/claim workflows to develop Delivery. Do not alter the
main programme, this guide, shared governance or another package's files to bypass requirements.
The integration owner updates programme status after the package is reviewed and merged.

Only work with disposable test state and synthetic inputs. Do not modify live Delivery records,
configure/start OwlBear MCP services, access company credentials/browser profiles, run real provider
mutations in tests, or activate a release. No timeout, diagnostic retirement or caller assertion
is proof that a worker has stopped. Approval to implement is not merge, privacy or destructive-action
approval. Leave genuinely new product/safety decisions to the user; resolve ordinary code defects.

### Cloud Tools and Verification

Use available read/edit/shell/platform tools. VS Code APIs, language servers, tool discovery,
OwlBear memory and nested agents are not prerequisites. Read skills as files, not by launching
claim-dependent custom agents. Do not repeatedly try unavailable tools or request wider credentials.

**Never install or run MegaLinter in an agent session**, including `uv run megalint`,
`uv run quality`, `npx mega-linter-runner`, its container/image, or any wrapper that invokes it.
Use scoped check-only tools; avoid broad autofix/pre-commit aggregates. Existing external CI remains
responsible for its own checks. Do not disable checks or edit their policy to make a PR pass.

Resolve commands from current manifests and nearby tests, not assumptions about installed binaries.
Use `uv run --locked` for Python and locked npm dependencies for the frontend. Start with one pytest
worker in constrained runners. Install only needed locked tooling. Do not run workspace initialization
to set up a cloud test environment.

| Changed behavior | Available proof route | What it cannot prove |
| --- | --- | --- |
| Core state/custody/replay | Owning pytest suites; temporary repos, clocks, controlled processes and provider fakes below real owners. | Actual laptop/VS Code worker liveness. |
| MCP registration/arguments/results | [Registered-tool tests](../../serve/delivery-mcp/tests/test_target_server.py) use `Client(assemble_target_server(...))` in-process; [adapter tests](../../serve/delivery-mcp/tests/test_delivery_adapter.py) exercise strict mapping. No daemon or agent MCP binding needed. | Host discovery and external stdio/remote transport. |
| HTTP behavior | [Cockpit route tests](../../tests/test_cockpit_work_items.py) use the in-process test client and disposable fixtures. | Deployed service operation. |
| UI logic/types | [Frontend scripts](../../serve/cockpit/web/package.json): scoped tests, type/build checks and the current package-owned linters. Resolve commands from the checked-out manifest. | Real geometry, focus or browser security from jsdom alone. |
| Browser interaction | `npm run test:e2e:work` uses [a disposable fixture server](../../serve/cockpit/web/e2e/support/start-work-portfolio-stack.mjs). Browser MCP is not needed. Inspect and clean up the harness's temporary resources. | Managed macOS authentication or live activation. |
| Agent/prompt contracts | [Ecosystem tests](../../tests/test_agent_ecosystem_validation.py) plus actual schema/adapter tests. | Real host dispatch and independently selected model execution. |
| Static validity | Explicit owned paths with `uv run --locked ruff check`, `ruff format --check`, frontend build/direct linters, and document link checks. | All checks included in external CI/MegaLinter. |

### Execution Budget

Classify proof as **cloud-required**, **external CI**, or **host-only** and minimize execution cost
without weakening its assertions. These rules apply to every phase, including D08 integration:

- **Never run the whole OwlBear test suite in an agent session**, directly or through an aggregate.
   Select explicit tests; no bare repository-wide pytest or full-workspace test command.
- Inner loop: run the smallest test/node/filter covering the changed behavior immediately after
   the first substantive edit. Add neighboring tests or direct-consumer cases only for a concrete
   regression risk. A whole file or module is not the default after each edit.
- Closeout: if broader regression is justified, run it once near the end, limited to affected
   modules and necessary consumer checks. A module-wide run is a ceiling, not a mandatory gate.
   After a repair, rerun failed and impacted checks; repeat broader proof only if that repair invalidates it.
- Apply the same discipline to builds, typechecks, lint, browser runs and dependency setup. Prefer
   scoped/incremental commands; reserve an indivisible package build for changes that need it and avoid
   repeating successful expensive steps on unchanged inputs. Do not reinstall unchanged dependencies.
- Before a costly command, check its scope and likely duration against the remaining session budget.
   Use prior measured duration when available. Split necessary proof into bounded selections or record
   it for external verification rather than launching a command unlikely to finish with handoff time left.
- Reuse recorded proof only when relevant source, dependencies, fixtures and configuration remain valid;
   label it as prior evidence, not a fresh run. Never rerun suites merely for reassurance or a new session.

"Cumulative package proof" means coverage of the package's affected contracts across phases, not
the entire repository. Track which evidence remains valid and run the missing affected checks.
External CI retains its required broad gates. Real test/build/lint failures need repair or an explicit
unresolved defect; do not add skips, weaken assertions or relabel them as resource limitations.

Missing MCP/editor/MegaLinter is expected. If another needed capability is unavailable, perform one
bounded diagnosis, record the affected check, reason, available proof and follow-up environment/owner,
then continue supported work. Do not claim unrun checks passed. If core behavior cannot be tested,
publish an explicitly unverified checkpoint; if reading/editing/publication is impossible, report that
specific blocker. Missing an optional capability does not invalidate all work on the package.

### Package Record and Approval

Each package has one committed plan: `.owlbear/research/delivery-cloud-dNN-plan.md`, using the
lowercase package ID, for example `delivery-cloud-d04-plan.md`. Reuse the existing package record
when present. Keep one current specification and concise progress, not a chronological diary.
Git history and PR discussions retain superseded details.

The plan must contain:

1. **Contract:** concrete result, relevant programme requirements, invariants, interfaces/error cases,
   existing owners to reuse, explicit exclusions and unresolved decisions.
2. **Phases:** exact IDs, dependency order, editable paths, required exports/consumer companions,
   positive/negative scenarios and runnable proof commands. Separate narrow inner-loop checks from
   justified closeout checks, with expected runtime where known. For each phase, assess complexity/
   uncertainty and impact if wrong to choose proof boundaries and identify unresolved decisions.
   Use Model Selection below for the actual next action, not a permanent expensive-model assignment
   attached to the phase ID. Keep tests with the behavior they prove.
3. **Progress:** for each phase, implementation revision, actual proof, review reference and remaining
   work. Keep specification approval separate from worker-written progress.
4. **Verification gaps:** check/claim, reason unrun, evidence available, responsible environment and
   whether the gap blocks a successor, package merge or only final host acceptance.

Discover revisions and PR metadata from the checkout/platform. Record the distinction between
checkout head and PR comparison base; do not invent unavailable metadata. No user hash entry is
required. Use the actual invocation's PR, not an assumption that only one PR exists in the repository.

Planning alone does not authorize implementation. An explicit implementation request authorizes
the named phase against the package plan currently presented on that PR; unresolved listed decisions
are not implicitly approved. Resolve and record that plan revision yourself. If specification changes
after presentation make the request ambiguous, ask about the concrete change, not for a hash.
Later workers may update progress but must not rewrite approved semantics to fit their implementation.

Within a package, advance only after prerequisite code, cloud-required proof and independent review
are present on the same PR branch, with findings addressed. Any external gap that invalidates the
successor's safety contract blocks that successor. Between packages, require the predecessor's code
PR merged into `dev` with required checks/reviews satisfied. Host checks expressly assigned to D08-H
remain pending; their absence must not be reported as full product acceptance or silently waived.

### Model Selection

**Default to GPT-5.6 Luna Max for planning, implementation, review, repair and resume.** Settled
requirements, existing patterns and clear acceptance criteria do not need a larger model merely
because the action is called planning or review. High impact requires strong proof, not automatic
model escalation. A precisely diagnosed safety defect with a defined repair/test boundary can be
Luna work. This cloud staffing policy replaces model preferences elsewhere, not product requirements.

| Select | When it earns the additional cost | Complete PR mention |
| --- | --- | --- |
| GPT-5.6 Luna Max | Default, including source-grounded planning and independent review against explicit criteria. | `@copilot+gpt-5.6-luna:max` |
| Claude Opus 5 | An additional perspective is needed on ambiguous acceptance, cross-component safety interactions or consequential final review. Name the unresolved claim it must assess. | `@copilot+claude-opus-5` |
| GPT-6 Astra | Novel architecture or cross-cutting contracts require broad synthesis and a material trade-off cannot be resolved from the approved plan/current owners. Scope it to that decision, then return bounded work to Luna. | `@copilot+gpt-6-astra` |

These mention forms have been supplied by the user or observed in this repository's PR workflow.
Do not invent depth suffixes. Other models/depths, including Sol, need an exact GitHub-generated
selector and a concrete benefit for this task; do not make them mandatory escalation steps.
Respect the user's selected model. A recommendation cannot switch the running session's model.

Do not escalate solely because of a phase letter, a risk label, a timeout, a test failure or review
findings. First narrow the current task and use its evidence. Recommend a larger model only with
one concrete unresolved decision or demonstrated reasoning gap and why the extra review/reasoning
would help. Exact cost ratios and benchmark equivalence are not assumed. Repair/resume starts with
Luna unless the remaining work meets that escalation test; it need not inherit the previous model.

Independent review still uses a separate read-only worker, not the implementer's self-check. Luna
may review Luna-produced work against well-defined criteria; different-family Opus review is useful
where the stated risk or ambiguity warrants it, not compulsory for every phase. Preserve any
explicit task-specific review requirement until changed by the user. No model choice waives tests,
acceptance, unresolved findings, required human approval or exact-revision review.

### Session End and Recovery

Target 30 minutes of coding and 15 minutes of proof/handoff; stop new implementation by minute 35
and finish by minute 50 inside the platform's 59-minute limit. These are soft working targets.
Publish coherent checkpoints early through the platform; unpushed work may not survive interruption.
If a phase is too large, checkpoint it and continue that phase in another session. Never trim safety
or proof to fit the clock. Split an oversized PR only at a reviewed coherent boundary.

End with the phase, observed code revision, actual checks, unresolved findings/gaps and **one complete
next request in a `text` code block**. Start the request with the exact model-qualified mention from
Model Selection, then the action, actual phase ID, this guide's path and necessary PR/review context.
Default prefix: `@copilot+gpt-5.6-luna:max`. Never output a bare `Repair D03-C ...`, plain `@copilot`,
a model placeholder, or a separate model recommendation in place of a usable command. No hashes,
paths or model names should need manual assembly. If escalating, explain why outside the block,
but still put the selected model's complete mention inside it.

Choose the next action from evidence: partial work -> Resume the same phase; unresolved review
findings -> Repair that phase; ready candidate -> Review; reviewed prerequisite -> propose only the
next phase defined in the package plan. Include the review/report link if not already readable on
the PR. A genuine unresolved user decision needs a precise question, not a command that presumes
approval. If the package is ready for human merge, state that instead of inventing another agent job.

Keep the package progress and PR summary aligned with the published result, replacing obsolete
"plan only" or "no implementation" claims as work advances. Do not append a session-by-session
transcript. Use plain status: ready for review, partial, or blocked, with external gaps explicit.
The next request is a recommendation only; it does not dispatch, grant approval or start a successor.

On interruption, inspect published commits, the package record and actual test/review evidence.
Preserve good work. Do not restart the package or assume success from a missing response. Repair
bad changes from the last good checkpoint; obtain explicit approval before discarding prior work.
After any code change, rerun affected proof and review the changed candidate.

## Actions

Read the selected action only, together with Common Rules and the matching Package.

### Plan

Suffix P. Use the Package's source anchors and programme sections to find the controlling owners.
Verify its predecessor is complete in published source; reuse completed work in this package.
Do not execute a predecessor's unfinished work or choose another package. Identify a missing
dependency precisely while preserving any useful planning result.

Research enough to settle the next coherent contract and falsifiable proof. The Package's phase
table is an initial split, not sufficient authority for implementation. Resolve concrete paths,
interfaces, transaction boundaries and test oracles in the package plan. Revise the split if needed,
preserving all requirements and explicit phase dependencies; don't create speculative frameworks.
Identify genuinely unresolved design decisions separately from straightforward decomposition of
settled requirements; apply Model Selection to the decision rather than all planning work.

Create/revise only the package plan and required source attribution, open/update the package draft
PR targeting `dev`, and stop. No product edits. Present only genuine user decisions and the first
implementation request. Do not plan unrelated packages or update the programme status.

### Implement

Suffix A, B, C, etc. Read the package plan's approved contract, requested phase, prerequisite
progress and latest review. If the plan is absent, do not guess implementation scope: request the
package's P phase. If a phase is undefined, ask for the intended phase rather than selecting one.

State the narrow behavior hypothesis and first discriminating check, then implement in the owning
abstraction using current patterns. Keep required schemas, exports, tests and minimal consumer
companions together so the result is usable. Stay inside the phase; resolve local defects, but
stop for a genuinely new product/safety decision. Apply Common Rules' focused verification.

Publish the result to the existing package PR, update its plan's progress/gaps, and request review
of this phase. Even when another phase is ready, stop until explicitly instructed to start it.
On the final implementation phase, cover missing affected contracts within the Execution Budget
and request cumulative review; do not interpret cumulative proof as a whole-project suite run.

### Review

Read-only review of the named phase on the supplied PR. For P, assess the proposed plan against
current source and programme requirements: complete scope, feasible dependencies, concrete contracts,
bounded phases, discriminating tests and cloud capability limits. Planning review precedes approval;
do not demand an approved plan or implementation tests for code that does not yet exist.

For an implementation phase, read its approved contract, real diff, owning code/tests and proof
results; do not treat the implementation summary as verification. Review the phase's interaction
with prior phases; on the final phase, review the cumulative package.
Record the actual base/head and whether tests were run by you, reported by another worker or unrun.

Prioritize correctness, data preservation, custody, stale approvals, replay, privacy and missing
discriminating tests. Report severity and actionable source references, or no findings with limits.
Expected absent cloud tools alone are not findings. No edits, fix commits, PR approval or merge.
A new reviewer session is preferred; PR-thread context reuse must not be called context isolation.
If PR/scope is missing, ask for its link. Do not guess a passing verdict without a comparison scope.

Publish findings or the no-findings verdict as a comment on the reviewed package PR when permitted.
If commenting is unavailable, return the full report in the persistent session result and a copy-ready
Repair request that includes its link. Do not request broader permissions. The next worker must be
able to retrieve the report; if the link is inaccessible, ask for the report text rather than guessing.

### Repair

Retrieve and read the named phase's review from the package PR or supplied report link, verifying
its phase and reviewed revision. If findings are missing or inaccessible, request the report before
making review-driven edits. Read current source and the approved plan. Repair supported findings
in that scope, explain any disagreement using code/test evidence, and preserve good prior work.
Do not redesign the package or start the next phase. Run focused regression proof, update progress
and map findings to fixes. Publish and request re-review of the new head; do not self-certify it.
For P, repair only the proposed plan and its source grounding, not product code; no prior plan approval
is required to address planning findings. Reapproval is needed if an already approved contract changes.

### Resume

Continue only the named interrupted phase. Use its latest instruction, committed specification,
published changes, check logs and reviews to determine what remains. Do not replay already recorded
effects blindly or trust a stale progress label. If the phase already finished, report that evidence
and its next review/decision instead of doing duplicate work. Continue under Plan or Implement as
appropriate; if an interrupted repair is evident, finish that repair. No automatic successor.

## Packages

Read only the selected package. Source anchors are navigation entry points, not a predetermined
editable-file list. Resolve exact owners/tests at the current revision. The programme's numbered
WP/P/V identifiers are stable lookup keys; search their headings/rows rather than reading its full
history. All packages use P for planning; A onward are implementation phases in the committed plan.
The initial order is P, then A, B, C and so on as listed, one at a time. Before implementation,
the planner must give each phase explicit prerequisites and preserve stable IDs once approved.
If a phase needs multiple sessions, resume that ID; do not silently add or select a different phase.

### D03: Recovery

**Predecessor:** D02 code complete, reviewed and published. **Programme:** WP3, P05/P10/P11;
V06-V10, V13, V18, V20. **Start at:** [portfolio application](../../serve/delivery/src/owlbear_delivery/portfolio_application.py),
[workspace owner](../../serve/delivery/src/owlbear_delivery/change_workspace.py),
[runtime](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) and their owning tests.

**Result:** bounded, preservation-first recovery of D02's retained failures, plus useful offline
diagnostics. Cover failed finalizers, uncertain claim activation, damaged coordination and interrupted
engine actions. A timeout or missing host tool never permits replacing a possibly live worker.
No foreign/staged/private bytes may be discarded or exposed by preservation. Unknown corruption
must remain diagnosed, not rehashed into trusted authority. No general migration framework here.

| Phase | Initial scope and decisive proof |
| --- | --- |
| D03-P | Settle supported exclusion evidence, recovery state/effect contracts, retry identity and all phase tests against D02. No product edits. |
| D03-A | Critical exclusion/recovery reference path. A controlled still-writing worker cannot contaminate replacement; ambiguous termination stays blocked; supported exclusion survives restart. |
| D03-B | Persist failure identity, action-specific budget/backoff and exhaustion. Equivalent retries share semantic identity despite fresh operation IDs or sessions; unrelated Changes still run. |
| D03-C | Nonterminal worktree/proof repair and return to the original action. Preserve exact owned bytes/index/head; reject drift, foreign/staged/secret-like changes; inject partial preservation/write failures. |
| D03-D | Read-only offline diagnosis below damaged runtime composition. Missing MCP and malformed frontier fixtures return bounded evidence without repair writes. |
| D03-E | Registered adapters/controller handoffs and cumulative failure-to-repair proof. Validate requests/results in-process and keep actual host exclusion/dispatch gaps explicit. |

### D04: Revision and Evidence

**Predecessor:** D03 merged with required proof. **Programme:** WP4, P12-P14;
V14-V16, V18, V21. **Start at:** the [Delivery package](../../serve/delivery/src/owlbear_delivery/),
its source-bound admission/design/state/workspace snapshot tests, and
[Designer workflow](../../share/skills/w-design-session/SKILL.md) as source to edit, not to execute.

**Result:** coherent same-Change revision activation, immutable evidence applicability and precise
remaining requests. Old proof is reusable only for its original covered claim/version; a new request
ID alone does not invalidate it. Acquisition stays blocked while activation participants disagree.
Do not silently certify old evidence against a changed target or force a stage through the UI.

| Phase | Initial scope and decisive proof |
| --- | --- |
| D04-P | Resolve package/admission/frontier/snapshot identities, candidate/active layout, activation participants and evidence coverage; design realistic interrupted-step tests. |
| D04-A | Prepare/activate/reconcile one coherent revision path. Crashes at each durable boundary restart to approved old state or exact coherent new state, without duplicate effects. |
| D04-B | Immutable applicability and minimal request carry-forward. Unchanged covered claims reuse proof; changed claims expose the exact gap without fabricating acceptance. |
| D04-C | Registered adapter and same-Change Designer resume integration; cumulative source-bound activation/evidence proof and explicit host-handoff limits. |

### D05: Merge Approval

**Predecessor:** D04 merged. **Programme:** WP2 provider/approval scope, P08/P09;
V12, V19. **Start at:** [GitHub provider](../../serve/delivery-github/src/owlbear_delivery_github/github.py),
its tests, D02 publication/observation owners and [Cockpit API](../../serve/cockpit/src/owlbear_cockpit/).

**Result:** explicit user approval for one exact head, protected provider execution and truthful
readback. Proposal approval is not merge approval. Stale provider observations, changed heads,
protection failures and lost responses cannot cause duplicate or unapproved merges. Use provider
fixtures, never a real merge to test the implementation. Resolve policy questions before coding.

| Phase | Initial scope and decisive proof |
| --- | --- |
| D05-P | Investigate actual provider capabilities/permissions, freshness and approval contract; revalidate earlier research against D04. No provider mutations. |
| D05-A | Approval identity, invalidation and fixed provider/readback path. Test stale head, unmergeable/protected PR, expired observations and lost-response replay. |
| D05-B | API and Cockpit confirmation/cancel/error states, with server-owned authorization and stale-confirmation E2E; cumulative package proof. |

### D06: Prepared Assistance

**Predecessor:** D05 merged; D04 evidence contract present. **Programme:** WP5, P15-P18;
V15-V17, V22-V23. **Start at:** [Delivery](../../serve/delivery/src/owlbear_delivery/),
[Cockpit](../../serve/cockpit/) and [Browser](../../serve/browser/) owners; locate the published
B1 candidate and its approved procedure. Missing B1 source is a dependency, not permission to invent it.

**Result:** agent-prepared checks, private local input via opaque references, owned resources and
separate human confirmation. Resolve retention/privacy policy explicitly. No company URLs, tokens,
credentials or profiles in plans/transcripts/logs/receipts; use synthetic inputs. Cancellation/Not now
is not success. Real managed-device sign-in remains V23 host proof, never a cloud claim.

| Phase | Initial scope and decisive proof |
| --- | --- |
| D06-P | Settle registry, input descriptors, retention, provenance, preparation and resource/cancellation contract; expose genuinely missing user decisions. |
| D06-A | Prepared lifecycle and candidate/resource identity. Human attention requires an available prepared handler; evidence distinguishes observations from confirmation. |
| D06-B | Local input handoff, origin protections, expiry/cancel and opaque references. Synthetic-secret/log/receipt and stale-session negative tests. |
| D06-C | B1 runner using approved source and owned browser resources, tested with synthetic sites. Unsupported host capability is visible and non-runnable. |
| D06-D | Settled assistance/evidence/Not now presentation and cumulative integration; no new secret fields or client-owned authorization. |

### D07: Offline Maintenance

**Predecessor:** D06 merged; D03/D04 custody/schema contracts stable. **Programme:** WP6,
P19-P21; V18, V20, V21, V24. **Start at:** [Delivery storage/transactions](../../serve/delivery/src/owlbear_delivery/),
[repository tools](../../serve/tools/) and [setup](../../setup/).

**Result:** minimum supported offline repair/migration and release/restart procedure on disposable
installations, below broken application composition. Preserve pending actions, claims, approvals,
evidence and old schemas/journals. Do not bless unknown corruption or restore old state over new
evidence. No live migration or new controller framework merely to execute development.

| Phase | Initial scope and decisive proof |
| --- | --- |
| D07-P | Inventory supported schema/version transitions and copy-based fixtures, including pre-D02 claims and new action journals. Define refusal, drain, bounded lock/fetch and rollback contracts. |
| D07-A | One fenced offline proposal/application transition with corruption refusal, stale proposal checks and crash/replay at every durable boundary. |
| D07-B | Minimum executable selection/drain/restart procedure. Active writers fence changes; incompatible downgrade refuses before mutation; target-sync failures cannot hang maintenance indefinitely. |
| D07-C | Setup/distribution wiring from that contract; missing-capability and disposable installation/restart proof. Actual host release activation remains outside cloud execution. |

### D08: Integration and Host Acceptance

**Predecessor:** D03-D07 merged with required code proof. **Programme:** WP7, P22-P24;
complete V01-V24 matrix. **Start at:** the integrated package plans/reviews, current programme,
public docs, [agent wiring](../../share/WIRING.md) and existing cross-package suites.

**Result:** a reconciled integrated candidate and precise host acceptance handoff. Retire old public
entry points only after their normal and exceptional capabilities have proved replacements. No
mock-only test, package status label or cloud review can certify managed SSO or live activation.

| Phase | Initial scope and decisive proof |
| --- | --- |
| D08-P | Map each acceptance claim to integrated source, actual proof and remaining gap; plan bounded docs/fault-matrix slices without reopening settled product scope. |
| D08-A | Reconcile public docs/wiring and run cumulative synthetic fault/restart/journey proof; independently review the exact candidate and publish host-check instructions. |
| D08-H | Host-only: actual VS Code/macOS/managed-browser journey, fresh-session handoffs and copy-based upgrade rehearsal. Stop before live activation pending explicit user authorization. |

## Operator Quick Start

### Launch and Continue

1. Check the requested package's actual status and published prerequisites. Use its existing PR for
   unfinished work, not a new planning task. The selected checkout must contain this guide and needed
   source; cloud workers cannot see unpushed local changes. For an unproven environment, verify locked
   dependency setup, one focused in-process test and a published result retrievable by the next session.
   Reuse valid environment evidence; do not repeat a pilot just because a new phase starts.
2. For a new package, select **maba-pag/owlbear**, starting branch **dev**, and Luna Max unless the
   current action meets the escalation criteria. Use the complete prompt below with the desired ID.
3. Read the resulting plan. On that PR, post the implementation prompt for its first phase. This
   authorizes the named phase against the presented plan, not unresolved decisions or successors.
4. Use review/repair/resume prompts on that PR. For a fresh independent review task, attach the PR
   URL and select the same model/depth in the UI if that composer does not interpret qualified mentions.
   Do not assume a new task knows which PR to review. No hashes or test commands need manual entry.
5. After all phases, review the cumulative result, satisfy required checks and human approvals,
   merge, then start the next package from `dev`. Missing connectivity means the session stops and waits.

These examples are complete PR-comment requests. Change only the phase ID to the actual target;
an example ID is not a current status claim. In a new-task composer, also select the matching model
in its UI; the qualified mention is the supported PR-follow-up route, not a universal UI override.

**Plan**:

```text
@copilot+gpt-5.6-luna:max Work on D04-P using .owlbear/research/delivery-cloud-flight-handoff.md.
Follow its Agent Start Here reading route and execute only that phase.
```

**Authorize an implementation phase** (change only the phase ID):

```text
@copilot+gpt-5.6-luna:max Work on D03-B using .owlbear/research/delivery-cloud-flight-handoff.md.
I approve the package plan presented in this PR for that phase. Follow the reading route and stop after it.
```

**Review against defined criteria**:

```text
@copilot+gpt-5.6-luna:max Review D03-B using .owlbear/research/delivery-cloud-flight-handoff.md and this PR.
```

**Different-family review when warranted**:

```text
@copilot+claude-opus-5 Review D03-C using .owlbear/research/delivery-cloud-flight-handoff.md and this PR.
```

**Repair findings**:

```text
@copilot+gpt-5.6-luna:max Repair D03-C using .owlbear/research/delivery-cloud-flight-handoff.md and this PR's review.
```

**Resume an interruption**:

```text
@copilot+gpt-5.6-luna:max Resume D03-C using .owlbear/research/delivery-cloud-flight-handoff.md and this PR.
```

### Platform Preparation

Check account cloud access, model availability, budget and human approval requirements before launch.
Before relying on multiple sequential packages, inspect `dev`'s actual required checks and approval
rules and confirm an eligible approver is available where required. The requester may not qualify
as the required approver of their own Copilot PR. If merge eligibility cannot be established, continue
useful work on the current package PR but do not start a dependent package or weaken protections.
An agent review is not a substitute for a required human approval.

A new cloud task creates a branch; an existing-PR comment normally updates that PR's branch.
Use the latter for phases.

[Copilot setup steps](../../.github/workflows/copilot-setup-steps.yml) install uv, Python from
[.python-version](../../.python-version), and Node from [Cockpit's .nvmrc](../../serve/cockpit/web/.nvmrc),
then restore locked Python workspace/dev dependencies and Cockpit npm dependencies with caching.
The checkout follows the task context; it is not forced to `dev`. Frontend steps are conditional
on the frontend lockfile, so the consumer checkout without frontend sources remains usable.
Optional Python extras and browser binaries are installed only when a selected check needs them.
Setup runs version checks, not tests, builds, MCP services or MegaLinter. Step timeouts bound dependency
installation; the job's 59-minute ceiling preserves the cloud session's platform allowance.

Renovate's existing GitHub Actions manager updates action digests/tags and the explicit uv version.
Its existing pyenv/nvm managers update the shared Python/Node pins; the workflow has no duplicate
runtime versions to synchronize. Package versions remain in their existing Renovate-managed lockfiles.

GitHub must have this workflow on the repository's **default branch** before automatic setup works.
If generated `main` is the default, use the normal reviewed infrastructure sync from `dev`; do not
commit directly to `main` or change the default branch/protections as a shortcut. `workflow_dispatch`
allows a setup-only rehearsal once discoverable. Inspect setup logs: GitHub can still start the agent
after a setup step fails, so file presence is not proof of a ready environment. Never use `setup/init.py`
as a cloud bootstrap. The guide must also be present in the selected task checkout.

[Source CI](../../.github/workflows/source-verification.yml) and
[Cockpit CI](../../.github/workflows/cockpit-verification.yml) target `dev` and skip drafts. Mark
appropriate PRs ready and approve workflow runs when required, or use supported manual checks on
the exact branch. Absent checks are not green. Whole-source lint or external MegaLinter may still
find issues beyond scoped agent proof; do not launch them inside the agent or waive merge gates.

## References

- [Programme and acceptance](change-continuation-delivery-redesign.md): product authority and status.
- [Cloud agent](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent): asynchronous execution and 59-minute session limit.
- [GitHub task/PR controls](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github): new tasks, follow-ups and workflow approvals.
- [Model selection](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/changing-the-ai-model): select models/depth in the UI, not prompts.
- [Environment](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment) and [MCP configuration](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/configure-mcp-servers): cloud tools are not local VS Code bindings.

- [Session persistence](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/manage-and-track-agents) and [security controls](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations): published checkpoints, permissions and review limits.
