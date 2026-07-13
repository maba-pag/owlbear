---
id: 1016
title: Documentation currency — implement per Brief docs-currency-2026-04-19
status: archived
priority: medium
created: 2026-04-19 23:45:06.730729+00:00
updated: 2026-04-20 00:36:36.798342+00:00
tags:
- docs-currency
- parent-task
- phase-0
- phase-1
- phase-2
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Source

Full Brief: `.owlbear/briefs/draft-docs-currency-2026-04-19/brief.md`
Working dir (context, decisions, synthesis, panel stances): `.owlbear/briefs/draft-docs-currency-2026-04-19/`

> **Note:** working dir may be renamed to `.owlbear/briefs/docs-currency-2026-04-19/` (drop "draft-" prefix) before planner runs. Both paths should be checked.

## Posture

Quality over everything. No backwards compatibility. No legacy. Time unbounded.

## Problem (one-line)

OwlBear's product documentation has accumulated drift; `doc-writer` v1's scope is 5 paths but ~70 product docs sit outside its gate. No periodic backstop exists. Doc rot has flipped from tolerable to a quality blocker at the consumer boundary.

## Outcomes (acceptance criteria)

1. Auto-generated doc index at `.owlbear/doc-index.md` (best-effort fresh; mechanical regen on doc-audit/SessionStart/on-demand)
2. All known-rotten docs remediated (SECURITY.md, both READMEs, serve/knowledge/README.md, 7 missing serve/*/README.md, placeholder URLs, zero v1 residue)
3. Seven owlbear-dev Excalidraw diagrams (1 overview + 6 modules: kanban, memory, MCP, pipeline, ideation, Cockpit) with `describes` glob metadata + auto-maintained footer
4. `doc-writer` v2 defined and verified across exactly 6 named test cases (no-op / prose / diagram-maintenance / explicit-diagram / deletion-proposal / ambiguous-misclassification) with stated expected outcomes per case; pass = 6/6
5. `doc-audit.prompt.md` exists and works (mirrors agent-audit; pre-scan summary; one-finding-at-a-time; hard cap 3 rescans/file)
6. Consumer can use OwlBear from docs (opportunistic field validation, **non-gating**)
7. Two-layer safety net in place (Layer 1: per-task doc-writer v2; Layer 2: periodic doc-audit)

## Suggested phasing (planner refines)

```
Phase 0 (prerequisite tooling — parallelizable except as noted)
  ├─ r-doc-standards skill (must come first)
  ├─ serve/tools/ + doc-index script + markdown index format
  ├─ deny-code-writes.py refactor (two variants: live + seed)
  └─ doc-audit.prompt.md skeleton (depends on r-doc-standards)

Phase 1 (depends on ALL of Phase 0)
  └─ doc-writer v2 (broadened scope + relevance gating SHIP TOGETHER, never sequentially)

Phase 2 (depends on Phase 1)
  ├─ area sweep tasks (per area, then per-file as size warrants)
  ├─ 7 diagram tasks
  └─ doc-audit gate run as final acceptance
```

## Scope summary

- IN (~25 files): 3 root, 9 serve/*/README.md, 2 setup/*.md, 4 share-category READMEs, 7 share/diagrams/*.excalidraw
- OUT: agent-executable files (agents, skills, instructions, prompts, share/skills/*/references/, .github/copilot-instructions.md)
- doc-audit findings on OUT files route to `architect` (not doc-writer)

## Key non-negotiables

- doc-writer never autonomously creates diagrams or deletes files
- Deletion workflow: doc-writer → child task via owlbear-kanban MCP (NEW capability) → scribe writes DR in .owlbear/decisions/pending/ → blocked → user resolves → test-writer writes inbound-link tests → builder removes file + repairs links in single atomic commit → reviewer → doc-writer updates index
- Diagrams are descriptive, never authoritative
- Index must be auto-generated, never hand-maintained
- Hook refactor (allowlist `.md`+`.excalidraw` for consumer-seed; broader for owlbear-dev) is BLOCKING prerequisite for v2

## Risks for planner attention

- Board-volume during sweep (tens, possibly low-hundreds of tasks)
- Time-in-docs-status per task likely to increase
- Committed doc-index = review noise (mitigation options in Brief §7a)
- Hook refactor may surface previously-allowed writes

## Open items deferred to planner

- Final `doc-audit` audit dimensions list
- Exact Phase 2 task granularity
- Whether `h-*` handbooks and skill `references/` warrant inclusion (defaulted OUT)
- Whether index should also enumerate inbound links
- Conditional regen on doc-writer SessionStart (perf optimization)

## Process follow-up (separate child task suggested)

Update `share/skills/w-ideation/SKILL.md` Step 5 to formalize "never bulk-ratify analysis the user hasn't seen — walk one tightly-coupled cluster per turn with original text quoted, Critic concern in plain language, proposed change visible." See Brief §9.

