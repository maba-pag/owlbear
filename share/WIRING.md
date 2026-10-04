# Agent Ecosystem Wiring

This document is the derived operational map of OwlBear's active shared agent ecosystem. It helps
customization authors see cross-file relationships without reconstructing the graph from every
frontmatter block and workflow body.

The map is descriptive, not authoritative. Resolve discrepancies in this order:

Executable frontmatter, bodies, loading instructions, hooks, registries, and runtime schemas take
precedence. See [README.md](README.md) for composition, ownership, change procedure, and validation.

## Connection Vocabulary

| Label | Meaning |
| --- | --- |
| `auto` | VS Code injects the control from workspace configuration or matching instruction scope |
| `prompt` | A prompt selects an agent or directs the current agent to a skill |
| `required` | The agent lists the skill in `<required_reading>` and loads it at session start |
| `conditional` | A workflow, prompt, or universal rule loads the skill only when its named condition occurs |
| `delegate` | The caller exposes and invokes a subagent through `agents:` and its `<agents>` table |
| `hook` | VS Code runs a command at `SessionStart`, `PreToolUse`, or `PostToolUse` |

Discovery metadata is not a loaded skill body and is omitted below.

## Universal And Contextual Instructions

| Control | Scope and timing | Job |
| --- | --- | --- |
| `.github/copilot-instructions.md` | `auto`, every workspace turn | Current-project identity, topology, stack, commands, and resources |
| `owlbear-system.instructions.md` | `auto`, `applyTo: "**"` | Universal OwlBear heuristics, memory governance, and tool bootstrap |
| `agent-ecosystem.instructions.md` | `auto` for shared and project-local customization roots | Route customization authors to `README.md` and `h-agent-structure` |
| `python.instructions.md` | `auto` for `**/*.py` | Route Python work to `h-python-conventions` |
| `frontend.instructions.md` | `auto` for supported frontend source and style extensions | Route frontend work to `h-frontend-conventions` |
| `doc-standards.instructions.md` | `auto` for canonical project documentation | Route documentation work to `r-doc-standards` |
| `research-docs.instructions.md` | `auto` for `.owlbear/research/*.md` | Route research artifacts to `w-research` |

Project-local `.owlbear/instructions/` files compose with these shared instructions when their
`applyTo` globs match. They are intentionally not copied into this portable shared map.

## Agent Runtime Map

This table snapshots agent declarations and includes runtime-relevant built-in delegates.

| Agent | Model | Required reading | Delegates | Hooks |
| --- | --- | --- | --- | --- |
| designer | Claude Opus 5.5 (copilot) | `w-design-session` | conceptual-design-reviewer, designer-challenger, Explore | `PreToolUse`: allow only scratch/research edits and read-only terminal commands; target publication uses the admission tool surface |
| conceptual-design-reviewer | GPT-6.1 Sol (copilot) | `r-challenger-protocol`, `h-module-design`, `h-frontend-design` | None | `PreToolUse`: deny writes except scratch |
| designer-challenger | GPT-6.1 Sol (copilot) | `r-challenger-protocol`, `h-codebase-orientation`, `h-module-design` | None | `PreToolUse`: deny writes except scratch |
| planner | Claude Opus 5.5 (copilot) | `w-frontier-planning` | planner-challenger, Explore | `PreToolUse`: deny writes except scratch; terminal read-only; publishes advisory-reviewed task chains and returns worker-owned transitions |
| planner-challenger | GPT-6.1 Sol (copilot) | `r-challenger-protocol`, `h-codebase-orientation`, `h-module-design`, `h-ac-quality` | None | `PreToolUse`: deny writes except scratch |
| orchestrator | GPT-6 Luna | `w-orchestration` | see below | Session-start claim check; user-confirmed stopped claims use one exact release; window loss is engine-settled after the write/process guard. |
| repairer | GPT-6 Luna | `h-decision-requests` | None | One exact Change view and one bounded answer/repair interaction; high-level Delivery tools only, no repository or worker authority |
| builder | GPT-6 Luna | `w-packet-building`, `r-workspace-governance`, `h-codebase-orientation` | build-reviewer | Assigned Change worktree only; successful Build uses the claim-bound submit-result facade; normally returned retry/block/Planning-or-Design-return transitions are settled by Orchestrator, while other supported transitions are forwarded; `SessionStart`: repository context; `PostToolUse`: lint changed files |
| build-reviewer | GPT-6.1 Sol (copilot) | `r-challenger-protocol`, `h-codebase-orientation` | None | Exact-commit task-result or finalization review with read-only Git; `PreToolUse`: deny writes except scratch; terminal read-only |
| finalizer | GPT-6 Luna | `w-change-finalization`, `h-codebase-orientation` | build-reviewer | User-invoked exact Change proof and finalization; `PreToolUse`: deny writes and terminal mutation |
| test-curator | GPT-6.1 Sol (copilot) | `w-test-curation`, `r-workspace-governance` | None | `PreToolUse`: deny source writes through recognized file tools; terminal execution is trusted for this manually invoked role |
| memory-curator | GPT-6 Luna | `w-mem-curation` | None | None |
| knowledge-ingestor | GPT-6 Luna | `h-knowledge-ops` | None | None |
| knowledge-enricher | GPT-6 Luna | `w-knowledge-enrichment`, `h-knowledge-ops` | None | None |
| Explore (built-in) | default | None declared by OwlBear | None | VS Code built-in delegate; no OwlBear-specific model override or hook |

