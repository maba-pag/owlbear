# Delivery Tool Surface Audit

> **Owning task:** none yet — input to the [liveness-first rebuild](delivery-liveness-first-rebuild.md) (M1 ownership map, M3 D4)
> **Date:** 2026-10-10
> **Question:** Which Delivery MCP tools exist, which agents and workflows use them for what, how hard
> are their arguments to supply correctly, and what tool-design rules should the rebuild adopt?
> **Status:** Analysis, corrected after an independent challenge (2026-10-10). Tool-contract rules
> T1–T8 (§4) are user-decided (2026-10-10). No tool, agent grant or skill was changed. Counts are at
> `753eb92`; #440 later added two fields (538).

## 1. Context and Question

The user observed that Delivery has more than 60 MCP tools, many for recovery and repair, and that
agents frequently get tool arguments wrong. The hypothesis to test: a small tool with one clear job and
one or two arguments is reliable, while a many-argument "do everything" tool fails more often and should
be split. This audit produces the two requested maps — agent to tool, and tool to arguments — measures
argument burden from the live registry, and derives design rules for the rebuild.

## 2. Sources Studied

| ID | Source | Fact used | Limits |
| --- | --- | --- | --- |
| A01 | Registry built in-process with `assemble_target_server` over a stub application (`.owlbear/scratch/tool-audit/extract_tools.py`) | 64 registered tools; names, annotations, descriptions, full input schemas | Same assembly as [the registry test](../../serve/delivery-mcp/tests/test_target_server.py); no live Delivery state touched |
| A02 | Schema walk (`identity_burden.py`, inline summary) | Per-tool field count, nesting depth, union points, 40/64-hex identities, `expected_*` fences, `confirmed_*` flags, length limits, field-description coverage | `$ref` cycles cut; counts include nested model fields |
| A03 | Text references in `share/agents`, `share/skills`, `share/prompts`, `.github/*`, `serve/cockpit` (`map_usage.py`) | Which agent grants, skills and prompts name each tool | A name match also counts prohibitions ("never call X"); `answer`/`repair` collide with ordinary words and were restricted to frontmatter grants and repair skills |
| A04 | `rg` over `serve/delivery/src`, `serve/cockpit`, tests | Callers of tools that no workflow names | Static search |
| A05 | Local session store, 2026-09-05 → 2026-10-09 | 7 turns with `ERR_TARGET_PARAM_VALIDATION` in 5 of 125 sessions | Floor only: tool errors live in debug logs that the index does not cover |
| W01 | [Anthropic: Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) (2025-09-11) | Fewer purpose-built tools; consolidate chained calls; distinct non-overlapping purposes; unambiguous parameter names; semantic identifiers beat cryptic IDs and reduce hallucination; actionable errors; evaluation-driven tool design | Vendor guidance; principles, not Copilot-specific measurements |

## 3. Analysis

### 3.1 Surface summary

| Measure | Value |
| --- | --- |
| Registered tools | 64: 21 read-only, 40 writes, 3 destructive |
| Argument fields, all levels | 536 |
| Fields with a schema description | **0 (0%)** |
| Tools with at most 6 fields | 54 |
| Fields in the five largest tools | 315 (59%) |
| Schema text for all 64 tools | ~85 KB, ~21k tokens |

The user's intuition is half right. Most tools — including nearly all recovery tools — are already small
(1–6 flat arguments). The burden is concentrated in five tools on the **normal** path, which every
Change crosses:

| Tool | Fields | Depth | Union points | Hex identities | `expected_*` fences | Length-limited text | Called by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `settle_worker_invocation` | 75 | 7 | 2 | 8 | 5 | 6 | Orchestrator |
| `submit_result` | 72 | 6 | 2 | 12 | 1 | 5 | Builder |
| `finalize_change` | 66 | 6 | 2 | 10 | 1 | 5 | Finalizer |
| `transition_delivery` | 53 | 6 | 1 | 5 | 2 | 1 | Orchestrator |
| `derive_evidence_receipts` | 49 | 5 | 1 | 7 | 1 | 5 | Builder, Finalizer |
| `report_finalization_failure` | 17 flat (10 required) | 2 | 0 | 7 | 6 | 4 | Finalizer |
| `acquire_change_action` | 14 | 2 | 0 | 8 | 1 | 2 | Orchestrator |

