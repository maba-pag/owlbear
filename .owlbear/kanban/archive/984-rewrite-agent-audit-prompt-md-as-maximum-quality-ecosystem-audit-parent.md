---
id: 984
title: Rewrite agent-audit.prompt.md as maximum-quality ecosystem audit (parent)
status: backlog
priority: needed
created: 2026-04-18T21:21:13.595363+00:00
updated: 2026-04-18T21:35:41.983833+00:00
tags:
- prompt
- agent-ecosystem
- quality-gate
- ideation-brief
parent:
depends_on: []
blocked: true
block_reason: 'Parent Brief — split into children #1000, #1001, #1002, #1003. Unblock
  when all children reach done.'
claimed_by:
claimed_at:
---
# Brief: Rewrite `agent-audit.prompt.md` as a Maximum-Quality Ecosystem Audit

> Source: `.owlbear/briefs/draft-agent-audit-prompt-2026-04-18/brief.md` (full draft, including context.md, decisions.md, synthesis.md, and panelist stances available there).

## Context

`agent-audit.prompt.md` (recently moved to `.github/prompts/`, dev-only) is the quality gate for OwlBear's agent ecosystem: agents, skills, instruction stubs, authority instruction files, copilot-instructions, and memory. This ecosystem is the foundation every consuming OwlBear project depends on. The current prompt works but was a quick-shot. Goal: sharpen to the absolute best possible standard.

## Goals

- Complete coverage: 7 audit dimensions × 2 surfaces (definitions + memory).
- Toughest standard: rule-conformance + signal quality + blind spots + 2nd-order effects.
- Top-down + bottom-up: find what's missing, not just what's wrong.
- Continuous loop: one finding → askQuestions → fix → verify → next; on exhaustion, "run from the top?"; bail anytime; never silent-stall.
- Single self-contained file. Audit references standards, never restates them.

## Plan (four atomic tasks)

1. **Task 1a** — Expand `share/skills/h-agent-structure/SKILL.md`: formalize stub-vs-authority instruction file taxonomy + tighten boundary-fitness language (loading model fit) so audit's Structural dimension can probe against it.
2. **Task 1b** — Create `share/skills/h-memory-structure/SKILL.md` (new handbook). **Terse-by-construction**: few required fields, tight length limits, explicit anti-patterns. No optional menus (LLMs invent content). Covers entry shape, categories, file vs. MCP relationship, tier-content fit, dedupe/supersede rules, content-quality bar.
3. **Task 1c** — Add a delegation/operational-isolation rule (location TBD by architect — likely `h-agent-structure` or `r-pipeline-protocol`) defining markers for "when to extract a dedicated agent/subagent" (precedent: quality-runner). Future audits flag missed extraction opportunities.
4. **Task 2** — Rewrite `.github/prompts/agent-audit.prompt.md` per the structure below, referencing 1a/1b/1c.

**Sequencing:** Task 2 depends on 1a/1b/1c. Tasks 1a/1b/1c are independent and can run in parallel.

## Task 2 — Audit Prompt Structure (5 sections)

1. **Preamble** — role, stakes, behavioral contract; trust signals ("rejection is safe", "all evidence inline").
2. **Audit Surface & Standards** — two surfaces with explicit weighting (Definitions >80%, Memory <20%); standards loading order; references-not-restates principle; graceful MCP degradation.
3. **Seven Audit Dimensions** with negative-space probes: Structural (with boundary-fitness sub-probe) / Duplication / Content Placement / Quality / Pipeline Integrity / SNR / Memory Governance & Content.
4. **Process** — scan-first, severity-first ordering (HIGH→MED→LOW), continuous one-finding-at-a-time loop using a finding card (Header / Evidence / Options-when-ambiguous / Recommendation / Approval via askQuestions), confidence on every finding AND every option, conditional phase breaks (≥3 in next tier), queue re-evaluation after each fix, pause/bail any time.
5. **Verification** — pipeline trace (impl + non-impl), rejection-routing consistency (no BLOCK verdicts), SNR spot-check, coverage summary, then askQuestions "run from the top again?".

**Carry forward from current prompt:** pipeline-routing tables, dynamic file discovery via `file_search`, standards-first loading order.
**Drop:** the static FINDINGS / REMEDIATION PLAN batch output template.

## Acceptance (Task 2)

- Single self-contained `.prompt.md` under `.github/prompts/`.
- All 7 dimensions × both surfaces covered (with MCP-unavailable degradation path).
- Loop runs continuously; uses literal `askQuestions` at every user-facing turn.
- Re-scan prompted on queue exhaustion.
- Each finding card includes confidence on the recommendation AND each option.
- References (does not duplicate) rules in `h-agent-structure`, `h-memory-structure`, `r-pipeline-protocol`, `r-project-standards`.

## Out of scope

- Persistent `.owlbear/audit/deviations.md`.
- Splitting prompt into `w-agent-audit` skill.
- Editing consuming projects' `.github/prompts/`.
- Cost/context-window/wall-time as primary audit signals (no telemetry standard).

## Risks

- **MCP forward-compat** — graceful degradation today, picks up MCP automatically when available.
- **Loop fatigue** — severity-first + conditional phase breaks.
- **False positives if 1a/1b/1c land incomplete** — sequencing prevents.
- **`h-memory-structure` bloat** — terse-by-construction (required + bounded, not optional + menu) prevents LLM invention.

[[2026-04-18]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent Brief decomposed into 4 atomic tasks, each with one concern |
| Interface clarity | PASS | AC lines are verifiable conditions with explicit section names, field counts, and line limits |
| Dependency correctness | PASS | #1002 depends on #1000 (both edit same file); #1003 depends on #1000, #1001, #1002 |
| Module layering | PASS | All tasks modify skill/prompt layer; no upward imports |
| TDD compliance | PASS | All 4 tasks are non-impl (markdown only); tagged `agent` or `prompt` for pass-through |
| KISS/YAGNI | PASS | 4 tasks is minimal for the goal; no hypothetical scope |
| Premise challenge | PASS | Current audit prompt exists but is explicitly a quick-shot; improvement justified by ecosystem dependency |
| Pattern consistency | PASS | Follows h-agent-structure patterns for skills, r-project-standards for file placement |
| Security surface | PASS | No new system boundaries — all files are internal agent ecosystem artifacts |
| Single domain | PASS | All tasks within agent-ecosystem domain |

### Architecture Notes

- **Task 1c location decided:** `h-agent-structure` (not `r-pipeline-protocol`). Agent extraction is a structural concern about the ecosystem, not a pipeline coordination rule.
- **File-conflict prevention:** #1002 depends on #1000 because both modify `h-agent-structure/SKILL.md`. Brief proposed parallel execution but sequential is safer.
- **Non-impl tagging:** All children tagged `agent` or `prompt` for test-writer pass-through per `w-arch-review` Step 3 non-impl tagging rule.

### Challenge Results

- Challenger: SKIPPED (SPLIT verdict — challenger optional per w-arch-review Step 2.5)

### Verdict: SPLIT

### Children Created

| ID | Title | Depends on |
|----|-------|------------|
| #1000 | Expand h-agent-structure: instruction taxonomy + boundary fitness | — |
| #1001 | Create h-memory-structure handbook skill | — |
| #1002 | Add agent-extraction markers to h-agent-structure | #1000 |
| #1003 | Rewrite agent-audit.prompt.md per Brief #984 | #1000, #1001, #1002 |

### Action Taken

Split parent Brief into 4 child tasks. Parent blocked as container until all children reach done.