# Brief: Rewrite `agent-audit.prompt.md` as a Maximum-Quality Ecosystem Audit

## Context

`agent-audit.prompt.md` (recently moved to `.github/prompts/`, dev-only — not consumer-facing) is the quality gate for OwlBear's agent ecosystem: agents, skills, instruction stubs, authority instruction files, copilot-instructions, and memory. This ecosystem is the foundation every consuming OwlBear project depends on, so the audit prompt is unbelievably critical. The current prompt works (run multiple times, drove real edits) but was a quick-shot. The user wants it sharpened to the absolute best possible standard.

## Goals

- **Complete coverage.** All 7 audit dimensions × all relevant surfaces (definitions + memory).
- **Toughest standard.** Rule-conformance + signal quality + blind spots + 2nd-order effects.
- **Top-down + bottom-up.** Find what's *missing* (negative space), not only what's wrong.
- **Continuous loop.** One finding → user approves via `askQuestions` → implement → verify → next. On exhaustion, "run from the top again?" Bail anytime via `askQuestions`. Never silent-stall.
- **Single self-contained file.** No skill split.
- **Audit references standards, never restates them.** Each authority skill carries its rules; the audit prompt carries the *process* of checking against them.

## Plan (four atomic tasks, sequenced)

### Task 1a — Expand `h-agent-structure`
- Formalize the distinction between **instruction stubs** (3-line pointers) and **authority instruction files** (`agent-common.instructions.md`, `owlbear-system.instructions.md`, etc. — files that legitimately contain rules). Define naming, placement, content rules for each.
- Tighten **boundary-fitness language** (loading model + 80% rule + file-type semantics) so the audit's Structural dimension can probe "is this file the right loading-model unit?" with a clear authority anchor.

### Task 1b — Create `h-memory-structure` (new handbook)
Define what makes a well-formed memory entry. **Terse-by-construction**: few required fields, tight length limits, explicit anti-patterns. No "optional menu" sections (LLMs invent content to fill them). Style: to-the-point, no fluff, no nice-ities. Covers entry shape, categories, the relationship between file-based `/memories/` and `owlbearMemory` MCP, tier-content fit (what belongs in user vs. session vs. repo vs. canonical), dedupe/supersede rules, content-quality bar.

### Task 1c — Add a delegation / operational-isolation rule
Location TBD by architect — likely `h-agent-structure` or `r-pipeline-protocol`. Define markers for "when to extract a dedicated agent or subagent" (precedent: `quality-runner` exists because test-running has many failure modes despite a one-line prose). Once landed, future audit runs can flag missed opportunities. Without this task, the (B) operational-complexity smell has no rule to anchor against.

### Task 2 — Rewrite `agent-audit.prompt.md`

**Structure (5 sections):**

1. **Preamble** — Role, stakes, behavioral contract (continuous loop, never silent-stall, all interaction via `askQuestions` literal). Trust signals: "rejection is safe", "all evidence presented inline".

2. **Audit Surface & Standards** —
   - **Two surfaces (with explicit weighting):**
     - **Definitions (>80% audit weight):** `share/agents/`, `share/skills/`, `share/instructions/`, `.github/copilot-instructions.md`
     - **Memory:** `/memories/`, `/memories/repo/inbox/`, `owlbearMemory` MCP — storage backend (file vs. MCP) is implementation detail; both feed the same audit dimension. Graceful degradation when MCP is unavailable.
   - **Standards loading order** (load before any evaluation): `h-agent-structure` (expanded) → `h-memory-structure` (new) → `r-pipeline-protocol` → `r-project-standards` → supporting skills as needed.
   - **References, never restates** — every check cites a rule from one of these sources.

