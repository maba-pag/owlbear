---
name: h-agent-structure
description: "Handbook: Structural standards for OwlBear agent files, skill files, and instruction stubs"
user-invocable: false
---

# Agent Ecosystem Structure

Structural model for all OwlBear agent, skill, and instruction files. Single source of truth for what belongs where.

## Loading Model

Content reaches agents through four mechanisms, ordered by reliability:

| Mechanism | Trigger | Reliability | Use for |
|-----------|---------|-------------|---------|
| `copilot-instructions.md` | Every interaction | Guaranteed | Universal foundation (80%+ of agents need it) |
| Agent file body | Agent invocation | Guaranteed | Identity, constraints, communication format |
| Skills (SKILL.md) | Explicit `read_file` or auto-load by relevance | High | Procedures, protocol, domain knowledge |
| Instruction stubs (.instructions.md) | `applyTo` glob matches a touched file | Medium | Safety nets — pointers to skills |

Pipeline agents load `r-pipeline-protocol` and `r-project-standards` from their `<critical_rules>` reference. This is deterministic because the agent body always loads.

### File Type Selection

| File type | Choose when |
|-----------|------------|
| `.prompt.md` | User-facing one-shot command, invoked explicitly. Default for user commands. |
| `SKILL.md` | Reusable domain knowledge that auto-loads by relevance, or needs co-located resources. |
| `.agent.md` | Long-lived role with persistent behavior: tool restrictions, model preferences, handoff boundaries, hooks. |

Default: user-facing one-shot commands use `.prompt.md` unless auto-loading or co-located resources are needed.

## Agent Tiers

| Tier | Agents | Pipeline protocol needed? |
|------|--------|--------------------------|
| T1 — Orchestrator | orchestrator, ideator | From agent critical_rules |
| T2 — Pipeline | researcher, architect, test-writer, builder, reviewer, doc-writer, auditor | Yes — critical_rules reference |
| T3 — Support | scribe, planner, curator | If applicable — from critical_rules |
| T4 — Tools | challenger, code-reader, Explore, fix-attempt, quality-runner, ideation-architect, ideation-critic, ideation-data, ideation-enduser, ideation-pragmatist, ideation-security | Not needed |

## Principles

### Rule of Two

A fact appears in at most **two** places:

1. **Source of truth** — the most specific location (skill > protocol > copilot-instructions)
2. **One inline reference** — a 1-line summary or pointer in the consumer

If a rule applies to 2+ agents identically, it belongs in `r-pipeline-protocol`, `r-project-standards`, or `copilot-instructions.md` — not repeated in each agent.

### 80% Rule

Content in `copilot-instructions.md` must benefit ≥ 80% of agents. Below that threshold, it goes to a more specific skill or `r-pipeline-protocol`.

### Implicit Encoding

Every section in an agent file can carry more than its primary function:

| Section | Primary function | Implicit function |
|---------|-----------------|-------------------|
| `<persona>` | Identity | Behavioral rules through emotional framing |
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
- `disable-model-invocation: true` — prevents direct invocation by other models. The orchestrator's explicit `agents` array overrides this. Use for all pipeline agents (T2-T3).

### Required Sections

**`<persona>`** — 2-3 short paragraphs defining role, expertise, and attitude.

Design process:

1. List the 5 most important behaviors for this agent
2. Find a real-world scenario where those behaviors arise naturally from the situation's constraints
3. Frame the persona in that scenario — the emotional stakes should make the desired behaviors feel inevitable, not imposed
4. Cross-check: which explicit rules in `<critical_rules>` can now be removed because the persona already implies them?

The persona is not decoration — it is an **implicit rule encoder**. A well-chosen emotional framing activates behavioral patterns that would otherwise cost explicit rule tokens.

**`<critical_rules>`** — 3-7 non-negotiable constraints, ordered by importance.

- First item: "**Follow the `{primary_skill}` skill** for {1-line summary}."
- Pipeline agents (T1-T3): second item references `r-pipeline-protocol` for shared conventions.
- Every remaining rule must be **unique** to this agent. If the same rule would appear in 2+ agents, it belongs in `r-pipeline-protocol` or `copilot-instructions.md`.
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
| Success | done → archived | confidence ≥ .95 |
| Reject  | done → review | fixable gaps |
```

**`<subagents>`** — Only agents that delegate to sub-agents.

```markdown
| Agent | When | Example |
|-------|------|---------|
| scribe | Decision point requiring user input | `Scribe: task_id=42, mode=check-or-create, concern="..."` |
```

### Forbidden Content

Agent files must NOT contain:

- Step-by-step procedures → belongs in the owning workflow skill
- Channel A/B protocol definition → belongs in `r-pipeline-protocol`
- Commit discipline → belongs in `r-project-standards`
- Shared red flags that apply to multiple agents → belongs in `r-pipeline-protocol`
- Command templates (MCP kanban tools, git) → belongs in the skill's output template
- Verbatim copies of skill checklist content → reference the skill instead
- Rules that apply identically to 2+ agents → belongs in a shared location

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

- **Agent names** are **role nouns** (reviewer, builder, auditor).
- **Skill names** are **domain-action compounds** — use verbs/actions, not plural nouns. E.g., `code-review` not `code-reviews`, `decision-routing` not `decision-requests`, `tdd-green` not `tdd-workflow`.
- The `w-` prefix replaces the word "workflow" — don't use both (e.g., `w-research` not `w-research-workflow`).

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

**Step 0 applies to:** All workflow skills where the agent claims and processes a task (w-tdd-red, w-tdd-green, w-code-review, w-doc-update, w-task-verification, w-arch-review, w-research, w-mem-curation).

**Step 0 without claiming:** w-task-decomposition (creates tasks, doesn't claim one).

**No Step 0:** w-orchestration (this doesn't follow the pipeline lifecycle — it has its own dispatch pattern).

**Workflow skills must NOT contain:**

- Claiming/commit boilerplate (reference `r-pipeline-protocol` and `r-project-standards`)
- MCP kanban tools Commands table (commands appear inline where used)
- Channel A/B protocol explanation (that's `r-pipeline-protocol`)

### Rules Skill Structure

Rules skills define shared conventions referenced by multiple agents. Organized by topic with tables for structured reference.

### Handbook Skill Structure

Handbook skills carry domain-specific knowledge. Organized by domain topics with recipes and patterns.

## Instruction Stub Format (.instructions.md)

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
|------|---------|-----------|
| `python.instructions.md` | `"**/*.py"` | `h-python-conventions` |
| `frontend.instructions.md` | `"**/*.tsx,**/*.jsx,**/*.vue,**/*.svelte,**/*.css,**/*.scss"` | `h-frontend-conventions` |
| `research-docs.instructions.md` | `".owlbear/research/*.md"` | `w-research` |
| `agents-and-skills.instructions.md` | `"share/agents/**,share/skills/**"` | `h-agent-structure` |

## Formatting Rules

- Agent file body uses **XML-style tags** (`<persona>`, `<critical_rules>`, etc.) for clear section delimitation.
- Skill files use **markdown headers** (`##`, `###`).
- No backtick wrappers around `.agent.md` or `.instructions.md` content — the `read_file` tool adds fencing that is NOT part of the file.
- Empty lines around enumerations (bullet lists, numbered lists) and before closing XML tags. Without this, markdown parsers treat the next line as list continuation.
