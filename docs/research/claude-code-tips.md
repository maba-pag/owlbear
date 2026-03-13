# Claude Code Tips — Research Findings

> **Owning task:** #596 — Research: ykdojo/claude-code-tips
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Analyze [ykdojo/claude-code-tips](https://github.com/ykdojo/claude-code-tips) (45 tips + 6 packaged skills + system prompt patches) for workflow patterns, prompt engineering techniques, and developer productivity ideas applicable to OwlBear's agent system.

**License note:** All Rights Reserved (not MIT). We study patterns and ideas only — no code copying.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| ykdojo/claude-code-tips README (45 tips) | <https://github.com/ykdojo/claude-code-tips> | .85 |
| GLOBAL-CLAUDE.md (personal workflow rules) | (repo file) | .70 |
| Skills: handoff, clone, half-clone, review-claudemd, gha | (repo skills/) | .80 |
| Spectrum of Agentic Coding essay | (repo content/) | .65 |
| Boris Cherny's 10 tips (summarized) | (repo content/boris-claude-code-tips.md) | .75 |

## 3. Analysis — Patterns Applicable to OwlBear

### 3a. Handoff document pattern (Tips 8, 23)

| Aspect | claude-code-tips | OwlBear current |
|--------|------------------|-----------------|
| Context transfer | HANDOFF.md file (goal, progress, what worked/failed, next steps) | kanban task body + `--append-body --timestamp` |
| Trigger | Manual or /handoff slash command | Agent manually writes handoff in task body |
| Freshness | Explicit "start fresh with just this file" | New chat session inherits copilot-instructions |
| Half-clone | Keep later half of conversation history | No equivalent |

**Takeaway (.75):** OwlBear's kanban body already serves as a handoff mechanism, but lacks a structured handoff template. A formalized handoff section (what worked / what failed / next steps) in task body edits would improve inter-agent continuity. The orchestrator could enforce this at status transitions.

### 3b. Instruction review from session history (Tip 30, review-claudemd skill)

| Aspect | claude-code-tips | OwlBear current |
|--------|------------------|-----------------|
| Pattern | Analyze recent conversations to find violated/missing CLAUDE.md rules | Task #146 (self-improvement pipeline) in backlog — not yet built |
| Execution | Subagents scan JSONL history, produce bullet-point findings | Planned: analytics → evaluate → propose → human-gate |
| Scope | Global + project CLAUDE.md | Agent definitions + copilot-instructions |

**Takeaway (.60):** The review-claudemd pattern validates the design of task #146. OwlBear's planned self-improvement pipeline already covers this. No new task needed — but the skill's "batch by size, spin subagents, aggregate" workflow is a useful implementation reference when #146 reaches development.

### 3c. GHA failure investigation skill (Tip 29, gha skill)

| Aspect | claude-code-tips | OwlBear current |
|--------|------------------|-----------------|
| Pattern | Structured CI failure investigation: get info → check flakiness → find breaking commit → root cause → check existing fix PRs | No CI pipeline yet |
| Execution | Single skill with `gh` CLI | N/A |

**Takeaway (.50):** Not immediately actionable — OwlBear doesn't have CI yet. Worth revisiting when CI is set up.

### 3d. Self-verification prompts (Tip 28)

| Aspect | claude-code-tips | OwlBear current |
|--------|------------------|-----------------|
| Pattern | "Double check everything, every single claim — make a table of what you could verify" | Reviewer agent verifies AC line-by-line with evidence |
| Prompt | Ad-hoc prompt injection | Structured in reviewer/auditor agent definitions |

**Takeaway (.40):** OwlBear already has formalized verification (reviewer + auditor agents with evidence tables). The ad-hoc prompting pattern is less rigorous than what OwlBear already does.

### 3e. Abstraction level spectrum (Tip 32, spectrum essay)

| Level | Description | OwlBear equivalent |
|-------|-------------|-------------------|
| Vibe coding | Let AI go wild, no review | Not supported — TDD mandatory |
| Agentic + discipline | Git, file-level understanding, testing | Builder agent baseline |
| Agentic SE | Thorough tests, CI, function-level review | Reviewer + writer gates |
| High-quality SE | Line-by-line review, self-reflection loops | Auditor gate + confidence scores |

**Takeaway (.55):** OwlBear's pipeline already maps to Level 4 (high-quality SE). The spectrum framework is a useful mental model for documentation but doesn't suggest changes.

### 3f. Command simplification pattern (GLOBAL-CLAUDE.md)

| Aspect | claude-code-tips | OwlBear current |
|--------|------------------|-----------------|
| Pattern | Break complex bash commands into multiple simple commands; avoid complex pipes | terminal.instructions.md has concise flags, redirect strategy |
| Rationale | Makes each command independently approvable; avoids approval fatigue | Reduces wasted tool calls |

**Takeaway (.70):** OwlBear's terminal instructions focus on output handling but don't explicitly address command decomposition for approval. Since OwlBear's `TerminalToolset.run_command()` has approval gates, breaking complex commands into simple steps would reduce approval friction and improve auditability.

### 3g. Context token management (Tips 5, 8, 15)

| Aspect | claude-code-tips | OwlBear current |
|--------|------------------|-----------------|
| Fresh context | Short conversations, proactive compaction | Session-scoped by design (new chat = fresh context) |
| Token budgeting | System prompt trimming (50% reduction), lazy-load MCP tools | `knowledge_context_tokens` config (default 2000) |
| Context monitoring | Status bar with token % usage | No visible token tracking |

**Takeaway (.45):** OwlBear operates within VS Code Copilot Chat where context management is handled differently. The token budgeting principle is already applied via `knowledge_context_tokens`. Not directly actionable.

## 4. Recommendation

**Primary (.75 confidence):** Add a structured handoff template to `agent-common.instructions.md` section "Task coordination > Handoff / blocked". When agents transition a task between statuses, require a structured note: `## Handoff: {what-worked} | {what-failed} | {next-steps}`. This costs ~5 lines of instruction and improves inter-agent continuity.

**Secondary (.70 confidence):** Add a command decomposition guideline to `agent-common.instructions.md` section "Terminal discipline": "Break complex chained commands into separate simple commands for independent approval and auditability." This aligns with OwlBear's approval gate architecture.

**Deferred:** The review-claudemd pattern (session history analysis → instruction improvement) validates #146's design. Reference this repo's approach when that task reaches development.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add structured handoff template to agent-common.instructions.md" --priority nice-to-have --tags "scope:copilot,agent,phase-research" --body "Add a what-failed tracking field to the handoff template in agent-common.instructions.md section 'Task coordination > Handoff / blocked'. Current template has 'Current state / Open questions / Next step'; add 'what-failed' tracking. See docs/research/claude-code-tips.md §3a for context. AC: (1) agent-common.instructions.md handoff template includes a what-failed field; (2) field is documented in the Handoff / blocked section."

kanban\kanban-md.exe create "Add command decomposition guideline to Terminal discipline" --priority nice-to-have --tags "scope:copilot,docs,phase-research" --body "Add a command decomposition guideline to agent-common.instructions.md section 'Terminal discipline': break complex chained commands into separate simple steps for independent approval and auditability. See docs/research/claude-code-tips.md §3f. AC: (1) agent-common.instructions.md Terminal discipline section has a command decomposition bullet; (2) guideline explains the approval-gate rationale."
```

