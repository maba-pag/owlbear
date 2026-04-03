# Architect Decision-Request Verification Gate

> **Owning task:** #461 — Add decision-request verification to architect backlog gate
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

The parent research (#385, `docs/research/mandatory-user-decision-gate.md`) established a 3-tier classification for research outcomes and identified gap G3: the architect never verifies whether a research-driven task has an approved decision request (DR) before advancing it past backlog. This research details the implementation approach for closing that gap.

**Key questions:** (1) How should the architect detect research-driven tasks? (2) How does the architect trace to the approved DR? (3) Where in the arch-review workflow should the check go? (4) What edge cases must be handled?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | CrewAI Task Guardrails | docs.crewai.com/concepts/tasks | .80 |
| 2 | AutoGen Human-in-the-Loop | microsoft.github.io/autogen/stable/.../human-in-the-loop.html | .75 |
| 3 | GitHub Actions Environment Protection | docs.github.com/en/actions/.../managing-environments-for-deployment | .70 |
| 4 | OwlBear mandatory-user-decision-gate research | docs/research/mandatory-user-decision-gate.md | 1.0 |
| 5 | OwlBear decision-requests skill | skills/decision-requests/SKILL.md | 1.0 |
| 6 | OwlBear arch-review skill | skills/arch-review/SKILL.md | 1.0 |

## 3. Analysis

### 3a. Detection mechanism — How does the architect know a task is research-driven?

| Approach | Detection method | Pros | Cons |
|----------|-----------------|------|------|
| **A: Tag-based** | Task tagged `research` | Simple, deterministic | Follow-up tasks typically aren't tagged `research` |
| **B: Body-reference** | Body mentions `docs/research/*.md` | Catches follow-ups that reference the research doc | Requires body string scanning |
| **C: Both (rec:)** | Tag OR body reference | Most reliable, catches all cases | Slightly more work (negligible) |

Follow-up tasks from #385 (e.g., #459–#462) reference the research doc in their body but aren't tagged `research`. Option C catches both direct research tasks and their follow-ups. The arch-review skill already reads the task body (Step 1.3), so body scanning adds no extra step.

### 3b. Traceability — How does the architect find the approved DR?

| Approach | Chain | Pros | Cons |
|----------|-------|------|------|
| **A: Research doc → owning task → DR** | Body → research doc → `Owning task: #N` → `docs/decisions/resolved/N-*.md` | Always works, no new metadata | 3-hop lookup |
| **B: Explicit DR reference in task body (rec:)** | Body → `DR: docs/decisions/resolved/N-slug.md` | 1-hop lookup, simplest | Requires researcher to include DR ref (change in #460) |
| **C: Scan resolved/ for research task ID** | Extract owning task ID from research doc → glob `docs/decisions/resolved/{id}-*` | Works without metadata changes | 2-hop, glob can be slow with many files |

**Recommendation (.85):** Design for approach A (always works), but instruct the researcher (#460) to include an explicit DR reference (approach B) as an optimization. The architect tries B first (direct reference), falls back to A.

### 3c. T3 determination — How does the architect know if the outcome is T3?

The deterministic triggers from the parent research (#385, §4) apply. A research outcome is T3 if ANY trigger is true: adds capability, changes architecture, modifies agent/skill/pipeline behavior, alters security policy, changes user-facing behavior, or proposes deprecation/removal.

The architect already evaluates many of these in Step 3 (premise challenge, single responsibility, KISS/YAGNI). Adding T3 trigger evaluation requires reading the research doc (already done in Step 1.3) and checking if the proposed changes match any T3 trigger. This maps naturally to CrewAI's guardrail pattern (S1): a prerequisite validation that must pass before the task proceeds.

### 3d. Integration point — Where in the workflow?

| Option | Location | Pros | Cons |
|--------|----------|------|------|
| **A: New Step 1b (gate check)** | After Step 1 (read task), before Step 2 (analyze codebase) | Short-circuits early, saves analysis time | Adds a step |
| **B: New criterion in Step 3** | Evaluation item #12 | Fits existing structure | Full analysis runs even if DR is missing |
| **C: Part of Step 4 verdict** | Block verdict condition | No structural change | Late detection, wasted work |

**Recommendation (.80):** Option A. If an approved DR is missing for a T3 outcome, there's no point running the full architecture evaluation. This follows AutoGen's `HandoffTermination` pattern (S2): early termination when a prerequisite condition is unmet. GitHub Actions (S3) similarly blocks deployment before any work runs if required reviewers haven't approved.

## 4. Recommendation (.85 confidence)

Add a **Step 1b — Decision-request verification** to the arch-review skill, between Step 1 and Step 2:

1. Check if task body references `docs/research/*.md` or task is tagged `research`
2. If yes, read the research doc; check if outcome involves T3 triggers
3. If T3: look for approved DR in `docs/decisions/resolved/` matching the research task ID
4. If no approved DR found: Block to ideation — "T3 research outcome requires approved decision request"
5. If approved DR found: Note it in the Architecture Review section and proceed

Also add to `agents/architect.agent.md`:
- Red flag: "You are approving a task derived from research that introduces a new capability, arch change, or process change — but no approved decision request exists"
- Architecture Review template: add "DR verification: {result}" line

**Risk:** Additional lookup step per research-driven task. Mitigated by the early short-circuit design — non-research tasks skip entirely.

**No additional follow-up tasks needed** — #461's existing AC already covers these changes precisely.

## 5. Implementation Checklist (maps to AC)

| AC Item | File to change | What to add |
|---------|---------------|-------------|
| Architect checks for approved DR | `skills/arch-review/SKILL.md` | New Step 1b with detection + traceability procedure |
| T3-origin tasks without DR rejected | `skills/arch-review/SKILL.md` | Step 1b Block path when T3 + no approved DR |
| Red flag added | `agents/architect.agent.md` | New bullet in red flags section |
| Review section notes DR result | `agents/architect.agent.md` | Add DR verification line to Architecture Review template |
