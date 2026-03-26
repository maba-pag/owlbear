# Agent kanban-md Standardization Plan

> **Date:** 2026-03-19
> **Context:** Follow-up to planner wave-planning standardization (completed same session).
> **Goal:** Slim the 460-line shared kanban-md skill to ~60 lines and move per-agent
> command recipes into each agent's own skill file.

## Problem

The shared `kanban-md/SKILL.md` (460 lines) is loaded by every agent that references the
kanban-md skill. Most content is irrelevant to any given agent:

- 144 lines of full command documentation (agents use ~5 commands each)
- 89 lines of Agent Cheatsheet (generic examples, not agent-specific)
- 49 lines of Workflows (standup/triage/sprint — human-facing, not agent-facing)
- 39 lines of Decision Tree (interactive use, not dispatched-agent use)

Result: agents improvise commands instead of following the prescribed pattern, because the
correct commands are buried in noise.

## Decisions Made (via askQuestions)

1. **Delivery mechanism:** Per-agent SKILL files (docs-gate, tdd-workflow, etc.)
2. **Shared skill:** Minimal reference only (~60 lines) — protocol summary + pitfalls
3. **Kanban-planner:** Treat as full pipeline member, add recipes to task-decomposition skill
4. **Implementation order:** All at once (not incremental)

## Architecture

### Shared kanban-md skill (after slimming)

Target: ~60 lines. Contains ONLY:

| Section | Lines | Content |
|---------|-------|---------|
| Frontmatter | 5 | Name, description (narrowed to "claiming protocol and pitfalls reference") |
| OwlBear convention | 2 | Binary path note |
| Claiming protocol summary | 18 | 3-phase lifecycle (claim → maintain → advance+release), dispatch vs pick rule, cross-task boundaries (brief) |
| Command synopsis table | 12 | One-line signature per command (show, edit, create, list, move, pick, handoff, delete, board, agent-name) — NO detailed docs |
| Critical pitfalls | 15 | The truly dangerous ones: orthogonal filters, --body newline bug, --depends-on vs --add-dep, --unclaimed for claim timeout, claim by ID not pick |
| Footer | 2 | "Per-agent command recipes live in each agent's skill file." |

**REMOVED entirely:**

- Decision Tree (39 lines) — interactive reference, not needed by dispatched agents
- Workflows section (49 lines) — standup/triage/sprint are human activities
- Agent Cheatsheet (89 lines) — replaced by per-agent recipe tables
- Detailed Core Commands docs (144→12 synopsis) — agents only need the flags they use
- Long-form rules (13→6) — redundant with protocol summary

### Per-agent recipe tables

Each agent's skill gets a `## kanban-md Commands` section near the top (after frontmatter,
before Step 1). Format:

```markdown
## kanban-md Commands

| Action | Command |
|--------|---------|
| Read task | `kanban\kanban-md.exe show {id}` |
| Claim | `kanban\kanban-md.exe edit {id} --claim <agent>` |
| ... | ... |

No other kanban-md commands needed. See kanban-md skill for claiming protocol and pitfalls.
```

## Per-Agent Command Maps

### Writer (docs-gate/SKILL.md)

- **Pipeline:** docs → done (or reject to review)
- **Commands:**
  - Read task: `show {id}`
  - Claim: `edit {id} --claim <agent>`
  - Append report: `edit {id} -a "## Docs Gate\n{content}" -t --claim <agent>`
  - Advance (pass): `edit {id} --status done --release`
  - Reject: `edit {id} --status review --block "reason" --release`

### Builder (tdd-workflow/SKILL.md)

- **Pipeline:** in-progress → review (or BLOCK to todo)
- **Commands:**
  - Read task: `show {id}`
  - Claim: `edit {id} --claim <agent>`
  - Append notes: `edit {id} -a "## Builder Notes\n{content}" -t --claim <agent>`
  - Advance: `edit {id} --status review --release`
  - BLOCK (fundamental): `edit {id} --status todo --block "reason" --release`
  - Pass-through: same append + advance (for non-impl tasks)

### Reviewer (code-review/SKILL.md)

- **Pipeline:** review → docs (PASS) or review → todo (FAIL)
- **Commands:**
  - Read task: `show {id}`
  - Claim: `edit {id} --claim <agent>`
  - Append evidence: `edit {id} -a "## Review Evidence\n{content}" -t --claim <agent>`
  - PASS: `edit {id} --status docs --release`
  - FAIL: `edit {id} --status todo --block "reason" --release`

### Test-writer (tdd-red/SKILL.md)

- **Pipeline:** todo → in-progress
- **Commands:**
  - Read task: `show {id}`
  - Claim: `edit {id} --claim <agent>`
  - Append summary: `edit {id} -a "## Test-Writer Notes\n{content}" -t --claim <agent>`
  - Advance: `edit {id} --status in-progress --release`
  - Pass-through: same append + advance (for non-impl tasks)

