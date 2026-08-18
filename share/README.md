# share/ - Agent Ecosystem

`share/` is the portable GitHub Copilot customization layer that OwlBear-enabled workspaces load.
It contains roles, reusable instructions, user-invoked prompts, and visual references. This guide
is for contributors changing that layer and for agents that need to locate the correct authority.

[Project README](../README.md) · [Package map](../serve/README.md) ·
[Derived wiring map](WIRING.md)

## Choose your next action

| You need to... | Start with | Authority to change |
| --- | --- | --- |
| Add or change a Copilot role | [Agents](#agents) | An `.agent.md` file and its required readings |
| Add a reusable workflow or rule | [Skills](#skills) | A `w-`, `r-`, or `h-` skill file |
| Apply a rule automatically by file type | [Instructions](#instructions) | An `.instructions.md` file and its `applyTo` scope |
| Add a user command | [Prompts](#prompts) | A `.prompt.md` file and its selected agent |
| Understand why something loaded | [Effective instruction stack](#effective-instruction-stack) | The matching roots and direct dependency |
| Check delegation, hooks, or tools | [WIRING.md](WIRING.md) | Executable frontmatter and hook/source files |
| Validate an ecosystem change | [Validation](#validation) | The focused validator and regression test |

## The one-minute model

Agents are Copilot roles. Skills teach reusable procedures or domain knowledge. Instructions apply
rules to matching files. Prompts are user-facing entry points. Hooks and MCP schemas are the hard
controls that can reject an operation; prose can only guide a model. WIRING.md summarizes the live
relationships, but the executable files remain authoritative.

The normal path is:

```text
prompt -> agent -> required/on-demand skills -> tools and hooks -> runtime authority
```

Project-specific overrides live under `.owlbear/{agents,skills,instructions,prompts}/`. Workspace
settings select both the shared and project-local roots, so inspect `.vscode/settings.json` before
diagnosing a loading problem.

## Directory Layout

| Directory | Contents | Naming convention |
| --- | --- | --- |
| `agents/` | Persistent roles with identity, model, tools, hooks, dependencies, and output contracts | `{role}.agent.md` |
| `skills/` | Reusable workflows, shared rules, and domain handbooks | `{prefix}-{domain}/SKILL.md` |
| `instructions/` | Auto-applied universal authorities and narrow safety-net stubs | `{domain}.instructions.md` |
| `prompts/` | User-invoked one-shot entry points | `{verb}.prompt.md` or `{scope}-{verb}.prompt.md` |
| `diagrams/` | Shared explanatory visual assets | Descriptive filenames |

## Agents

Start with the agent file when the change concerns a role's identity, tools, hooks, delegation,
required reading, or output contract. Its frontmatter is load-bearing; update direct dependencies
and WIRING.md when those relationships change.

## Skills

Use `w-` for ordered workflows, `r-` for shared rules, and `h-` for handbooks loaded when a domain
needs deeper knowledge. Required reading belongs in an agent only when the skill is needed in nearly
every session; specialist material should load on demand immediately before its decision.

## Instructions

Instruction frontmatter controls `applyTo` matching. Keep an instruction concise and point to the
full skill that owns the procedure. More specific rules do not automatically erase broader rules;
resolve conflicts by identifying the job and its fit authority.

## Prompts

Prompts are user-facing workflow entry points. They collect the smallest input needed and route to
the agent or workflow that owns the next decision. They should not become a second copy of a skill.

## Visual Orientation

The [MCP topology diagram](diagrams/mcp-topology.svg) shows the five seeded stdio servers and the
runtime surfaces behind them. Its [editable Excalidraw source](diagrams/mcp-topology.excalidraw) is
descriptive; `seed/.vscode/mcp.json` and the server implementations remain authoritative.

## Product Boundary

The ecosystem targets **GitHub Copilot custom agents in VS Code**. Its frontmatter fields, tool
names, hooks, instruction loading, prompt routing, and subagent behavior are product contracts, not
portable conventions for Claude.ai, Claude Code, ChatGPT, Codex, or a generic model API.

Agent `model:` fields declare the intended Copilot model for each role. They do not prove which
model ran, expose its reasoning setting, or create a cross-product fallback. When model availability
or runtime attribution matters, verify it in the active VS Code product rather than inferring it
from this repository.

## Effective Instruction Stack

The model does not read every control in the same way. The effective behavior for one invocation is
the ordered composition of the active layers below.

| Layer | When it appears | Appropriate content | Authority |
| --- | --- | --- | --- |
| Platform and policy | Every session | Product-level safety, tool semantics, and system behavior | VS Code and GitHub Copilot |
| `.github/copilot-instructions.md` | Every turn in the workspace | Current-project identity, topology, stack, commands, and resources | Project workspace |
| Matching `.instructions.md` files | When `applyTo` matches the working file | Universal behavior, project-local domain rules, or a pointer to a specialist skill | Most specific matching instruction |
| Skill discovery metadata | Available for relevance and invocation routing | Name, category, and concise trigger description | Skill frontmatter |
| Prompt body | When the user invokes the prompt | One-shot input handling, selected agent, and workflow entry | Prompt file |
| Agent body | When the role is selected or dispatched | Identity, boundaries, guaranteed dependencies, communication contract | Agent file |
| Required skill bodies | At agent session start | Knowledge needed in at least 90% of that role's sessions | Agent `<required_reading>` |
| On-demand skill bodies | When a named condition occurs | Specialist procedure, rules, or domain knowledge | Calling workflow or companion table |
| Runtime state and tools | When queried or invoked | Current jobs, Memory, Knowledge, schemas, and mutation semantics | Owning runtime service |

More specific rules do not automatically erase broader rules. Resolve a conflict by identifying the
job and its fit authority; do not preserve both versions as competing truths.

### Skill Loading Tiers

1. **Required reading** is listed directly in an agent's `<required_reading>` section and loaded at
 session start. Use it only when the role needs the full skill in roughly 90% or more of sessions.
2. **On-demand reading** is named by a workflow step, companion table, prompt, or instruction stub
 and loaded immediately before the relevant decision or operation.
3. **Discovery metadata** is not the skill body. A visible skill description helps routing but does
 not mean the procedure has been read.

Only direct, regular dependencies belong in `<required_reading>`. A required skill owns the timing
of its situational companions. This keeps specialist material out of early context while preserving
a reachable loading path.

An `applyTo` stub can reinforce an important skill boundary for agents that reach the file without
the expected workflow. The stub should point to the authority, not reproduce it.

## Soft Guidance And Hard Controls

Text and enforcement serve different jobs even when both use imperative language.

| Control | Kind | What it can do |
| --- | --- | --- |
| Personas, critical rules, workflows, handbooks, examples, and prompt instructions | Soft | Steer model decisions; they cannot mechanically prevent a violation |
| Agent `tools:` and `agents:` frontmatter | Hard runtime boundary | Limit exposed capabilities and dispatch targets |
| `PreToolUse`, `PostToolUse`, and `SessionStart` hooks | Hard runtime boundary | Reject operations, add context, or run checks at defined lifecycle points |
| MCP and application schemas | Hard runtime boundary | Reject invalid operations or state |
| Repository validators and regression tests | Hard repository boundary | Detect invalid customization structure and authority drift before delivery |

Do not describe a prose requirement as enforced. If a yes/no rule is safety-critical or structural,
prefer an existing tool restriction, hook, schema, validator, or focused regression test. Keep the
text as the explanation and point to the enforcing owner.

## Choosing The Owning Artifact

Put one rule in one canonical home and give consumers at most one concise pointer or reinforcement.

| Job | Canonical home |
| --- | --- |
| Current-project facts, paths, stack, and commands | `.github/copilot-instructions.md` |
| Behavior every OwlBear agent needs on nearly every turn | Universal authority instruction |
| File-domain safety net that routes to fuller guidance | Instruction stub |
| Reusable convention shared by multiple roles | `r-` rules skill |
| Step-by-step procedure | `w-` workflow skill |
| Situational technical or domain reference | `h-` handbook skill |
| One role's identity, model, tools, hooks, boundaries, and output interface | Agent file |
| User-facing one-shot command and input collection | Prompt file |
| Project-specific behavior that should not ship to every consumer | Matching `.owlbear/` customization |
| Tool arguments, state transitions, and validation semantics | Owning runtime implementation or schema |

Skill prefixes encode the content type:

| Prefix | Meaning |
| --- | --- |
| `w-` | Workflow: ordered procedure with entry, execution, and output behavior |
| `r-` | Rules: shared behavioral convention used by multiple consumers |
| `h-` | Handbook: domain knowledge loaded when that capability is needed |

For required frontmatter, body sections, naming grammar, nesting-depth constraints, and extraction
criteria, read `h-agent-structure`. It is the creation-time structural authority; this README owns
the composition and maintenance model.

## Runtime And Source Of Truth

Several representations are intentionally derived:

- Agent frontmatter and body sections own model, tool, hook, required-reading, and delegation
  declarations.
- Skill and prompt bodies own their direct and conditional loading instructions.
- Instruction frontmatter owns `applyTo` scope.
- MCP servers and application models own live tool and schema behavior; handbooks document them.
- [WIRING.md](WIRING.md) summarizes those relationships for ecosystem-wide orientation. It never
  overrides an executable declaration.

When changing a relationship, edit its executable owner first, then update direct pointers and the
derived wiring map in the same change. Do not hand-maintain a second inverse list inside another
skill or agent.

### Delegation And Nesting

VS Code does not inject the global agent catalog at deeper nesting levels. A dispatching agent's
frontmatter `agents:` list and body `<agents>` table therefore form a load-bearing pair and must
agree. Agents callable at nesting depth three or deeper also require the product-specific invocation
setting documented in `h-agent-structure`.

The agent validator enforces the current delegation alignment and nesting-depth rule. Do not copy
the current set of nested agents into this README; consult [WIRING.md](WIRING.md) for the derived
inventory and the agent files for authority.

## Change Workflow For Agents And Skills

Use this sequence for changes under `share/{agents,skills,instructions,prompts}/` or the equivalent
project-local `.owlbear/` roots:

1. **Confirm the active roots.** Read `.vscode/settings.json` and distinguish the loaded tree from
 source, seed, generated, or consumer copies.
2. **Read the structural authority.** Load `h-agent-structure` and the matching instruction stub.
3. **Find the executable owner.** Start from the named agent, skill, prompt, instruction, hook, or
 failing validator. Follow only the direct loading and delegation edges needed for the change.
4. **Classify the job.** Decide whether the behavior is project fact, universal behavior, shared
 rule, workflow, handbook knowledge, role boundary, prompt entry, or runtime enforcement.
5. **Check timing.** Required reading should represent regular use; specialist material should load
 immediately before its phase. Avoid both unavailable-late rules and irrelevant-early context.
6. **Check enforcement.** Separate prose guidance from tool, hook, schema, and validator behavior.
 Update the hard owner when the requirement must reject invalid behavior mechanically.
7. **Edit the smallest canonical surface.** Update direct consumers only when their pointer,
 allowlist, hook, or output contract changes. Remove obsolete copies instead of synchronizing them.
8. **Update the derived map.** Revise [WIRING.md](WIRING.md) for changed roles, loading edges,
 delegation, hooks, models, or entry points.
9. **Run focused validation.** Use the checks below and any workflow-specific regression that
 exercises the changed decision.

## Validation

These validator commands are for the OwlBear development checkout. The consumer `main` branch
ships the shared customization files but not the development-only `.owlbear/` validator scripts or
the repository test suite; contributors should run them from the `dev` checkout.

Run structural validators after changing agents, skills, or prompts:

```shell
uv run python .owlbear/scripts/validate_agents.py
uv run python .owlbear/scripts/validate_skills.py
uv run python .owlbear/scripts/validate_prompts.py
```

Run ecosystem integrity and write-boundary regressions when changing agent structure, MCP grants,
delegation, write restrictions, or delivery ownership:

```shell
uv run pytest -q \
  tests/test_agent_ecosystem_validation.py \
  tests/test_write_guard_hooks.py
```

Also run the narrow test or executable check owned by the changed workflow. Validator success proves
structural conformance, not that the instruction is useful, correctly timed, or behaviorally
effective.

## Maintenance Boundaries

- Keep this README stable and category-oriented. Do not add a list of every current agent, skill,
  instruction, or prompt.
- Keep [WIRING.md](WIRING.md) exact and current. It may enumerate active controls because its job is
  to expose the derived runtime map.
- Keep structural specification in `h-agent-structure`; link rather than duplicate its templates.
- Keep workflow and domain details in their owning skills; do not turn this guide into required
  reading for unrelated product work.
- Preserve project-local rules under `.owlbear/` when they are not portable to consumers.
- Treat observed model behavior as evidence, not a reason to add repeated reminders at multiple
  layers. First ask whether the model failed or the harness loaded the wrong, late, or conflicting
  control.
