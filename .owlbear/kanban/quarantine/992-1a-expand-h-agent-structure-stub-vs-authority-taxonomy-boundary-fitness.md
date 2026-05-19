---
id: 992
title: '1a: Expand h-agent-structure — stub vs. authority taxonomy + boundary-fitness'
status: archived
priority: important
created: 2026-04-18T21:23:32.394740+00:00
updated: 2026-04-19T01:35:39.569109+00:00
tags:
- type:docs
- scope:skills
parent: 984
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #984

## Objective

Expand `share/skills/h-agent-structure/SKILL.md` with two additions:

1. **Instruction file taxonomy** — formalize the distinction between instruction stubs (3-line pointers in `share/instructions/`) and authority instruction files (`agent-common.instructions.md`, `owlbear-system.instructions.md`, etc.) that legitimately contain rules. Define naming, placement, and content rules for each type.
2. **Boundary-fitness language** — tighten the loading model rules (80% rule, file-type semantics, path complexity) so the audit's Structural dimension can probe "is this file the right loading-model unit?" with a clear authority anchor.

## Acceptance Criteria

- [ ] `h-agent-structure/SKILL.md` contains a section defining instruction stubs vs. authority instruction files with naming, placement, and content rules for each.
- [ ] Boundary-fitness section includes the 80% rule, loading-model unit fit, and file-type semantic guidance.
- [ ] Existing content preserved; additions are additive.
- [ ] No rules duplicated from other skills — references only.

## Files

- `share/skills/h-agent-structure/SKILL.md`
[[2026-04-18]]

## Architecture Review

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1: section defining stubs vs. authority instruction files | REFINE — ambiguous whether to expand existing "Instruction Stub Format" section or create parallel section | Clarified: expand existing section (rename heading, add authority file sub-section) |
| AC2: boundary-fitness section with 80% rule, loading-model unit fit, file-type semantics | REFINE — "loading-model unit fit" is undefined jargon; "includes the 80% rule" ambiguous (restate vs reference) | Clarified below |
| AC3: existing content preserved; additions additive | PASS — clear and verifiable |
| AC4: no rules duplicated from other skills | PASS — clear and verifiable |

### Refined Acceptance Criteria

- [ ] The existing "Instruction Stub Format" section is expanded into an "Instruction File Taxonomy" section (or similar) covering both stubs and authority files. Sub-sections for each type with naming, placement, and content rules. Existing stub table preserved.
- [ ] Authority instruction file rules define: (a) when an instruction file legitimately contains rules directly (vs. pointing to a skill), (b) naming convention, (c) `applyTo` scope expectations, (d) note that `copilot-instructions.md` is a separate loading mechanism (not an instruction file) — it already appears in the Loading Model table.
- [ ] New "Boundary Fitness" section (under Principles or as a peer section) provides criteria for determining whether content is in the correct loading-model unit. Must include: (a) reference (not restatement) of the existing 80% Rule, (b) path-coverage heuristic — if a single execution path touches <30% of a file, the file likely bundles unrelated concerns, (c) reference (not restatement) of the existing File Type Selection table for file-type semantic guidance.
- [ ] Existing content preserved; additions are additive. Renaming the "Instruction Stub Format" heading is permitted.
- [ ] No rules duplicated from other skills — references only. No duplication within the file (Rule of Two applies internally).

### Builder Guidance

- The two authority files (`agent-common.instructions.md` ~130 lines, `owlbear-system.instructions.md` ~160 lines) have different `applyTo` scopes: `agent-common` fires on `share/agents/**` (domain-scoped), `owlbear-system` fires on `**` (universal). The taxonomy should note this distinction but need not create sub-categories — scope is already visible in the `applyTo` field.
- The boundary-fitness section should enable a downstream audit prompt to ask: "Is this content in the right loading-model unit?" with a clear checklist. Think auditor-facing, not builder-facing.
- Do NOT move the 80% Rule or File Type Selection table — reference them from the new section.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file, one topic: expanding h-agent-structure |
| Interface clarity | PASS (after refine) | AC tightened to resolve ambiguities |
| Dependency correctness | PASS | No deps; independent of sibling tasks 1b, 1c |
| Module layering | PASS | Docs-only change in share/skills/ |
| TDD compliance | PASS | Tagged type:docs — non-impl pass-through |
| KISS/YAGNI | PASS | Minimal additions to existing file |
| Premise challenge | PASS | File currently lacks authority file taxonomy and boundary-fitness criteria |
| Pattern consistency | PASS | Follows existing handbook skill structure |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent ecosystem structure only |

