# Agent Ecosystem Wiring

This document is the derived operational map of OwlBear's active shared agent ecosystem. It helps
customization authors see cross-file relationships without reconstructing the graph from every
frontmatter block and workflow body.

The map is descriptive, not authoritative. Resolve discrepancies in this order:

Executable frontmatter, bodies, loading instructions, hooks, registries, and runtime schemas take
precedence. See [README.md](README.md) for composition, ownership, change procedure, and validation.

## Connection Vocabulary

| Label | Meaning |
|-------|---------|
| `auto` | VS Code injects the control from workspace configuration or matching instruction scope |
| `prompt` | A prompt selects an agent or directs the current agent to a skill |
| `required` | The agent lists the skill in `<required_reading>` and loads it at session start |
| `conditional` | A workflow, prompt, or universal rule loads the skill only when its named condition occurs |
| `delegate` | The caller exposes and invokes a subagent through `agents:` and its `<agents>` table |
| `hook` | VS Code runs a command at `SessionStart`, `PreToolUse`, or `PostToolUse` |

Discovery metadata is not a loaded skill body and is omitted below.

## Universal And Contextual Instructions

| Control | Scope and timing | Job |
|---------|------------------|-----|
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
|-------|-------|------------------|-----------|-------|
| designer | GPT-5.6 Sol | `w-design-session` | designer-challenger, Explore | None; authority writes are bounded by the role and narrow native tool surface |
| designer-challenger | Claude Sonnet 5 | `r-challenger-protocol`, `h-codebase-orientation`, `h-module-design` | None | `PreToolUse`: deny writes except scratch |
| planner | GPT-5.6 Sol | `w-frontier-planning` | planner-challenger, Explore | None; no lifecycle or tracked-write tools |
| planner-challenger | Claude Sonnet 5 | `r-challenger-protocol`, `h-codebase-orientation`, `h-module-design`, `h-ac-quality` | None | `PreToolUse`: deny writes except scratch |
| orchestrator | GPT-5.6 Terra | `w-orchestration` | planner, builder, acceptor, verifier, collector, memory-curator, Explore | None; legacy `pick_tasks` plus non-default native pick/start, purpose-specific finish/reject, release, and recovery tools |
| shaper | GPT-5.6 Sol | `r-pipeline-protocol`, `r-challenger-protocol`, `r-workspace-governance` | shaper-challenger, Explore | `PreToolUse`: deny non-document writes |
| builder | GPT-5.6 Terra | `w-packet-building`, `r-pipeline-protocol`, `r-challenger-protocol`, `r-workspace-governance`, `h-codebase-orientation` | builder-challenger, build-reviewer | `SessionStart`: task context; `PostToolUse`: lint changed files |
| build-reviewer | Claude Sonnet 5 | `r-challenger-protocol`, `h-codebase-orientation` | None | `PreToolUse`: deny writes except scratch |
| acceptor | GPT-5.6 Terra | `w-node-acceptance` | None | `PreToolUse`: deny writes except scratch; before/after tracked-state check |
| verifier | GPT-5.6 Terra | `r-pipeline-protocol`, `r-challenger-protocol`, `r-workspace-governance`, `h-codebase-orientation` | verifier-challenger | `SessionStart`: task context; `PostToolUse`: lint changed files |
| collector | GPT-5.6 Terra | `r-pipeline-protocol`, `r-workspace-governance`, `h-mcp-kanban` | Explore | `PreToolUse`: deny writes except scratch |
| shaper-challenger | Claude Sonnet 5 | `h-ac-quality`, `h-module-design`, `r-challenger-protocol` | None | `PreToolUse`: deny writes except scratch |
| builder-challenger | MAI-Code-1-Flash | `r-challenger-protocol` | None | `PostToolUse`: lint changed files |
| verifier-challenger | GPT-5.6 Luna | `r-challenger-protocol` | None | `PreToolUse`: deny writes except scratch |
| test-curator | GPT-5.6 Terra | `w-test-curation` | None | `PreToolUse`: deny source writes |
| memory-curator | GPT-5.6 Terra | `w-mem-curation` | None | None |
| knowledge-ingestor | GPT-5.6 Luna | `h-knowledge-ops` | None | None |
| knowledge-enricher | GPT-5.6 Luna | `w-knowledge-enrichment`, `h-knowledge-ops` | None | None |

