---
id: 1001
title: Create h-memory-structure handbook skill
status: archived
priority: medium
created: 2026-04-18 21:34:33.195499+00:00
updated: 2026-04-19 02:48:52.510150+00:00
tags:
- agent
- agent-ecosystem
parent: 984
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Create `share/skills/h-memory-structure/SKILL.md` — a terse handbook defining structural standards for OwlBear memory entries (file-based and MCP-based). Terse-by-construction: required fields only, tight length limits, explicit anti-patterns.

## Context

No handbook currently exists for memory entry structure. `owlbear-system.instructions.md` § Memory Governance defines which tier stores what, but not the shape, quality bar, or deduplication rules for entries. The audit prompt (Task 2, sibling) needs this handbook to probe Memory Governance findings.

## Acceptance Criteria

- [ ] New file at `share/skills/h-memory-structure/SKILL.md` with frontmatter: `name: h-memory-structure`, `description: "Handbook: Memory entry structure — tiers, entry shape, and content-quality bar"`, `user-invocable: false`.
- [ ] `## Entry Shape` section with ≤5 required fields per entry template. Zero optional fields.
- [ ] `## Tier-Content Fit` table mapping content types to memory tiers per `owlbear-system.instructions.md` § Memory Governance. References (does not restate) the governance section.
- [ ] `## File vs. MCP Relationship` section: when each is used, dual-write during migration (per `r-pipeline-protocol` § Post-task Reflection).
- [ ] `## Deduplication Rules` section: how to detect duplicates, supersede/merge procedure, which entry wins on conflict.
- [ ] `## Content-Quality Bar` section: concrete pass/fail criteria (not aspirational). Example: "Entry must cite a specific task ID or file path; generic advice fails."
- [ ] `## Anti-Patterns` section with ≤5 items, each ≤2 lines.
- [ ] Total file length ≤150 lines.
- [ ] No optional fields, no menus of choices, no "consider also" language.

## Files

- `share/skills/h-memory-structure/SKILL.md` (new)

[[2026-04-18]]

## Architecture Review

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1 — Frontmatter spec | CLEAR | No change |
| AC2 — Entry Shape ≤5 fields | REFINED | Clarified: fields = `record_learning` authoring params; handbook may promote tool-optional fields to required if always needed for quality entries |
| AC3 — Tier-Content Fit table | CLEAR | No change |
| AC4 — File vs MCP Relationship | CLEAR | `r-pipeline-protocol` § Post-task Reflection confirmed present and covers dual-write |
| AC5 — Deduplication Rules | REFINED | Scoped to write-time prevention only; must reference `w-mem-curation` for curation-time dedup |
| AC6 — Content-Quality Bar | CLEAR | No change; may include confidence calibration guidance |
| AC7 — Anti-Patterns | CLEAR | No change |
| AC8 — ≤150 lines | CLEAR | Tight but achievable for 6 sections + frontmatter |
| AC9 — No optional fields | CLEAR | Handbook may promote tool-optional params (e.g. scope_agent) to handbook-required |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One skill file, one concern (memory entry structure) |
| Interface clarity | PASS | After refinement, all AC lines are mechanically verifiable |
| Dependency correctness | PASS | No dependencies; independent of siblings #1000, #1002 |
| Module layering | PASS | `share/skills/h-memory-structure/` follows handbook convention |
| TDD compliance | PASS | Non-impl task tagged `agent` for test-writer pass-through |
| KISS/YAGNI | PASS | ≤150 lines + ≤5 fields + explicit anti-pattern limits enforce minimality |
| Premise challenge | PASS | No existing handbook covers entry shape/quality. `h-mcp-memory` = tool reference, `w-mem-curation` = curation workflow, Memory Governance = tier allocation. Gap confirmed. |
| Pattern consistency | PASS | Follows `h-*` handbook naming, SKILL.md structure per `h-agent-structure` |
| Security surface | PASS | No system boundaries — markdown artifact only |
| Single domain | PASS | Agent-ecosystem domain only |

### Architecture Notes

