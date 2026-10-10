# Delivery Liveness-First Rebuild

> **Owning task:** none yet — user-requested direction research after the 2026-10-09 B1 dead end
> **Date:** 2026-10-09
> **Question:** Why does Delivery need manual repair so often, what is it supposed to do at the
> highest level, and what path of intermediate documents and products leads to a Delivery that
> reliably makes progress — possibly as a re-implementation with selective reuse?
> **Status:** Analysis and recommended roadmap, revision 2 (2026-10-10): corrected after six
> independent challenges and re-weighted by the user toward end-to-end design and failure modes
> (§1). Decided by the user: TD-1 to TD-8 (§3.8). Every other recommendation is `autonomous` until
> the user decides it.

## 1. Context and Question

On 2026-10-09 the B1 Change (`macos-managed-browser-authentication`) hit two new dead ends in one
continuation session after a full day of incident repair (N13-A/B merged, live upgrade, target
conflict resolution). The user asked for a step back: what Delivery is for, how it behaves in
practice, why, and what the way to a working system is. The user expects a large change, possibly a
re-implementation from scratch with reuse where beneficial.

A second, coupled question (section 3.9) is how the planned move away from the classic VS Code
Copilot Chat surface should be sequenced relative to this rebuild.

**User direction, 2026-10-10.** Delivery has never run a Change on a consumer project as intended:
one short consumer use about six months ago, not comparable to today, and otherwise only use on
OwlBear itself, in parts. History matters only as far as it improves the design; the weight belongs
on a watertight end-to-end journey and on failure modes — past designs caught obscure ones and missed
ordinary ones. Proof matters; test volume does not. Real consumer use should then need fixes, not
rework. The user keeps the open Changes running in parallel. The journey and failure catalogue are in
the companion [journey research](delivery-next-journey-and-failure-modes.md).

## 2. Sources Studied

