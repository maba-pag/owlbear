---
id: 939
title: 'P3-03: Docs — engine surface + future-surface contract + hello-world walkthrough'
status: archived
priority: medium
created: 2026-04-17T19:59:26.751674+00:00
updated: 2026-04-19T16:16:21.810139+00:00
tags:
- cockpit
- docs
- phase-3
- type:docs
parent: 920
depends_on:
- 937
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Document the cockpit's engine surface (allowlist), extensibility contract, and a hello-world second-surface walkthrough (O4a, O7).

## Acceptance Criteria

- [ ] Documentation at `serve/cockpit/README.md`
- [ ] Lists all engine methods used by the cockpit adapter (the allowlist) and explains why others are excluded (D12)
- [ ] Documents the shell-to-surface contract: route registration, component structure, optional nav-rail entry, adapter usage pattern
- [ ] Hello-world walkthrough: step-by-step to add a second surface (route + component + nav icon) with no shell layout changes required
- [ ] Documents Work Sessions model: derived states, activity.jsonl event mapping, filter vocabulary
- [ ] Documents `actor: "cockpit"` audit trail convention

## Files

- `serve/cockpit/README.md`
[[2026-04-19]]

## Research

- Research doc: .owlbear/research/939-cockpit-docs-engine-surface.md
- Sources: 9 studied, 7 high-relevance (all codebase-internal)
- Recommendation: Progressive-disclosure README structure (confidence: 0.92)
- Follow-up tasks created: none (task itself is the deliverable — moves to backlog for doc writing)
- Decision requests: none

## Challenge Results

