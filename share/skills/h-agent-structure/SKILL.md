---
name: h-agent-structure
description: "Handbook: Structural standards for shared agent files, skill files, and instruction stubs"
user-invocable: false
---

# Agent Ecosystem Structure

Structural model for all shared agent, skill, and instruction files. Single source of truth for what belongs where.

## Foundation

For loading mechanisms (copilot-instructions, instructions, skills), two-tier skill loading, belts-and-suspenders, and tier counts with agent names, see [share/README.md](../../README.md).

This skill specifies file structure, required sections, naming grammar, anti-patterns, and instruction file types — the creation-time spec.

## File Type Selection

| File type | Choose when |
|-----------|------------|
| `.prompt.md` | User-facing one-shot command, invoked explicitly. Default for user commands. |
| `SKILL.md` | Reusable domain knowledge that auto-loads by relevance, or needs co-located resources. |
| `.agent.md` | Long-lived role with persistent behavior: tool restrictions, model preferences, handoff boundaries, hooks. |

Default: user-facing one-shot commands use `.prompt.md` unless auto-loading or co-located resources are needed.

## Boundary Fitness

| Condition | Tier |
|-----------|------|
| Current-project identity, topology, stack, commands, or resources | `copilot-instructions.md` |
| Universal OwlBear behavior needed by every agent | Authority `.instructions.md` such as `owlbear-system.instructions.md` |
| Reusable behavior needed by multiple but not all roles | Shared skill or protocol |
| Content is loaded from `<critical_rules>` | Skill-tier minimum (SKILL.md or authority `.instructions.md`) |
| Content applies to a single agent only | Agent file body |
| Content is a step-by-step procedure invoked on-demand | Workflow skill (SKILL.md) |
| Content is a file-type safety net pointing to a skill | Instruction stub (`.instructions.md`) |

## Agent Extraction Markers

### Extract when (≥ 2 apply)

- Concern requires a distinct `tools:` allowlist.
- Concern has an independent failure domain (its failure should not abort the parent).
- Same delegation pattern appears in 2+ agents.
- Concern requires a distinct model (cost, capability, or context-length profile).
- Concern's procedure would exceed one screen inline in the parent's `<critical_rules>`.

### Defer extraction when (< 2 extract conditions apply)

- No distinct `tools:` or model requirements — parent's allowlist covers the concern.
- Concern never fails independently — any failure aborts the parent.
- Concern fits in a single `<critical_rules>` bullet.

### Precedent

`builder-challenger` extracted from `builder`: independent cheap cross-check, distinct model, and deterministic auto-fix/reporting boundary.

## Principles

### Rule of Two

A fact appears in at most **two** places:

1. **Source of truth** — the most specific shared skill, protocol, instruction, or project-fact source
2. **One inline reference** — a 1-line summary or pointer in the consumer

If a rule applies to 2+ agents identically, it belongs in a shared skill, protocol, or authority
instruction, not in local project instructions and not repeated in each agent.

### Project Instructions Boundary

`copilot-instructions.md` describes the current project. It may contain identity, repository topology,
technology choices, package-specific commands, and primary project resources. It must not contain
portable OwlBear workflows, agent behavior, tool manuals, file-placement policy, or pipeline rules.

Shared behavior belongs in `owlbear-system.instructions.md` only when every agent needs it on every
turn. Otherwise use the narrowest shared skill or protocol and load it from the relevant roles.

### Implicit Encoding

Every section in an agent file can carry more than its primary function:

| Section | Primary function | Implicit function |
|---------|-----------------|-------------------|
| `<persona>` | Identity | Behavioral rules through emotional framing |
| `<required_reading>` | Dependency declaration | Guaranteed skill loading at session start |
| `<output_format>` | Communication spec | Evidence forcing through required columns |
| `<examples>` | Behavioral reference | Reasoning patterns through abstract principles |
| `<pipeline_position>` | Pipeline context | Quality bar through threshold conditions |
| `<boundaries>` | Safety constraints | Behavioral nudges through red flags |

## Agent File Structure (.agent.md)

Agent files define **identity, authority, and boundaries**. They answer: "Who am I? What can I touch? How do I communicate?"

