---
id: 1003
title: 'Rewrite agent-audit.prompt.md per Brief #984'
status: archived
priority: medium
created: 2026-04-18 21:35:10.131608+00:00
updated: 2026-04-19 13:22:26.348121+00:00
tags:
- prompt
- agent-ecosystem
- type:docs
parent: 984
depends_on:
- 1000
- 1001
- 1002
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Rewrite `.github/prompts/agent-audit.prompt.md` as the maximum-quality ecosystem audit prompt per the Brief in parent task #984.

## Context

The current audit prompt works but was a quick-shot. The rewrite sharpens coverage to 7 audit dimensions x 2 surfaces (definitions + memory), replaces the batch output template with a continuous one-finding-at-a-time loop, and references (not restates) the standards formalized in sibling tasks #1000, #1001, #1002.

## Acceptance Criteria

- [ ] Single self-contained `.prompt.md` at `share/prompts/agent-audit.prompt.md`; delete stale `.github/prompts/agent-audit.prompt.md`.
- [ ] Five sections in order:
  1. **Preamble** — role, stakes, behavioral contract; trust signals ("rejection is safe", "all evidence inline").
  2. **Audit Surface and Standards** — two surfaces with explicit weighting (Definitions >80%, Memory <20%); standards loading order (`h-agent-structure` first, then `h-memory-structure`, then `r-pipeline-protocol`, then `r-project-standards`); references-not-restates principle; graceful MCP degradation path when `owlbearMemory` tools unavailable.
  3. **Seven Audit Dimensions** — Structural (incl. boundary-fitness sub-probe from #1000) / Duplication / Content Placement / Quality / Pipeline Integrity / SNR / Memory Governance and Content (referencing #1001). Each dimension has at least one negative-space probe (what's missing, not just what's wrong).
  4. **Process** — scan-first; severity-first ordering (HIGH then MED then LOW); one-finding-at-a-time loop using finding card (Header / Evidence / Options-when-ambiguous / Recommendation / askQuestions approval); confidence on every finding AND every option; conditional phase breaks (3+ in next tier); queue re-evaluation after each fix; pause/bail any time.
  5. **Verification** — pipeline trace (impl + non-impl paths); rejection-routing consistency (no BLOCK verdicts); SNR spot-check; coverage summary; askQuestions "run from the top again?"
- [ ] All 7 dimensions x both surfaces (definitions + memory) covered, with explicit MCP-unavailable degradation path for memory surface.
- [ ] Loop runs continuously; uses literal `askQuestions` at every user-facing turn.
- [ ] Re-scan prompted via askQuestions on queue exhaustion.
- [ ] Each finding card includes confidence on the recommendation AND each option.
- [ ] References (does not duplicate) rules from `h-agent-structure`, `h-memory-structure`, `r-pipeline-protocol`, `r-project-standards`.
- [ ] Carries forward from current prompt: pipeline-routing tables, dynamic `file_search` discovery, standards-first loading order.
- [ ] Drops from current prompt: static FINDINGS / REMEDIATION PLAN batch output template.

## Files

- `share/prompts/agent-audit.prompt.md` (new location)
- `.github/prompts/agent-audit.prompt.md` (delete after rewrite)

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One prompt file rewrite + stale file cleanup |
| Interface clarity | PASS | AC lines are specific, verifiable conditions with named sections and component lists (after refinements below) |
| Dependency correctness | PASS | #1000, #1001, #1002 all archived/done; deliverables verified in filesystem |
| Module layering | PASS | Prompt layer only; no upward imports |
| TDD compliance | PASS | Non-impl task (markdown only); `type:docs` tag added for pass-through |
| KISS/YAGNI | PASS | Single-file rewrite with clear scope; no hypothetical requirements |
| Premise challenge | PASS | Existing prompt is acknowledged quick-shot; dependencies formalized the standards it references |
| Pattern consistency | PASS | File path corrected to `share/prompts/` per `r-project-standards` and resolved decision `owlbear-folder-restructure` |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Agent-ecosystem domain only |

### AC Refinements Applied

1. **File path corrected:** `.github/prompts/` → `share/prompts/` per `r-project-standards` file placement table and resolved decision `.owlbear/decisions/resolved/owlbear-folder-restructure.md`. Added "delete stale `.github/prompts/agent-audit.prompt.md`" to AC line 1.
2. **Loading order fixed:** AC line 2 now includes `h-memory-structure` in the standards loading order (4 skills, not 3), matching AC line 7 and the Brief.
3. **MCP namespace corrected:** `owlbear-memory` → `owlbearMemory` (actual camelCase tool namespace per `h-memory-structure` and `owlbear-system.instructions.md`).
4. **Pass-through tag added:** `type:docs` tag added; `prompt` is not in the canonical pass-through list.

### Dependency Verification

| Dep | Title | Status | Deliverable |
|-----|-------|--------|-------------|
| #1000 | Expand h-agent-structure: instruction taxonomy + boundary fitness | archived | `h-agent-structure/SKILL.md` contains Boundary Fitness and instruction taxonomy sections |
| #1001 | Create h-memory-structure handbook skill | archived | `h-memory-structure/SKILL.md` exists with entry shape, tiers, dedup rules |
| #1002 | Add agent-extraction markers to h-agent-structure | archived | `h-agent-structure/SKILL.md` contains Agent Extraction Markers section |

### Challenge Results

- Challenger: **reconsider** (confidence 0.55)
- Findings: C1 tag defect, C2 file placement, C3 loading order omission, C4 MCP namespace
- Architect response: **accepted all four** — applied AC refinements above. C1→added `type:docs` tag. C2→corrected file path to `share/prompts/`. C3→added `h-memory-structure` to loading order. C4→fixed namespace to `owlbearMemory`.

### Verdict: APPROVE (after REFINE)

### Action Taken: Refined AC (4 corrections), added `type:docs` pass-through tag, advancing to `todo`

[[2026-04-19]]
Architecture review complete. Refined 4 AC defects (file path, loading order, MCP namespace, pass-through tag) before approving. All dependencies verified done. Challenger findings accepted and resolved.
[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged `type:docs`) — no tests applicable.
- Task is a `.prompt.md` file rewrite plus deletion of a stale prompt file. No Python source files, no testable interfaces.
- AC references only non-Python deliverables: `share/prompts/agent-audit.prompt.md` and `.github/prompts/agent-audit.prompt.md`.
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

**Files changed:**

- `share/prompts/agent-audit.prompt.md` — created (new location per r-project-standards)
- `.github/prompts/agent-audit.prompt.md` — deleted (stale)

**AC verification:**

- 5 sections in order: Preamble / Audit Surface and Standards / Seven Audit Dimensions / Process / Verification ✓
- Both surfaces (Definitions >80%, Memory <20%) with explicit weights ✓
- Standards loading order: h-agent-structure → h-memory-structure → r-pipeline-protocol → r-project-standards ✓
- MCP degradation path for memory surface in §2 and D7 ✓
- All 7 dimensions: D1 Structural (incl. boundary-fitness sub-probe) / D2 Duplication / D3 Content Placement / D4 Quality / D5 Pipeline Integrity / D6 SNR / D7 Memory Governance ✓
- Each dimension has at least one negative-space probe ✓
- Continuous finding loop with finding card (Header / Evidence / Options / Recommendation / askQuestions) ✓
- Confidence on every finding AND every option ✓
- Phase break rule: 3+ findings in next tier triggers askQuestions pause ✓
- Queue re-evaluation after each fix ✓
- askQuestions at every user-facing turn (queue summary, each finding, phase breaks, verification) ✓
- Re-scan via askQuestions "run from the top again?" on queue exhaustion ✓
- References-not-restates: every finding cites a skill rule; no content duplicated from skills ✓
- Carries forward: pipeline-routing table (D5), dynamic file_search discovery (§2), standards loading order (§2) ✓
- Drops: static FINDINGS / REMEDIATION PLAN batch output template ✓
- r-project-standards compliance: file placed at share/prompts/ ✓

**Commit:** `79d70f0c` — docs: rewrite agent-audit prompt, 5 sections x 7 dimensions (#1003, builder)
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: N/A — `type:docs` pass-through (no Python files changed)

### Lint: N/A — markdown only

### Coverage: N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

Skipped — no `TestFromAC_*` classes; `type:docs` pass-through confirmed by test-writer notes.

#### Security Review

No issues — markdown prompt file, no code, no injection surface, no secrets.

#### Test Integrity

Skipped — no tests.

#### Test Quality

Skipped — no tests.

#### Data Safety

N/A.

#### Builder Process Quality

Single `## Builder Notes` section. Clean first attempt. **CLEAN**.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| File at `share/prompts/agent-audit.prompt.md`; stale `.github/prompts/` deleted | File exists; `file_search` for `.github/prompts/agent-audit.prompt.md` → no results | PASS |
| Five sections in order | §1 Preamble / §2 Audit Surface / §3 Seven Dimensions / §4 Process / §5 Verification present in order | PASS |
| Two surfaces with explicit weights (Definitions >80%, Memory <20%) | §2 table: `Definitions \| >80%`, `Memory \| <20%` | PASS |
| Standards loading order: h-agent-structure → h-memory-structure → r-pipeline-protocol → r-project-standards | §2 "Load in this exact order" numbered list | PASS |
| MCP degradation path | §2 paragraph + D7 "MCP degradation" subsection both present | PASS |
| All 7 dimensions + boundary-fitness sub-probe in D1 | D1–D7 all present; D1 has "Boundary-fitness sub-probe" subsection | PASS |
| Each dimension has ≥1 negative-space probe | All 7 dimensions have explicit "Negative-space probe:" paragraph | PASS |
| Continuous finding loop with finding card + askQuestions | §4 Phase 2: card format + `askQuestions` call after each card | PASS |
| Confidence on every finding AND every option | Recommendation: `confidence: {0.0–1.0}`; Options: `confidence: {0.0–1.0}` per option | PASS |
| Phase break: 3+ in next tier | §4: "if the next tier has 3 or more findings, present a phase-break summary via `askQuestions`" | PASS |
| Queue re-evaluation after each fix | §4: "After every fix, re-scan the affected file and update the queue." | PASS |
| askQuestions at every user-facing turn | Phase 1 queue confirm, Phase 2 per-finding, phase-break, §5 coverage summary | PASS |
| Re-scan via askQuestions "run from the top again?" | §5: `askQuestions` with "Run from the top again?" option | PASS |
| References-not-restates | §2 explicit contract; each dimension cites `skill § section` | PASS |
| Carries forward: pipeline-routing table, `file_search`, standards loading order | D5 rejection-routing table; §2 `file_search` note; §2 ordered loading list | PASS |
| Drops: static FINDINGS / REMEDIATION PLAN batch template | No such template present in file | PASS |

### Verdict

All 16 AC lines PASS. No Pass 1 failures. No deductions.

**Confidence: 0.95 → PASS #1003 → docs**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` has no reference to `agent-audit` or the old `.github/prompts/` path. `owlbear-system.instructions.md` already documents `share/prompts/` as canonical. No update needed. |
| 2 | Module docstrings | No | N/A | No Python files changed — `type:docs` pass-through. |
| 3 | External attribution | No | N/A | Rewrite derived from internal Brief (#984) and existing OwlBear conventions. No external sources used. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this task. Work originated from Brief in parent #984. |

### Files Updated

- None — existing docs already accurate.

### Scratch Files Cleaned

- None — no `.owlbear/scratch/1003-*` files found.

### Spot-Check Evidence

- `share/prompts/agent-audit.prompt.md` confirmed present: all 5 sections (Preamble / Audit Surface / Seven Dimensions / Process / Verification), all 7 dimensions (D1–D7), continuous finding loop, `askQuestions` at every user-facing turn, confidence on every finding and option.
- `.github/prompts/agent-audit.prompt.md` confirmed deleted (`file_search` → no results).
- `copilot-instructions.md` reviewed in full — no stale path references found.
[[2026-04-19]]

## Audit

### AC Verification (spot-check, reviewer 16/16 trusted)

| AC Line | Evidence | Status |
|---------|----------|--------|
| File at share/prompts/agent-audit.prompt.md; stale deleted | file_search returns 1 result at new path only | PASS |
| Five sections in order | Read file: Preamble / Audit Surface / Seven Dimensions / Process / Verification confirmed | PASS |
| Standards loading order (4 skills) | Section 2 numbered list: h-agent-structure, h-memory-structure, r-pipeline-protocol, r-project-standards | PASS |
| All 7 dimensions + boundary-fitness | D1-D7 present; D1 has Boundary-fitness sub-probe subsection | PASS |
| Continuous finding loop + askQuestions | Section 4 Phase 2 finding card format with askQuestions after each | PASS |
| Confidence on findings AND options | Template shows confidence: {0.0-1.0} on recommendation and per-option | PASS |
| Remaining 10 AC lines | Reviewer verified with specific citations; spot-check of file content consistent | PASS (trusted) |

### Test Results

- pytest: 664 passed, 6 failed (all in mcp-knowledge/knowledge packages, NOT in task scope)
- ruff: clean

### Architect Quality: 5/5

Specific, complete, verifiable AC. 16 lines covering structure, content, process, and negative requirements. Architect applied 4 refinements after challenger review (file path, loading order, MCP namespace, pass-through tag) before development began. No builder improvisation needed.

### Deduction Breakdown

- AC lines with no evidence: 0
- Lint violations: 0
- AC quality score <=3: No (5/5)
- Missing reviewer evidence: No (detailed 16-line AC table, all PASS)
- Full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive
