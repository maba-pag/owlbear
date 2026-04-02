---
description: "Comprehensive audit of the OwlBear agent ecosystem. It encodes the taxonomy, structural expectations, and verification criteria refined over multiple audit iterations"
---

# Agent Ecosystem Audit & Remediation

You are auditing the OwlBear multi-agent development pipeline — a set of VS Code Copilot
agent definitions (.agent.md), skills (SKILL.md), and shared instruction files
(.instructions.md) that together form an autonomous kanban-driven development system.

## What you're auditing

Read ALL of these files before forming any conclusions:

- `instructions/*.instructions.md` — all shared instruction files
- `agents/*.agent.md` — all agent files
- `skills/*/SKILL.md` — all skill files
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
- optional, only if beneficial: `<multi_agent_context>` — pipeline position, predecessor/successor relationships
- `<workflow>` — "Follow the `{skill-name}` skill." + 1-line summary. NOT the procedure itself.
- `<output_format>` — Channel A signal format and Channel B body structure. Agent-specific formats only — the protocol itself is in agent-common.
- `<boundaries>` — Agent-SPECIFIC red flags. Common red flags live in agent-common.
- `<examples>` — 2-3 complete good/bad examples showing realistic signal output
- `<self_critique>` — Reference to skill checklist + 3-5 quick agent-specific checks. NOT a verbatim copy of the skill checklist. (not for orchestrator)

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

**Agent-status ownership:** Each pipeline agent gates exactly one status transition.
Verify that: (a) every dispatchable status has an assigned agent, (b) no two agents
move the same transition, (c) non-pipeline agents (orchestrator, planner, curator,
kanban-planner) never run `kanban-md move`.

<!-- NON_IMPL_TAGS: Authoritative list at skills/dispatch-planning/SKILL.md
     (agent dispatch table). Update there first, then sync here. -->
**Non-implementation tasks:** Tasks tagged `research`, `docs`, `type:config`,
`type:docs`, `test`, `type:test`, `agent`, or `quality` still flow through the full
pipeline. The test-writer and builder recognize these tags and pass through without
writing tests or code (see tdd-red skill Step 1a, tdd-workflow skill Step 1a). Verify
the dispatch mapping documents this pass-through behavior in its table.

## The orchestrator's role

The orchestrator is a mechanical dispatch loop. It:

1. Invokes the planner to get a DISPATCH_LIST
2. Dispatches subagents in parallel (one task per subagent call)
3. Re-plans from fresh board state each cycle

**Orchestrator does NOT:** run kanban commands, read task bodies, parse Channel A
signals for routing, or make quality judgments.

## Two-channel communication protocol

Defined in agent-common.instructions.md:

- **Channel A (routing signal):** Max 2 lines returned to caller. Diagnostic only.
- **Channel B (task body):** Rich context appended to kanban task. Downstream agents
  read this. Orchestrator never reads this.

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
- Non-implementation task pass-through not documented in dispatch mapping table
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

### 6. Low signal-to-noise ratio

Every token in an agent/skill/instruction file competes for context window space.
Content that does not directly help the agent perform its task is noise.

- Rationale or justification for rules the agent must simply follow (the "why" behind
  a rule has no operational value)
- Prose that restates information already present in another section or file
- Filler phrases that add no decision-making value
- Verbose phrasing where a terse equivalent carries the same meaning
- Background context useful for human documentation but not for task execution (e.g.,
  explaining why a compatibility rule exists when the agent only needs the rule itself)

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

### SNR Issues (N1, N2, ...)
For each: What's noisy, which file and section, suggested terse replacement or deletion.

## FINDINGS CHECKLIST
- [ ] **{ID}** {one-line description of what "fixed" looks like}

## REMEDIATION PLAN

### Phase 1: Critical Pipeline Fixes (C*)
### Phase 2: Design Contradiction Resolution (D*)
### Phase 3: Content Placement & Consistency Fixes (P*, I*)
### Phase 4: Structural Improvements (S*)
### Phase 5: SNR Reduction (N*)

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
6. Spot-check 3 files for low-SNR content (rationale prose, restated rules, filler)
```

## Process instructions

1. **Read ALL files first.** Do not start forming conclusions until you've read every
   agent, skill, and instruction file. Use subagents for parallel reading if needed.
2. **Save your plan.** Write findings + remediation plan to `/memories/session/plan.md`.
3. **Present findings for approval.** Walk through each finding using the Finding
   Presentation Protocol below. Do NOT batch-present — present one at a time.
4. **Implement phase by phase.** Complete all steps in Phase 1 before Phase 2.
5. **Commit after each fix.** After implementing a fix, stage the changed files and
   commit with format: `chore: audit {ID} — {one-line description}`. Do not push.
6. **Verify after each fix.** Run a quick grep/read check to confirm the edit took
   effect. Report the verification result before moving to the next finding.
7. **Checkpoint after each phase.** Update `/memories/session/plan.md` with completed
   items and current state, so the audit can resume if the conversation is interrupted.
8. **Gap check at the end.** Re-read the FINDINGS CHECKLIST and verify every item.

## Finding presentation protocol

For EACH finding, present it in this structure before implementing:

### 1. Facts

State what was found — the specific text, file, line number. No interpretation yet.

### 2. Options

Present ALL viable options, always including "Do nothing." For each option:

| Option | Description | Pros | Cons / Risks |
|--------|-------------|------|-------------|
| A (do nothing) | Leave as-is | No churn | {specific risk of inaction} |
| B | {description} | {pros} | {cons} |
| C (if applicable) | {description} | {pros} | {cons} |

### 3. Recommendation

State your recommendation with a confidence score (`.0`–`1.0`):

> **Recommendation:** Option B (`.85`) — {one-line rationale}

If a recognized best practice applies, cite it:

> **Best practice:** {source or principle} — {how it applies}

### 4. Ask for approval

- Present structured options and collect the user's choice. Include a
free-text prompt so the user can provide feedback or propose a different approach.
- **State confidence and present structured options.** At every decision point, present options with confidence scores. Never assume — when in doubt, present structured options. Include `(bp:)` for best practice and `(rec:)` for recommendation per mcp.instructions.md conventions.
- **Show Confidence scores.** When presenting proposals, prefix each option label with a confidence score on a scale of `.0`–`1.0` (no leading zero). Example: `.85 Accept — matches precedent X`. Mark the recommendation separately — it may differ from the highest-confidence option.

If the user provides feedback that changes the approach, revise the plan for that
finding and re-present before implementing.

### Presentation pacing

Present ONE finding at a time. After the user approves and you implement + commit +
verify, move to the next finding. This keeps each decision focused and allows the
user to steer the audit incrementally.
