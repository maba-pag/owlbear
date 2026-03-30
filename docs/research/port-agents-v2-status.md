# Port Agents to .agent.md v2 — Status & Approach

> **Owning task:** #8 — Port agents to .agent.md format
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #8 requires porting all 11 v1 agents from `.github/agents/` to `agents/` at repo
root, replacing PydanticAI tool references with VS Code built-in + MCP tool names. Task
#4 (archived) validated the .agent.md format and produced the tool mapping. This research
assesses the current port status and identifies remaining work.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Task #4 research doc | `docs/research/agent-md-format.md` | .95 — complete tool mapping, 5 external sources |
| Git history `ec84b55` | Port commit `agents/` with v2 tool names | .95 — proves implementation works |
| Git history `6d76867` | Refactor commit that regressed tool names | .90 — root cause of regressions |
| `agent-common.instructions.md` | VS Code auto-staging trap documentation | .85 — known pitfall |
| Task #36 audit notes | Auditor's cross-task regression alert | .85 — first detection of regression |

## 3. Current State Assessment

### 3.1 Port Status by AC Line

| AC Line | Status | Evidence |
|---------|--------|----------|
| Port all 11 agents to `agents/` | DONE | All 11 files exist at `agents/*.agent.md` |
| `tools:` maps to VS Code/MCP names | REGRESSED | 11 agents use `todo` (should be `todos`); curator has `resolveMemoryFileUri` |
| `agents:` enables correct handoffs | DONE | Orchestrator lists 11 subagents; researcher has `[Explore]`; 9 leaf agents have `[]` |
| Test 2+ agents in Copilot Chat | DONE | Task #4 validated Explore, orchestrator delegation, reviewer tool restrictions |
| Update `settings.json` | DONE | `chat.agentFilesLocations` includes both `.github/agents` and `agents` |
| Delete `.github/agents/` v1 copies | DONE | Directory exists but is empty |

### 3.2 Test Results (current, 2026-03-29)

Test file `tests/test_agent_port_v2.py`: **13 failed, 28 passed**.

| Failure Category | Count | Root Cause |
|-----------------|-------|------------|
| `todo` not renamed to `todos` | 11 | Auto-staging regression |
| `resolveMemoryFileUri` in curator | 2 | Auto-staging regression |

### 3.3 Regression Root Cause

Commit `ec84b55` correctly ported all agents with `todos` and without
`resolveMemoryFileUri`. Commit `6d76867` ("Refactor test-writer and writer agents")
re-serialized all 11 agent files, reverting tool names to VS Code's auto-detected
values. This is the **VS Code auto-staging trap** documented in
`agent-common.instructions.md` line 113 and first detected by the auditor in task #36.

## 4. Analysis

### 4.1 Remaining Implementation (task #8 scope)

| Fix | Files | Effort | Risk |
|-----|-------|--------|------|
| `todo` → `todos` in tools lists | 11 agents | Trivial (1 token per file) | Re-regression from auto-staging |
| Remove `resolveMemoryFileUri` from curator | 1 agent | Trivial (delete 1 entry) | Same |

### 4.2 Auto-Staging Defense Options

| Option | KISS | YAGNI | Effectiveness | Recommendation |
|--------|------|-------|---------------|----------------|
| Pre-commit hook (grep check) | High | Medium | High — blocks bad commits | Recommended (.80) |
| CI check in GitHub Actions | High | Low | Medium — detects after push | Alternative |
| Test suite (already exists) | High | Already done | Medium — must be run manually | Keep |
| `.gitattributes` merge driver | Low | High | Low — doesn't prevent staging | Reject |

## 5. Recommendation (.90 confidence)

Task #8 is **ready for implementation** with a proven approach (commit `ec84b55`). The
remaining work is surgical: fix 13 tool references across 11 files, then validate with
the existing test suite. The auto-staging trap is the primary risk; a pre-commit hook
or explicit `git diff --cached agents/` check before committing is recommended as a
follow-up.

### Implementation Approach

1. Replace `todo` with `todos` in `tools:` list of all 11 agents
2. Remove `vscode/resolveMemoryFileUri` from `agents/curator.agent.md` tools list
3. Run `tests/test_agent_port_v2.py` — expect 41/41 pass
4. Commit with explicit `git diff --cached agents/` check before staging

### AC Refinement Suggestions for Architect

The existing AC is well-scoped. Suggest adding:
- AC: Run `tests/test_agent_port_v2.py` with 0 failures
- AC: Commit includes explicit auto-staging check (`git diff --cached agents/`)

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Add pre-commit guard against agent tool name regression" --priority nice-to-have --status ideation --tags phase-1,scope:agents,tooling --body "## Objective\nPrevent VS Code auto-staging from reverting agent tool name fixes.\n\n## Acceptance Criteria\n- [ ] Pre-commit hook or CI check that fails if any agents/*.agent.md tools: list contains bare 'todo' (not 'todos')\n- [ ] Check also fails if resolveMemoryFileUri appears in any agent file\n- [ ] Hook runs in < 1s\n- [ ] Documented in README or contributing guide"
```
