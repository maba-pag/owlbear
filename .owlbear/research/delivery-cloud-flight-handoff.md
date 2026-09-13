# Delivery Cloud Flight Handoff

> **Owning request:** Prepare reviewable cloud work during an eight-hour flight.
> **Date:** 2026-09-13
> **Question:** Can bounded parallel cloud sessions advance Delivery without a reliable laptop connection?
> **Status:** Proposed batch workflow, not dispatch authorization or an amendment to the active implementation plan.

## 1. Recommendation

Use GitHub Copilot **cloud agent** on GitHub.com. Default to one active package PR and one
bounded session at a time. Plan and implement its phases on that branch, independently review
the result, merge accepted work, then start the next package from the published baseline.
Optional parallel research needs explicit independent ownership; it is not required for this flight.
The user selects models and reasoning depth in GitHub's UI; copied prompts do not select models
or require a repository model router.

Use **one named, bounded outcome per session**, not "implement the next item in the plan".
The active D packages are larger than the documented 59-minute hard session limit. Target
30 minutes of implementation plus 15 minutes of proof and handoff, stopping by minute 50.
These are planning targets, not enforced timers or guarantees that a job will fit.

One coherent package PR may take several sessions: planning, implementation, repairs and independent
review. A short PR comment starts the next bounded session with a manually selected model. The
branch and committed package plan carry progress, not a continuously running chat. No connection
means the current session finishes and waits; successors do not start themselves. Do not promise
completion of D03-D08 during the flight. Useful reviewed PRs are the realistic goal.

### Practical Alternatives

| Option | Assessment |
| --- | --- |
| Copilot cloud agent | Recommended: asynchronous execution, familiar PRs and explicit model selection. |
| GitHub-hosted Claude or Codex | Real alternatives if enabled; different harnesses can provide another opinion. GitHub documents shared platform limitations, so this is not a timeout escape. |
| CLI agent on an always-on remote machine | Viable if already provisioned and rehearsed. Needs stable server connectivity, credentials, cost limits, durable logs and process recovery. Too much new setup for this flight otherwise. |
| Copilot automations | Scheduled/event sessions exist, but require a private/internal repository and policy access. Not a tested dependency-and-review coordinator; unnecessary for the user's manual batches. |
| Laptop online agent or an untested offline model | Does not solve this reliably. No validated local model setup exists here, and laptop online execution still needs connectivity and uptime. |

## 2. Verified Constraints

| Source | Relevant fact |
| --- | --- |
| [Cloud agent overview](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent) | Background execution, ephemeral environments, one branch and at most one PR per task, 59-minute hard limit. |
| [Planning and iteration](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/research-plan-iterate) | GitHub.com supports planning before code and iterating before opening a PR. Ask explicitly for a PR when wanted. |
| [Model selection](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/changing-the-ai-model) | Supported entry points have a picker; without one the selection is Auto. Current list includes Astra, Opus and Luna; account availability must be checked. |
| [GitHub and PR controls](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github) | Select starting branch; a new PR comment can select a model for follow-up work. Later issue comments are not automatically consumed. |
| [Session management](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/manage-and-track-agents) | Pushed commits and session logs survive; unpushed workspace contents are not a durable handoff guarantee. |
| [Cloud environment](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment) | Setup workflow must be on the default branch; setup failure can leave the agent running. Ubuntu/Windows supported, not macOS. |
| [Security controls](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations) | Restricted branch publication, human review/merge controls and workflow approval by default. The requester cannot supply their own required approval. |
| [Other agents](https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents), [automations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-automations) | Policy-dependent alternatives, not assumed available or configured here. |
| [Programme](change-continuation-delivery-redesign.md) | D03-D08 dependencies, original P scope, V01-V24 acceptance and live-state protections remain authoritative. |
| [Source CI](../../.github/workflows/source-verification.yml), [Cockpit CI](../../.github/workflows/cockpit-verification.yml) | Both target `dev` and skip draft PRs. Whole-source lint can fail despite a scoped local proof. Browser compatibility CI is not the full Work portfolio E2E gate. |

Observed preparation baseline: `6a223aa49`, with D02 still being repaired in the other chat.
The updated departure assumption is reviewed D02 complete and D03 not yet complete. Verify that
checkpoint at launch; this proposal is not evidence that D02 has already passed its remaining gates.
No Copilot setup workflow was present. Repository visibility/default-branch metadata queries
returned no usable output; account model access, approval rules and cloud execution are unverified.
Usage includes Actions time and AI credits/tokens; do not estimate cost solely by session count.

## 3. Preflight and Handoff

