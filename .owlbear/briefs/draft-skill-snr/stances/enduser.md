# End-User Stance — Interaction Design for SNR Tools

## User Experience Position

The core UX tension is: sufficient approval granularity for confident control vs. death-by-a-thousand-clicks across 80 files. The broad audit is the funnel; the deep-dive is the scalpel. The interaction model must respect that the user thinks in file-sections (their mental model) not noise-categories (the tool's taxonomy).

## Usability Reasoning

### Q1: Deep-dive interaction model — Single structured proposal per file

**Recommendation: One proposal document per file, organized by section, reviewed top-to-bottom.**

The proposal has two clearly-labeled regions presented together (not as separate "passes"):

1. **Structural changes** (top): merges, splits, moves to other files, full-section deletions. Shown as a summary list with one-line rationale per change.
2. **Compression edits** (body): per-section before/after diffs of surviving sections.

The user reviews this as one document. Structural changes first because they're highest-impact and affect what follows. Then compression section-by-section.

Why not full-file before/after (Option A): At 540 lines, the user must visually diff an entire file. That's work the tool should do for them. Unacceptable cognitive load.

Why not pure diff (Option C): Diffs without surrounding context make it impossible to judge whether a cut is safe — the user needs to see what *stays* to evaluate what *goes*.

Why not two separate passes: Introduces a mode-switch between "structural thinking" and "compression thinking." One proposal, two regions, one read-through.

For short files (<80 lines): offer full-file before/after as an alternative mode (user's choice, not forced).

### Q2: Cognitive load in broad audit — Findings during, ranking at end

The broad audit produces two distinct output types:
- **Findings** (actionable now): one-at-a-time approval loop. Keep the existing pattern — it works.
- **Priority ranking** (actionable later): end-of-run deliverable as a sorted table.

The ranking MUST be end-of-run, not progressive. Relative signal-density scoring against peers requires the complete cohort. A ranking at file 5/80 is noise — it creates false confidence around immature numbers that will shift as more files are evaluated.

During the audit, the prompt may maintain a running "attention flags" list (unranked, just noted), but the formal ranked deliverable appears only after the full scan.

Findings and ranking are never interleaved within a single file's evaluation.

### Q3: Session continuity — Deep-dive is independent; user bridges manually

**The deep-dive tool does NOT receive broad-audit findings automatically.**

Rationale: The broad audit is an ecosystem-level indicator. The deep-dive is a sentence-level evaluator. If audit findings are injected before the deep-dive forms its own view, anchoring is inevitable regardless of how they're labeled ("provisional," "observations," etc.). Renaming doesn't neutralize priming.

The deep-dive forms its own assessment independently. The user — who has already seen the audit — can optionally provide context ("the audit flagged repetition in §3") if they want to direct attention. This preserves tool independence while respecting that the user themselves carry context across sessions.

The cost (user must manually bridge) is low: the user already chose this file because of the ranking. They know why they're here.

### Q4: Approval granularity — Section-based with informed batch-approve

**Base unit: one approval decision per logical section (H2 boundary in the proposal).**

For a typical 5-12 section skill file, that's 5-12 decisions — enough control without exhaustion.

**"Approve remaining" escape hatch** — available after the user has reviewed at least 2-3 sections and established trust in the tool's judgment for this file. Gated behind a brief summary of remaining proposals (one line per section: "§5: remove 12 lines of prescriptive message templates"). The user sees what they're approving before confirming. Not blind.

**"Show all" escape hatch** — user can switch to full-proposal view for any file at any time.

**Scale management:** The broad audit narrows 80 files to ~15-25 high-priority. The user picks 3-5 per session. At 5-12 decisions per file with escape hatches, that's 15-50 decisions per working session — appropriate for someone who values control.

## Key Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| Single proposal (not two passes) | One mental model, no mode-switching | Tool must reason about structure and compression together |
| Ranking at end only | Accurate relative scoring | User doesn't see priority until full scan completes |
| No automatic context passing | Deep-dive independence, no anchoring | User must manually bridge if they want to direct attention |
| Section-based granularity | Matches mental model of file structure | Breaks down if sections are themselves malformed (but structural proposals address this) |
| Informed batch-approve | Throughput when trust is established | Risk of "approval fatigue" on later sections (mitigated by summary requirement) |

## Warnings

1. **The structural proposals ARE the hardest decision.** Merging sections, moving content to other files — these are the changes most likely to cause regression and most cognitively demanding for the user. The proposal must make structural changes visually distinct and front-loaded so the user is freshest when reviewing them.

2. **Category-level patterns (e.g., "all workflow skills have this same verbose section") are the broad audit's job, not the deep-dive's.** If the deep-dive surfaces a cross-cutting pattern, it should flag it for the broad audit's next run rather than trying to solve it file-by-file.

3. **The 80-file scale only works if the funnel is aggressive.** If the broad audit flags 60/80 files as high-priority, the deep-dive UX collapses regardless of chunk size. The audit's ranking must genuinely prioritize — not just sort by descending verbosity.

4. **Approval fatigue is the real enemy.** The user said "plenty of chance to approve/reject" — but after the 30th file, that enthusiasm will erode. The escape hatches must be genuinely available and non-judgmental (no "are you sure you want to skip review?").

## Confidence

0.72 — Position is solid on interaction model and granularity. Moderate uncertainty on whether end-of-run-only ranking will feel too delayed for an 80-file audit that takes substantial time to complete. The user may want earlier signal. A possible compromise (flagging without ranking) partially addresses this but isn't fully validated.
