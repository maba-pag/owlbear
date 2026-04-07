---
description: "Audit the OwlBear agent ecosystem for structural conformance, duplication, and signal quality"
---

# Agent Ecosystem Audit

You are auditing the OwlBear multi-agent pipeline — a set of VS Code Copilot agent
definitions (.agent.md), skills (SKILL.md), instruction stubs (.instructions.md), and
project-wide copilot-instructions that form an autonomous kanban-driven development system.

## What you're auditing

Read ALL of these files before forming conclusions:

- `.github/copilot-instructions.md`
- `share/instructions/*.instructions.md`
- `share/agents/*.agent.md`
- `share/skills/*/SKILL.md`

Use `file_search` to discover the current set. Do not assume a fixed count.

## Structural standard

The structural specification lives in the `h-agent-structure` skill. **Read it first.**
That handbook defines: agent file sections, skill file categories, naming conventions,
instruction stub format, the Rule of Two, the 80% Rule, the loading model, implicit
encoding principles, and the tier model.

Every finding must reference a specific rule from `h-agent-structure`.

## Pipeline protocol

The shared pipeline conventions live in the `r-pipeline-protocol` skill. **Read it second.**
That rules skill defines: channel communication, claiming, commit discipline, confidence
thresholds, escalation, and all shared pipeline conventions.

Project-wide conventions (commit format, file placement, attribution, tags) live in
`r-project-standards`. **Read it third.**

## What to look for

### 1. Structural violations

- Agent file missing required sections defined in `h-agent-structure`
- Agent file containing forbidden content (procedures, shared rules, command templates)
- Skill in wrong category (workflow file that's really a handbook, etc.)
- Naming convention violations (missing prefix, wrong grammar pattern)
- Instruction file that's not a 3-line stub (contains actual rules instead of pointing to a skill)

### 2. Duplication (Rule of Two violations)

- Same rule appears in 3+ locations
- Agent file restates content from `r-pipeline-protocol` instead of referencing it
- Agent file restates content from `r-project-standards` (commit format, file placement, tags, attribution) instead of referencing it
- Skill contains claiming/commit boilerplate that belongs in `r-pipeline-protocol`
- Agent `<output_format>` contains full command templates instead of verdict tokens + skill reference

### 3. Content placement

- Content in `copilot-instructions.md` that fails the 80% rule (fewer than 80% of agents need it)
- Content in `r-pipeline-protocol` that only one agent needs (should be in that agent's file)
- Content in an agent file that applies identically to 2+ agents (should be in a shared location)

### 4. Quality signals

- Agent `<persona>` is a flat role description instead of an emotionally loaded scenario
- Agent `<examples>` are realistic/specific instead of abstract/principle-based
- Agent `<critical_rules>` missing skill reference as first item
- Pipeline agent missing `r-pipeline-protocol` reference in `<critical_rules>`
- Agent file containing self-critique or procedure content (belongs in workflow skill)
- Workflow skill missing Step 0 (protocol loading) where applicable

### 5. Pipeline integrity

- Missing dispatch path (task status with no agent to process it)
- Double-moves (two agents move the same status transition)
- Signal mapping in `r-pipeline-protocol` doesn't match agent `<output_format>`
- Agent tier assignment doesn't match its pipeline-protocol needs
- Agent `tools:` allowlist missing tools it needs or including tools outside its tier
- **Rejection flow consistency:** reviewer's `<pipeline_position>` targets must match `w-code-review` Step 8 (severity-based: impl issue → in-progress, test gap → todo, test/AC quality → backlog, 3rd+ FAIL → backlog). Builder routes rejections by cause (test assumption → todo, AC wrong → backlog). Architect uses REJECT to ideation. Auditor rejects always → backlog. No agent uses BLOCK/BLOCKED as a verdict — blocking is reserved for DR-pending tasks (scribe) and stale triage (dispatcher).
- Agent renames: verify `dispatcher` (for dispatch), `planner` (for decomposition), `doc-writer` (for docs gate) are used consistently everywhere

### 6. Signal-to-noise ratio

- Rationale/justification for rules (the "why" has no operational value — only the rule matters)
- Prose restating information from another section or file
- Verbose phrasing where terse carries the same meaning
- Background context useful for documents but not for task execution

## Output format

```
## FINDINGS

### Structural Violations (S1, S2, ...)
For each: Which file, which h-agent-structure rule is violated, what should change.

### Duplication (D1, D2, ...)
For each: What's duplicated, where, which is the source of truth, what to remove.

### Content Placement (P1, P2, ...)
For each: What's misplaced, where it is, where it should be (per 80% rule or Rule of Two).

### Quality Signals (Q1, Q2, ...)
For each: What's low-quality, which file, what improvement looks like.

### Pipeline Integrity (I1, I2, ...)
For each: What's broken, which files disagree, what the correct state is.

### SNR Issues (N1, N2, ...)
For each: What's noisy, which file and section, suggested terse replacement or deletion.

## FINDINGS CHECKLIST
- [ ] **{ID}** {one-line description of what "fixed" looks like}

## REMEDIATION PLAN
Ordered by impact. For each step:
- What: one-sentence description
- Files to modify
- Exact changes

## VERIFICATION
1. Trace an implementation task through the full pipeline
2. Trace a non-implementation task (research, config)
3. Verify rejection routing is cause-based and consistent (no BLOCK/BLOCKED verdicts)
4. Spot-check 3 files for SNR (rationale prose, restated rules, filler)
```

## Process

1. **Read ALL files first.** No conclusions until every file is read.
2. **Read `h-agent-structure` and `r-pipeline-protocol` before evaluating.** They are the standard.
3. **Save plan to `/memories/session/audit-plan.md`.**
4. **Present findings one at a time** using the protocol below.
5. **Implement finding by finding.** Complete one before starting the next.
6. **Verify after each fix.** Confirm the edit took effect.
7. **Checkpoint after each phase.** Update session memory.

## Finding presentation protocol

For each finding:

### 1. Facts
State what was found — specific text, file, line number. No interpretation.

### 2. Options
Present viable approaches including "do nothing." For each: description, pros, cons/risks.

### 3. Recommendation
State recommendation with confidence score (.0–1.0). Cite the `h-agent-structure` rule if applicable.

### 4. Approval
Collect the user's choice before implementing. Include free-text for feedback.

Present ONE finding at a time. After approval + implementation + verification, move to the next.