### Frontmatter (YAML)

```yaml
---
name: {agent-name}
description: "{one-line role description}"
argument-hint: "{Verb}: {what_this_agent_processes}"
user-invocable: {true|false}
disable-model-invocation: {true|false}
model: {model_or-array}
tools: [{tool_list}]
agents: [{subagent_names}]    # only if agent delegates
hooks:                         # only if enforcement needed
  PreToolUse:
    - type: command
      command: {hook_command}
---
```

- `user-invocable: false` — hides from the `/` slash-command menu. Use for pipeline-only agents/skills that should only be dispatched by the orchestrator.
- `disable-model-invocation: true` — prevents autonomous invocation by other models. Use for L1/L2 pipeline agents. **Must be `false` for ND3 agents** (agents that may be called at nesting depth ≥3), because VS Code does not resolve agents with `true` at depth ≥2. See § Nesting Depth & DMI below.

### Required Sections

**`<persona>`** — 2-3 short paragraphs defining role, expertise, and attitude.

Design process:

1. List the 5 most important behaviors for this agent
2. Find a real-world scenario where those behaviors arise naturally from the situation's constraints
3. Frame the persona in that scenario — the emotional stakes should make the desired behaviors feel inevitable, not imposed
4. Cross-check: which explicit rules in `<critical_rules>` can now be removed because the persona already implies them?

The persona is not decoration — it is an **implicit rule encoder**. A well-chosen emotional framing activates behavioral patterns that would otherwise cost explicit rule tokens.

**`<required_reading>`** — Skills the agent must `read_file` at session start.

Lists the skills this agent needs in 90%+ of sessions. These are Level 0 (direct) dependencies only — transitive dependencies (skills referenced by other skills) are handled by each skill's own Step 0 / preamble.

**Criterion:** if the agent almost always needs the skill (90%+), list it. If the agent sometimes needs it, it stays on-demand (loaded during the workflow when relevant).

```markdown
<required_reading>

- `r-pipeline-protocol` — task lifecycle, communication, quality
- `r-pipeline-protocol` — primary workflow/rules source

</required_reading>
```

**`<critical_rules>`** — 3-7 non-negotiable constraints, ordered by importance.

- First item: "**Follow the `{primary_skill}` skill** for {1-line summary}."
- Pipeline agents (T1-T3): second item references `r-pipeline-protocol` for shared conventions.
- Every remaining rule must be **unique** to this agent. If the same rule would appear in 2+ agents,
  it belongs in a shared skill, protocol, or authority instruction.
- Each rule must be **actionable** — it can be verified as followed or violated.

**`<output_format>`** — The agent's communication interface.

- **Channel A:** verdict tokens + format string. One row per verdict.
- **Channel B:** body section name + what to include (brief description). Full template lives in the owning workflow skill.
- The agent defines WHAT the output looks like. The skill defines HOW to construct it (command syntax, full templates).

**`<boundaries>`** — Agent-specific red flags and failure rationalizations.

- Only constraints that apply specifically to THIS agent. Common red flags live in `r-pipeline-protocol`.
- Optional: failure rationalizations table (common self-deception patterns with correct responses).

**`<examples>`** — 2-3 abstract, principle-based examples.

- Mix of good and bad examples.
- Encode **reasoning patterns**, not action sequences. Abstract examples generalize better than specific ones and cost fewer tokens.
- Each example: 2-3 lines describing the principle in action, not specific task IDs or filenames.

### Optional Sections

**`<pipeline_position>`** — Pipeline agents (T2) only.

Compact transition table showing what triggers this agent and what it produces:

```markdown
| Trigger | From → To | Condition |
|---------|-----------|-----------|
| Done    | build → verify | implementation and focused evidence complete |
| Reject  | build → shape  | scope, AC, or dependency premise is wrong |
```

**`<agents>`** — Only agents that delegate to sub-agents.

```markdown
| Agent | When | Example |
|-------|------|---------|
| shaper-challenger | AC quality and scope review during shaping | `Challenge Shape: task_id=42, proposed_verdict=APPROVED, reasoning="..."` |
```