Tool allowlists remain in agent frontmatter; they are not duplicated here.

Orchestrator acquires and dispatches work, then forwards ordinary transitions and routes typed
attention and admitted Change repair proposals. Before dispatching, it inspects running
Planner/Builder/Finalizer claims in its entry scope (`/continue-change`: only that Change through
`get_change`; `/orchestrate`: `list_changes`, then `get_change`) and asks once with `vscode/askQuestions`
whether each exact prior run was stopped. Only a confirmed stop uses one exact
`release_stuck_worker` call. A `worker-stall-wait` needs no question and yields with its retry time
or bounded process details. Delivery records each claim's issuing VS Code window PID and process
start time, then settles a previous-session loss on acquisition only after that window is gone, no
worktree write occurred for 30 seconds, and the worktree/Git-admin process guard passes. An
MCP-server restart while the window is alive does not qualify. Orchestrator runs periodic memory
curation and has no repository write tools. Returned Planner/Builder no-results use
`ended-without-result` only after dispatch return and owned mutators settle. `worker-host-lost` and
`worker-released-stuck` are engine-only and never go through Orchestrator settlement. A lost or
released Finalizer without a report receives `finalizer-ended-without-report` with unknown checks,
not proof.

## Prompt Entry Map

| Prompt | Entry route | Initial loading behavior |
| --- | --- | --- |
| `ideate` | `prompt` -> designer in discovery mode | Agent required-reading loads `w-design-session`; selects or creates one target Design session |
| `design` | `prompt` -> designer in direct design mode | Agent required-reading loads `w-design-session`; rehydrates the same target Design session |
| `orchestrate` | `prompt` -> orchestrator | Agent required-reading loads `w-orchestration`; session-start stale-claim check precedes dispatch |
| `continue-change` | `prompt` -> orchestrator | One selected Change; acquires and dispatches at most one Change action at a time |
| `challenge-plan_sol` | Current agent directed by `.github/prompts` | Dispatches a fresh unnamed read-only subagent with `GPT-6.1 Sol (copilot)`; caller reconciles evidence and owns the recommendation |
| `challenge-implementation_sol` | Current agent directed by `.github/prompts` | Dispatches a fresh unnamed read-only subagent with `GPT-6.1 Sol (copilot)`; caller reconciles findings and owns the verdict |
| `finalize-change` | `prompt` -> finalizer | Agent required-reading loads `w-change-finalization`; engine proof and exact reviewed finalization |
| `inspect-change` | built-in `ask` mode | Read-only Change diagnosis through `get_change` and `delivery_health` only; no mutation or host repair |
| `release-stuck-worker` | `prompt` -> orchestrator | Claim from `get_change`; skip `worker-stall-wait`; confirm stop if needed; release once under the write/process guard |
| `upgrade-delivery` | Current agent directed by prompt | Prompt-defined N02-D procedure: install, online read-only preflight, user stop, offline preflight, backup, `delivery-migrate`, confirmed switch, user restart and verification through `delivery-controller` |
| `address-pr-feedback` | Current agent directed by prompt | Loads `w-address-pr-feedback`; `start` evaluates and repairs external review threads, while `resume` publishes the fresh finalized head before replying and resolving threads |
| `resolve-target-conflict` | Current agent directed by prompt | Loads `w-target-conflict-resolution`; resolves exact target merges in the managed Change worktree and hands off to finalization |
| `resolve-delivery-attention` | Temporary recovery/exception prompt | Loads `w-delivery-attention-resolution`; binds one exact Change or Integration attention before interactive diagnosis; retire only after Cockpit and Delivery provide tested guided routes for all prompt-only recovery capabilities |
| `test-curation` | `prompt` -> test-curator | Agent required-reading loads `w-test-curation` |
| `kb-ingest` | `prompt` -> knowledge-ingestor | Agent required-reading loads `h-knowledge-ops` |
| `kb-enrich` | `prompt` -> knowledge-enricher | Agent required-reading loads `w-knowledge-enrichment` and `h-knowledge-ops` |
| `architecture-review` | Current agent directed by prompt | Loads module-design, orientation, visual-output, and idea-refinement skills |
| `arch-audit` | Current agent directed by prompt | Loads `h-module-design` |
| `frontend-audit` | Current agent directed by prompt | Loads frontend design and conventions; loads frontend proof guidance only for that toolchain |
| `memory-audit` | Current agent directed by prompt | Loads memory structure and MCP memory before review; pending inspection uses preflight metadata and hands curation to `memory-curator` |
| `legacy-audit` | Current agent directed by prompt | Loads `h-codebase-orientation`; uses its prompt-defined read-only audit procedure |