### 3.2 Map 1 — agents to tools

| Agent | Delivery tools granted | What it uses them for | Schema size |
| --- | --- | --- | --- |
| `orchestrator` | `get_change`, `acquire_change_action`, `execute_change_action`, `settle_worker_invocation`, `transition_delivery`, `release_stuck_worker`, `observe_acceptance` | Observe one Change, acquire one action, run an engine action, settle or forward a worker result, release a user-stopped worker, check a merge | ~5.6k tokens |
| `builder` | `show_build_context`, `derive_evidence_receipts`, `submit_result` | Load task context, mint evidence and review receipts, submit the exact-commit result | ~5.1k tokens |
| `planner` | `show_plan_context`, `publish_delivery_plan` | Load claim context, publish the task chain | ~0.7k tokens |
| `finalizer` | `show_finalization_context`, `derive_evidence_receipts`, `finalize_change`, `report_finalization_failure`, `reconcile_finalization_head` | Prove and finalize one reviewed head, or record a bounded failure | ~5.7k tokens |
| `designer` | `create_design_session`, `read_design_session`, `revise_design_session`, `derive_delivery_contract`, `publish_design_checkpoint`, `admit_change`, `get_change`, `set_change_intent`, `prepare_review_repair` | Author, checkpoint and admit a Design; pause/resume/abandon; open review repair | ~1.0k tokens |
| `designer-challenger` | `read_design_session`, `derive_delivery_contract` | Read-only Design challenge | ~0.1k tokens |
| `repairer` | `get_change`, `answer`, `repair` | Apply an engine-authored repair proposal or selected answer | ~0.7k tokens |
| Default agent through prompts | `resolve-delivery-attention`, `resolve-target-conflict`, `address-pr-feedback`: no restriction, all 64. `inspect-change`: 2; `upgrade-delivery`: 4; `repair-delivery`: none (offline commands) | Attention resolution, target sync, PR feedback, diagnostics | Up to ~21k tokens |

Named agents are well scoped: 26 of 64 tools are granted to a named agent, and no agent holds more than
nine. The broad exposure is the default agent: three maintenance prompts run without a tool
restriction, and one skill, `w-delivery-attention-resolution`, names 28 tools.