The `<agents>` table must list every agent in the frontmatter `agents:` array and vice versa. This is the **only** source of subagent knowledge at nesting depth ≥2 (VS Code does not inject the agents catalog at that depth). A CI validation script enforces alignment — see `.owlbear/scripts/validate_agents.py`.

### Forbidden Content

Agent files must NOT contain:

- Step-by-step procedures → belongs in the owning workflow skill
- Channel A/B protocol definition → belongs in `r-pipeline-protocol`
- Commit discipline → belongs in `r-project-standards`
- Shared red flags that apply to multiple agents → belongs in `r-pipeline-protocol`
- Command templates (MCP kanban tools, git) → belongs in the skill's output template
- Verbatim copies of skill checklist content → reference the skill instead
- Rules that apply identically to 2+ agents → belongs in a shared location

### Nesting Depth & DMI

VS Code has a limitation: at nesting depth ≥2 (3rd-level subagents), agents with `disable-model-invocation: true` cannot be resolved. Additionally, the `<agents>` catalog from the VS Code system prompt is not injected at depth ≥2 — agents rely solely on their own `<agents>` body section to know what subagents are available.

**Rules:**

1. **ND3 agents** (agents callable at nesting depth ≥3) must have `disable-model-invocation: false`.
2. **ND1/ND2 agents** keep `disable-model-invocation: true` (default for pipeline agents).
3. **Every dispatching agent** must have an `<agents>` body section listing all agents from its frontmatter `agents:` array — this is the only discovery mechanism at depth ≥2.
4. ND3 agents are tagged with `(ND3)` in their `description` field for identification.

**Current ND3 agents:** shaper-challenger, builder-challenger, verifier-challenger, ideation-critic.

Caller inventory is intentionally not duplicated here. The source of truth for caller → subagent relationships is each caller's frontmatter `agents:` array plus its `<agents>` body table; see [share/WIRING.md](../../WIRING.md) for the inverse ecosystem map. When adding a new caller, update the caller's agent file. When adding a new ND3 agent, set `disable-model-invocation: false`, tag the description with `(ND3)`, and add it to this list.

Built-in agents (`Explore`, `General Purpose`) resolve at any depth regardless of settings.

## Skill File Structure (SKILL.md)

Skills define **procedures, protocol, or domain knowledge**. They live in `share/skills/{prefix}-{name}/SKILL.md`.

### Frontmatter (YAML)

```yaml
---
name: {prefix}-{skill-name}
description: "{Category}: {one-line description}"
user-invocable: {true|false}
---
```

- `name` — **required.** Must match the parent directory name exactly. Lowercase, hyphens for spaces. VS Code uses this for discovery and slash-command routing.
- `description` — **required.** Starts with category label (`Workflow:`, `Rules:`, or `Handbook:`).
- `user-invocable` — **required.** Default `false` for pipeline/internal skills. Set `true` only for skills users invoke directly via `/` menu (e.g., `h-excalidraw-diagram`).

### Three Categories

| Prefix | Category | Description starts with | Purpose |
|--------|----------|------------------------|---------|
| `w-` | Workflow | "Workflow:" | Step-by-step procedures for any agent or user-invokable process |
| `r-` | Rules | "Rules:" | Shared conventions governing behavior |
| `h-` | Handbook | "Handbook:" | Domain-specific knowledge consulted situationally |

### Naming Grammar

- **Agent names** are **role nouns** or role compounds (builder, verifier, builder-challenger).
- **Skill names** are **domain-action compounds** — use verbs/actions, not plural nouns. E.g., `test-curation` not `test-curations`, `decision-routing` not `decision-requests`, `task-decomposition` not `task-workflow`.
- The `w-` prefix replaces the word "workflow" — don't use both (e.g., `w-test-curation` not `w-test-curation-workflow`).

### Workflow Skill Structure

```markdown
## Step 0 — Setup
Read `r-pipeline-protocol` skill if not already loaded.
Claim the task (pipeline-protocol → Task Setup → Claiming).

## Step 1 — {first unique action}
{Procedure unique to this skill}

## Step N-1 — Deliverables
Commit per r-project-standards → Commit Discipline.
{Skill-specific: which files, which commit type prefix}

## Step N — Advance
{Status transition + claim release}

## Output Template
{Full Channel B template. The template's STRUCTURE forces evidence — if a column
exists for "Evidence," the agent must find evidence to fill it.}

## Known Pitfalls
- {pitfall}: {avoidance}
```

