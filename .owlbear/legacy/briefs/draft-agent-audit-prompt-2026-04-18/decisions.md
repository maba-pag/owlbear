# Decisions — Agent-Audit Prompt Rewrite

## D1: Approach
**Rewrite, not patch.** Use Architect's 5-section structure populated with End-User's UX contracts. Carry forward proven content (pipeline routing tables, dynamic file discovery, standards-first loading). Reject the current prompt's batch FINDINGS/REMEDIATION format; replace with continuous one-finding-at-a-time card loop.

## D2: 7 audit dimensions (was 6)
Existing: Structural / Duplication / Content Placement / Quality / Pipeline Integrity / SNR.
Add: **Memory Governance & Content** (governance + content quality, dual-source aware: file-based now, MCP soon).

## D3: Acknowledged deviations file
**Not in scope.** No `.owlbear/audit/deviations.md`. Fully ephemeral — re-evaluate intentional deviations on every run.

## D4: Instruction file taxonomy
**Fix at source first.** Update `share/skills/h-agent-structure/SKILL.md` to formally define "instruction stubs" vs. "authority instruction files," then have the audit prompt reference that distinction. This becomes a prerequisite task.

## D5: Confidence scores
**Every finding AND every suggested fix/option carries a confidence score (0.0–1.0).** Informational only — does not branch UX.

## D6: askQuestions coupling
**Hardcode `askQuestions` literal in the prompt.** It is the direct VS Code interaction mechanism, not part of the OwlBear toolchain (no decision/action requests). VS Code naming is stable.

## D7: Loop stop
Loop until queue exhausted OR user bails via askQuestions. No hard pass cap. On exhaustion, askQuestions "run from the top again?"

## D8: Discovery surfaces
Three: file-based (agents/skills/instructions/copilot-instructions), memory-files (`/memories/repo/inbox/`), and `owlbearMemory` MCP. MCP unavailable today — graceful degradation; forward-compatible.

## D9: Methodology
Top-down (rules-down) AND bottom-up (negative-space probes per dimension — find what's missing, not just what's wrong).

## D10: Plan shape
Four atomic kanban tasks:
1. **Task 1a** — Update `h-agent-structure` to formalize stub vs. authority instruction file taxonomy AND tighten the boundary-fitness language so the audit's Structural dimension can probe loading-model fit against it.
2. **Task 1b** — Create `h-memory-structure` (new handbook). Terse-by-construction: few required fields, tight length limits, explicit anti-patterns. No "optional menu" sections (LLMs invent content). German-style: to-the-point, no fluff, no nice-ities.
3. **Task 1c** — Add a "delegation / operational-isolation" rule (location TBD by architect — likely `h-agent-structure` or `r-pipeline-protocol`) so audits can flag missed opportunities to extract a dedicated agent (precedent: `quality-runner`).
4. **Task 2** — Rewrite `agent-audit.prompt.md` per this Brief, referencing all of 1a/1b/1c.

## D11: Surfaces (revised)
**Two** discovery surfaces, with explicit weighting:
- Definitions (>80% audit weight): agents, skills, instructions, copilot-instructions
- Memory: `/memories/`, `/memories/repo/inbox/`, `owlbearMemory` MCP — storage backend (file vs. MCP) is implementation detail with graceful degradation

## D12: Scope/decomposition smell
- (A) Path complexity: handled as a **sub-probe inside Structural**, anchored to h-agent-structure loading model. Not a new dimension.
- (B) Operational complexity / delegation: handled by Task 1c creating the rule the audit can probe against. Audit picks it up automatically once the rule lands.
- Cost/context-window: dropped as a primary signal — too weak without telemetry standards.
