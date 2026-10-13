# Delivery Liveness-First Rebuild

> **Owning task:** none yet — user-requested direction research after the 2026-10-09 B1 dead end
> **Date:** 2026-10-09
> **Question:** Why does Delivery need manual repair so often, what is it supposed to do at the
> highest level, and what path of intermediate documents and products leads to a Delivery that
> reliably makes progress — possibly as a re-implementation with selective reuse?
> **Status:** Analysis and recommended roadmap, revision 2 (2026-10-10): corrected after six
> independent challenges and re-weighted by the user toward end-to-end design and failure modes
> (§1). Decided by the user: TD-1 to TD-37 (§3.8). Every other recommendation is `autonomous` until
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
ordinary failures and keeps binding size and style rules.

### 3.6 Target principles (recommended, not decided)

| ID | Principle | Replaces |
| --- | --- | --- |
| P1 | **Liveness first, within a safety boundary.** Every step ends in one of five exits — done, retry, ask, back, stop — as defined in the [journey research](delivery-next-journey-and-failure-modes.md#33-one-exit-contract-for-every-step). A stop preserves work and names one action. Unknown effects and possibly live workers are never replaced automatically | Containment ending in read-only diagnosis (RC1) |
| P2 | **Code runs the loop; agents do the creative work.** Deterministic sequencing, identities, and bookkeeping live in engine code, not skill prose | LLM orchestrator loop (RC2) |
| P3 | **Contracts at authoring time.** Workers receive output schemas and limits up front and validate before returning; malformed output becomes a bounded automatic retry, not a stuck claim. Agent-facing tools follow rules T1–T8 of the [tool-surface audit](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits): one job per tool, no copied identities, author calls the validating tool, every field described | End-of-pipe validation (RC2) |
| P4 | **Stay out of the product repository's way.** Delivery state is outside product branches; anything that touches product code — installs, checks, hooks, conflict resolution — runs inside an agent task with the fix loop; git/GitHub/CI own what they already own | Self-conflict and hook coupling (RC3) |
| P5 | **Evidence valid until its inputs change.** A review or person-only check records what it depends on — claim, procedure, covered files, relevant environment — and is requested again only when one of those changes | Re-asking on every commit (RC3) |
| P6 | **One user-level status per Change**, derived in one place, with one next action | 13 inconsistent fields (RC5) |
| P7 | **Size and style rules and subtraction.** Countable limits on tools, step kinds, exits, error kinds and test volume (tool counts per [audit rule T7](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits)); modules split by use case with one owner per decision; agent instructions follow a language style instead of line ceilings (TD-19, [charter §3.9](delivery-next-charter.md#39-size-and-style-rules)) | Fix-by-addition (RC4) |
| P8 | **Proof, not test volume** (direction TD-3). The design is proven by walking every journey stage and failure mode against the specification, then by real consumer use. Automated tests cover only engine logic whose failure would be silent; no assertions on agent prose wording; agent definitions get structural checks only | Tests of parts and wording instead of journeys (RC6) |
| P9 | **Fixable by design.** A fix is local when it keeps four contracts intact: approved interaction, ownership, preservation and replay, and evidence validity ([journey research §3.3](delivery-next-journey-and-failure-modes.md#33-one-exit-contract-for-every-step)). A failure that requires changing one of them sends that area back to M3 | Fix-by-addition (RC4) |

### 3.7 Roadmap: milestones, documents, and products

| # | Milestone | Deliverables | Exit criterion |
| --- | --- | --- | --- |
| M0 | **Stop growing old Delivery; let open Changes finish** | The user keeps the open Changes running (TD-2). Old-engine fixes only where those Changes need them, each naming what it later deletes. Other Delivery fix lanes are wound down after their work is preserved — no bulk cleanup. Failures seen in the open Changes become catalogue rows | No new old-engine mechanism without an open Change that needs it |
| M1 | **Ground truth (light)** | **Ownership map:** what git, GitHub, CI and the Copilot platform already own versus what Delivery must own; the [tool-surface audit](delivery-tool-surface-audit.md) is its tool part. **Route comparison** at design level: targeted repair, thin layer over GitHub and the Copilot platform, or new core. **R8 platform probe** as a separately authorized sandbox run (§3.9). No historical census or baseline metrics | Every Delivery responsibility has an owner; the route is chosen with reasons; every R8 probe has a result. Done 2026-10-10 (L14); the `maba-pag` probe (TD-17) is still to run |
| M2 | **Charter** | **R4** (one page): purpose, operating context, ownership, touchpoint budget, exit contract, non-goals, size and style rules (TD-19); the earlier programme rules it supersedes, with reasons (§3.8) | User approval; later design cannot override it without re-deciding. Draft: [charter](delivery-next-charter.md) |
| M3 | **Watertight design** — most of the effort | **D1 end-to-end journey** and **D2 failure catalogue** for a consumer project (first draft: [journey research](delivery-next-journey-and-failure-modes.md)); **D3 status and exit model**; **D4 minimal architecture** on the Copilot runtime with the tool contract (TD-1); **D5 cutover plan** with a deletion list | Every journey stage and catalogue row has a concrete detection, exit and user-visible text; the connected traces of the journey research §3.6 hold; every necessary finding of the independent user-experience, failure-mode and consumer-fit challenges is resolved or rejected with evidence; user approval. Drafts 2026-10-10, challenged once and corrected: [status and exits](delivery-next-status-and-exits.md), [architecture](delivery-next-architecture.md), [cutover](delivery-next-cutover.md) |
| E1 | **Content portability (enabling)** | Agents, skills and instructions that survive the rebuild moved to locations the Copilot harness reads (repository or plugin, per the [distribution research](owlbear-distribution-agent-host.md)); prompts converted to skills; `.mcp.json` registration; reviewer guards re-expressed as harness hooks or tool allow-lists. Non-Delivery content may move once R8 settles loading. Everything the Local-based Delivery needs stays in place until the open Changes finish. Delivery skills scheduled for deletion are not ported | Non-Delivery workflows run in a Copilot-harness session; Local workflows still work; M4 can load its agents |
| M4 | **Build in vertical slices** | The journey built stage by stage on a sandbox consumer repository (non-OwlBear toolchain, CI, branch protection), each slice demonstrated end to end. The common failure rows are triggered by hand once. Automated tests only per P8 | The whole journey runs once on the sandbox; every hand-triggered common failure ends in its designed exit and, once its prerequisite is restored, continues to the next successful step; one interruption with an unconfirmed push or PR ends without lost work or duplicate effects; touchpoints stay within the budget. A failed gate returns the affected contract to M3. First slice: one sandbox Change through ask → answer → resumed build ([architecture](delivery-next-architecture.md)). Slice 1 built overnight 2026-10-10 as a prototype on branch `next/m4-slice1` (draft PR #449, not merged before charter approval): engine core, SDK runner, host; each phase challenged, repaired and demonstrated live in the sandbox. Slice 2 ran the whole journey once in the sandbox — build, review, person-only check, publish, CI, consent bound to the head, merge, cleanup — plus a CI failure fixed by a Builder task and consent voided by a head change. Every failure found live or by review was fixed locally without a new exit or state (P9). Slice 3 added the chat entry, planner, brief review, setup with readiness, profile confirmation and consent-gated writes, and ran from a chat-shaped brief to a merged PR with only brief approval and merge consent as touchpoints. Next: PR #449 continues as the base, reshaped to the module rules (TD-18, TD-19); the first release before real-project use (TD-20) adds the New Change button, automatic merge with pull-back instead of merge consent, thread replies and resolution, the agent visual check, a Change card with a deterministic "now" line, step time, a quiet warning and credits |
| M5 | **First real consumer project** | Real Changes on consumer projects; OwlBear itself keeps being developed directly in chat (TD-10) | At least two Changes merged in consumer projects; every problem found is fixed locally (P9); anything that changes one of the four contracts returns to M3 for that area |
| M6 | **Cutover and deletion** | No switch of OwlBear's own development (TD-10). The open Changes finish on the old engine (M0, TD-2); then one deletion PR retires the old engine, tools, skills, tests and superseded research and updates product documentation | Done after the open Changes finish and two Changes merged in consumer projects; size and style rules of R4 hold; old Delivery skills and tools no longer exist |
| M7 | **Size and style rules (continuous)** | Tests for tool counts, step kinds, exits, error kinds, test volume, module size by use case and ruff complexity; every real-use failure becomes a catalogue row | Rules hold |

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
| Q9 | Status and interaction surface | Charter proposal: Cockpit as status and answer surface with a New Change button that opens VS Code chat (TD-13), chat for conversation, and a local host that starts bounded runners ([charter §3.7](delivery-next-charter.md#37-interaction-surface-and-runner-activation)); this keeps tool rule T6 as decided |

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
| TD-2 | The open Changes continue on the old engine in parallel until finished; their failures feed the catalogue | `decided`: "i do want to finish the open changes … i will keep them going in parallel"; re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-3 | Proof over test volume: automated tests are build artifacts and stay minimal; no tests of agent prose wording; structural checks of agent definitions remain. The concrete policy (P8) and budget are set in R4 | `decided`: "proof are important. tests are not. tests are build artifacts"; operationalization `autonomous`; re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-4 | Stay on GitHub Copilot | `decided`: "we are bound to github copilot, so we cant just switch platforms"; re-confirmed in the read-back of 2026-10-11 | 2026-10-09 |
| TD-5 | Local Copilot CLI and Copilot SDK use with the user's seat is allowed by the employer; probe tools may be installed wherever convenient | `decided` (answered question); read-back 2026-10-11: "Yes, allowed; install them wherever convenient" (the isolated installs of the earlier record were the assistant's addition) | 2026-10-10 |
| TD-6 | Sandbox repository for R8 and M4 under `maba-pag`, or under `boecht` when that is the signed-in account | `decided` (answered question) | 2026-10-10 |
| TD-7 | OwlBear's own research is committed to `dev` and pushed right away, for now. Later, one shared documents repository for all projects, a folder per project, takes project research and the former `.owlbear/` documents, OwlBear's own included; consumer projects no longer contain them. Research about a consumer project is never committed into that project | `decided` (answered question); read-back 2026-10-11 ("commit to dev and push right away FOR NOW; once we implemented the separate repo …"), readings chosen 2026-10-11: "One shared documents repository for all projects, a folder per project" | 2026-10-10 |
| TD-8 | Overnight work proceeds as far as possible, without a Copilot usage limit | `decided` (answered question) | 2026-10-10 |
| TD-9 | OwlBear is for the owner's personal use on his laptop; a colleague would at most read the repository and build their own variant | `decided`: "this project is for personal use on my laptop"; re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-10 | Delivery-next need not support OwlBear developing itself; OwlBear keeps being developed directly in chat. Not a goal now; looked at again after the first real project. TD-2's open Changes still finish on the old engine | `decided`: "i dont need it to work on itself" (forked chat); read-back 2026-10-11 ("No; it may, if its possible as an almost free byproduct, but its not a design goal"), readings chosen 2026-10-11: "Not a goal now; look at it again after the first real project" | 2026-10-10 |
| TD-11 | Setup writes `.vscode/tasks.json` (host start on folder open) and `.mcp.json` (chat tools) only with consent; nothing from OwlBear is committed into the consumer project | `decided`: approved the fork's proposal | 2026-10-10 |
| TD-12 | Parallel Changes that overlap: do not ask by default; show "overlaps with X"; integration handles conflicts; ask only on real behavioural collisions; docs, lockfiles and generated files are ignored | `decided`: "proposal sounds good, approved" (forked chat; wording is the fork's) | 2026-10-10 |
| TD-13 | A "New Change" button in Cockpit opens VS Code chat with the shaping skill, so no prompt is copied | `decided`: "approved the button to start chat" | 2026-10-10 |
| TD-14 | UI changes always get visual testing of design and layout. The agent's visual check is enough for the automatic merge, except when the agent is unsure or the brief declares a person-only check: then the merge waits until the owner has looked. The owner can always look at any screenshot on the card without anything waiting | `decided`: "there needs to always be visual testing regarding design and layout"; answered question; read-back 2026-10-11 ("i only look if the agent is unsure OR a manual review is defined"), readings chosen 2026-10-11: "Merge waits in both cases, and I can always look at any screenshot on the card without anything waiting" | 2026-10-10 |
| TD-15 | Delivery merges automatically once every gate passes, including no unanswered comments or open discussions, and pulls the result back to the local clone | `decided`: "letting the agent/delivery also merge automatically … this ofc also needs to include automated pulls back to local"; re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-16 | Routine CI fixes and reactions to comments and reviews are automated, including replying to and resolving the threads an agent fixed. When human input is still needed stays open | `decided`: "fix ci, react to comments including reviews"; answered question; re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-17 | Copilot use runs on `maba-pag`'s business seat (required). Target: every GitHub write (push, PR, comment, merge) by the repository owner's account where possible, otherwise by `maba-pag` as collaborator. Start: `maba-pag` does everything as collaborator; switch once the target works | `decided` (forked chat); read-back 2026-10-11 ("maba-pag is required for copilot use. it would be great if its possible to use any other user …"), readings chosen 2026-10-11: "Aim for the first reading, but start with maba-pag doing everything and switch once it works" | 2026-10-10 |
| TD-18 | The prototype (PR #449) is the base to continue, reshaped to the module rules (TD-19) | `autonomous`: delegated in the read-back of 2026-10-11 ("take your recommendation"). Reason: the retrospective review found specific contradictions to repair (C1–C7), not a wrong foundation; the reshaped modules and their live proofs stay usable | 2026-10-10 |
| TD-19 | No ceilings on agent instructions: they lose detail. Instead, a language style: specialist terms instead of fillers or explanations, but not "caveman" style. For code, a size limit is fine when exceeding it means splitting into more modules, not cutting logic; interface overhead is not counted | `decided`: "strict budgets for agents dont work … we should rather define language style … for code this does work if the ceiling means splitting into more files/modules"; re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-20 | First release, before real-project use: New Change button, automatic merge with pull-back, thread replies and resolution, agent visual pre-check, Change card with a deterministic "now" line, step time, quiet warning and credits, and the watcher agent. Notifications, scanner triage and a knowledge home wait for evidence from real use | `decided` (answered question); read-back 2026-10-11 added the watcher agent: "The six items, plus the watcher agent" | 2026-10-10 |
| TD-21 | No cost question: credits are shown per Change and step, never used to stop or ask | `decided` (answered question); re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-22 | No merge-queue support until a consumer project uses one; until then Delivery detects a queue and leaves that merge to the owner in GitHub (as built) | `autonomous`: the choice between "no support" and "add it once a consumer project needs it" was delegated in the read-back of 2026-10-11 ("i think no support … i am torn … i will take your recommendation between those two"). Reason: no project uses a queue today, and detection already prevents a wrong merge. The owner had taken a merge queue for stacked PRs; it is GitHub's queue that tests approved PRs together with the latest target before merging each in turn. Earlier: "i dont know what that is, so probably no" | 2026-10-10 |
| TD-23 | Charter and design approved on the basis of nine cornerstones (what it is, touchpoints, merge gate, PR comments, after the merge, failures, agents and safety, models, approval), with TD-24 to TD-29 as amendments | `decided` (answered question) | 2026-10-10 |
| TD-24 | Visual changes: before and after screenshots are captured and shown to the owner without interrupting the run, so the owner can intervene or simply see the difference | `decided`: "screenshots of the before/after are created and presented to the user. this does not interrupt the process"; re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-25 | When the target repository lacks "require branches to be up to date" or "require conversation resolution", Delivery shows a visible note, not a warning, and behaves as if they were on: it keeps the branch up to date and resolves conversations before merging | `decided`: "make it a visible note, but not a warning"; read-back 2026-10-11: "A visible note, and Delivery behaves as if they were on (keeps the branch up to date, resolves conversations)" | 2026-10-10 |
| TD-26 | Pull-back assumes the local copy is dirty (memories and other local files change constantly) and must update it reliably without conflicts, by rebase where needed, without losing local work | `decided`: "we have to assume local copy is never clean … we need a reliable mechanism to pull without conflicts and sometimes that could even mean a rebase"; re-confirmed in the read-back of 2026-10-11 | 2026-10-10 |
| TD-27 | Models and reasoning effort per role: reviews on `gpt-6.1-sol` at `xhigh`; challenges on `gpt-6.1-sol` at `high`; design and planning on `claude-opus-5.5` at `high`; building on `claude-opus-5.5` at `medium`, also the default for roles not yet chosen; model and effort are chosen per role where that has not happened yet. A benchmark on OwlBear's own work compares `gpt-6-luna` max with `claude-haiku-5.5` high, and `claude-haiku-5.5` xhigh with `gpt-6.1-sol` low, for quality and cost; it only informs, and the cheap tier is chosen with the owner afterwards | `decided`, read-back 2026-10-11, replacing the earlier record ("i have changed my opinion here … i see sol xhigh as reviewer, sol high as challenger. opus high as designer, opus medium as builder and default setting for now …"); readings chosen 2026-10-11: "Planner on Opus high, like the designer"; "Same benchmark, only to inform; we pick the cheap tier together afterwards". Earlier: luna and haiku at max, reviews Sol high, challenges Sol medium, planning Opus high | 2026-10-11 |
| TD-28 | Work happens in worktrees for the first release; containers are looked at before a later decision | `decided`: "its probably fine for a v1" | 2026-10-10 |
| TD-29 | Agents never push; Delivery performs every git and GitHub write | `decided`: "agree on agents never push...Github write" | 2026-10-10 |
| TD-30 | PR comments: every human comment is answered; the agent judges bot comments (acts on real findings, records "no action needed" for notices); no `@owlbear` mention gate | `decided`: "suggestion 2 is accepted" | 2026-10-11 |
| TD-31 | Code size and complexity: default rules of tools such as SonarQube or Snyk serve as guidance for deciding whether code is still acceptable or needs a split or rework, with wiggle room, not as a hard tool gate; SonarQube itself is not used (licence), Snyk perhaps later | `decided`: "take these default rules as an instruction to decide whether something is still acceptable or needs a split or rework, but with some wiggle room, other than a hard tool"; re-confirmed in the read-back of 2026-10-11 | 2026-10-11 |
| TD-32 | Delivery never uses the `auto` model; every session names its model. Turns whose output is thrown away (probes, tests) use `gpt-6-luna` at `low`, including the first turn a VS Code chat window starts and Delivery cancels, which must not run on the window's default model; small tasks that must be done correctly use `claude-haiku-5.5` at `medium` | `decided`: "we never use auto, ever"; read-back 2026-10-11 ("never use auto. if we need a test model … luna low … smaller tasks correctly … haiku medium"), readings chosen 2026-10-11: "… the 'cancelled first turn' of a VS Code chat must also run on Luna low, not on the window's default" | 2026-10-11 |
| TD-33 | Module size: agents aim for at most 400 lines per module; a test fails at 500 raw lines, without excluding comments or structure (replaces the logic-line counter of TD-19's implementation) | `decided` (answered question, the user's own proposal); re-confirmed in the read-back of 2026-10-11 | 2026-10-11 |
| TD-34 | Runtime per step (read-back of 2026-10-12).
- Each agent has a default runtime (initially the SDK) and its own model, effort and context size on the config page.
- A step runs in its agent's default runtime unless its needed tools (the agent's default categories plus its task's additions) are not available there. Then Delivery chooses a runtime that has them, for example a window for "browser use".
- Visible steps run as window chats (TD-35).
- The watcher must be able to read, steer and stop every runtime in use. | `decided`: chose "Each agent has a default runtime (initially the SDK) and its own model, effort and context size on the config page …" among four variants and the TD-41 closing options, after readings R2, R3 and R5. Earlier: "only the steps that need vs code tools run in vs code agent mode, the rest runs via sdk or cli …"; read-back 2026-10-11 | 2026-10-12 |
| TD-35 | Visibility (read-back of 2026-10-12, replacing the "managed or all in VS Code" switch). A step is visible if its agent needs it, its Change is set to always visible, or the global switch is on (R1). Visible steps run as chats in a VS Code window, so the owner sees them in a window, with the same tool list as unwatched: window tools are filtered if that works, which is untested (R5, P18). Changes take effect from the next session. VS Code is started when it is not running | `decided`: chose "As the first, but visible steps run as chats in a VS Code window, so you see them in a window. Window tools are filtered if that works (untested)" among four variants and the TD-41 closing options, after two "explain" rounds. Earlier record: "how about just managed or everything in vs code …", re-confirmed 2026-10-11 | 2026-10-12 |
| TD-36 | Missing tools (read-back of 2026-10-12). Known needs choose the runtime up front (TD-34). If a tool is still lacking, the agent ends the step with a "missing tool" report, and Delivery handles it by case:
- temporary error: Delivery retries now, then later;
- available in another runtime: one rerun there;
- needs the owner's setup: he is asked for that action;
- exists nowhere: back to planning.

A denial by Delivery's guard never leads to more tools (R6) | `decided`: chose "Known needs choose the runtime up front. If a tool still lacks, the agent ends the step with a 'missing tool' report …" among four variants and the TD-41 closing options. Earlier: "i am unsure. i think the task fails because the agent cant do what it needs to do and reports 'wrong harness/tools missing' … then for a retry the other harness (vs code) is used"; read-back 2026-10-11 | 2026-10-12 |
| TD-37 | Overnight 2026-10-11: probe, design, build, test and more; `maba-pag` was added as a collaborator to both sandbox repositories; VS Code stays open and the Mac awake | `decided` (answered questions) | 2026-10-11 |
| TD-38 | "Before" screenshots are part of shaping: once a Change is known to alter a page, shaping establishes the render recipe, captures the current pages from the target and writes the visual states against them; approval waits until that capture has finished. The comparison is per Change, not per task. At the visual check, if the target's UI paths changed since the shaping capture, "before" is retaken from the new starting point and the shaping set stays the design reference. Replaces the charter's "before the first build task"; TD-24 stays. Plan: [visual baseline](delivery-next-visual-baseline.md) | `decided`: "1: agree" to the assistant's proposal of 2026-10-11 containing exactly these points. The owner's earlier view, given as not yet decided: "i feel like it might be enough to compare deisgn phase versus overall result, not on a per task basis" | 2026-10-11 |
| TD-39 | The Changes page loads the Porsche Design System the way PDS documents it, from its CDN, and nothing else: no own fallback rendering, no own load diagnostic | `decided`: "A" ("i would prefer the way pds recommends … the fewer deviations from pds the better"); read-back 2026-10-11: "PDS's documented CDN loading, nothing else" | 2026-10-11 |
| TD-40 | Every preview run gets a free port chosen by Delivery; recipes take the port as a placeholder | `decided`: "3 is confiremd option 3 now"; re-confirmed in the read-back of 2026-10-11 | 2026-10-11 |
| TD-41 | Read-back of decisions (pattern P6): close variants of the recorded decision, as many as really differ in consequence (1 to 4, the matching one at varying positions), one or two other directions where real ones exist, and at the end "take your recommendation" (the result is the assistant's `autonomous` choice, with reasons), "none of these: show me more options" (a bounded set across directions, each with pros, cons, risks and a confidence), and "explain first"; free text always open; no recommendation mark. When the direction itself is in doubt, the direction is asked first, then the nuances, with the reason stated. Used at the end of ideation and before design approval, and for consequential choices of the assistant | `decided`: "P6 adaptive, with a direction check", chosen among five patterns with the assistant's and Sol's confidences; the owner's direction: "3 options in the same direction … + i let you decide + another direction + none of the above, find more options … + explain first" | 2026-10-11 |
| TD-42 | Confidence in a "more options" follow-up: a separate percentage per option that it is a good choice, not adding up across the options | `decided`: "A separate percentage per option that it is a good choice, not adding up" (chosen among four) | 2026-10-11 |
| TD-43 | A free-text answer is never recorded as written: the assistant offers the readings it sees, filling gaps differently (as many as really differ, 2 to 5), plus "your words as written", "show me more readings" and "explain first"; the owner chooses the one meant | `decided`: "for my free text, give me multiple options on how you understood them, or could understand them, including filling the parts i maybe forgot, and let me choose the one i emant, not the one i wrote"; format chosen among five: "As in round 3 …" | 2026-10-11 |
| TD-44 | Until the watcher agent exists, steps may run outside VS Code (SDK or CLI); the owner reads their logs afterwards | `decided`: "SDK steps may run meanwhile; only their logs can be read afterwards" (chosen among three, against the assistant's recommendation to run every step in VS Code) | 2026-10-11 |
| TD-45 | The SDK route keeps its hard guard against writes outside the worktree permanently; in VS Code the watcher governs such writes (D6) | `decided`: "Keep it permanently on the SDK route" (chosen among three) | 2026-10-11 |
| TD-46 | Intended writes outside the worktree: Delivery's own state, temporary files and the user's tool caches; anything else is stopped by the watcher unless the brief names it | `decided`: "Allowed: Delivery's own state, temporary files, the user's tool caches; anything else is stopped unless the brief names it" (chosen among three) | 2026-10-11 |
| TD-47 | The watcher agent's model and effort are chosen after the benchmark of TD-27 | `decided`: "Decide after the benchmark (N2)" | 2026-10-11 |
| TD-48 | Starting a window step (read-back of 2026-10-12; applies to every visible step and every step with window tools, TD-35).
- The window's first turn is shell-only (`code chat "!echo <nonce>"`, no model call), so the window owns the chat and serves its tools.
- Delivery signs in to the agent host again and waits until it lists the step's model.
- Every turn, including steering messages and reminders, names model and effort.
- A turn on any other model stops the step; a model that never appears ends it with a reason.
- The proof covers Opus, Sol and a full step.

Chosen, not built ([runtime research P14](delivery-next-agent-runtime.md)) | `autonomous`: the owner chose "take your recommendation" among four variants and the TD-41 closing options. The assistant picked "as recorded, made complete" because it is the only fully tested variant (sign-in plus wait, 3 of 3 runs). A restart cannot undo a turn already billed to another model, and the cancelled first turn starts on the window's model. Risk: a later drop of the model list stops the step. The original choice of 2026-10-11 came from a question that carried a recommendation mark, against TD-41 | 2026-10-12 |
| TD-50 | Watching and the SDK guard: until the watcher exists, steps that normally run in the SDK cannot be watched. Afterwards watching may change only how writes outside the worktree are controlled (the guard in the SDK, the watcher in a window); everything else stays the same | `decided`: chose "Until the watcher exists, steps that normally run in the SDK can't be watched; afterwards, as in the first option" among four options and the TD-41 closing options; owner's reading, 2026-10-13: "it says that i accept that steps inside the sdk cannot be controlled and prevented from doing shady things or misbehaving before watcher exists" (it does not stop steps from being made visible) | 2026-10-12 |
| TD-51 | Page errors (uncaught exceptions) count as console errors in the visual check: new ones fail, existing ones are reported | `decided`: chose "Page errors count as console errors: new ones fail, existing ones are reported" among three options and the closing options | 2026-10-12 |
| TD-52 | Config values are global, with overrides per project for single values | `decided`: chose "Global with overrides per project: one config for all projects; a project may override single values" among three options and the closing options | 2026-10-12 |
| TD-53 | Subagent models (TD-32 detail): subagents may use any named model; only Auto voids the step; other models are logged. The main agent is checked against its own model | `decided`: chose "Subagents may use any named model; only Auto voids the step; other models are logged (today's behaviour plus an Auto check)" among four options and the closing options; ratifies the subagent part of commit `4e0cbf674`, which had decided this ahead of the owner | 2026-10-12 |
| TD-54 | Unreadable usage on the SDK route: the step runs to its end, then usage is read again. If still unreadable, the result is not accepted, and the Change stops with an error message until the owner acts (retry or accept). If it happens more than once, Delivery builds around it, first by reading the runtime's session record | `decided`: free text "unreadable usage lets the step run until the end … but blocks further work if it isnt accessible at work end. and some error message", reading chosen: "Option 1" after the assistant's recommendation; choice between readings 1 and 3 | 2026-10-12 |
| TD-55 | Watcher stance (D5, D6 detail): the watcher intervenes only after an action (stop, then D6's retry); nothing is prevented beforehand. Safety checks judge actions, not reasoning. An outgoing transfer of local data that it notices is stopped like an unwanted outside write. The agent's reasoning may prompt a closer look at its next actions but is never a stop reason on its own; otherwise reasoning feeds only memory and improvement. Catching exfiltration is not a design goal for now. The watcher is multi-purpose, e.g. summarizing the current status for the Cockpit overview (to be discussed) | `decided`: free text "i accept the risk that watcher can only intervene post haste, not prevent outside writes or malicious actions … we focus on actions only for security/safety checks, not thoughts. those are only for memory/improvement", then chose "B and C" in the read-back, adding "thats not the inly task of watcher. it also does other things, like summarize the current status for the cockpit overview … watcher is generally multi purpose" | 2026-10-12 |
| TD-56 | TD-54 "accept": Delivery stores the unprocessed result with the commit, brief version and step it depends on. "Accept" is offered only while these still match; otherwise only "Run this step again" | `decided`: chose "Accept only while nothing it depends on changed" among four options and the closing options | 2026-10-12 |
| TD-57 | Settings location (TD-52, N8): the shared documents repository's location is set up now; the global settings live at its root and each project's settings in that project's folder | `decided`: chose "Set up the documents repository's location now: global settings at its root, each project's settings in its project folder" among three options and the closing options, after asking "dont we have a separate repo for project files like research? why cant it also hold global settings?" | 2026-10-12 |
| TD-58 | Delivery-next's agents, skills, prompts and instructions are not written from scratch: the existing ones are studied for their good parts, ideas and structure, and serve as the base to improve. Not a plain reuse. The old agents were not the old Delivery's problem | `decided`: free text "i do not agree with rewriting the agents. there was a lot of work put into them and we should at least use them to leran from them. the agent werent the problem with old delivery. i am not saying we should re-use them, but they have good parts and ideas, and the structure may also be something we can re-use or at least use as a base to improve. saqme for the skills, prompts, instructions." | 2026-10-12 |
| TD-59 | TD-57's repository: private `maba-pag/owlbear-common`, cloned at `~/Projects/owlbear-common` (created 2026-10-12, empty) | `decided`: free text "new private repo maba-pag/owlbear-common cloned to ~/Projects/owlbear-common" | 2026-10-12 |
| TD-60 | Systems for checks (TD-49 detail): three tiers, dev (the Change's worktree), test, live. Delivery's checks never touch live. Click and type steps run only on seeded test data (fixtures), never on live data or a live snapshot | `decided`: free text "we should adopt a three tier model of dev, test, live system/repo", then a live-snapshot proposal; after the assistant's assessment (outside services still reachable with live keys, personal data, stack-specific, missing states) chose "Fixtures only (seeded test data), no live data" among four options and the closing options | 2026-10-12 |
| TD-61 | Cockpit overview of a running step: stages per agent, possibly different per role: preparation (loading skills and memories, getting the work from Delivery), working (implementing, designing, reviewing, …), challenge #1, #2, … (each challenger run), fixing #1, #2, … (work after each challenge), finalizing (committing, writing memory back, returning the task to Delivery). How the stages are detected is open | `decided`: free text "for every agent there are stages. maybe different, maybe identical. something like \"preparation …, working …, challenge #1 …, fixing #1 …, finalizing …\"" after asking for more options | 2026-10-12 |
| TD-62 | Order of the remaining work: item 9's window proof first, while the owner is at the machine; then the TD-58 study and rework of the agents; then items 6 and 7, which depend on it | `autonomous`: owner chose "Take your recommendation". Reason: only item 9 needs the owner present; the study is read-only and items 6 and 7 build on its result | 2026-10-12 |
| TD-63 | T7 re-decided (changes TD-1's T7 and the charter's tool budget): no tool-count limits. Every Delivery tool serves one named process action (T1). A test checks every agent-facing tool: each field described (T4), small and flat (T5: about six fields, one nesting level). Whether the surface works is measured (T8), not counted. Item 7 gets its own `report_missing_tool` | `decided`: free text "i do not agree with t7, this is far too strict. tools follow process, they dont define process by limiting options. this limit only forces tools to have too many arguments and make tools unusable. this is imho very bad design."; shown T7's record (TD-1, charter values 6/3), asked for the recommendation, then chose "Yes, take it" | 2026-10-12 |
| TD-64 | TD-57 details: a project's folder in `owlbear-common` is named after its repository; a save on the settings page commits and pushes | `decided`: chose "Repository name" and "Commit and push", each among three options and the closing options | 2026-10-13 |
| TD-65 | TD-60's test data: the project settings name a seed command; Delivery runs it before the "before" and again before the "after" capture, so both start from the same data. Without one, only static states | `autonomous`: owner chose "Take your recommendation". Reason: Delivery controls when the data is reset, so before and after compare like with like; the project keeps its own stack and fixtures | 2026-10-13 |
| TD-66 | TD-61's stages are inferred by the watcher | `decided`: chose "The watcher infers it" among four options and the closing options | 2026-10-13 |
| TD-67 | The prototype's per-project `runtime=vscode` switch keeps working until routing is switched on; then it is removed, with a one-time notice naming the projects that used it, so the owner can turn visibility on | `autonomous`: owner chose "Take your recommendation" after the explanation. Reason: mapping it to the global switch would widen a project setting to all projects, and "always visible" per Change misses new Changes; it is the only window path until routing exists | 2026-10-13 |
| TD-68 | Night of 2026-10-13, owner away: the assistant may push all branches of all repositories, commit others' changes after checking they are worth keeping, rebase, manipulate and reload other VS Code windows (never the one running this chat), kill stray MCP servers, touch `share/` where necessary, and spend credits on live runs by judgement. No old Delivery runs anywhere | `decided`: free text "you may push all branches of all repos you like, yours or not, and you may even commit others changes if that helps you, but only after you checked them and decide they are worth keeping", "nothing is running except this chat … there is def no old system running anywhere … you may kill it if neccessary. you may touch share/ if you think its neccessary", chose "No cap, use judgement" and "Reloading other windows is fine, never this one" | 2026-10-13 |
| TD-69 | Each Delivery agent's file lists its tools, as the old OwlBear agents do; each runtime offers exactly those plus Delivery's result tools. This settles item 4's allowlists and P23 | `decided`: "ofc you need to define tools for eac agent… you are makig this unneccessarily hard" (2026-10-14) | 2026-10-14 |
| TD-70 | Delivery's agents keep using the project's owlbear-memory: recall at the start, save non-obvious lessons, curated as before | `decided`: "the agents will still use owlbear-memory" (2026-10-14) | 2026-10-14 |
| TD-71 | TD-56 scope: Delivery does not keep what challengers and subagents judge, because those are challenges, not reviews. Their sessions inside a step stay rerun-only | `decided`: free text "no we dont keep what challenger and subagent judge, as these are not reviews, those are challenges" (2026-10-14). Open: the visual review runs on the reviewer role (`roles.py`), so whether it counts as a review falls to the glossary | 2026-10-14 |
| TD-72 | Agent memory moves to the shared repository (TD-57): one memory folder per project, in the project's folder there. A folder for lessons that span projects may follow. The working repository holds no memory files | `decided`: "yes, move memory to the common repo" (2026-10-14), answering the assistant's proposal | 2026-10-14 |
| TD-73 | The brief review is a challenge, not a review, and is named "brief challenge" | `decided`: "for me it feels like a challenge" (2026-10-14); the assistant agreed: it runs on the challenger role while the brief is still being shaped, and its findings go back to the owner | 2026-10-14 |
| TD-74 | Delivery has three reviews: one after each task's build, one at the end of a Change, and the visual review of the screenshots. Other judgements are most probably challenges | `decided`: "agree theres a review for each task build and at the end of a change. the rest are most probably challenges only" (2026-10-14); amended the same day: "screenshot judgement is a review", the assistant agreeing, then "yes" to three reviews | 2026-10-14 |
| TD-75 | The screenshot judgement gets no "accept" for a result whose model cannot be verified; it is run again | `decided`: "i dont think we need an accept button there" (2026-10-14). How screenshots are judged is open ([design skill research](delivery-next-design-skill.md)) | 2026-10-14 |
| TD-76 | Impeccable is extracted into Delivery's own design skill, not installed. Its detector and the extracted rules are updated together and regularly, by a structured plan | `decided`: "extract", and "we need a structured plan to update. the runner and the extracted design rules need to be updated together, regularly" (2026-10-14). Plan: [design skill research](delivery-next-design-skill.md) §3.5 | 2026-10-14 |
| TD-77 | The detector's findings are evidence for the judges, never a fail on their own | `decided`: "evidence for the judges" (2026-10-14) | 2026-10-14 |
| TD-78 | Two judges, correctness and design, judge every visual review in parallel; no "another verdict" button. A correctness fail goes back to the build automatically. A design fail goes back or to the owner, by a setting with two values, which a project may override | `decided`: "agreed" to two judges and "yes" to automatic correctness fails; "can we make it configurable if design failures go back automatically? … then design failes either go back or go to the user for review" (2026-10-14). The default `ask` is the assistant's (`autonomous`) | 2026-10-14 |
| TD-79 | The owner decides on one page: screenshot comparison, both verdicts, then Pass or Fail, with each verdict's findings as checkboxes and an optional comment. Fail needs a finding or a comment, and its comment becomes a criterion of the next visual review; a Pass comment is kept as a note | `decided`: chose "you pass/fail recommendation" over five fixed options (2026-10-14) | 2026-10-14 |
| TD-49 | Screenshot method (read-back of charter §3.10, which was `approved` but never asked).
- Delivery captures each UI state itself with a headless browser, at the configured desktop widths (R7).
- A state may contain simple steps such as clicks or typing before the screenshot.
- The capture collects console errors; errors new since "before" fail the check (R8).
- The reviewer judges images and errors.
- A task can add the tool category "browser use" for the reviewer, to explore in a window beyond the states; console access there is untested.

Amends charter §3.10's "desktop and phone sizes" | `decided`: chose "As the first, plus: a task can add 'browser use' for the reviewer, to explore in a window beyond the states (console there untested)" among four variants and the TD-41 closing options, after the readings R7 and R8 | 2026-10-12 |

**User direction, not yet decisions** (2026-10-14):
- Memory may move into the shared repository (TD-57), so it neither dirties the working repository
  nor needs files in a consumer repository: one memory folder per project, and perhaps a common
  folder for lessons that span projects. Decided as TD-72. The 101 entries moved on 2026-10-14
  (owlbear-common `fec1f8e`, dev `543a12fc0`).
- The project needs a glossary that defines word pairs which feel similar but are not, starting
  with review and challenge. The owner's own description of that pair was deliberately
  exaggerated and is not to be used as wording. Draft:
  [glossary](delivery-next-glossary.md).

**User direction, not yet decisions** (2026-10-10, cornerstone walkthrough): whether three roles are
enough is open ("i dont want to actively decide that three roles are enough"); the brief and plan
reviews act as challengers, and cheap helper subagents on `claude-haiku-5.5` (code research, small
lookups) may help. Answering only comments that address Delivery (for example `@owlbear`) was raised
as a question. Code-size and complexity rules could build on SonarQube, Snyk or Aikido rules and
later be enforced by such a tool in CI.

**Under review (2026-10-11):** running the agent sessions through the Copilot SDK outside VS Code
(route R2+3 in the route comparison) was an `autonomous` recommendation that was never put to the
user; that the sessions keep working with VS Code closed is a side effect, not a decision. The user
asked to research what tools and configuration this route loses against VS Code (integrated browser
with viewports in particular) before it stands. The New Change button was confirmed by the user's
check: `code chat` always opened in the sandbox's own VS Code window, also with other windows active.

**User direction, not yet decisions** (forked chat, 2026-10-10): Cockpit as the communication channel
instead of Teams, Slack or Signal; "my goal would be for delivery to just run on itself"; start
sessions from Cockpit; more detail than "an agent is running" without rebuilding chat; a watcher
agent that narrates, derives learnings and, later, steers; cheap subagents (for example search on the
cheapest model) with model and reasoning effort per role; a durable home for research and learnings
outside `.git/`. The retry policy proposed in the fork — environment failures wait and never count,
only identical failures without progress count, then one different approach, then one question — is
adopted as design, `autonomous`.

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

### 3.11 Retrospective review, 2026-10-11

At the owner's request one Sol instance reviewed the assistant's plans and records since the rebuild
began, stage by stage in the order they were discussed (material in `.owlbear/scratch/retro-review/`,
not tracked). Limit: answers given in question dialogs are not stored in any readable log, so rows
whose origin is "answered question" can be checked only against their own quotes.

Patterns it found, with examples: proposals hardened into owner decisions (the merge prohibition
corrected on 2026-10-10; the dropped retake of TD-38); code treated as the specification (the brief's
missing render recipe written into the design as fact); claims beyond the evidence (the prototype
"ran from a chat-shaped brief" while the chat was a scripted client; port risks dismissed with a
wrong argument); consequential choices handed to the owner after building, without context.

Records corrected the same day: TD-38 restated with what the owner agreed; the M4 status above;
the charter's TD-24 sentence; the as-built "before" paragraphs of the architecture and status docs;
the [visual-baseline plan](delivery-next-visual-baseline.md) §7.

Code contradicting the decided or approved design, verified at `600636899` and queued for repair:

| # | Contradiction | Decided or approved rule |
| --- | --- | --- |
| C1 | The brief has no render recipe; the chat tool drops `ui` and visual states | Charter §3.10; TD-38 |
| C2 | Previews start without a free port or a check that the address is free | TD-40 |
| C3 | A resolved integration conflict that touches another Change's scope always asks, even when no behaviour contradicts | TD-12: "ask only on real behavioural collisions" |
| C4 | `no-action` is refused only for review threads, so a human's PR comment can stay unanswered | TD-30: every human comment is answered |
| C5 | An approved brief cannot be changed; the API knows only pause, resume and abandon | Journey D6 |
| C6 | The VS Code driver lets the window's first turn start on the window's default model, then cancels it | TD-32: "we never use auto, ever"; that turn must run on `gpt-6-luna` `low` |
| C7 | "All in VS Code" still runs steps with screenshot attachments through the SDK | TD-35 |

C6 and C7 need research first (whether VS Code can start a chat turn with a named model, and take
attachments), then the owner's call only if the platform cannot comply.

The owner's read-back of 2026-10-11 (32 decisions re-asked, paraphrased, with variant options) changed
or refined about half of them; the rows above carry the new wording. New or changed work from it:

| # | Work | From |
| --- | --- | --- |
| N1 | Watcher agent in the first release, now also the guard against unwanted writes outside the worktree (no sandbox, no hook) and the observer that lets steps run outside VS Code | TD-20, TD-34, D5, D6 |
| N2 | Role models: reviews Sol `xhigh`, challenges Sol `high`, design Opus `high`, building Opus `medium` and default; an own benchmark of Luna `max` vs Haiku `high` and Haiku `xhigh` vs Sol `low` | TD-27 |
| N3 | Throwaway and test turns on Luna `low`; small correct tasks on Haiku `medium` | TD-32 |
| N4 | Interactive mode for roles that ask the owner (ideation, design), autopilot for the rest; the question tool in the agent definition decides | D4 |
| N5 | A step whose session lacks needed tools ends with that report and is retried in VS Code, instead of choosing VS Code upfront | TD-36 |
| N6 | The merge waits for the owner when the visual reviewer is unsure about a state, as for a declared person-only check | TD-14 |
| N7 | Start with `maba-pag` doing every GitHub write as collaborator; later the repository owner's account writes where possible | TD-17 |
| N8 | Later: one shared documents repository for all projects, a folder per project | TD-7 |
| N9 | Remove the instruction rule against writes outside the worktree now; the watcher's stop (retried once with its reason, then the owner) replaces it | D6 |
| N10 | Autopilot agents raise decision or action requests that block their whole task; agents with the question tool run interactive | D4 |

### 3.12 Repair plan, 2026-10-11

Order: settled small repairs first; two live probes that decide how C6 and C7 are fixed; the watcher
designed with the owner, built and proven (it carries TD-20, TD-34, D5 and D6); the planned visual
work, whose live proof waits for a runtime the owner can follow; then the remaining runtime and
design-first items. Each code item is one commit on `next/m4-slice1` with the smallest test that
fails without it and a Sol review of the diff. Sol challenged this plan once; its findings are folded
in (watcher build and proof added, C6 probe replaced, N3 and the SDK guard added, TD-41/43 coverage
widened).

| Phase | Item | Approach | Proof |
| --- | --- | --- | --- |
| 1 Settled repairs | TD-27 roles, N3 | `roles.py`: builder `claude-opus-5.5` `medium` (also the default), reviewer `gpt-6.1-sol` `xhigh`, challenger `gpt-6.1-sol` `high`; planner stays Opus `high`. `RoleModel` drops the rule that Luna and Haiku run only at `max`, keeps the refusal of `auto` | A configured `gpt-6-luna` `low` and `claude-haiku-5.5` `medium` load; `auto` is refused; the next useful real review reports `gpt-6.1-sol` `xhigh` |
| 1 | C4 human replies (TD-30) | `no-action` refused for every human-authored item, not only review threads | A human issue comment answered `no-action` is rejected; a bot notice still passes |
| 1 | N9 outside writes (D6, TD-45) | Delete the rule from `agents/builder.md`; the SDK route's hard guard stays | Deletion inspected |
| 2 Probes | C6 first turn (TD-32) | Done (P14). The planned probe (no bootstrap turn) gave the right model but no window tools. The route chosen instead is TD-48 | P14 runs 3 to 5, Sol-verified host records |
| 2 | C7 screenshots in VS Code (TD-35) | Done (P14): an `embeddedResource` PNG over the agent host reaches the model | Colours named in all runs; position swapped in 2 of 7 at Luna `low` |
| 3 Watcher | N1 design | Ideation and design with the owner, Read-Back included: what it reads (SDK events, agent host chat), how it steers (steering message) and stops (turn cancel and the session's processes), which outside actions are allowed or stopped, D6's retry once then ask, its model and effort | Owner-approved design |
| 3 | N2 benchmark (TD-27, TD-47) | Luna `max` vs Haiku `high`, Haiku `xhigh` vs Sol `low` on OwlBear's own tasks, quality and cost; informs the cheap tier and the watcher's model, chosen with the owner | Results table; owner's choice |
| 3 | N1 build | Watcher for both runtimes, on the model chosen after N2; stops writes outside the worktree except Delivery's state, temporary files, tool caches and what the brief names (TD-46) | Live: it reads a running step, steers it once, stops an unwanted outside write, the step is retried once with its reason, a second stop asks the owner |
| 4 Visual baseline | C1, C2, N6 | [Visual-baseline plan](delivery-next-visual-baseline.md) slices 1 to 5; until the watcher exists, steps may run outside VS Code with their logs read afterwards (TD-44) | As in that plan |
| 5 Runtime | TD-34, TD-35, TD-36, TD-50 (read back 2026-10-12), N4/N10 (D4) | Superseded by the approved design §3.13 and its build order | Per item of §3.13 |
| 5 | TD-41 to TD-43 in Delivery | Read-back before brief approval in the delivery skill; free-text answers to Delivery questions offered as readings to choose from, with the question tool's option limit raised from five to eight | An unconfirmed free-text answer is not recorded as authority; the chosen reading is |
| 6 Design first | C3 collision test, C5 change of mind | Short design each, Sol-challenged, then build | Per design |
| Later | N7 account split, N8 documents repository, TD-10 review | When the first real project starts | — |

Phase 1 status, 2026-10-11, pushed to `next/m4-slice1` at `2eee8762f`, 601 tests pass:

- TD-27 and N3 in `d4d30fa39`.
- C4 in `eca659d2f`. GitHub's author type `Bot` marks a comment or review as a bot's. Only those may
  end as `no-action`; the builder prompt offers `no-action` only for them; review threads still need
  a fix or an answer.
- N9 in `f50347733` and `2eee8762f`. The rule is gone from `agents/builder.md`, the build prompt
  and the VS Code window instructions.
- Sol reviewed all four commits.
  - Accepted: the VS Code window copy of the rule (repaired in `2eee8762f`).
  - Rejected: re-validating stored pre-C4 `no-action` handlings. Delivery Next is unreleased, and
    no stored Change has one.
- Open for the N1 design: the build prompt's allowed-command section still says "`cd` only to
  directories inside the worktree". It describes the SDK guard (TD-45), but the VS Code route has no
  such guard.

Phase 2 status, 2026-10-11 ([runtime research P14](delivery-next-agent-runtime.md)):

- C7: a PNG sent as an `embeddedResource` attachment over the agent host reaches the model. It
  passed in 2 runs in a Delivery-created session and 3 in window chats. The fix is to send VS Code
  steps' screenshots that way instead of through the SDK. Left and right were swapped in 2 of 7
  runs at Luna `low`, so position claims need a stronger model or a labelled image.
- C6: probably caused by the agent host offering only Auto for a moment after each new window opens
  (strongly supported, not proven).
  - TD-48, read back 2026-10-12, sets the route: a shell-only first turn, sign in again and wait
    for the model list, then every turn names model and effort.
  - The 3 passing runs did sign-in plus wait; waiting alone is untested.
  - Chosen, not built. Build items: TD-48 in `vscode_step` with steering and reminders naming the
    model, C7 attachments, and a proof covering Opus, Sol and a full step.
- Open: TD-35's wording, now worked as a planned topic (steps 0 to 7, approved by the owner;
  builds of TD-48 and C7 held until it is through). Result on 2026-10-12:
  - TD-34, TD-35, TD-36 and TD-48 were read back;
  - TD-49 to TD-52 were decided;
  - the design §3.13 was approved as written.

  The owner allowed overnight work: the §3.13 build items that do not need the watcher, plus the
  config page, with routing kept off. Each item gets a failing test, a Sol review and a push.
  Afterwards, research for the next session (watcher, reusable implementations). Live runs, windows
  and models as needed. Decisions the assistant takes alone are Sol-challenged; owner decisions
  wait. Step 1 cleanup: 45 probe sessions and ten probe
  folders removed with consent; disposing a session also deletes its host record, so the six P14
  records were copied first to `.owlbear/scratch/ahp/c6/records/`.

Owner readings confirmed 2026-10-11 (TD-43; meanings, not decisions; the decisions follow in step 5):

- R1 Visibility levels only add. A chat is visible if its agent (or step) needs it, if its Change
  is set to always visible, or if the global switch is on. "Agent needs to be visible" is a
  requirement: it cannot work unseen, for example because it asks the owner. The Change and global
  settings are watching wishes, switchable at any time and effective from the next session.
- R2 Visibility is set per agent. Tool needs are set per agent as the default, with a per-task
  addition only where a task really needs more.
- R3 A config page, which does not exist yet (the old Cockpit has none), shows the global visibility
  switch and every OwlBear agent. Per agent it sets visible yes/no, default runtime, model, effort
  and context window size.
  - Its runtime picker shows the tools each runtime adds to the common baseline, and the agent's
    tools it would lack there.
  - A Change or task may add visibility and tool categories, never remove them. Model, effort and
    context size are plain defaults that a task does not change.
  - The agent file lists the most the agent could ever need. A step's needed set is the agent's
    default categories plus its task's additions. Delivery leaves the agent's default runtime only
    when the needed set is not available there.
  - The owner's earlier words, not offered back as a separate reading: runtimes "differ in tools
    and visibility and models and access to mcp and internet search and maybe even more, and that
    needs to be transparent"; unneeded runtimes such as CLI and cloud can be switched off in config.
- R4 Before steps move between runtimes, the owner wants to know whether a role behaves the same
  and delivers the same quality when its tools differ.
- R5 Watching is only seeing: a watched step behaves exactly as unwatched (tools, model, mode,
  permissions, result). A step's tools follow from its needs alone. Extra tools a runtime offers are
  hidden, and a runtime with too few is not used for that step.
  - Tools come in a few coarse categories (for example browser use). Each agent has a default set,
    and a task can only add whole categories, never remove basics or adjust single tools.
  - About 80% of tasks run with the defaults.
- R6 A missing tool reaches the owner only when he can act on it (install, enable, sign in).
  - Temporary errors: Delivery retries, now and later.
  - A tool available in another runtime: Delivery moves the step there.
  - A tool that exists nowhere: a planning error, fixed in planning.
- R7 (2026-10-12) Screenshots are desktop only, at widths between 1280 and 2400. The exact widths
  are a setting (default 1280, 1920, 2400), never below 1280.
- R8 (2026-10-12) The visual check collects browser console errors. Errors that were not in the
  "before" capture fail the check; existing ones are only reported.

Research questions from the readings (step 3), on top of the unknowns U1 to U5:

- Q-A Which settings can be passed when a session starts or a message is sent, instead of living in
  the agent file: model, effort, context size, tools, agent, mode, others? Should model, effort and
  context size leave the agent definition for OwlBear's config?
- Q-B How does an agent cope when its definition or linked skills mention tools a run does not
  have? One definition per agent or near-identical variants? Should skills be required reading or
  read when needed, and how big is the risk that a needed skill goes unread? The owner wants
  research plus the assistant's and Sol's opinions.

### 3.13 Runtime, tools and visibility: design draft, 2026-10-12

Draft, revised after Sol's challenge; for the owner's approval, not a decision. It builds on TD-34,
TD-35, TD-36, TD-48 and TD-49, readings R1 to R8, and runtime research P10 to P18. It keeps binding:
- TD-32: every turn on the named model, both runtimes;
- TD-44: SDK steps may run before the watcher exists, logs read afterwards;
- TD-45: the SDK guard;
- TD-46: allowed outside writes;
- D4, N4 and N10: modes;
- D6: retry once with the reason, then the owner;
- N3: Luna `low` for throwaway turns, Haiku `medium` for small tasks;
- N6: the merge waits when the visual reviewer is unsure.

**Runtimes.** A catalogue on the config page; each entry can be switched off.

| Runtime | What it is | Tools beyond the shared baseline | MCP servers | Live view for the owner | Outside-write control |
| --- | --- | --- | --- | --- | --- |
| `sdk` | Copilot runtime process Delivery starts | none | only those Delivery passes (K2) | no (VS Code shows a snapshot at most, K4) | Delivery's hard guard (TD-45) |
| `window` | Chat in a VS Code window, started per TD-48 | window tools: browser, tasks, problems | owner's VS Code `mcp.json` | yes | the watcher (D6) |

- The shared baseline is the runtime's own tools (files, edit, shell) and Delivery's result tools.
- Left out:
  - an agent-host session without a window: TD-35 puts visible steps in windows, and nothing else needs it;
  - the CLI: the same engine as the SDK;
  - cloud: not examined.
- Unknown and to be measured at build: whether both runtimes offer the same models and web search.

**Tool categories (R5).** Baseline always. Extra categories are coarse; today only `browser`
(TD-49's exploring reviewer), provided by `window`.
- The agent file lists the most the agent may ever use (R3).
- A step's allowlist is the baseline plus the agent's default categories and its task's additions.
- Delivery passes that allowlist per step:
  - SDK: `available_tools`;
  - window: the `tools:` line of the agent file Delivery writes per step, which works for runtime
    tools (K5).
- Open: whether `tools:` also filters a window's own tools and MCP tools. TD-35 accepts window tools
  "if that works"; the build tests it before routing is switched on.
- Open: which names each runtime's allowlist uses. The SDK allowlist covers built-in, MCP and
  Delivery's tools; K5 showed four runtime tools that are always present. The build maps categories
  to concrete names per runtime.
- **Settled by TD-50:** R5 says a watched step behaves exactly as unwatched, "permissions" included,
  but a visible step runs in `window`, which has no SDK guard (TD-45). Until the watcher exists, steps
  that normally run in the SDK cannot be watched. Afterwards watching may change only how writes
  outside the worktree are controlled.

**Agent definitions (Q-A, Q-B), the assistant's opinion.**
- Q-A: model, effort and context size leave the agent files and live in OwlBear's config, per agent
  (R3). They are passed per session (SDK) or per message (window), which both runtimes support (P15).
  - The window takes a numeric `contextSize` per model; the SDK only has a default or long-context
    tier. The config stores the size; Delivery checks per model what each runtime can do and
    records the effective setting.
  - TD-32 in the SDK: today's check flags another model only when the named model is entirely
    absent from the usage (`sdk_adapter._usage`). A mixed turn passes, and the flag invalidates
    nothing. The build must stop any step whose usage names another model, for every turn: start,
    resume, reminder.
  - The tool list stays in the agent file as the maximum (R3). Delivery narrows it per step.
  - Confidence: high. Sol agrees: high.
- Q-B: one source file per agent.
  - Its core text never tells the agent to use a tool it might lack.
  - Mandatory material for an extra category, and for the workflow, loads at session start. Only
    situational references stay on demand.
  - Category material lives in a skill that Delivery preloads when the step has that category. The
    SDK's per-agent `skills` and the agent file's `skills:` line, which the agent host forwards
    (P18), both take skill names. That is from the source; untested.
  - Open for the build:
    - how preloaded skill names resolve, and what happens when one is missing;
    - skills the runtime discovers on its own;
    - relative references inside skills.
  - So there are no near-identical files to maintain and no extra context in the ~80% of steps
    without the category. The "read when needed" risk is reduced for the preloaded material, not
    removed in general.
  - Evidence so far: one run (K5), in which an agent asked for an absent tool said so and stopped.
  - R4 needs its own comparison: the same role, model, effort, context and effective tools in `sdk`
    and in `window`, before any role moves runtime. N2's model benchmark stays as decided, and
    TD-47's watcher choice follows N2.
  - Confidence: one source file high; equal behaviour across runtimes medium.

**Visibility (TD-35, R1).** A step is visible if its agent "needs visibility" (config), its Change is
"always visible" (a toggle on the Changes page), or the global switch is on (config page). Visible
steps run in `window`. Changes apply from the next session.

**Modes (D4, N4, N10), unchanged by watching.**
- An agent whose definition has the question tool (`askQuestions`) runs interactive, and needs
  visibility, since the owner answers in the chat. Its question tool is always in its allowlist.
- Every other agent runs autopilot. When only the owner can settle something, it uses Delivery's
  decision or action request, which blocks its whole task (N10). That tool is always in its
  allowlist.
- Watching never changes an agent's mode.

**Routing (TD-34).** A step runs in its agent's default runtime, unless:
- it is visible: then `window`;
- its allowlist needs a category the default runtime lacks: then the first enabled runtime that has
  it.

If no enabled runtime fits, Delivery tells the cases apart:
- a runtime that has the category is switched off: owner setup (enable it);
- the category needs setup, for example a missing browser install: owner setup (that action);
- the category exists nowhere: back to planning (TD-36).

**Missing tools (TD-36).**
- The prompt's "if something you need is missing, call `ask_question`" is replaced by a "missing
  tool" result: the tool or category, and what failed.
- Delivery decides the case:
  - temporary error: retry now, then later; how often and how long is a proposal for the build;
  - in another enabled runtime: one rerun there;
  - owner setup: a decision request naming the action;
  - nowhere: back to planning, which changes the task.
- Guard denials stay denials.

**Screenshots (TD-49).**
- Widths come from config: default 1280, 1920, 2400, each between 1280 and 2400 (R7).
- Recipe states may contain clicks and typing before the shot.
- Playwright collects console errors for "before" and "after". Errors new since "before" fail the
  check; existing ones are reported (R8).
  - Uncaught page errors count as console errors (TD-51).
- The reviewer gets images and errors. A task may add `browser` for the reviewer.
- When the reviewer is unsure about a state, the merge waits for the owner (N6).
- Screenshots reach a reviewer in `window` as attachments (C7), before visible visual reviews are
  switched on.

**Window start (TD-48)** as recorded.

**Config page (R3).** A new page in Delivery's web UI, beside `changes.html`:
- the global visibility switch;
- runtimes on or off, with their catalogue rows;
- per agent: needs visibility, default runtime, model, effort, context size, default categories;
- a runtime picker showing the tools it adds over the baseline, and the agent's listed tools it
  lacks.

Today the profile holds per-project role models (`Profile.roles`) and one global `runtime` switch.
Both move into this structure, and the migration keeps every effective role setting.

**Task categories.**
- The planner writes a task's added categories into the task (a new field) and Delivery validates
  them.
- Review and fix tasks inherit them.
- The whole-Change visual review takes the categories of TD-49 (`browser` only when a task asks for
  it).

**Settled since the draft:** TD-50 (watching and the guard), TD-51 (page errors), TD-52 (config is
global with per-project overrides).

**Build order (proposal, after Sol).**
1. Facts that gate routing:
   - the window-tool and MCP filter test;
   - tool-name mapping per runtime;
   - model, effort and context support per runtime;
   - the R4 comparison for a role before it may move.
2. Config structure, migration, then the page.
3. TD-48 window start, and TD-32 checks on every turn in both runtimes.
4. Routing, allowlists, task categories, modes and preloaded skills.
5. The missing-tool result.
6. TD-49 capture changes and C7 attachments.

§3.12 keeps the watcher (N1) in phase 3, before visual work and runtime routing. Meanwhile TD-44
applies (SDK steps, logs read afterwards), and window steps are unguarded until the watcher exists
(D6). Real cost per runtime is measured with the R4 comparison.

**Overnight build plan, 2026-10-12, revised after Sol's challenge** (owner scope: the build items
that do not need the watcher, plus the config page; routing stays off). Every item: a failing test,
the change, ruff, the full delivery-next suite, a Sol review of the diff, then a commit and push to
`next/m4-slice1` (PR #449). Choices the assistant makes alone are Sol-challenged. Live proofs use
throwaway folders and are cleaned up.

1. **Gating facts, no activation.** Concrete tool names per runtime; whether `tools:` hides window and
   MCP tools; model, effort and context support per runtime; attachment size limits.
2. **TD-32 in the SDK.**
   - Each agent checked against its own configured model: start, resume and reminder turns, plus
     `auto` resolution.
   - A mismatch, even one seen after the result was submitted, clears the accepted result and ends
     the step with the reason.
3. **TD-48 window start.**
   - Bootstrap `!echo` bound by nonce, folder and uniqueness; its finished shell turn is accepted.
   - The bootstrap's own shell confirmation is handled without changing global approvals.
   - Reconnect to the same host, restore subscriptions, close both connections.
   - Steering and reminders carry model, effort and agent.
   - Proof: Luna `low`, short Opus and Sol turns, then one full builder step with a window tool, a
     result and confirmed cleanup.
4. **Config schema** with per-field global and project resolution, and an idempotent migration,
   tested in throwaway storage. The file location and the visibility activation stay unresolved.
5. **Config page:** global and project GET and PUT behind the existing token and local-host checks;
   controls for settings not yet applied are shown as inactive; one browser save and read-back proof.
6. **Modes and skills:**
   - D4, N4 and N10 modes: question tool → interactive; otherwise autopilot with Delivery's blocking
     request.
   - Mandatory skills preloaded, with one minimal check of a missing skill.
7. **Missing-tool result** with the full TD-36 classification, all cases tested. Rerunning in another
   runtime is not switched on.
8. **TD-49 capture.**
   - Desktop widths with height 800 kept.
   - Click and type steps through draft schema, stored state, `briefs.drafted` and versioning.
   - Console and page errors kept per state and width, with listeners attached before navigation.
   - New errors fail, existing ones are reported. A missing "before" is never a clean baseline.
   - Reviewer uncertainty blocks per N6. The 390 px assertions are updated.
   - Proof: one page with an existing and a new error.
9. **C7 attachments**, bounded by the measured limits. Proof: one real Sol screenshot review in a
   window. Normal runs stay where they are (TD-50, R4).

**Night progress, 2026-10-13** (branch `next/m4-slice1`, each item test-first, full suite, Sol review):
- item 9 `0b4300c83`; the per-step relay name `ec7b719ea` (runtime research P21);
- shared settings in `owlbear-common` (TD-57, TD-64) `7b67cae93`; agents rebuilt on the old ones
  (TD-58) `22f2205a4`;
- item 7 `824717d37`: `report_missing_tool` with the TD-36 cases; a conversation task never
  re-plans; planning starts on a clean tree (leftover edits stashed, a failed stash asks); the TD-63
  per-tool shape test replaces the tool count;
- item 6 `199695546`: two cleaned skills preloaded for every role in both runtimes (P22).
- TD-56 `c8ea1ac47`: an agent step's own result with unread usage is held, bound to its gate
  question, and offered for "accept" only while step, brief version and commit still match.
  Reviewer sessions inside a step (plan challenge, brief review, visual review) stay rerun-only:
  their verdicts depend on inputs Delivery does not hold. That narrows TD-56; it goes to the owner.
  Settled by TD-71.
- item 8c `190968bca`: click and type steps (exact names, editable fields only, no reach outside
  the preview but static files); a separate chat tool `save_visual_check` keeps both chat tools
  within T5; a new or changed state takes the brief version; the seed command (TD-65) is a project
  setting; without it the after capture asks and the before renders only static states.
- Live: a Luna `low` builder told to use an uninstalled tool called `report_missing_tool` with the
  exact error, and Delivery asked the owner to set it up (P24).
- Found: window steps offer the runtime's `ask_user` and the owner's MCP tools, which a read-only
  Luna reviewer used to write files (P23). The window `tools:` allowlist (P19 F2) fixes it; item 4.
- Autonomous choices made overnight, each Sol-reviewed: planning first stashes edits an earlier
  step left (the read-only planner rejects a dirty tree); a stepped state's network reach is
  limited to the preview plus static files; the chat brief tool keeps the visual check it does not
  send.
- TD-69 and TD-70 `a068a6cf7` (2026-10-14):
  - Each agent file names its tools in the runtime's own names. Only the builder can create or
    edit, and the reviewer only recalls memory.
  - The window accepts the same names, so one list serves both runtimes. It gets a per-step memory
    server with the workspace as its working directory.
  - The SDK approves an MCP request only for the role's own MCP tools.
  - Live (P25): both runtimes offered exactly those tools, with no `ask_user` and none of the
    owner's MCP tools. Recall and save worked in both.
  - Rejected Sol finding: saved memories land untracked in the main checkout, as with the old
    agents (TD-70).

**Deferred to the owner:** where the global config file lives (once decided, the runners must read
the same global layer the settings page edits; today the host passes none, so global saves are
refused); any rule allowing subagent models
beyond each agent's own; how the old `runtime=vscode` setting migrates, given TD-50; plus watcher
design and model, benchmark choices, switching routing on, and watching SDK steps.

Then research for the next session: watcher design options and reusable implementations, grounded in
existing code and Sol-challenged.

## 4. Recommendation, Confidence, and Limits

**Recommendation:** treat this as a re-founding with the weight on design. Let the open Changes
finish on the old engine while it stops growing (M0). Keep the groundwork light: ownership map,
route comparison and the R8 platform probe (M1). Make the charter a set of explicit user decisions
(M2). Put most of the effort into a watertight end-to-end journey and failure
catalogue for a consumer project, challenged independently (M3). Build in vertical slices on a
sandbox consumer repository, proven by demonstration with tests only per P8 (M4). Then use it on a
real consumer project and expect fixes, not rework (M5), and delete the old engine (M6). Integrate
the platform migration rather than sequencing it (S3).

**Status, 2026-10-10 morning.**

| Milestone | State | Where |
| --- | --- | --- |
| M1 | Done: ownership map, route comparison, live platform probe | L14 |
| M2 | Charter drafted and challenged; awaits approval | [charter](delivery-next-charter.md) |
| M3 | Journey and catalogue, status and exits, architecture, cutover: drafted, challenged three times, corrected; awaits approval | L14, M3 row |
| M4 | Prototype on branch `next/m4-slice1`, PR #449, not merged: the whole journey ran in the sandbox from a brief to a merged PR, with the chat simulated by a scripted MCP client (no real chat session was exercised; the chat tool cannot save UI fields, G2 of the [visual-baseline plan](delivery-next-visual-baseline.md)), with brief approval and merge consent as the only touchpoints; twelve common failures were triggered by hand and each ended in its designed exit and continued; every failure found was fixed locally (P9). Reshape phases A–E done on PR #449 (draft), with Sol challenges per phase and a final re-check; CI skips draft PRs (repository rule), so local proof: the full Python suite passed at `372f3c2a7` (5,601 passed). Live run of the reshaped first-release flow on the protected sandbox (PR #8): owner review thread fixed, replied to and resolved by Delivery, automatic merge without consent, pull-back of the checked-out `main`; four defects it found were fixed with tests. Remaining: `maba-pag` probe (TD-17); visual check, overlap display and the New Change button not yet run live | `serve/delivery-next/DEMO-slice1.md` on the branch |

Proven since: merge under a ruleset (required check, squash only, linear history) in the public
sandbox `boecht/owlbear-sandbox-protected` — never merged while CI was pending or red, merged the
consented head with the `sha` guard. On the branch, the sync manifest has a `delivery-next` scope
behind the `sync_delivery_next` input, default off: the package reaches consumer `main` only when
that input is set at dispatch (cutover §3.2 step 5).

Still unproven, needed before M5: the `maba-pag` probe on its business seat (TD-17) — models,
reasoning effort per session and agent, context window, subagent models and cost; the folder-open
start, skill loading and workspace trust inside VS Code; the Changes page used in a browser by the
owner.

**Confidence:** high that ordinary failures nobody designed for, together with an inward-facing
design (RC6), explain the observed pattern; every 2026-10-09 incident was ordinary. Medium on the
relative weight of RC1–RC5, because self-use data is thin and is deliberately not refined further.
Medium on how much code is reusable.

**Limits:** metrics are local proxies from self-use only. Likelihood labels in the failure catalogue
are judgments to be corrected by real use. This document does not change any Delivery authority,
lane, or live state.