1. **Freeze a reviewed checkpoint with the other chat.** Confirm actual D02 completion, then start
   D03-P. If D02 is unfinished, prepare its exact remaining slice first. If some D03 work exists,
   reuse its reviewed commits and plan only the remainder; do not reimplement it or assume D04 is ready.
2. **Publish required context.** The user pushes the reviewed `dev` checkpoint and approved handoff.
   Record full source/plan/dependency SHAs. Cloud workers cannot see unpushed local work, the fork's
   chat or untracked B1 packages. Do not upload live state, private URLs, credentials or browser profiles.
3. **Verify access and review policy.** Check cloud agent availability, model picker, budget,
   concurrency and eligible human approvals. Always select `dev`, not generated consumer `main`.
   If another eligible human is required but unavailable, plan to accumulate candidate PRs, not merge.
4. **Run a real cloud pilot before departure.** Verify the chosen branch/SHA, locked dependency
   installation, one owning Python test and, for UI work, build and the disposable E2E harness.
   Record setup duration. Pilot success, not a prompt, establishes environment readiness.
5. **Prepare deterministic setup if needed.** Reuse current CI's pinned actions/tool versions.
   A Copilot setup workflow only works once present on the actual default branch; do not change
   that branch or protections as a shortcut. Otherwise validate explicit bootstrap in the pilot.
6. **Resolve CI operation.** Draft PRs here skip the source/Cockpit workflows even after permission
   to run workflows. The user marks appropriate PRs ready and approves workflow execution when needed.
   Alternatively use a supported manual workflow on the exact branch/head. Skipped means unrun.
7. **Finalize the first package handoff.** D03-P must produce the concrete paths/contracts/tests
   for its implementation phases. Save the package PR and plan-commit URLs for low-bandwidth access.
   Approve the plan before implementation; do not launch placeholder implementation tickets.

Bootstrap ingredients to verify in the pilot: uv required by [pyproject.toml](../../pyproject.toml),
`uv python install`, `uv sync --locked --all-packages --all-extras --all-groups`; Node from
[the pinned version](../../serve/cockpit/web/.nvmrc), `npm ci --engine-strict` in the frontend,
and the needed Python/Node Playwright browsers. Read the actual test harness before starting it.
Do not run workspace `setup/init.py`, configure laptop MCPs or disable safety controls to bootstrap.

### Cloud-Only Authorization

Before launch, explicitly approve the exception to local "one writer on dev" and "user pushes"
rules: the cloud platform may create and publish **only each job's assigned PR branch**, targeting
`dev`. Sequential phases use that same package branch; any separately approved independent job
uses its own branch and bounded ownership. No direct target push,
merge, force-push, protection change, real provider mutation during tests or live activation follows.
This proposal does not install that exception into the running fork's instructions.

After handoff the local fork must not write the same implementation slice. The package worker updates
only its assigned package plan and PR progress, not the programme status or shared governance. One
integration owner updates the programme after the package merges. No model configuration is needed.

## 4. Package PRs and Phase Handoffs

**One package PR, multiple bounded sessions** is the default. This replaces the earlier implication
that every A/B/C phase needs a separate merged PR. It does not mean one uninterrupted chat can run
for hours or that a worker may implement all phases without checkpoints.

### How the Plan Reaches the Next Worker

1. D03-P opens the D03 draft PR and commits a package-specific plan under `.owlbear/research/`,
   for example `delivery-cloud-d03-plan.md`. D04-P later does the same with
   `delivery-cloud-d04-plan.md` on the D04 PR. These files are future outputs, not created here.
2. The plan names the source baseline, approved product requirements, owning files, exact interfaces,
   phase dependencies, negative cases, proof commands, exclusions and unresolved decisions. It has a
   compact progress section. It does not replace or edit this flight guide or the programme authority.
3. Review the plan, then explicitly approve its exact commit in the PR. Planning stops there.
   The planning-only PR need not be merged before implementation on that same branch.
4. Start A with a PR comment containing the approved plan path/commit, phase ID and current head.
   The next worker reads the file from Git, verifies the plan approval and prerequisite bytes, and
   implements only A. The same thread is convenient; a fresh session works equally well from these inputs.
5. A publishes coherent code/test commits and updates only the package progress record: completed
   observations, actual proof, open findings and next phase. The PR handoff names the exact head and
   last independently reviewed checkpoint. Never infer approval from the worker's own status text.
6. Review A and resolve findings before B starts from that reviewed branch checkpoint; repeat for C.
   Plan changes that alter contracts, permissions or scope require explicit reapproval. Later workers
   may update progress, but cannot silently rewrite the approved specification to match their code.