**Step 0 applies to:** Workflow skills where the agent claims and processes a task, such as `w-mem-curation` and `w-task-decomposition`.

**No Step 0:** w-orchestration (own dispatch pattern), w-test-curation (suite-scoped inventory, not task-scoped).

**Workflow skills must NOT contain:**

- Claiming/commit boilerplate (reference `r-pipeline-protocol` and `r-project-standards`)
- MCP kanban tools Commands table (commands appear inline where used)
- Channel A/B protocol explanation (that's `r-pipeline-protocol`)

### Rules Skill Structure

Rules skills define shared conventions referenced by multiple agents. Organized by topic with tables for structured reference.

### Handbook Skill Structure

Handbook skills carry domain-specific knowledge. Organized by domain topics with recipes and patterns.

## Instruction File Types

Instruction files (`.instructions.md`) serve two distinct roles. Knowing which role a file plays determines its permitted content.

### Stubs — Safety Nets

Instruction stubs are **safety nets** — minimal files that catch agents working in a domain without having loaded the relevant skill.

Format:

```markdown
---
applyTo: "{glob_pattern}"
description: "{domain} conventions for this workspace"
---

For project-specific {domain} conventions, read the `{skill_name}` skill.
```

A stub is justified when there is a realistic scenario where an agent edits files matching the glob WITHOUT having already loaded the skill from its critical_rules or workflow.

Current stubs:

| File | applyTo | Points to |
|------|---------|----------|
| `python.instructions.md` | `"**/*.py"` | `h-python-conventions` |
| `frontend.instructions.md` | `"**/*.tsx,**/*.jsx,**/*.vue,**/*.svelte,**/*.css,**/*.scss"` | `h-frontend-conventions` |
| `research-docs.instructions.md` | `".owlbear/research/*.md"` | `w-research` |
| `agent-ecosystem.instructions.md` | `"share/agents/**,share/skills/**,share/instructions/**,share/prompts/**,.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**"` | `share/README.md` + `h-agent-structure` |
| `doc-standards.instructions.md` | `"README.md,README-consumer.md,SECURITY.md,serve/*/README.md,share/README.md,setup/*.md"` | `r-doc-standards` |

### Authority Files — Embedded Rules

| Use authority `.instructions.md` when | Rationale |
|---------------------------------------|-----------|
| Rules are universal or near-universal | No single skill boundary fits |
| Content is always needed for the target scope | Loading a skill on every interaction would be wasteful |
| `applyTo` scope is broad enough that no single skill owns the content | Authority files cross skill boundaries |

Current authority files:

| File | applyTo | Role |
|------|---------|------|
| `pipeline-agents.instructions.md` | `share/skills/r-pipeline-protocol/**` | Channel B protocol and per-agent section-header mapping (pipeline-scoped) |
| `owlbear-system.instructions.md` | `**` | System instructions — decision heuristics, system awareness, memory governance, and operational fundamentals (universal) |

| Rule | Value |
|------|-------|
| Naming | Hyphenated lowercase; generic cross-cutting names (not domain-specific like `python.instructions.md`) |
| `applyTo` scope | Domain-scoped: specific directory tree. Universal: `**`. Stub: file-extension pattern (`**/*.py`). |
| `copilot-instructions.md` | Not an instruction file — separate loading mechanism, not governed by `applyTo`. See Loading Model. |

## Formatting Rules

- Agent file body uses **XML-style tags** (`<persona>`, `<critical_rules>`, etc.) for clear section delimitation.
- Skill files use **markdown headers** (`##`, `###`).
- No backtick wrappers around `.agent.md` or `.instructions.md` content — the `read_file` tool adds fencing that is NOT part of the file.
- Empty lines around enumerations (bullet lists, numbered lists) and before closing XML tags. Without this, markdown parsers treat the next line as list continuation.
