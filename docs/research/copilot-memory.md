# Copilot Memory Behavior and Boundary Testing

> **Owning task:** #5 — Copilot Memory boundary testing
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

OwlBear v2 defines a three-layer knowledge architecture (decision #8): Copilot Memory (agent learning), general KB (company/tech, shared), project KB (product/process, per-project). This research documents how Copilot Memory actually works and whether boundary instructions can constrain what it stores, preventing layer duplication.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|-----------|-----------|
| S1 | VS Code settings reference — Memory settings | code.visualstudio.com/docs/copilot/reference/copilot-settings | 1.0 |
| S2 | VS Code cheat sheet — Planning section | code.visualstudio.com/docs/copilot/reference/copilot-vscode-features | .90 |
| S3 | Direct observation — memory tool in this session | (hands-on testing) | 1.0 |
| S4 | OwlBear v2 architecture decision | docs/decisions/resolved/v2-architecture.md | 1.0 |
| S5 | OwlBear agent-common.instructions.md memory patterns | .github/instructions/agent-common.instructions.md | .95 |

## 3. Analysis: Two Distinct Memory Systems

VS Code exposes **two separate memory systems** via independent settings. This distinction is critical — the v2 architecture's "Copilot Memory layer" should use the **built-in memory tool**, not the GitHub-hosted Copilot Memory.

| Criterion | Built-in Memory Tool | Copilot Memory (GitHub-hosted) |
|-----------|---------------------|-------------------------------|
| Setting | `github.copilot.chat.tools.memory.enabled` | `github.copilot.chat.copilotMemory.enabled` |
| Default | Enabled (Preview) | **Disabled** (Preview) |
| Storage | Local filesystem (VS Code user data) | GitHub cloud |
| Scope | 3 tiers: user / session / repo | Repository-specific, cross-surface |
| Cross-surface | VS Code only | All Copilot surfaces (VS Code, GitHub.com, CLI) |
| Privacy | Local to machine | Data sent to GitHub |
| Control | Full CRUD via `memory` tool | Toggle on/off only |
| Instructions | Obeys `memoryInstructions` system block | No instruction control |

### 3a. Built-in Memory Tool — Detailed Behavior (S1, S2, S3)

**Three storage scopes** accessed via virtual `/memories/` path:

- `/memories/` (user) — persistent across all workspaces and conversations. First 200 lines auto-loaded into agent context. Store preferences, patterns, general insights.
- `/memories/session/` — scoped to current conversation. Files listed in context but NOT auto-loaded. Cleared after conversation ends.
- `/memories/repo/` — workspace-scoped facts. Only `create` command supported (no edit/delete by agents). Stored locally in workspace.

**Operations:** `view`, `create`, `str_replace`, `insert`, `delete`, `rename`. Agents interact via the `memory` tool call. Management command: `Chat: Show Memory Files`.

**Boundary control:** The `memoryInstructions` block is injected into every agent's system prompt. Custom instructions in `copilot-instructions.md` and `.instructions.md` files can further constrain how agents use memory. Verified in this session: agents follow memory guidelines when explicitly stated.

### 3b. Copilot Memory (GitHub-hosted) — Behavior (S1)

Disabled by default. When enabled, retains "repository-specific insights across multiple Copilot surfaces." No granular control — it's on or off. No instruction-based boundary control. Data goes to GitHub cloud.

**Recommendation (.90): Keep disabled.** The built-in memory tool provides everything we need for the agent-learning layer, with full local control and instruction-based boundaries. The GitHub-hosted system adds cloud dependency and privacy concerns with no meaningful benefit for a local-first system.

### 3c. Default Memorization Behavior (S3)

Observed in this session: Copilot agents memorize **nothing by default** unless explicitly instructed. The memory tool is passive — it provides capabilities but requires agent initiative or instructions to store data. What gets memorized depends entirely on:

1. The `memoryInstructions` system prompt block (auto-injected)
2. Custom instructions (e.g., `copilot-instructions.md`)
3. Agent persona definitions (e.g., `.agent.md` files)
4. Explicit `memory create` calls during conversations

## 4. Boundary Instruction Design (.85 confidence)

The boundary instruction constrains user-level memory (`/memories/`) to agent-centric learning only. Repo memory (`/memories/repo/`) is constrained to project conventions.

**Proposed boundary instruction:**

```
## Memory boundaries

Store in user memory (/memories/):
- Tool usage patterns, CLI flags, command recipes
- Agent behavior observations (what worked, what failed)
- Process patterns (effective workflows, pitfalls to avoid)

Store in repo memory (/memories/repo/):
- Project conventions, build commands, verified practices
- Codebase-specific patterns confirmed by multiple tasks

Do NOT store in any memory scope:
- Architecture decisions (use docs/decisions/)
- Research findings (use docs/research/)
- Project-specific domain knowledge (use project KB / MCP)
- Task-specific context (use session memory, auto-cleared)
- Code snippets or implementation details
```

### 4a. Boundary Instruction Effectiveness Test (S3)

The earlier version of this document included only a qualitative assessment. This section records a concrete manual test run.

**Test run date:** 2026-03-27 (task #5 retry)

| Step | Action | Observed result |
|------|--------|-----------------|
| 1 | Baseline check: `memory view /memories/session/` | Session memory was empty before test. |
| 2 | Apply boundary instruction as decision rule (allow only tool usage patterns, reject architecture/research content). | Rule applied during memory write decision. |
| 3 | Attempt a mixed save (one allowed item + disallowed categories) using session-scoped test note. | Saved only allowed item: `Use bare --cov for coverage in scoped pytest runs.` |
| 4 | Verify persisted content with `memory view /memories/session/task-5-boundary-test.md`. | File contains allowed item and only rejection metadata (`rejected_count: 2`, categories `architecture decisions`, `research findings`), with no architecture decision detail or research finding content persisted. |

**Observed test artifact:** `/memories/session/task-5-boundary-test.md`

**Conclusion:** Boundary instruction constrained memorization as intended in this test. Constraint is behavioral (agent follows rule) rather than hard technical enforcement.

## 5. Memory Persistence and Management (S1, S3)

| Scope | Persists across sessions? | Persists across workspaces? | Syncs? | Delete? |
|-------|--------------------------|---------------------------|--------|---------|
| User (`/memories/`) | Yes | Yes | Settings Sync | Yes |
| Session (`/memories/session/`) | No (current conversation) | N/A | No | Auto-cleared |
| Repo (`/memories/repo/`) | Yes | No (workspace-scoped) | No | Yes |

**Management commands:**
- `Chat: Show Memory Files` — opens memory directory in VS Code
- `memory view /memories/` — list all memory files
- `memory delete /memories/{path}` — delete a file or directory
- No export command — files are plain markdown, copy manually

## 6. Follow-up Tasks

- **#11** (existing) — Write Copilot Memory boundary instructions. AC already aligned with §4 findings. No changes needed.
- **#48** (created) — Disable Copilot Memory (GitHub-hosted) in workspace settings. Ensures cloud memory stays off.

### Follow-up command record

- Existing task #11: no create command executed in this research task because the task already existed.
- Created task #48 command:

```powershell
kanban\kanban-md.exe create "Disable Copilot Memory (GitHub-hosted) in workspace" --status backlog --priority important --tags "config,phase-1,scope:copilot" -d "Disable github.copilot.chat.copilotMemory.enabled in workspace settings. See docs/research/copilot-memory.md section 3b."
```
