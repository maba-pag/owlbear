---
id: 1404
title: 'A1: h-ac-quality skill — unified two-tier, six-rule AC schema'
status: archived
priority: medium
created: 2026-05-07T23:16:25.145713+00:00
updated: 2026-05-08T00:35:57.675250+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
- agent
parent: 1403
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `h-ac-quality` skill file created at `share/skills/h-ac-quality/SKILL.md`
P2: Skill contains meta-rule: "Every AC line must be independently verifiable by a downstream agent without access to the author's intent"
P2: Skill contains Tier 1 (Behavior AC) with three rules: B1 (function-scoped), B2 (input→output pairs), B3 (no naked quantifiers with 7 banned words)
P2: Skill contains Tier 2 (Process AC) with three rules: P1 (agent/stage-scoped), P2 (observable artifact/state change), P3 (verification method stated)
P2: Skill contains two-pass validation description: mechanical lint pass (B3 banned words, P1 agent name, AC numbering) → semantic review pass
P2: Skill contains bad→good transformation examples for each rule
P2: Skill contains validation checklist usable by both planner (drafting) and architect/challenger (validation)
P3: Verification by artifact inspection of the created skill file

## Scope

**In scope:** New skill file creation, schema definition, examples, validation checklist
**Out of scope:** Updating planner/architect/challenger to reference this skill (A2, A3), any code changes
[[2026-05-07]]
## Research\n- Research doc: .owlbear/research/1404-ac-quality-skill-schema.md\n- Sources: 7 studied (4 codebase, 3 web), 5 high-relevance\n- Recommendation: Proceed as specified in Brief #1403 (confidence: 0.90)\n\nKey findings:\n1. AC quality rules are scattered across 7+ skill locations with no single authority — consolidation is warranted.\n2. Proposed B1–B3 (Behavior AC) rules are well-grounded in standard AC best practices (Atlassian, AltexSoft, NextGenAnalysts), adapted for code-scoped verification.\n3. Proposed P1–P3 (Process AC) rules are novel extensions for AI agent pipeline AC — no direct prior art, but follow the same testability/independence principles.\n4. B3 banned words list (7 words) targets the exact root cause of 5/5 worst pipeline tasks.\n5. Follow-up tasks #1405 (A2: planner update) and #1406 (A3: architect update) already exist with correct dependencies.\n\nT1 (Autonomous) — no architecture changes, no security implications, no new capabilities beyond brief spec.
[[2026-05-07]]
## Architecture Review

**Verdict: APPROVE → todo**

### AC Assessment

| AC Line | Assessment | td |
|---------|-----------|-----|
| P1: skill file at `share/skills/h-ac-quality/SKILL.md` | Clear path, verifiable by existence | td:0 |
| P2: meta-rule (independent verifiability) | Specific text, verifiable by inspection | td:0 |
| P2: Tier 1 (B1, B2, B3) | Structure defined; B3 banned words enumerated in brief and research doc | td:0 |
| P2: Tier 2 (P1, P2, P3) | Parallel structure to Tier 1, clear | td:0 |
| P2: two-pass validation | Mechanical + semantic passes specified | td:0 |
| P2: bad→good examples for each rule | 6 rules = 6 examples minimum, verifiable | td:0 |
| P2: validation checklist | Audience (planner + architect/challenger) specified | td:0 |
| P3: verification by artifact inspection | Method note, not behavioral AC — acceptable | td:0 |

All AC lines: td:0. **Test-writer: SKIP** — pure skill-file creation, no testable code.

### Architecture Notes

1. **No existing skill conflict.** Confirmed `share/skills/h-ac-quality/` does not exist. 16 existing h-* skills follow consistent frontmatter pattern (name, description, user-invocable: false).
2. **Pattern consistency.** Skill should follow standard h-* structure: YAML frontmatter + markdown body. Existing examples: `h-agent-structure`, `h-memory-structure`.
3. **B3 banned words.** The 7 words (all, every, correctly, properly, exactly, valid, appropriate) are enumerated in both the brief (line 35) and research doc (§3.2). Builder has unambiguous source of truth.
4. **Scope boundary respected.** Task creates the skill only; consumer updates (planner, architect/challenger) are deferred to #1405 and #1406 with correct `depends_on: [1404]`.
5. **Single responsibility.** One skill file, one schema definition. No code, no consumer changes. ✓

