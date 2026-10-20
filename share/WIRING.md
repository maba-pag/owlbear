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
| test-curator | GPT-6.1 Sol (copilot) | `w-test-curation`, `r-workspace-governance` | None | `PreToolUse`: deny source writes through recognized file tools; terminal execution is trusted for this manually invoked role |
| memory-curator | GPT-6 Luna | `w-mem-curation` | None | None |
| knowledge-ingestor | GPT-6 Luna | `h-knowledge-ops` | None | None |
| knowledge-enricher | GPT-6 Luna | `w-knowledge-enrichment`, `h-knowledge-ops` | None | None |

Tool allowlists remain in agent frontmatter; they are not duplicated here.

The new Delivery engine ships its own agents and skills in its package; they are not part of this
shared map.

## Prompt Entry Map

| Prompt | Entry route | Initial loading behavior |
| --- | --- | --- |
| `challenge-plan_sol` | Current agent directed by `.github/prompts` | Dispatches a fresh unnamed read-only subagent with `GPT-6.1 Sol (copilot)`; caller reconciles evidence and owns the recommendation |
| `challenge-implementation_sol` | Current agent directed by `.github/prompts` | Dispatches a fresh unnamed read-only subagent with `GPT-6.1 Sol (copilot)`; caller reconciles findings and owns the verdict |
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

The new Delivery engine's Changes page (New Change, the shaping chat) replaces the retired
`ideate`, `design`, `continue-change`, `finalize-change`, `inspect-change`, `address-pr-feedback`,
`resolve-target-conflict`, `repair-delivery` and `resolve-delivery-attention` prompts.

## Conditional Skill Loading

The named caller owns each on-demand condition and timing.

| Caller or trigger | Conditional skill | Load condition |
| --- | --- | --- |
| universal memory governance | `h-memory-structure`, `h-mcp-memory` | A save-capable role has a qualifying reusable insight |
| Python instruction | `h-python-conventions` | The active file matches the Python instruction scope |
| frontend instruction | `h-frontend-conventions` | The active file matches the frontend instruction scope |
| frontend conventions | package-provided `pds-knowledge-{framework}` | The project declares a PDS wrapper and its generated companion link resolves |
| proof selection | `h-pytest-and-linting` or `h-vitest-and-linting` | The changed domain uses that test and lint toolchain |

## Required Skill Consumers

This inverse map includes only direct `<required_reading>` consumers, not conditional loading.

| Skill | Required by |
| --- | --- |
| `w-test-curation` | test-curator |
| `r-workspace-governance` | test-curator |
| `w-mem-curation` | memory-curator |
| `h-knowledge-ops` | knowledge-ingestor, knowledge-enricher |
| `w-knowledge-enrichment` | knowledge-enricher |

## Delegation And Nesting

No shared agent delegates to a subagent. No agent triggers `memory-curator`; the user runs it or
reviews pending entries on the Delivery engine's Memory page.

The agent validator enforces frontmatter-to-`<agents>` alignment; see `h-agent-structure` for the
nesting rules.

## Hard-Control Map

| Control | Attached roles | Enforcement job |
| --- | --- | --- |
| Agent `tools:` allowlist | Every agent | Limits runtime capabilities exposed to the role |
| `deny-src-writes.py` | test-curator | Restricts recognized file-tool writes to tests and scratch; manually invoked terminal execution is trusted |
| MCP schemas and stores | Tool-capable roles | Validate arguments, transitions, and persisted state |
| `validate_agents.py` | Repository validation | Checks frontmatter, required sections, tools, hooks, and delegation |
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

These validator scripts and the regression test are maintenance commands for the OwlBear checkout.
Consumer projects should follow the
[setup guide](../setup/setup-guide.md) for installation and verification.

If a validator disagrees, repair its executable owner before this map.
