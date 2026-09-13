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
| [Repository MCP configuration](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/configure-mcp-servers) | Cloud MCP tools require repository configuration; local VS Code bindings do not transfer automatically. No OwlBear MCP configuration is required for the in-process tests below. |
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

### Cloud Capability Contract

The implementation needs repository read/edit tools, a shell able to run the locked Python/Node
toolchains, and platform branch publication. It does **not** need this chat's VS Code tools,
subagents, language server, OwlBear MCPs or MegaLinter. This is a source-verified execution path,
not a claim that the user's cloud environment has already passed the pilot.

For these cloud jobs, **do not start or configure an OwlBear MCP server**. GitHub can support
configured MCP servers in general; their absence here is intentional, not a fatal prerequisite.
Testing MCP server code is different from using a live MCP tool as the agent's execution interface.

| Need or unavailable capability | Cloud route and evidence limit |
| --- | --- |
| Delivery core behavior | Owning pytest suites with temporary repositories, fake clocks and provider fixtures. Run real owners; do not replace the behavior under test with a mock. |
| Registered MCP tools, schemas and envelopes | [Existing tests](../../serve/delivery-mcp/tests/test_target_server.py) assemble the real server object and use `Client(server)` in-process. Tests cover listing, invocation, rejected arguments and a fixture-backed runtime transition. No daemon, listening port or agent MCP binding is needed; this does not prove stdio/remote transport or VS Code discovery. |
| HTTP behavior | [Existing route tests](../../tests/test_cockpit_work_items.py) use the test application/client and disposable fixtures rather than a live Cockpit installation. |
| UI behavior and types | The [frontend scripts](../../serve/cockpit/web/package.json) provide Vitest, TypeScript/build and direct lint. If browser execution works, use Playwright's disposable harness; no browser MCP tool is required. |
| Real browser geometry/focus | `npm run test:e2e:work` uses a temporary workspace and local fixture server through [the harness](../../serve/cockpit/web/e2e/support/start-work-portfolio-stack.mjs). If browser binaries, subprocesses or local ports are unavailable, record a pending browser check and continue unit/build work; jsdom is not equivalent proof. |
| Editor diagnostics, symbol search, skill loading | Read repository-relative instruction/skill files with available file/shell tools; use text search and compiler/linter diagnostics. Do not require `get_errors`, `tool_search`, a rename provider or a VS Code task API. |
| Native agents, memory and live host handoffs | Do not invoke claim-dependent Planner/Builder/Finalizer workflows, memory bootstrap or nested subagents. Validate their files/contracts with existing tests; actual host dispatch/review and termination capabilities remain host checks. |
| Git and PR handling | Use the platform's permitted branch/commit/publication tools. No particular local helper binding or unrestricted GitHub API token is a prerequisite. Preserve the assigned branch/owned scope; never broaden token permissions to reproduce this editor's tools. |

**MegaLinter is prohibited inside these agent sessions**, including installation/image pulls,
`uv run megalint`, `uv run quality`, `npx mega-linter-runner`, and Docker-based equivalents.
The [quality aggregate](../../serve/tools/src/owlbear_tools/quality.py) includes MegaLinter, so
it is not a fallback. Avoid uninspected aggregate hooks, whole-repository autofixes and broad
pre-commit runs. Use direct, check-only linters scoped to owned files instead, even when a general
skill recommends an aggregate. Do not change the repository's CI or disable a required check.
Existing CI can run MegaLinter separately on its configured infrastructure; absence of an agent-run
MegaLinter result never blocks implementation or creation of a reviewable PR.

Lightweight recipes, resolved against the departure revision and changed paths:

```shell
uv run --locked pytest serve/delivery-mcp/tests/test_target_server.py serve/delivery-mcp/tests/test_delivery_adapter.py -q --tb=short -n 0
uv run --locked pytest tests/test_cockpit_work_items.py -q --tb=short -n 0
uv run --locked pytest tests/test_agent_ecosystem_validation.py -q --tb=short -n 0
```

These are alternative owning scopes, not a mandatory combined gate for every edit. Add the touched
core suite or exact node IDs. Use direct `uv run --locked ruff check` and `ruff format --check` with
explicit changed Python paths; never run automatic fixes on unrelated files. In the frontend directory,
use `npm test -- <test-file>`, `npm run build`, and `npx --no-install eslint <changed-files>`;
use the maintained CSS/HTML checks when relevant. Existing locked tools are preferred to downloads.
Start pytest with one worker in constrained runners; split slow suites across sessions instead of
removing assertions or globally increasing timeouts. No full-suite/MegaLinter prerequisite to coding.

