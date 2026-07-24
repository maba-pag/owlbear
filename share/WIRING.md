# Agent Ecosystem Wiring

This document is the derived operational map of OwlBear's active shared agent ecosystem. It helps
customization authors see cross-file relationships without reconstructing the graph from every
frontmatter block and workflow body.

The map is descriptive, not authoritative. Resolve discrepancies in this order:

1. agent, prompt, skill, and instruction frontmatter;
2. agent body sections and direct workflow loading instructions;
3. hooks, tool registries, and runtime schemas;
4. this document.

See [README.md](README.md) for the stable composition model, artifact ownership, change procedure,
and validation commands. Update this map whenever an executable loading or delegation relationship
changes.

## Connection Vocabulary

| Label | Meaning |
|-------|---------|
| `auto` | VS Code injects the control from workspace configuration or matching instruction scope |
| `prompt` | A prompt selects an agent or directs the current agent to a skill |
| `required` | The agent lists the skill in `<required_reading>` and loads it at session start |
| `conditional` | A workflow, prompt, or universal rule loads the skill only when its named condition occurs |
| `delegate` | The caller exposes and invokes a subagent through `agents:` and its `<agents>` table |
| `hook` | VS Code runs a command at `SessionStart`, `PreToolUse`, or `PostToolUse` |

Discovery metadata alone is not a loaded skill body and is therefore not represented as a runtime
edge below.

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

Required skills and custom delegates below are exact snapshots of agent declarations. Built-in
delegates are shown because they affect runtime behavior but do not have repository agent files.

| Agent | Model | Required reading | Delegates | Hooks |
|-------|-------|------------------|-----------|-------|
| orchestrator | GPT-5.6 Terra | `w-orchestration` | builder, verifier, collector, memory-curator, Explore | None |
| shaper | GPT-5.6 Sol | `r-pipeline-protocol`, `r-workspace-governance` | shaper-challenger, Explore | `PreToolUse`: deny non-document writes |
| builder | GPT-5.6 Terra | `r-pipeline-protocol`, `r-workspace-governance`, `h-codebase-orientation` | builder-challenger | `SessionStart`: task context; `PostToolUse`: lint changed files |
| verifier | GPT-5.6 Terra | `r-pipeline-protocol`, `r-workspace-governance`, `h-codebase-orientation` | verifier-challenger | `SessionStart`: task context; `PostToolUse`: lint changed files |
| collector | GPT-5.6 Terra | `r-pipeline-protocol`, `r-workspace-governance`, `h-mcp-kanban` | Explore | `PreToolUse`: deny writes except scratch |
| shaper-challenger | Claude Sonnet 5 | `h-ac-quality`, `h-module-design`, `r-pipeline-protocol` | None | `PreToolUse`: deny writes except scratch |
| builder-challenger | MAI-Code-1-Flash | `r-pipeline-protocol` | None | `PostToolUse`: lint changed files |
| verifier-challenger | GPT-5.6 Luna | `r-pipeline-protocol` | None | `PreToolUse`: deny writes except scratch |
| test-curator | GPT-5.6 Terra | `w-test-curation` | None | `PreToolUse`: deny source writes |
| memory-curator | GPT-5.6 Terra | `w-mem-curation` | None | None |
| knowledge-ingestor | GPT-5.6 Luna | `h-knowledge-ops` | None | None |
| knowledge-enricher | GPT-5.6 Luna | `w-knowledge-enrichment`, `h-knowledge-ops` | None | None |

Tool allowlists remain in agent frontmatter and are validated against known product and MCP tool
names. They are deliberately not duplicated here: exact tool grants change more often than role and
loading relationships, and tests already enforce the sensitive Kanban and memory profiles.

## Prompt Entry Map

| Prompt | Entry route | Initial loading behavior |
|--------|-------------|--------------------------|
| `shape` | `prompt` -> shaper | Shaper selects `w-spec-shaping` or `w-task-repair` after classifying the input |
| `orchestrate` | `prompt` -> orchestrator | Agent required-reading loads `w-orchestration` |
| `test-curation` | `prompt` -> test-curator | Agent required-reading loads `w-test-curation` |
| `kb-ingest` | `prompt` -> knowledge-ingestor | Agent required-reading loads `h-knowledge-ops` |
| `kb-enrich` | `prompt` -> knowledge-enricher | Agent required-reading loads `w-knowledge-enrichment` and `h-knowledge-ops` |
| `ideate` | Current agent directed by prompt | Loads `w-idea-refinement` |
| `architecture-review` | Current agent directed by prompt | Loads module-design, orientation, visual-output, and idea-refinement skills |
| `arch-audit` | Current agent directed by prompt | Loads `h-module-design` |
| `frontend-audit` | Current agent directed by prompt | Loads frontend design and conventions; loads frontend proof guidance only for that toolchain |
| `memory-audit` | Current agent directed by prompt | Loads memory structure, MCP memory, and curation skills before review |
| `legacy-audit` | Current agent directed by prompt | Uses its prompt-defined read-only audit procedure |

