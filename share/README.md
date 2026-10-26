# share/ - Agent Ecosystem

`share/` is the portable GitHub Copilot customization layer that OwlBear-enabled workspaces load: agents, skills
and instructions. This guide is for contributors changing that layer and for agents that need to find the right
authority.

[Project README](../README.md) · [Package map](../serve/README.md)

## Choose your next action

| You need to... | Start with | Authority to change |
| --- | --- | --- |
| Add or change a Copilot role | [Agents](#agents) | An `.agent.md` file and its required readings |
| Add a reusable workflow or rule | [Skills](#skills) | A `w-`, `r-`, or `h-` skill file |
| Apply a rule automatically by file type | [Instructions](#instructions) | An `.instructions.md` file and its `applyTo` scope |
| Understand why something loaded | [Relationship map](#relationship-map) | The matching instruction, agent or calling skill |
| Validate an ecosystem change | [Validation](#validation) | The focused validator and regression test |

## The one-minute model

Agents are Copilot roles. Skills teach reusable procedures or domain knowledge. Instructions apply rules to
matching files. Tool allowlists, MCP schemas and validators are the hard controls that can reject an operation;
prose can only guide a model. The executable files are the authority; the map below summarises them.

Project-specific overrides live under `.owlbear/{skills,instructions,prompts}/`. Workspace settings select both
the shared and project-local roots, so inspect `.vscode/settings.json` before diagnosing a loading problem.

## Directory Layout

| Directory | Contents | Naming convention |
| --- | --- | --- |
| `agents/` | Persistent roles with identity, model, tools, dependencies, and output contracts | `{role}.agent.md` |
| `skills/` | Reusable workflows, shared rules, and domain handbooks | `{prefix}-{domain}/SKILL.md` |
| `instructions/` | Auto-applied universal authorities and narrow pointers to skills | `{domain}.instructions.md` |

Delivery's own role agents and skills are not here: they ship inside the Delivery package
(`serve/delivery-next/src/owlbear_delivery_next/agents/` and `skills/`) and load only in the agent sessions OwlBear
starts. `owlbear install` links the shaping agent and its skill into `~/.copilot` so **New Change** finds them in
any VS Code window. Its `owlbear-curator` and `owlbear-test-curator` replaced the retired `memory-curator` and
`test-curator`.

### Agents

Start with the agent file when the change concerns a role's identity, tools, delegation, required reading, or output
contract. Its frontmatter is load-bearing.

### Skills

| Prefix | Meaning |
| --- | --- |
| `w-` | Workflow: ordered procedure with entry, execution, and output behavior |
| `r-` | Rules: shared behavioral convention used by multiple consumers |
| `h-` | Handbook: domain knowledge loaded when that capability is needed |

Required reading belongs in an agent only when the skill is needed in roughly 90% of its sessions; specialist
material loads on demand immediately before its decision. A visible skill description helps routing but does not
mean the skill has been read.

### Instructions

Instruction frontmatter controls `applyTo` matching. Keep an instruction short and point to the skill that owns the
procedure; the pointer should not reproduce it.

### Prompts

`share/` ships no prompts: Delivery's pages and steps replaced its chat commands. OwlBear's own repository keeps none
either: the Copilot harness does not load prompt files. Its audits are skills invoked by name until they become
Maintenance actions (`D-01M5WG5KHAXT8P99VXHKWW5EBJ`).

## Relationship Map

Only live relationships are listed. When one changes, edit its executable owner first, then this map in the same
change.

### Instructions

| Instruction | Applies to | Loads |
| --- | --- | --- |
| `.github/copilot-instructions.md` | Every workspace turn | Project identity, topology, commands |
| `owlbear-system.instructions.md` | `**` | `h-memory-structure` and `h-mcp-memory` when a save-capable role has a reusable insight; `r-challenger-protocol` when handling review findings; `r-workspace-governance` for commits and artifact placement |
| `agent-ecosystem.instructions.md` | Shared and project-local customization roots | This README and `h-agent-structure` |
| `python.instructions.md` | `**/*.py` | `h-python-conventions`, which points to `h-pytest-and-linting` for test and lint commands |
| `frontend.instructions.md` | The Delivery engine's pages under `serve/delivery-next/src/owlbear_delivery_next/web/` | `h-frontend-conventions`, which points to `h-frontend-design` and, when a project declares a PDS wrapper, its package-provided `pds-knowledge-{framework}` skill |
| `doc-standards.instructions.md` | Canonical project documentation | `r-doc-standards` |
| `research-docs.instructions.md` | `.owlbear/research/*.md` | `w-research`, which uses `h-codebase-orientation` |

Project-local `.owlbear/instructions/` files compose with these when their `applyTo` globs match. They are not part
of the portable map.

### Agents

| Agent | Required reading | Delegates |
| --- | --- | --- |
| `knowledge-ingestor` | `h-knowledge-ops` | None |
| `knowledge-enricher` | `w-knowledge-enrichment`, `h-knowledge-ops` | None |

No shared agent delegates to a subagent or declares hooks. Tool allowlists and models stay in agent frontmatter.

### Repository skills

`.github/skills/` holds this repository's own skill: `session-review` reviews another local chat. It is not shared
with consuming projects.

## Effective Instruction Stack

| Layer | When it appears | Appropriate content | Authority |
| --- | --- | --- | --- |
| Platform and policy | Every session | Product-level safety, tool semantics, and system behavior | VS Code and GitHub Copilot |
| `.github/copilot-instructions.md` | Every turn in the workspace | Current-project identity, topology, stack, commands, and resources | Project workspace |
| Matching `.instructions.md` files | When `applyTo` matches the working file | Universal behavior, project-local domain rules, or a pointer to a skill | Most specific matching instruction |
| Skill discovery metadata | Available for routing | Name and concise trigger description | Skill frontmatter |
| Agent body | When the role is selected or dispatched | Identity, boundaries, dependencies, communication contract | Agent file |
| Required skill bodies | At agent session start | Knowledge needed in most of that role's sessions | Agent `<required_reading>` |
| On-demand skill bodies | When a named condition occurs | Specialist procedure, rules, or domain knowledge | Calling instruction or skill |
| Runtime state and tools | When queried or invoked | Changes, Memory, Knowledge, schemas, and mutation semantics | Owning runtime service |

More specific rules do not automatically erase broader rules. Resolve a conflict by identifying the job and its
fit authority; do not keep both versions as competing truths.

## Soft Guidance And Hard Controls

| Control | Kind | What it can do |
| --- | --- | --- |
| Personas, rules, workflows, handbooks, examples | Soft | Steer model decisions; cannot prevent a violation |
| Agent `tools:` and `agents:` frontmatter | Hard runtime boundary | Limit exposed capabilities and dispatch targets |
| MCP and application schemas | Hard runtime boundary | Reject invalid operations or state |
| Repository validators and regression tests | Hard repository boundary | Detect invalid customization structure and drift |

Do not describe a prose requirement as enforced. If a yes/no rule is safety-critical or structural, prefer a tool
restriction, schema, validator, or focused regression test, and keep the text as the explanation.

## Choosing The Owning Artifact

Put one rule in one canonical home and give consumers at most one concise pointer.

| Job | Canonical home |
| --- | --- |
| Current-project facts, paths, stack, and commands | `.github/copilot-instructions.md` |
| Behavior every OwlBear agent needs on nearly every turn | Universal authority instruction |
| File-domain safety net that routes to fuller guidance | Instruction pointer |
| Reusable convention shared by multiple roles | `r-` rules skill |
| Step-by-step procedure | `w-` workflow skill |
| Situational technical or domain reference | `h-` handbook skill |
| One role's identity, model, tools, boundaries, and output interface | Agent file |
| Project-specific behavior that should not ship to every consumer | Matching `.owlbear/` customization |
| Tool arguments, state transitions, and validation semantics | Owning runtime implementation or schema |

For required frontmatter, body sections, naming grammar, nesting rules, and extraction criteria, read
`h-agent-structure`. It is the structural authority; this README owns the composition and the map.

## Product Boundary

The ecosystem targets **GitHub Copilot custom agents in VS Code**. Its frontmatter fields, tool names, instruction
loading, and subagent behavior are product contracts, not portable conventions for other products. Agent `model:`
fields declare the intended model; they do not prove which model ran.

## Change Workflow

1. **Confirm the active roots.** Read `.vscode/settings.json` and tell the loaded tree from source or consumer
 copies.
2. **Read the structural authority.** Load `h-agent-structure` and the matching instruction.
3. **Find the executable owner** and classify the job with the table above.
4. **Check timing and enforcement.** Required reading for regular use, specialist material just before its phase;
 a hard owner for anything that must reject invalid behavior.
5. **Edit the smallest canonical surface.** Remove obsolete copies instead of synchronising them, and update the
 [relationship map](#relationship-map).
6. **Run focused validation.**

## Validation

These commands are for the OwlBear checkout; consumer projects follow the [setup guide](../setup/setup-guide.md).

```shell
uv run python .owlbear/scripts/validate_agents.py
uv run python .owlbear/scripts/validate_skills.py
uv run pytest -q tests/test_agent_ecosystem_validation.py
```

The regression test exercises the validators and resolves declared OwlBear MCP tools against live registries. Also
run the narrow test owned by the changed workflow. Validator success proves structure, not that an instruction is
useful or well timed. If a validator disagrees with this map, fix the executable owner first.