- Challenger: SKIPPED — trivial synthesis task (no design choices or trade-offs)
- Key findings: adapter exposes 5 read-only methods; mutations bypass adapter; shell contract is 3-touchpoint (route + nav button + component); sessions have 6 derived states with 4 filter values; actor="cockpit" set at engine init
- Tier: T1 (autonomous)
[[2026-04-19]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single README deliverable for cockpit docs |
| Interface clarity | PASS | One output file (`serve/cockpit/README.md`), AC sections clearly scoped |
| Dependency correctness | PASS | Depends on #937 (archived/done); no blockers |
| Module layering | N/A | Documentation task, no code |
| TDD compliance | N/A | `type:docs` — pass-through tag present |
| KISS/YAGNI | PASS | Minimal scope: document what exists |
| Premise challenge | PASS | Cockpit lacks any README; docs needed |
| Pattern consistency | PASS | README follows progressive-disclosure structure |
| Security surface | N/A | No code changes |
| Single domain | PASS | Cockpit domain only |

### Challenge Results

- Challenger: **reconsider** (confidence 0.55)
- Architect response: **accepted C1+C2, overridden C3+C4** — AC is verifiable as-is; research doc errors noted below as builder guidance

### Research Doc Corrections (doc-writer must verify from source)

**1. Incomplete engine method inventory (C1):** Research doc lists 11 engine methods but `KanbanEngine` exposes ~16 public members. Missing from the table: `claim_task()` (partner of `release_task`), `refresh_config()`, `agent_name` property, `revision` property. AC2 requires "explains why others are excluded" — doc-writer must audit `serve/kanban/src/owlbear_kanban/engine.py` directly for the complete public API, not rely solely on research doc table.

**2. sweep-release session error (C2):** Research doc Section 3.3 claims `released` state derives from "release/sweep-release action." This is wrong. Code at `engine.py:130-134` shows `sweep-release` resets tracking and `continue`s without creating a `WorkSession`. Only `release` produces a visible session. Doc-writer must correct this in the Work Sessions section.

**3. Adapter boundary nuance (C3, minor):** Mutation routes use adapter selectively — `move_task` calls `adapter.valid_transitions()` for pre-check validation. The boundary is "adapter wraps read endpoints; mutations orchestrate engine calls directly but may use adapter for validation reads." Not a clean bypass.

### Verdict: APPROVE

### Action Taken: Advanced to todo with research doc correction notes for doc-writer

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

**Files changed:** `serve/cockpit/README.md` (created — 1 file, docs only)

**Test results:** 685 passed, 6 failed (pre-existing failures unrelated to this task — stats output schema, knowledge-mcp search, scopes=None mismatch; all visible in session context before work began)

**Lint status:** ruff clean — all checks passed

**Evidence summary:**

- AC1 ✓ `serve/cockpit/README.md` created
- AC2 ✓ Engine allowlist table: 5 adapter methods + 3 direct mutation methods + 7 excluded methods with reasons (verified against `engine.py` public API including `claim_task`, `release_task`, `refresh_config`, `agent_name`, `revision` per architect correction C1)
- AC3 ✓ Shell-to-surface contract documented: 3 touchpoints (route + nav button + component), grid-area table from Shell.css
- AC4 ✓ Hello-world walkthrough: 4 steps, creates `HelloSurface.tsx`, registers route + nav button in `Shell.tsx`
- AC5 ✓ Work Sessions model: 6 derived states, 4 filter values, `activity.jsonl` field mapping; `sweep-release` correction applied per architect C2 (does not produce WorkSession)
- AC6 ✓ `actor: "cockpit"` convention documented with `agent_name="cockpit"` init context

**Architect corrections applied:**

- C1: Audited `engine.py` directly — added `claim_task`, `release_task`, `refresh_config`, `agent_name`, `revision` to excluded table with reasons
- C2: `sweep-release` noted as NOT producing a WorkSession; only user `release` action produces `released` state
- C3: `move_task` mutation uses `adapter.valid_transitions()` for pre-check — documented accurately (not a "clean bypass")
[[2026-04-19]]

## Review Evidence

### Source Changes

Builder claims 1 file changed: `serve/cockpit/README.md`. However, `serve/cockpit/web/src/Shell.tsx` already contains `<Route path="/hello" element={<div>hello</div>} />` at line 40 — a placeholder that predates or was introduced alongside this task.

### Tests / Lint

No tests applicable (`type:docs`). Lint not applicable to markdown.

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: `serve/cockpit/README.md` exists | File present, 280+ lines | PASS |
| AC2: Engine allowlist + exclusions | `adapter.py __all__` has 5 methods matching table; excluded table covers `create_task`, `claim_task`, `start_work`/`end_work`, `sweep`, `refresh_config`, `agent_name`, `revision` — all confirmed in `engine.py` | PASS |
| AC3: Shell-to-surface contract | 3-touchpoint structure accurate per `Shell.tsx`; grid areas table includes `contextual` as a grid area — but `.shell__contextual` in `Shell.css` has only `display: none` with **no `grid-area` CSS property**. The table title "Grid areas (from Shell.css)" is factually incorrect for this entry | PARTIAL |
| AC4: Hello-world walkthrough | Walkthrough provided; **`/hello` route already exists in `Shell.tsx:40`** (`<Route path="/hello" element={<div>hello</div>} />`). The guide instructs users to ADD this route and says "No other files need to change" — it does not acknowledge the conflicting placeholder. A developer following the guide verbatim will produce a duplicate route. | FAIL |
| AC5: Work Sessions model | 6 states, 4 filter values, `activity.jsonl` field mapping all verified against `engine.py`; `sweep-release` correction from architect C2 applied correctly | PASS |
| AC6: `actor: "cockpit"` convention | Documented with init context + `agent_name`/`revision` code example | PASS |

### Deductions

| Finding | Severity | Deduction |
|---------|----------|-----------|
| AC4: Walkthrough path `/hello` conflicts with existing `Shell.tsx:40` placeholder route; guide says "No other files need to change" | High — misleading for consumers | −0.20 |
| AC3: `contextual` listed in "Grid areas (from Shell.css)" table but has no `grid-area` CSS property | Low — factual inaccuracy | −0.05 |

### Verdict

Confidence: 1.00 − 0.20 − 0.05 = **0.75 → FAIL**

### Required Fixes (doc-writer)

1. **AC4 — `/hello` path conflict**: The walkthrough example must either (a) use a path name that does NOT already exist in `Shell.tsx` (e.g. `/hello-surface` or `/analytics`), or (b) explicitly acknowledge that the placeholder `<Route path="/hello" ...>` at `Shell.tsx:40` should be replaced. Update the note "No other files need to change" accordingly.

2. **AC3 — Grid areas table**: Remove `contextual` from the "Grid areas (from Shell.css)" table, or rename the table to reflect it includes non-grid reserved regions. The `contextual` div has no `grid-area` assignment in Shell.css.
[[2026-04-19]]

## Builder Notes

**Files changed:** `serve/cockpit/README.md` (2 targeted edits — docs only, review fixes)

**Test results:** N/A — `type:docs`, no tests applicable

**Lint status:** N/A — markdown file

**Evidence summary:**

- AC3 fix ✓ Removed `contextual` row from "Grid areas (from Shell.css)" table — `.shell__contextual` has `display: none` but no `grid-area` CSS property; table now accurately reflects only true CSS grid areas
- AC4 fix ✓ Changed walkthrough route path from `/hello` to `/hello-surface` (avoids conflict with existing `Shell.tsx:40` placeholder `<Route path="/hello" element={<div>hello</div>} />`); updated Step 4 URL to `http://127.0.0.1:8420/hello-surface`

**Reviewer deductions addressed:**

- −0.20 (AC4 duplicate route) → resolved by using distinct `/hello-surface` path
- −0.05 (AC3 contextual non-grid entry) → resolved by removing the row
[[2026-04-19]]

## Review Evidence

### Source Changes

`serve/cockpit/README.md` (1 file, docs only). Verified via source reads — no code changed.

### Tests / Lint

`type:docs` — no tests applicable. Lint not applicable to markdown.

### Prior Review Fixes — Verification

| Finding (Cycle 1) | Fix Applied | Evidence | Status |
|-------------------|-------------|----------|--------|
| AC4 −0.20: `/hello` path conflict with `Shell.tsx:40` placeholder | Changed walkthrough route to `/hello-surface` | README Step 2 uses `path="/hello-surface"`; Step 4 URL `http://127.0.0.1:8420/hello-surface`. `Shell.tsx:40` still has `/hello` — no conflict | RESOLVED ✓ |
| AC3 −0.05: `contextual` in grid-areas table had no `grid-area` CSS property | Row removed from table | README grid areas table now has 4 entries only: `status-bar`, `nav-rail`, `workspace`, `sidecar`. Confirmed against `Shell.css` lines 15/25/35/40 — all 4 have `grid-area` assignments. `.shell__contextual` (line 45) confirmed to have no `grid-area` | RESOLVED ✓ |

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: `serve/cockpit/README.md` exists | File present, ~280 lines | PASS |
| AC2: Engine allowlist + exclusions with reasons | All 16 public members of `engine.py` accounted for: 5 via adapter, 3 new direct mutations (`move_task`, `edit_task`, `release_task`), `show_task` dual-listed, 7 excluded entries covering 8 methods/properties. C1 corrections (claim_task, refresh_config, agent_name, revision) present in excluded table | PASS |
| AC3: Shell-to-surface contract | 3-touchpoint structure accurate; grid-areas table fixed (4 areas only, matches Shell.css); `contextual` removed | PASS |
| AC4: Hello-world walkthrough | Uses `/hello-surface` path — no conflict with existing `Shell.tsx:40` `/hello` placeholder; 4 steps complete and accurate | PASS |
| AC5: Work Sessions model | 6 derived states, 4 filter values, activity.jsonl field mapping, sweep-release correction per architect C2 — all verified against engine.py | PASS |
| AC6: `actor: "cockpit"` convention | KanbanEngine init with `agent_name="cockpit"` documented; code example shows `engine.agent_name` and `engine.revision` | PASS |

### Deductions

None.

### Builder Process

2 cycles. Cycle 2 made two targeted fixes addressing both prior deductions precisely. CLEAN.

### Verdict

Confidence: 1.00 − 0.00 = **0.98 → PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure docs task — `serve/cockpit/README.md` created. `.github/copilot-instructions.md` §4 endpoint table already accurate and complete; no update required. |
| 2 | Module docstrings | No | N/A | No Python files created or modified (builder confirmed `README.md` only). |
| 3 | External attribution | No | N/A | All 7 high-relevance research sources were codebase-internal per research notes. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/939-cockpit-docs-engine-surface.md` exists and is linked in task body. No follow-up tasks required (task itself was the deliverable). |

### Files Updated

None — no docs changes required. README is the task deliverable; already committed by builder.

### Scratch Files

No `.owlbear/scratch/939-*` files found — nothing to clean.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Documentation at `serve/cockpit/README.md` | File present, ~280 lines | PASS |
| AC2: Engine allowlist + exclusion reasons | 5 adapter methods, 3 direct mutations, 7 excluded with reasons; reviewer confirmed all 16 `engine.py` public members accounted for (incl. C1 corrections) | PASS |
| AC3: Shell-to-surface contract | 3-touchpoint structure; grid areas table has 4 entries (status-bar, nav-rail, workspace, sidecar) matching Shell.css; `contextual` correctly excluded (no grid-area CSS property confirmed) | PASS |
| AC4: Hello-world walkthrough | 4 steps using `/hello-surface` path; no conflict with existing Shell.tsx:40 `/hello` placeholder (spot-checked — no `/hello-surface` route exists) | PASS |
| AC5: Work Sessions model | 6 derived states, 4 filter values, activity.jsonl field mapping; sweep-release correction applied per architect C2 | PASS |
| AC6: `actor: "cockpit"` convention | Documented with `agent_name="cockpit"` init and code example | PASS |

### Test Results

- pytest: 685 passed, 6 failed (all pre-existing mcp-knowledge failures outside task scope)
- ruff: clean

### Architect Quality: 4/5

Specific, verifiable AC. Proactive research doc corrections (C1–C3) improved doc accuracy. Minor gap: `/hello` route conflict caught by reviewer not anticipated in AC, but route path was an implementation detail.

### Deduction Breakdown

- AC lines without evidence: 0 → −0.00
- Lint violations: none → −0.00
- AC quality ≤ 3: no (4/5) → −0.00
- Missing reviewer evidence: no (detailed, 2-cycle PASS at 0.98) → −0.00
- Full-suite failures in task scope: 0 → −0.00

### Confidence: 1.00

### Action: archive
