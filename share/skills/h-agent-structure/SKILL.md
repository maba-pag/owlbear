---
name: h-agent-structure
description: "Handbook: Structural standards for shared agent files, skill files, and instruction stubs"
user-invocable: false
---

# Agent Ecosystem Structure

Structural model for all shared agent, skill, and instruction files. Single source of truth for what belongs where.

## Foundation

Use [share/README.md](../../README.md) for the effective instruction stack, loading tiers, owning
artifact selection, and maintenance workflow. This skill is the creation-time structural authority:
file schemas, required sections, naming grammar, extraction criteria, and anti-patterns.

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

`build-reviewer` qualifies through its independent committed-packet review, distinct model, and hard
read-only boundary.

## Principles

### Rule of Two

A fact appears in at most **two** places:

1. **Source of truth** — the most specific shared skill, protocol, instruction, or project-fact source
2. **One inline reference** — a 1-line summary or pointer in the consumer

If a rule applies to 2+ agents identically, it belongs in a shared skill, protocol, or authority
instruction, not in local project instructions and not repeated in each agent.

### Runtime Relevance

Include only information the role can act on in the current invocation. State the current rule, not
the migration story behind it. Future switches, superseded behavior, prior failures, and decision
rationale belong in planning authority, task history, or tests unless they change a current action.

Prefer one precise rule over a rationale plus examples plus repeated warnings. Keep edge cases only
when they change routing, mutation, safety, or evidence requirements.

An instruction that requires a tool mutation must name the tool, required arguments, and any
outcome-specific fallback. Never shorten an executable procedure to an ambiguous verb such as
"release", "advance", or "record" unless another loaded authority defines that exact operation.

### Implicit Encoding

Agent sections also steer behavior implicitly:

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

- `user-invocable: false` — hides from the `/` slash-command menu. Use for internal agents/skills that should only be dispatched by an owning workflow.
- `disable-model-invocation: true` — prevents autonomous invocation by other models. Use for L1/L2 delivery agents. **Must be `false` for ND3 agents** (agents that may be called at nesting depth ≥3), because VS Code does not resolve agents with `true` at depth ≥2. See § Nesting Depth & DMI below.

### Required Sections

**`<persona>`** — Usually 1-3 short paragraphs defining role, expertise, and attitude. Use only the
paragraphs needed to encode the role's distinct behavioral frame; do not pad a narrow role to meet a
count.

Frame a real scenario whose constraints imply the role's most important behaviors. Remove explicit
rules only when that frame makes the behavior reliably clear; persona text is not decoration.

**`<required_reading>`** — Skills the agent must `read_file` at session start.

List direct skills needed in 90%+ of sessions. Leave situational skills on-demand and let each
required skill load its own transitive dependencies.

```markdown
<required_reading>

- `{primary_skill}` — primary workflow or domain authority
- `r-challenger-protocol` — advisory evidence and caller routing when this role challenges or invokes a reviewer

</required_reading>
```

**`<critical_rules>`** — The smallest complete set of non-negotiable constraints, ordered by
importance; 3-7 is the normal range. Exceed it only when every additional rule is distinct,
agent-specific, and would lose a necessary constraint if combined or moved to shared authority.

- First item: "**Follow the `{primary_skill}` skill** for {1-line summary}."
- Challengers and their callers reference `r-challenger-protocol` for advisory evidence and routing.
- Every remaining rule must be **unique** to this agent. If the same rule would appear in 2+ agents,
  it belongs in a shared skill, protocol, or authority instruction.
- Each rule must be **actionable** — it can be verified as followed or violated.

**`<output_format>`** — The agent's communication interface.

- Dispatched native agents define exact structured dispositions that match the owning lifecycle
  operation or fail-closed route.
- User-facing agents define their durable authority mutation boundary and concise human summary.
- The agent defines WHAT the output looks like. The skill defines HOW to construct it (command syntax, full templates).

**`<boundaries>`** — Agent-specific red flags and failure rationalizations.

- Only constraints that apply specifically to THIS agent. Common reviewer red flags live in
  `r-challenger-protocol`.
- Optional: failure rationalizations table (common self-deception patterns with correct responses).

**`<examples>`** — Usually 2-3 abstract, principle-based examples. Add more only when each resolves a
distinct, likely boundary confusion that the existing examples do not cover.

- Mix of good and bad examples.
- Encode **reasoning patterns**, not action sequences. Abstract examples generalize better than specific ones and cost fewer tokens.
- Each example: 2-3 lines describing the principle in action, not specific task IDs or filenames.

