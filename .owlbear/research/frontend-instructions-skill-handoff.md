# Frontend Instructions → Skill Handoff

> **Owning task:** #937 — Refactor frontend.instructions.md into lean guardrails plus skill handoff
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #937 asks whether `frontend.instructions.md` should be refactored to add a handoff to the newly-created `frontend-design` skill (#934, archived). The question: what stays in the always-on instruction, what gets delegated to the skill, and what handoff pattern should be used?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `.github/instructions/frontend.instructions.md` | 1.0 | Current file: 776 tokens, 55 lines covering design-system, a11y, component structure, responsive, testing [S1] |
| S2 | `.github/skills/frontend-design/SKILL.md` + 7 references | 1.0 | Completed skill with deep design guidance, universal blockers, and adapted references [S2] |
| S3 | `docs/research/instruction-token-audit.md` | .90 | Token budget analysis — frontend.instructions.md at 776 tokens is already lean [S3] |
| S4 | VS Code custom instructions docs | .95 | "Use instructions for project-wide standards; use skills for specialized capabilities loaded on-demand" [S4] |
| S5 | VS Code agent skills docs | .95 | Skills use progressive loading — discovery from name/description, then body, then resources — keeping context efficient [S5] |
| S6 | Existing OwlBear handoff patterns | .90 | `python.instructions.md` → `pytest-and-linting` skill; `research-docs.instructions.md` → `research-workflow` skill; `agent-common.instructions.md` → `kanban-md` skill [S6] |
| S7 | `docs/research/impeccable-design-skills.md` | .85 | Parent research recommending lean instructions + deep skill split [S7] |

## 3. Analysis

### 3.1 Content Overlap Assessment

| Section in instructions | Overlaps with skill? | Keep in instructions? | Rationale |
|------------------------|:--------------------:|:---------------------:|-----------|
| Design system (PDS) | No | Yes | Project-specific policy — not design expertise [S1, S4] |
| Accessibility minimums | Partial (universal blockers in skill) | Yes | Short rule set vs. deep reference — no duplication risk [S1, S2] |
| Component structure | No | Yes | Project convention, not design knowledge [S1, S4] |
| Responsive design | Partial (responsive-design.md reference) | Yes | 4-bullet guardrails vs. deep reference — complementary, not redundant [S1, S2] |
| Testing | No | Yes | Project testing policy [S1, S4] |

**Conclusion:** No content should be removed from `frontend.instructions.md`. The file is already at guardrail level (776 tokens) [S3]. The a11y and responsive sections overlap with the skill only at the surface — the instructions set minimums, the skill provides deep guidance. Removing them would lose the always-on enforcement [S4, S5].

### 3.2 Handoff Pattern Selection

| Pattern | Example in OwlBear | Tokens | Verdict |
|---------|-------------------|--------|---------|
| Short name only | `see the research-workflow skill` | ~8 | Sufficient for a file already scoped by applyTo [S6] |
| Name + full path | `Read the decision-requests skill (.github/skills/decision-requests/SKILL.md)` | ~16 | Overkill — the skill auto-loads by relevance [S5, S6] |
| Name + purpose | `see the pytest-and-linting skill for correct commands` | ~12 | Best fit — names the skill and explains what it covers [S6] |

**Recommendation:** Use the "name + purpose" pattern. It tells Copilot both where to look and what the skill covers, matching the `python.instructions.md` precedent [S6].

### 3.3 Placement

The handoff should go near the top of the file (after the intro paragraph) rather than at the bottom, because skills loaded by relevance need the handoff visible in context. The instruction-token-audit found that information in the middle of long contexts is systematically ignored [S3]. A top-placed handoff also follows the principle that the most important routing information comes first.

## 4. Recommendation (.92 confidence)

Add a 2–3 line "Design guidance" section after the intro paragraph in `frontend.instructions.md`, using the "name + purpose" handoff pattern:

> For deeper design guidance — typography, color, spatial layout, motion, interaction, responsive patterns, and UX writing — use the `frontend-design` skill.

No content removal needed. The file stays under 800 tokens. The `applyTo` scope is unchanged [S1, S4, S5, S6, S7].

**Risk:** The a11y universal blockers appear in both the instruction file and the skill. This is intentional — the instruction set is the always-on minimum, and the skill provides expanded context. No de-duplication needed because they serve different purposes (enforcement vs. guidance) [S2, S4].

## 5. Follow-up Tasks

Task #937 is already scoped with clear AC. No additional follow-up tasks are needed — the existing AC covers the exact change recommended above.