Local capability-path proof on 2026-09-13: **3 passed in 4.16 seconds** for
`test_registered_tool_invokes_strict_adapter_once`,
`test_flattened_tool_rejects_unknown_arguments_before_delegation`, and
`test_assembled_work_item_tools_observe_runtime_transition` in the registered-tool suite above,
using `uv run --locked pytest <node IDs> -q --tb=short -n 0 -p no:cacheprovider`.
No MCP daemon, live state or MegaLinter was used. This proves the existing in-process route is
executable locally; Linux cloud dependencies, resource limits and actual tool access still need the pilot.

### Nonfatal Capability Gaps and Real Blockers

Missing OwlBear MCP, VS Code APIs, memory, nested agents or MegaLinter is **expected**: use the
routes above without retry loops, installation attempts or a request for more credentials.
Mark transport/host/heavy checks `NOT_RUN_CAPABILITY` with the exact reason, affected claim,
replacement proof already run, and follow-up command/environment/owner. Preserve them in the
package plan's verification ledger and PR handoff, not only ephemeral chat. Missing browser or
lightweight lint binaries gets one bounded environment diagnosis, then the same treatment.

Continue implementing and testing the supported slice. Use `READY_FOR_INDEPENDENT_REVIEW` plus
`verification: partial` when scoped code and available meaningful proof are ready but external
checks remain. Use `CHECKPOINT_ONLY` if insufficient behavioral proof is available. A failing
assertion, compile error or introduced lint error is **not** a capability gap: repair it or record
the exact unresolved defect. Do not add skips or weaken tests to conceal it.

No shell, no usable dependencies, inability to publish, or a missing safety-critical contract can
block the affected slice. Keep already useful work and report the smallest unblock. Do not turn
one unavailable optional tool into abandonment of the entire package. If even the core behavior
cannot be exercised, publish an explicitly unverified draft, not a passing result.

The planner classifies proof before implementation: **cloud-required**, **external CI**, and
**host-only**. Intermediate phases can proceed after scoped proof and review when a recorded
external check does not invalidate their dependency contract. Do not claim whole-package acceptance
until its required checks are satisfied. Merge protections, safety-critical predecessor proof and
live activation gates remain unchanged; any change to a mandatory acceptance gate needs explicit
approval. Host-only product acceptance can remain pending after a code PR merges when the approved
plan already assigns it to D08-H, but it must not be reported as completed by cloud tests.

## 3. Preflight and Handoff

1. **Freeze a reviewed checkpoint with the other chat.** Confirm actual D02 completion, then start
   D03-P. If D02 is unfinished, prepare its exact remaining slice first. If some D03 work exists,
   reuse its reviewed commits and plan only the remainder; do not reimplement it or assume D04 is ready.
2. **Publish required context.** The user pushes the reviewed `dev` checkpoint and approved handoff.
   The preparing/cloud agent records source/plan/dependency revisions; the user does not look up or
   paste commit hashes. Cloud workers cannot see unpushed local work, the fork's
   chat or untracked B1 packages. Do not upload live state, private URLs, credentials or browser profiles.
3. **Verify access and review policy.** Check cloud agent availability, model picker, budget,
   concurrency and eligible human approvals. Always select `dev`, not generated consumer `main`.
   If another eligible human is required but unavailable, plan to accumulate candidate PRs, not merge.
4. **Run a real cloud pilot before departure.** Verify branch/SHA, read/edit/shell/publication tools,
   locked dependencies and one owning Python/in-process MCP test. For UI work, try build and the
   disposable browser harness; record unavailable capabilities rather than aborting other proof.
   No OwlBear MCP startup or MegaLinter is part of the pilot. Record setup duration and proof limits.
5. **Prepare deterministic setup if needed.** Reuse current CI's pinned actions/tool versions.
   A Copilot setup workflow only works once present on the actual default branch; do not change
   that branch or protections as a shortcut. Otherwise validate explicit bootstrap in the pilot.
6. **Resolve external verification.** Draft PRs here skip the source/Cockpit workflows even after permission
   to run workflows. The user marks appropriate PRs ready and approves workflow execution when needed.
   Alternatively use a supported manual workflow on the exact branch/head. Skipped means unrun.
   MegaLinter stays outside agent sessions. Lack of CI access does not stop code or PR work; it
   leaves the external gate pending and cannot authorize a merge that requires it.
