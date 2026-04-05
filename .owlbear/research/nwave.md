# nWave-ai/nWave Research

> **Owning task:** #589 — Research: nWave-ai/nWave
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Analyze [nWave](https://github.com/nWave-ai/nWave) (MIT) for multi-agent delegation, orchestration patterns, and task execution logic reusable in OwlBear. nWave is a Claude Code plugin framework with 23 agents, 98+ skills, and a Deterministic Execution System (DES) for TDD enforcement.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| nWave repo (cloned) | <https://github.com/nWave-ai/nWave> | 1.0 — primary |
| CrewAI Crews docs | <https://docs.crewai.com/concepts/crews> | 0.7 — prior art comparison |

## 3. Analysis

### 3.1 Architecture Overview

nWave uses a **wave-based pipeline** (DISCOVER > DISCUSS > DESIGN > DEVOPS > DISTILL > DELIVER) where each wave produces artifacts reviewed by humans before the next wave runs. The orchestrator (main Claude instance) delegates to specialized agents via Claude Code's `Task` tool, never implementing directly.

Key architectural components:

- **23 agents**: 12 specialists + 11 paired reviewers (every specialist has a reviewer)
- **Commands** (`.md` files with YAML frontmatter): entry points that define orchestration logic
- **Skills** (`.md` knowledge files): domain expertise loaded on-demand via Read tool
- **DES (Deterministic Execution System)**: Python enforcement layer using Claude Code hooks
- **Hexagonal architecture**: ports/adapters throughout the DES enforcement codebase

### 3.2 Patterns Comparison (nWave vs OwlBear vs CrewAI)

| Pattern | nWave | OwlBear | CrewAI |
|---------|-------|---------|--------|
| Delegation | Claude `Task` tool + DES markers | `DelegationToolset.delegate_to_agent()` | `allow_delegation` on Agent |
| Orchestrator | Main instance coordinates, never implements | PydanticAI orchestrator agent | `manager_agent` in hierarchical process |
| Enforcement | Hook-based (PreToolUse/PostToolUse/SubagentStop) | Hook system (`HookEvent`/`HookRegistry`) | `step_callback` / `task_callback` |
| Quality gates | DES blocks non-compliant prompts (exit code 2) | Approval gates (config-driven) | None built-in |
| Agent pairing | Every specialist has `-reviewer` (haiku model) | Separate reviewer agent (single) | No built-in reviewer pattern |
| Tool restriction | Per-agent `tools:` in frontmatter (least privilege) | Per-toolset registration at bootstrap | Per-agent `tools` list |
| Skill loading | On-demand Read of `.md` skill files per phase | `SkillsRegistry` loads skills into context | Knowledge sources on crew |
| Rigor profiles | 5 levels (lean/standard/thorough/exhaustive/custom) | None | None |
| Stale detection | `StaleExecutionDetector` (30min threshold on IN_PROGRESS) | None | None |
| Turn limits | Configurable per task type (15-50) | `MAX_DELEGATION_DEPTH=5` | `max_rpm` per crew/agent |
| Execution log | JSON append-only log per feature + JSONL audit trail | JSONL session files + ErrorJournal | `output_log_file` |

### 3.3 Patterns Worth Adopting

**P1: Rigor Profile System (.85 confidence)**
nWave's `/nw:rigor` command lets users dial quality vs. speed per task. Profiles control which model runs (haiku/sonnet/opus), whether review is enabled, TDD depth, and mutation testing. This maps directly to OwlBear's need to balance token cost against quality for different task types. Implementation: config key in `owlbear.toml` with profile presets, read at bootstrap, passed into agent dependencies.

**P2: Structured Reviewer Pairing (.80 confidence)**
Every nWave specialist agent has a paired reviewer agent using a cheaper model (haiku). Reviewers are strictly read-only, produce YAML-structured feedback with severity ratings (critical/high/medium/low), and have a 2-iteration maximum. OwlBear already has a reviewer agent, but it's singular. The pairing pattern (specialist + reviewer using cheaper model) is more cost-efficient for per-task review.

**P3: DES-Style Pre/Post Tool Hooks for Enforcement (.75 confidence)**
nWave uses Claude Code's hook protocol (JSON stdin/stdout, exit codes 0/1/2) to validate every `Task` invocation before and after execution. OwlBear already has `HookEvent`/`HookRegistry`, but lacks **blocking** pre-tool validation (the DES `PreToolUseService` pattern that can reject a delegation before it runs). This would strengthen approval gates.

**P4: Stale Execution Detection (.70 confidence)**
`StaleExecutionDetector` scans for tasks stuck in IN_PROGRESS beyond a configurable threshold. Simple pattern: scan kanban board for stale tasks, alert or auto-block. Useful for OwlBear's always-on daemon to detect stuck agent loops.

**P5: Turn Limits Per Task Type (.70 confidence)**
nWave configures turn limits by task complexity (quick=15, standard=30, complex=50). OwlBear currently only enforces `MAX_DELEGATION_DEPTH=5`. Adding per-task-type turn budgets would prevent runaway token consumption on simple tasks.

### 3.4 Patterns Not Worth Adopting

| Pattern | Reason |
|---------|--------|
| Wave pipeline (6 waves) | YAGNI — OwlBear's kanban pipeline (ideation > backlog > ... > done) already covers this |
| DES marker injection in prompts | Claude Code specific (`<!-- DES-VALIDATION : required -->`) — not portable to PydanticAI |
| Plugin/marketplace system | Claude Code specific — OwlBear is standalone daemon |
| Mutation testing enforcement | YAGNI — premature for current phase |
| Feature-ID derivation wizard | Already handled by kanban-md task creation |

## 4. Recommendation (.80 confidence)

Adopt P1 (rigor profiles) and P4 (stale detection) first — both are low-complexity, high-value additions. P2 (reviewer pairing) is a natural extension of existing reviewer pattern but lower priority until multi-agent delegation is more mature. P3 (blocking pre-tool hooks) and P5 (turn limits) are quality-of-life improvements that build on existing infrastructure.

Risk: Over-engineering enforcement (DES is ~60 Python files for what boils down to "validate prompts before/after delegation"). Keep OwlBear implementation KISS — rigor profiles are config, stale detection is a periodic scan.

## 5. Follow-up Tasks

See kanban commands below.
