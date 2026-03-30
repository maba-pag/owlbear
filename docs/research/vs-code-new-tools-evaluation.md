# Evaluate New VS Code Tools for v2 Agents

> **Owning task:** #95 — Evaluate new VS Code tools for v2 agents (search/usages, search/changes, vscode/askQuestions)
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

The agent-port-v2 research (#4) identified three new VS Code built-in tools not used in v1 and deferred evaluation to a separate task. The question: should OwlBear v2 agents adopt `search/usages`, `search/changes`, and `vscode/askQuestions`? If so, which agents benefit and what changes are needed?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | VS Code Copilot Cheat Sheet [S1] | .95 | Complete built-in tool list with descriptions for all three tools |
| S2 | VS Code Agent Tools docs [S2] | .90 | Tool sets, approval model, tool set grouping, custom agent tool scoping |
| S3 | VS Code Custom Agents docs [S3] | .90 | `tools` field semantics: explicit list restricts; missing tool = ignored silently |
| S4 | OwlBear agent-port-v2 research (#4) [S4] | .85 | Original deferral: "Defer new tool additions to a separate task" |
| S5 | OwlBear agent definitions (11 .agent.md files) [S5] | 1.0 | Current tool lists per agent — ground truth for gap analysis |
| S6 | OwlBear orchestrator-rewrite-sequencer research [S6] | .80 | Proposed keeping `vscode/askQuestions` for orchestrator escalation |

## 3. Analysis

### 3.1 Tool Inventory

| Tool | Description | Part of `search` set? | Runtime mapping |
|------|-------------|:---------------------:|-----------------|
| `search/usages` | Find All References + Find Implementation + Go to Definition [S1] | Yes [S2] | `vscode_listCodeUsages` |
| `search/changes` | List source control changes (staged/unstaged/merge-conflicts) [S1] | Yes [S2] | `get_changed_files` |
| `vscode/askQuestions` | Interactive question carousel for clarifying questions [S1] | No — standalone `vscode/` tool | None currently available |

### 3.2 Current Agent Access

| Agent | Has `search`? | Has `vscode/askQuestions`? | User-invocable? |
|-------|:------------:|:-------------------------:|:---------------:|
| orchestrator | No | No | Yes |
| planner | No | No | No |
| kanban-planner | Yes | No | Yes |
| researcher | Yes | No | No (mode only) |
| architect | Yes | No | No |
| test-writer | Yes | No | No |
| builder | Yes | No | No |
| reviewer | Yes | No | No |
| writer | Yes | No | No |
| auditor | Yes | No | No |
| curator | Yes | No | Yes |

### 3.3 Tool-by-Tool Evaluation

**search/usages (.75 confidence)**

| Criterion | Assessment |
|-----------|-----------|
| Already accessible? | Yes — 9/11 agents have `search` tool set [S5] |
| Tool list changes? | None needed — `search` set includes it automatically [S2] |
| Agent awareness? | GAP — no agent skill or instruction references this tool by name [S5] |
| Value | Reviewer: trace callers of changed functions. Builder: understand dependency graph before changes. Architect: assess impact of proposed interface changes. |
| Language support | Python, PS1, JSON, Markdown, .agent.md, .instructions.md — covers OwlBear's stack [S1] |
| KISS alignment | Yes — leverages IDE-native analysis instead of grep-based searching |
| Action needed | Update reviewer and builder skills to reference `search/usages` for impact analysis |

**search/changes (.80 confidence)**

| Criterion | Assessment |
|-----------|-----------|
| Already accessible? | Yes — 9/11 agents have `search` tool set [S5] |
| Tool list changes? | None needed [S2] |
| Agent awareness? | GAP — no skill workflow includes a "check source control changes" step [S5] |
| Value | Reviewer: see exactly what the builder changed. Auditor: verify commit scope matches task AC. Builder: pre-commit scope check per agent-common commit discipline. |
| KISS alignment | Yes — replaces manual `git status`/`git diff` terminal commands with native tool |
| Action needed | Update reviewer skill to add diff-check step. Update auditor skill to verify scope. |

**vscode/askQuestions (.70 confidence)**

| Criterion | Assessment |
|-----------|-----------|
| Already accessible? | NO — not in any agent's tool list [S5] |
| Instructions reference it? | YES — copilot-instructions.md says "askQuestions liberally"; orchestrator-rewrite research recommends keeping it [S6] |
| Dead-letter gap? | YES — agents are told to "askQuestions" but cannot; tool not granted |
| Which agents need it? | Only user-invocable: orchestrator, kanban-planner, curator [S3] |
| Pipeline agents? | NO — subagent-only agents don't interact with users; `askQuestions` would block/stall [S1, Autopilot section] |
| Value | Structured carousel UI instead of free-text questions; cleaner UX for decisions |
| Risk | Low — adding to 3 agents; explicitly excluded from 8 pipeline agents |
| KISS alignment | Yes — replaces ad-hoc text prompting with purpose-built UI tool |
| Action needed | Add `vscode/askQuestions` to orchestrator, kanban-planner, curator tool lists |

### 3.4 Summary Matrix

| Tool | Tool list changes? | Instruction/skill changes? | Impact | Priority |
|------|:-----------------:|:-------------------------:|--------|----------|
| `search/usages` | None | Yes — add to reviewer + builder skills | Medium | nice-to-have |
| `search/changes` | None | Yes — add to reviewer + auditor skills | Medium-High | important |
| `vscode/askQuestions` | Yes — 3 agents | None | High | needed |

## 4. Recommendation (.75 confidence)

Adopt `search/usages` and `search/changes` in v2. **Do NOT adopt `vscode/askQuestions`.**

1. **`search/changes`** (important) — reviewer and auditor can verify builder scope without manual git commands. Skill updates only.
2. **`search/usages`** (nice-to-have) — semantic code analysis improves impact checking but agents can work without it. Skill updates only.

### askQuestions — project decision (2026-03-29)

While `vscode/askQuestions` is a useful tool for general interactive Copilot sessions, **this project requires asynchronous user input, not blocking synchronous interaction**. The OwlBear pipeline is designed to run fully automated agent chains where any blocking prompt would stall the dispatch loop. The established mechanism for agent-to-user deferral is the **decision-requests skill** (`docs/decisions/pending/`), which allows agents to create structured decision files, block the task, and continue other work without interrupting the pipeline. Therefore `vscode/askQuestions` will not be granted to any agent. The "askQuestions liberally" guidance in `copilot-instructions.md` applies only to interactive user sessions, not to automated pipeline agents.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Grant vscode/askQuestions to user-invocable agents (orchestrator, kanban-planner, curator)" --priority needed --status ideation --tags phase-2,scope:agents,config --body "## Acceptance Criteria\n- [ ] orchestrator.agent.md tools list includes vscode/askQuestions\n- [ ] kanban-planner.agent.md tools list includes vscode/askQuestions\n- [ ] curator.agent.md tools list includes vscode/askQuestions\n- [ ] No pipeline-only agents (builder, reviewer, writer, test-writer, auditor, planner, architect, researcher) have vscode/askQuestions\n\nSee docs/research/vs-code-new-tools-evaluation.md for details."

kanban\kanban-md.exe create "Add search/changes usage to reviewer and auditor skill workflows" --priority important --status ideation --tags phase-2,scope:agents,docs --body "## Acceptance Criteria\n- [ ] code-review skill (SKILL.md) includes a step to check source control changes via search/changes before reading code\n- [ ] task-verification skill (SKILL.md) includes a step to verify commit scope matches task AC via search/changes\n- [ ] Steps reference the tool by name so agents know to invoke it\n\nSee docs/research/vs-code-new-tools-evaluation.md for details."

kanban\kanban-md.exe create "Add search/usages guidance to reviewer and builder skill workflows" --priority nice-to-have --status ideation --tags phase-2,scope:agents,docs --body "## Acceptance Criteria\n- [ ] code-review skill includes guidance to use search/usages for impact analysis on changed functions\n- [ ] tdd-workflow skill includes guidance to use search/usages to understand existing callers before implementing\n- [ ] Steps reference the tool by name so agents know to invoke it\n\nSee docs/research/vs-code-new-tools-evaluation.md for details."
```
