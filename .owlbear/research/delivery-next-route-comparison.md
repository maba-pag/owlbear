# Delivery Next: Route Comparison

> **Owning task:** none — M1 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** Which route reaches the target journey and failure catalogue with the least risk:
> targeted repair of the current engine, a thin layer over the Copilot platform and GitHub, or a new
> minimal core beside the old engine — and which current code is worth reusing?
> **Status:** Analysis for M1 at `8d07aa9dd`. Uses the user's decisions TD-1 to TD-8 of the
> [rebuild research](delivery-liveness-first-rebuild.md#38-decisions-reserved-for-the-user); every
> conclusion here is `autonomous` until the user approves the charter.

## 1. Context and Question

The rebuild research (§3.7, M1) asks for a design-level route comparison before the charter. The
target is fixed by the [journey research](delivery-next-journey-and-failure-modes.md): stages J0–J9,
the touchpoint budget, five exits plus pending, the failure catalogue and DR1–DR15. The user's own
direction frames the choice: Delivery "is obviously completely overbuilt … should instead have been
a more resilient implementation that can correct inline instead of fail and require another tool to
fix" (2026-09-11), and "this will be a huge change or maybe even re-implementation from scratch with
some re-use where beneficial" (2026-10-09). The open Changes keep running on the old engine (TD-2).

## 2. Sources Studied

| ID | Source | Relevant fact | Limits |
| --- | --- | --- | --- |
| L01 | [Rebuild research](delivery-liveness-first-rebuild.md) §3.2–3.9 | RC1–RC6, P1–P9, roadmap, Q1 lean, TD-1–TD-8, platform findings F1–F5 | Agent analysis; only TD-1–TD-8 are user decisions |
| L02 | [Journey research](delivery-next-journey-and-failure-modes.md) | Journey, touchpoint budget, exit contract, catalogue with C/O/R labels, DR1–DR15 | Likelihood labels are judgments |
| L03 | [Tool-surface audit](delivery-tool-surface-audit.md) | 64 tools, 536 fields, author/caller split, rules T1–T8 | Counts at `753eb92` |
| L04 | `wc -l` over [owlbear_delivery](../../serve/delivery/src/owlbear_delivery/) | 60,824 lines in 55 modules; largest: `delivery_application_loader.py` 3,106, `delivery_runtime.py` 3,064, `application_readiness.py` 2,771 | Includes docstrings |
| L05 | [remote_git.py](../../serve/delivery/src/owlbear_delivery/remote_git.py) L14, [storage_io.py](../../serve/delivery/src/owlbear_delivery/storage_io.py) L9–L16, [git_executable.py](../../serve/delivery/src/owlbear_delivery/git_executable.py) | Only Delivery import is `git_executable`; bounded noninteractive transport, `RemoteGitWriteUnknown`, `classify_write_readback`; `atomic_write`, `locked_roots`, `ControllerLock` use stdlib only | Behavior read, not re-tested |
| L06 | [publication_provider.py](../../serve/delivery/src/owlbear_delivery/publication_provider.py) L1–L11; [github.py](../../serve/delivery-github/src/owlbear_delivery_github/github.py) L17–L47; [memory.py](../../serve/delivery-github/src/owlbear_delivery_github/memory.py) L10–L34 | Provider contract imports stdlib and pydantic only; the `gh` provider imports only that contract and its own `effect_launcher`. `github.py` L17 imports from the package root, whose [`__init__.py`](../../serve/delivery/src/owlbear_delivery/__init__.py) L111, L265, L353 loads `delivery_runtime`, `portfolio_application`, `recovery` | No `--hostname`/`GH_HOST` handling found; merge queue detected (`_QUEUE_RULE_TYPE` L132) and refused, not followed |
| L07 | [merge_offer.py](../../serve/delivery/src/owlbear_delivery/merge_offer.py) L12, L93–L99; [merge_approval.py](../../serve/delivery/src/owlbear_delivery/merge_approval.py) L13–L18, L76–L77 | Import only the provider contract and `storage_io`; models still carry `finalization_id`, `ready_receipt_id`, `review_id` from the old proof model | Static read |
| L08 | [worker_stall.py](../../serve/delivery/src/owlbear_delivery/worker_stall.py) L42–L455 | No Delivery imports; `ProcessTableWorktreeProbe.active_processes` (L421) finds processes working in a worktree; `DeliveryClaimIssuer` and window-host identity are Local-claim specific | psutil-based, macOS/Linux |
| L09 | [acceptance_criteria.py](../../serve/delivery/src/owlbear_delivery/acceptance_criteria.py); [evidence.py](../../serve/delivery/src/owlbear_delivery/evidence.py) L16–L32 | Criterion parsing and content versions use pydantic only; evidence evaluation imports `runtime_models` receipts, frontier and legacy schema plus `target_contract` | — |
| L10 | [work_items.py](../../serve/delivery/src/owlbear_delivery/work_items.py) L11–L41, L330–L344, L767 | `derive_delivery_progress` takes `DeliveryReadiness`, `WorkItemCardView`, `DeliveryFrontier` and custody evidence; module imports runtime, evidence, finalization, merge, recovery and receipt modules | Vocabulary (`DeliverySituation`, `DeliveryWaitingOn`) is separable |
| L11 | [workspace_preservation.py](../../serve/delivery/src/owlbear_delivery/workspace_preservation.py) L15–L31, L319–L330; [workspace_target_sync.py](../../serve/delivery/src/owlbear_delivery/workspace_target_sync.py) L12–L14 | Preservation is a mixin over `recovery`, `runtime_transaction`, `workspace_models` and rejects pre-existing staged content; target sync is the engine-owned merge that runs product hooks | — |
| L12 | Cockpit backend [target_work.py](../../serve/cockpit/src/owlbear_cockpit/routes/target_work.py) L58–L90, [ideas.py](../../serve/cockpit/src/owlbear_cockpit/routes/ideas.py) L14; web [WorkPortfolioTable.tsx](../../serve/cockpit/web/src/components/WorkPortfolioTable.tsx) L4, [MergeApprovalDialog.tsx](../../serve/cockpit/web/src/components/MergeApprovalDialog.tsx) L3, [CopyCommand.tsx](../../serve/cockpit/web/src/components/CopyCommand.tsx), [usePollingFetch.ts](../../serve/cockpit/web/src/hooks/usePollingFetch.ts) | Delivery routes import portfolio, work-item, runtime and diagnostics modules; Ideas and Memory need only `atomic_write`. Web: 13,373 non-test lines; ~8,450 in Delivery views typed against `ChangeGroupView`, `WorkItemCardView`, `MergeOffer` | Line counts by file |
| L13 | `.owlbear/controller/` (`pin.json`, `releases/`); [execution plan](delivery-redesign-execution-plan.md) L134, N10-M | The open Changes run on a pinned controller release; live code changes arrive only through `/upgrade-delivery`, with state-format migrations (format 2 → 3 at N10-M) | Not inspected beyond listing |
| W01 | [Copilot SDK](https://github.com/github/copilot-sdk) | GA with semantic versioning; Python package bundles the Copilot CLI; JSON-RPC to the CLI server; custom agents, skills, tools, hooks; per-call permission handler; billed per prompt like the CLI | README level |
| W02 | [Choose and use an agent harness](https://code.visualstudio.com/docs/agents/run/agent-harnesses) | Copilot harness built on the SDK; worktree isolation only in the Agents window; worktree sessions run "Allow all"; ignored files and installed dependencies absent; desktop app must keep running for local sessions; sessions and settings do not synchronize across products; hooks in preview | Product docs, 2026-10-07 |
| W03 | [Dynamic workflows](https://docs.github.com/copilot/concepts/agents/dynamic-workflows) | Public preview; Copilot app, CLI, SDK; code-defined steps, structured results with format correction, pause and resume from saved results; `copilot workflow run` shows no permission prompts; credit limit approximate | VS Code not listed |
| W04 | [VS Code September 2026 releases](https://github.blog/changelog/2026-10-01-github-copilot-in-vs-code-september-2026-releases) | Agents window: PR creation form, agent merge (preview), automations (preview), session cleanup (preview), attention badge (preview) | UI features; no programmatic API stated |

## 3. Analysis

### 3.1 The routes, and where routes 2 and 3 meet

| Route | What it is |
| --- | --- |
| R1 Targeted repair | Keep the engine and its authority model; fix the failure classes in place, add the exit contract, shrink tools to T1–T8 |
| R2 Thin layer | Delivery keeps brief, project profile, status and a loop driver; sessions, worktrees, PR creation, review, CI repair and merge go to the Copilot platform and GitHub |
| R3 New minimal core | A new package beside the old engine, built on the Copilot runtime; cutover and deletion at M6; reuse of single functions |

**Convergence.** R2 cannot stay thin at the points the journey needs most. The platform features it
would delegate to (W04) are Agents-window UI: the PR form, enabling agent merge and choosing a
worktree are user actions per session, outside the touchpoint budget. One Change spans many sessions
(plan, tasks, reviews), so no platform surface gives one status line per Change (P6). Person-only
checks (J7, H1–H3), merge consent bound to a head (DR15), retry budgets carried across `back` (DR13)
and the lock (DR10) have no platform owner. A loop driver that fills these gaps through the SDK and
`gh` is a minimal core. Conversely, R3 is only minimal if it delegates everything the platform and
GitHub already own. The two routes therefore merge into one:

**R2+3 — thin core on the Copilot runtime.** A new package and state root beside the old engine. It
owns only what the M1 ownership map leaves to Delivery: brief and plan state, project profile, the
loop with its exits and budgets, questions, person-only check validity, merge consent, the per-Change
lock and the status line. Agents run through the Copilot SDK (sessions, custom agents, skills,
permission handler). Code facts stay in git and GitHub, read and written through the reused `gh`
provider. Platform UI features (agent merge, PR form, automations) are optional accelerators, adopted
only after R8 shows they are observable from code and not in preview; nothing on the critical path
depends on them.

### 3.2 Journey, touchpoints, common failures and the exit contract

| C rows or concern | R1 Targeted repair | R2 Thin layer | R2+3 Thin core |
| --- | --- | --- | --- |
| Touchpoint budget | Local cannot resume work after an answer; the user re-runs `/continue-change` (journey §3.7); fixing that needs another runtime | User operates the Agents window per session (PR form, agent merge, worktree choice) | Answers resume the loop if R8 confirms question round trips; otherwise one generic "continue" (journey §3.2 fallback) |
| S1–S3 setup and profile | Add profile and readiness to an engine that assumes `uv`, pytest and `github.com` | Platform checks Copilot sign-in only; profile still needed | Profile (DR1) and readiness (DR2) are core features; a small server shrinks S2 |
| D1–D4 shape and plan | Existing Designer/Planner flow, 11 tools | Prompts only; no plan state, so D4 `back` has no owner | Plan state and `back` in code |
| B1–B6 build | B2/B3 need integration moved from the engine merge (L11) into tasks; B5 needs new author-called tools (T3) | Work runs in platform sessions; dependencies absent in platform worktrees (W02); B4/B6 invisible to a thin layer | Task step runs an SDK session after the profile install; diff and check verification in code; T3 tools |
| B7 unattended permission | Local has no unattended mode | Worktree sessions run "Allow all" (W02), no scoped policy | SDK permission handler decides per call (W01); R8 confirms |
| I1, P1, P2 integrate and CI | Engine-owned merge runs product hooks (L11) | Agent merge handles conflicts, failed checks, reruns — preview (W04) | Core observes via the provider; fixes run as tasks; agent merge optional after R8 |
| H1, M1 human checks and merge | Exist, but evidence is re-asked per commit (RC3) | No owner for person-only checks | Check inputs recorded (P5); merge observed via provider |
| X1–X3 sessions and time | Loop lives in chat prose; closes with the window | Agent Host sessions survive window close (W02), but a Change spans sessions | State outside chat; re-entry by observation (DR5); runtime survival per R8 |
| Exit contract | Retrofit over 67 error codes and 26 recovery tools; containment model stays | Platform outcomes are not exits; the layer must infer them | The five exits and pending are the core's only step outcomes |

### 3.3 Fixability (P9), size and budgets (P7)

| Contract or measure | R1 | R2 | R2+3 |
| --- | --- | --- | --- |
| Approved interaction | Spread over 2,127 lines of skill prose and prompts | Partly the platform's UI, which changes monthly | Charter plus code |
| Ownership | Custody, claims and receipts across 55 modules | Shared with the platform; vendor changes can move it | Ownership map; code owns the loop, git/GitHub own facts |
| Preservation and replay | Fence-heavy; rejects staged content (L11), unlike DR6 | Platform session cleanup (preview) | DR5/DR6 in one place; reused write-unknown readback (L05) |
| Evidence validity | Exact-commit receipts | None | Recorded inputs (P5) |
| Size today or at start | 60.8k source, 60.5k test lines, 64 tools | Smallest code | Budgets set in R4 before code; ~4.5k reused lines as seed (§3.4) |
| Reaching T7's example of ≤15 tools | Delete ≥49 tools from a live engine | Trivially met; uncovered rows become user work | Met by construction: identities live in code (T2) |

R1 cannot meet P9 without changing all four contracts, which by P9's own rule sends every area back
to M3 — R1 becomes a rewrite in place. R2 meets budgets by moving rows out of anyone's ownership.

### 3.4 Reuse without the old authority model

Worth reusing — copied into the new package so the old engine stays byte-identical for TD-2 and M6
deletion needs no untangling:

| Module or function | Lines | Coupling (L-ref) | Use in the new core |
| --- | --- | --- | --- |
| `remote_git.py`: `run_remote_git`, `read_remote_ref`, `RemoteGitWriteUnknown`, `classify_write_readback` | 290 | Only `git_executable` (L05) | Push and ref reads with timeouts; replay only on confirmed absence (DR5, X4) |
| `git_executable.py` | 18 | stdlib | As is |
| `storage_io.py`: `atomic_write`, `locked_roots`, `ControllerLock` | 188 | stdlib (L05) | Atomic state (DR11), per-Change lock (DR10) |
| `publication_provider.py` | 476 | stdlib, pydantic (L06) | PR, check and merge contracts; `classify_publication_check` (P10); `merge_request_body` never bypasses rules |
| `serve/delivery-github`: `GitHubCliPublicationProvider`, `effect_launcher`, `InMemoryPublicationProvider` | 2,338 | Only the provider contract; repoint `github.py` L17 from the package root (L06) | Adapt: J6–J8 publication, checks, merge; in-memory double for the few P8 tests. Rule reads must keep unknown visibility unknown — `_read_branch_rules` treats every HTTP 403 as "no rules" — and the profile must supply required-check identities, which the exported merge settings omit (DR1, P10). Add merge-queue following (row M3) and verify GitHub Enterprise hosts |
| `merge_offer.py`, `merge_approval.py` | 581 | Provider contract, `storage_io` (L07) | Adapt: keep block reasons and attempt readback; drop `finalization_id`, `ready_receipt_id`, `review_id` |
| `worker_stall.py`: `ProcessTableWorktreeProbe`, `psutil_user_processes` | 546 | None (L08) | Adapt: termination evidence for DR10, B6, X5; drop `DeliveryClaimIssuer` |
| `acceptance_criteria.py`: `parse_acceptance_item`, `acceptance_version` | 116 | pydantic (L09) | Criterion identity and version as one P5 input |

About 1k lines reuse as is and 3.5k with adaptation: roughly 7% of engine plus GitHub adapter.

Not worth reusing as code:

| Module or area | Why (L-ref) | Keep instead |
| --- | --- | --- |
| `work_items.py` `derive_delivery_progress` | Inputs are readiness, card, frontier and custody (L10): it projects the machine (RC5) | The single-derivation idea and the `DeliverySituation`/`DeliveryWaitingOn` vocabulary for D3 |
| `evidence.py`, `acceptance.py` | Receipt and transaction models (L09) | P5 is a different model |
| `workspace_preservation.py`, `workspace_target_sync.py`, `change_workspace.py` | Fence mixins over recovery and transactions; engine merge runs hooks (L11) | The `git status --porcelain=v1 -z --untracked-files=all --ignored=matching` inventory as a recipe |
| `delivery_runtime`, `runtime_*`, `application_*`, `recovery`, `state_*`, `portfolio_*`, loader | The authority model itself | Nothing |
| `serve/delivery-mcp` | 64-tool registry, field-less schemas (L03) | New T1–T8 tools |
| Delivery loop skills (`w-orchestration`, `w-delivery-*`, `w-target-conflict-resolution`) | Loop prose replaced by code (P2) | Worker craft from `h-ac-quality`, Builder and reviewer checklists, rewritten against T1–T8 |
| Cockpit Delivery route and views | `target_work.py` and ~8.45k web lines typed to old projections (L12) | Shell, theme, `usePollingFetch`, `CopyCommand`, Ideas and Memory; table and merge-dialog patterns. Depends on Q9 |

Correction to the rebuild research Q1: the GitHub provider is **not** coupled to the old authority
model at import level (L06); only its package-root import and the merge models' proof fields are.
Evidence types are coupled, as stated.

### 3.5 Platform dependence, open Changes (TD-2) and consumer fit

| Concern | R1 | R2 | R2+3 |
| --- | --- | --- | --- |
| Preview dependence | None new, but bound to Local, which "will be removed" (L01 F2) | High: agent merge, automations, cleanup, badges (W04), hooks (W02), dynamic workflows (W03) | SDK is GA (W01); open points are runtime behavior for R8 (questions, permissions, termination, billing). Python structured output experimental (L01 Q7) |
| Open Changes on the old engine | Every fix reaches them only through `/upgrade-delivery` and state migrations of the pinned controller (L13) | Untouched | Untouched: separate package, state root and MCP server name; old skills stay in Local locations until M6 (E1) |
| Consumer project | Assumes OwlBear toolchain; state in product branches (RC3) | Good for platform users; enterprise policy may block previews (row S4); missing dependencies in worktrees | Profile-first; state outside the checkout (DR11); SDK bundles the CLI (W01). Enterprise enablement of SDK/CLI use is checked per consumer (row S4) |

### 3.6 Effort, risk and how each route fails

| Route | Effort (relative) | Risk | What makes it fail |
| --- | --- | --- | --- |
| R1 | Smallest next step; largest total | High | Fix-by-addition continues (RC4); each fix risks the open Changes; Local removal forces a port anyway (option S1 was rejected in L01 §3.9) |
| R2 | Smallest code | High, external | Preview features change or vanish; not callable from code; touchpoints exceed the budget; failures not observable as exits |
| R2+3 | Medium–high: new loop, profile, status, tools; M3 design dominates | Medium | Second-system overbuild; porting old modules re-imports the authority model; R8 gaps in question round trips or permissions; two systems coexisting confuse prompts and status until M6 |

Mitigations for R2+3: R4 budgets before code (P7, T7); reuse only §3.4's list, copied; no module
import from `owlbear_delivery`; one vertical slice at a time on the sandbox (M4).

## 4. Recommendation, Confidence, and Limits

**Recommendation (`autonomous`):** take the merged route R2+3, a thin core on the Copilot runtime.
Reject R1. Use R2's discipline as the core's scope rule: Delivery owns only what the ownership map
assigns it; everything git, GitHub, CI and the Copilot runtime already own stays there. Reuse the
eight items in §3.4's first table by copying; reuse nothing from the authority model.

Decisive reasons: R1 must change all four P9 contracts, so it is a rewrite done inside the engine the
open Changes depend on (TD-2) and on a deprecated harness. Pure R2 cannot hold the touchpoint budget,
one status line or the exit contract, because the features it would delegate to are preview UI
features owned per session. R2+3 builds the exit contract, budgets and consumer profile in from the
start, depends on a GA SDK rather than previews, and leaves the old engine untouched.

**Confidence:** high that R1 should be rejected; medium-high that R2+3 beats pure R2; medium on the
exact delegation boundary, which R8 settles.

**Conditions that would change it:**

| Condition | Effect |
| --- | --- |
| R8: the SDK cannot drive a session with a custom agent and a validated result, or cannot surface questions and permissions while VS Code is open | Core stays; the loop runs inside a Copilot-harness session or as a dynamic workflow (Q7), with the one-"continue" fallback |
| R8: agent merge, PR creation and worktrees are callable and observable from code, and generally available | Shift toward R2: delegate J5 and rows P1, P3 and M2 to agent merge; the core shrinks |
| Enterprise policy blocks SDK or CLI use for typical consumers | Re-evaluate: harness-hosted loop, or narrower consumer support |
| R8 billing: one Change costs more than the user accepts | Fewer agent calls per step; may favor platform features |
| M3 finds most stages need receipts and custody fences of the old model | Reconsider reuse of the authority model; R1 stays rejected because of TD-2 and Local |
| Local removal announced with a date before M6 | Route unchanged; cutover accelerated |

**Limits:** coupling was read from imports and signatures, not by running anything; reused modules
need their tests copied or rewritten under P8. Platform facts are documentation-level until R8. Effort
is relative only. No Delivery state, lane or worktree was touched.
