# Context — doc-writer quality

## Problem Statement (draft)

The doc-writer pipeline agent and the `docs` kanban stage are not producing meaningful documentation updates. The user reports that the agent primarily updates Excalidraw diagram timestamps ("last verified" footers) but fails to read, check, and substantively update documentation — particularly README files. The documentation corpus is described as "REALLY bad, outdated, and plain wrong."

## Root Cause (M1 finding)

The doc-writer answers the wrong question. It asks "did this task's diff break any docs?" — which is almost always "no" because most tasks touch a few lines, the README was already wrong before the task ran, and the checklist doesn't ask "is the doc correct overall?". This is a scope-of-concern problem: task-scoped diff checking will never fix pre-existing rot.

Concrete evidence:
- `serve/kanban/README.md` has stale "orchestrator" reference (line 3), inconsistent task_id typing (int vs string, lines 25-26), and the doc-writer has passed this file many times without catching any of it
- Diagrams have PNG screenshots (user-created) but they're not embedded in READMEs, and the doc-writer hasn't created any new diagrams since initial creation
- The main visible doc-writer action is updating Excalidraw footer timestamps
- **pipeline.excalidraw** references removed "orchestrator" while wearing a 2026-05-05 "Last verified" date — verification theater
- **memory-layers.excalidraw** has text clipping and overlap rendering errors
- Multiple diagrams are extremely shallow (pipeline is just boxes + labels, no meaningful detail)
- No new diagrams created since initial batch (e.g., browser package has none)

## Active Tensions

1. Task-scoped vs. file-scoped: The doc-writer only checks "did this diff break docs?" but never "are the docs correct?"
2. Verification theater: Diagram timestamps imply review happened, but content is never read
3. Depth vs. throughput: The 90/80 no-op rate design goal (from original brief) may be actively harmful — it optimizes for speed at the cost of quality
4. Two audiences: Docs serve both agents (who parse them mechanically) and humans (who need accuracy and usability) — currently serving neither well
5. Attribution hygiene: full-file verification will find pre-existing issues unrelated to the current task — need a clean separation between inline fixes and follow-up tasks

## Locked Outcomes (post-challenge revision)

1. **Per-task honest verification:** doc-writer reads the *entire* relevant README when a task touches a package. Uses structural checks (grep for removed symbols, signature comparison) where possible + LLM editorial for missing coverage and prose accuracy. Fixes task-related issues inline. Marks pre-existing issues with `<!-- TODO: ... -->` markers directly in the doc — visible to humans reading the doc and parseable by doc-audit.
2. **No diagram responsibility:** doc-writer no longer touches .excalidraw files. All diagram work moves to doc-audit.
3. **doc-audit as deep sweep:** periodic prompt handles full editorial review — resolves TODO markers, creates/fixes diagrams, does cross-reference checking, structural quality review across the whole corpus.

### Cut (challenger pressure)
- Module docstrings: ruff D100 handles this mechanically, not a doc-writer concern
- "Tiered speed": not a deliverable, emergent from #1 + #3

## Project Type

existing-feature/refactor — `doc-writer` v2 and `w-doc-update` already exist and shipped. This is about behavioral quality, not existence.

## Current State

- `doc-writer.agent.md`: 165-line agent with 7-item checklist, scope classification, persona as "technical editor at regulated-industry publisher"
- `w-doc-update` skill: v2 with scope classification, relevance gating, 7 checklist items, deletion detection
- Prior brief: `docs-currency-2026-04-19` designed the current system
- Infrastructure: `doc-index`, `serve/tools/`, diagram `describes` metadata all in place
- Surface survey: all 9 `serve/*/README.md` files exist, diagrams exist, Docs Gate sections show evidence — but content quality is poor
