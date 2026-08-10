# Brief: Pipeline Review Rethink

## Problem

The OwlBear pipeline's quality gates are misaligned with their cost. The iteration spirals are multi-causal: vague AC wording, proof-quality defects in tests, and the reviewer's first-failure gating pattern all contribute. Archive analysis of the 5 worst tasks shows:

1. **Vague AC cause iteration spirals.** 5/5 worst tasks trace to infinitely-divisible AC wording ("match exactly," "all modes"). #1061 spiraled through 10+ rounds, 6 FAILs, 3 loop-breakers. The planner creates vague AC; the architect doesn't always catch them.

2. **Reviewer cost exceeds value delivered.** Reviewer runs 3x longer than any other agent, re-executes the same tests the builder already ran, and gates on first failure — turning 2 legitimate findings into 8+ pipeline runs.

3. **Test lifecycle gap.** 219 stale task-scoped tests in `tests/` from completed/archived tasks. No consolidation mechanism. TestFromAC immutability blocks natural cleanup.

4. **Agent role boundaries overlap.** Reviewer checks correctness (auditor's job). Auditor re-checks completeness (reviewer's job). Overlapping mandates produce redundant work and inconsistent verdicts.

## Mental Model: Checker Subagent Pattern

Each pipeline agent has (or could have) a **checker subagent** for self-validation:

- **Builder → Reviewer** (externalized checker). Stays external: combining blocks parallel work; reviewer rejects to test-writer/architect, not just builder.
- **Architect → Challenger** (expanded). Validates AC quality in addition to design decisions. Architect acts only if challenger flags issues.
- **Planner** drafts AC using `h-ac-quality` rules. Architect is the AC quality authority; planner is the drafter. When planner-created AC meet the quality bar, architect's checker approves without redundant review.
- **Researcher → Challenger** (retained). Validates research findings quality. No new scope added.
- **Test-writer, doc-writer** — checkers dropped (cost/benefit insufficient).
- **Auditor** — pipeline-end gate, not a checker.

## Decisions

### D1: AC Quality Schema — Unified two-tier, six-rule schema

**Meta-rule:** Every AC line must be independently verifiable by a downstream agent without access to the author's intent.

**Tier 1 — Behavior AC** (code changes):
- B1: Function-scoped — name the function/endpoint/command under test
- B2: Input→output pairs — concrete input condition + expected observable output
- B3: No naked quantifiers — 7 banned words (all, every, correctly, properly, exactly, valid, appropriate) unless followed by exhaustive enumeration

**Tier 2 — Process AC** (workflow/role/pipeline changes):
- P1: Agent/stage-scoped — name the agent, skill, or pipeline stage
- P2: Observable artifact/state change — before→after difference
- P3: Verification method stated — artifact inspection, stage-transition audit, field presence, or diff comparison

**Validation:** Two-pass. Mechanical lint (B3 banned words, P1 agent name present, AC numbering) → semantic review (challenger validates slot content quality).

Ships as `h-ac-quality` skill section, referenced by planner (drafting) and architect/challenger (validation).

### D2: Evidence Handoff — Trust the builder

No evidence formality. Builder runs quality-runner, writes results in task body. Reviewer reads them. No hashes, no provenance, no verification layer. If results are fabricated, the auditor's full suite run catches the discrepancy.

**Separate fix:** Pre-flight commit check in `end_work` — each agent verifies its own files are committed before calling `end_work`. The check is **scoped to the agent's file domain** (researcher: `.owlbear/research/`, test-writer: `tests/`, builder: `serve/*/src/`, etc.) — NOT raw `git status --porcelain`, which would show other agents' dirty files in the shared worktree. Fixes researcher/test-writer ~20% commit miss rate without PostToolUse hooks (which would cause overcommits with parallel agents).

**Protocol language update:** The current "never trust self-assessment/reporting" rule in `r-pipeline-protocol` is softened to: "Upstream evidence is valid input. Verify through independent checks only when cost-justified. The auditor serves as the pipeline-end integrity gate."

### D3: Finding vs. Opinion

