# Architect Debate Log

## Cycle 1

### Draft Position

5-item checklist: README Verification, Module Docstrings (unchanged), External Attribution, Research Doc, Deletion Detection. Directory-convention mapping with no metadata. Structural verification inline in skill text as grep steps. Clear doc-writer/doc-audit split with TODO markers as handoff. TODO format: `<!-- TODO(doc-writer): {desc} | found={date} | task=#{id} -->`.

### Critic Challenges (6)

1. **Critical — TODO visibility.** HTML comments are invisible in rendered Markdown; context.md says "visible to humans reading the doc." Conflict between rendered visibility and the chosen format.

2. **Critical — Mapping coverage incomplete.** Initial table only covered `serve/{pkg}/src/**` → README. Missed root docs, setup guides, `share/WIRING.md`, cross-package triggers.

3. **Critical — Structural verification too narrow.** Decisions.md says "symbol grep, signature comparison" but position only included symbol grep. Signature drift (when a symbol survives but its API changes) is uncovered by Layer 1.

4. **Moderate — Docstring item contradicts locked decision.** Keeping Module Docstrings as checklist item 2 reopens a cut that decisions.md explicitly locked. Ruff D100 is aspirational (currently in ignore list).

5. **Minor — Metadata argument over-argued.** Spent too much text rejecting metadata when the real issue is the wrong question being asked.

6. **Moderate — Attribution heuristic not operationalized.** No concrete procedure for distinguishing task-caused vs. pre-existing issues.

### Revisions Applied

- Challenge 1: Maintained HTML comments. OwlBear docs are consumed in editors; source visibility is sufficient. Added sync-to-main constraint: TODO markers must be resolved before release.
- Challenge 2: Accepted. Expanded mapping table to full documentation surface.
- Challenge 3: Partially accepted. See Cycle 2.
- Challenge 4: Restored docstrings as transitional item. See Cycle 2 for re-evaluation.
- Challenge 5: Accepted. Shortened metadata section.
- Challenge 6: Accepted. Added 5-step attribution heuristic.

## Cycle 2

### Critic Challenges (5)

1. **Critical — Docstring item contradicts locked decision (again).** Restoring docstrings as "transitional" reopens the cut. The decision was explicit: ruff D100 handles this. The gap (D100 not enforced) is a config task, not a doc-writer design issue.

2. **Critical — Signature comparison missing from Layer 1.** Decisions.md mentions signature comparison alongside symbol grep. Position only implemented grep. Signature drift when a function name survives but parameters change is a real failure mode.

3. **Moderate — TODO markers and consumer audience.** Main branch ships docs to consumers. HTML comments are invisible there. If markers leak through, consumers see correct-looking docs with hidden warnings.

4. **Moderate — Attribution heuristic step 5 relaxes Option C.** Making "already-wrong content that references task symbols" into task-caused work is a scope expansion that contradicts the Option C decision (full-file scan + task-scoped fix).

5. **Moderate — Root doc mapping understated.** Root docs reference many packages (e.g., Cockpit launch commands, MCP inventory). Triggering root reads only on "root source changes" misses package changes that affect root doc content.

### Final Revisions

- Challenge 1: **Accepted.** Removed docstrings from checklist entirely. Respecting the locked cut. The ruff D100 enablement is a separate follow-up task to be created as a brief deliverable. Checklist drops to 4 items.
- Challenge 2: **Partially accepted.** Full signature comparison (AST parsing) is impractical for the per-task gate (research Q2 flags this). However, the LLM editorial layer (Layer 2) handles signature drift during full-file reading — it reads both the README code blocks and the current source, comparing naturally. Acknowledged the gap in Layer 1 and documented the delegation to Layer 2. No separate tool.
- Challenge 3: **Accepted with mitigation.** Added constraint: sync-to-main must not proceed with unresolved TODO markers. doc-audit or a pre-sync check must clear them. HTML comments remain the format — invisible to consumers is a feature (fallback safety), not a bug.
- Challenge 4: **Accepted.** Removed step 5 from the attribution heuristic. Pre-existing issues stay pre-existing regardless of symbol overlap. Cleaner alignment with Option C.
- Challenge 5: **Partially accepted.** Added a public-interface trigger: root docs are triggered when a task changes a package's entry points, CLI commands, or configuration — not just "root source changes." Interior implementation changes don't affect root docs. This is LLM judgment but bounded by the trigger definition.

### Position Assessment

After two Critic cycles, the position is structurally sound. Remaining moderate-severity items (signature drift delegation to Layer 2, root-doc trigger boundaries) are acknowledged trade-offs, not design flaws. The Critic's strongest contributions were: removing the docstring item (respecting locked decisions), tightening the attribution heuristic, and surfacing the sync-to-main constraint for TODO markers.