3. **Seven Audit Dimensions** — each with explicit **negative-space probes** for bottom-up discovery:
   1. **Structural** — agent/skill files conform to the expanded `h-agent-structure`. Includes a sub-probe for **boundary fitness / path complexity** ("is this file the right loading-model unit?" / "does any single execution path touch <30% of the file?") anchored to the loading model rules.
   2. **Duplication** — Rule of Two violations; same rule in 3+ places.
   3. **Content Placement** — 80%-rule violations; rules in the wrong file.
   4. **Quality** — persona richness, example specificity, presence of skill references in `<critical_rules>`.
   5. **Pipeline Integrity** — dispatch paths, no double-moves, signal mapping, rejection routing (cause-based, no BLOCK/BLOCKED verdicts), agent rename consistency.
   6. **SNR** — rationale prose, restated rules, filler.
   7. **Memory Governance & Content** — entries conform to `h-memory-structure`; tier boundaries from `owlbear-system.instructions.md` §4 respected; no content contradicting authority skills; no staleness; no duplicates. Dual-source aware (file + MCP).

4. **Process** —
   - **Scan-first**: read everything before queuing any finding.
   - **Severity-first ordering** (HIGH → MED → LOW). Severity rubric defined in the prompt.
   - **Continuous one-finding-at-a-time loop** using the **finding card**:
     ```
     [Finding N of M | severity | dimension]
     Evidence:    {raw quotes / file refs / "searched X, not found in Y"}
     Options:     {only when genuine ambiguity exists; each option has its own confidence (0.0–1.0)}
     Recommendation: {action + confidence (0.0–1.0)}
     Approval:    askQuestions (approve / modify / reject / pause)
     ```
   - Every finding AND every suggested fix/option carries a confidence score (informational, doesn't branch UX).
   - **Conditional phase break** between severity tiers when next tier has ≥3 findings ("HIGH complete; 12 MED next — Continue / Pause?").
   - **Queue re-evaluation after each fix** — surface count change to user.
   - **Pause/bail** at any prompt — no penalty.

5. **Verification (end-of-cycle, before "run again?" prompt)** —
   - Pipeline trace: implementation task path AND non-implementation task path (research, config) — both reachable end-to-end.
   - Rejection-routing consistency — cause-based per `r-pipeline-protocol`, no BLOCK/BLOCKED verdicts.
   - SNR spot-check — 3 random files for rationale prose / restated rules / filler.
   - Coverage summary — confirm all 7 dimensions and both surfaces were exercised this cycle.
   - Then `askQuestions` "run from the top again? (yes / no / pause and resume later)".

**Carry forward from current prompt:** Pipeline-integrity routing tables (severity-based reviewer rejection paths, builder/architect/auditor verdicts), dynamic file discovery via `file_search`, standards-first loading order.

**Drop from current prompt:** The static FINDINGS / REMEDIATION PLAN batch output template (conflicts with the interactive loop).

**Acceptance:**
- Single self-contained `.prompt.md` file under `.github/prompts/`.
- Covers all 7 dimensions and both surfaces (with MCP-unavailable degradation path).
- Loop runs continuously without silent stalls; uses `askQuestions` literal at every user-facing turn.
- Re-scan ("run from the top?") prompted on queue exhaustion.
- Each finding card includes confidence on the recommendation AND on each option.
- References (does not duplicate) rules in `h-agent-structure`, `h-memory-structure`, `r-pipeline-protocol`, `r-project-standards`.

## Out of scope

- Persistent `.owlbear/audit/deviations.md` — re-evaluate intentional deviations fresh each run.
- Splitting prompt into a `w-agent-audit` skill.
- Editing consuming projects' `.github/prompts/`.
- Cost/context-window/wall-time as primary audit signals (no telemetry standard to anchor against).

## Dependencies

Task 2 depends on 1a, 1b, 1c. Tasks 1a/1b/1c are independent of each other and can run in parallel.

## Risks

- **MCP forward-compat** — `owlbearMemory` MCP not yet functional. Audit must degrade gracefully today and pick up MCP automatically when available, without prompt rewrite.
- **Loop fatigue** — dozens of findings in one session. Mitigated by severity-first ordering + conditional phase breaks.
- **False positives if standards land incomplete** — sequencing (1a/1b/1c before 2) prevents this.
- **`h-memory-structure` bloat risk** — LLMs invent content to fill optional sections. Mitigated by terse-by-construction design (required + bounded, not optional + menu).
