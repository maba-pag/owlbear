---
id: 1423
title: 'P1-02: Rewrite w-doc-update skill — 4-item checklist + verification layers'
status: todo
priority: needed
created: 2026-05-08T00:32:18.617094+00:00
updated: 2026-05-09T01:15:40.014827+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
- type:docs
parent: 1421
depends_on:
- 1422
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

Full rewrite of `share/skills/w-doc-update/SKILL.md` implementing the doc-writer quality redesign:

1. Convention mapping table mapping code path patterns to documentation files (serve/{pkg}/src/** → serve/{pkg}/README.md, etc.)
2. 4-item checklist: README Verification, External Attribution, Research Doc, Deletion Detection — no diagram items
3. Verification layers section: Layer 1 (grep for removed symbols) + Layer 2 (LLM full-file editorial read)
4. TODO marker format and insertion rules: `> **TODO:** {category} — {description} [#{id}]` with categories stale|inaccurate|missing|unverified
5. Gate-blocking rules: unverified on task-introduced content blocks; unverified on pre-existing passes
6. No-impact fast path: if changed files map to no READMEs, advance with evidence
7. Attribution rules for task-caused (fix inline) vs pre-existing (TODO marker)

**In scope:** SKILL.md content only. Must pass test assertions from #1422.
**Out of scope:** Agent file changes (#1424), prompt file changes (#1425).

Brief: see parent #1421
## Research\n- Research doc: .owlbear/research/doc-update-skill-rewrite-1423.md\n- Sources: 4 studied, 3 high-relevance\n- Recommendation: fast-track — implementation already complete, 52/52 tests pass (confidence: 0.95)
[[2026-05-08]]
## Research\nValidation pass — the SKILL.md rewrite was already implemented by the parent #1421 builder (commits 4404082c, eb98fff3, d41dc0b4). All 52 test assertions from #1422 pass. All 7 AC items verified against the brief design spec.\n\nResearch doc: .owlbear/research/doc-update-skill-rewrite-1423.md\nConfidence: 0.95\nNo follow-up tasks needed — siblings #1424 and #1425 already exist.
[[2026-05-08]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single deliverable: SKILL.md rewrite |
| Interface clarity | PASS | 7 AC items are specific and testable (52 assertions from #1422 confirm) |
| Dependency correctness | PASS | Depends on #1422 (test suite) — completed/archived, tests pass |
| Module layering | N/A | Skill file, no code imports |
| TDD compliance | PASS | #1422 provides 52 test assertions; implementation pre-verified |
| KISS/YAGNI | PASS | Exactly the scope from the brief, no extras |
| Premise challenge | PASS | Doc-writer quality redesign is a validated need (brief + parent #1421) |
| Pattern consistency | PASS | Follows standard SKILL.md structure (frontmatter, steps, output template, verification checklist) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Shared/skills domain only |

### Failure Mode Map
N/A — no codepaths with failure modes (markdown skill file).

### Design Diverge
Skipped — single clear approach (implementation already complete, no alternatives to evaluate).

### Challenge Results
Challenger: SKIPPED — all td:0 (per Step 2.1)

### Test Depth
AC lines: all td:0 — implementation already exists and is covered by 52 tests from #1422.
Test-writer: SKIP

### Context Note
Research confirms the SKILL.md v3 rewrite was already implemented by the parent #1421 builder (commits 4404082c, eb98fff3, d41dc0b4). All 7 AC items verified against the current file content. Builder should verify existing content satisfies AC and confirm — no new writing needed.

Tagged `type:docs` for test-writer pass-through routing.

### Verdict: APPROVE
### Action Taken: Advanced to todo with type:docs tag added for pipeline routing.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Architect confirmed: "Test-writer: SKIP" in architecture review.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Non-implementation task pass-through confirmed from task body (`## Test-Writer Notes`).
- Implementation: no files changed.
- Verification: quality-runner scoped run on tests/test_doc_writer_quality_1422.py => 52 passed, 0 failed.
- Lint: ruff scoped to tests/test_doc_writer_quality_1422.py => clean (0 issues).
- Coverage: N/A for docs-only/pass-through verification cycle.
- Evidence summary: acceptance criteria are already satisfied by existing content in share/skills/w-doc-update/SKILL.md; builder required only independent verification and routing to review.
- Fixes applied: none (no implementation delta needed).
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_doc_writer_quality_1422.py`: 52 passed, 0 failed, 0 skipped.
- Parallel fan-out note: `code-reader` returned no response, so I fell back to sequential manual review of `share/skills/w-doc-update/SKILL.md` and `tests/test_doc_writer_quality_1422.py`.

### Lint
- `ruff` scoped to `tests/test_doc_writer_quality_1422.py`: clean (0 violations).

### Coverage
- N/A for this markdown-only verification task. The independent quality-runner pass was run without coverage modules.

### Loop / Scope
- Prior review failures: none. The task file contains one `## Builder Notes` section at `.owlbear/kanban/tasks/1423-p1-02-rewrite-w-doc-update-skill-4-item-checklist-verification-layers.md:84` and no prior `## Review Evidence` section.
- Dirty-tree / commit-diff audit: not independently executable in the current tool surface, so TestFromAC immutability remains slightly lower-confidence.

### AC Compliance
| AC | Evidence | Mapped Test(s) | Status |
|---|---|---|---|
| 1. Convention mapping table | `share/skills/w-doc-update/SKILL.md:24-37` and explicit src row at `:30`; no-impact fast path at `:37` | `tests/test_doc_writer_quality_1422.py:28`, `:275`, `:433`, `:451` | PASS |
| 2. 4-item checklist, no diagram items | checklist section at `share/skills/w-doc-update/SKILL.md:39-72`; item headings at `:43`, `:52`, `:58`, `:63` | `tests/test_doc_writer_quality_1422.py:28`, `:231`, `:238`, `:244`, `:250` plus diagram-ban assertions in the same suite | PASS |
| 3. Verification layers | Item 1 layers at `share/skills/w-doc-update/SKILL.md:47-48`; dedicated section at `:94-101` | `tests/test_doc_writer_quality_1422.py:284`, `:294` | PASS |
| 4. TODO marker format + categories | template at `share/skills/w-doc-update/SKILL.md:74-87`, exact template at `:76` | `tests/test_doc_writer_quality_1422.py:189-225`, especially `:220` | PASS |
| 5. Gate-blocking rules | `share/skills/w-doc-update/SKILL.md:89-92`, with explicit task/pre-existing lines at `:91-92` | `tests/test_doc_writer_quality_1422.py:405`, `:419` | PASS |
| 6. No-impact fast path | `share/skills/w-doc-update/SKILL.md:37` requires `"no docs impact" with evidence and advance` | `tests/test_doc_writer_quality_1422.py:433` | PASS |
| 7. Attribution rules: task-caused fix inline vs pre-existing TODO marker | live file contains the rule at `share/skills/w-doc-update/SKILL.md:49-50`, but the suite does not contain a discriminating assertion for either clause | no direct AC7 proof; closest checks only prove generic TODO marker presence / gate wording at `tests/test_doc_writer_quality_1422.py:60`, `:78`, `:405`, `:419` | FAIL |

### Test Quality Assessment
- `TestFromAC_*` coverage is strong for AC1-AC6: the suite checks exact headings, exact row coupling, explicit gate lines, and the exact TODO template.
- AC7 remains under-proven. A mutation that removes or weakens `share/skills/w-doc-update/SKILL.md:49-50` while leaving the generic TODO section and gate rules intact would likely keep the current 52-test suite green.

### Deductions
- `-0.18` AC7 lacks mapped discriminating TestFromAC proof.
- `-0.02` `code-reader` returned no response; manual sequential review used instead.
- `-0.02` commit/diff-based immutability check was unavailable in the current tool surface.

### Verdict
- FAIL
- Confidence: `0.78`

### Action
- Reject to `todo`. The live SKILL.md content satisfies the task, but the proof is incomplete for AC7. This is a test-gap / proof-quality failure, not a builder-content failure.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add discriminating `TestFromAC_*` assertions that fail if Item 1 no longer requires `Fix task-caused issues inline` and `For pre-existing unresolved issues, insert a visible TODO marker`; if the strengthened tests pass against current content, advance directly back to review per builder-skip | `tests/test_doc_writer_quality_1422.py` | AC7 gap: `share/skills/w-doc-update/SKILL.md:49-50` is not directly asserted; current closest checks are only `tests/test_doc_writer_quality_1422.py:60`, `:78`, `:405`, `:419` |