# Ideator Agent (Mediator) — Research

> **Owning task:** #645 — P4-05: Create ideator.agent.md (Mediator)
> **Date:** 2026-04-06  **Status:** Complete

## 1. Context and Question

Task #645 requires creating the central ideator agent — the Mediator that drives the 6-moment thinking process, manages the Working Directory (Blackboard), invokes voice subagents, and hands off to the planner. The spec is `thinking-companion-framework.md` §6, §7, §12. Dependencies resolved: #641 (archived, kanban rename), #644 (done, critic-voice.agent.md).

**Key questions:** What frontmatter structure, tool set, subagent list, and agent tier apply? What AC refinements are needed?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `thinking-companion-framework.md` §6, §7, §12 | Spec | 1.0 — primary design authority |
| 2 | `share/agents/orchestrator.agent.md` | Codebase | 0.9 — closest pattern (user-invocable, multi-subagent) |
| 3 | `share/agents/critic-voice.agent.md` | Codebase | 0.8 — first voice agent built (#644), structural reference |
| 4 | `share/skills/h-agent-structure/SKILL.md` | Codebase | 0.9 — structural standards for agent files |
| 5 | `tests/test_grant_vscode_askquestions_to_user_invocable.py` | Codebase | 0.9 — blanket ban on vscode/askQuestions (task #123) |
| 6 | `share/agents/planner.agent.md` | Codebase | 0.7 — user-invocable agent pattern with kanban tools |

## 3. Analysis

### 3a. vscode/askQuestions Conflict (Critical)

AC#16 lists `vscode_askQuestions`. Test `test_grant_vscode_askquestions_to_user_invocable.py` enforces a **blanket ban** across all agents (task #123, parametrized over all `*.agent.md` files). Adding the ideator will trigger this test.

The ideator is a conversational agent — it asks questions through the chat interface, like the orchestrator. No special tool needed. **Resolution: drop `vscode/askQuestions` from AC#16.** No exemption, no test update.

### 3b. Agent Tier Classification

| Option | Tier | Pipeline protocol? | Rationale |
|--------|------|--------------------|-----------|
| A — T3 Support | T3 | No | Closest match: planner (user-invocable, creates tasks). But planner is pipeline-adjacent; ideator is pre-pipeline. |
| B — New tier | T0 | No | "Entry point" tier. Overkill for one agent. |
| **C — T3 (rec)** | T3 | No | Pragmatic: user-invocable, not a pipeline agent, delegates to subagents. References `w-ideation` skill, not `r-pipeline-protocol`. |

### 3c. Tool Set Comparison

| Tool Category | Tools | Justification |
|---------------|-------|---------------|
| File system | `edit/createDirectory`, `edit/createFile`, `edit/editFiles` | Working Dir management (AC#8, AC#14) |
| Read | `read/readFile`, `read/viewImage` | Input files, summary files (AC#13) |
| Search | `search` | Codebase scanning during conversation |
| MCP kanban | `owlbear-kanban/create_task`, `owlbear-kanban/list_tasks`, `owlbear-kanban/show_task` | Handoff (AC#15), re-entry board detection |
| MCP project | `owlbear-project/*` | Existing project detection (AC#8) — **first agent to use this namespace** |
| MCP knowledge | `owlbear-knowledge/search-knowledge` | Lightweight M3 context queries — **first agent to use this namespace** |
| Memory | `vscode/memory`, `owlbear-memory/*` | Standard agent learning |
| Subagent | `agent` | Voice/subagent invocation (AC#9-AC#12) |
| ~~vscode/askQuestions~~ | ~~dropped~~ | Blanket ban (§3a). Chat interface suffices. |
| ~~execute/*~~ | ~~not needed~~ | No terminal operations. Research delegated to Explore. |
| ~~web~~ | ~~not needed~~ | ecosystem research delegated to Explore subagent |

### 3d. Subagent List

| Agent | When invoked | Spec reference |
|-------|-------------|----------------|
| critic-voice | After M1, M2, M4, M5 (standalone checks) | §7 Critic invocation points |
| pragmatist-voice | Between M3 and M4 (synthesis) | §7 Structural voices |
| architect-voice | Voice deliberation phase | §7 Domain voices |
| data-voice | Voice deliberation phase | §7 Domain voices |
| enduser-voice | Voice deliberation phase | §7 Domain voices |
| security-voice | Voice deliberation phase | §7 Domain voices |
| planner | M6 handoff (task decomposition) | §6 Moment 6 |
| Explore | M3 landscape scan (codebase + ecosystem) | §6 Moment 3 |

### 3e. Agent File Structure

Per h-agent-structure, procedures belong in `w-ideation` skill (#651). Agent file encodes identity:

| Section | Content | Est. lines |
|---------|---------|------------|
| Frontmatter | name, description, argument-hint, user-invocable, model, tools, agents | 15 |
| `<persona>` | Mediator dual-mode (Investigator + Facilitative), emotional framing | 15 |
| `<critical_rules>` | Skill ref, context window economy, transparency, Working Dir, voice delegation | 12 |
| `<subagents>` | 8-row table with invocation context | 15 |
| `<boundaries>` | Context discipline, no pipeline protocol, Working Dir scope | 12 |
| `<examples>` | Good/bad Mediator behaviors (abstract) | 15 |
| **Total** | | **~85 lines** |

### 3f. First-of-Kind Aspects (Risks)

| Aspect | Risk | Mitigation |
|--------|------|------------|
| First `owlbear-project/*` user | MCP namespace untested in agent frontmatter | Builder validates tool availability at runtime |
| First `owlbear-knowledge/*` user | Same as above | Same — fallback: delegate to Explore |
| First Blackboard pattern agent | Working Dir file management complexity | Procedures in w-ideation skill, not agent file |
| First parallel voice invocation from agent file | runSubagent concurrency verified (spec §14, tested up to 6) | Low risk — already confirmed |

## 4. Recommendation

**Build the ideator agent file** (~85 lines) following the orchestrator pattern with these adaptations:

1. **Drop `vscode/askQuestions`** from tools — blanket ban + unnecessary for conversational agent
2. **Classify as T3** — no pipeline protocol references in critical_rules
3. **Include `owlbear-project/*` and `owlbear-knowledge/search-knowledge`** — first-of-kind but functional MCP servers
4. **Reference `w-ideation` skill** as primary procedural source — keep agent file identity-focused
5. **No `disable-model-invocation`** — user-invocable agent (matches orchestrator, planner pattern)
6. **No hooks** — writes only to `.owlbear/briefs/`, not source code

**Confidence: 0.85**

**Challenge: FALLBACK — challenger agent not in available roster. Self-challenge performed.**
Self-challenge findings: (a) first-of-kind MCP namespaces are low risk — servers exist and are registered; (b) tool set is intentionally minimal — `edit_task` deferred for re-entry phase; (c) agent file size at ~85 lines is within established range.

## 5. Follow-up Tasks

No new follow-up tasks needed. Existing board coverage:
- #646-#650: voice agent files (depend on #645)
- #651: `w-ideation/SKILL.md` workflow (depends on #646-#650)
- #652: `h-voice-panel/SKILL.md` handbook (depends on #646-#650)

### AC Refinements for Architect

The following AC lines need architect attention during review:

| AC# | Issue | Recommended refinement |
|-----|-------|----------------------|
| 16 | Lists `vscode_askQuestions` — blanket ban in test #123 | Drop. Chat interface is the conversation channel. |
| 16 | "MCP knowledge" unspecified granularity | Specify: `owlbear-knowledge/search-knowledge` (read-only query only) |
| 16 | Missing `agent` tool for subagent invocation | Add `agent` to tool list |
| — | Missing `disable-model-invocation` statement | Confirm: NOT set (user-invocable agent) |
| — | Missing tool: `search` for codebase scanning | Add to AC or verify in tool list |
