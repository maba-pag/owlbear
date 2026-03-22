---
description: "Comprehensive audit of the OwlBear agent ecosystem. It encodes the taxonomy, structural expectations, and verification criteria refined over multiple audit iterations"
---

# Agent Ecosystem Audit & Remediation

You are auditing the OwlBear multi-agent development pipeline — a set of VS Code Copilot
agent definitions (.agent.md), skills (SKILL.md), and shared instruction files
(.instructions.md) that together form an autonomous kanban-driven development system.

## What you're auditing

Read ALL of these files before forming any conclusions:

- `.github/instructions/*.instructions.md` — all shared instruction files
- `.github/agents/*.agent.md` — all agent files
- `.github/skills/*/SKILL.md` — all skill files
- `.github/copilot-instructions.md` — project-wide copilot instructions

Use `file_search` to discover the current set. Do not assume a fixed count — agents,
skills, and instructions may be added or removed between audits.

## Taxonomy: What belongs where

This is the critical framework. Every piece of content must live in exactly one place:

### Agent files (.agent.md) — WHO the agent is

Agent files define **identity, authority, and boundaries**. They answer: "Who am I?
What's my role? What can I touch? How do I communicate?"

**Must contain:**

- `<persona>` — 3-5 sentences defining role, expertise, and attitude
- `<critical_rules>` — 3-7 non-negotiable rules SPECIFIC to this agent (not duplicated from shared instructions)
- `<multi_agent_context>` — pipeline position (with canonical pipeline string, own position bolded), predecessor/successor relationships
- `<workflow>` — "Follow the `{skill-name}` skill." + 1-line summary. NOT the procedure itself.
- `<output_format>` — Channel A signal format and Channel B body structure. Agent-specific formats only — the protocol itself is in agent-common.
- `<boundaries>` — Agent-SPECIFIC red flags. Common red flags live in agent-common.
- `<examples>` — 2-3 complete good/bad examples showing realistic signal output
- `<self_critique>` — Reference to skill checklist + 3-5 quick agent-specific checks. NOT a verbatim copy of the skill checklist.

**Must NOT contain:**

- Step-by-step procedures (→ belongs in skills)
- Generic rules that apply to all agents (→ belongs in agent-common.instructions.md)
- Verbatim copies of skill checklists (→ reference the skill + add quick checks)
- Protocol definitions (→ agent-common)

### Skill files (SKILL.md) — WHAT the agent does (procedures)

Skills define **step-by-step procedures**. They answer: "Given a task, what exact
steps do I follow?"

**Must contain:**

- Numbered steps with explicit commands
- Decision trees (if X → do A, else → do B)
- Output templates and formatting rules
- Known pitfalls and edge cases for THIS procedure
- Self-critique checklists specific to the procedure

**Must NOT contain:**

- Agent persona or identity (→ agent file)
- Pipeline position or handoff rules (→ agent file)
- Cross-agent rules (→ instructions files)

**Relationship:** One agent may reference multiple skills. One skill may be used by
multiple agents. The agent file says "Follow the X skill" — the skill contains the
procedure.

### Instruction files (.instructions.md) — shared rules and conventions

Instructions define **rules that apply across agents or across the codebase**.

**Key concern: loading reliability.** Instruction files only load when the agent
interacts with files matching their `applyTo` glob. This means:

- An instruction file with `applyTo: "**/*.py"` does NOT load when agents interact
  only via terminal commands
- An instruction file with `applyTo: "docs/*.md"` does NOT load until the agent
  edits a doc file, which may be late in the workflow
- For critical rules that agents need early, consider: converting to a skill (always
  available via `read_file`), adding key rules to the agent file, or ensuring the
  `applyTo` pattern is broad enough

For each instruction file, verify: will the agents that need these rules actually
trigger the `applyTo` glob during their normal workflow?

**Deduplication principle:** If a rule appears in 2+ agent files, it should instead
be in an instruction file or skill with agents referencing it. Exception: critical
operational values (like confidence thresholds) can appear BOTH in the centralized source
of truth AND inline in agents for quick reference.

## The canonical pipeline

```
ideation → (researcher) → backlog → (architect) → todo → (test-writer RED) → in-progress → (builder GREEN) → review → (reviewer) → docs → (writer) → done → (auditor) → archived
```

Every agent file that mentions the pipeline must use this exact string (with its own
position bolded).

**Agent-status ownership:** Each pipeline agent gates exactly one status transition.
Verify that: (a) every dispatchable status has an assigned agent, (b) no two agents
move the same transition, (c) non-pipeline agents (orchestrator, planner, curator,
kanban-planner) never run `kanban-md move`.

**Non-implementation exceptions:** Some task types (research, docs, config) skip the
test-writer. Verify the dispatch mapping explicitly encodes these exceptions in a table
(not just inline prose).

## The orchestrator's role

The orchestrator is a mechanical dispatch loop. It:

1. Invokes the planner to get a DISPATCH_LIST
2. Dispatches subagents in parallel (one task per subagent call)
3. Re-plans from fresh board state each cycle

**Orchestrator does NOT:** run kanban commands, read task bodies, parse Channel A
signals for routing, or make quality judgments.

**Orchestrator tools:** only `[agent, vscode/askQuestions, vscode/memory, todo]`.