### Auditor (task-verification/SKILL.md)

- **Pipeline:** done → archived (or reject to review/backlog)
- **Commands:**
  - List done tasks: `list --compact --status done`
  - Read task: `show {id}`
  - Claim: `edit {id} --claim <agent>`
  - Append audit: `edit {id} -a "## Audit\n{content}" -t --claim <agent>`
  - Archive: `archive {id}` then `edit {id} --release`
  - Reject (fixable): `edit {id} --status review --block "reason" --release`
  - Reject (fundamental): `edit {id} --status backlog --block "reason" --release`

### Researcher (research-workflow/SKILL.md)

- **Pipeline:** ideation → backlog
- **Commands:**
  - Read task: `show {id}`
  - Claim: `edit {id} --claim <agent>`
  - Append research: `edit {id} -a "## Research\n{content}" -t --claim <agent>`
  - Create follow-ups: `create "TITLE" --priority P --status ideation --tags T`
  - Advance: `edit {id} --status backlog --release`

### Architect (arch-review/SKILL.md)

- **Pipeline:** backlog → todo (or reject/refine/split/merge)
- **Commands:**
  - Read task: `show {id}`
  - Claim: `edit {id} --claim <agent>`
  - Append review: `edit {id} -a "## Architecture Review\n{content}" -t --claim <agent>`
  - Approve: `edit {id} --status todo --release`
  - Refine: `edit {id} --body "{revised AC}" --claim <agent>` (keep claimed, iterate)
  - Split (create new): `create "TITLE" --priority P --tags T --depends-on ID --body "AC"`
  - Split (create TDD test task): `create "Test: TITLE" --priority P --tags T,test --body "AC"`
  - Merge (delete redundant): `delete ID --yes`
  - Block: `edit {id} --block "reason" --release`

### Kanban-planner (task-decomposition/SKILL.md)

- **Role:** Decomposes features into tasks. Outputs create commands but does NOT execute them.
- **Commands:**
  - Board overview: `board --compact`
  - List existing tasks: `list --compact`
  - Read parent task: `show {id}`
  - Append plan to parent: `edit {id} -a "## Planning\n{content}" -t`
  - OUTPUT (not executed): `create "P{n}-{nn}: TITLE" --priority P --tags T --depends-on ID --body "AC"`

### Curator (curation-workflow/SKILL.md)

- **Role:** Utility agent, triages lessons learned. Minimal kanban-md interaction.
- **Commands:**
  - Read task (if dispatched with ID): `show {id}`
  - Append report (if dispatched with ID): `edit {id} -a "## Curation\n{content}" -t`
  - (Most work is memory tool operations, not kanban-md)

### Planner (wave-planning/SKILL.md) — ALREADY DONE

- Has full Command Recipes section from previous session. No changes needed.

### Orchestrator — NO CHANGES

- Explicitly prohibited from using kanban-md ("You never call kanban-md list or show").

## Files to Modify (10 total)

1. `.github/skills/kanban-md/SKILL.md` — slim from ~460 to ~60 lines
2. `.github/skills/docs-gate/SKILL.md` — add writer recipe table
3. `.github/skills/tdd-workflow/SKILL.md` — add builder recipe table
4. `.github/skills/code-review/SKILL.md` — add reviewer recipe table
5. `.github/skills/tdd-red/SKILL.md` — add test-writer recipe table
6. `.github/skills/task-verification/SKILL.md` — add auditor recipe table
7. `.github/skills/research-workflow/SKILL.md` — add researcher recipe table
8. `.github/skills/arch-review/SKILL.md` — add architect recipe table
9. `.github/skills/task-decomposition/SKILL.md` — add kanban-planner recipe table
10. `.github/skills/curation-workflow/SKILL.md` — add curator recipe table

## Implementation Notes

- Each per-agent recipe table goes between the frontmatter/intro and Step 1
- The shared skill is a complete rewrite (easier than surgical edits on 460 lines)
- Every skill already has inline `kanban\kanban-md.exe` commands scattered through steps —
  those stay as-is. The recipe table is a quick-reference summary at the top.
- The "See kanban-md skill for claiming protocol and pitfalls" footer in each table
  provides the cross-reference back to the shared skill.
- Current inline commands in per-agent skills are ALREADY CORRECT — they match the
  3-phase protocol (claim → maintain → advance+release). We are not changing them,
  just adding the summary table.

## Workflow for Implementation

For each file:

1. Read the original file
2. Write the new version to a temp file (docs/scratch/temp-{name}.md)
3. Compare
4. If satisfied, replace the original with the new version