Tool allowlists remain in agent frontmatter; they are not duplicated here.

## Prompt Entry Map

| Prompt | Entry route | Initial loading behavior |
|--------|-------------|--------------------------|
| `ideate` | `prompt` -> designer in discovery mode | Agent required-reading loads `w-design-session`; selects or creates one native session |
| `design` | `prompt` -> designer in direct design mode | Agent required-reading loads `w-design-session`; rehydrates the same native session |
| `shape` | `prompt` -> shaper | Shaper selects `w-spec-shaping` or `w-task-repair` after classifying the input |
| `orchestrate` | `prompt` -> orchestrator | Agent required-reading loads `w-orchestration` |
| `test-curation` | `prompt` -> test-curator | Agent required-reading loads `w-test-curation` |
| `kb-ingest` | `prompt` -> knowledge-ingestor | Agent required-reading loads `h-knowledge-ops` |
| `kb-enrich` | `prompt` -> knowledge-enricher | Agent required-reading loads `w-knowledge-enrichment` and `h-knowledge-ops` |
| `architecture-review` | Current agent directed by prompt | Loads module-design, orientation, visual-output, and idea-refinement skills |
| `arch-audit` | Current agent directed by prompt | Loads `h-module-design` |
| `frontend-audit` | Current agent directed by prompt | Loads frontend design and conventions; loads frontend proof guidance only for that toolchain |
| `memory-audit` | Current agent directed by prompt | Loads memory structure and MCP memory before review; pending inspection uses preflight metadata and hands curation to `memory-curator` |
| `legacy-audit` | Current agent directed by prompt | Uses its prompt-defined read-only audit procedure |

Project-local prompts are outside the portable inventory. They may select built-in agents or load
project-local skills in addition to the shared surface.

## Conditional Skill Loading

The named caller owns each on-demand condition and timing.

| Caller or trigger | Conditional skill | Load condition |
|-------------------|-------------------|----------------|
| shaper prompt | `w-spec-shaping` | Input is an OpenSpec implementation plan |
| shaper prompt | `w-task-repair` | Input is existing work rejected to shape |
| shaping workflows | `w-task-decomposition` | Approved scope must become atomic tasks and dependencies |
| shaping workflows | `w-research` | Local evidence cannot resolve a material claim |
| shaping workflows | `h-codebase-orientation`, `h-module-design`, `h-ac-quality` | Source ownership, architecture, or AC drafting requires the specialist boundary |
| pipeline protocol | `h-mcp-kanban` | A role needs Kanban tool syntax or lifecycle semantics and does not already require it |
| pipeline protocol | `h-decision-requests` | A role creates or consumes a Decision or Action Request |
| pipeline protocol | `h-mcp-memory` | `recall_memory` returned entries that must be assessed |
| universal memory governance | `h-memory-structure`, `h-mcp-memory` | A save-capable role has a qualifying reusable insight |
| Python instruction | `h-python-conventions` | The active file matches the Python instruction scope |
| frontend instruction | `h-frontend-conventions` | The active file matches the frontend instruction scope |
| proof selection | `h-pytest-and-linting` or `h-vitest-and-linting` | The changed domain uses that test and lint toolchain |

## Required Skill Consumers

This inverse map includes only direct `<required_reading>` consumers, not conditional loading.