7. **Finalize the first package handoff.** D03-P must produce the concrete paths/contracts/tests
   for its implementation phases. Bookmark the package PR for low-bandwidth access. Approve the
   displayed plan before implementation; let the agent resolve its revision and prepare the next prompt.

Bootstrap ingredients to verify in the pilot: uv required by [pyproject.toml](../../pyproject.toml),
`uv python install`, `uv sync --locked --all-packages --all-extras --all-groups`; Node from
[the pinned version](../../serve/cockpit/web/.nvmrc), `npm ci --engine-strict` in the frontend,
and the needed Python/Node Playwright browsers. Read the actual test harness before starting it.
Do not run workspace `setup/init.py`, configure laptop MCPs or disable safety controls to bootstrap.

### Cloud-Only Authorization

Cloud tasks use GitHub's normal branch, commit and publication workflow. Do not transplant the
local "one writer on dev" or "user pushes manually" procedure into the cloud session: publication
to the task's PR is necessary to deliver its work. The kickoff prompt explicitly requests that cloud
workflow for `maba-pag/owlbear`, with `dev` as the PR base. No manual branch creation or push command
is needed in the prompt. This does not authorize merging, changing protections, real provider effects
during tests or live activation. It does not alter how the local implementation fork operates.

GitHub's documented distinction matters: a **new task** creates a new branch from the selected base;
an **existing-PR comment** normally starts a session that updates that PR's branch. To continue the
same package, comment on its PR instead of starting another unrelated task from `dev`. Repository
access alone does not uniquely identify an intended PR; use the invocation's actual PR context.

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
   phase dependencies, negative cases, proof commands, exclusions and unresolved decisions. It has
   compact progress and verification sections separating cloud-required, external-CI and host-only
   proof with explicit fallback routes. It does not replace this guide or the programme authority.
3. Review the displayed plan, then approve it through the implementation comment on that PR.
   The agent resolves and records the revision being approved; the user need not copy its hash.
   If intervening specification edits make the approval ambiguous, ask for a plain-language
   confirmation of the changed plan. The planning-only PR need not be merged first.
4. Start A with the copy-ready PR comment below. The worker discovers this PR's head, reads its
   committed package plan and preceding discussion, verifies prerequisites, and implements only A.
   No PR number, paths, test commands or hashes need to be transcribed by the user. If the launch
   lacks PR context, ask for the PR link rather than guessing from repository access.
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

**Within-package barrier:** required cloud tests and independent review of the phase checkpoint,
with predecessor commits on the same branch and external gaps recorded as above. No unresolved
gap may invalidate the successor's safety contract. **Between-package barrier:** the approved
package merge requirements, checks/reviews and merge into the baseline used by the next package;
host-only acceptance explicitly assigned to D08-H remains pending rather than being fabricated.
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

## 6. Copy-Ready Cloud Prompts

### What Was Wrong With the Earlier Templates

- They made the user fill in PR IDs, commit hashes, plan paths, file lists and commands that the
   agent should discover or produce. Those are implementation bookkeeping, not human decisions.
- They mixed new-task and existing-PR launch mechanics, and asked for a PR number before one existed.
- They required a large common block plus another template, so neither was a useful standalone request.
- They repeated local push/custody procedures that do not describe GitHub's cloud publication path.
- They were precise about administrative inputs but vague about the actual D03 result.

The replacements below are complete requests: copy **one block**, not a common block plus a form.
No hashes, file lists, test commands, approval URLs or PR numbers need filling in. Select
`maba-pag/owlbear`, `dev` for a new package, and your model/reasoning depth in GitHub's UI.
The D03 examples are ready as written. For a later phase, change only the human-readable phase ID
(for example D03-B to D03-C); for a later package, use the exact kickoff prompt its planner prepares.

**Agent-owned bookkeeping:** discover the current checkout revision and, when invoked from a PR,
its number/base/head from the supplied context and available repository tools. Record revisions for
review/recovery yourself. The starting checkout SHA is not necessarily the PR base SHA; distinguish
what is actually observed. Find the package plan from the PR description or its package-specific
research file, and resolve files/tests from source. Do not ask the user to retrieve this metadata.
If PR context is genuinely absent or ambiguous, ask only for a PR link; do not assume the repository
has only one accessible PR. Missing optional metadata does not prevent source work, but a review
without a known comparison scope must be reported as limited, not invented.

