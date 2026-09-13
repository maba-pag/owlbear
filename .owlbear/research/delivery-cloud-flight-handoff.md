# Delivery Cloud Flight Handoff

> **Owning request:** Prepare reviewable cloud work during an eight-hour flight.
> **Date:** 2026-09-13
> **Question:** Can bounded parallel cloud sessions advance Delivery without a reliable laptop connection?
> **Status:** Proposed batch workflow, not dispatch authorization or an amendment to the active implementation plan.

## 1. Recommendation

Use GitHub Copilot **cloud agent** on GitHub.com. Start 1-4 independent sessions, let them
finish without keeping the laptop connected, review their PRs, merge accepted work, and launch
the next batch from the resulting published baseline. The user selects models and reasoning
depth in GitHub's UI; copied prompts do not select models or require a repository model router.

Use **one named, bounded outcome per session**, not "implement the next item in the plan".
The active D packages are larger than the documented 59-minute hard session limit. Target
30 minutes of implementation plus 15 minutes of proof and handoff, stopping by minute 50.
These are planning targets, not enforced timers or guarantees that a job will fit.

One coherent PR may take several sessions: planning, implementation, repairs and independent
review. A short PR comment can start the next session with a manually selected model. No
connection means the current batch finishes and waits; dependent batches do not start themselves.
Do not promise completion of D04-D08 during the flight. Useful reviewed PRs are the realistic goal.

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
| [Programme](change-continuation-delivery-redesign.md) | D04-D08 dependencies, original P scope, V01-V24 acceptance and live-state protections remain authoritative. |
| [Source CI](../../.github/workflows/source-verification.yml), [Cockpit CI](../../.github/workflows/cockpit-verification.yml) | Both target `dev` and skip draft PRs. Whole-source lint can fail despite a scoped local proof. Browser compatibility CI is not the full Work portfolio E2E gate. |

Observed preparation baseline: `6a223aa49`, with D02 still being repaired in the other chat.
D03 completion in two to three hours is an assumption, not a dispatch prerequisite already met.
No Copilot setup workflow was present. Repository visibility/default-branch metadata queries
returned no usable output; account model access, approval rules and cloud execution are unverified.
Usage includes Actions time and AI credits/tokens; do not estimate cost solely by session count.

## 3. Preflight and Handoff

1. **Freeze a reviewed checkpoint with the other chat.** Confirm actual D03 completion. If it
   is unfinished, prepare its exact remaining slice instead of assigning D04 on assumed future code.
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
7. **Finalize the first batch.** Every implementation ticket needs exact paths/contracts/tests and
   approved predecessors. Save PR/session URLs for low-bandwidth access. Do not launch placeholders.

Bootstrap ingredients to verify in the pilot: uv required by [pyproject.toml](../../pyproject.toml),
`uv python install`, `uv sync --locked --all-packages --all-extras --all-groups`; Node from
[the pinned version](../../serve/cockpit/web/.nvmrc), `npm ci --engine-strict` in the frontend,
and the needed Python/Node Playwright browsers. Read the actual test harness before starting it.
Do not run workspace `setup/init.py`, configure laptop MCPs or disable safety controls to bootstrap.

### Cloud-Only Authorization

Before launch, explicitly approve the exception to local "one writer on dev" and "user pushes"
rules: the cloud platform may create and publish **only each job's assigned PR branch**, targeting
`dev`. Independent sessions have separate branches and bounded ownership. No direct target push,
merge, force-push, protection change, real provider mutation during tests or live activation follows.
This proposal does not install that exception into the running fork's instructions.

After handoff the local fork must not write the same implementation slice. Workers must not all
edit the programme status or shared governance. Each records progress in its PR; one integration
owner updates the programme after the batch. No new model configuration belongs in the repository.

## 4. Batch Design

**Barrier:** all writers finish; independent reviews bind exact base/head SHAs; repair findings;
merge accepted PRs in dependency order; prove the combined baseline; then start the next batch.
Later PRs must be refreshed/retested if earlier merges affect their inputs. Separate branches alone
do not prove independence. A failed job holds its dependent chain, not unrelated research.

