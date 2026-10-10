# Delivery Next: Ownership Map

> **Owning task:** none — M1 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** For every responsibility the current Delivery system carries, who owns it in the next
> version — git, GitHub, CI, the Copilot platform, the new thin core (Delivery-next) or nobody — and
> what minimal state and operations remain for Delivery-next?
> **Status:** M1 analysis at `dev` `0fca95146`. Uses the user's decisions TD-1 to TD-8 of the
> [rebuild research](delivery-liveness-first-rebuild.md#38-decisions-reserved-for-the-user); every
> conclusion here is `autonomous` until the user approves the charter.

## 1. Context and Question

M1 needs an ownership map: what git, GitHub, CI and the Copilot platform already own, and what
Delivery must own ([rebuild §3.7](delivery-liveness-first-rebuild.md#37-roadmap-milestones-documents-and-products)).
The [route comparison](delivery-next-route-comparison.md) chose a thin core on the Copilot runtime
(R2+3) and left the exact delegation boundary to this map and the [R8 probe](delivery-next-platform-probe.md).

Every row comes from a module docstring, skill, agent, prompt or tool of the current system. Probe
verdicts are cited as P1–P12; "unproven" names what R8 did not establish.

## 2. Sources Studied

| ID | Source | Relevant fact | Limits |
| --- | --- | --- | --- |
| L01 | [Rebuild research](delivery-liveness-first-rebuild.md) §3.4–§3.9 | RC1–RC6, P1–P9, M0–M7, TD-1–TD-8, platform findings F1–F5 | Only TD-1–TD-8 are user decisions |
| L02 | [Journey research](delivery-next-journey-and-failure-modes.md) | J0–J9, five exits plus pending, catalogue rows, DR1–DR15 | Likelihood labels are judgments |
| L03 | [Route comparison](delivery-next-route-comparison.md) §3.4 | Reuse list of eight items, ~4.5k lines, copied not imported | Coupling read statically |
| L04 | [Platform probe](delivery-next-platform-probe.md) §3.2, §4 | Verdicts P1–P12 | One laptop, free identity, Auto models, private unprotected repository |
| L05 | [Tool-surface audit](delivery-tool-surface-audit.md) | 64 tools, recovery families, rules T1–T8 | Counts at `753eb92` |
| L06 | `ls` and `ast.get_docstring` over [owlbear_delivery](../../serve/delivery/src/owlbear_delivery/) | 55 modules with one-line purposes and line counts; all are classified below | Docstrings summarize; bodies read only where cited |
| L07 | [delivery-github](../../serve/delivery-github/src/owlbear_delivery_github/) | `github.py` 1,541 lines (gh provider), `effect_launcher.py` 261 (frozen-body merge launch), `memory.py` 536 (test double) | — |
| L08 | [delivery-mcp](../../serve/delivery-mcp/src/owlbear_delivery_mcp/) | `target_server.py` 1,456 and `target_models.py` 1,457 lines expose the 64 tools | — |
| L09 | [Cockpit backend](../../serve/cockpit/src/owlbear_cockpit/) | `routes/target_work.py` 931, `target_models.py` 716, `target_context.py` 51 serve Delivery; `routes/ideas.py`, `routes/memory.py` do not | Web views not re-read; route comparison L12 covers them |
| L10 | [serve/tools](../../serve/tools/src/owlbear_tools/) `delivery_*.py` | `delivery_controller` (install, pin, verify releases), `delivery_lc` (live-compatibility gate), `delivery_migration`, `delivery_repair`, `delivery_diagnostics`, `delivery_config` | Docstrings |
| L11 | [setup/init.py](../../setup/init.py) L62–L83, L994–L1042 | Writes `.owlbear/delivery/config.json`, sets state branch `owlbear/delivery-state`, registers the `owlbear-delivery` MCP server | — |
| L12 | `grep` for `refs/` over the engine | Custom refs: `attempts`, `quarantine`, `quarantine-index`, `recovery`, `target-sync`, `target-observation`, `packages` | Literal count only |
| L13 | Delivery skills `share/skills/w-*` (nine, 2,541 lines), `h-ac-quality`, `h-decision-requests`, `h-process-observations`; agents and prompts in `share/` | Loop prose, worker craft and user entry points | Line counts today |

## 3. Analysis

### 3.1 Owners

| Owner | What it owns | Preview or unproven parts |
| --- | --- | --- |
| git | Commits, branches, worktrees, merges, refs, history | — |
| GitHub | Pull requests, reviews and code owners, checks and statuses, rulesets, merge with a head-SHA guard, merge queue, push protection | Rules and protected merge unproven (R8: HTTP 403 on the free plan) |
| CI | Running the project's checks on the pushed head | — |
| Copilot platform | Sessions, custom agents and subagents, model routing, tool-permission enforcement, transcripts and resume, loading repository agents and skills | Preview: agent merge, Agents-window PR form, automations, dynamic workflows. Unproven: explicit models (P6) |
| Delivery-next | Intent, brief, plan, the loop with exits and budgets, questions, check validity, merge consent, lock, status, project profile | — |
| drop | Exists only for the old authority model (custody, receipts, fences) | — |

### 3.2 Intent and design

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Refine a rough idea | [w-idea-refinement](../../share/skills/w-idea-refinement/SKILL.md), `/ideate` | Copilot platform (repository skill) | Pre-Change conversation; repository skills load (R8 P7) | J2 |
| Shape the brief with the user | [w-design-session](../../share/skills/w-design-session/SKILL.md), `designer` | Copilot runs the Designer interactively; Delivery-next stores the brief | Chat belongs to the platform; the brief is Change state | J2, D1–D3 |
| Challenge the brief | `designer-challenger`, `conceptual-design-reviewer` | Delivery-next runs a read-only agent | Typed verdict and read-only handler proven (P1, P5) | J2, D5 |
| Authored design packages with Git checkpoints | [design_package](../../serve/delivery/src/owlbear_delivery/design_package.py), `refs/owlbear/packages` | drop | Authority on branches caused self-conflicts (RC3) | DR11 |
| Admit design; compile the Delivery Contract | [delivery_admission](../../serve/delivery/src/owlbear_delivery/delivery_admission.py), [target_contract](../../serve/delivery/src/owlbear_delivery/target_contract.py), [delivery_contract_discovery](../../serve/delivery/src/owlbear_delivery/delivery_contract_discovery.py) | Delivery-next records approval of one brief version | Approval is a touchpoint; admission transactions served receipts | J2, DR4 |
| Acceptance-criterion identity and version | [acceptance_criteria](../../serve/delivery/src/owlbear_delivery/acceptance_criteria.py) | Delivery-next (reuse) | Criterion version is a recorded check input (P5) | H3 |
| Pause, resume, abandon | [application_lifecycle](../../serve/delivery/src/owlbear_delivery/application_lifecycle.py), `set_change_intent` | Delivery-next; GitHub closes the PR on abandon | User intent has no external owner | D6, X6 |

### 3.3 Planning

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Ordered task list with checks | [w-frontier-planning](../../share/skills/w-frontier-planning/SKILL.md), `planner`, `publish_delivery_plan` | Copilot runs the Planner; Delivery-next validates and stores the typed plan | P1 proven; structured output is experimental, so the loop validates and retries | J3, D4 |
| Challenge the plan | `planner-challenger`, [r-challenger-protocol](../../share/skills/r-challenger-protocol/SKILL.md) | Delivery-next runs a read-only agent | As for the brief | J3, D9 |
| Bounded worker context | [portfolio_application](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) (`show_plan_context`, `show_build_context`) | Delivery-next builds the prompt | Code passes context; no handles to copy (T2) | DR12 |
| Frontier, stages, claims, transitions | [delivery_runtime](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py), [runtime_models](../../serve/delivery/src/owlbear_delivery/runtime_models.py), [runtime_reads](../../serve/delivery/src/owlbear_delivery/runtime_reads.py), [runtime_support](../../serve/delivery/src/owlbear_delivery/runtime_support.py) | drop; plan plus current step | Claims served custody; the lock gives one writer | DR4, DR10 |
| Overlap with other open Changes | none | Delivery-next | Only Delivery knows other plans | D7 |

### 3.4 Task execution

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Run one task with a custom agent | [w-packet-building](../../share/skills/w-packet-building/SKILL.md), `builder`, [w-orchestration](../../share/skills/w-orchestration/SKILL.md), [application_acquisition](../../serve/delivery/src/owlbear_delivery/application_acquisition.py) | Copilot (SDK session); Delivery-next picks agent, prompt and permissions | Proven (P1, P9); agent dispatch partial (P6); the loop leaves prose (RC2) | J4, B4 |
| Model per step | Agent frontmatter, model tiers | Delivery-next decides; Copilot routes | Unproven: explicit model selection (P6 replaced it with Auto silently) | DR13, S9 |
| Isolated workspace per Change | [change_workspace](../../serve/delivery/src/owlbear_delivery/change_workspace.py), [workspace_worktree_state](../../serve/delivery/src/owlbear_delivery/workspace_worktree_state.py), [workspace_snapshots](../../serve/delivery/src/owlbear_delivery/workspace_snapshots.py), [workspace_models](../../serve/delivery/src/owlbear_delivery/workspace_models.py) | git worktree; Delivery-next creates and removes it | Agents-window worktrees are UI-only with "Allow all"; SDK session in a worktree proven (P8, P9) | J4, B19 |
| Install, check, commit with hooks | Builder skill (`uv`), engine merge commit | Copilot agent inside the task | P9: agent fixed missing `node_modules`; hooks are project policy | B1–B3, DR3 |
| Unattended tool permissions | Local approval prompts | Copilot enforces; Delivery-next owns each step's allow list | Proven (P5): deny wins, unlisted denied, no hang | B7, DR9 |
| Verify result and route the exit | `submit_result`, [runtime_settlement](../../serve/delivery/src/owlbear_delivery/runtime_settlement.py), [runtime_receipts](../../serve/delivery/src/owlbear_delivery/runtime_receipts.py) | Delivery-next checks diff, exit codes, checklist | Settlement replay and receipt chains drop | B4, B5, DR4 |
| End hung or orphaned workers | [worker_stall](../../serve/delivery/src/owlbear_delivery/worker_stall.py), `release_stuck_worker` | Delivery-next via `tasks.list`, `tasks.cancel`, PID check | Partial (P4b) while the runtime lives; after a crash only recorded PIDs | B6, DR10 |

### 3.5 Independent review

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Review each task commit | `build-reviewer`, review receipts in [evidence](../../serve/delivery/src/owlbear_delivery/evidence.py) | Delivery-next runs a read-only reviewer with a typed verdict | P1, P5 proven; reviewer model unproven (P6) | J4, B12 |
| Keep the reviewer read-only | Agent tool lists, Local hooks | Copilot permission handler, Delivery-next policy | Proven (P5); pre-tool hooks unproven | DR9 |
| Review valid until inputs change | Exact-commit review receipts | Delivery-next records reviewed head and files | Stops re-review per commit (P5) | I1 |
| Review on the PR | [w-address-pr-feedback](../../share/skills/w-address-pr-feedback/SKILL.md), `prepare_review_repair` | GitHub; Delivery-next turns comments into fix tasks | GitHub owns review state | P3, P7 |

### 3.6 Evidence and person-only checks

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Task check results | `derive_evidence_receipts`, [evidence](../../serve/delivery/src/owlbear_delivery/evidence.py) | Delivery-next stores outcome and inputs; git holds the commit | Canonical receipts and digests drop (T2, T5) | B1, B8 |
| Final proof of the head | [w-change-finalization](../../share/skills/w-change-finalization/SKILL.md), `finalizer`, [finalization_reports](../../serve/delivery/src/owlbear_delivery/finalization_reports.py) | Delivery-next final step; CI is the remote gate | A separate finalization authority adds no exit | J6, DR15 |
| Person-only checks | Scoped requests in [evidence](../../serve/delivery/src/owlbear_delivery/evidence.py), [h-process-observations](../../share/skills/h-process-observations/SKILL.md) | Delivery-next | No platform owner (route §3.1) | J7, H1–H3 |
| Completion of a merged Change | [acceptance](../../serve/delivery/src/owlbear_delivery/acceptance.py) | GitHub (merged PR); Delivery-next history line | State must not mirror GitHub facts | J9, M1 |

### 3.7 Integration with the moving target

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Observe the target head | `refs/owlbear/target-observation`, [workspace_target_sync](../../serve/delivery/src/owlbear_delivery/workspace_target_sync.py) | git fetch via reused [remote_git](../../serve/delivery/src/owlbear_delivery/remote_git.py) | Bounded, noninteractive | I1, X3 |
| Merge the target and resolve conflicts | [workspace_target_sync](../../serve/delivery/src/owlbear_delivery/workspace_target_sync.py), [w-target-conflict-resolution](../../share/skills/w-target-conflict-resolution/SKILL.md) | git inside an agent task with checks and review | The engine merge ran product hooks (RC3) | I1–I3, DR3 |
| Others' pushes to the Change branch | `adopt_external_head`, `promote_external_head`, `recover_out_of_band_head` | git merge as an I4 task | Adoption fences exist only for custody | I4 |

### 3.8 Publication and CI

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Push the Change branch | [change_publication](../../serve/delivery/src/owlbear_delivery/change_publication.py) | git via reused `remote_git`; replay only on confirmed absence | `classify_write_readback` fits DR5 | J6, X4 |
| Create the PR, draft and ready | [draft_pull_request](../../serve/delivery/src/owlbear_delivery/draft_pull_request.py), [publication_provider](../../serve/delivery/src/owlbear_delivery/publication_provider.py), [github.py](../../serve/delivery-github/src/owlbear_delivery_github/github.py) | GitHub via reused gh provider | gh PR proven (P9); Agents-window PR form untested | J6, P6 |
| Supersession, checkpoint obligations, baseline recovery | [application_publication](../../serve/delivery/src/owlbear_delivery/application_publication.py), [checkpoint_supervisor](../../serve/delivery/src/owlbear_delivery/checkpoint_supervisor.py) | drop | Re-entry by observation replaces background reconciliation | DR5 |
| Run checks | Project CI | CI | — | P1, P4 |
| Report checks on the head | `observe_change_publication_checks` | GitHub; Delivery-next observes and opens fix tasks | `gh pr checks` proven (P9) | P1, P2, P8, P10 |
| Block committed secrets | none | GitHub push protection | Never bypassed | B15 |
| Effective rules and required checks | Provider queries | GitHub; Delivery-next re-reads before publish and merge | Unproven: rulesets on a protected repository (403) | DR1, P5, P7 |

### 3.9 Merge

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Whether merging is possible | [merge_offer](../../serve/delivery/src/owlbear_delivery/merge_offer.py) | GitHub facts; Delivery-next block reasons (adapted reuse) | Fresh provider facts, no proof fields | J8 |
| Consent bound to one head | [merge_approval](../../serve/delivery/src/owlbear_delivery/merge_approval.py), [application_merge](../../serve/delivery/src/owlbear_delivery/application_merge.py) | Delivery-next records consent; GitHub enforces the `sha` guard | No platform owner | DR15, M2 |
| Execute the merge | [effect_launcher](../../serve/delivery-github/src/owlbear_delivery_github/effect_launcher.py), gh provider | GitHub | Unproven under branch protection (403) | J8 |
| Follow a merge queue | Refused by the provider today | GitHub queue; Delivery-next observes as pending | New; unproven | M3 |
| Merged or closed in GitHub | `observe_acceptance` | GitHub state, observed by Delivery-next | Facts stay in GitHub | M1, M4 |
| Agent merge (feedback, checks, conflicts) | — | Copilot platform, preview, optional | Unproven (untested) | I2, M2 |
| Cleanup after merge | Three cleanup tools, `application_lifecycle` | Delivery-next after preservation; git removes | — | J9, M5 |

### 3.10 Status and user interaction

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| One status per Change | [application_readiness](../../serve/delivery/src/owlbear_delivery/application_readiness.py), [work_items](../../serve/delivery/src/owlbear_delivery/work_items.py), [completed_history](../../serve/delivery/src/owlbear_delivery/completed_history.py) | Delivery-next derives one line | About 13 other fields disagree today (RC5) | DR8 |
| Status surface | Cockpit [target_work.py](../../serve/cockpit/src/owlbear_cockpit/routes/target_work.py), [target_models.py](../../serve/cockpit/src/owlbear_cockpit/target_models.py), [target_context.py](../../serve/cockpit/src/owlbear_cockpit/target_context.py) | Open (Q9): Cockpit, or Agents window plus PR | Unproven: SDK sessions in the Agents window | DR8 |
| Durable questions and answers | [h-decision-requests](../../share/skills/h-decision-requests/SKILL.md), `answer` | Delivery-next | Runtime-held questions disproved across processes (P2b); answer after resume proven (P2d) | DR7 |
| Failure classification | [diagnostics](../../serve/delivery/src/owlbear_delivery/diagnostics.py), 67 error codes | drop; five exits plus pending | One step outcome vocabulary | DR4 |
| Entry commands | `continue-change`, `inspect-change`, `design`, `ideate`, `finalize-change` prompts | Copilot platform skills; one "continue" | Skills as slash commands proven (P7); prompt files deprecated for Agent Host | J1 |
| Work survives a closed window | Local chat | Copilot transcript plus Delivery-next re-entry | Partial: SDK resume needs a "continue" message (P3); Agent Host untested | X1 |

### 3.11 Recovery

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Recover claims, worktrees, heads, baselines | [recovery](../../serve/delivery/src/owlbear_delivery/recovery.py), [application_recovery](../../serve/delivery/src/owlbear_delivery/application_recovery.py), [w-delivery-attention-resolution](../../share/skills/w-delivery-attention-resolution/SKILL.md), 16 tools | drop; exits plus re-entry by observation | Containment without an exit (RC1) | DR4, DR5 |
| Offline state repair | [state_repair](../../serve/delivery/src/owlbear_delivery/state_repair.py), `delivery_repair`, `delivery_diagnostics`, [w-delivery-repair](../../share/skills/w-delivery-repair/SKILL.md), `repairer` | drop; atomic writes keep the previous version, `stop` names "restore previous" | Rare row | DR11 |
| Backward moves | `administrative_move`, `preview_administrative_move` | Delivery-next `back` exit | — | D6, B9 |
| Preserve unfinished work | [workspace_preservation](../../serve/delivery/src/owlbear_delivery/workspace_preservation.py), `refs/owlbear/recovery`, quarantine refs | Delivery-next inventory; git stores it privately, never pushed | Recipe reused, code not | DR6, M5 |
| Resume after a killed driver | Settlement replay, [runtime_transaction](../../serve/delivery/src/owlbear_delivery/runtime_transaction.py) | Copilot transcript (P3) plus Delivery-next observation | Resume never re-runs a turn | X1, X4 |

### 3.12 State and storage

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Change state | [delivery_state](../../serve/delivery/src/owlbear_delivery/delivery_state.py) on branch `owlbear/delivery-state`, `.owlbear/delivery/` | Delivery-next: one file per Change outside the checkout | No remote snapshot, no product-branch content | DR11 |
| Custom refs | `refs/owlbear/attempts`, `quarantine`, `target-sync`, `packages` | drop | Custody artifacts | DR11 |
| Atomic writes and the lock | [storage_io](../../serve/delivery/src/owlbear_delivery/storage_io.py), [workspace_coordination](../../serve/delivery/src/owlbear_delivery/workspace_coordination.py) | Delivery-next (reuse `storage_io`) | Runtime gives a signal, not exclusion (P3c) | DR10 |
| Code facts | Mirrored heads and publication records | git and GitHub only | Read, never mirrored | DR5 |
| Models and composition | [application_models](../../serve/delivery/src/owlbear_delivery/application_models.py), [application_support](../../serve/delivery/src/owlbear_delivery/application_support.py), [delivery_application_loader](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py), [`__init__`](../../serve/delivery/src/owlbear_delivery/__init__.py), [identities](../../serve/delivery/src/owlbear_delivery/identities.py), [yaml_rt](../../serve/delivery/src/owlbear_delivery/yaml_rt.py) | drop; a few small models | Composition of the old application | DR12 |

### 3.13 Upgrade and migration

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Pinned releases, live-compatibility gate | `delivery_controller`, `delivery_lc`, [release_integrity](../../serve/delivery/src/owlbear_delivery/release_integrity.py), `/upgrade-delivery` | drop; `uv` lock and git tags. OwlBear's own use runs a tagged install (M3 decides) | Protected live custody state | S6 |
| State formats and migration | [state_formats](../../serve/delivery/src/owlbear_delivery/state_formats.py), [state_migration](../../serve/delivery/src/owlbear_delivery/state_migration.py), `delivery_migration` | Delivery-next: version field; migrate forward or `stop` | Small state needs no fenced copy-first journal | S6 |
| Copilot or VS Code changes | none | Copilot platform; Delivery-next readiness reports versions | — | X7 |

### 3.14 Multiple Changes

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Portfolio acquisition and guidance | [portfolio_application](../../serve/delivery/src/owlbear_delivery/portfolio_application.py), [portfolio_operating](../../serve/delivery/src/owlbear_delivery/portfolio_operating.py), `list_changes` | drop; Delivery-next lists Changes | One loop per Change | DR8 |
| One writer, publication leases | [workspace_coordination](../../serve/delivery/src/owlbear_delivery/workspace_coordination.py), [change_workspace](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | Delivery-next lock | P3c | DR10, X5 |
| Overlap and conflicts between Changes | none | Delivery-next plan check; git in J5 | — | D7, I2 |
| Spend across Changes | none | Delivery-next budgets; Copilot quota | Unproven: quota exhaustion | S9, DR13 |

### 3.15 Setup and project profile

| Responsibility | Today | Owner | Reason | Serves |
| --- | --- | --- | --- | --- |
| Wiring and server registration | [setup/init.py](../../setup/init.py), `delivery_config` | Delivery-next setup, user-local | Tracked files only with consent | J0, DR14 |
| Project profile | none; assumes `github.com`, `main`, `uv` | Delivery-next detects and the user confirms; GitHub supplies rules | Consumer fit | DR1, S3 |
| Readiness | `delivery_health` (state only) | Delivery-next; GitHub CLI and Copilot report sign-in | One concrete fix per failure | DR2, S1, S4 |
| Load agents and skills | `chat.*FilesLocations` (Local only) | Copilot from `.github/agents`, `.github/skills` | Agents and skills load in CLI (P6, P7); skill use in SDK sessions untested | E1 |
| MCP in worktree sessions | none | Delivery-next grants folder trust per worktree path | P8 | J0 |
| Billing identity and models | none | Copilot; Delivery-next discloses spend | Unproven on the employer seat | S9, DR13 |

### 3.16 Capability status after R8

| Capability | Status | Consequence for ownership |
| --- | --- | --- |
| Typed agent results, read-only handler | Proven (P1, P5); API experimental | Workers return results; the loop validates |
| Unattended permissions; worktree → PR → CI | Proven (P5, P9) | Copilot enforces Delivery-next's lists; project work stays in tasks |
| Resume after a killed driver | Proven (P3) | Delivery-next re-enters by observation |
| Runtime-held durable questions | Disproved (P2b) | Questions live in Delivery-next |
| Session exclusion | Disproved (P3c) | Delivery-next lock |
| Termination confirmation | Partial (P4, P4b) | Record PIDs; `stop` when unverifiable |
| Dynamic workflows as the loop | Rejected (P10) | Not a core dependency |
| Explicit models, SDK skill use, pre-tool hooks, protected merge and rulesets, merge queue, agent merge, Agents-window PR form, SDK sessions in the Agents window, quota exhaustion, employer seat | Unproven | Nothing on the critical path depends on them; re-probe under the employer seat and a protected sandbox before M3 commits (R8 §4) |

## 4. Recommendation, Confidence, and Limits

**Conclusions (`autonomous`).** git, GitHub and CI own every code fact (commits, pushes, PRs,
checks, reviews, rules, merges); Delivery-next reads them and never mirrors them. The Copilot
platform owns execution: sessions, agents, permission enforcement, transcripts. Delivery-next owns
only what nobody else does. Custody, receipts, fences, recovery routes, pinned releases and state
repair are dropped.

### What Delivery-next owns

**State** (one versioned file per Change and one per project, outside the checkout, atomic writes):

| Record | Fields |
| --- | --- |
| Project profile | Format version; host and repositories; target branch; per-package install and check commands with directory; CI and required checks; merge method and queue; hooks, signing, LFS; support statement; confirmed at |
| Change | Format version; profile reference and version; intent in the user's words; brief and approved version; acceptance criteria with versions; person-only checks with steps, recorded inputs and answer; decisions with origin; questions with options, answer and effect observed; plan (ordered tasks with scope and checks); current step (stage, task); exit or pending condition (kind, reason, actor, next observation); budgets per cause; branch and target names; Copilot session ids and recorded PIDs; merge consent (head SHA, time); lock (holder, host, PID, since) |
| Not stored | Commits, heads, PR state, checks, reviews, merge state: read from git and GitHub each time |

**Operations:**

| Kind | Operations |
| --- | --- |
| User | Set up and confirm profile; start a Change; approve the brief; answer; report a person-only check; approve merge of one head; pause, resume, abandon; show status |
| Loop steps | Observe; shape; plan; build task; review; integrate; publish; follow CI and reviews; person-only check; merge; preserve and clean up — each ends in done, retry, ask, back or stop, or is pending |
| Agent-facing | Workers in SDK sessions return typed results (P1) and need no result tool; the interactive Designer needs one tool to save a brief draft. Unproven: whether a schema failure returns to the same agent in-session (T3) |

**Modules that become unnecessary** (47 of 55 engine modules): `__init__`, `acceptance`,
`application_*` (8), `change_publication`, `change_workspace`, `checkpoint_supervisor`,
`completed_history`, `delivery_admission`, `delivery_application_loader`,
`delivery_contract_discovery`, `delivery_runtime`, `delivery_state`, `design_package`,
`diagnostics`, `draft_pull_request`, `evidence`, `finalization_reports`, `identities`,
`portfolio_application`, `portfolio_operating`, `recovery`, `release_integrity`, `runtime_*` (6),
`state_formats`, `state_migration`, `state_repair`, `target_contract`, `work_items`,
`workspace_*` (6), `yaml_rt`. Also `serve/delivery-mcp`, the Cockpit Delivery routes, the
`delivery_*` controller tools, the loop skills, the `orchestrator`, `finalizer` and `repairer`
agents and the recovery prompts.

**Reused** (copied, as in route comparison §3.4): `remote_git`, `git_executable`, `storage_io`,
`publication_provider`, the gh provider with `effect_launcher` and `memory`, `merge_offer` and
`merge_approval` (adapted), `worker_stall` (adapted), `acceptance_criteria`. Kept as ideas, not code:
the `work_items` situation vocabulary, the preservation inventory recipe and the format-version gate
of `state_formats`. Worker craft from `designer`, `planner`, `builder`, the challengers,
`build-reviewer` and `h-ac-quality` is rewritten for `.github/` (E1).

**Differences from the route comparison.** None in the code list. M3 should check whether a
`sha`-guarded merge plus readback makes the frozen-body `effect_launcher` unnecessary.

**Confidence.** High for the module inventory and git, GitHub and CI ownership; medium-high for
Copilot execution and permissions (one setup); medium for merge and status rows (unproven gates).

**Limits.** Classification follows docstrings and skill purposes; bodies were read only where cited.
R8 used a free identity, Auto models and an unprotected repository. Nothing live was touched.