## Two-channel communication protocol

Defined in agent-common.instructions.md:

- **Channel A (routing signal):** Max 2 lines returned to caller. Diagnostic only.
- **Channel B (task body):** Rich context appended to kanban task. Downstream agents
  read this. Orchestrator never reads this.

## Rejection blocking convention

Routine rejections (reviewer FAIL, writer reject-to-review, auditor reject-to-review)
use simple status movement (`--status {target} --release`) without `--block`. The task
auto-redispatches on the planner's next cycle. Rejection details live in the Channel B
task body (Review Evidence, Docs Gate, Audit sections).

`--block` is reserved for situations that require human intervention before redispatch:

- **Auditor → backlog**: fundamental quality issue needing redesign
- **Architect → ideation**: AC needs rework
- **Handoff**: waiting on user decision or external action
- **Decision requests**: blocked pending async user decision
- **Stale tasks**: blocked for triage

Verify that no routine rejection command uses `--block`.

## Defense-in-depth model

Three lines of defense (documented in agent-common):

1. **1st line** (test-writer + builder) — "Did I do it right?"
2. **2nd line** (reviewer) — "Did they do it right?"
3. **3rd line** (auditor) — "Was the ideated intent achieved?"

## Tool availability

Some tools exist in OwlBear's PydanticAI runtime but are NOT available in VS Code
Copilot agents (e.g., knowledge graph tools). References to unavailable tools should
be deactivated (HTML comments or explicit notices). Check all tool references against
what VS Code actually provides.

## What to look for

Analyze every file for these categories of issues:

### 1. Critical pipeline breaks

- Agent has wrong tools for its role (orchestrator with terminal, planner with agent tool)
- Missing dispatch paths (task gets stuck because no agent picks it up)
- Non-implementation tasks have no explicit dispatch exception in the mapping table
- Double-moves (two agents move the same transition)
- Signals that don't match what the receiving agent expects
- References to tools not available in VS Code agent mode

### 2. Design contradictions

- Two files say opposite things about the same concept
- Agent claims to do X but its skill says Y
- Instruction file prescribes a different lifecycle than the corresponding skill
- Instruction file's `applyTo` pattern means it loads too late or not at all for its
  target audience

### 3. Content placement violations

- Agent self-critique is a verbatim copy of a skill checklist (should reference + quick checks)
- Agent file contains full step-by-step procedure (should be in a skill)
- Agent file exceeds ~200 lines (likely contains procedure content)
- Same rule appears in 2+ agents without being in a shared file
- Instruction file contains rules that only one agent uses (should be in that agent)

### 4. Consistency checks

- Pipeline string differs between agents
- Confidence thresholds differ between agent and agent-common
- kanban-md path inconsistencies (`kanban\kanban-md.exe` is canonical)
- Dispatch mapping table vs narrative text disagree
- Channel A signal format in agent doesn't match the per-agent table in agent-common
- `--block` used in routine rejection commands (reviewer FAIL, writer reject, auditor
  reject-to-review) — these should use simple status movement only

### 5. Structural issues

- Skill exists but no agent references it (orphan skill)
- Agent references a skill that doesn't exist (broken reference)
- Missing required sections in agent files (persona, critical_rules, examples, etc.)

## Output format

Produce your analysis in this structure:

```
## FINDINGS

### Critical Issues (C1, C2, ...)
For each: What's wrong, which files, what the correct behavior should be.

### Design Contradictions (D1, D2, ...)
For each: The two conflicting statements, which files, which one is correct.

### Content Placement / Duplication (P1, P2, ...)
For each: What's misplaced or duplicated, where it is, where it should be.

### Inconsistencies (I1, I2, ...)
For each: What's inconsistent, where, what the canonical version should be.

### Structural (S1, S2, ...)
For each: What's structurally wrong, what the target structure should be.

## FINDINGS CHECKLIST
- [ ] **{ID}** {one-line description of what "fixed" looks like}

## REMEDIATION PLAN

### Phase 1: Critical Pipeline Fixes (C*)
### Phase 2: Design Contradiction Resolution (D*)
### Phase 3: Content Placement & Consistency Fixes (P*, I*)
### Phase 4: Structural Improvements (S*)

For each step:
- What: one-sentence description
- Files to modify
- Exact changes (include code blocks for non-trivial changes)
- Dependencies on other steps

## VERIFICATION PLAN
1. Trace a hypothetical implementation task through the full pipeline
2. Trace a hypothetical non-implementation task (research, config)
3. Grep for orphaned references (removed agents, deprecated tools)
4. Verify all agent self-critiques reference skills (not duplicate them)
5. Re-verify every finding in the checklist
```

## Process instructions

1. **Read ALL files first.** Do not start forming conclusions until you've read every
   agent, skill, and instruction file. Use subagents for parallel reading if needed.
2. **Save your plan.** Write findings + remediation plan to `/memories/session/plan.md`.
3. **Ask before implementing.** Present the plan to the user. Wait for approval.
4. **Implement phase by phase.** Complete all steps in Phase 1 before Phase 2.
5. **Verify after each phase.** Run the relevant verification checks.
6. **Gap check at the end.** Re-read the FINDINGS CHECKLIST and verify every item.