7. Run cumulative package proof and independent exact-head review before merging the package PR.
   The next D package starts from the resulting `dev`, not an unmerged sibling branch.

Thus D04-P -> D04-A -> D04-B -> D04-C can share **one PR**, but each arrow is an explicit
bounded-session handoff. D04 currently has no D04-D phase; the planner may split an oversized phase
only while preserving its requirements and making the new dependency explicit. Independent reviews
use fresh read-only sessions so implementation chat context is not the sole basis for judgment.

### Recovery Without Starting Over

Record pushed checkpoints early; stopped/timed-out sessions need not have saved unpushed work.
If a worker runs beyond scope, stop it and inspect the diff after the last good checkpoint. A fresh
repair session can continue on the same PR using the approved plan and that commit, preserving good
work and reverting only identified bad commits/hunks after explicit approval. Prefer corrective/revert
commits over force-pushes, resets or deleting the branch. Re-run affected proof and review the new head.
Never trust a changed plan's progress claim without the referenced proof and review.

One PR can still grow too large to review comfortably. In that case finish a coherent tested slice,
review and merge it, then open a successor PR with the exact dependency. Fewer PRs are a convenience,
not permission to omit intermediate review or keep an unreviewable change growing indefinitely.

### First Wave, Assuming D02 Is Reviewed

Start **D03-P only**: inspect D02's retained failure/custody contracts and prepare P05/P10/P11
implementation phases on the D03 PR. Plan from actual source, not assumed host termination or
future recovery APIs. Approve this plan before departure if possible so D03-A can run in flight.

Optional read-only D05 provider research, D07 compatibility inventory or D08 proof-gap audit can
run separately later, with their own outputs and explicit authorization. They are not prerequisite
parallel launches. Their findings must be revalidated against subsequent package changes.

**Within-package barrier:** completed tests and independent review of the phase checkpoint, with
the predecessor commits present on the same PR branch. **Between-package barrier:** completed
package acceptance, required checks/reviews and merge into the baseline used by the next package.
Neither a finished chat nor an open PR is proof that either barrier is satisfied.

### Implementation Queue After Planning

Each row is a candidate **bounded phase**, requiring exact subdivision at the departure SHA.
Some phases may need several sessions on the same PR. "Reviewed" in the dependency column means
the within-package checkpoint barrier above; "package complete" means the merged package barrier.
The clock never justifies removing proof or requirements. The D03 planner must validate this proposed
internal ordering against D02; do not merge a partially safe recovery API merely to fit a session.

| Job | Bounded result and proof | Dependency |
| --- | --- | --- |
| D03-P | Plan recovery exits for retained finalizer/engine/claim failures, preservation, retries and offline diagnostics; settle exclusion evidence and per-phase proof. No product edits. | D02 complete and published |
| D03-A | Exact worker exclusion and failure-recovery contract with a critical reference path; ambiguous/still-writing workers cannot be replaced. Controlled-worker and restart tests. | Approved D03-P |
| D03-B | Durable failure fingerprints, action-specific retry budgets/backoff and exhaustion across restart. Key equivalent retries on stable semantic identity, not newly minted operation IDs. | Reviewed D03-A |
| D03-C | Preservation-first nonterminal worktree/proof repair and bounded return to the original action; protect foreign/staged/secret-like changes and survive partial preservation failure. | Reviewed D03-B |
| D03-D | Minimal read-only offline diagnosis without constructing damaged runtime; malformed frontier and unknown corruption remain evidence, not repair authorization. | Reviewed D03-C; approved P05 diagnostic contract |
| D03-E | Registered recovery/diagnostic adapters and worker/controller handoffs; assembled failure-to-repair/retry proof and truthful unavailable host capabilities. | Reviewed D03-D; no new custody semantics |
| D04-P | Plan revision activation, immutable evidence applicability and same-Change Designer handoff against the completed recovery contract. | D03 complete and published |
| D04-A | One coherent revision prepare/activate/reconcile path, identities and custody, with interrupted durable-step replay. | Approved D04-P |
| D04-B | Immutable evidence applicability and precise request carry-forward; unchanged claim reuses proof, changed claim cannot inherit acceptance silently. | Reviewed D04-A |
| D04-C | Same-Change Designer resume and registered adapter integration with realistic contracts/host-handoff fixtures. | Reviewed D04-B |
| D05-R | Provider capability/permissions and exact-head approval plan; revalidate any earlier research against D04. No real merge. | D04 complete and published |
| D05-A | Exact-head approval and fixed provider/readback behavior; stale approval, freshness, protections and lost responses. No inferred merge permission. | D04 complete; D05-R decisions approved |
| D05-B | Approval API and Cockpit confirmation with stale/cancel/failure E2E. | Reviewed D05-A |
| D06-P | Plan prepared interactions and resolve privacy/retention decisions; stop before implementation. | D04/D05 complete and published |
| D06-A | Prepared lifecycle, opaque references and independent human confirmation from the approved contract. | Approved D06-P and explicit decisions |
| D06-B | Local input protections, expiry/cancel and redaction proved with synthetic private inputs. | Reviewed D06-A |
| D06-C | B1 runner through owned resources and synthetic sites; exact B1 source must be published. | Reviewed D06-B |
| D06-D | Settled assistance/evidence/Not now presentation; no new secret fields or client authorization. | Reviewed D06-C |
| D07-R | Compatibility inventory and supported offline-transition plan using current schemas/journals and disposable old-state fixtures. Revalidate earlier research. | D06 complete and published |
| D07-A | One supported offline proposal/application transition below broken composition, with corruption refusal and crash/replay proof. | D06 complete; approved compatibility design |
| D07-B | Minimum supported version/drain/restart/downgrade refusal procedure on disposable installations. | Reviewed D07-A |
| D07-C | Setup/distribution wiring and unavailable-capability tests from the proved procedure. | Reviewed D07-B |
| D08-A | Integrated docs and cumulative synthetic fault matrix, precise remaining proof and reviewed candidate. | D04-D07 integrated |
| D08-H | Real VS Code/macOS/managed-browser journey, user sign-in and deliberate local activation decision. | After flight on the real host |

