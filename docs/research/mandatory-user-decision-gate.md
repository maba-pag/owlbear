# Mandatory User-Decision Gate for Research-Driven Features

> **Owning task:** #385 — Mandatory user-decision gate for research-driven features and architectural changes
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Research findings bypass user approval. Agents create follow-up tasks at `ideation` that flow through the full pipeline without the user ever approving the direction. The decision-request skill exists but is optional — triggered only when "multiple valid options exist" or "confidence < .85." Single-option conclusions (the majority) skip user oversight entirely.

**Key questions:** (1) What gaps exist in the current workflow? (2) How should research outcomes be classified? (3) What changes enforce mandatory gates? (4) Should the 5-day auto-timeout apply to high-impact decisions?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Anthropic "Building Effective Agents" | anthropic.com/engineering/building-effective-agents | .90 |
| 2 | AutoGen Human-in-the-Loop docs | microsoft.github.io/autogen/stable/.../human-in-the-loop.html | .85 |
| 3 | CrewAI Tasks docs (human_input, guardrails) | docs.crewai.com/concepts/tasks | .75 |
| 4 | GitHub Actions Environment Protection Rules | docs.github.com/en/actions/.../managing-environments-for-deployment | .70 |
| 5 | OwlBear decision-requests skill | skills/decision-requests/SKILL.md | 1.0 |
| 6 | OwlBear agent-common instructions | instructions/agent-common.instructions.md | 1.0 |
| 7 | OwlBear researcher agent | agents/researcher.agent.md | 1.0 |
| 8 | OwlBear architect agent | agents/architect.agent.md | 1.0 |
| 9 | OwlBear extend-decision-request research | docs/research/extend-decision-request-for-action-requests.md | .85 |

## 3. Gap Analysis

| # | Gap | Current behavior | Impact |
|---|-----|-----------------|--------|
| G1 | Optional by default | Decision requests created only for multi-option/low-confidence | Features bypass user entirely |
| G2 | Agent self-gates | Researcher decides when user approval is needed | Fox-guarding-henhouse problem |
| G3 | No architect verification | Architect never checks for approved decision request | Research-driven tasks flow freely |
| G4 | Uniform auto-timeout | 5-day auto-resolve treats trivial and critical equally | High-impact decisions auto-approved |
| G5 | No outcome classification | No formal taxonomy of research outcome types | No trigger for mandatory gates |

**Prior art confirms gates are standard.** Anthropic's guide (S1) states agents should "pause for human feedback at checkpoints" and that "human review remains crucial for ensuring solutions align with broader system requirements." AutoGen (S2) uses `HandoffTermination` for structured control transfer. CrewAI (S3) has mandatory `human_input` flags and `guardrail` functions. GitHub Actions (S4) uses required-reviewer gates per environment. All four systems offer explicit, typed mechanisms for human-in-the-loop — none rely solely on agent judgment to decide when.

## 4. Classification System

### Tier-based research outcome classification

| Tier | Category | Decision required? | Auto-timeout | Examples |
|------|----------|--------------------|-------------|----------|
| **T1: Autonomous** | Bug fix, refactor, config, perf optimization | No | N/A | Root cause analysis, linter config, dep version bump |
| **T2: Advisory** | Library selection, approach with trade-offs | Advisory DR (urgency: advisory) | 5 days | sqlite-vec vs ChromaDB, WrapperToolset vs hook-based |
| **T3: Mandatory** | New feature, arch change, security policy, process change, breaking change | Blocking DR (urgency: blocking) | None (block indefinitely) | New agent capability, module restructure, pipeline change |

### Classification triggers (deterministic, not judgment-based)

A research outcome is **T3 (mandatory)** if ANY of these are true:

- Adds a capability that doesn't currently exist
- Changes the architecture of one or more modules
- Modifies agent instructions, skills, or pipeline behavior
- Alters security policy or safety boundaries
- Changes user-facing behavior or external interfaces
- Proposes deprecation or removal of existing functionality

A research outcome is **T2 (advisory)** if:

- Multiple implementation approaches exist with meaningful trade-offs
- AND none of the T3 triggers apply

Everything else is **T1 (autonomous)**: proceed directly.

### Why deterministic triggers, not confidence thresholds?

The current system relies on agent confidence (≥ .85 → proceed). This is subjective and unreliable — a researcher can be highly confident about a bad direction. Anthropic (S1) recommends "programmatic checks on intermediate steps" and AutoGen (S2) uses typed termination conditions, not agent self-assessment. The triggers above are checkable facts: either the outcome adds a new capability or it doesn't.

## 5. Auto-Timeout Proposal

