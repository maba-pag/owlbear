# Quality-Runner Wiring into Pipeline Agents

> **Owning task:** #264 — Wire Quality-Runner into pipeline agents
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Four pipeline agents (builder, reviewer, auditor, test-writer) independently run pytest, ruff, and coverage using direct terminal commands. This duplicates 10+ pitfalls documented in the `pytest-and-linting` skill (PS 5.1 piping, bare `--cov` only, WMI hang, `asyncio_mode=strict`, etc.) across 4 agents and 4 skill files. Task #263 creates a Quality-Runner utility subagent to encapsulate this. Task #264 wires it into the consuming agents.

**Research question:** What are the concrete changes needed per agent and skill file to integrate Quality-Runner, and what is the recommended migration approach?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — `agents:` array, nesting, override of `disable-model-invocation` |
| S2 | VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — `agents` field spec, tool inheritance, assign mode |
| S3 | Subagent nesting architecture research | docs/research/subagent-nesting-architecture.md | .95 — Quality-Runner I/O contract, category validation |
| S4 | Existing pipeline agent files | agents/{builder,reviewer,auditor,test-writer}.agent.md | .95 — current tool lists, `agents: []` |
| S5 | Existing skill files | skills/{tdd-workflow,tdd-red,code-review,task-verification}/SKILL.md | .95 — current test/lint invocation steps |
| S6 | Workspace settings | .vscode/settings.json | .90 — `allowInvocationsFromSubagents` already enabled |

## 3. Analysis

### 3a. Current Test/Lint Invocation Points

| Agent | Skill | Steps with direct pytest/ruff/coverage | Mode |
|-------|-------|----------------------------------------|------|
| Builder | tdd-workflow | Step 3 (verify fail), Step 4 (verify pass), Step 5 (builder-discovered), Step 7 (full verify) | scoped |
| Reviewer | code-review | Step 3 (tests), Step 4 (lint), Step 5 (coverage) | scoped |
| Auditor | task-verification | Step 2 (full suite + lint) | full |
| Test-writer | tdd-red | Step 5 (verify all FAIL + lint) | scoped |

**Total:** 12 direct invocation points across 4 skill files, all replaceable with Quality-Runner calls.

### 3b. Frontmatter Changes per Agent

All 4 agents currently have `agents: []` (S4). Each needs:

```yaml
agents: [quality-runner]
```

Quality-Runner uses `user-invocable: false` without `disable-model-invocation: true` (S3 cross-cutting). Alternatively, Quality-Runner can use `disable-model-invocation: true` and rely on the explicit `agents:` array override (S1, S2). The second approach is more restrictive — only agents that explicitly list Quality-Runner can invoke it. Recommend the restrictive approach (.80 confidence) per least-privilege principle.

**Tool retention:** All 4 agents keep their existing `execute/*` tools. Builder and auditor need them for git operations. Reviewer and test-writer could theoretically drop them, but keeping them provides fallback capability and avoids risk. A future optimization task can evaluate removal.

### 3c. Skill Changes per Agent

Each skill replaces direct `uv run pytest/ruff` commands with a Quality-Runner invocation pattern:

```
Invoke Quality-Runner subagent with:
- mode: scoped (or full for auditor)
- test_paths: [tests/test_{module}.py]
- task_id: {id}
- coverage_modules: [{module}] (when coverage needed)
- lint_paths: [{paths}]
```

Quality-Runner returns structured text with sections: tests, lint, coverage, errors. The parent agent reads the returned text and acts on the results (pass/fail counts, lint status, coverage percentage).

| Agent | Skill file | Steps to update | Notes |
|-------|-----------|-----------------|-------|
| Builder | tdd-workflow | 3, 4, 5, 7 | Builder has multiple verify cycles (RED, GREEN, discovered); may invoke Quality-Runner 2-3 times per task |
| Reviewer | code-review | 3, 4, 5 | Steps 3-5 merge into single Quality-Runner call (tests+lint+coverage) |
| Auditor | task-verification | 2 | Uses `mode: full` for cross-task regression check |
| Test-writer | tdd-red | 5 | Verifies all tests FAIL; Quality-Runner reports failure details |

