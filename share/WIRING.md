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
| designer | GPT-5.6 Sol | `w-design-session` | conceptual-design-reviewer, designer-challenger, Explore | None; draft writes are role-bounded and target publication uses the admission tool surface |
| conceptual-design-reviewer | Claude Opus 5 | `r-challenger-protocol`, `h-module-design`, `h-frontend-design` | None | `PreToolUse`: deny writes except scratch |
| designer-challenger | Claude Opus 5 | `r-challenger-protocol`, `h-codebase-orientation`, `h-module-design` | None | `PreToolUse`: deny writes except scratch |
| planner | GPT-5.6 Sol | `w-frontier-planning` | planner-challenger, Explore | `PreToolUse`: deny writes except scratch and terminal mutation; publishes advisory-reviewed task chains and returns worker-owned transitions |
| planner-challenger | Claude Opus 5 | `r-challenger-protocol`, `h-codebase-orientation`, `h-module-design`, `h-ac-quality` | None | `PreToolUse`: deny writes except scratch |
| orchestrator | GPT-5.6 Terra | `w-orchestration` | planner, builder, claim-arbiter, memory-curator, Explore | Target portfolio and plan/build/assembly mutation tools; no repository write tools |
| builder | GPT-5.6 Terra | `w-packet-building`, `r-workspace-governance`, `h-codebase-orientation` | build-reviewer | Assigned change worktree only; `SessionStart`: repository context; `PostToolUse`: lint changed files |
| build-reviewer | Claude Sonnet 5 | `r-challenger-protocol`, `h-codebase-orientation` | None | `PreToolUse`: deny writes except scratch |
| claim-arbiter | Claude Opus 5 | `r-challenger-protocol` | None | `PreToolUse`: deny writes except scratch; final isolated disagreement decision |
| test-curator | GPT-5.6 Terra | `w-test-curation` | None | `PreToolUse`: deny source writes |
| memory-curator | GPT-5.6 Terra | `w-mem-curation` | None | None |
| knowledge-ingestor | GPT-5.6 Luna | `h-knowledge-ops` | None | None |
| knowledge-enricher | GPT-5.6 Luna | `w-knowledge-enrichment`, `h-knowledge-ops` | None | None |

Tool allowlists remain in agent frontmatter; they are not duplicated here.

## Prompt Entry Map

| Prompt | Entry route | Initial loading behavior |
|--------|-------------|--------------------------|
| `ideate` | `prompt` -> designer in discovery mode | Agent required-reading loads `w-design-session`; selects or creates one target Design session |
| `design` | `prompt` -> designer in direct design mode | Agent required-reading loads `w-design-session`; rehydrates the same target Design session |
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
| Planner or Builder context | `h-decision-requests` | One bounded user choice or action requires an embedded `DeliveryRequest` in `BlockDelivery` |
| native design/planning | `w-research` | Local evidence cannot resolve a material claim and the owning workflow permits research |
| native design/planning | `h-codebase-orientation`, `h-module-design`, `h-ac-quality` | Source ownership, architecture, packet boundaries, or acceptance drafting requires the specialist boundary |
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
| `r-challenger-protocol` | conceptual-design-reviewer, designer-challenger, planner-challenger, build-reviewer |
| `h-codebase-orientation` | designer-challenger, planner-challenger, builder, build-reviewer |
| `h-module-design` | designer-challenger, planner-challenger |
| `h-frontend-design` | conceptual-design-reviewer |
| `r-workspace-governance` | builder |
| `h-ac-quality` | planner-challenger |
| `w-orchestration` | orchestrator |
| `w-test-curation` | test-curator |
| `w-mem-curation` | memory-curator |
| `h-knowledge-ops` | knowledge-ingestor, knowledge-enricher |
| `w-knowledge-enrichment` | knowledge-enricher |

## Delegation And Nesting

| Delegate | Caller | Runtime consequence if unavailable |
|----------|--------|------------------------------------|
| conceptual-design-reviewer | designer | A consequential product, workflow, or interaction concept proceeds without independent conceptual challenge |
| designer-challenger | designer | Native admission lacks required repository-grounded entity challenge evidence |
| planner | orchestrator | An acquired Planning launch cannot produce a published task chain and worker-owned transition |
| planner-challenger | planner | A proposed Delivery task chain cannot receive independent advisory evidence |
| builder | orchestrator | Target build and assembly jobs cannot produce reviewed exact-commit claims |
| build-reviewer | builder | A target build or assembly claim cannot satisfy independent review |
| claim-arbiter | orchestrator | A persisted owner-reviewer disagreement cannot receive its one final decision |
| memory-curator | orchestrator | Periodic memory housekeeping is skipped |
| Explore | designer, planner, orchestrator | Broad read-only orientation must be performed by the caller or omitted |

The agent validator enforces ND3 metadata and frontmatter-to-`<agents>` alignment; see
`h-agent-structure` for the nesting rules.

## Hard-Control Map

| Control | Attached roles | Enforcement job |
|---------|----------------|-----------------|
| Agent `tools:` allowlist | Every agent | Limits runtime capabilities exposed to the role |
| `deny-writes.py` | planner, conceptual-design-reviewer, designer-challenger, planner-challenger, build-reviewer, claim-arbiter | Rejects durable edit-tool writes outside scratch; planner also enables terminal read-only mode |
| `deny-src-writes.py` | test-curator | Restricts writes to tests and scratch |
| `session-context.py` | builder | Adds repository context at session start |
| `lint-changed.py` | builder | Runs changed-file checks after tool use |
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