| ID | Source | Relevant fact | Limits |
| --- | --- | --- | --- |
| L01 | [Redesign programme](change-continuation-delivery-redesign.md) §1 | States the product promise: one `/continue-change` per Change; the user never operates Delivery internals (U1–U5); failures have an owner and a bounded path | Agent-written requirements text labelled "from the user" (§3.8), not behavior |
| L02 | [Execution plan](delivery-redesign-execution-plan.md) | Programme declared complete 2026-10-06 (N10-M); N11–N13 followed as incident phases | Status as recorded by agents |
| L03 | Earlier reframes: [operating-model reframe](delivery-operating-model-reframe.md) (2026-07-25), [agent-driven redefinition](agent-driven-delivery-redefinition.md) (2026-08-02), [worktree-native redesign](delivery-worktree-native-redesign.md) (2026-08-10), [status-model rethink](delivery-status-model-rethink.md) (2026-10-07) | Four prior direction resets before this one | Read at header level only |
| L04 | `find`/`wc` over `serve/delivery*`, `serve/cockpit*` | Size figures in §3.2 | Line counts include docstrings and blank lines |
| L05 | Registry built in-process (see [tool-surface audit](delivery-tool-surface-audit.md)); `rg` over `serve/delivery*/src` | 64 registered MCP tools with 536 argument fields; 67 distinct `ERR_*` codes | Registry exact at `753eb92`; error count by pattern |
| L06 | `git log --since=2026-06-01` on Delivery paths | 689 commits; 369 subjects match fix/repair/recover/dead end/stuck/stale/regression | Keyword match on subjects; Delivery package paths exist since 2026-08-07 |
| L07 | Local Copilot session store, 2026-09-05 → 2026-10-09 | Intervention counts in §3.2 | Local machine only; counts turns that invoke the command; interventions in free chat are not counted |
| L08 | B1 package history and `git diff --shortstat 52f9f006…4e94543d` | B1 lifetime and product size | Product paths `serve share seed setup tests` only |
| L09 | [workspace_target_sync.py](../../serve/delivery/src/owlbear_delivery/workspace_target_sync.py) L864 | Engine-owned merge runs `git commit --no-edit`, which executes repository pre-commit hooks in the managed worktree | Observed failure: Biome missing `node_modules`, formatter auto-fix |
| L10 | [runtime_models.py](../../serve/delivery/src/owlbear_delivery/runtime_models.py) L528, L1085; [evidence.py](../../serve/delivery/src/owlbear_delivery/evidence.py) L469 | `procedure` is limited to 512 characters | The Builder skill did not state the limit at incident time; #443 added it on 2026-10-09. The transport error still names no field ([target_server.py](../../serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py) L1350) |
| L11 | `get_change` for B1 after the rejected settlement, 2026-10-09 | One card simultaneously reported "Ready for finalization", activity `ready`, readiness `running`/`active-custody`, "Claimed by Builder", and a read-only `/repair-delivery` prompt | Single observation |
| L12 | [Workspace instructions](../../.github/copilot-instructions.md) | "Never use Delivery to implement Delivery." | Policy text |
| L13 | [Distribution under the Agent Host](owlbear-distribution-agent-host.md) (2026-10-07) | `share/` customizations, prompts and agent-scoped hooks do not reach Copilot-harness sessions; MCP `cwd` differs by registration path | Static analysis of VS Code 1.140; no live probe |
| L14 | M1 and M2 results: [ownership map](delivery-next-ownership-map.md), [route comparison](delivery-next-route-comparison.md), [platform probe](delivery-next-platform-probe.md), [charter draft](delivery-next-charter.md) (2026-10-10) | Thin core on the Copilot runtime; Python SDK loop; loop-owned questions; default-deny permissions; termination by cancel and verify | Probe on a free personal account, Auto model, unprotected repository |
| W01 | [VS Code 1.141 release notes](https://code.visualstudio.com/updates/v1_141) (2026-10-07) | Copilot harness is built on the Copilot SDK, consistent with the Copilot app and Copilot CLI, runs in the Agent Host and "might already be the default"; it is "gradually becoming the default" for enterprise users | Release notes |
| W02 | [Choose and use an agent harness](https://code.visualstudio.com/docs/agents/run/agent-harnesses) | Recommends the Copilot harness for day-to-day work; Local is the extension-host workflow; worktree isolation per session; handoff between harnesses | Product docs |
| W03 | [Agent Host concept](https://code.visualstudio.com/docs/agents/concepts/agent-host) | Sessions survive window close; host is source of truth; reads `.mcp.json`, forwards `.vscode/mcp.json`; hooks are harness-specific | "Under active development" |
| W04 | [Prompt files](https://code.visualstudio.com/docs/agent-customization/prompt-files) | Prompt files are deprecated for Agent Host sessions; "the Local agent will be removed in a future release" | No removal date |
| W05 | [Migrate Copilot customizations](https://code.visualstudio.com/docs/agent-customization/migrate-customizations), [custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents) | `chat.*FilesLocations` read only by Local; prompts convert to skills; no automatic hook or tool-set migration; agent `hooks:` run only in Local | Migration is experimental |
| W06 | [Copilot SDK](https://github.com/github/copilot-sdk) | Generally available, Python package `github-copilot-sdk`; same engine as Copilot CLI; custom agents, skills, tools, hooks, MCP | README level |
| W07 | [GitHub Copilot in VS Code, September 2026](https://github.blog/changelog/2026-10-01-github-copilot-in-vs-code-september-2026-releases) | Agents window: PR creation from sessions, agent merge (review feedback, failed checks, conflicts, reruns; preview), automations, attention badges | Several items in preview |
| W08 | [Dynamic workflows changelog](https://github.blog/changelog/2026-10-01-dynamic-workflows-in-copilot-cli-and-the-copilot-app), [concept](https://docs.github.com/copilot/concepts/agents/dynamic-workflows), [how-to](https://docs.github.com/copilot/how-tos/use-copilot-agents/use-dynamic-workflows) | Code-defined orchestration with agents; structured results with format correction; pause/resume with saved results; user input; limits; available in Copilot CLI, Copilot app and SDK; defined in Copilot extensions (`extension.mjs`) | Public preview; VS Code support not stated |
| W09 | [Supported AI models per client](https://docs.github.com/en/copilot/reference/ai-models/supported-models) | GitHub's client list: GitHub.com, Copilot CLI, VS Code, Visual Studio, Eclipse, Xcode, JetBrains | Model availability table, not a licensing statement |
| W10 | [T3 Code repository](https://github.com/pingdotgg/t3code) | MIT; agent control surface over Codex, Claude Code, Cursor, Grok Build, OpenCode, Antigravity; no Copilot provider; v0.0.45, very early, large contributions not accepted | README level |
| W11 | [Copilot CLI ACP server](https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server) | Copilot CLI runs as an Agent Client Protocol server for IDEs, CI, custom front-ends and multi-agent systems; stdio or TCP; server-side tool filtering | Public preview |
| W12 | [OpenCode providers](https://opencode.ai/docs/providers/) | OpenCode offers a GitHub Copilot provider via device login; states some subscription plugins are prohibited by their vendor | Third-party claim; no GitHub endorsement found |

## 3. Analysis

### 3.1 What Delivery is supposed to do

From the highest level, Delivery has one job: turn an approved idea into a merged pull request with
as little of the user's attention as possible. The user approves intent, then repeats one command;
agents plan, build, review, repair, and publish; the user only decides, authenticates or confirms
person-only checks, and approves the merge (L01, U1–U5).

### 3.2 How it behaves in practice

| Measure | Value | Source |
| --- | --- | --- |
| Engine source | 60,511 lines in 55 modules (`serve/delivery/src`) | L04 |
| Engine tests | 60,529 lines (`serve/delivery/tests`) | L04 |
| Adapters and UI | MCP 3,107; GitHub provider 2,344; Cockpit backend 2,478; Cockpit web 25,811 lines | L04 |
| Agent-facing surface | 64 MCP tools (536 argument fields, none described), 67 error codes | L05 |
| Workflow prose agents must follow | 2,127 lines across eight Delivery skills | L04 |
| Change rate | 689 commits since 2026-06-01; 369 fix-type subjects | L06 |
| Planning volume | 53 Delivery research and plan documents | L03 |
| User interventions | 12 `/repair-delivery` (9 sessions), 2 attention and 1 target-conflict invocations versus 65 `/continue-change` invocations (29 sessions) | L07 |
| B1 cost | 26 sessions mentioning B1 over 2026-09-07 → 2026-10-09 for a product diff of 14 files, +966/−139 lines, still not merged | L07, L08 |

All of this is OwlBear working on itself; Delivery has never run a Change on a consumer project (§1).
The numbers show friction in self-use, not a production failure rate. They motivate the rebuild and
are deliberately not refined into a baseline. Delivery itself is built outside Delivery (L12), and fix
lanes kept adding special cases while this research was written (#442 on 2026-10-09, #440 on
2026-10-10).

### 3.3 The 2026-10-09 session as a microcosm

Every item below is an ordinary failure mode, not an obscure one.

1. **Self-conflict.** The target sync conflicted on four of Delivery's own package files
  (add/add), because Delivery authority is committed to both the target and the Change branch.
2. **Environment coupling.** The engine-owned merge commit failed with an opaque "Error executing
  tool": repository hooks ran inside the managed worktree, Biome lacked `node_modules`, and a
  formatter hook modified files (L09).
3. **Basis race.** The first acquisition returned `stale` because readiness changed between
  observation and acquisition.
4. **Contract at the wrong end.** The Builder wrote a block request whose `procedure` exceeded the
  512-character limit it was never told about (L10). Both `transition_delivery` and
  `settle_worker_invocation` rejected it; the claim stayed in `active-custody`; the only suggested
  route was a read-only diagnosis that states it cannot repair authority (L11).
5. **Contradictory status.** The same card showed five mutually inconsistent statements (L11). The
  engine already derives one progress state (`derive_delivery_progress` in `work_items.py`); other
  fields shown beside it contradicted it.
6. **Evidence churn.** The previously answered managed-Mac pilot was asked again after the merge.
  The merge changed four browser source files, so part of the re-check may have been legitimate;
  the defect is that no check records which inputs it depends on.

### 3.4 Root causes

| ID | Root cause | Mechanism | Evidence |
| --- | --- | --- | --- |
| RC1 | **Containment without an exit** | The programme's recovery rule (2026-09-25) is "bounded recovery now; explicit containment otherwise". Recovery coverage stayed narrow and containment ends in read-only diagnosis instead of an actionable exit, so unanticipated ordinary states become freezes that need the user | L01 §1.1, §3.3 items 2 and 4 |
| RC2 | **A deterministic loop executed by LLM prose** | The orchestrator is a skill, not code: a model copies 64-hex identities and basis fields and forwards large JSON transitions under ~2,100 lines of rules. The engine validates afterwards and can reject irreversibly (`retry_safe: false`). Normal-path tools require 5–12 copied hex identities each and use nested unions of up to 75 fields ([tool-surface audit](delivery-tool-surface-audit.md)) | §3.2, §3.3 item 4 |
| RC3 | **Entanglement with the managed repository** | Delivery state lives in product branches (self-conflicts), product hooks run in engine commits, worktrees lack dependencies, and the target moves continuously. Reviews and person-only checks do not record which inputs they depend on, so each target movement can re-ask them | §3.3 items 1, 2, 6 |
| RC4 | **Fix-by-addition** | Incidents mostly add a state, error code, tool, recovery route, prompt, or document: 72 of 81 production fix commits on Delivery since 2026-10-01 grew the code. Agent-authored plans, challenges and reviews produce precise contracts faster than whole journeys are proven | §3.2, L02, L03 |
| RC5 | **The UI projects the machine, not the work** | Users see custody, claims, bases, dispositions, attempts. The engine derives one progress state, but about 13 other fields computed in different layers are shown beside it and can disagree | §3.3 item 5; [status-model rethink](delivery-status-model-rethink.md) |
| RC6 | **Designed inward, never from the consumer journey** | Delivery was designed and exercised only on OwlBear itself. Failure analysis concentrated on integrity edge cases (identities, custody, races) while ordinary failures — product hooks, missing dependencies, limits unknown to authors, moved targets, closed sessions — surfaced only in use. Tests verify parts and even agent prose wording (110.7k lines of Python tests for 91.6k lines of Python source) instead of journeys | §1, §3.3; user, 2026-10-10 |

Underlying all six: the design is a ledger-grade, fail-closed system (exact identities, receipts,
custody) supervising fallible LLM workers in a fast-moving single-user repository. The declared
operating context — one trusted user, trusted but fallible agents, loopback-only Cockpit (L02 §1.9)
— makes much of that exactness costly relative to its value. Two guarantees remain essential:
unfinished work is never lost, and external effects are never duplicated. Git, GitHub pull requests,
CI, review, history, and revert already provide branch isolation, auditability, and recovery of
committed work that Delivery partially re-implements.

### 3.5 Why prior reframes did not converge

Each prior reframe (L03) correctly diagnosed a symptom and then added mechanism: graph authority,
worktree custody, continuation, settlement types, recovery routes, status projections. Deletion
lists (for example §13.2 of the worktree-native redesign) and assembled journey proofs (N10) did
exist, but they faced inward: journeys exercised OwlBear on itself with hand-authored worker
activity, no design walked a consumer's journey, and nobody catalogued ordinary failure modes. A
sixth reframe will repeat the pattern unless the design starts from the consumer journey and its
ordinary failures and keeps a binding size budget.

### 3.6 Target principles (recommended, not decided)

| ID | Principle | Replaces |
| --- | --- | --- |
| P1 | **Liveness first, within a safety boundary.** Every step ends in one of five exits — done, retry, ask, back, stop — as defined in the [journey research](delivery-next-journey-and-failure-modes.md#33-one-exit-contract-for-every-step). A stop preserves work and names one action. Unknown effects and possibly live workers are never replaced automatically | Containment ending in read-only diagnosis (RC1) |
| P2 | **Code runs the loop; agents do the creative work.** Deterministic sequencing, identities, and bookkeeping live in engine code, not skill prose | LLM orchestrator loop (RC2) |
| P3 | **Contracts at authoring time.** Workers receive output schemas and limits up front and validate before returning; malformed output becomes a bounded automatic retry, not a stuck claim. Agent-facing tools follow rules T1–T8 of the [tool-surface audit](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits): one job per tool, no copied identities, author calls the validating tool, every field described | End-of-pipe validation (RC2) |
| P4 | **Stay out of the product repository's way.** Delivery state is outside product branches; anything that touches product code — installs, checks, hooks, conflict resolution — runs inside an agent task with the fix loop; git/GitHub/CI own what they already own | Self-conflict and hook coupling (RC3) |
| P5 | **Evidence valid until its inputs change.** A review or person-only check records what it depends on — claim, procedure, covered files, relevant environment — and is requested again only when one of those changes | Re-asking on every commit (RC3) |
| P6 | **One user-level status per Change**, derived in one place, with one next action | 13 inconsistent fields (RC5) |
| P7 | **Budgets and subtraction.** Explicit limits on tools, states, error codes, tests and skill prose. Tool budgets per [audit rule T7](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits) | Fix-by-addition (RC4) |
| P8 | **Proof, not test volume** (direction TD-3). The design is proven by walking every journey stage and failure mode against the specification, then by real consumer use. Automated tests cover only engine logic whose failure would be silent; no assertions on agent prose wording; agent definitions get structural checks only | Tests of parts and wording instead of journeys (RC6) |
| P9 | **Fixable by design.** A fix is local when it keeps four contracts intact: approved interaction, ownership, preservation and replay, and evidence validity ([journey research §3.3](delivery-next-journey-and-failure-modes.md#33-one-exit-contract-for-every-step)). A failure that requires changing one of them sends that area back to M3 | Fix-by-addition (RC4) |

### 3.7 Roadmap: milestones, documents, and products

| # | Milestone | Deliverables | Exit criterion |
| --- | --- | --- | --- |
| M0 | **Stop growing old Delivery; let open Changes finish** | The user keeps the open Changes running (TD-2). Old-engine fixes only where those Changes need them, each naming what it later deletes. Other Delivery fix lanes are wound down after their work is preserved — no bulk cleanup. Failures seen in the open Changes become catalogue rows | No new old-engine mechanism without an open Change that needs it |
| M1 | **Ground truth (light)** | **Ownership map:** what git, GitHub, CI and the Copilot platform already own versus what Delivery must own; the [tool-surface audit](delivery-tool-surface-audit.md) is its tool part. **Route comparison** at design level: targeted repair, thin layer over GitHub and the Copilot platform, or new core. **R8 platform probe** as a separately authorized sandbox run (§3.9). No historical census or baseline metrics | Every Delivery responsibility has an owner; the route is chosen with reasons; every R8 probe has a result. Done 2026-10-10 (L14); the employer-seat and protected-merge probes are still to repeat |
| M2 | **Charter** | **R4** (one page): purpose, operating context, ownership, touchpoint budget, exit contract, non-goals, budgets for tools, states, error codes and tests; the earlier programme rules it supersedes, with reasons (§3.8) | User approval; later design cannot override it without re-deciding. Draft: [charter](delivery-next-charter.md) |
| M3 | **Watertight design** — most of the effort | **D1 end-to-end journey** and **D2 failure catalogue** for a consumer project (first draft: [journey research](delivery-next-journey-and-failure-modes.md)); **D3 status and exit model**; **D4 minimal architecture** on the Copilot runtime with the tool contract (TD-1); **D5 cutover plan** with a deletion list | Every journey stage and catalogue row has a concrete detection, exit and user-visible text; the connected traces of the journey research §3.6 hold; every necessary finding of the independent user-experience, failure-mode and consumer-fit challenges is resolved or rejected with evidence; user approval |
| E1 | **Content portability (enabling)** | Agents, skills and instructions that survive the rebuild moved to locations the Copilot harness reads (repository or plugin, per the [distribution research](owlbear-distribution-agent-host.md)); prompts converted to skills; `.mcp.json` registration; reviewer guards re-expressed as harness hooks or tool allow-lists. Non-Delivery content may move once R8 settles loading. Everything the Local-based Delivery needs stays in place until the open Changes finish. Delivery skills scheduled for deletion are not ported | Non-Delivery workflows run in a Copilot-harness session; Local workflows still work; M4 can load its agents |
| M4 | **Build in vertical slices** | The journey built stage by stage on a sandbox consumer repository (non-OwlBear toolchain, CI, branch protection), each slice demonstrated end to end. The common failure rows are triggered by hand once. Automated tests only per P8 | The whole journey runs once on the sandbox; every hand-triggered common failure ends in its designed exit and, once its prerequisite is restored, continues to the next successful step; one interruption with an unconfirmed push or PR ends without lost work or duplicate effects; touchpoints stay within the budget. A failed gate returns the affected contract to M3 |
| M5 | **First real consumer project** | Real Changes on a consumer project | Changes merged; every problem found is fixed locally (P9); anything that changes one of the four contracts returns to M3 for that area |
| M6 | **Cutover and deletion** | OwlBear's own Changes and the status view switched to the new core; open work finished on the old core (M0); old engine, tools, skills, tests and superseded research retired; product documentation updated | Size within R4 budgets; old Delivery skills and tools no longer exist |
| M7 | **Budgets (continuous)** | Budget tests for tools, states, error codes and test volume; every real-use failure becomes a catalogue row | Budgets hold |

M1 is read-only except for the separately authorized R8 sandbox probe. M4 must not start before M2
and M3 are approved. Most of the effort belongs in M3: past designs failed on ordinary failure
modes, not for lack of history or test volume. The new core is built on the Copilot runtime, not on
the Local harness; the old Delivery keeps running on Local until M6.

### 3.8 Decisions reserved for the user

| ID | Decision | Recommendation |
| --- | --- | --- |
| Q1 | Rewrite the core, refactor in place, or shrink to a thin layer | M1 result: routes 2 and 3 merge into a thin core on the Copilot runtime beside the old engine; targeted repair rejected; about 1k lines reused as is and 3.5k adapted, copied rather than imported ([route comparison](delivery-next-route-comparison.md)) |
| Q2 | Where Delivery state lives | Outside product branches |
| Q3 | Evidence validity | Valid until its recorded inputs change (P5) |
| Q4 | Who runs the loop | Engine code (P2) |
| Q5 | What the user sees | One status line and one next action per Change (P6) |
| Q6 | Sequencing with the VS Code agent-platform migration | Integrate (§3.9 option S3): the Copilot runtime is a design input of M2/M3 and the base of M4; content portability (E1) runs as an enabling track; no port of the current Delivery |
| Q7 | Programmable loop technology | R8 result: a small Python loop on the Copilot SDK. Dynamic workflows are not loadable in Python SDK sessions and stay optional for parallel reviews inside one step; structured output is experimental ([probe](delivery-next-platform-probe.md)) |
| Q8 | Switch to a third-party agent front-end | No; isolate Copilot SDK calls in ordinary modules and build no front-end abstraction (§3.10) |
| Q9 | Status and interaction surface | Charter proposal: Cockpit as status and answer surface, chat for conversation, and a local host that starts bounded runners ([charter §3.7](delivery-next-charter.md#37-interaction-surface-and-runner-activation)); this keeps tool rule T6 as decided |

**Provenance of earlier "user decisions".** Until 2026-10-10 the programme documents labelled agent
choices and user choices alike as user decisions. This plan therefore treats every earlier record as
`autonomous` unless the user's own words are found; superseding one only needs its reason recorded.

| Earlier record | User's own words found | Treatment here |
| --- | --- | --- |
| "Bounded recovery now; explicit containment otherwise" ([programme §1.1](change-continuation-delivery-redesign.md#11-requirements-from-the-user), 2026-09-25) | None; the phrase appears only in agent-written plans and checks | `autonomous`; superseded by P1, because containment ended in read-only diagnosis (RC1) |
| Native VS Code Orchestrator, not Copilot CLI, sampling or another runtime (same section, 2026-09-30) | A question and a proposal: "why we would need the gh copilot cli … we have vs code copilot to use", and the Orchestrator re-dispatching the Builder on retry | Rule text `autonomous`. The concern still holds: the Copilot SDK is the runtime VS Code's Copilot harness already uses, not an extra tool. Where the loop runs is settled after R8 (Q7) |
| Requirements U1–U8 (same section, "from the user") | No direct source; consistent with the user's 2026-09-11/12 complaints that Delivery is overbuilt and asks him to do things he cannot understand | `autonomous` input; the touchpoint budget and exit contract of the journey research replace them |
| U-1 push and PR authority with "never merge" ([execution plan](delivery-redesign-execution-plan.md), 2026-10-02) | Per-task grants: "commit and push your changes, run ci … you have my explicit authorization"; "auth to implement, commit, push, run ci, merge" (2026-10-02/03) | Push, PR and merge are granted per task in the user's prompts; "never merge" was the workspace-governance default |
| "Never use Delivery to implement Delivery" ([workspace instructions](../../.github/copilot-instructions.md)) | Creating a Change inside Delivery for monumental changes to Delivery "will never work" (2026-09-11) | The user's direction; kept |

**Recorded decisions.**

| ID | Decision | Origin | Date |
| --- | --- | --- | --- |
| TD-1 | Agent-facing tools follow rules T1–T8 of the [tool-surface audit](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits); T7 budget values are set in R4 | `decided`: "make your proposed rules accepted decisions" | 2026-10-10 |
| TD-2 | The open Changes continue on the old engine in parallel until finished; their failures feed the catalogue | `decided`: "i do want to finish the open changes … i will keep them going in parallel" | 2026-10-10 |
| TD-3 | Proof over test volume: automated tests are build artifacts and stay minimal; no tests of agent prose wording; structural checks of agent definitions remain. The concrete policy (P8) and budget are set in R4 | `decided`: "proof are important. tests are not. tests are build artifacts"; operationalization `autonomous` | 2026-10-10 |
| TD-4 | Stay on GitHub Copilot | `decided`: "we are bound to github copilot, so we cant just switch platforms" | 2026-10-09 |
| TD-5 | Local Copilot CLI and Copilot SDK use with the user's seat is allowed by the employer; probe tools may be installed (CLI user-level, SDK in an isolated environment) | `decided` (answered question) | 2026-10-10 |
| TD-6 | Sandbox repository for R8 and M4 under `maba-pag`, or under `boecht` when that is the signed-in account | `decided` (answered question) | 2026-10-10 |
| TD-7 | Research commits are pushed directly to `dev` | `decided` (answered question) | 2026-10-10 |
| TD-8 | Overnight work proceeds as far as possible, without a Copilot usage limit | `decided` (answered question) | 2026-10-10 |

### 3.9 Platform migration interplay

**Findings.**

- **F1 One runtime, several front-ends.** The recently launched agent surfaces are front-ends of one
  GitHub Copilot runtime, the engine behind Copilot CLI: VS Code's Copilot harness on the Agent Host
  (Chat view and Agents window), the standalone GitHub Copilot app, and Copilot CLI. The Copilot SDK
  exposes the same runtime to programs; the cloud agent is a remote target that returns pull
  requests. Claude and Codex harnesses are third-party and outside the GitHub Copilot constraint
  (W01, W02, W06).
- **F2 Local is legacy.** OwlBear runs on Local, the extension-host chat. It works "for now" and "will
  be removed in a future release"; the Copilot harness is the recommended day-to-day target and is
  gradually becoming the default (W01, W02, W04). No removal date is published.
- **F3 OwlBear's loading path is Local-only.** `chat.*FilesLocations`, prompt files, agent-scoped
  hooks, tool sets and profile-stored customizations are not read by the Copilot harness;
  `.vscode/mcp.json` is forwarded but superseded by `.mcp.json` (W03–W05, L13).
- **F4 The platform now ships what Delivery re-implements.** Per-session worktree isolation, pull
  request creation from sessions, agent merge that handles review feedback, failing checks and merge
  conflicts (preview), scheduled automations, attention badges, and sessions that survive window
  closure (W02, W03, W07).
- **F5 Code-defined orchestration exists.** Dynamic workflows define steps in code, call agents for
  judgment, request structured results with automatic format correction, pause and resume with saved
  step results, ask the user, and enforce limits — the shape P1–P3 require. They are in public
  preview, documented for Copilot CLI, the Copilot app and the SDK (not VS Code), and are written as
  JavaScript Copilot extensions (W08). The Python SDK offers the same runtime without that dependency
  (W06).

**Sequencing options.**

| Option | Benefit | Cost and risk | Verdict |
| --- | --- | --- | --- |
| S1 Migrate first: port current OwlBear including Delivery to the Copilot harness, then rebuild | Leaves the deprecated base early | Ports ~2,100 lines of loop prose, Local hooks, prompts and worktree-hostile MCP binding (Delivery refuses linked worktrees) for a system scheduled for replacement; likely a new incident wave | Reject |
| S2 Rebuild on Local, migrate after | Familiar base | Designs the new loop around primitives being removed (prompt files, Local hooks, subagent-driven loop); designs twice; exposed to an unannounced Local removal | Reject |
| S3 Integrate: the Copilot runtime is a design input; the skeleton is built on it; old Delivery stays frozen on Local until cutover | One design; reuses platform worktrees, PR creation, merge assistance and orchestration instead of re-implementing them; largest deletion | Several platform features are previews and change monthly; capabilities must be proven first (R8); old Delivery depends on Local until M6 | Recommend |

Under S3, which surface to use: the VS Code Copilot harness (Session Target **Copilot**, Agents
window) for interactive work; the Copilot SDK for the deterministic loop, compared with dynamic
workflows invoked through the SDK (Q7). Choosing the harness does not lock OwlBear out of Copilot
CLI or the Copilot app, because all three share the runtime and repository customization formats
(W05). A shared runtime does not mean shared sessions, settings or permissions; R8 must name which
surface owns each.

**R8 probe list** (sandbox repository, explicitly authorized, because it creates sessions and pull
requests): custom agents dispatching subagents with model selection; skills invoked as slash
commands with arguments; `.mcp.json` server `cwd` in folder and worktree sessions; repository hooks
or tool allow-lists enforcing a read-only reviewer; a user-question tool; a Python SDK program
driving a session with a custom agent and receiving a schema-validated result; **one round trip of
question, answer and resume while VS Code is open**; which surface owns the session, the question and
permission UI, the worktree, the pull request and the merge; **unattended tool permissions** (journey
row B7); continuation after the window closes (row X1); **how the runtime confirms that a session
and the commands it started have ended** (DR10), and what the user can do when it cannot; dynamic
workflows through the SDK; PR
creation and agent-merge behavior; **billing identity, the cost of one Change, and behavior when
quota runs out**; employer authorization for local SDK or CLI use (confirmed, TD-5), and company policy for plugins,
extensions and experimental flags.

**Risks.** Preview features may change or disappear; mitigate by depending only on R8-proven,
preferably generally available capabilities. If Local removal is announced before M6, pin the VS
Code version for the frozen path or accelerate cutover. Enterprise policy may block plugins,
extensions or experimental CLI features; R8 checks this before M3 commits to them.

### 3.10 Third-party platforms (quick check, 2026-10-10)

Question: could OwlBear leave VS Code for an open-source agent front-end such as T3 Code, building
modules beside it or forking it, while staying on GitHub Copilot?

**The gate is how the front-end reaches Copilot.**

| Route | Who documents it | Status for OwlBear |
| --- | --- | --- |
| VS Code, Copilot CLI, Copilot app, Visual Studio, JetBrains, Xcode, Eclipse | GitHub (W09) | First-party clients |
| Copilot SDK in our own program | GitHub; GA; supports signed-in user, OAuth GitHub App and tokens (W06) | GitHub-documented for embedding Copilot, subject to enterprise authorization |
| Copilot CLI as an ACP server driven by any client | GitHub; public preview; use cases include custom front-ends and multi-agent systems (W11) | GitHub-documented, subject to enterprise authorization; the front-end supplies UI, Copilot CLI supplies the agent and auth |
| Third-party tool calling Copilot models directly with a device-login token (for example OpenCode's GitHub Copilot provider) | Only the third party (W12) | Not found in GitHub's client list; compliance unconfirmed |
| Reverse-engineered Copilot API proxies | Neither (local research [887](887-copilot-sdk-vs-openai-compat-endpoint.md)) | Excluded: carries terms-of-service and abuse-detection risk |

**T3 Code (W10).** MIT-licensed TypeScript "agent harness control surface" (desktop, web and mobile)
over Codex, Claude Code, Cursor, Grok Build, OpenCode and Antigravity. It has no GitHub Copilot
provider; Copilot would arrive only through OpenCode's direct provider (unconfirmed compliance) or a new
ACP or SDK adapter written and maintained by OwlBear. It is at v0.0.45, "very very early", and does not
accept large contributions, so a fork would carry its fast-moving codebase alone.

**Assessment.** Leaving VS Code does not remove the hard parts identified in this document: the
agent runtime is GitHub's in every compliant route, and RC1–RC6 are OwlBear design problems, not
front-end problems. A third-party front-end would add an integration layer (ACP or SDK) plus a UI
codebase to maintain, while GitHub's own surfaces gain sessions, worktrees, PR flow and orchestration
monthly (§3.9). The compliant third-party routes are the same SDK and ACP interfaces the rebuild can
use from VS Code; designing the engine against them (Q7) keeps a later front-end switch open
without committing to one now.

**Recommendation (autonomous):** do not switch platforms now. Isolate Copilot SDK calls in ordinary
modules and build no front-end abstraction. A broader comparison of agent
front-ends is worthwhile only if R8 shows the Copilot harness cannot host the skeleton; then compare
candidates that drive Copilot through ACP or the SDK, not through direct model access.

## 4. Recommendation, Confidence, and Limits

**Recommendation:** treat this as a re-founding with the weight on design. Let the open Changes
finish on the old engine while it stops growing (M0). Keep the groundwork light: ownership map,
route comparison and the R8 platform probe (M1). Make the charter a set of explicit user decisions
(M2). Put most of the effort into a watertight end-to-end journey and failure
catalogue for a consumer project, challenged independently (M3). Build in vertical slices on a
sandbox consumer repository, proven by demonstration with tests only per P8 (M4). Then use it on a
real consumer project and expect fixes, not rework (M5), and delete the old engine (M6). Integrate
the platform migration rather than sequencing it (S3).

**Confidence:** high that ordinary failures nobody designed for, together with an inward-facing
design (RC6), explain the observed pattern; every 2026-10-09 incident was ordinary. Medium on the
relative weight of RC1–RC5, because self-use data is thin and is deliberately not refined further.
Medium on how much code is reusable.

**Limits:** metrics are local proxies from self-use only. Likelihood labels in the failure catalogue
are judgments to be corrected by real use. This document does not change any Delivery authority,
lane, or live state.
