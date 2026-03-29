# Confidence Scoring and Structured Options Rules for copilot-instructions.md

> **Owning task:** #127 — Add confidence scoring and structured options rules to copilot-instructions.md
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Agent-common.instructions.md has a confidence threshold table for reviewer/auditor verdicts (≥.90 and ≥.95 respectively), but no general rule requires agents to state confidence when deriving decisions from source material. The parent research (#125, `docs/research/askquestions-cleanup-scope.md` §3.4) identified this gap: the old "askQuestions liberally" guidance needs replacing with a tool-agnostic behavioral rule that preserves the valuable pattern of structured decision-making.

Question: What wording should go into `copilot-instructions.md` Process Habits, and how should it reference existing conventions?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | garrytan/gstack structured question protocol | .85 | "One issue per question; recommend + WHY + lettered options" — tool-agnostic decision pattern [already cited in `docs/research/gstack-agent-patterns.md`] |
| S2 | Anthropic prompting best practices (agentic research section) | .80 | "Track your confidence levels in your progress notes to improve calibration" — industry pattern for agent self-assessment |
| S3 | OwlBear decision-requests skill (SKILL.md) | .90 | Existing `(bp:)`/`(rec:)` annotation convention and confidence scoring — already tool-agnostic |
| S4 | OwlBear agent-common.instructions.md §Confidence thresholds | .95 | Verdict thresholds (reviewer ≥.90, auditor ≥.95) — must remain authority for pass/fail gates |
| S5 | OwlBear askquestions-cleanup-scope.md §3.4 | .95 | Gap analysis identifying the missing general confidence rule |

## 3. Analysis

### Current state

| Location | Confidence usage | Scope |
|----------|-----------------|-------|
| agent-common §Confidence thresholds | Reviewer ≥.90, Auditor ≥.95/.85 | Verdict gates only |
| decision-requests SKILL.md | `.0–1.0` scores + `(bp:)`/`(rec:)` tags | Decision request options only |
| Research workflow SKILL.md | `.0–1.0` on recommendations | Researcher output only |
| copilot-instructions.md Process Habits | No confidence rule exists | — |

### Gap

No general rule tells all agents to state confidence when making decisions derived from source material (e.g., choosing between implementation approaches, interpreting ambiguous AC, recommending patterns). The verdict thresholds are narrow — they only cover the reviewer PASS/FAIL and auditor ARCHIVE/REJECT decisions.

### Proposed wording

Two new bullet points in Process Habits (between "TDD by default" and "Deliverables are kanban tasks"):

1. **State confidence at decision points.** When deriving a decision from source material, state confidence as a score (0.0–1.0). Present structured options with `(bp:)` for best practice and `(rec:)` for recommendation per the decision-requests skill convention. Never assume — when multiple valid approaches exist, present them with trade-offs.
2. Cross-reference note: "Agent-specific verdict thresholds (reviewer ≥ .90, auditor ≥ .95) are defined in `agent-common.instructions.md` and remain the authority for pipeline gate decisions."

### Risk assessment

| Risk | Likelihood | Mitigation |
|------|:----------:|------------|
| Over-scoring: agents attach .95 to everything | Medium | The convention is self-correcting — reviewers/auditors verify confidence claims |
| Verbose output from forced options | Low | "When multiple valid approaches exist" scopes the trigger; trivial decisions skip it |
| Conflict with verdict thresholds | None | Explicit cross-reference preserves agent-common as authority |

## 4. Recommendation (.90 confidence)

Add the two bullets as described above. This is a low-risk, high-value improvement that:

- Fills the gap identified in parent research §3.4 [S5]
- Aligns with gstack's structured question protocol [S1] and Anthropic's confidence calibration guidance [S2]
- Reuses the existing `(bp:)`/`(rec:)` convention from decision-requests [S3]
- Explicitly defers to agent-common for verdict thresholds [S4]
- Does NOT reference askQuestions or any specific tool (per AC)

## 5. Follow-up Tasks

Task #127 itself is the implementation task. No additional follow-up tasks needed — the AC is concrete and the implementation approach is clear. The builder should:

1. Add the two bullets to Process Habits in `.github/copilot-instructions.md`
2. Verify no askQuestions reference is introduced
3. Verify the `(bp:)`/`(rec:)` reference points to the decision-requests skill