D03 covers original P05/P10/P11, including V06-V10, V13, V18 and V20. Carry forward D02's explicit
recovery gaps for failed finalizers, uncertain activation, damaged coordination and interrupted
engine actions; do not omit them when splitting phases. Controlled-worker tests can prove supported
exclusion mechanics, not actual VS Code/macOS host capabilities that the cloud lacks. Missing
termination evidence must still block replacement and leave the host gate explicit.

The default queue is sequential: finish and merge D03, then D04, then D05, D06, D07 and D08's
cloud-verifiable portion. Keep behavior tests with each phase. No need to fill four simultaneous slots.

Linux cloud proof cannot replace V23 managed-device authentication or actual VS Code handoffs.
D08-H remains open even if cloud CI passes. Do not migrate actual retained records in the cloud.

## 5. Model Choices Outside Prompts

The user selects the model and thinking depth at launch and each follow-up. There is no automatic
switch within a session and no repo configuration requirement. Use a strong planning session for
the next coherent contract, not a speculative low-level plan for the entire programme.

- Strong model: uncertain activation, custody, evidence, authorization, privacy and migration work.
- Less expensive implementation model: settled adapters/workflows and bounded engineering.
- Cheapest tier: exact mechanical presentation/docs only when both uncertainty and impact are low.
- Independent review: fresh different-family session where available; critical review remains rigorous.

A strong plan does not make unresolved critical implementation low-risk. Keep such code with the
strong tier. Do not run planning and review as mandatory extra sessions for a trivial mechanical task;
reuse an already-approved contract. Built-in automatic code review is useful but not evidence of the
deliberately selected independent reviewer or a required human approval.

## 6. Reusable Prompt Templates

These are ordinary copyable text, not installed skills or agent files. Replace every placeholder
before dispatch. Choose models and reasoning depth separately in the UI.

### Common Context for Each Job

```text
Repository: <repo>. Package PR: <number, or create for planning>.
New package: branch from dev at <base SHA>. Existing package: use this PR branch
at <expected current head>; do not branch again from dev for each phase.
Assigned phase: <exact phase>. Package plan: <path and approved plan commit>.
Plan approval: <PR comment URL, or pending for planning only>.
Required predecessor checkpoints: <reviewed SHAs>. Result: <one concrete outcome>.
Owned files: <explicit paths>. Exclusions: <paths and behavior>.
Interfaces and scenarios: <exact settled contract/examples>.
Proof commands: <resolved tests/lint/build and expected observations>.

Read .github/copilot-instructions.md, applicable instructions/skills from this
checkout, and the named sections of .owlbear/research/change-continuation-delivery-redesign.md.
Read the committed package plan and verify its approved revision and checkpoints.
Do not select another phase/package or depend on an unmerged sibling PR.
Missing prerequisites mean NOT_READY, not permission to invent a substitute.

For this cloud job I authorize platform publication only to its assigned PR branch
targeting dev, as an exception to local direct-dev/user-push rules. No target push,
merge, force-push, protection changes or live activation. No Delivery records,
claims or laptop MCP workflows. Use disposable repos, local provider fixtures and
synthetic private inputs; no real credentials or managed-company authentication.
Do not edit the active programme status, shared governance or another job's files.
Update only the assigned package plan's progress section and PR handoff. Contract
changes require explicit reapproval; your own progress text does not grant it.

Use locked repository toolchains and existing test helpers. Do not skip tests,
weaken assertions, alter safety semantics or claim unrun host checks passed.
Plan for 50 minutes: stop starting new edits by minute 35, publish coherent
checkpoints and the current status by minute 45, then finish proof/report and stop.
These soft targets do not override the platform's hard limit. Publish early.
Return exact base/head, owned changes, actual commands/results, unrun gates,
blockers and one precise next action. Do not dispatch another job yourself.
```