Project-local prompts are outside the portable inventory. They may select built-in agents or load
project-local skills in addition to the shared surface.

## Conditional Skill Loading

The named caller owns each on-demand condition and timing.

| Caller or trigger | Conditional skill | Load condition |
| --- | --- | --- |
| Planner or Builder context | `h-decision-requests` | Fresh context contains a request, or routing identifies an authority-compatible stakeholder choice or external action |
| native design/planning | `w-research` | Local evidence cannot resolve a material claim and the owning workflow permits research |
| native design/planning | `h-codebase-orientation`, `h-module-design`, `h-ac-quality` | Source ownership, architecture, packet boundaries, or acceptance drafting requires the specialist boundary |
| universal memory governance | `h-memory-structure`, `h-mcp-memory` | A save-capable role has a qualifying reusable insight |
| Python instruction | `h-python-conventions` | The active file matches the Python instruction scope |
| frontend instruction | `h-frontend-conventions` | The active file matches the frontend instruction scope |
| frontend conventions | package-provided `pds-knowledge-{framework}` | The project declares a PDS wrapper and its generated companion link resolves |
| proof selection | `h-pytest-and-linting` or `h-vitest-and-linting` | The changed domain uses that test and lint toolchain |
| Builder or Finalizer post-result context | `h-process-observations` | A reviewed result exposes retry, return, block, review-finding, material divergence, or explicit process-learning need |
| `resolve-delivery-attention` prompt | `w-delivery-attention-resolution` | One exact operator-required Delivery attention or blocked outcome needs interactive diagnosis or a user-selected remedy |
| `resolve-target-conflict` prompt | `w-target-conflict-resolution` | One exact target merge needs managed-worktree resolution and Delivery-owned merge validation |

## Required Skill Consumers

This inverse map includes only direct `<required_reading>` consumers, not conditional loading.