### Optional Sections

**`<pipeline_position>`** — Optional for roles whose local threshold is clearer as a transition table.

Compact transition table showing what triggers this agent and what it produces:

```markdown
| Trigger | From → To | Condition |
|---------|-----------|-----------|
| Success | build job → build receipt | committed packet and exact-commit review pass |
| Re-entry | build job → Specification | admitted packet cannot own the finding |
```

**`<agents>`** — Only agents that delegate to sub-agents.

```markdown
| Agent | When | Example |
|-------|------|---------|
| planner-challenger | Packet DAG review before plan success | `Challenge Plan: change_id=cache, job_id=42, target=DN-004, packets=[...]` |
```

The `<agents>` table must list every agent in the frontmatter `agents:` array and vice versa. This is the **only** source of subagent knowledge at nesting depth ≥2 (VS Code does not inject the agents catalog at that depth). The `validate-agents` pre-commit hook enforces alignment through `.owlbear/scripts/validate_agents.py`.

### Forbidden Content

Agent files must NOT contain:

- Step-by-step procedures → belongs in the owning workflow skill
- Commit discipline → belongs in `r-workspace-governance`
- Command templates (MCP kanban tools, git) → belongs in the skill's output template
- Verbatim copies of skill checklist content → reference the skill instead
- Shared protocols, red flags, or rules → belong in the matching shared skill

### Nesting Depth & DMI

**Rules:**

1. **ND3 agents** (callable at nesting depth ≥3) must have `disable-model-invocation: false`; VS Code
  cannot resolve them otherwise.
2. **ND1/ND2 agents** keep `disable-model-invocation: true` (default for delivery agents).
3. **Every dispatching agent** must mirror its frontmatter `agents:` array in `<agents>`; the global
  agent catalog is unavailable at depth ≥2.
4. ND3 agents are tagged with `(ND3)` in their `description` field for identification.

**Current ND3 agents:** build-reviewer, planner-challenger.

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

- **Agent names** are **role nouns** or role compounds (builder, claim-arbiter, build-reviewer).
- **Skill names** are **domain-action compounds** — use verbs/actions, not plural nouns. E.g., `test-curation` not `test-curations`, `decision-routing` not `decision-requests`, `task-decomposition` not `task-workflow`.
- The `w-` prefix replaces the word "workflow" — don't use both (e.g., `w-test-curation` not `w-test-curation-workflow`).

### Workflow Skill Structure

```markdown
## Step 0 — Setup
Validate the supplied authority and immutable execution identity before mutation.

## Step 1 — {first unique action}
{Procedure unique to this skill}

## Step N-1 — Deliverables
Commit per `r-workspace-governance` → Commit Discipline.
{Skill-specific: which files, which commit type prefix}

## Step N — Advance
{Status transition + claim release}

## Output Template
{Full Channel B template with fields that force required evidence.}

## Known Pitfalls
- {pitfall}: {avoidance}
```

**Step 0 applies to:** Workflows that consume an engine-started job or immutable candidate.

**No Step 0:** w-orchestration (own dispatch pattern), w-test-curation (suite-scoped inventory, not task-scoped).

**Workflow skills must NOT contain:**

- Commit boilerplate (reference `r-workspace-governance`)
- MCP kanban tools Commands table (commands appear inline where used)
- Generic lifecycle tool syntax (the owning workflow or runtime contract defines it)

### Rules Skill Structure

Rules skills define shared conventions referenced by multiple agents. Organized by topic with tables for structured reference.

### Handbook Skill Structure

Handbook skills carry domain-specific knowledge. Organized by domain topics with recipes and patterns.

## Instruction File Types

Instruction files (`.instructions.md`) are either stubs or authorities.

### Stubs — Safety Nets

Instruction stubs are minimal safety nets for agents that reach a domain without its skill loaded.

Format:

```markdown
---
applyTo: "{glob_pattern}"
description: "{domain} conventions for this workspace"
---

For project-specific {domain} conventions, read the `{skill_name}` skill.
```

A stub is justified when there is a realistic scenario where an agent edits files matching the glob WITHOUT having already loaded the skill from its critical_rules or workflow.

### Authority Files — Embedded Rules

| Use authority `.instructions.md` when | Rationale |
|---------------------------------------|-----------|
| Rules are universal or near-universal | No single skill boundary fits |
| Content is always needed for the target scope | Loading a skill on every interaction would be wasteful |
| `applyTo` scope is broad enough that no single skill owns the content | Authority files cross skill boundaries |

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
