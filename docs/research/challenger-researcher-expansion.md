# Challenger Expansion to Researcher Agent

> **Owning task:** #469 — Expand Challenger to researcher agent (Phase 2)
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

The Challenger subagent was designed as an adversarial pre-decision review agent (#465 research). Phase 1 integrated it into the architect's arch-review workflow (#467 agent, #468 skill integration). Phase 2 extends the same pattern to the researcher agent, challenging recommendations before they are committed to the research document.

**Question:** How should the Challenger integrate into the research-workflow skill, what are the trigger conditions, and how does the I/O contract adapt?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | docs/research/challenger-subagent-design.md S3h — expansion path | .95 |
| S2 | skills/arch-review/SKILL.md Step 3.5 — implemented precedent (#468) | .95 |
| S3 | Du et al. 2023 (arxiv.org/abs/2305.14325) — multiagent debate | .85 |
| S4 | Liang et al. 2024 (arxiv.org/abs/2305.19118) — DoT in self-reflection | .85 |
| S5 | agents/challenger.agent.md — implemented I/O contract | .90 |

## 3. Analysis

### 3a. Integration point

The research-workflow skill has: Step 3 (Analyze/compare → forms recommendation) → Step 4 (Write research doc → commits recommendation). The challenge belongs between them as **Step 3.5**, mirroring the arch-review pattern exactly (S2). The researcher forms the recommendation during Step 3 but hasn't committed it to the document until Step 4 — this is the pre-commitment intervention point identified by Liang et al. (S4).

### 3b. Trigger conditions

| Condition | Challenge? | Rationale |
|-----------|-----------|-----------|
| Research produces recommendation with confidence score | **Mandatory** | Highest value — wrong recommendations misdirect downstream tasks (S1) |
| Pure information-gathering (no recommendation) | Skip | No verdict to challenge |
| Trivial/N/A research (rename, config tweak) | Skip | Cost exceeds value |

### 3c. I/O contract mapping

The Challenger's 6-field generic input maps to the researcher context:

| Challenger field | Researcher provides |
|---|---|
| task_id | Research task ID |
| proposed_verdict | Proposed recommendation text + confidence score |
| reasoning | Step 3 analysis summary (trade-off matrix conclusions) |
| ac_lines | Research question/scope being answered |
| codebase_evidence | Codebase search results and existing patterns found |
| research_doc | Path to research notes or draft (optional at this stage) |

Output contract remains unchanged — the Challenger's 6-section output (Challenges, Blind Spots, Alternative Angles, Risk Assessment, Confidence in Original, Recommendation) applies directly.

### 3d. Integration protocol comparison

| Challenger output | Architect (S2) | Researcher (proposed) |
|---|---|---|
| proceed, confidence ≥ .80 | Continue with APPROVE | Continue with recommendation. Note in doc §4. |
| reconsider OR < .80 | Revise AC or change verdict | Revise recommendation, adjust confidence, or justify override |
| block | Move task to ideation | Revisit research scope. Must rebut if proceeding. |

### 3e. Changes required

| File | Change | Impact |
|------|--------|--------|
| researcher.agent.md | `agents: [Explore]` → `agents: [Explore, challenger]` | Frontmatter only |
| research-workflow SKILL.md | Add Step 3.5 section (trigger, prompt, protocol, fallback) | ~30 lines new content |

## 4. Recommendation (.85 confidence)

Mirror the arch-review Step 3.5 pattern exactly. The arch-review integration (S2) establishes a proven template; applying the same structure to the researcher minimizes design risk. The researcher keeps final authority — the Challenger advises only.

**Risk:** Additional Opus 4.6 call per recommendation-bearing research task (~60% of research tasks). Mitigated by: one-shot interaction (bounded cost), skip trigger for trivial/info-only tasks. Same cost profile the architect already accepts.

**Alternative considered — optional-only integration (.65 confidence):** Making the challenge optional defeats the purpose. Self-reflection bias (S4) means researchers will skip the challenge when they're most confident — exactly when challenges are most valuable. Mandatory trigger for recommendation-bearing tasks, skip for info-only tasks.

## 5. Follow-up Tasks

T3 classification: modifies agent instructions and skill pipeline behavior. Blocking decision request created at `docs/decisions/pending/469-challenger-researcher-expansion.md`.