Aim for **one core writer plus up to three genuinely independent jobs**, not four writers merely
to occupy slots. Shared schema, export, test fixture, lockfile and programme files each have one
owner. Do not split indispensable exports/consumer companions out of a change if doing so leaves
the baseline broken. Avoid stacked PRs and cross-branch dependency juggling during this flight.

### First Batch, Assuming D03 Is Reviewed

| Slot | Job | Output and independence |
| --- | --- | --- |
| 1 | D04-P: revision/evidence implementation plan | Exact P12/P13/P14 contracts, failure matrix, owning files and bounded next tickets; no product edits. |
| 2 | D05-R: provider/approval research | Current capability, permissions, stale-head/protection/lost-response cases; no code or real merge. Revalidate integration details after D04. |
| 3 | D07-R: compatibility inventory | Existing schemas/journals and disposable old-state fixtures to cover later; report only, not migrations or a frozen future schema. |
| 4, optional | D08-R: independent proof-gap audit | Map current V scenarios to exact tests/commits and host-only gaps; do not declare future work complete. |

Use separate per-job research files or session reports; never have four workers edit the same plan.
Planning/research PRs may be merged as clearly labelled proposals, not product acceptance. Approve
D04-P before boarding if possible: that lets D04-A replace planning in slot 1 and deliver code in flight.

### Implementation Queue After Planning

Each row is a candidate **session-sized outcome**, requiring exact subdivision at the departure SHA.
Some critical rows may still require several sessions on the same PR. The clock never justifies
removing proof or reducing product requirements. No later D implementation starts ahead of the
active programme's dependencies; earlier read-only research does not change this ordering.

| Job | Bounded result and proof | Dependency |
| --- | --- | --- |
| D04-A | One coherent revision prepare/activate/reconcile path, identities and custody, with interrupted durable-step replay. | Approved D04-P |
| D04-B | Immutable evidence applicability and precise request carry-forward; unchanged claim reuses proof, changed claim cannot inherit acceptance silently. | Reviewed D04-A |
| D04-C | Same-Change Designer resume and registered adapter integration with realistic contracts/host-handoff fixtures. Split independent consumers only after schema approval. | Reviewed D04-B |
| D05-A | Exact-head approval and fixed provider/readback behavior; stale approval, freshness, protections and lost responses. No inferred merge permission. | D04 complete; D05-R decisions approved |
| D05-B | Approval API and Cockpit confirmation with stale/cancel/failure E2E. | Reviewed D05-A |
| D06-P/A | First resolve privacy/retention decisions; then a separate job implements prepared lifecycle, opaque references and independent human confirmation. | D04/D05 complete; explicit decisions |
| D06-B | Local input protections, expiry/cancel and redaction proved with synthetic private inputs. | Reviewed D06-A |
| D06-C | B1 runner through owned resources and synthetic sites; exact B1 source must be published. | Reviewed D06-B |
| D06-D | Settled assistance/evidence/Not now presentation; no new secret fields or client authorization. | Reviewed D06-C |
| D07-A | One supported offline proposal/application transition below broken composition, with corruption refusal and crash/replay proof. | D06 complete; approved compatibility design |
| D07-B | Minimum supported version/drain/restart/downgrade refusal procedure on disposable installations. | Reviewed D07-A |
| D07-C | Setup/distribution wiring and unavailable-capability tests from the proved procedure. | Reviewed D07-B |
| D08-A | Integrated docs and cumulative synthetic fault matrix, precise remaining proof and reviewed candidate. | D04-D07 integrated |
| D08-H | Real VS Code/macOS/managed-browser journey, user sign-in and deliberate local activation decision. | After flight on the real host |