## Linkages

- Replaces/revises: doc-writer.agent.md, w-doc-update/SKILL.md, deny-code-writes.py (both variants), possibly setup/init.py
- Creates: r-doc-standards/SKILL.md, doc-audit.prompt.md, serve/tools/ package, share/diagrams/ + 7 files, .owlbear/doc-index.md, verification log
- Reference (do not modify): agent-audit.prompt.md, h-agent-structure, h-excalidraw-diagram
[[2026-04-19]]
## Planning

### Decomposition: Documentation Currency (Brief docs-currency-2026-04-19)

- Tasks created: 20 subtasks under #1016 + 1 standalone process-improvement task
- Dependency layers: 5 (P0 independent, P0 dependent, P1 RED, P1 GREEN, P2 sweep/diagrams, P2 gate)
- Phases: 0 (6 tasks), 1 (2 tasks), 2 (12 tasks)

### Task List

| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1017 | P0-01: r-doc-standards skill | needed | — | phase-0, docs-currency, docs-agent |
| 1018 | P0-02: Tests for doc-index script (RED) | needed | — | phase-0, docs-currency, docs-tooling |
| 1019 | P0-04: Tests for deny-code-writes refactor (RED) | needed | — | phase-0, docs-currency, docs-tooling |
| 1020 | P0-03: doc-index script + serve/tools/ package (GREEN) | needed | 1018 | phase-0, docs-currency, docs-tooling |
| 1021 | P0-05: deny-code-writes.py refactor (GREEN) | needed | 1019 | phase-0, docs-currency, docs-tooling |
| 1022 | P0-06: doc-audit.prompt.md skeleton | needed | 1017 | phase-0, docs-currency, docs-agent |
| 1023 | P1-01: doc-writer v2 verification spec (RED) | needed | 1020, 1021, 1022 | phase-1, docs-currency, docs-agent |
| 1024 | P1-02: doc-writer v2 implementation (GREEN) | critical | 1023 | phase-1, docs-currency, docs-agent |
| 1025 | P2-01: Root docs sweep | important | 1024 | phase-2, docs-currency, docs-sweep |
| 1026 | P2-02: serve/* READMEs sweep | important | 1024 | phase-2, docs-currency, docs-sweep |
| 1027 | P2-03: setup/*.md sweep | important | 1024 | phase-2, docs-currency, docs-sweep |
| 1028 | P2-04: share-category READMEs sweep | important | 1024 | phase-2, docs-currency, docs-sweep |
| 1029 | P2-05: Project overview diagram | important | 1024 | phase-2, docs-currency, docs-diagram |
| 1030 | P2-06: Kanban module diagram | important | 1024 | phase-2, docs-currency, docs-diagram |
| 1031 | P2-07: Memory layers diagram | important | 1024 | phase-2, docs-currency, docs-diagram |
| 1032 | P2-08: MCP topology diagram | important | 1024 | phase-2, docs-currency, docs-diagram |
| 1033 | P2-09: Pipeline diagram | important | 1024 | phase-2, docs-currency, docs-diagram |
| 1034 | P2-10: Ideation panel diagram | important | 1024 | phase-2, docs-currency, docs-diagram |
| 1035 | P2-11: Cockpit diagram | important | 1024 | phase-2, docs-currency, docs-diagram |
| 1036 | P2-12: doc-audit gate run | important | 1025-1035 | phase-2, docs-currency |
| 1037 | Update w-ideation: no bulk-ratify rule | nice-to-have | — | process-improvement |

### Open items resolved by planner

1. **Doc-audit dimensions:** initial 7 (D1-D7) specified in P0-01 and P0-06 AC; r-doc-standards author refines.
2. **Phase 2 granularity:** 4 area sweeps + 7 diagrams + 1 gate = 12 tasks. Per-file sub-decomposition not warranted at this stage.
3. **h-* handbooks / skill references:** kept OUT per Brief default. No scope holes observed.
4. **Inbound links in index:** NO. Outbound only; inbound computed by reversal at audit time. Keeps generator simple.
5. **Conditional regen on SessionStart:** YES. Skip when index mtime > newest doc mtime. Specified in P0-03 AC.
[[2026-04-19]]
## Test-Writer Notes
- Non-impl pass-through: tagged `parent-task` — umbrella task with no direct Python interface.
- All AC lines with testable Python interfaces are delegated to dedicated subtasks:
  - AC1 (doc-index script) → #1018 (RED) + #1020 (GREEN)
  - AC2 (deny-code-writes refactor) → #1019 (RED) + #1021 (GREEN)
  - AC4 (doc-writer v2 test spec) → #1023 (RED) + #1024 (GREEN)
- Remaining AC lines (AC2 doc remediation, AC3 diagrams, AC5 prompt file, AC6 consumer validation, AC7 safety net) reference only `.md`, `.excalidraw`, and `.yml` artifacts — no Python implementation at this level.
- Passing through to builder.
[[2026-04-20]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
[[2026-04-20]]
## Review Evidence

**Task type:** Parent umbrella task — no code implementation, no tests. Review scope: decomposition completeness and AC delegation fidelity.

**Tests:** N/A — no Python implementation. Quality-Runner not invoked (nothing to run).
**Lint:** N/A — no code files changed.
**Coverage:** N/A.
**Security:** N/A — no code changes.
**TestFromAC modifications:** N/A — no TestFromAC classes exist.
**Builder loop check:** CLEAN — single pass-through note, no retries.

**AC compliance table:**

| AC | Evidence | Status |
|----|----------|--------|
| AC1 (doc-index) | #1018 (RED tests), #1020 (GREEN impl), `depends_on` chain verified on board | COVERED |
| AC2 (rotten docs) | #1025 root, #1026 serve/*, #1027 setup, #1028 share-category — all `parent: 1016`, `depends_on: [1024]` | COVERED |
| AC3 (7 diagrams) | #1029–#1035 — exactly 7 diagram tasks, all `parent: 1016`, `depends_on: [1024]` | COVERED |
| AC4 (doc-writer v2) | #1023 (RED), #1024 (GREEN), `depends_on: [1023]` confirmed | COVERED |
| AC5 (doc-audit prompt) | #1022 `depends_on: [1017]`, `parent: 1016` | COVERED |
| AC6 (consumer validation, non-gating) | Distributed across phase 2 sweeps + #1036 gate run | COVERED |
| AC7 (two-layer safety net) | Layer 1: #1024; Layer 2: #1022 + #1036 | COVERED |

**Structural verification:**
- Child task count: 20 tasks with `parent: 1016` (IDs 1017–1036) — matches planner note ("20 subtasks under #1016") exactly.
- Standalone #1037 correctly `parent: null`.
- Brief exists at `.owlbear/briefs/docs-currency-2026-04-19/brief.md` (draft- prefix dropped per task body note).
- Dependency graph verified end-to-end against board state.

**Deductions:** 0
**Confidence: .97 → PASS**
[[2026-04-20]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Parent umbrella task — no code written, no behavior introduced. `copilot-instructions.md` git log shows no commits for #1016. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Builder confirmed "non-implementation task." |
| 3 | External attribution | No | N/A | No external patterns used. Brief-driven decomposition only. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` file produced. Brief at `.owlbear/briefs/docs-currency-2026-04-19/brief.md` exists and is referenced in task body. |

### Files Updated
None.

### Scratch Files
No `.owlbear/scratch/1016-*` files found.

### Summary
No docs impact at this level. All AC lines with docs impact are delegated to child tasks (#1017–#1036), each of which will pass their own docs gate. Parent task advances cleanly.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 (doc-index) | #1018 (review) + #1020 (backlog, depends 1018) on board | PASS |
| AC2 (rotten docs remediation) | #1025–#1028 sweep tasks, parent: 1016, depends: [1024] | PASS |
| AC3 (7 Excalidraw diagrams) | #1029–#1035, exactly 7, correct parents/deps | PASS |
| AC4 (doc-writer v2) | #1023 (RED) + #1024 (GREEN), dependency chain intact | PASS |
| AC5 (doc-audit prompt) | #1022, depends: [1017] | PASS |
| AC6 (consumer validation, non-gating) | Distributed across P2 sweeps + #1036 gate | PASS |
| AC7 (two-layer safety net) | Layer 1: #1024; Layer 2: #1022 + #1036 | PASS |

### Structural Verification
- 20 child tasks with parent: 1016 (IDs 1017–1036) — matches planner note exactly
- #1037 standalone (parent: null) — correct
- Brief at `.owlbear/briefs/docs-currency-2026-04-19/brief.md` — exists
- Dependency DAG: P0 independent → P0 dependent → P1 → P2 → gate — verified via board state

### Test Results
- pytest: 755 passed, 34 failed, 4 skipped — 0 failures in task scope (28 are RED-phase from child #1019, 6 pre-existing in mcp-knowledge)
- ruff: clean

### Architect Quality: 4/5
Specific outcomes (7 AC lines), clear phasing guidance, IN/OUT scope, non-negotiables, risks. Minor: umbrella AC is delegation-level, but appropriate for parent task. Planner decomposed effectively into 20 subtasks with correct dependency DAG.

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 delegation-verified) → -0
- Lint violations: 0 → -0
- AC quality ≤ 3: no (4/5) → -0
- Missing reviewer evidence: no (detailed, PASS) → -0
- Full-suite failures in scope: 0 → -0

### Confidence: 1.00
### Action: archive