Commit identities still matter for exact-code review and restart, but **the agent records them**.
Each session must end with a short result, actual proof/gaps, the observed revision and one fully
written suggested follow-up comment. The suggestion is not automatically authorized or dispatched.
Never ask the user to assemble the next prompt out of technical fields.

### Start D03 Planning

**Where:** new cloud task; choose `maba-pag/owlbear` and base `dev`. No PR exists yet.

```text
Prepare D03 for maba-pag/owlbear. Plan only; do not implement it yet.
Use the checkout GitHub supplied and its normal cloud commit/publication workflow.
Open a draft PR targeting dev for this package's plan and later implementation.

Read .owlbear/research/change-continuation-delivery-redesign.md for D03/P05/P10/P11,
and .owlbear/research/delivery-cloud-flight-handoff.md for cloud execution limits.
Check the current code and recorded D02 status. Reuse completed work; if a necessary
D02 prerequisite is unfinished, identify it rather than starting D02 or inventing it.

Plan how to recover retained failed claims/finalizers/engine actions without losing
work or replacing a worker that may still write; preserve foreign/staged/private
changes; bound equivalent retries across restart; and diagnose broken state offline.
Write .owlbear/research/delivery-cloud-d03-plan.md with concrete implementation
phases, owning files, interfaces, negative cases, tests, and explicit exclusions.
Separate cloud-executable proof from later CI/host checks. Aim for phases that fit
30 minutes of coding plus 15 minutes of proof, not one huge D03 session.

No live OwlBear MCP/Delivery workflows, live state or credentials. Do not install
or run MegaLinter or uv run quality. Read files and use ordinary available tools;
missing editor/MCP tools must not block planning. Do not change the main programme
plan or this flight guide. Leave genuine safety/product decisions visible.

Record the checkout revision yourself. Publish the plan through this cloud task,
summarize decisions I must make, give a ready-to-paste first implementation comment,
and stop by 50 minutes. Do not implement or merge anything.
```

### Approve the Plan and Start D03-A

**Where:** comment on the D03 PR after reading its plan. No PR number is needed in the text.
This approves the displayed plan for D03-A, not any unresolved permission/privacy decision.

```text
@copilot I approve the D03 plan currently presented in this PR. Implement D03-A only.
Use this PR's committed package plan and current code; discover and record the
revisions yourself. If the plan has changed since it was presented or a genuine
decision remains unresolved, explain the difference before acting on it.

Implement the planned worker-exclusion and recovery reference path: a worker that
may still write must not be replaced, and retained work/evidence must survive recovery.
Use existing owners and realistic restart/controlled-worker tests. Run a focused
behavior check immediately after the first substantive edit, then the affected tests.
Publish changes normally to this PR; do not create another package or merge it.

Follow .owlbear/research/delivery-cloud-flight-handoff.md's Cloud Capability Contract:
no live OwlBear MCP or Delivery workflows, no MegaLinter or uv run quality. Use
in-process tests, locked toolchains and scoped linters. Record unavailable external
checks and continue supported work; fix actual failures instead of weakening tests.

Update the package plan's progress and PR summary, not the programme authority.
Report actual results and the next ready-to-paste review or repair request. Publish
coherent checkpoints early and stop by 50 minutes, before D03-B. If unfinished,
preserve the partial result and say exactly what remains; do not claim completion.
```

### Start the Next Named Phase

**Where:** same PR, after review/repair of the predecessor. This example starts D03-B;
change only `D03-B` to the next phase named in the reviewed package plan when appropriate.

```text
@copilot Implement D03-B only, following the approved package plan in this PR.
Read the current branch, previous phase result and independent review. Verify that
the prerequisite code and required proof are present and review findings addressed.
Resolve paths, tests and revisions yourself; do not ask me to supply commit hashes.
Do not reinterpret an unchecked progress box as approval or start another phase.

Use GitHub's normal publication to this PR and the cloud capability rules in
.owlbear/research/delivery-cloud-flight-handoff.md. No live OwlBear MCP/Delivery,
MegaLinter or uv run quality. Run in-process behavior tests and scoped lint/build;
record unavailable external checks without abandoning supported implementation.
Repair real failures and preserve safety rules and existing evidence.

Update the package progress and PR summary with actual results, unresolved checks
and a ready-to-paste follow-up request. Publish checkpoints early, stop by 50 minutes
and leave the next phase for a separate instruction. Do not merge.
```