### 3d. Nesting Depth Validation

Orchestrator → Pipeline Agent → Quality-Runner = **L2 nesting**. Maximum depth is **5** (S1). L2 is well within limits. No further nesting from Quality-Runner is expected (it runs commands, not subagents).

Setting `chat.subagents.allowInvocationsFromSubagents` is already enabled in `.vscode/settings.json` (S6). No configuration change needed.

### 3e. Context Savings Estimate

| Agent | Current test/lint context (tokens) | With Quality-Runner (tokens) | Savings |
|-------|------------------------------------|------------------------------|---------|
| Builder | ~2000-4000 (multiple pytest/ruff outputs) | ~200-400 (structured summary) | 80-90% |
| Reviewer | ~1500-3000 (pytest + ruff + coverage outputs) | ~200-400 | 80-87% |
| Auditor | ~3000-6000 (full suite output) | ~300-500 | 85-92% |
| Test-writer | ~800-1500 (verify failures + ruff) | ~150-300 | 75-80% |

These savings reduce context pollution, leaving more room for code analysis and decision-making.

### 3f. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Quality-Runner failure blocks pipeline | Medium | Keep execute/* tools on all agents as fallback; skill docs reference direct commands |
| Structured output parsing errors | Low | Quality-Runner returns plain text sections, not JSON; agents pattern-match |
| Multiple invocations per builder step | Low | Builder already runs pytest 2-3x per task; subagent overhead < context savings |
| Reviewer loses direct terminal visibility | Low | Reviewer can read Quality-Runner's detailed output; tools kept as fallback |

### 3g. Scope Assessment

8 files changed (4 agent.md + 4 skill.md). Agent.md changes are 1 line each. Skill changes are ~5-15 lines each (replacing command examples with invocation patterns). Total diff: ~40-70 lines. This is formulaic and fits a single task scope. No decomposition needed.

## 4. Recommendation (.85 confidence)

Wire Quality-Runner into all 4 pipeline agents in a single task after #263 completes. The changes are formulaic: add `agents: [quality-runner]` to each agent's frontmatter, and update each skill's test/lint steps to delegate to Quality-Runner while keeping direct commands documented as fallback.

**Recommended AC refinement for #264:**

- [ ] Builder, reviewer, auditor, test-writer agent.md files have `agents: [quality-runner]`
- [ ] tdd-workflow skill Steps 3/4/5/7 reference Quality-Runner invocation pattern
- [ ] code-review skill Steps 3/4/5 reference Quality-Runner invocation pattern
- [ ] task-verification skill Step 2 references Quality-Runner invocation (mode: full)
- [ ] tdd-red skill Step 5 references Quality-Runner invocation pattern
- [ ] Each skill retains direct command fallback referencing pytest-and-linting skill
- [ ] No existing execute/* tools removed from any agent

**Open dependency:** This task is blocked by #263 (Quality-Runner creation) and decision 228-esub-utility-subagents. No new tasks needed — #264 has correct scope.

## 5. Follow-up Tasks

No new tasks needed. Task #264 already captures the correct scope. Task #263 (prerequisite) already exists. Decision 228-esub-utility-subagents is pending user approval.

One potential future optimization (not blocking):

```
kanban\kanban-md.exe create "Evaluate execute/* tool removal from reviewer agent" --priority nice-to-have --status ideation --tags scope:agents,phase-2 --body "After Quality-Runner is wired in and validated, evaluate whether the reviewer agent can drop execute/* tools entirely. The reviewer only uses terminal for pytest and ruff — both now handled by Quality-Runner. Removing execute/* tools would enforce the read-only boundary more strictly. Requires validation that no edge-case terminal usage exists."
```