Example rolling batches: D04-A plus read-only provider/compatibility work; then D04-B plus an
independent approved test-fixture job if genuinely disjoint; then D04-C consumers split across
MCP, HTTP or agent docs only where their exact paths and inputs do not overlap. Otherwise dispatch
one writer. Product tests stay with behavior, not assigned to a disconnected team inventing oracles.

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
Repository: <repo>. Starting branch: dev. Expected base: <full SHA>.
Assigned job: <exact job>. Approved plan/ticket: <URL and revision>.
Required predecessor commits: <SHAs>. Result: <one concrete outcome>.
Owned files: <explicit paths>. Exclusions: <paths and behavior>.
Interfaces and scenarios: <exact settled contract/examples>.
Proof commands: <resolved tests/lint/build and expected observations>.

Read .github/copilot-instructions.md, applicable instructions/skills from this
checkout, and the named sections of .owlbear/research/change-continuation-delivery-redesign.md.
Do not select another unfinished package or depend on unmerged sibling work.
Missing prerequisites mean NOT_READY, not permission to invent a substitute.

For this cloud job I authorize platform publication only to its assigned PR branch
targeting dev, as an exception to local direct-dev/user-push rules. No target push,
merge, force-push, protection changes or live activation. No Delivery records,
claims or laptop MCP workflows. Use disposable repos, local provider fixtures and
synthetic private inputs; no real credentials or managed-company authentication.
Do not edit the active programme status, shared governance or another job's files.

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
Plan ONLY <job>, using the common context. No product edits.
Ground the contract in current owning source/tests, not assumed future features.
Resolve state transitions, side-effect boundaries, error mapping and negative cases.
Split into coherent jobs targeting 30 minutes coding plus 15 minutes proof/handoff.
Give each exact file ownership, dependency SHAs, runnable checks and exclusions.
Identify remaining critical decisions and genuinely independent parallel jobs.
Write the plan only to <one assigned research file>, open a draft PR, then STOP.
Implementation requires explicit approval; don't treat merging a proposal as
authorization for undecided product/privacy/permission choices.
```

### Implement an Approved Job

```text
Implement ONLY <job> from approved plan <URL/revision>, expected head <SHA>,
using the common context. Open a PR targeting dev, or continue this assigned PR.
Start at the named owner and cheapest discriminating test. After the first
substantive edit, run that check before expanding the slice. Keep required
schemas/exports/tests with their owner; no placeholder behavior to meet the clock.
Checkpoint coherent progress early. If blocked by a new critical decision, record
evidence and stop instead of guessing. No successor work or own merge/approval.
Report READY_FOR_INDEPENDENT_REVIEW, CHECKPOINT_ONLY, BLOCKED_ENVIRONMENT or
BLOCKED_DECISION with exact commits, actual proof and remaining work. Stop.
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
@copilot Resume ONLY <job> on this PR at observed head <SHA>.
Read pushed commits, PR handoff, session logs and check results before editing.
The prior session may have timed out before reporting. Preserve its work, verify
what exists and don't repeat an effect without its owning receipt. Do not restart
the programme or choose a successor. Remaining slice/findings: <exact scope>.
Required proof: <commands>. Apply the common context and publish a durable status
before the working budget ends. Leave incomplete work draft. Stop.
```

## 7. Low-Bandwidth Operating Cycle

1. Before disconnecting, start the approved 1-4 jobs against the same recorded batch baseline.
2. At the next connection, read each PR's short status and request review or a bounded repair.
   Select the model in the new session/PR-comment UI, not in the pasted instruction.
3. Mark appropriate PRs ready and allow workflows after inspecting changes. Never interpret absent
   draft checks as green. Confirm actual head and human approval eligibility before merging.
4. Merge accepted independent PRs in the planned order; recheck later heads and combined tests.
   A pending critical failure holds dependent jobs. Unrelated research may still proceed.
5. Start the next named batch from the new published baseline. No connectivity means waiting safely.

The next preparation action is an actual cloud setup/pilot and a departure-SHA planning ticket,
not a new runtime automation system. This document does not dispatch work or change repository policy.
Its checks validate structure/links, not cloud access, bootstrap success or 50-minute task fit.