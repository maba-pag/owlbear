# MCP Tool Reference Test Validation

> **Owning task:** #572 — P2-01: Test — Validate MCP tool references in agents, skills, instructions
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #572 requires a RED-phase test file (`tests/test_mcp_tool_references_483.py`) that validates MCP tool references exist alongside CLI in agents, skills, and instructions. A prior attempt exists (references task #562). This research validates the existing file against #572's AC and identifies gaps for the test-writer.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | tests/test_mcp_tool_references_483.py | Codebase | .95 — existing test to audit |
| 2 | docs/research/mcp-tool-references-alongside-cli.md | Research | .90 — prior CLI-to-MCP mapping |
| 3 | skills/mcp-kanban/SKILL.md | Codebase | .90 — MCP tool surface |
| 4 | 11 agent .agent.md files | Codebase | .85 — CLI patterns to validate |
| 5 | 14 skill SKILL.md files (AC list) | Codebase | .85 — CLI/section structure |
| 6 | agent-common.instructions.md | Codebase | .85 — CLI refs needing MCP pairs |

## 3. Analysis

### 3a. Existing Test Coverage vs AC

| AC Item | Existing Coverage | Gap |
|---------|-------------------|-----|
| test file exists at correct path | ✅ Full | None |
| 11 agents with MCP tool patterns | ❌ 10/11 (scribe excluded) | +1 agent (scribe) |
| 14 skills with MCP alternatives | ❌ 8/14 (cheatsheet skills only) | +6 skills, but see 3b |
| mcp-kanban SKILL.md workflow pattern | ✅ Tests Agent Workflow heading | Partial — missing Channel B, per-tool existing content |
| agent-common + research-docs MCP syntax | ✅ Full | None |
| All tests fail on current HEAD | ✅ Confirmed | None |

### 3b. Semantic Classification of 14 AC-Listed Skills

The AC lists 14 skills, but not all references are actionable CLI commands needing MCP pairs:

| Skill | Ref Type | Needs MCP? | Expected MCP Tools |
|-------|----------|-----------|-------------------|
| arch-review | Cheatsheet + inline | Yes | show-task, edit_task, create_task, start_work, end_work |
| code-review | Cheatsheet + inline | Yes | show-task, edit_task, start_work, end_work |
| curation-workflow | Cheatsheet | Yes | show-task, edit_task |
| docs-gate | Cheatsheet + inline | Yes | show-task, edit_task, start_work, end_work |
| task-decomposition | Cheatsheet + inline | Yes | list_tasks, show-task, edit_task, create_task |
| task-verification | Cheatsheet + inline | Yes | show-task, edit_task, start_work, end_work |
| tdd-red | Cheatsheet + inline | Yes | show-task, edit_task, start_work, end_work |
| tdd-workflow | Cheatsheet + inline | Yes | show-task, edit_task, start_work, end_work |
| decision-requests | Inline (block/unblock) | Yes | edit_task |
| dispatch-planning | Inline (list/show) | Yes | list_tasks, show-task |
| research-workflow | Inline (edit status) | Yes | edit_task, end_work |
| kanban-md | Claiming protocol | Yes | start_work, edit_task, end_work |
| orchestration | Context ref (what agents do) | Borderline | show-task at most |
| pytest-and-linting | Marker description | **No** | None — ref is `Requires the kanban-md binary` |

**Result:** 12 skills genuinely need MCP alternatives. 1 is borderline (orchestration — describes what agents do, not a command recipe). 1 does not (pytest-and-linting — test marker, not CLI invocation). The AC count of 14 appears derived from a naive grep.

### 3c. Test Assertion Strategy for Inline-Ref Skills

The existing test checks `## kanban-md Commands` sections. The 4-6 missing skills lack this section. Two viable approaches:

| Approach | Pros | Cons |
|----------|------|------|
| A: Check whole body for MCP tool names | Simple, catches any addition | May pass on tangential mentions |
| B: Check specific sections where CLI refs appear | Precise, validates co-location | Requires per-skill section mapping |

**(rec:) Approach A** for the 4-6 inline-ref skills — the test is RED-phase, so false passes aren't possible (zero MCP refs exist). The builder adding MCP refs will naturally place them near CLI refs.

### 3d. Tool-Name Assertions Beyond start_work/end_work

Existing test only checks `start_work` and `end_work`. The challenger correctly noted this misses skill-specific tools:

- **kanban-planner** primarily uses `create_task`, `list_tasks` — not start/end lifecycle
- **task-decomposition** uses `create_task`, `list_tasks`, `show-task`
- **architect** uses `show-task`, `edit_task`, `create_task`

Minimum assertion per file should check for at least one of the file's *relevant* MCP tools, not just the compound tools. But parametrized tests are cleanest with uniform assertions. Recommend: keep `start_work`/`end_work` as the baseline (all agents use the lifecycle), add `edit_task` as a third check (all agents write Channel B).

### 3e. Scribe Agent — Most Acute Gap

The scribe already declares `'owlbear-kanban/*'` in its YAML `tools:` list but exclusively documents CLI syntax in its body (4 CLI refs, 0 MCP refs). This is the most inconsistent agent — it has MCP access but no MCP guidance.

### 3f. mcp-kanban SKILL.md — Per-Tool Params Already Exist

The Tools table (lines 18-26) already lists all 8 tools with key parameters. The AC item "per-tool parameter reference" is partly satisfied. What's missing: (a) Agent Workflow section, (b) Channel B protocol section showing how `edit_task(append_body=...)` replaces CLI `-a` flag.

## 4. Recommendation (.80 confidence)

The existing test file is a strong foundation (~60% AC coverage). The test-writer should augment it with 5 changes:

1. **Add scribe to PIPELINE_AGENTS** (10 → 11)
2. **Add parametrized tests for 4 inline-ref skills** (decision-requests, dispatch-planning, research-workflow, kanban-md) checking whole-body for relevant MCP tool names
3. **Add `edit_task` assertion** to agent and cheatsheet-skill parametrized tests (beyond just start_work/end_work)
4. **Add mcp-kanban SKILL.md tests** for Channel B protocol heading
5. **Fix docstring** task reference (#562 → #572)

For orchestration: include if AC is taken literally, but the assertion should be lenient (any MCP tool name in body). For pytest-and-linting: exclude — the ref is not an invocable command.

Challenge: reconsider — confidence in original: .65. Challenger raised valid concerns about semantic classification (accepted — refined in 3b), scribe urgency (accepted — elevated in 3e), tool-name specificity (accepted — addressed in 3d), inline assertion pattern (accepted — addressed in 3c). T1 classification maintained.

## 5. Follow-up Tasks

No new tasks needed — #572 is the test task itself and is ready for the test-writer. Sibling tasks #573-#576 handle the implementation. The 5 augmentations above are within #572's existing scope.
