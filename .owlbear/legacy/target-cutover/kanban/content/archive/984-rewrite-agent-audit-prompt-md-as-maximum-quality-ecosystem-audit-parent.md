---
id: 984
title: Rewrite agent-audit.prompt.md as maximum-quality ecosystem audit (parent)
status: archived
priority: medium
created: 2026-04-18T21:21:13.595363+00:00
updated: 2026-04-19T16:56:57.571885+00:00
tags:
- prompt
- agent-ecosystem
- quality-gate
- ideation-brief
parent:
depends_on: []
blocked: false
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
[[2026-04-19]]

## Architecture Review (Re-evaluation)

### Situation

Parent Brief was previously SPLIT into children #1000–#1003 (prior review in body). Children no longer exist on the board (completed and archived). All 4 planned deliverables verified present in codebase:

| Planned task | Deliverable | Status |
|-------------|-------------|--------|
| 1a — Instruction taxonomy + boundary fitness | `share/skills/h-agent-structure/SKILL.md` §Loading Model, §Boundary Fitness | Present |
| 1b — Create h-memory-structure | `share/skills/h-memory-structure/SKILL.md` | Present (full: entry shape, tiers, dedup, quality bar) |
| 1c — Agent extraction markers | `share/skills/h-agent-structure/SKILL.md` §Agent Extraction Markers | Present (extract-when/defer-when + precedent) |
| 2 — Rewrite audit prompt | `share/prompts/agent-audit.prompt.md` | Present (7 dimensions × 2 surfaces, process loop, verification) |

### Brief AC Verification (Task 2)