**Author/caller split.** The Builder is not granted `transition_delivery` or `settle_worker_invocation`.
It writes `block`, `retry` and `return` transitions as text in its final answer, and Orchestrator forwards
them. The author therefore never sees the schema that validates its payload — including the 512-character
`procedure` limit that rejected the 2026-10-09 B1 block after the Builder had ended
([rebuild research §3.3](delivery-liveness-first-rebuild.md#33-the-2026-10-09-session-as-a-microcosm)).

### 3.3 Map 1b — workflows to tools

| Workflow | Delivery tools it names |
| --- | --- |
| `w-delivery-attention-resolution` (default agent) | 28: inspection (`show_work_item`, `show_work_item_view`, `show_operator_context`, `show_integration_attention`, `delivery_health`, `get_change`), recovery (`recover_claim`, `recover_integration_repair_claim`, `recover_change_worktree`, `recover_out_of_band_head`, `recover_publication_baseline`, `adopt_external_head`, `promote_external_head`, `administrative_move`, `preview_administrative_move`), state repair (`repair`, `repair_delivery_state_snapshot`, `repair_target_sync_publication`), publication (`mark_change_ready`, `observe_change_publication_checks`, `reconcile_change_checkpoint`, `observe_acceptance`), intent (`set_change_intent`, `answer`), cleanup (three cleanup tools, `list_retained_change_worktrees`) |
| `w-orchestration` | 11, including prohibitions (`recover_claim`, `submit_result`, `report_finalization_failure` named as "do not call") |
| `w-design-session` | 9 |
| `w-change-finalization`, `w-packet-building` | 6 each |
| `w-address-pr-feedback`, `w-target-conflict-resolution` | 5 each |
| `w-frontier-planning` | 4 |
| `w-delivery-repair` | none: it uses offline repair commands |

Name matching counts prohibitions and other non-calling mentions; the counts show which tools a
workflow talks about, not which it calls.

### 3.4 Map 2 — tools and their arguments

Columns: kind (R read-only, W write, D destructive); required/top-level arguments; fields at all nesting
levels; maximum depth; 40/64-hex identities the caller must supply; `expected_*` fence values; users found
by name (§2 A03 limits apply).

#### Change loop

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `get_change` | R | Return one coherent Change detail, health, and repair projection | 1/1 | 1 | 1 | 0 | 0 | agents: orchestrator, designer, repairer; skills: w-delivery-attention-resolution, w-design-session, w-orchestration; prompts: continue-change, inspect-change, upgrade-delivery |
| `acquire_change_action` | W | Acquire at most one supported action for the exact selected Change | 5/5 | 14 | 2 | 8 | 1 | agents: orchestrator; skills: w-orchestration; prompts: continue-change |
| `execute_change_action` | W | Invoke only the engine-owned operation already acquired for this Change | 2/2 | 2 | 1 | 1 | 0 | agents: orchestrator; skills: w-orchestration; prompts: continue-change |
| `settle_worker_invocation` | W | Settle one exact ended Planner or Builder invocation, or a normally returned Finalizer invocation | 1/3 | 75 | 7 | 8 | 5 | agents: orchestrator; skills: h-decision-requests, w-frontier-planning, w-orchestration, w-packet-building |
| `transition_delivery` | W | Apply one worker-owned Delivery transition | 2/2 | 53 | 6 | 5 | 2 | agents: orchestrator; skills: h-ac-quality, w-frontier-planning, w-orchestration, w-packet-building |
| `release_stuck_worker` | W | Settle one user-confirmed stopped worker as a failed attempt once nothing still uses its worktree | 3/4 | 4 | 1 | 0 | 0 | agents: orchestrator; skills: w-orchestration |
| `observe_acceptance` | W | Observe acceptance once (Check again): one read per call, never a budget reset; it never merges | 1/1 | 1 | 1 | 0 | 0 | agents: orchestrator; skills: w-address-pr-feedback, w-delivery-attention-resolution, w-orchestration; prompts: continue-change |
| `acquire_actions` | W | Acquire one fenced action when selection is supplied, otherwise a portfolio batch | 0/1 | 7 | 2 | 2 | 4 | **none found** (tests only) |

#### Worker context and results

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `show_plan_context` | R | Show bounded Planning context for one claim | 4/4 | 4 | 1 | 0 | 0 | agents: planner; skills: w-frontier-planning |
| `publish_delivery_plan` | W | Publish one claim-scoped Delivery plan | 2/2 | 18 | 5 | 0 | 0 | agents: planner; skills: h-ac-quality, w-frontier-planning |
| `show_build_context` | R | Show bounded Build context for one claim | 4/4 | 4 | 1 | 0 | 0 | agents: builder; skills: w-packet-building |
| `derive_evidence_receipts` | R | Return canonical observation and review receipts without reading or changing Delivery state | 0/2 | 49 | 5 | 7 | 1 | agents: builder, finalizer; skills: w-change-finalization, w-packet-building |
| `submit_result` | W | Publish and promote one exact Builder result as one claim-bound operation | 4/4 | 72 | 6 | 12 | 1 | agents: builder; skills: r-workspace-governance, w-orchestration, w-packet-building |

#### Design

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `create_design_session` | W | Create one authored Design session | 3/3 | 3 | 1 | 0 | 0 | agents: designer; skills: w-design-session; prompts: ideate |
| `read_design_session` | R | Read one verified authored Design session and its current identity | 1/1 | 1 | 1 | 0 | 0 | agents: designer, designer-challenger; skills: w-design-session; prompts: design, ideate |
| `revise_design_session` | W | Replace authored Design bytes for one exact package identity | 4/4 | 4 | 1 | 1 | 1 | agents: designer; skills: w-design-session; prompts: design |
| `put_design` | W | Create or CAS-revise one authored Design package | 3/4 | 4 | 1 | 1 | 1 | **none found** (tests only) |
| `derive_delivery_contract` | R | Derive one Delivery contract without publication | 1/1 | 1 | 1 | 0 | 0 | agents: designer, designer-challenger; skills: w-design-session |
| `publish_design_checkpoint` | W | Publish one verified Design checkpoint | 1/1 | 1 | 1 | 0 | 0 | agents: designer; skills: w-design-session |
| `admit_change` | W | Admit one exact approved Design version as executable Delivery authority | 3/6 | 6 | 2 | 4 | 3 | agents: designer; skills: w-design-session |
| `admit_delivery_change` | W | Admit one source-bound Delivery change | 3/6 | 6 | 2 | 4 | 3 | **none found** (tests only; same arguments as `admit_change`) |
| `set_change_intent` | W | Apply one version-bound pause, resume, or abandon intent; Pause under custody drains first | 3/4 | 4 | 1 | 1 | 1 | agents: designer; skills: w-delivery-attention-resolution, w-design-session |
| `prepare_review_repair` | W | Return one open Change pull request to draft before external review repair | 1/1 | 1 | 1 | 0 | 0 | agents: designer; skills: w-address-pr-feedback, w-design-session |

#### Finalization and publication

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `show_finalization_context` | R | Show engine-resolved context for one exact Change finalization | 1/1 | 1 | 1 | 0 | 0 | agents: finalizer; skills: w-address-pr-feedback, w-change-finalization, w-target-conflict-resolution; prompts: finalize-change |
| `finalize_change` | W | Finalize one exact clean reviewed Change head with persisted evidence | 2/2 | 66 | 6 | 10 | 1 | agents: finalizer; skills: w-change-finalization; prompts: finalize-change |
| `report_finalization_failure` | W | Persist one bounded finalization diagnostic without granting proof authority | 10/17 | 17 | 2 | 7 | 6 | agents: finalizer; skills: w-change-finalization, w-orchestration |
| `reconcile_finalization_head` | W | Retain or invalidate finalization from engine-derived local/provider head evidence | 1/1 | 1 | 1 | 0 | 0 | agents: finalizer; skills: w-change-finalization |
| `reconcile_change_checkpoint` | W | Reconcile one durable checkpoint using only engine-derived external identities | 1/1 | 1 | 1 | 0 | 0 | skills: w-address-pr-feedback, w-delivery-attention-resolution |
| `observe_change_publication_checks` | R | Observe checks at the engine-derived published Change head | 1/1 | 1 | 1 | 0 | 0 | skills: w-delivery-attention-resolution |
| `mark_change_ready` | W | Mark one exact finalized and fully published Change pull request ready | 4/4 | 4 | 1 | 2 | 0 | skills: w-delivery-attention-resolution |
| `supersede_publication` | W | Publish one successor branch and pull request for exact publication attention | 3/3 | 3 | 1 | 1 | 1 | Cockpit only |

#### Target sync

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sync_change_with_target` | W | Fetch and merge one exact target head through the managed Change worktree | 3/3 | 3 | 1 | 1 | 1 | skills: w-target-conflict-resolution |
| `resolve_target_sync_conflict` | W | Resolve one exact preserved target-sync conflict with a reviewed merge | 4/4 | 4 | 1 | 2 | 1 | skills: w-target-conflict-resolution |
| `abort_target_sync_conflict` | W | Abort one exact preserved target-sync conflict | 4/4 | 4 | 1 | 2 | 1 | Cockpit only |
| `repair_target_sync_publication` | W | Repair one exact quarantined target-sync publication after confirmation | 6/6 | 6 | 1 | 2 | 2 | skills: w-delivery-attention-resolution |

#### Attention, requests and recovery

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `list_work_items` | R | List bounded work-item projections | 0/0 | 0 | 0 | 0 | 0 | skills: w-address-pr-feedback, w-target-conflict-resolution; prompts: upgrade-delivery |
| `show_work_item` | R | Show one exact bounded work item | 2/2 | 2 | 1 | 0 | 0 | skills: w-delivery-attention-resolution |
| `show_work_item_view` | R | Show one exact detailed Work Item view | 2/2 | 2 | 1 | 0 | 0 | skills: w-delivery-attention-resolution, w-target-conflict-resolution |
| `show_operator_context` | R | Show bounded operator state for one exact outcome or Change | 2/2 | 2 | 1 | 0 | 0 | skills: w-delivery-attention-resolution |
| `show_integration_attention` | R | Show current typed Integration attention | 1/1 | 1 | 1 | 0 | 0 | skills: w-delivery-attention-resolution |
| `answer` | W | Apply one version-bound answer to a retained Delivery request | 2/10 | 13 | 2 | 2 | 2 | agents: repairer; skills: w-delivery-repair |
| `repair` | W | Diagnose or apply one high-level repair proposal | 1/3 | 3 | 1 | 1 | 0 | agents: repairer; skills: w-delivery-repair, w-delivery-attention-resolution |
| `preview_administrative_move` | R | Preview one backward movement without changing Delivery state | 3/3 | 3 | 1 | 0 | 0 | skills: w-delivery-attention-resolution |
| `administrative_move` | W | Apply one exact operator-directed backward movement | 6/6 | 6 | 1 | 1 | 1 | skills: w-delivery-attention-resolution |
| `recover_claim` | W | Request exact recovery; caller confirmation cannot establish worker exclusion | 5/5 | 5 | 1 | 0 | 0 | skills: w-delivery-attention-resolution, w-orchestration, w-packet-building |
| `recover_integration_repair_claim` | W | Request legacy Integration recovery without treating identity as exclusion evidence | 3/3 | 3 | 1 | 0 | 0 | skills: w-delivery-attention-resolution |
| `recover_change_worktree` | W | Recreate one exact Change worktree after explicit reviewed-head confirmation | 3/3 | 3 | 1 | 1 | 0 | skills: w-delivery-attention-resolution |
| `recover_out_of_band_head` | W | Preserve one out-of-band Change head and restore reviewed authority | 6/6 | 6 | 1 | 3 | 3 | skills: w-delivery-attention-resolution |
| `recover_publication_baseline` | W | Recover one unknown publication baseline after explicit confirmation | 5/5 | 5 | 1 | 2 | 1 | skills: w-delivery-attention-resolution |
| `adopt_external_head` | W | Adopt one exact remote Change descendant through the managed Change worktree | 4/4 | 4 | 1 | 2 | 1 | skills: w-delivery-attention-resolution |
| `promote_external_head` | W | Promote one exact adopted external Change head before Builder acquisition | 3/3 | 3 | 1 | 1 | 1 | skills: w-change-finalization, w-delivery-attention-resolution |

#### Controller state repair

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `delivery_health` | R | Return bounded diagnostics for quarantined or unavailable Delivery state | 0/0 | 0 | 0 | 0 | 0 | skills: w-delivery-attention-resolution; prompts: inspect-change, upgrade-delivery |
| `repair_delivery_state_snapshot` | W | Repair one exact confirmed local frontier successor over remote state | 3/3 | 3 | 1 | 0 | 0 | skills: w-delivery-attention-resolution |
| `propose_quarantined_delivery_state_snapshot_repair` | R | Return exact fences for one known quarantined remote snapshot | 1/1 | 1 | 1 | 0 | 0 | engine repair proposals only |
| `repair_quarantined_delivery_state_snapshot` | W | Repair one exact confirmed quarantined remote Delivery snapshot | 6/6 | 6 | 1 | 2 | 3 | engine repair proposals only |
| `repair_stranded_frontier` | W | Repair one exact confirmed missing request-provenance defect | 5/5 | 5 | 1 | 1 | 1 | engine repair proposals only |

#### Cleanup

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `list_retained_change_worktrees` | R | List retained Change worktrees and their cleanup eligibility | 0/0 | 0 | 0 | 0 | 0 | skills: w-delivery-attention-resolution |
| `cleanup_abandoned_change_worktree` | D | Remove one exact abandoned Change worktree while retaining its branch | 1/1 | 1 | 1 | 0 | 0 | skills: w-delivery-attention-resolution |
| `cleanup_abandoned_change_worktree_after_target_sync_discard` | D | Discard one abandoned target merge and remove its exact worktree | 4/4 | 4 | 1 | 1 | 2 | skills: w-delivery-attention-resolution |
| `cleanup_completed_change_worktree` | D | Remove one exact completed Change worktree after receipt validation | 2/2 | 2 | 1 | 1 | 0 | skills: w-delivery-attention-resolution |

#### Portfolio and history

| Tool | Kind | Purpose | Args (req/top) | Fields | Depth | Hex IDs | Fences | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `list_changes` | R | Return grouped Change state and operating guidance | 0/0 | 0 | 0 | 0 | 0 | skills: w-orchestration; prompts: upgrade-delivery |
| `list_completed_changes` | R | List one bounded completed-history page | 0/2 | 2 | 1 | 0 | 0 | Cockpit only |
| `search_completed_changes` | R | Search bounded completed-history summaries | 1/3 | 3 | 1 | 0 | 0 | Cockpit only |
| `show_completed_change` | R | Show one exact completed Delivery change | 1/2 | 2 | 1 | 1 | 0 | Cockpit only |

### 3.5 Why arguments go wrong

| ID | Mechanism | Evidence | Effect |
| --- | --- | --- | --- |
| AF1 | **Identity echo.** Agents must copy exact 40/64-hex identities and fence values from earlier responses | Schema paths (all branches, optional included): `submit_result` 12 hex identities; `finalize_change` 10; `acquire_change_action` 8; `settle_worker_invocation` 8 plus 5 `expected_*` fields. A single call needs fewer, and some are server-issued values echoed back | Copying long opaque strings is where models hallucinate (W01); a single wrong character is a hard rejection |
| AF2 | **Do-everything unions.** One tool accepts several operations distinguished by shape or discriminator | `settle_worker_invocation`: three untagged variants, each valid only for some roles; `transition_delivery`: four discriminated actions; `answer`: 10 top-level arguments validated by mode | The agent must select the right branch and omit the others; schema errors name branches it never meant to use (the 2026-10-09 error listed 11 alternatives) |
| AF3 | **Author is not the caller.** Builder authors transitions as text; Orchestrator forwards them | Builder lacks `transition_delivery`; B1 `procedure` rejected after the Builder had ended | Validation feedback reaches an agent that may not change the payload; the claim stays stuck |
| AF4 | **No field documentation.** 0 of 536 fields carry a description; limits live in prose | The `procedure` limit of 512 was missing from `w-packet-building` at incident time (added by #443); the transport error still says only "Invalid tool arguments. Check the tool input schema" without naming the field | Agents infer meaning from field names alone and cannot tell which field to fix |
| AF5 | **Flat many-argument writes.** | `report_finalization_failure`: 17 top-level arguments, 10 required, 6 fences | Many independent chances to be wrong in one call |
| AF6 | **Unbounded default-agent exposure.** | Three maintenance prompts carry no tool restriction; up to 64 tools and ~21k tokens of schema | Tool selection errors among similar recovery tools; context spent on tools the task never needs |

### 3.6 Redundant, dead and misplaced surface

| Finding | Tools |
| --- | --- |
| No caller outside tests | `acquire_actions` (portfolio acquisition retired by continuation), `admit_delivery_change` (same arguments as `admit_change`), `put_design` (overlaps `create_design_session` and `revise_design_session`) |
| Called only by Cockpit, still exposed to agents | `supersede_publication`, `abort_target_sync_conflict`, `list_completed_changes`, `search_completed_changes`, `show_completed_change` |
| Reached only through engine-authored repair proposals | `propose_quarantined_delivery_state_snapshot_repair`, `repair_quarantined_delivery_state_snapshot`, `repair_stranded_frontier` |
| Recovery, repair and cleanup families | 16 attention/recovery, 5 controller-state repair, 4 cleanup, 1 target-sync publication repair: 26 tools, mostly 3–6 flat arguments |
| Overlapping read views | `get_change`, `show_work_item`, `show_work_item_view`, `show_operator_context`, `show_integration_attention`, `list_work_items`, `list_changes` all project Change state |

### 3.7 Assessment against tool-design guidance

| Principle (W01) | Delivery today |
| --- | --- |
| Few tools, each with a clear and distinct purpose | 64 tools; seven overlapping state views; recovery split into many single-situation tools |
| Consolidate frequently chained calls | Continuation chains `get_change` → `acquire_change_action` (copy basis) → `execute_change_action` on every cycle |
| Semantic identifiers instead of cryptic IDs | Normal-path writes require 5–12 hex identities |
| Unambiguous, documented parameters | No field descriptions |
| Actionable errors | Schema errors list every union branch; the merge-commit failure was an unexplained "Error executing tool" ([rebuild research §3.3](delivery-liveness-first-rebuild.md#33-the-2026-10-09-session-as-a-microcosm)) |
| Evaluate tools against realistic tasks | Extensive unit tests of the engine; no evaluation of agent tool-call success |

## 4. Recommendation, Confidence, and Limits

The problem is less the number of tools than **what agents must author and copy**. Splitting large
tools alone would multiply tools without removing the copied identities.

**Decision TD-1 (origin `decided`, 2026-10-10):** the user accepted rules T1–T8 as the tool contract
for the rebuilt Delivery (M3 D4), in direct reply to this audit. Concrete budget values for T7 are set in
the R4 charter; the figures in T7 are examples, not decided limits. Changing any rule requires the user
to re-decide it.

| ID | Rule | Replaces |
| --- | --- | --- |
| T1 | **One job per agent-facing tool.** No discriminated unions: split `settle`/`transition`/`answer`-style tools by action (for example `report_blocked`, `request_retry`, `return_to_planning`) | AF2 |
| T2 | **Agents author content, not identity.** The server binds Change, claim, attempt, heads and fences from the session or a single short handle it issued; agents never echo hex identities or fence values | AF1 |
| T3 | **The author calls the validating tool** while it can still correct the payload; payload limits are returned as actionable errors to that author | AF3 |
| T4 | **Every field described**, with limits and one example; errors name the one field to fix | AF4 |
| T5 | **Small flat writes.** At most about six fields and one level of nesting; evidence submitted as simple records the server canonicalizes | AF5 |
| T6 | **Recovery belongs to the engine and the user, not to agents.** Engine-owned recovery runs automatically; user decisions run as Cockpit actions; at most one agent tool requests recovery | AF6, §3.6 |
| T7 | **Budgets enforced by tests** (milestone M7): concrete limits set in the R4 charter, for example at most 15 agent-facing tools in total, at most five per role, no dead or Cockpit-only tools exposed to agents | Fix-by-addition |
| T8 | **Measure tool-call success** during the M4 demonstration and real use (M5): invalid-argument rate, retries, wrong-tool selection | No evaluation |

On the Copilot runtime ([rebuild research §3.9](delivery-liveness-first-rebuild.md#39-platform-migration-interplay)),
T2 and T3 become easier: a code-driven loop holds identities in code and asks agents only for judgment,
and dynamic workflows request structured results with automatic format correction.

**Interim cleanup — rejected (challenge, 2026-10-10):** removing the three test-only tools, hiding
Cockpit-only tools from agents and describing the five large tools would not have prevented the B1
failure, which came from the author/caller split and the field-less error. It would only churn code
the open Changes still run on (M0).

**Beyond T1–T8:** an interrupted write whose acknowledgement is lost must be safe to replay. The
[journey research](delivery-next-journey-and-failure-modes.md#35-design-requirements) covers this as
re-entry by observation (DR5, row X4).

**Confidence:** high for the inventory, argument metrics and grants (generated from the registry and
frontmatter). Medium for workflow usage (name matching includes prohibitions). Low for error frequency
(session index is a floor). The rules T1–T8 follow established tool-design guidance and the observed
B1 failure; their effect should be measured by T8 rather than assumed.

**Limits:** schema token counts are byte approximations; the Copilot harness may load tools lazily, which
reduces context cost but not argument burden. Scratch extraction scripts are in
`.owlbear/scratch/tool-audit/` and are not maintained artifacts.
