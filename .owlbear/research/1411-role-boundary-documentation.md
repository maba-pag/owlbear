# Role Boundary Documentation — In Scope / Out of Scope for Pipeline Agent Skills

> **Owning task:** #1411 — C3: Role boundary documentation
> **Date:** 2026-05-09 **Status:** Complete

## 1. Context and Question

The pipeline review rethink (Brief #1403) restructured agent responsibilities across A2, A3, B1, and C1. The current skill files embed boundaries in scattered locations (Known Pitfalls, step descriptions, Critical Rules) but lack a single canonical "In Scope / Out of Scope" section. Agent definition files have `<boundaries>` sections with rationalization/response patterns, but those cover behavioral guardrails, not structured scope.

**Question:** What format and content should the "In Scope / Out of Scope" sections contain for each of the 7 pipeline agent skills, and do the post-rethink boundaries have any overlapping mandates or uncovered gaps?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | Brief #1403 (`draft-pipeline-review-rethink/brief.md`) | Internal | 1.0 — authoritative decision record |
| 2 | `w-task-decomposition/SKILL.md` | Internal | 0.9 — current planner skill |
| 3 | `w-arch-review/SKILL.md` | Internal | 0.9 — current architect skill |
| 4 | `w-tdd-red/SKILL.md` | Internal | 0.9 — current test-writer skill |
| 5 | `w-tdd-green/SKILL.md` | Internal | 0.9 — current builder skill |
| 6 | `w-code-review/SKILL.md` | Internal | 0.9 — current reviewer skill |
| 7 | `w-task-verification/SKILL.md` | Internal | 0.9 — current auditor skill |
| 8 | `w-doc-update/SKILL.md` | Internal | 0.9 — current doc-writer skill |
| 9 | `r-pipeline-protocol/SKILL.md` | Internal | 0.8 — trust model and evidence principles |
| 10 | 7 agent `.agent.md` `<boundaries>` sections | Internal | 0.7 — rationalization patterns |

## 3. Analysis

### 3.1 Current Boundary State

All 7 pipeline agent skills lack explicit "In Scope / Out of Scope" sections. Boundaries exist in three scattered forms:

1. **Status gates** — each agent processes exactly one input status
2. **Editability constraints** — hooks enforce file-type restrictions
3. **Responsibility limits** — embedded in step descriptions and pitfalls

### 3.2 Proposed Section Format

Place a `## Scope` section immediately after the skill description paragraph and before `## Step 0 — Setup`. This matches the brief's own format and avoids disrupting the step sequence.

```markdown
## Scope

### In Scope
- {responsibility 1}
- {responsibility 2}

### Out of Scope
- {non-responsibility 1} — {who handles it}
- {non-responsibility 2} — {who handles it}
```

Convention: each "Out of Scope" bullet names which agent DOES handle it. This prevents gaps.

### 3.3 Proposed Boundaries Per Agent

#### Planner (w-task-decomposition)

| In Scope | Out of Scope |
|----------|-------------|
| Break features into atomic tasks | Architecture evaluation — architect |
| Draft AC using `h-ac-quality` rules | AC quality validation — architect/challenger |
| Create consolidation-test tasks (≥2 impl siblings) | Implementation — builder |
| Assign priorities and dependency graphs | Test writing — test-writer |
| Route tasks to `backlog` (or `research` for researcher follow-ups) | Moving tasks to `todo` — architect |

#### Architect (w-arch-review)

| In Scope | Out of Scope |
|----------|-------------|
| Validate AC quality via challenger dispatch | AC drafting — planner |
| Evaluate architecture against `r-architecture-standards` | Writing source code — builder |
| Annotate test depth `(td:N)` per AC line | Writing tests — test-writer |
| Detect missing consolidation-test tasks (backstop) | Code review — reviewer |
| Approve `backlog → todo` | Running full test suite — auditor |
| Design diverge when ≥2 valid approaches | Documentation updates — doc-writer |

#### Test-writer (w-tdd-red)

| In Scope | Out of Scope |
|----------|-------------|
| Write failing tests from AC (RED phase) | Writing or editing source code — builder |
| Non-impl pass-through (tag-based) | AC quality validation — architect |
| Depth-zero pass-through (all `td:0`) | Code review — reviewer |
| Retry-cycle gap-fill (surgical fill from reviewer findings) | Architecture decisions — architect |
| Direct-to-review advance (test-only retry, all green) | Full-suite regression — auditor |

#### Builder (w-tdd-green)

| In Scope | Out of Scope |
|----------|-------------|
| Implement minimal code to pass tests (GREEN phase) | Writing tests — test-writer |
| Run quality-runner (scoped tests + lint + coverage) | Refactoring unrelated modules — separate task |
| Non-impl pass-through | AC quality validation — architect |
| Reject to test-writer (wrong interface) or architect (wrong AC) | Code review — reviewer |
| Commit source files before advancing | Documentation updates — doc-writer |

#### Reviewer (w-code-review)

| In Scope | Out of Scope |
|----------|-------------|
| 3-item checklist: AC→code, test→AC, proof sufficiency | Re-executing tests (reads builder evidence) — builder provides |
| Batch-all-findings before verdict | Fixing code — builder |
| Finding vs. opinion separation (Review Evidence + Observations) | Full-suite regression — auditor |
| Code-reader dispatch for `td:2` tasks | Architect quality scoring — auditor |
| Builder evidence consistency check | Documentation updates — doc-writer |
| PASS confirmation statement for auditor traceability | Security scanning — CI/SAST (D2) |

#### Doc-writer (w-doc-update)

| In Scope | Out of Scope |
|----------|-------------|
| README verification via convention mapping | Fixing runtime code — builder (reject to review) |
| External attribution updates | Writing tests — test-writer |
| Research doc linkage verification | Code review — reviewer |
| Deletion detection (orphaned references) | Full-suite regression — auditor |
| TODO markers for pre-existing issues | AC quality validation — architect |

#### Auditor (w-task-verification)

| In Scope | Out of Scope |
|----------|-------------|
| Full-suite regression test (cross-task, not scoped) | Re-verifying code-level detail — reviewer already did |
| AC spot-check (1–2 key items, not full map) | Fixing code — builder |
| Architect quality scoring (1–5) | Writing tests — test-writer |
| Confidence scoring with deduction rubric | Documentation updates — doc-writer |
| Research task verification (doc + follow-ups exist) | AC quality validation — architect |
| Commit kanban/decision files after archival | Security scanning — CI/SAST (D2) |

### 3.4 Overlap and Gap Analysis

| Boundary | Agent A | Agent B | Status |
|----------|---------|---------|--------|
| AC quality | Planner (drafter) | Architect (validator) | Clean — complementary |
| Test quality | Test-writer (creates) | Reviewer (alignment check) | Clean — distinct concerns |
| Evidence | Builder (produces) | Reviewer (validates) | Clean — trust-the-builder model |
| Regression | Reviewer (scoped evidence) | Auditor (full suite) | Clean — scope vs. breadth |
| Code-level detail | Reviewer (maps AC→code) | Auditor (spot-checks 1–2) | Clean — auditor trusts reviewer |
| Architect feedback | Architect (validates) | Auditor (scores) | Clean — prospective vs. retrospective |

**Gaps identified:** None. The pipeline covers: decomposition → validation → testing → implementation → review → documentation → verification.

**Security scanning gap (transitional):** Reviewer previously did cognitive security checks. Post-rethink, this is delegated to CI/SAST (D2). If D2 is not yet operational, the architect's Step 2.9 (security surface check) and reviewer's proof sufficiency are the interim coverage. This is documented in the brief; no new gap.

## 4. Recommendation

**Recommendation (confidence: .90):** Add `## Scope` sections with `### In Scope` / `### Out of Scope` subsections to all 7 pipeline agent skill files using the format and content in §3.3. Each "Out of Scope" item should name the responsible agent to prevent ambiguity.

Challenge: FALLBACK — codebase-only research, no external sources to challenge.

The format is minimal (8–12 bullets per agent), placed after the description paragraph and before Step 0. This adds ~15 lines per file, well within the skill file size budget.

## 5. Follow-up Tasks

One implementation task to add the sections to all 7 skill files. T1 (autonomous) — no user decision needed; this is documentation of existing responsibilities, not new behavior.
