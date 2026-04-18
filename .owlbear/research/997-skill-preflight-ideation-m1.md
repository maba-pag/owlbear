# Skill Pre-Flight for w-ideation M1

> **Owning task:** #997 — Add skill pre-flight to w-ideation M1
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

M3 landscape scan (via Explore subagent) covers codebase + ecosystem but fires AFTER M1 and M2 are locked. Existing conventions in skill/instruction files can contradict M1 assumptions — only surfacing at M3 when decisions are already committed, forcing loop-backs.

Concrete example from ideation #973: "every block requires a DR" was locked in M1. `r-pipeline-protocol` § Blocking Convention already distinguishes DR from AR and lists legitimate non-DR/AR blocks — a 30-second grep would have caught it.

**Question:** Where and how should a skill pre-flight step be added to M1, and what should it cover?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `share/skills/w-ideation/SKILL.md` | Codebase — current M1 definition | 1.0 |
| `share/skills/w-research/SKILL.md` § Step 1.5 | Codebase — existing pre-flight pattern | 0.9 |
| `share/skills/r-pipeline-protocol/SKILL.md` § Knowledge Pre-flight | Codebase — pre-flight precedent | 0.8 |
| `share/agents/ideator.agent.md` | Codebase — Mediator tool access | 0.8 |
| `share/skills/README.md` | Codebase — skill catalog structure | 0.7 |

## 3. Analysis

### Insertion Point Options

| Option | When | Pros | Cons |
|--------|------|------|------|
| **A: Between M1 step 5 and 6** | After narrowing, before Problem Statement | Topic clear → good keywords; catches conflicts before locking | Adds time to M1 |
| **B: Separate Step 0.5** | Before M1 conversation | Early check | Topic unknown — keyword matching impossible |
| **C: Between M1 and M2** | After Problem Statement, before Outcomes | Problem Statement provides precise keywords | Problem Statement already "locked" |

**Option A is the correct insertion point.** At step 5, the Mediator has narrowed from vague to specific — keywords are clear. The Problem Statement hasn't been written yet, so findings can still reshape it.

### Mediator Capability Check

The ideator agent already has: `textSearch`, `fileSearch`, `readFile`, `searchSubagent`. No new tooling needed — it can grep `share/skills/` and `share/instructions/` directly.

### Existing Pre-Flight Patterns

Three pre-flight patterns already exist in the codebase:

| Pattern | Location | Scope |
|---------|----------|-------|
| Knowledge Pre-flight | `r-pipeline-protocol` § 1 | Memory server query for past learnings |
| Resolved Decision Pre-flight | `r-pipeline-protocol` § 1 | Check task body for resolved DRs |
| Research Pre-Flight | `w-research` Step 1.5 | Check `.owlbear/research/` for existing docs |

The skill pre-flight follows the same convention: fast, read-only check that prevents wasted work downstream.

### Scope Control

The pre-flight must NOT become a mini-M3:
- Time budget: 1–2 minutes (2–3 grep calls + skim headlines)
- Targets: `share/skills/` and `share/instructions/` only (not full codebase)
- Depth: headlines + key sections, not full file reads
- Outcome: surface conflicts as probes, not resolve them

## 4. Recommendation (confidence: 0.88)

Insert a "Skill Pre-Flight" sub-step in M1 between steps 5 and 6 with this structure:

1. Extract 2–3 keywords from the narrowed problem.
2. Grep `share/skills/` and `share/instructions/` for those keywords.
3. Skim matched sections (headlines + key sentences).
4. If existing conventions contradict or inform assumptions → surface as M1 probes before tier confirmation.
5. If nothing relevant → continue normally.

Include keyword → skill mapping examples in the step definition. Mark explicitly as "not a substitute for M3 Explore."

Challenge: skipped — trivial skill-file modification, no architectural/security impact.

## 5. Follow-up Tasks

- **#998** (expected): Implement the skill pre-flight sub-step in `w-ideation/SKILL.md`