Project-local prompts are outside the portable inventory. They may select built-in agents or load
project-local skills in addition to the shared surface.

## Conditional Skill Loading

These are the load-bearing on-demand paths in the shared ecosystem. The named caller owns the
condition and timing.

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

This inverse map includes only direct `<required_reading>` consumers. Conditional consumers belong
in the preceding table and must not be mistaken for guaranteed session-start context.

| Skill | Required by |
|-------|-------------|
| `r-pipeline-protocol` | shaper, builder, verifier, collector, shaper-challenger, builder-challenger, verifier-challenger |
| `r-workspace-governance` | shaper, builder, verifier, collector |
| `h-codebase-orientation` | builder, verifier |
| `h-mcp-kanban` | collector |
| `h-ac-quality` | shaper-challenger |
| `h-module-design` | shaper-challenger |
| `w-orchestration` | orchestrator |
| `w-test-curation` | test-curator |
| `w-mem-curation` | memory-curator |
| `h-knowledge-ops` | knowledge-ingestor, knowledge-enricher |
| `w-knowledge-enrichment` | knowledge-enricher |

## Delegation And Nesting

| Delegate | Caller | Runtime consequence if unavailable |
|----------|--------|------------------------------------|
| builder | orchestrator | Build tasks cannot be dispatched |
| verifier | orchestrator | Verify tasks cannot be dispatched |
| collector | orchestrator | Collect tasks cannot be dispatched |
| memory-curator | orchestrator | Periodic memory housekeeping is skipped |
| shaper-challenger | shaper | Shape approval loses the required adversarial cross-check |
| builder-challenger | builder | Build completion loses its required proof and scope cross-check |
| verifier-challenger | verifier | Verification completion loses its required final cross-check |
| Explore | orchestrator, shaper, collector | Broad read-only orientation must be performed by the caller or omitted |

The three challenger roles are callable at nesting depth three and therefore declare
`disable-model-invocation: false`. Their descriptions carry the `(ND3)` marker. The agent validator
enforces this set and verifies that custom delegates in frontmatter match each caller's `<agents>`
table. Built-in agents resolve independently of repository agent definitions.

## Hard-Control Map

| Control | Attached roles | Enforcement job |
|---------|----------------|-----------------|
| Agent `tools:` allowlist | Every agent | Limits runtime capabilities exposed to the role |
| `deny-non-doc-writes.py` | shaper | Allows documentation and diagram writes, rejects code writes |
| `deny-writes.py` | collector and read-only challengers | Rejects durable writes outside scratch |
| `deny-src-writes.py` | test-curator | Restricts writes to tests and scratch |
| `session-context.py` | builder, verifier | Adds task-aware context at session start |
| `lint-changed.py` | builder, verifier, builder-challenger | Runs changed-file checks after tool use |
| MCP schemas and stores | Tool-capable roles | Validate arguments, transitions, and persisted state |
| `validate_agents.py` | Repository validation | Checks tools, delegation alignment, and nesting-depth metadata |
| `validate_skills.py` | Repository validation | Checks skill metadata and structure |
| `test_skill_authority_wiring.py` | Repository regression | Checks required readers, tool profiles, and authority reachability |
| Write-guard regression tests | Repository regression | Exercise path restrictions and hook behavior |

Workflow prose explains these constraints but does not replace their runtime or repository owner.

## Maintenance Protocol

Update this document in the same change when any of these surfaces changes:

- an agent's model, required reading, delegate list, hook, or role;
- a prompt's selected agent or initial skill route;
- an instruction's loading scope or target authority;
- a workflow's load-bearing conditional companion;
- a nested agent's caller or invocation-depth requirement;
- a hard control's attached role or enforcement job.

Do not update this map from memory. Read the changed executable files, then run:

```shell
uv run python .owlbear/scripts/validate_agents.py
uv run python .owlbear/scripts/validate_skills.py
uv run pytest -q tests/test_skill_authority_wiring.py
```

If this map and a validator disagree, repair the executable source or validator first, then
regenerate the affected rows here.