- **Authoring fields**: `record_learning` takes 4 required (`agent_id`, `content`, `category`, `confidence`) + 2 optional (`scope_agent`, `scope_project`). The handbook's ≤5 required fields should be derived from this interface — promoting `scope_agent` to required is sound since `r-pipeline-protocol` always passes it.
- **Dedup boundary**: `w-mem-curation` Step 2 owns curation-time dedup (post-write grouping and merging). This handbook's dedup rules must target write-time prevention: "check before recording." No overlap if boundary is explicit.
- **Discoverability**: Task #1003 (audit prompt) will reference this skill. Auto-loading by relevance handles other consumers. Not an AC gap.
- **Confidence calibration**: `tools.py` enforces floor of 0.7; `r-pipeline-protocol` defaults to 0.8. Handbook's Content-Quality Bar section is the natural home for calibration guidance.

### Challenge Results

- Challenger: reconsider (0.55)
- Key concerns: (C1) field list naming, (C2) dedup overlap with w-mem-curation, (C3) optional fields tension
- Architect response: ACCEPTED C2 — refined AC5 with write-time scope boundary. C1/C3 resolved by clarifying AC2/AC9 intent in this review note. C1 was about my reasoning, not the AC text — the AC says "≤5 required fields" without naming them, giving the builder correct flexibility. B1 (discoverability) addressed by #1003 dependency.

### Verdict: REFINE → APPROVE

### Action Taken: Refined AC2 and AC5 for precision, approved to todo. Builder guidance in architecture notes above

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged `agent`) — no tests applicable.
- AC deliverable: `share/skills/h-memory-structure/SKILL.md` only. No Python source files, no testable interfaces.
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

**Files changed:** `share/skills/h-memory-structure/SKILL.md` (new, 110 lines)

**AC verification:**

- [x] Frontmatter: `name: h-memory-structure`, correct description, `user-invocable: false`
- [x] `## Entry Shape` — 5 required fields: `agent_id`, `content`, `category`, `confidence`, `scope_agent`. Zero optional fields listed.
- [x] `## Tier-Content Fit` — table maps content types to tiers; references `owlbear-system.instructions.md § Memory Governance` as source of truth (does not restate)
- [x] `## File vs. MCP Relationship` — 4-row table covering standard use, MCP unavailable, curation pass, pre-flight. References `r-pipeline-protocol § Post-task Reflection` for dual-write procedure.
- [x] `## Deduplication Rules` — write-time only; explicit boundary ("Curation-time dedup … handled by `w-mem-curation` Step 2"); supersede/merge procedure; conflict resolution rule.
- [x] `## Content-Quality Bar` — concrete pass criteria (cites task ID/file/tool) and fail criteria (generic, no citation, ambiguous scope, duplicate). Confidence calibration table (0.7–1.0) per architecture notes.
- [x] `## Anti-Patterns` — exactly 5 items, each ≤2 lines.
- [x] Total length: 110 lines (limit 150) ✓
- [x] No optional fields, no "consider also" language ✓