### Review the Current PR

**Where:** on the package PR, with the review model selected separately. A PR-comment session
has the PR context but can inherit previous conversation context; do not claim it is context-isolated.
For a fresh independent review, start a separate review task with the **PR URL attached**, remove
`@copilot` below, and use the same text. That link is the only input needed outside a PR context.

```text
@copilot Review this PR's latest implementation against its package plan and the
Delivery programme. Review only: do not edit code, apply fixes, approve or merge.
Determine and record the actual base/head revisions yourself. Inspect source and
tests rather than accepting the implementation summary as evidence.

Focus on custody, data preservation, replay, stale approval, privacy and missing
discriminating tests. Check the latest phase and its interaction with earlier phases;
if the package claims completion, assess the cumulative package diff and required proof.
Report concrete findings with severity and file references, or no findings with limits.

Use .owlbear/research/delivery-cloud-flight-handoff.md's cloud verification rules:
no live OwlBear MCP, MegaLinter or uv run quality. Distinguish proven behavior, reported
tests and checks awaiting CI/the real host. Missing expected cloud tools is not itself
a code defect or permission to waive a failed test. If review scope/context cannot be
resolved, ask for the PR link, not hashes. End with one ready-to-paste repair request
when needed and stop by 50 minutes. This report is not a required human approval.
```

### Repair Review Findings

**Where:** on the same PR, after the reviewer has returned findings.

```text
@copilot Address the latest independent review findings on this PR. Inspect the
current code and review evidence first; repair valid findings in the existing scope
and explain any disagreement with source/test evidence. Do not start another phase.
Use the committed package plan and discover revisions and affected tests yourself.

Follow .owlbear/research/delivery-cloud-flight-handoff.md's capability rules: no live
OwlBear MCP/Delivery, MegaLinter or uv run quality. Run focused regression tests and
scoped lint/build; report missing external checks separately from real failures.
Publish corrections normally to this PR without discarding good prior work.

Update the package progress and PR summary, mapping each finding to its correction
and proof. Give a ready-to-paste re-review request, then stop by 50 minutes. Do not
claim independent review has passed your new code and do not merge.
```

### Resume an Interrupted Phase

**Where:** on the same PR after timeout or a lost response. This continues the existing phase,
not whichever D package happens to be next in the programme.

```text
@copilot Resume the interrupted phase on this PR, not the next phase or package.
Inspect the published commits, package plan, latest task instruction, progress and
available session/check logs to determine what actually completed. Do not start over
or assume success from a missing final response. If the interrupted scope cannot be
identified, ask which phase; don't ask me to reconstruct hashes or test commands.

Preserve good committed work and finish only the remaining phase. Follow
.owlbear/research/delivery-cloud-flight-handoff.md: no live OwlBear MCP/Delivery,
MegaLinter or uv run quality; use in-process tests and scoped checks, and record
unavailable external verification without hiding genuine failures.

Publish coherent progress normally to this PR, update the package progress and give
actual proof plus one ready-to-paste next action. Stop by 50 minutes and do not merge
or advance to another phase. Request explicit approval before discarding prior work.
```

## 7. Low-Bandwidth Operating Cycle

1. Start D03-P after verifying reviewed D02, or the next explicitly approved phase on its package PR.
   Run one writer. Only launch parallel read-only work when separately approved and independent.
2. At the next connection, read the package PR's short status and request review or a bounded repair.
   Select the model in the new session/PR-comment UI, not in the pasted instruction.
3. After required cloud proof and independent review, approve the next phase on the same PR branch
   only if pending external checks do not invalidate its dependency contract. Carry the gap ledger.
   Allow required workflows/manual branch checks as appropriate; absent draft checks are not green.
4. When the package is complete, mark its PR ready, satisfy actual CI/approval requirements and
   review the cumulative exact head before merging. Repairs or base changes require relevant revalidation.
5. Start the next package from the merged published baseline. No connectivity means waiting safely.

The next preparation action is an actual cloud setup/pilot and a departure-SHA planning ticket,
not a new runtime automation system. This document does not dispatch work or change repository policy.
Its document checks validate structure/links, not cloud access or 50-minute task fit. In-process
test-path evidence must be reported separately from an actual cloud pilot; never conflate them.
