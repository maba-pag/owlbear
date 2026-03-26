# Prompt vs Skill vs Agent — Command Surface Rules

> **Owning task:** #942 — Codify prompt-vs-skill-vs-agent rules for user-facing command surfaces
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

OwlBear uses three VS Code customization surfaces — `.prompt.md`, `SKILL.md`, and `.agent.md` — but has no documented rule for when to choose which. Task #930 research recommended `.prompt.md` as the default for user-facing commands, but the rule was never codified. The question: what decision table should guide future OwlBear customization work?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | VS Code prompt files docs | .95 | Prompt file mechanics: slash-command invocation, optional tools/agent/model frontmatter, lightweight single-task framing [S1] |
| S2 | VS Code custom agents docs | .95 | Agent mechanics: persistent persona, tool restrictions, handoffs, model preferences, subagent orchestration [S2] |
| S3 | VS Code agent skills docs | .95 | Skill mechanics: progressive loading, co-located scripts/resources, open standard, auto-load by relevance [S3] |
| S4 | VS Code customization overview | .90 | Official taxonomy: instructions (standards), prompts (tasks), skills (capabilities), agents (personas) [S4] |
| S5 | OwlBear existing surfaces | 1.0 | 2 prompts, 21 skills, 11 agents already in repo; conventions emerged but undocumented [S5] |
| S6 | Impeccable command patterns research | .90 | Prior OwlBear research recommending `.prompt.md` for user-facing one-shots [S6] |

## 3. Analysis

### 3.1 Decision Table

| Criterion | `.prompt.md` | `SKILL.md` | `.agent.md` |
|-----------|:------------:|:----------:|:-----------:|
| **Primary purpose** | Repeatable one-shot task [S1] | Reusable domain knowledge [S3] | Long-lived persona with tool/model config [S2] |
| **Invocation** | User types `/name` [S1] | Auto-loaded by relevance or `/name` [S3] | Selected from agent picker [S2] |
| **Persistence** | Single turn — runs once per invocation [S1] | Loaded into context for duration of conversation [S3] | Active until user switches agent [S2] |
| **Tool restrictions** | Optional `tools` frontmatter [S1] | None — relies on agent's tool set [S3] | `tools` frontmatter scopes available tools [S2] |
| **Co-located resources** | No — single Markdown file [S1] | Yes — scripts, examples, templates in skill dir [S3] | No — single Markdown file [S2] |
| **Auto-load** | Never — always user-invoked [S1] | Yes — model can load by relevance [S3] | Never — user selects [S2] |
| **Portability** | VS Code only [S1] | Open standard (agentskills.io) — VS Code, CLI, coding agent [S3] | VS Code + Claude format [S2] |
| **OwlBear count** | 2 (orchestrate, agent-audit) [S5] | 21 (all pipeline skills) [S5] | 11 (all pipeline agents) [S5] |

### 3.2 When-to-Use Rule

| Choose this surface | When all of these are true |
|---------------------|---------------------------|
| `.prompt.md` | User-facing one-shot command; no co-located scripts needed; no auto-load required [S1, S4, S6] |
| `SKILL.md` | Reusable domain knowledge an agent should auto-load by relevance; or needs co-located scripts/templates/examples [S3, S4] |
| `.agent.md` | Needs persistent persona, scoped tool restrictions, model preferences, or handoff orchestration [S2, S4] |

**Default for new user-facing commands:** `.prompt.md` unless the command needs auto-loading or co-located resources [S1, S6].

### 3.3 OwlBear Examples

| Surface | OwlBear example | Why this surface |
|---------|----------------|------------------|
| `.prompt.md` | `orchestrate.prompt.md` — starts the orchestrator via `/orchestrate` | One-shot user command that delegates to an agent; no scripts or auto-load needed [S5] |
| `SKILL.md` | `research-workflow/SKILL.md` — structured research procedure | Domain knowledge auto-loaded when researcher agent is active; contains step-by-step procedures agents reference mid-conversation [S5] |
| `.agent.md` | `reviewer.agent.md` — code review persona | Long-lived role with specific tool restrictions and pipeline gate ownership; user selects it from agent picker [S5] |

## 4. Recommendation (.90 confidence)

Add a short "Command Surface Selection" section to `.github/copilot-instructions.md` containing:

1. The decision table from §3.2 (when-to-use rule)
2. The three concrete OwlBear examples from §3.3
3. The default rule: user-facing one-shot commands → `.prompt.md` unless auto-load or co-located resources are needed

This keeps the guidance visible to all agents without creating a separate doc that drifts. The table is 9 lines — well within the "short decision table" AC.

**Risk:** The rule may need revisiting if VS Code merges prompt and skill invocation surfaces. Mitigation: the table is small enough to update in-place.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add command-surface selection table to copilot-instructions.md" --priority nice-to-have --status ideation --tags "docs,scope:copilot,type:docs" --parent 942 --body "AC:\n- Add a 'Command Surface Selection' section to .github/copilot-instructions.md with the when-to-use decision table from docs/research/prompt-vs-skill-vs-agent-rules.md §3.2\n- Include one OwlBear example per surface (prompt: orchestrate.prompt.md, skill: research-workflow/SKILL.md, agent: reviewer.agent.md)\n- State default: user-facing one-shot commands use .prompt.md unless auto-load or co-located resources are needed\n- Scope limited to copilot-instructions.md; do not rename or add commands"
```
