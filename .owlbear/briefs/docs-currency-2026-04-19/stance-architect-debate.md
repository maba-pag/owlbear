# Architect — Critic Debate Log

**Panelist:** Architect
**Brief:** draft-docs-currency-2026-04-19
**Cycles:** 5

---

## Cycle 1 — Index-derived scope circularity

**Critic challenge:**

> Your index-derived scope for doc-writer is circular. The index enumerates what exists, but doc-writer also needs to know about docs that SHOULD exist but DON'T. An index of existing files can't surface missing docs — that's the coverage gap problem (7 of 9 serve/* packages have no README). Your scope model handles what IS, not what SHOULD BE.

**Architect response:** ACCEPTED — refined.

Valid challenge. The concern surfaces a real gap: the index is a maintenance tool (what exists), not a completeness tool (what's missing). These are different concerns that belong to different components:

- **doc-writer per-task scope** = "docs affected by this task" — the index helps find relevant EXISTING docs, but doc-writer's checklist should also ask "did this task create a new package/module that needs docs?" That's a w-doc-update checklist item, not an index feature.
- **Missing-doc detection** = doc-audit's job. The audit compares the index against codebase signals (every `serve/*` with `pyproject.toml` should have a README, every agent in `share/agents/` should be covered). The audit finds gaps; the sweep creates the missing docs.

Position refined: index is scope for MAINTENANCE; audit is scope for GAP DETECTION. doc-writer's expanded checklist includes "did this task create something that needs new docs?"

---

## Cycle 2 — Diagram sync surface

**Critic challenge:**

> You put diagrams in `.owlbear/diagrams/` but `.owlbear/` is excluded from main-branch sync per `.github/copilot-instructions.md`. The 7 diagrams are product artifacts consumed by downstream projects — they need to be in the synced surface. Your own context says these are product deliverables.

**Architect response:** ACCEPTED — location changed.

Correct. `.owlbear/` is dev-only working space — research, decisions, kanban, scratch. Diagrams are product artifacts that consumers need. Revised location: `share/diagrams/`. The `share/` directory syncs to main, is already the home for shared product artifacts (agents, skills, instructions, prompts), and provides a single enumeration point.

Position hardened: `share/diagrams/` is the only correct location given the sync model.

---

## Cycle 3 — r-doc-standards vs w-doc-update boundary

**Critic challenge:**

> You're creating r-doc-standards as a new skill. But the existing w-doc-update already contains doc-writer's operational checklist. Won't r-doc-standards duplicate w-doc-update? Where exactly is the boundary? Can you name one rule that belongs in r-doc-standards that could NOT live in w-doc-update?

**Architect response:** REJECTED — stood firm.

Different file types serve different purposes per `h-agent-structure`:

- `w-doc-update` is a **workflow** skill — procedural steps (Step 0: claim, Step 1: assess, Step 2: clean, etc.). It tells the agent WHAT TO DO.
- `r-doc-standards` is a **rules** skill — declarative constraints (every serve/* README MUST have sections X, Y, Z; all file paths in docs MUST resolve). It tells the audit WHAT IS CORRECT.

Concrete example: "every serve/* package with a pyproject.toml MUST have a README containing Purpose, Installation, Configuration, and API/Usage sections." This is a citable audit rule — doc-audit needs it to generate findings. It does NOT belong in w-doc-update because w-doc-update is a process, not a standard.

The pattern is identical to how `r-project-standards` (rules) and `r-pipeline-protocol` (rules) exist alongside workflow skills that reference them. No duplication — different audiences, different invocation contexts.

---

## Cycle 4 — DR overhead for deletion

**Critic challenge:**

> Your deletion workflow routing through scribe/DR is heavyweight for what might be a frequent operation. If the sweep finds 10 orphaned docs, that's 10 individual DRs clogging the decisions queue. The user said quality over speed, but there's a difference between quality and bureaucratic ceremony. What if deletion was a simpler inline approval during the sweep?

**Architect response:** ACCEPTED — partially refined.

The per-task case stands: during normal operation, deletion proposals are rare (the system is maintaining, not remediating). One DR per deletion is appropriate overhead for an irreversible action.

For the sweep specifically: refined to allow **aggregated DRs**. The sweep executor can bundle multiple proposed deletions into a single DR with a table (file, reason, evidence). One user resolution covers the batch. This is a planner-level decomposition choice — the architecture supports both individual and aggregated DRs without modification.

The inline-approval alternative (doc-writer asks the user mid-task) breaks the agent's autonomous execution model. Agents don't block on user input mid-task — they flag and advance. The DR mechanism preserves this contract.

---

## Cycle 5 — Index freshness as SPOF

**Critic challenge:**

> You identified index freshness as a warning but didn't architect a mitigation. What happens concretely when the SessionStart hook fails? Does doc-writer refuse to run? Use a stale index? Skip index-dependent checks? "Fail loudly" is a hand-wave, not a design.

**Architect response:** ACCEPTED — refined with concrete behavior.

Specified: if the index script exits non-zero, the SessionStart hook chain fails, and the doc-writer session does not start. This is the existing hook behavior — `session-context.py` already runs as a SessionStart hook, and hook failures block session initialization.

Additionally: the index file includes a `generated` timestamp. doc-writer's Step 1 (assess) checks the timestamp. If the index is older than 1 hour, doc-writer regenerates it inline before proceeding. This is a staleness circuit-breaker, not a replacement for the hook — it catches the case where the hook ran but the session is long-lived.

The index script itself is idempotent and fast (filesystem walk + heading extraction, no network calls). Regeneration cost is negligible.

---

## Exit

After 5 cycles, all challenges addressed. Position hardened with refinements from cycles 1, 2, 4, and 5. Cycle 3 challenge rejected with evidence. Final stance published to `stance-architect.md`.