### Challenge Results

- Challenger: reconsider (confidence 0.50)
- Architect response: accepted — refined AC to resolve all three ambiguities (80% rule reference vs restate, "loading-model unit fit" replaced with concrete language, section placement clarified)

### Verdict: REFINE → APPROVE

### Action Taken: Tightened AC to resolve ambiguities identified by challenger. Task advanced to todo with refined AC in architecture review note

[[2026-04-18]]

## Test-Writer Notes

- Non-implementation task (tagged type:docs) — no tests applicable.
- AC describes additions to `share/skills/h-agent-structure/SKILL.md` (markdown skill file only).
- No Python interfaces, modules, or src/ files referenced.
- Step 2a heuristic: AC references only `.md` file — non-impl pass-through.
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

### Files Changed

- `share/skills/h-agent-structure/SKILL.md` — 43 insertions, 2 deletions

### Changes Made

1. **Instruction File Taxonomy section** — renamed `## Instruction Stub Format` to `## Instruction File Taxonomy` and added `### Authority Files — Embedded Rules` sub-section alongside the existing `### Stubs — Safety Nets`. Authority file rules cover: when to use inline rules (universal/near-universal, always-needed for scope), naming convention, `applyTo` scope expectations, and a clear note that `copilot-instructions.md` is NOT an instruction file. Current authority files table included (`agent-common.instructions.md` domain-scoped, `owlbear-system.instructions.md` universal).

2. **Boundary Fitness section** — added `### Boundary Fitness` under Principles (after `### 80% Rule`). Contains a 5-row checklist table for auditing loading-model unit fit, the path-coverage heuristic (< 30% of sections per single execution path = likely bundled concerns), and references to the existing 80% Rule and File Type Selection table (no duplication).

### AC Verification

- ✅ Instruction File Taxonomy section with naming, placement, and content rules for stubs and authority files
- ✅ Authority file rules: (a) when to contain rules inline, (b) naming convention, (c) applyTo scope expectations, (d) copilot-instructions.md separation noted
- ✅ Boundary Fitness section: 80% Rule referenced (not restated), path-coverage heuristic (< 30%), File Type Selection referenced (not restated)
- ✅ Existing content preserved; additions additive (stub table intact, heading rename only)
- ✅ No rules duplicated from other skills — references only

### Test Results

Non-implementation task (type:docs) — no tests applicable.

### Lint

N/A — markdown-only changes.

### Commit