### Plan, Then Stop

```text
Plan ONLY <D03-P or named package planning phase>, using the common context. No product edits.
Ground the contract in current owning source/tests, not assumed future features.
Resolve state transitions, side-effect boundaries, error mapping and negative cases.
Split into coherent jobs targeting 30 minutes coding plus 15 minutes proof/handoff.
Give each exact file ownership, dependency SHAs, runnable checks and exclusions.
Identify remaining critical decisions and sequential within-package checkpoints.
Commit the plan to <one assigned package research file> on the package branch,
open its draft PR, report the plan commit SHA and STOP. Do not edit the programme
or flight guide. Implementation requires approval of this exact plan revision;
the same unmerged PR will host implementation phases after approval.
Do not infer undecided product/privacy/permission choices from that approval.
```

### Implement an Approved Job

```text
Implement ONLY <phase> from committed package plan <path at approved SHA>,
approval <comment URL>, expected package PR head <SHA>, using the common context.
Continue this assigned PR branch; do not create a new PR or start again from dev.
Start at the named owner and cheapest discriminating test. After the first
substantive edit, run that check before expanding the slice. Keep required
schemas/exports/tests with their owner; no placeholder behavior to meet the clock.
Checkpoint coherent progress early. If blocked by a new critical decision, record
evidence and stop instead of guessing. No successor work or own merge/approval.
Update package progress and the PR handoff; record the exact head, completed
observations, actual proof, findings and next phase. Report READY_FOR_INDEPENDENT_REVIEW,
CHECKPOINT_ONLY, BLOCKED_ENVIRONMENT or BLOCKED_DECISION. Stop before the next phase.
```

### Fresh Independent Review

```text
Review ONLY PR <number>, base <SHA>, head <SHA>, against <approved ticket/revision>.
Read-only source review: no fixes, commits, branches, merges or approval API calls.
Inspect actual code/tests before relying on implementation conclusions. Prioritize
data loss, custody, stale approval, replay, privacy and missing discriminating tests.
Distinguish executed proof, worker-reported proof and unrun checks. Post findings
with severity/path/line, or no findings, and explicit limits. Bind the verdict to
the exact base/head; any subsequent change requires relevant revalidation/re-review.
This is advisory review, not GitHub's required human approval. Stop.
```

Start a fresh review session rather than reusing the implementer's reasoning thread. A session
report is sufficient if that entry point cannot post a PR comment; link it without calling it approval.

### Resume or Repair on the Same PR

```text
@copilot Resume ONLY <phase> on this package PR at observed head <SHA>.
Read the package plan <path at approved SHA>, approval <comment URL>, last reviewed
checkpoint <SHA>, pushed commits, PR handoff and check results before editing.
The prior session may have timed out before reporting. Preserve its work, verify
what exists and don't repeat an effect without its owning receipt. Do not restart
the programme or choose a successor. Remaining slice/findings: <exact scope>.
Required proof: <commands>. Apply the common context and publish a durable status
before the working budget ends. Leave incomplete work draft. Stop.
```

## 7. Low-Bandwidth Operating Cycle

1. Start D03-P after verifying reviewed D02, or the next explicitly approved phase on its package PR.
   Run one writer. Only launch parallel read-only work when separately approved and independent.
2. At the next connection, read the package PR's short status and request review or a bounded repair.
   Select the model in the new session/PR-comment UI, not in the pasted instruction.
3. After a phase passes proof and independent review, approve the next phase on the same PR branch.
   Allow required workflows/manual branch checks as appropriate; absent draft checks are not green.
4. When the package is complete, mark its PR ready, satisfy actual CI/approval requirements and
   review the cumulative exact head before merging. Repairs or base changes require relevant revalidation.
5. Start the next package from the merged published baseline. No connectivity means waiting safely.

The next preparation action is an actual cloud setup/pilot and a departure-SHA planning ticket,
not a new runtime automation system. This document does not dispatch work or change repository policy.
Its checks validate structure/links, not cloud access, bootstrap success or 50-minute task fit.
