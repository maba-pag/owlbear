# Fix ideator/w-ideation askQuestions instruction conflict

> **Owning task:** #996 — Fix ideator/w-ideation askQuestions instruction conflict
> **Date:** 2026-04-18 **Status:** Complete (validation pass)

## 1. Context and Question

The ideator agent's `critical_rules` originally scoped `askQuestions` to "decision points" (tier selection, approach choice, panelist veto, Brief approval, moment transitions). The `w-ideation` skill described M1 as natural investigative dialogue with no `askQuestions` annotation on probe steps. This allowed the model to end M1 turns with prose questions instead of `askQuestions`, causing silent stalls.

Surfaced during ideation session for #973. See `.owlbear/briefs/draft-blocked-task-dr-enforcement/context.md`.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `share/agents/ideator.agent.md` (owlbear-dev, current) | 1.0 — primary file with critical_rules |
| 2 | `share/skills/w-ideation/SKILL.md` (owlbear-dev, current) | 1.0 — primary file with M1 protocol |
| 3 | `share/agents/ideator.agent.md` (owlbear/main, pre-fix) | 0.9 — shows old "askQuestions for decisions" wording |
| 4 | `share/skills/w-ideation/SKILL.md` (owlbear/main, pre-fix) | 0.9 — shows old M1 without per-step annotations |
| 5 | User memory entry "askQuestions Best Practice" | 0.8 — documents the rule and root cause |

## 3. Analysis

This is a **validation pass** — the fix described in the AC has already been applied on the `dev` branch.

### AC Verification

| AC | Status | Evidence |
|----|--------|----------|
| `ideator.agent.md` has unambiguous "askQuestions is the only way to end a user-facing turn" clause | ✅ Met | Line ~40: "askQuestions ends every user-facing turn. Every reply that requires a user response — including investigative M1–M3 probes..." |
| `w-ideation` Step 1 has explicit "every probe ends with askQuestions" | ✅ Met | Turn-ending rule paragraph + per-step annotations (steps 2–5 each annotated `→ end with askQuestions (freeform)`) |
| Worked `askQuestions` example with `allowFreeformInput: true` | ✅ Met | Code block in w-ideation Step 1 showing `vscode_askQuestions` with `allowFreeformInput: true` |
| No remaining conflict between the two documents | ✅ Met | Agent says "M1–M3 probes"; skill annotates M1 probes explicitly. Aligned. |

### Residual gap (minor)

M2 (Outcomes) steps 2–3 are user-facing probes ("Ask: ...") but lack the per-step `→ end with askQuestions (freeform)` annotation that M1 now has. The agent-level critical rule covers this broadly ("including investigative M1–M3 probes"), making the risk low. M2 probes are also more structured than M1 (specific questions, not open exploration).

**Assessment:** Not worth a separate task. The agent-level rule provides sufficient coverage. If M2 stalls are observed in practice, annotate M2 steps at that time.

## 4. Recommendation

**No further implementation needed.** All four AC are met on `dev`. The fix has not yet been synced to `main` via the `sync-to-main` workflow.

Confidence: **0.95** — high certainty the fix is complete. The 0.05 gap is the M2 annotation consistency, which is covered by the agent-level rule.

Challenge: FALLBACK — validation pass, no recommendation to challenge.

## 5. Follow-up Tasks

None created. All AC are met. The M2 annotation gap is documented above but does not warrant a separate task per YAGNI.