Reviewer produces two output sections:
- **Review Evidence** — findings only. Each cites a specific AC line or factual code/test deficiency. ≥1 finding = FAIL.
- **Observations** — opinions, improvement suggestions, non-blocking. Never affects the verdict. If the task passes (zero findings), the builder never sees observations. If rejected for a finding, builder sees observations during rework and can fix them "for free."

**The rule:** Every item in Review Evidence must cite an AC line or a factual deficiency. No AC citation = opinion = goes in Observations.

**PASS case:** When reviewer finds zero findings, it writes a one-line confirmation: "Verified: AC→code mapping complete, test→AC alignment confirmed, proof sufficiency met. Zero findings." This ensures the auditor knows what was checked even when nothing was flagged.

### D4: Consolidation-Test Trigger

Planner creates a consolidation-test task upfront during decomposition when ≥2 implementation tasks exist under a common parent. The task:
- Has `deps:` listing all sibling implementation task IDs
- Has title pattern: "consolidation test: {feature name}"
- Is created alongside the implementation tasks

**Backstop:** Architect's checker (challenger) detects missing consolidation-test tasks during AC validation. Logic: if task has ≥2 sibling implementation tasks under same parent AND no sibling consolidation-test task → flag for planner.

Single tasks (no parent, no siblings): no consolidation-test task needed — the task's own test suite is sufficient.

### D5: Legacy Audit Prompt

`legacy-audit.prompt.md` — a user-triggered one-shot prompt that scans for:
- `TODO(#nnnn)` where the task is archived/done
- Dead imports and zero-caller functions
- Mock objects referencing patterns no longer in production
- Test files `test_*_{task_id}.py` where task is archived but test remains
- Functions/modules with "legacy," "compat," "bridge," "shim" in names

Produces a ranked cleanup report grouped by type. Not auto-fixable. User decides what to clean up. No pipeline complexity added.

## Deliverables

### Workstream A: AC Quality (highest leverage)

| # | Deliverable | Type | Dependencies |
|---|-------------|------|--------------|
| A1 | `h-ac-quality` skill — unified schema with meta-rule, 2 tiers, 6 rules, bad→good transformations, validation checklist | Skill creation | None |
| A2 | Planner skill update — reference `h-ac-quality` for AC drafting, create consolidation-test tasks during decomposition, enforce routing (planner creates tasks at `backlog`, never `todo` — only architect moves `backlog→todo`) | Skill modification | A1 |
| A3 | Architect/challenger skill update — expand challenger to validate AC quality using `h-ac-quality`, detect missing consolidation-test tasks | Skill modification | A1 |

### Workstream B: Reviewer Restructure

