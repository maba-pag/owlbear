# Pragmatist Voice Agent — Research

> **Owning task:** #646 — P4-06: Create pragmatist-voice.agent.md
> **Date:** 2026-04-06  **Status:** Complete

## 1. Context and Question

Task #646 requires creating the Pragmatist voice — a synthesis subagent that reads all domain voice outputs + context and produces `synthesis.md` for the Mediator. The spec is `thinking-companion-framework.md` §7, §12. Dependency: #645 (done — ideator.agent.md created, lists `pragmatist-voice` in its agents array).

**Key questions:** What tool set (read + write), frontmatter structure, and I/O contract? What AC items need refinement? Does `disable-model-invocation` apply?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `thinking-companion-framework.md` §7, §12 | Spec | 1.0 — defines Pragmatist role, I/O contract, Blackboard read/write rules |
| 2 | `share/agents/critic-voice.agent.md` | Codebase | 0.9 — closest structural pattern (voice subagent, disable-model-invocation, dual-scope prompt) |
| 3 | `share/agents/ideator.agent.md` | Codebase | 0.9 — invoking agent, confirms pragmatist-voice in agents list + tool set context |
| 4 | `share/skills/h-agent-structure/SKILL.md` | Codebase | 0.8 — structural standards for agent files |
| 5 | de Bono, *Six Thinking Hats* (1985) — Blue Hat role | External | 0.7 — prior art for synthesis/facilitator role aggregating multiple perspective outputs |
| 6 | `tests/test_grant_vscode_askquestions_to_user_invocable.py` | Codebase | 0.8 — blanket ban applies to all .agent.md files (glob-based) |

## 3. Analysis

### 3a. Role Comparison: Pragmatist vs Critic

| Dimension | Critic | Pragmatist |
|-----------|--------|------------|
| Purpose | Adversarial challenge | Convergence synthesis |
| Model | GPT-5.4 (diversity) | Claude Opus 4.6 (same as other voices) |
| Reads | Position + context.md | context.md, decisions.md, ALL voices/*.md |
| Writes | None (returns text) | synthesis.md (file write) |
| Subagents | None | None |
| Invocation scope | Dual (standalone + embedded) | Single (post-deliberation only) |
| File tools needed | Read-only | Read + create |

### 3b. Tool Set Analysis

| Tool | Needed? | Justification |
|------|---------|---------------|
| `read/readFile` | **Yes** | Read context.md, decisions.md, voices/*.md from Working Dir |
| `edit/createFile` | **Yes** | Write synthesis.md to Working Dir |
| `search` | **Yes** | Discover which voice files exist (not all voices are always activated) |
| `vscode/memory` | **Yes** | Standard agent learning |
| ~~read/viewImage~~ | No | AC: does NOT read input files (images live in input/) |
| ~~read/problems~~ | No | No code diagnostics role |
| ~~edit/editFiles~~ | No | synthesis.md is created fresh each invocation; on loop-back, Mediator clears Working Dir before re-invocation (spec §12 Phase 5: "voices are intentionally stateless") |
| ~~agent~~ | No | Pragmatist invokes no subagents |

**Recommended tools:** `[read/readFile, edit/createFile, search, vscode/memory]` — 4 tools.

### 3c. Frontmatter Decisions

| Property | Value | Rationale |
|----------|-------|-----------|
| `user-invocable` | `false` | AC states this; subagent only |
| `disable-model-invocation` | `true` | Follows critic-voice pattern (voice subagent, only ideator should invoke) |
| `model` | `Claude Opus 4.6 (copilot)` | Spec §7: all voices except Critic use Claude Opus 4.6 |
| `agents` | `[]` | No subagent delegation |
| `argument-hint` | `"Synthesize: {working directory path}"` | Mediator passes Working Dir path |

### 3d. Agent File Structure Estimate

| Section | Content | Lines |
|---------|---------|-------|
| Frontmatter | name, description, argument-hint, user-invocable, disable-model-invocation, model, tools, agents | 12 |
| `<persona>` | Synthesis facilitator — convergence detector, disagreement flagger, attribution enforcer | 10 |
| `<critical_rules>` | I/O boundaries, debate log exclusion, attribution requirement, stateless invocation | 8 |
| Input/Output contract | Reads table, writes table, output structure (convergences, disagreements, recommendation) | 15 |
| `<boundaries>` | No debate logs, no input files, no user conversation, Working Dir scope | 8 |
| `<examples>` | Good (attributed synthesis) vs bad (opinion-as-resolution) | 10 |
| **Total** | | **~65 lines** |

### 3e. Cross-Cutting Test Constraints

| Test | Impact | Mitigation |
|------|--------|------------|
| `test_grant_vscode_askquestions_to_user_invocable.py` | Glob on ALL `*.agent.md` — pragmatist must NOT have vscode/askQuestions | Not in proposed tool set ✓ |
| `test_disable_model_invocation.py` | Lists 8 specific pipeline agents — pragmatist NOT in list | No conflict. Pragmatist can set it without triggering the "must NOT have" list ✓ |

### 3f. Prior Art: Synthesis Facilitator Role

The Pragmatist maps to de Bono's **Blue Hat** (1985): "The Big Picture & Managing" — the hat that aggregates all thinking directions and produces a cohesive summary for decision-makers. In the Blackboard architecture (Lalanda 1997), the Pragmatist is a knowledge source that reads the shared working memory and publishes a consolidated view. Both prior art sources validate the synthesis role as a distinct, non-trivial function that should NOT be conflated with mediation (the Mediator's job is user interaction, not synthesis).

## 4. Recommendation

**Build the pragmatist-voice agent file** (~65 lines) following the critic-voice structural pattern with these key differences:

1. **Claude Opus 4.6** model (NOT GPT-5.4 — only Critic uses different model family)
2. **4 tools** including `edit/createFile` for synthesis.md (Critic is read-only; Pragmatist writes)
3. **Single invocation scope** (post-deliberation only — simpler than Critic's dual-scope)
4. **Attribution as core persona trait** — disagreements flagged with voice names, never resolved algorithmically
5. **`disable-model-invocation: true`** — same as Critic, only ideator invokes

**Confidence: 0.88**

Challenge: FALLBACK — challenger agent not in available roster. Self-challenge performed:
- (a) `edit/createFile` vs `edit/editFiles` for loop-back: accepted as low risk — Mediator clears Working Dir per spec §12
- (b) `search` tool for voice discovery: pragmatic — Mediator passes names in prompt, but search is a safety net
- (c) 65-line estimate is smaller than critic-voice: expected — Pragmatist has simpler scope (no dual invocation)

## 5. Follow-up Tasks

### AC Refinements for Architect (binding on #646)

| AC# | Issue | Recommended Refinement |
|-----|-------|----------------------|
| — | Missing `disable-model-invocation` statement | Add: `disable-model-invocation: true` (follows critic-voice pattern) |
| — | Missing exact tool set specification | Add: `tools: [read/readFile, edit/createFile, search, vscode/memory]` |
| — | Missing `agents: []` requirement | Add: `agents: []` (no subagent delegation) |
| — | Missing `argument-hint` | Add: `argument-hint: "Synthesize: {working directory path}"` |
| AC6 | "produces recommendation" underspecified | Clarify: recommendation with confidence score, not just opinion |
| AC7 | Debate log exclusion mechanism unspecified | Encode in persona + critical_rules, not just prohibition |

No new follow-up tasks needed — existing board has full coverage (#647-#652).
