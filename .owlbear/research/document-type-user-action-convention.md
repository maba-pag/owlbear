# Document type:user-action Convention

> **Owning task:** #663 — Document type:user-action convention in r-pipeline-protocol and agent-common
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Parent task #661 researched and recommended the `type:user-action` tag convention to prevent #597-style futile pipeline loops. The convention was designed but not yet documented in the skill/instruction files that agents read. This research validates the documentation approach: what goes where, exact insertion points, and content specifications.

**Question:** What content should be added to each target file, and where?

## 2. Sources Studied

| Source | Path/URL | Relevance |
|--------|----------|-----------|
| #661 research doc | .owlbear/research/user-action-required-pipeline-handling.md | 1.0 — convention design |
| r-pipeline-protocol §5 | share/skills/r-pipeline-protocol/SKILL.md (L178-210) | 1.0 — insertion target |
| agent-common.instructions.md | share/instructions/agent-common.instructions.md | 1.0 — insertion target |
| r-project-standards §5 | share/skills/r-project-standards/SKILL.md (L75-91) | 1.0 — insertion target |
| #597 task body | kanban evidence of 4-cycle loop | .90 — dry-run baseline |
| 5 resolved action requests | .owlbear/decisions/resolved/167-*, 548-*, 532-* | .85 — AR flow validation |

## 3. Analysis

### Target file audit

| File | Current state | Gap | Insertion point |
|------|--------------|-----|-----------------|
| r-pipeline-protocol §5 | Mentions "physical user action" in Blocking Convention prose | No dedicated subsection, no heuristics, no dry-run | New `### User-Action Tasks` between `### Decision Tiers` (L201) and `### Handoff` (L203) |
| agent-common.instructions.md | Per-Agent Section Mapping only | No agent responsibility table for detection | New `## User-Action Detection Responsibilities` after existing table |
| r-project-standards §5 | Type row lists `type:build`, `type:test`, `type:docs` | `type:user-action` absent | Add to Type row examples + add behavioral note row |

### Content specifications

**r-pipeline-protocol — `### User-Action Tasks` (~40 lines):**
- Tag purpose: 1-line definition
- Detection heuristics: 4-row table (physical-action verbs, external-system refs, no testable interfaces, manual checkbox steps)
- Lifecycle: blocking flow (architect → AR → block → user acts → scribe resolves → architect re-verifies)
- Post-completion fast-path: `## Action Completed` in body → architect fast-approval
- Dual-nature: split per atomicity rule, code task depends_on user-action task
- Dry-run scenario: 8-step walkthrough showing #597 prevention (2 architect cycles vs 4+)

**agent-common — `## User-Action Detection Responsibilities` (~15 lines):**
- 5-row table: researcher (provisional), architect (mandatory gate), orchestrator (mechanical), test-writer/builder/reviewer (pass-through), auditor (verify convention)

**r-project-standards §5 — Type row expansion (~3 lines):**
- Add `type:user-action` to Type examples
- Add pipeline-behavior note row: `type:user-action` triggers architect AR gate, see r-pipeline-protocol §5

### Risk assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Pipeline-protocol §5 exceeds reasonable section size | Low — ~40 lines in a 210-line file | Dry-run scenario is the largest part; keep to 8 steps max |
| agent-common becomes prescriptive beyond its scope | Low — responsibility table matches existing section-mapping pattern | Table format, not prose |
| Stale cross-references if #662/#664 aren't completed | Medium — pipeline-protocol will ref NON_IMPL_TAGS and arch-review | Use "see" references; content stands alone without them |

## 4. Recommendation (.90 confidence)

Document as specified above. No alternative approaches — the content and placement are determined by the AC and parent #661 research. High confidence because:
- All insertion points verified (grep + file reads)
- No conflicts with existing content
- Content is derived directly from validated #661 recommendations
- Cross-file references are forward-compatible (each section stands alone)

Challenge: SKIPPED — no novel recommendation; documenting existing convention from #661 (which was challenged: block → revised to .78).

## 5. Follow-up Tasks

None needed. This task IS the documentation work — it proceeds through the pipeline (architect → doc-writer) to produce the actual edits.