### Dependency Analysis

- No dependencies to verify (Layer 0 task).
- Downstream: #1405, #1406, #1407 all depend on this task.

### Refinements Applied

- Added `agent` tag for test-writer pass-through (task creates agent-ecosystem artifact, not code).

### Challenge

Challenge: SKIP — all AC lines td:0, no testable code, pure documentation artifact.
[[2026-05-07]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC lines are (td:0) per architect review — pure skill-file creation, no testable Python interfaces.
- Passing through to builder.
[[2026-05-07]]
## Builder Notes
- Implementation: created share/skills/h-ac-quality/SKILL.md
- Scope: non-code skill artifact (no source/runtime behavior changes)
- Artifact verification: confirmed the skill includes meta-rule, Tier 1 (B1-B3), Tier 2 (P1-P3), two-pass validation flow, six bad->good rule examples, and a dual-role validation checklist (planner + architect/challenger)
- Tests: not applicable for this AC set (artifact-inspection task)
- Lint/coverage: not applicable for markdown skill artifact
- Commit: c474918eba159440c48d3dcc10bf8bbbe385d504 (feat: add AC quality schema skill (#1404, builder))

[[2026-05-08]]
## Review Evidence
### Scope and Provenance
- Reconstructed changed-file scope: `share/skills/h-ac-quality/SKILL.md` from builder notes, task scope, and current-tree workspace search.
- Current-tree search for `h-ac-quality` found the new skill plus brief/task/research references only; no live planner/architect consumer file updates were present, which is consistent with the task's out-of-scope boundary.
- Builder loop check: one `## Builder Notes` section only; no retry loop detected.

### Quality Runner
- Applicability: `td:0` markdown handbook task. `quality-runner` reported tests, lint, and coverage as not applicable for a markdown-only artifact and did not fabricate a green result.
- Test Results: N/A
- Lint Results: N/A via quality-runner scope; editor diagnostics on `share/skills/h-ac-quality/SKILL.md` reported no errors.
- Coverage: N/A

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| P1: `h-ac-quality` skill file created at `share/skills/h-ac-quality/SKILL.md` | File exists at `share/skills/h-ac-quality/SKILL.md`; frontmatter present at lines 1-4 with `name: h-ac-quality` | PASS |
| P2: meta-rule present | Exact meta-rule text present at `share/skills/h-ac-quality/SKILL.md:13` | PASS |
| P2: Tier 1 (B1/B2/B3) present | Tier 1 section at `share/skills/h-ac-quality/SKILL.md:15`; B1/B2/B3 headings at lines 19, 26, 33; 7 banned words enumerated at lines 37-44 | PASS |
| P2: Tier 2 (P1/P2/P3) present | Tier 2 section at `share/skills/h-ac-quality/SKILL.md:48`; P1/P2/P3 headings at lines 52, 59, 66; verification methods listed at lines 71-74 | PASS |
| P2: two-pass validation description present | `## Two-Pass Validation` at line 76; mechanical pass bullets at lines 80-83; semantic pass bullets at lines 85-88 | PASS |
| P2: bad->good transformation examples for each rule | Example headings present for B1/B2/B3/P1/P2/P3 at lines 94, 99, 104, 109, 114, 119 | PASS |
| P2: validation checklist usable by planner and architect/challenger | `## Validation Checklist` at line 124 with separate `Planner Draft Checklist` at line 128 and `Architect/Challenger Validation Checklist` at line 139 | PASS |
| P3: verification by artifact inspection | Review performed directly against the created artifact; skill also names `artifact inspection` as an allowed method at `share/skills/h-ac-quality/SKILL.md:71` | PASS |

### Pass 1 Checks
- Test-writer audit: SKIP — all AC lines are `td:0`; no `TestFromAC_*` tests expected.
- Test integrity: SKIP — no task tests exist.
- Security review: No executable code, dependency, secret, or input-surface changes in review scope.
- Test quality / implementation-aware test gaps: Not applicable to this markdown artifact task.
- Data safety: No runtime state or persistence behavior changed.
- Necessity check: In scope and justified by parent brief/task dependency chain.
- Builder process quality: CLEAN

### Deductions
- `-0.03` confidence: Git diff/status verification was unavailable in this tool surface, so commit-scope and dirty-tree checks were reconstructed from builder notes plus current-tree inspection rather than direct git evidence.
- `-0.01` confidence: No automated markdown linting is provided by `quality-runner`; artifact quality rests on direct manual audit plus editor diagnostics.

### Verdict
PASS -> docs | confidence 0.94

### Action
- Advance to `docs`.
- No blocking findings.
[[2026-05-08]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed file `share/skills/h-ac-quality/SKILL.md` is OUT of scope (SKILL.md). No IN-scope README/guide references `h-ac-quality`. |
| 2 | Module docstrings | No | N/A | No Python modules changed. |
| 3 | External attribution | Yes | Verified | 3 web sources (NextGenAnalysts, Atlassian, AltexSoft) already entered in `.owlbear/sources/overview.md` §"AC Quality Skill Schema (Task #1404)" at lines 9–11. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1404-ac-quality-skill-schema.md` exists; referenced in task body; follow-up tasks #1405 and #1406 exist with `depends_on: [1404]`. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: share/**` — matches the new skill file. Footer updated: `2026-05-05 (f7592274)` → `2026-05-08 (c474918e)`. Committed as `39c3c864`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification

- `share/skills/h-ac-quality/SKILL.md` — OUT of scope (agent-executable SKILL.md; not edited).
- Research doc and sources entries — IN scope; verified complete.
- `share/diagrams/project-overview.excalidraw` — IN scope; footer updated.

### Files Updated

- `share/diagrams/project-overview.excalidraw` — footer only (commit `39c3c864`)

### Scratch Files

None found (`/owlbear/scratch/1404-*`).

### Child Tasks

None.
[[2026-05-08]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| P1: skill file at path | File exists at share/skills/h-ac-quality/SKILL.md; frontmatter name: h-ac-quality | PASS |
| P2: meta-rule | Line 13: "Every AC line must be independently verifiable..." | PASS |
| P2: Tier 1 (B1/B2/B3) | Lines 15-46; B1 function-scoped, B2 input-output, B3 banned words (7 enumerated) | PASS |
| P2: Tier 2 (P1/P2/P3) | Lines 48-74; P1 agent-scoped, P2 artifact/state, P3 verification method | PASS |
| P2: two-pass validation | Lines 76-88; mechanical lint pass + semantic review pass | PASS |
| P2: bad-to-good examples | 6 examples (B1/B2/B3/P1/P2/P3) at lines 90-120 | PASS |
| P2: validation checklist | Lines 124-150; Planner Draft + Architect/Challenger sections | PASS |
| P3: artifact inspection | Verified directly by reading the file | PASS |

### Test Results
- pytest: 4789 passed, 215 failed (all pre-existing in unrelated modules: engine accessor migration, MCP memory, cockpit error envelope, PDS build compat)
- ruff: 12 violations in serve/tools/ and serve/knowledge/ (not in task scope)
- No regressions attributable to this markdown-only task

### Architect Quality: 4/5
AC lines are specific, enumerated, and independently verifiable. Minor structural note: multiple P2 lines could benefit from distinct numbering, but each was unambiguous in practice.

### Deduction Breakdown
- AC lines without evidence: 0 (all 8 verified) = 0
- Lint in task scope: none = 0
- AC quality (4/5, above threshold): 0
- Reviewer evidence: present and detailed with line numbers = 0
- Full-suite failures in task scope: none = 0

### Confidence: 1.00
### Action: archive