- [x] Single self-contained `.prompt.md` — at `share/prompts/` (correct per `r-project-standards`, Brief's `.github/prompts/` reference was outdated)
- [x] All 7 dimensions × both surfaces covered with MCP degradation path
- [x] Continuous one-finding-at-a-time loop using `askQuestions`
- [x] Re-scan prompted on queue exhaustion (§5 Verification)
- [x] Finding card includes confidence on recommendation AND each option
- [x] References-not-restates principle explicit in §2

### Non-impl tagging

Task tagged `prompt`, `agent-ecosystem` — sufficient for test-writer pass-through.

### Stale block_reason

`blocked: false` but `block_reason` still references children #1000–#1003. Cosmetic inconsistency; does not affect routing.

### Verdict: APPROVE

Parent Brief container — all children's work verified complete in codebase. Advancing for pipeline flow-through.
[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged `prompt`, `agent-ecosystem`) — no tests applicable.
- AC references only `.prompt.md` and `SKILL.md` files; no testable Python interfaces.
- Architect confirmed pass-through: "Task tagged `prompt`, `agent-ecosystem` — sufficient for test-writer pass-through."
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

**Non-implementation task** — tagged `prompt`, `agent-ecosystem`. Test-writer confirmed pass-through. No Python code changes required.

**Deliverables verified present in codebase:**

| AC Item | File | Evidence |
|---------|------|----------|
| 1a — Instruction taxonomy + boundary fitness | `share/skills/h-agent-structure/SKILL.md` | §Loading Model (L11), §Boundary Fitness (L35) present |
| 1c — Agent extraction markers | `share/skills/h-agent-structure/SKILL.md` | §Agent Extraction Markers (L54) present |
| 1b — h-memory-structure handbook | `share/skills/h-memory-structure/SKILL.md` | File exists |
| 2 — Rewrite audit prompt | `share/prompts/agent-audit.prompt.md` | §3 Seven Audit Dimensions (L46), finding card (L175), `askQuestions` at every user-facing turn (L169, L173, L201, L215), re-scan on exhaustion (L215) |

**Test results:** N/A (no testable Python interfaces)
**Lint status:** N/A (no Python changes)
**Files changed:** 0 (all deliverables pre-existing from child tasks #1000–#1003)
[[2026-04-19]]

## Review Evidence

### Test Results

N/A — Non-implementation task (tagged `prompt`, `agent-ecosystem`). No Python code, no testable interfaces.

### Lint

N/A — No Python files changed.

### Coverage

N/A — No Python modules touched.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

No `TestFromAC_*` classes — pass-through confirmed by architect and test-writer.

#### Security Review

No new code or system boundaries. No secrets, injection surfaces, path traversal, or deserialization. No issues.

#### Test Integrity

No `TestFromAC_*` tests — conditional skip applied.

#### Test Quality

N/A — no tests applicable.

#### Data Safety

N/A — no data operations.

#### Necessity Check

N/A — no new dependencies.

#### Builder Process Quality

CLEAN — single pass, no retries, no loop patterns.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Single self-contained `.prompt.md` | `share/prompts/agent-audit.prompt.md` — one file, 215 lines | PASS |
| All 7 dimensions × both surfaces with MCP degradation | D1–D7 at L46–L155; each applied to definitions + memory; MCP degradation in §2 (L40) and D7 (L147) | PASS |
| Loop uses literal `askQuestions` at every user-facing turn | L169 (queue summary), L173 (each finding), L201 (phase breaks), L215 (re-scan) — 4 explicit calls | PASS |
| Re-scan prompted on queue exhaustion | L215: `askQuestions` with option "Run from the top again?" | PASS |
| Finding card confidence on recommendation AND each option | L175–L199: card format shows `confidence: {0.0–1.0}` on each option and `Recommendation — confidence: {0.0–1.0}` | PASS |
| References-not-restates principle in §2 | L34: "This prompt does not reproduce rules from the four skills above. Every finding cites a specific rule in one of those skills." | PASS |
| 1a — stub-vs-authority taxonomy in h-agent-structure | Loading Model table distinguishes "Authority instructions (.instructions.md)" (Guaranteed, `<critical_rules>` attachment) from "Instruction stubs (.instructions.md)" (Medium, `applyTo` glob) | PASS |
| 1a — Boundary Fitness language | `h-agent-structure` §Boundary Fitness: 5-row selection table with tier conditions | PASS |
| 1b — h-memory-structure handbook | `share/skills/h-memory-structure/SKILL.md` — 5 required fields, Tier-Content Fit table, File vs. MCP Relationship, Deduplication Rules, Content-Quality Bar, Anti-Patterns | PASS |
| 1c — Agent extraction markers | `h-agent-structure` §Agent Extraction Markers: extract-when (5 conditions), defer-when (3 conditions), quality-runner precedent | PASS |
| Carry-forward: pipeline-routing table | D5 rejection-routing table present | PASS |
| Carry-forward: `file_search` dynamic discovery | §4 Phase 1 step 2: "Use `file_search` to discover the current definitions surface" | PASS |
| Carry-forward: standards-first loading order | §2 Standards Loading Order (4 skills in explicit order) | PASS |
| Drop: static batch FINDINGS/REMEDIATION template | One-finding-at-a-time loop replaces batch template — no static output section present | PASS |

### Deductions

None.

### Verdict

All 14 AC lines PASS. No CRITICAL failures. No test, lint, or security issues (non-impl). Builder-cited line numbers independently verified accurate.

**Confidence: .95 → PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | No Python behavior or CLI change. `.github/copilot-instructions.md` covers tech stack and Cockpit — unaffected by skill/prompt additions. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | No external repos, articles, or patterns cited anywhere in task body, brief, or reviewer notes. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc produced — ideation work tracked under `.owlbear/briefs/`. |
| — | skills/README.md count | **Yes** | **Updated** | `h-memory-structure` (new skill, task 1b) not counted. README showed 28 total / 12 w- / 13 h-; actual is 30 / 13 w- / 14 h- (also corrected pre-existing uncounted `w-test-curation`). |

### Files Updated

- `share/skills/README.md` — counts: total 28→30, h- 13→14, w- 12→13

### Scratch Files Cleaned

- None (no `.owlbear/scratch/984-*` files found)

Commit: `c3ebd0f7` — docs: update skill count in skills/README.md (#984, doc-writer)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Single self-contained `.prompt.md` | `share/prompts/agent-audit.prompt.md` — one file, ~225 lines | PASS |
| All 7 dimensions × both surfaces with MCP degradation | D1–D7 present; each applied to definitions + memory; MCP degradation in §2 and D7 | PASS |
| Loop uses literal `askQuestions` at every user-facing turn | Phase 1 (queue), Phase 2 (per-finding), Phase 5 (re-scan) — confirmed by reviewer L169, L173, L201, L215 | PASS |
| Re-scan prompted on queue exhaustion | §5 Verification: `askQuestions` with "Run from the top again?" | PASS |
| Finding card confidence on recommendation AND each option | Card format shows `confidence: {0.0–1.0}` on each option and recommendation | PASS |
| References-not-restates principle in §2 | L34 explicit statement confirmed | PASS |
| 1a — stub-vs-authority taxonomy | `h-agent-structure` §Loading Model table present | PASS |
| 1a — Boundary Fitness language | `h-agent-structure` §Boundary Fitness: 5-row selection table | PASS |
| 1b — h-memory-structure handbook | `h-memory-structure/SKILL.md` — 110 lines, 5 required fields, all sections present | PASS |
| 1c — Agent extraction markers | `h-agent-structure` §Agent Extraction Markers with extract-when/defer-when | PASS |
| Carry-forward: pipeline-routing table | D5 rejection-routing table present | PASS |
| Carry-forward: `file_search` dynamic discovery | §4 Phase 1 step 2 confirmed | PASS |
| Carry-forward: standards-first loading order | §2 explicit 4-skill order confirmed | PASS |
| Drop: static batch template | One-finding-at-a-time loop replaces batch — no static output section | PASS |

### Test Results

- pytest: 685 passed, 6 failed (all in mcp-knowledge — pre-existing, out of task scope)
- ruff: clean

### Architect Quality: 5/5

Exceptionally well-structured Brief: 4 atomic tasks with clear dependencies, specific verifiable AC with section names/field counts/line limits, explicit out-of-scope, risk analysis, and sequencing constraints.

### Deduction Breakdown

- AC lines without evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality ≤ 3: no (-.00)
- Missing reviewer evidence: no (-.00)
- In-scope test failures: 0 (-.00)

### Note

6 pre-existing test failures in mcp-knowledge domain (schema tests, query parameter, SKILL.md path) — unrelated to agent-ecosystem scope. Flagged for visibility but no deduction per rubric.

### Confidence: 1.00

### Action: archive
