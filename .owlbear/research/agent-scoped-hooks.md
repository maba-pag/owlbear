# Agent-Scoped Hooks: Tool Access, Lifecycle, and Pipeline Enforcement

> **Owning task:** #37 — Research agent-scoped hooks for tool access, lifecycle, and pipeline enforcement
> **Date:** 2026-04-04 **Status:** Complete
>
> **Relationship to #86:** Task #86 (archived) produced `docs/research/agent-scoped-hooks-pipeline-enforcement.md` —
> a 5-candidate evaluation of VS Code hooks for pipeline enforcement. This document extends that work
> with a per-agent guard catalog, lifecycle hook evaluation, boundary enforcement map, and exception paths
> per #37's distinct AC. VS Code hooks docs were updated 4/1/2026 with new capabilities not covered by #86.

## 1. Context and Question

OwlBear has 14 agents with varying write permissions. Pipeline discipline is enforced through
instruction-based rules ("never write to X") and `tools:` list restrictions. Two hooks are deployed:
PostToolUse lint guard (builder) and PreToolUse deny-writes (reviewer). Task #37 asks: what additional
guards, lifecycle hooks, and boundary enforcement are needed — and how should they be registered?

## 2. Sources Studied

| # | Source | Location/URL | Relevance |
|---|--------|-------------|-----------|
| 1 | VS Code Agent Hooks docs (4/1/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — canonical spec, updated with `updatedInput`, `env`, PostToolUse `decision: "block"` |
| 2 | OwlBear #86 research | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` | 1.0 — 5-candidate evaluation, recommendation matrix, rollout guidance |
| 3 | OwlBear #374 stop-hook removal | `docs/research/stop-commit-guard-defect-remediation.md` | 1.0 — parallel-agent deadlock evidence |
| 4 | OwlBear agent files (14) | `.github/agents/*.agent.md` | 1.0 — current tools, hooks, and permissions inventory |
| 5 | OwlBear pipeline protocol | `.github/skills/r-pipeline-protocol/SKILL.md` | 1.0 — boundary rules (DR namespace, commit discipline) |
| 6 | OwlBear TDD-RED skill | `.github/skills/w-tdd-red/SKILL.md` | 1.0 — test-writer boundary: "never create or edit files in src/" |

## 3. Analysis

### 3.1 Tool-Use Guards Catalog per Agent Role (AC1)

| Agent | Write Tools | Current Guard | Needed Guard | Priority | Mechanism |
|-------|-------------|-------------|--------------|----------|-----------|
| builder | Full (edit/*, create) | PostToolUse lint ✅ | ~~docs/decisions/ deny~~ *(low frequency)* | — | Instruction sufficient |
| test-writer | Full (edit/*, create) | None | **PreToolUse: deny writes to `packages/`** | High | Hook candidate |
| reviewer | None in tools list | PreToolUse deny-writes ✅ | Complete (defense-in-depth) | — | Hook deployed |
| architect | Full (edit/*, create) | None | Low — edits task bodies via MCP, not code | — | Instruction sufficient |
| researcher | Full (edit/*, create, web) | None | Low — creates docs/research/ only | — | Instruction sufficient |
| doc-writer | Full (edit/*, create) | None | **PreToolUse: deny writes to `packages/`** | Medium | Hook candidate |
| planner | Full (edit/*, create) | None | Low — creates docs and kanban tasks | — | Instruction sufficient |
| curator | Full (edit/*, create, rename) | None | Low — manages memory files only | — | Instruction sufficient |
| scribe | createFile only | None | Low — sole DR namespace handler | — | Instruction + tool-list |
| auditor | None | None | Complete via tools restriction | — | Tool list |
| orchestrator | readFile, agent only | None | Complete via tools restriction | — | Tool list |
| dispatcher | readFile, terminal | None | Complete via tools restriction | — | Tool list |
| code-reader | readFile, search only | None | Complete via tools restriction | — | Tool list |
| challenger | readFile, search only | None | Complete via tools restriction | — | Tool list |

**Key finding:** Only 2 agents need additional hook guards: **test-writer** (high — most common boundary
violation is writing source code) and **doc-writer** (medium — should not modify source packages).

### 3.2 Agent Start/Stop Lifecycle Hooks (AC2)

| Hook Event | Use Case | Value | Feasibility | Confidence |
|-----------|----------|-------|-------------|------------|
| **SessionStart** | Inject project context (branch, recent commits, active task) | Medium — reduces cold-start errors | .80 — `additionalContext` output is clean | .70 |
| **SubagentStart** | Audit log: which subagent dispatched, when, for what | Medium — dispatch tracing | .75 — `agent_type` field identifies subagent | .65 |
| **SubagentStop** | Verify deliverables exist after subagent completes | High — catches silent failures | .45 — limited to orchestrator scope; can't query files without tools | .40 |
| **Stop** | Commit guard (remind to commit) | Low — removed in #374 due to parallel-agent deadlock | .85 deadlock evidence | Skip |
| **PreCompact** | Export critical context before context window truncation | Low — rare trigger, hard to test | .60 — `trigger: "auto"` input is simple | .35 |

**Start hooks (recommended):**
- `SessionStart` injecting `additionalContext` with git branch + recent commits is low-cost, high-payoff.
  Script: `scripts/hooks/session-context.ps1`. Apply to pipeline agents with write permissions.

**Stop hooks (skip):**
- Stop commit guard remains infeasible for parallel subagent dispatch (#374 evidence).
- SubagentStop for deliverable verification is too limited (no tool access in hook context).

### 3.3 Pipeline Boundary Enforcement Map (AC3)

| Boundary | Current Enforcement | Violation Frequency | Hook Candidate | Confidence |
|----------|-------------------|-------------------|---------------|------------|
| test-writer must not write `packages/` | Instruction: w-tdd-red §5 | **High** — most common boundary violation | PreToolUse deny `packages/` paths | .80 |
| builder must not write `docs/decisions/` | Instruction: pipeline-protocol §1 | Low — builder rarely touches DR files | Instruction sufficient | — |
| builder must not modify `TestFromAC` classes | Instruction: w-tdd-green | Medium — hard to detect via hooks (need file content, not just path) | **Infeasible** via hooks (.30) | Skip |
| only scribe writes `docs/decisions/` | Instruction: pipeline-protocol §1 | Low — agents delegate to scribe subagent | Per-agent hook, but low ROI | Skip |
| doc-writer must not write `packages/` | Implicit (no instruction) | Low — doc-writer focuses on docs/ | PreToolUse deny `packages/` paths | .65 |
| reviewer is read-only | tools: restriction + PreToolUse hook | None observed since hook deployed | **Complete** ✅ | — |

**New since #86:** VS Code PreToolUse now provides `tool_input` with `filePath` (source [1]). Path-based
guards are feasible: script reads `tool_input.filePath`, checks against a deny-list of directory
prefixes, returns `permissionDecision: "deny"` for violations. This was assessed at .65 in #86 C5;
with `tool_input.filePath` confirmed, test-writer path enforcement rises to .80.

### 3.4 Hook Registration Mechanism (AC4)

**Established pattern** (from #86 implementation + VS Code 4/1/2026 spec):

| Scope | Location | When to Use | OwlBear Example |
|-------|----------|-------------|-----------------|
| Per-agent | `.agent.md` frontmatter `hooks:` | Agent-specific enforcement | builder: lint guard, reviewer: deny-writes |
| Workspace | `.github/hooks/*.json` | Cross-agent policy (fires for all agents) | Session context injection (all agents) |
| User | `~/.copilot/hooks/` | Personal overrides | Not used |
| Custom paths | `chat.hookFilesLocations` setting | Non-standard locations | Not used |

**Compatibility with MCP architecture:** Hooks and MCP tools are orthogonal. Hooks fire at VS Code
lifecycle events; MCP tools respond to tool calls. No conflict. The `owlbear-kanban/*` MCP tools
are unaffected by hooks — a PreToolUse hook cannot intercept MCP tool calls (MCP tools are server-side;
hooks intercept VS Code-native tools only). This limits boundary enforcement to file-editing tools.

**New capability (4/1/2026):** `updatedInput` in PreToolUse output can MODIFY `tool_input` before
execution. Theoretical use: rewrite file paths. Practical use: none recommended (path rewriting is
fragile and confuses the agent).

### 3.5 Exception Paths (AC5)

| Exception | Current Handling | Recommended Approach |
|-----------|-----------------|---------------------|
| Reviewer making minor test fixes | Reviewer has no write tools; delegates to builder subagent | No change — subagent delegation is the correct pattern |
| Builder writing "builder-discovered" tests | Allowed per pipeline protocol ("source code + builder-discovered tests") | No hook restriction on `tests/` for builder |
| Test-writer fixing test infrastructure | May need to edit `conftest.py` in `tests/` (allowed) but not `packages/` | Path-guard denies `packages/` only; `tests/` writes are allowed |
| Doc-writer editing README.md at repo root | Allowed — doc-writer owns all documentation including root-level | Path-guard denies `packages/` only; root files are allowed |
| Agent editing hook scripts themselves | Safety risk — agent could disable its own guard | Use `chat.tools.edits.autoApprove` to require manual approval for `scripts/hooks/` edits |

## 4. Recommendation (.78 confidence)

**Challenge:** FALLBACK — challenger not available in researcher mode.

**Phase 3 (next):** Add PreToolUse path guard to test-writer — highest-value undeployed hook.
Script: `scripts/hooks/deny-src-writes.ps1`. Denies writes to `packages/` directory. ~25 LOC.

**Phase 4 (optional):** Add SessionStart context injection to write-capable pipeline agents.
Script: `scripts/hooks/session-context.ps1`. Injects branch + recent commits. ~30 LOC.

**Phase 5 (optional):** Add PreToolUse path guard to doc-writer (same script as test-writer).

**Skip permanently:** Stop hooks (deadlock), SubagentStop verification (limited), TestFromAC guards
(need file content not available in hook stdin), cross-agent DR namespace enforcement (low ROI).

| Phase | Hook | Agent(s) | Value | Effort | Confidence |
|-------|------|----------|-------|--------|------------|
| 3 | PreToolUse path guard | test-writer | High | Low (~25 LOC) | .80 |
| 4 | SessionStart context | builder, test-writer, doc-writer | Medium | Low (~30 LOC) | .70 |
| 5 | PreToolUse path guard | doc-writer | Low-medium | Trivial (reuse Phase 3 script) | .65 |

## 5. Follow-up Tasks

Created at `ideation` status — see task IDs below.

| # | Title | Priority | One-line AC |
|---|-------|----------|-------------|
| #589 | Add PreToolUse path guard hook to test-writer agent (Phase 3) | nice-to-have | PreToolUse hook on test-writer denies writes to `packages/`; script reads `tool_input.filePath` |
| #590 | Add SessionStart context injection hook to pipeline agents (Phase 4) | someday | SessionStart hook injects git branch + recent commits via `additionalContext` |
| #591 | Add PreToolUse path guard hook to doc-writer agent (Phase 5) | someday | PreToolUse hook on doc-writer denies writes to `packages/`; reuses Phase 3 script (#589) |

**Tier classification:** All findings are T1 (autonomous implementation). No new capabilities, no
architecture changes, no security policy changes. These are incremental additions to an established
hook pattern (Phases 1-2 already deployed and validated).