| # | Deliverable | Type | Dependencies |
|---|-------------|------|--------------|
| B1 | `w-code-review` skill rewrite — batch all findings, finding vs. opinion separation (Review Evidence + Observations sections), stop re-executing tests (read builder's quality-runner output), scoped 3-item checklist (AC→code mapping, test→AC alignment, proof sufficiency with boundary examples), remove TestFromAC immutability rule. Also update `r-pipeline-protocol` trust model and reviewer contract to match new evidence model. | Skill rewrite + protocol update | A1, D2 (CI/SAST must be ready before reviewer stops cognitive security scanning) |
| B2 | Loop-breaker update in `r-pipeline-protocol` — change from 3 FAILs to 2 batch cycles (source: panel convergence C3, not D1-D5 decision) | Protocol modification | B1 |

### Workstream C: Role Sharpening

| # | Deliverable | Type | Dependencies |
|---|-------------|------|--------------|
| C1 | Auditor skill update — focus on regression + intent, remove overlap with reviewer, keep architect-quality scoring | Skill modification | B1 (need to know reviewer's final scope to draw boundary) |
| C2 | Test-writer skill update — default exact-value assertions, structural test separation (task tests in `tests/`, durable in `serve/*/tests/`), expanded mandate for consolidation-test tasks (test-writer can create/modify durable tests in `serve/*/tests/` during consolidation). Also update `h-python-conventions`, `w-tdd-green`, and `w-test-curation` to reflect new test placement conventions across all agents. | Skill modification + convention updates | None |
| C3 | Role boundary documentation — each agent's "in scope / out of scope" explicit in skill files | Documentation | A2, A3, B1, C1 |

### Workstream D: Pipeline Protocol

| # | Deliverable | Type | Dependencies |
|---|-------------|------|--------------|
| D1 | Pre-`end_work` scoped commit check — each agent verifies uncommitted files in its own file domain (researcher: `.owlbear/research/`, test-writer: `tests/`, builder: `serve/*/src/`, etc.) before calling `end_work`. NOT raw `git status --porcelain`. | Protocol modification | None |
| D2 | CI/SAST baseline — deterministic security scanning as prerequisite for removing reviewer's cognitive security checks (source: panel convergence C7) | Infrastructure | None (but must complete before B1 removes reviewer's security scanning) |

### Workstream E: Cleanup

| # | Deliverable | Type | Dependencies |
|---|-------------|------|--------------|
| E1 | `legacy-audit.prompt.md` — cleanup scan prompt | Prompt creation | None |
| E2 | Stale test cleanup — delete/archive 219 task-scoped tests from completed tasks | One-time task | C2 AND B1 (need structural separation rules AND TestFromAC immutability removed first) |

## Sequencing

```
A1 (AC quality skill)
├── A2 (planner update)
├── A3 (architect update)
└── B1 (reviewer rewrite)
    ├── B2 (loop-breaker)
    ├── C1 (auditor update)
    └── C3 (role boundaries)

C2 (test-writer update + convention updates)
    │
    └── E2 (stale test cleanup) ← also depends on B1 (immutability removed)

D1 (commit check) — independent
D2 (CI/SAST) — independent
└── B1 (reviewer rewrite) ← also depends on D2 (CI/SAST must be ready)
E1 (legacy-audit prompt) — independent
```

**Critical path:** A1 → B1 → C1. The AC quality skill is the foundation; reviewer rewrite depends on it (and D2); auditor update depends on knowing the reviewer's final scope.

**Parallel work:** C2, D1, D2, E1 can all proceed independently from the start.

## Transition: In-Flight Tasks

Tasks already on the board under the current model:
- Tasks in `in-progress`, `review`, or `done` finish under current rules.
- Tasks already in `todo` are reset to `backlog` so the architect can re-validate their AC under the new quality rules. We can afford it.
- All tasks in `backlog` (including reset ones) and new tasks are subject to the mandatory architect gate and new AC quality rules.
- **Retroactive consolidation-test creation:** For existing feature chains (≥2 implementation tasks under a common parent) that lack a consolidation-test task, the planner creates one. Nothing prevents retroactive creation — the consolidation-test simply depends on the existing implementation tasks.

## Scope Boundaries

**In scope:**
- All agent skill files that define quality-gate behavior
- Pipeline protocol (`r-pipeline-protocol`) for commit discipline and loop-breaker
- One new skill (`h-ac-quality`), one new prompt (`legacy-audit`)
- CI/SAST setup as prerequisite infrastructure
- 219 stale test cleanup

**Addressed outside pipeline integration:**
- Temporary implementation lifecycle — addressed by D5 (`legacy-audit.prompt.md`) through user-triggered scanning rather than pipeline complexity. See synthesis.md for the original gap analysis.

**Out of scope:**
- Doc-writer agent (needs separate rebuild — acknowledged in discovery)
- Orchestrator agent (no changes needed for this restructuring)
- MCP server code (pipeline changes are skill-level, not tool-level)
- Frontend/Cockpit (unrelated)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AC quality rules are too rigid for edge-case tasks | Medium | Medium | Meta-rule as fallback; rules are floors not ceilings; challenger semantic pass catches edge cases |
| Reviewer skill rewrite breaks existing review patterns during transition | Medium | High | Phase B1 carefully; run both old and new reviewer in parallel on 3-5 tasks before switching |
| Consolidation-test tasks add planner complexity | Low | Low | Simple rule (≥2 implementation tasks → create one); architect backstop catches misses |
| CI/SAST setup delays reviewer simplification | Medium | Medium | D2 is independent; start early; reviewer keeps cognitive security scanning until D2 completes |
| P3 (verification method) produces boilerplate on process AC | Medium | Low | Monitor first 10 process AC; drop P3 if it's consistently unhelpful |
| Proof-sufficiency boundary is ambiguous without examples | Medium | Medium | B1 includes concrete boundary examples in the reviewer skill: what constitutes sufficient proof vs. over-proof |
