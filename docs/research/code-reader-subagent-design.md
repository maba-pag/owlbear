# Code-Reader Subagent Design Validation

> **Owning task:** #307 — Create Code-Reader subagent (agent.md)
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #307 (created by #265 research) calls for a read-only Code-Reader subagent that runs steps 6.0–6.6 and 7.1–7.4 of the code-review skill in parallel with a Quality-Runner. The reviewer coordinator dispatches both, then synthesizes their reports at step 8. This research validates the design is implementable and the AC is complete.

**Key questions:** (1) Is assign-mode with read+search tools sufficient? (2) What model should it use? (3) Are there gaps in the AC?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — coordinator/worker pattern, "Thorough Reviewer" multi-perspective review |
| S2 | VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — assign mode, `agents:` override of `disable-model-invocation`, `user-invocable` |
| S3 | OwlBear reviewer-parallel-fan-out research | docs/research/reviewer-parallel-fan-out.md §3b | .95 — Code-Reader interface design, I/O contracts, tool list |
| S4 | OwlBear subagent-nesting-architecture research | docs/research/subagent-nesting-architecture.md §3c | .90 — assign vs inherit analysis, tool counts (~43 inherit vs ~30 assign) |
| S5 | OwlBear code-review skill | skills/code-review/SKILL.md steps 6–7 | .95 — exact steps the Code-Reader must execute |

## 3. Analysis

### 3a. Tool Surface Validation

| Tool | Purpose | Required? |
|------|---------|-----------|
| `read/readFile` | Read source/test files for analysis | Yes — core function |
| `read/viewImage` | View image files if referenced | Yes — completeness |
| `read/problems` | Check compile/lint errors in files | Yes — step 6.1 security, 7.1 style |
| `search` | Find code patterns, usages, definitions | Yes — steps 6.5, 6.6, 7.4 |
| `vscode/memory` | Access repo memory for conventions | Yes — context for quality judgments |

**Missing from §3b:** None. These 5 tools cover all read-only analysis operations. `vscode_listCodeUsages` is part of the `search` toolset (S2), so it's included. No terminal/edit/MCP tools needed (.90 confidence).

**Assign vs Inherit:** Assign is correct (.90 confidence). Inherit gives ~43 tools including `execute/runInTerminal`, `edit/editFiles`, and MCP servers — all unnecessary and risky for a read-only agent. Assign enforces the read-only boundary architecturally, not just by instruction (S2, S4).

### 3b. Model Selection

| Option | Pros | Cons | Confidence |
|--------|------|------|------------|
| Same as reviewer (Sonnet 4.6 / GPT-5.4) | Strong reasoning for security review, test quality | Higher cost per invocation | .85 |
| Lighter model (Haiku 4.5 / Flash) | Cheaper, faster | May miss subtle security issues in step 6.1 | .50 |

**Recommendation:** Same as reviewer (.85 confidence). Steps 6.1 (security review) and 6.3 (test quality) require nuanced reasoning about subtle vulnerabilities and assertion adequacy. This matches VS Code docs showing coordinator/worker can each specify their own model (S1). The reviewer-parallel-fan-out research concurs (S3, §4 table).

### 3c. Frontmatter Design

| Field | Value | Rationale |
|-------|-------|-----------|
| `name` | `code-reader` | Matches OwlBear naming convention |
| `user-invocable` | `false` | Subagent-only; hidden from picker (S2) |
| `disable-model-invocation` | `true` | Pipeline-only agent; reviewer's `agents: ['code-reader']` overrides (S2) |
| `tools` | 5 read+search tools (assign mode) | Minimal surface; enforces read-only (S4) |
| `agents` | `[]` | Leaf worker — no subagent spawning |
| `model` | `[Claude Sonnet 4.6 (copilot), GPT-5.4 (copilot)]` | Strong reasoning for security/quality |

### 3d. AC Gap Analysis

| Current AC | Assessment |
|------------|------------|
| `code-reader.agent.md` exists with assign-mode tools | Complete |
| Covers steps 6.0–6.6 and 7.1–7.4 | Complete — instructions must reference skill sections |
| Returns structured text report per §3b output contract | Complete — 8 output sections defined |
| Read-only: no terminal execution or file editing tools | Complete — enforced by assign mode |

**Gaps found:**

1. **Missing AC: `disable-model-invocation: true` + `agents: []`** — prevents uncontrolled invocation and subagent spawning. Add to AC.
2. **Missing AC: model specification** — should specify reviewer-grade models. Add to AC.
3. **Missing AC: input contract documentation** — the agent body should document what the coordinator passes (task_id, AC lines, changed_files, test_files). Already specified in §3b but not in AC.

### 3e. Dependency Status

| Dependency | Status | Impact |
|------------|--------|--------|
| Decision 228-parallel-fan-out | Pending (approved: false) | **Blocking** — task explicitly depends on approval |
| Quality-Runner agent (#263) | Unknown | Not a direct dependency for Code-Reader creation, but reviewer wiring (#265) needs both |

The Code-Reader agent file can be designed and built independently — it's a standalone `.agent.md` file. However, it can't be wired into the reviewer until decision 228 is approved and the reviewer updated (#265).

## 4. Recommendation (.90 confidence)

The Code-Reader design from §3b is **sound and implementable**. Assign mode with 5 read+search tools, reviewer-grade models, and the 8-section output contract. Three AC lines should be added for completeness. The task can proceed to backlog despite the pending decision — the agent file can be built and tested independently; wiring it into the reviewer is #265's scope.

## 5. Follow-up Tasks

No new follow-up tasks needed — #307 IS the implementation task. AC refinements recommended:

- Add: `disable-model-invocation: true` and `agents: []` in frontmatter
- Add: model matches reviewer (Sonnet 4.6 / GPT-5.4)
- Add: input contract documented in agent body (task_id, ac_lines, changed_files, test_files)

These refinements will be appended to the task body via Channel B.