| Skill | Required by |
| --- | --- |
| `w-design-session` | designer |
| `w-frontier-planning` | planner |
| `w-packet-building` | builder |
| `r-challenger-protocol` | conceptual-design-reviewer, designer-challenger, planner-challenger, build-reviewer |
| `h-codebase-orientation` | designer-challenger, planner-challenger, builder, build-reviewer, finalizer |
| `h-module-design` | designer-challenger, planner-challenger |
| `h-frontend-design` | conceptual-design-reviewer |
| `h-ac-quality` | planner-challenger |
| `w-orchestration` | orchestrator |
| `h-decision-requests` | repairer |
| `w-change-finalization` | finalizer |
| `w-test-curation` | test-curator |
| `r-workspace-governance` | builder, test-curator |
| `w-mem-curation` | memory-curator |
| `h-knowledge-ops` | knowledge-ingestor, knowledge-enricher |
| `w-knowledge-enrichment` | knowledge-enricher |

## Delegation And Nesting

| Delegate | Caller | Runtime consequence if unavailable |
| --- | --- | --- |
| conceptual-design-reviewer | designer | A consequential product, workflow, or interaction concept proceeds without independent conceptual challenge |
| designer-challenger | designer | Native admission lacks required repository-grounded entity challenge evidence |
| planner | orchestrator | An acquired Planning launch cannot produce a published task chain and worker-owned transition |
| planner-challenger | planner | A proposed Delivery task chain cannot receive independent advisory evidence |
| builder | orchestrator | Settled no-result preserves same-task work; unreturned/live work stays held |
| finalizer | orchestrator | An issued finalization launch is dispatched intact; normal failures settle only with its actual stored report and issued identities, while success is recorded without another API call; if the capability is unavailable, the orchestrator reports the native `/finalize-change <change_id>` entry instead |
| repairer | orchestrator | A Change-specific engine-authored repair proposal cannot receive its bounded user interaction |
| build-reviewer | builder | An exact-commit task result cannot receive advisory pass or finding evidence |
| build-reviewer | finalizer | An exact finalization proof cannot receive advisory pass or finding evidence |
| memory-curator | orchestrator | Scheduled memory housekeeping is unavailable; the failure is reported and does not stop independent Delivery acquisition |
| Explore | designer, planner, orchestrator | Broad read-only orientation must be performed by the caller or omitted |

`recover_claim` refusals report `ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED` and retain custody. The
user-stopped release route is separate.

The agent validator enforces ND3 metadata and frontmatter-to-`<agents>` alignment; see
`h-agent-structure` for the nesting rules.

## Hard-Control Map

| Control | Attached roles | Enforcement job |
| --- | --- | --- |
| Agent `tools:` allowlist | Every agent | Limits runtime capabilities exposed to the role |
| `deny-writes.py` | designer, planner, conceptual-design-reviewer, designer-challenger, planner-challenger, build-reviewer, finalizer | Rejects writes outside the configured scratch/research boundary; read-only terminal mode is enabled for reviewers, planner, and finalizer inspection |
| `deny-src-writes.py` | test-curator | Restricts recognized file-tool writes to tests and scratch; manually invoked terminal execution is trusted |
| `session-context.py` | builder | Adds repository context at session start |
| `lint-changed.py` | builder | Runs changed-file checks after tool use |
| MCP schemas and stores | Tool-capable roles | Validate arguments, transitions, and persisted state |
| `validate_agents.py` | Repository validation | Checks frontmatter, required sections, tools, delegation, and nesting-depth metadata |
| `validate_skills.py` | Repository validation | Checks skill metadata and structure |
| `validate_prompts.py` | Repository validation | Checks prompt metadata, routing targets, and explicit skill references |
| `test_agent_ecosystem_validation.py` | Repository regression | Exercises validators and resolves declared OwlBear MCP tools against live registries |
| Write-guard regression tests | Repository regression | Exercise path restrictions and hook behavior |

Runtime and repository controls remain authoritative over prose.

## Maintenance Protocol

Update affected rows in the same change as their executable owners, then run:

```shell
uv run python .owlbear/scripts/validate_agents.py
uv run python .owlbear/scripts/validate_skills.py
uv run python .owlbear/scripts/validate_prompts.py
uv run pytest -q tests/test_agent_ecosystem_validation.py
```

These validator scripts and the regression test are development-checkout maintenance commands;
they are not part of the generated consumer `main` surface. Consumer projects should follow the
[setup guide](../setup/setup-guide.md) for installation and verification.

If a validator disagrees, repair its executable owner before this map.