| Skill | Required by |
|-------|-------------|
| `w-design-session` | designer |
| `w-frontier-planning` | planner |
| `w-packet-building` | builder |
| `w-node-acceptance` | acceptor |
| `r-challenger-protocol` | designer-challenger, planner-challenger, shaper, builder, build-reviewer, verifier, shaper-challenger, builder-challenger, verifier-challenger |
| `h-codebase-orientation` | designer-challenger, planner-challenger, builder, build-reviewer, verifier |
| `h-module-design` | designer-challenger, planner-challenger, shaper-challenger |
| `r-pipeline-protocol` | shaper, builder, verifier, collector |
| `r-workspace-governance` | shaper, builder, verifier, collector |
| `h-mcp-kanban` | collector |
| `h-ac-quality` | planner-challenger, shaper-challenger |
| `w-orchestration` | orchestrator |
| `w-test-curation` | test-curator |
| `w-mem-curation` | memory-curator |
| `h-knowledge-ops` | knowledge-ingestor, knowledge-enricher |
| `w-knowledge-enrichment` | knowledge-enricher |

## Delegation And Nesting

| Delegate | Caller | Runtime consequence if unavailable |
|----------|--------|------------------------------------|
| designer-challenger | designer | Native admission lacks required repository-grounded entity challenge evidence |
| planner | orchestrator | Engine-selected native plan jobs cannot be refined or completed |
| acceptor | orchestrator | Engine-selected native accept jobs cannot produce independent success, rejection, or blocked dispositions |
| planner-challenger | planner | A packet DAG cannot satisfy the independent plan review gate |
| builder | orchestrator | Build tasks and engine-selected native build jobs cannot be completed |
| build-reviewer | builder | A native packet commit cannot satisfy mandatory independent inline review |
| verifier | orchestrator | Verify tasks cannot be dispatched |
| collector | orchestrator | Collect tasks cannot be dispatched |
| memory-curator | orchestrator | Periodic memory housekeeping is skipped |
| shaper-challenger | shaper | Shape approval loses the required adversarial cross-check |
| builder-challenger | builder | Build completion loses its required proof and scope cross-check |
| verifier-challenger | verifier | Verification completion loses its required final cross-check |
| Explore | designer, planner, orchestrator, shaper, collector | Broad read-only orientation must be performed by the caller or omitted |

The agent validator enforces ND3 metadata and frontmatter-to-`<agents>` alignment; see
`h-agent-structure` for the nesting rules.

## Hard-Control Map

| Control | Attached roles | Enforcement job |
|---------|----------------|-----------------|
| Agent `tools:` allowlist | Every agent | Limits runtime capabilities exposed to the role |
| `deny-non-doc-writes.py` | shaper | Allows documentation and diagram writes, rejects code writes |
| `deny-writes.py` | acceptor, collector, designer-challenger, planner-challenger, build-reviewer, and read-only pipeline challengers | Rejects durable edit-tool writes outside scratch |
| `deny-src-writes.py` | test-curator | Restricts writes to tests and scratch |
| `session-context.py` | builder, verifier | Adds task-aware context at session start |
| `lint-changed.py` | builder, verifier, builder-challenger | Runs changed-file checks after tool use |
| MCP schemas and stores | Tool-capable roles | Validate arguments, transitions, and persisted state |
| `validate_agents.py` | Repository validation | Checks frontmatter, required sections, tools, delegation, and nesting-depth metadata |
| `validate_skills.py` | Repository validation | Checks skill metadata and structure |
| `test_agent_ecosystem_validation.py` | Repository regression | Exercises validators and resolves declared OwlBear MCP tools against live registries |
| Write-guard regression tests | Repository regression | Exercise path restrictions and hook behavior |

Runtime and repository controls remain authoritative over prose.

## Maintenance Protocol

Update affected rows in the same change as their executable owners, then run:

```shell
uv run python .owlbear/scripts/validate_agents.py
uv run python .owlbear/scripts/validate_skills.py
uv run pytest -q tests/test_agent_ecosystem_validation.py
```

If a validator disagrees, repair its executable owner before this map.