`0ef5b6d9` — docs: expand h-agent-structure — instruction file taxonomy + boundary fitness (#992, builder)
[[2026-04-19]]

## Review Evidence

### Test Results

Non-implementation task (type:docs) — no tests applicable. Test-Writer pass-through confirmed correct.

### Lint

N/A — markdown-only changes.

### Coverage

N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

No `TestFromAC_*` classes exist. Non-impl pass-through. Skip (Step 5.0 conditional).

#### Security Review

No code changes. Markdown-only diff. No issues.

#### Test Integrity

N/A — no tests exist for this task.

#### Test Quality

N/A

#### Data Safety

N/A

#### Implementation-Aware Test Gap Analysis

N/A — docs-only task.

#### Builder Process Quality

Single `## Builder Notes` section. First-attempt success. CLEAN.

### Pass 2 — INFORMATIONAL

Minor observation: Boundary Fitness checklist row 1 ("Does ≥ 80% of agents need this?") echoes the 80% Rule immediately above it. The explicit `Reference: 80% Rule above` footer confirms intended reference/application, not duplication. Not a violation under Rule of Two — the checklist is a diagnostic application of the rule, not a restatement.

### AC Compliance

| Refined AC | Evidence | Status |
|------------|----------|--------|
| Instruction File Taxonomy section (stubs + authority file sub-sections, naming/placement/content rules) | `SKILL.md` line 259: `## Instruction File Taxonomy (.instructions.md)` with `### Stubs — Safety Nets` (line 263) and `### Authority Files — Embedded Rules` (line 289) | PASS |
| Authority file rules: (a) when to use inline rules, (b) naming convention, (c) applyTo scope, (d) copilot-instructions.md separation | Lines 291–296 (when), line 304 (naming), line 306 (applyTo scope), line 308 (copilot-instructions.md NOT an instruction file) | PASS |
| Boundary Fitness section: 80% Rule ref (not restatement), path-coverage heuristic (<30%), File Type Selection ref | Lines 58–77: 5-row checklist table + path-coverage heuristic + `Reference: 80% Rule above · File Type Selection table above` | PASS |
| Existing content preserved; additions additive; heading rename permitted | Stub table intact at lines 270–276; original stub body preserved under `### Stubs — Safety Nets`; only addition is intro paragraph + new sub-heading + authority file sub-section | PASS |
| No rules duplicated from other skills; no internal duplication (Rule of Two) | Checklist uses references ("see 80% Rule", "see File Type Selection table"), not verbatim rule text; no duplication detected within file | PASS |

### Deductions

None.

### Verdict

All 5 refined AC lines PASS. No Pass 1 critical failures. Security: clean. Process: clean. Confidence: .96 → PASS.
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | type:docs task; only `share/skills/h-agent-structure/SKILL.md` changed; copilot-instructions.md covers Cockpit stack/branches/API — no update needed |
| 2 | Module docstrings | No | N/A | Zero `.py` files in diff |
| 3 | External attribution | No | N/A | Builder notes cite no external sources; taxonomy is internal OwlBear concepts |
| 4 | CLI changes | No | N/A | No CLI components touched |
| 5 | Research doc | No | N/A | Task references parent #984 brief; no research doc produced |

### Files Updated

None — no documentation files require updating. SKILL.md changes are the task deliverable (committed by builder at `0ef5b6d9`).

### SKILL.md Verification

- `### Boundary Fitness` present under Principles: 5-row checklist table, path-coverage heuristic (< 30%), references to 80% Rule and File Type Selection (not restated). ✅
- `## Instruction File Taxonomy (.instructions.md)` present with `### Stubs — Safety Nets` (stub table intact) and `### Authority Files — Embedded Rules` (naming convention, applyTo scope expectations, copilot-instructions.md separation note). ✅
- Existing content preserved; no internal duplication. ✅

### Scratch Files

No `992-*` scratch files found. Clean.
[[2026-04-19]]

## Audit

### AC Verification

| Refined AC Line | Evidence | Status |
|-----------------|----------|--------|
| Instruction File Taxonomy section (stubs + authority file sub-sections) | SKILL.md L259: `## Instruction File Taxonomy (.instructions.md)` with `### Stubs — Safety Nets` (L263) and `### Authority Files — Embedded Rules` (L289) | PASS |
| Authority file rules: (a) when inline, (b) naming, (c) applyTo scope, (d) copilot-instructions.md separation | L291-293 (when), L308 (naming), L310 (applyTo scope), L312 (copilot-instructions.md NOT an instruction file) | PASS |
| Boundary Fitness section: 80% Rule ref, path-coverage heuristic (<30%), File Type Selection ref | L58-77: 5-row checklist table + path-coverage heuristic + reference footer | PASS |
| Existing content preserved; additions additive; heading rename permitted | Stub table intact at L270-276; heading renamed from "Instruction Stub Format" to "Instruction File Taxonomy" | PASS |
| No rules duplicated from other skills; no internal duplication | References only ("see 80% Rule", "see File Type Selection table"); no verbatim rule text duplicated | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all pre-existing in serve/mcp-knowledge/tests/ — unrelated to this docs-only task), 0 skipped
- ruff: clean (0 violations)

### Architect Quality: 4/5

Initial AC had 3 ambiguities (80% rule reference vs restate, "loading-model unit fit" undefined, section placement unclear). Architecture review + challenger interaction resolved all three. Refined AC was specific and verifiable. Minor gap: required refinement rather than being right first time.

### Deduction Breakdown

- No AC evidence gaps: -0
- Lint clean: -0
- Full-suite failures outside task scope: -0
- Reviewer evidence detailed and present: -0
- AC quality 4/5 (above ≤3 threshold): -0

### Confidence: .98

### Action: archive