**Lint:** N/A (markdown only, not Python)
**Tests:** Non-implementation task — test-writer pass-through confirmed in task body.
**Commit:** `9e181283` — docs(agent): add h-memory-structure handbook skill (#1001)
[[2026-04-19]]

## Review Evidence

**Type:** Non-implementation task (markdown artifact only). No Python source files, no tests to run. Quality-Runner not applicable — test-writer confirmed pass-through in task body.

**File reviewed:** `share/skills/h-memory-structure/SKILL.md` (110 lines, commit `9e181283`)

**Structure compliance (`h-agent-structure`):**

- File type: SKILL.md ✓ (handbook — reusable domain knowledge, on-demand load)
- Naming: `h-memory-structure` with `h-` prefix ✓
- Location: `share/skills/h-memory-structure/SKILL.md` ✓

**AC Compliance Table:**

| AC line | Evidence | Status |
|---------|----------|--------|
| AC1 — Frontmatter: `name: h-memory-structure`, correct description, `user-invocable: false` | Lines 2-4 match exactly | PASS |
| AC2 — `## Entry Shape` ≤5 required fields, zero optional fields | Lines 17-22: exactly 5 fields (`agent_id`, `content`, `category`, `confidence`, `scope_agent`); no optional fields listed; `scope_project` explicitly omitted with note | PASS |
| AC3 — `## Tier-Content Fit` table references (not restates) `owlbear-system.instructions.md § Memory Governance` | Line 30: "Per `owlbear-system.instructions.md` § Memory Governance (single source of truth)"; 7-row table adds "Not memory" rows as practical extensions — verified against governance source, no verbatim restatement | PASS |
| AC4 — `## File vs. MCP Relationship`: when each used, dual-write during migration, references `r-pipeline-protocol § Post-task Reflection` | Lines 59-66: 4-row table covers standard/unavailable/curation/pre-flight; explicit reference to `r-pipeline-protocol § Post-task Reflection` (section confirmed at line 169 of SKILL.md) | PASS |
| AC5 — `## Deduplication Rules`: detect, supersede/merge, which-wins; write-time scoped, references `w-mem-curation` | Lines 70-87: explicit "write time" scope statement, references `w-mem-curation` Step 2 as boundary, 4-step procedure, "Which entry wins" rule | PASS |
| AC6 — `## Content-Quality Bar`: concrete pass/fail criteria (not aspirational) | Lines 89-107: binary "passes if all" / "fails if any" lists with specific citable criteria; confidence calibration table with 0.7–1.0 | PASS |
| AC7 — `## Anti-Patterns` ≤5 items, each ≤2 lines | Lines 109-end: exactly 5 items; each bold title + 1 sentence | PASS |
| AC8 — Total ≤150 lines | Builder-reported 110 lines; file content confirms this — read_file(1,150) did not overflow | PASS |
| AC9 — No optional fields, no menus, no "consider also" language | No optional fields in Entry Shape; category values are constraints not menus; no "consider also" language found | PASS |

**Cross-reference accuracy:**

- `record_learning` fields: handbook promotes `scope_agent` to required — consistent with architect approval in Architecture Notes (AC2 refinement)
- `r-pipeline-protocol § Post-task Reflection`: section confirmed present (line 169); dual-write procedure and `confidence=0.8` default match handbook guidance
- `owlbear-system.instructions.md § Memory Governance`: Tier-Content Fit table accurately reflects all 4 tiers + negative guidance from "Do NOT store" paragraph
- `h-mcp-memory`: Tool reference relationship correctly described

**Deductions:** 0

**Verdict:** PASS | confidence .97
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New skill file addition; copilot-instructions.md does not enumerate individual skills; no existing docs reference this skill |
| 2 | Module docstrings | No | N/A | No Python files created or modified |
| 3 | External attribution | No | N/A | All references (owlbear-system.instructions.md, r-pipeline-protocol, h-mcp-memory, w-mem-curation) are internal artifacts; no external sources studied |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No .owlbear/research/1001-* file found; task required no external research |

### Files Updated

- None

### Scratch Files Cleaned

- None (no .owlbear/scratch/1001-* files found)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — Frontmatter | Lines 2-4: name, description, user-invocable match spec exactly | PASS |
| AC2 — Entry Shape ≤5 fields | Lines 17-22: 5 fields (agent_id, content, category, confidence, scope_agent), zero optional | PASS |
| AC3 — Tier-Content Fit table | Line 30: references owlbear-system.instructions.md § Memory Governance; 7-row table, no verbatim restatement | PASS |
| AC4 — File vs MCP Relationship | Lines 59-66: 4-row table, references r-pipeline-protocol § Post-task Reflection | PASS |
| AC5 — Deduplication Rules | Lines 70-87: write-time scope, references w-mem-curation Step 2, 4-step procedure, conflict resolution | PASS |
| AC6 — Content-Quality Bar | Lines 89-107: binary pass/fail criteria with specific citations, confidence calibration table | PASS |
| AC7 — Anti-Patterns ≤5 items | Lines 109-end: exactly 5 items, each bold title + 1 sentence | PASS |
| AC8 — ≤150 lines | 110 lines confirmed via read_file | PASS |
| AC9 — No optional fields | No optional fields in Entry Shape, no "consider also" language | PASS |

### Test Results

- pytest: N/A (markdown-only artifact, no Python files changed; test-writer confirmed pass-through)
- ruff: N/A (no Python files)
- Quality-Runner: unavailable (not in agent list); zero regression risk for markdown-only deliverable

### Architect Quality: 5/5

Specific, mechanically verifiable AC lines. Challenger concerns addressed with refinements (AC2 field scope, AC5 dedup boundary). Architecture notes guided builder effectively on scope_agent promotion and confidence calibration placement.

### Deduction Breakdown

- AC lines without evidence: 0 (all 9 verified)
- Lint violations: 0 (N/A)
- AC quality ≤3: 0 (score 5)
- Missing reviewer evidence: 0 (present, detailed, .97)
- Full-suite failures: 0 (N/A)
- Quality-Runner unavailable: -.02 (conservative deduction for process gap, mitigated by zero-Python-change scope)

### Confidence: .98

### Action: archive