| Option | T2 behavior | T3 behavior | KISS | Risk |
|--------|-------------|-------------|------|------|
| **A: Keep 5d for T2, remove for T3** (.85) | 5-day auto-resolve | Block indefinitely | High | T3 tasks stuck until user acts |
| B: Escalate instead of auto-resolve | 5-day escalation | Block indefinitely | Medium | Adds escalation mechanism |
| C: Remove auto-timeout entirely | Block indefinitely | Block indefinitely | High | Low-impact decisions also stuck |

**Recommendation (.85): Option A.** T2 decisions are low-impact approach selections — auto-resolve is safe. T3 decisions affect features, architecture, or security — auto-resolving defeats the purpose of the gate. Risk mitigation: planner surfaces "N pending mandatory decisions" at session start.

## 6. Required Changes (4 files)

| # | File | Change | Effort |
|---|------|--------|--------|
| C1 | `skills/decision-requests/SKILL.md` | Add `impact_tier` field (1/2/3); T3 blocks indefinitely; T2 keeps 5-day | Low |
| C2 | `agents/researcher.agent.md` | Add tier classification step after analysis; T3 = mandatory DR | Low |
| C3 | `skills/research-workflow/SKILL.md` | Update Step 5 with tier classification and decision tree | Low |
| C4 | `agents/architect.agent.md` | Add decision-request verification for research-driven tasks at backlog gate | Low |
| C5 | `instructions/agent-common.instructions.md` | Update defer-to-user triggers with tier classification reference | Low |

## 7. Recommendation (.85 confidence)

Adopt the 3-tier classification system with deterministic triggers. T3 (new features, arch changes, security, process changes) always require a blocking decision request that does NOT auto-resolve. T2 (approach selection with trade-offs) uses advisory decision requests with 5-day auto-timeout. T1 (bug fixes, refactors, config) proceeds autonomously.

**Risk:** Increased latency for T3 research — tasks block until user decides. Mitigated by planner surfacing pending decisions and user checking `docs/decisions/pending/` regularly.

## 8. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Update decision-requests skill with impact_tier field and T3 indefinite blocking" --priority needed --status ideation --tags "process,scope:agents,quality" --body "Add impact_tier (1/2/3) to decision-request frontmatter. T3 decisions block indefinitely (no auto-resolve). T2 keeps 5-day auto-timeout. Update file format section, resolution workflow, and planner integration notes. See docs/research/mandatory-user-decision-gate.md. AC: - [ ] impact_tier field in frontmatter (values: 1, 2, 3) - [ ] T3 decisions do not auto-resolve (planner skips 5-day timer for impact_tier=3) - [ ] T2 decisions keep current 5-day auto-resolve - [ ] Updated file format example showing impact_tier - [ ] Updated blocking behavior section documenting tier differences"
kanban\kanban-md.exe create "Update researcher agent and research-workflow skill with tier classification" --priority needed --status ideation --tags "process,scope:agents,quality" --body "Add mandatory tier classification step to research-workflow Step 5 and researcher agent boundaries. After completing analysis, researcher must classify outcome as T1/T2/T3 using deterministic triggers. T3 outcomes MUST create a blocking decision request. T1 proceeds directly. See docs/research/mandatory-user-decision-gate.md. AC: - [ ] research-workflow Step 5 has tier classification decision tree - [ ] researcher agent boundaries list T3 triggers explicitly - [ ] researcher critical_rules updated: T3 outcomes require blocking DR - [ ] Red flag added: creating follow-up tasks for T3 outcome without DR"
kanban\kanban-md.exe create "Add decision-request verification to architect backlog gate" --priority needed --status ideation --tags "process,scope:agents,quality" --body "Architect must verify that research-driven tasks (tagged 'research' or referencing a research doc) have an approved decision request before advancing past backlog. If no approved DR exists for a T3 outcome, reject to ideation. See docs/research/mandatory-user-decision-gate.md. AC: - [ ] Architect checks for approved DR when task references research doc - [ ] T3-origin tasks without approved DR are rejected to ideation - [ ] Architect red flag added: approving research-driven feature without DR - [ ] Architecture Review section notes DR verification result"
kanban\kanban-md.exe create "Update agent-common defer-to-user boundary with tier classification" --priority needed --status ideation --tags "process,scope:agents,quality" --body "Replace vague defer-to-user triggers with tier classification reference. Per-role triggers table should reference T1/T2/T3 system. Researcher trigger changes from 'finding recommends a feature or direction' to 'T3 outcome per research classification'. See docs/research/mandatory-user-decision-gate.md. AC: - [ ] Defer-to-user boundary references tier classification - [ ] Per-role triggers table updated with tier references - [ ] Researcher row references T3 mandatory gate explicitly"
```
