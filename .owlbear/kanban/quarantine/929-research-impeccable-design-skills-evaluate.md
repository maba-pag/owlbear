---
id: 929
title: 'Research: Impeccable design skills — evaluate adoption for OwlBear frontend skill'
status: archived
priority: nice-to-have
created: 2026-03-21T23:56:33.4243655+01:00
updated: 2026-03-22T19:11:16.3731207+01:00
started: 2026-03-22T19:11:12.0857775+01:00
completed: 2026-03-22T19:11:12.0857775+01:00
tags:
    - research
    - ui
    - scope:copilot
    - agent
class: standard
---

## Context

Paul Bakaus's Impeccable repo (<https://github.com/pbakaus/impeccable>, Apache 2.0) expands on Anthropic's frontend-design skill with 7 domain-specific reference files and curated anti-patterns. OwlBear already has a frontend.instructions.md but it is intentionally lean compared to what Impeccable offers.

## Scope

- Research only. Do not create or modify .github/skills/frontend-design/ or .github/instructions/frontend.instructions.md as part of this task.
- Deliver durable artifacts only: docs/research/impeccable-design-skills.md, docs/sources/overview.md, and ideation follow-up tasks for the adoption work.

## Acceptance Criteria

- [ ] Create docs/research/impeccable-design-skills.md with sections for context/question, sources studied, comparison against .github/instructions/frontend.instructions.md, a catalog of all seven Impeccable reference areas, anti-pattern assessment, recommendation, and follow-up tasks.
- [ ] The research doc must state, for each reference area (typography, color-and-contrast, spatial-design, motion-design, interaction-design, responsive-design, ux-writing), whether OwlBear should adapt it, keep it out of always-on instructions, or skip it, with rationale.
- [ ] The research doc must recommend what stays in .github/instructions/frontend.instructions.md versus what moves into a dedicated .github/skills/frontend-design/ skill, and must explicitly state whether any Impeccable material should be copied verbatim.
- [ ] The research doc must classify anti-pattern guidance into universal blockers versus taste-specific heuristics and give concrete examples of each class.
- [ ] Create ideation follow-up tasks for the concrete adoption work and link them back to docs/research/impeccable-design-skills.md.
- [ ] Update docs/sources/overview.md with attribution entries for the external sources used to shape the recommendation.

## References

- Repo: <https://github.com/pbakaus/impeccable>
- Website: <https://impeccable.style>
- Anthropic original: <https://github.com/anthropics/skills/tree/main/skills/frontend-design>

[[2026-03-22]] Sun 04:45

## Research

- Doc: docs/research/impeccable-design-skills.md
- Summary:
  - OwlBear should keep frontend.instructions.md lean and scoped, then add a dedicated .github/skills/frontend-design/ skill for deeper design guidance.
  - All seven Impeccable reference areas are worth adapting; none should be copied verbatim into always-on instructions.
  - Anti-pattern guidance should split universal blockers from taste-specific heuristics.
  - Command-surface adoption like /teach-impeccable is deferred to #930.
- Follow-up tasks created: #934, #937, #938.
- Attribution updated: docs/sources/overview.md.
- Create commands recorded in docs/research/impeccable-design-skills.md.

[[2026-03-22]] Sun 17:12

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Clone repo into docs/scratch/research/impeccable/ for analysis | Useful research method but not a durable deliverable; scratch clones should not be required for downstream verification. | Rewrote into an explicit no-code research-output contract. |
| Catalog the 7 reference files (typography, color-and-contrast, spatial-design, motion-design, interaction-design, responsive-design, ux-writing) with a summary of each | Valid requirement, but it belongs as document content rather than a standalone process checkpoint. | Bound it to a required section in docs/research/impeccable-design-skills.md. |
| Compare against OwlBear's existing frontend.instructions.md - identify gaps and overlaps | Architecturally necessary because frontend.instructions.md is the current scoped frontend policy surface. | Kept as an explicit comparison requirement in the research contract. |
| Evaluate which reference files to adopt (verbatim with attribution), adapt, or skip - with rationale | Sound decision point, but the durable question is the adoption policy, not the temporary analysis workflow. | Rewrote it to require per-reference adoption guidance and an explicit verbatim-copy decision. |
| Assess anti-pattern catalog: which ones are universal vs. taste-specific | Good and mechanically checkable once tied to concrete examples. | Kept and required examples in both classes. |
| Produce research doc at docs/research/impeccable-design-skills.md | Correct primary artifact. | Kept. |
| Create follow-up kanban tasks for concrete adoption steps (e.g., create/update frontend-design skill, add anti-patterns file) | Correct if the follow-up tasks are atomic and linked back to the research doc. | Kept and verified with #934, #937, and #938. |
| Update docs/sources/overview.md with attribution entry | Correct and required because this recommendation depends on external prior art. | Kept and verified. |

### Architecture Notes

- .github/instructions/frontend.instructions.md is already the repo's scoped frontend baseline, so the recommendation to keep that file lean and move deeper design fluency into a dedicated skill matches the current instruction architecture instead of bloating always-on prompt text.
- The workspace already uses dedicated skill packages under .github/skills/*/SKILL.md, and no .github/skills/frontend-design/ exists yet. That makes the proposed skill addition a clean follow-up rather than duplicate agent-config surface.
- docs/research/impeccable-design-skills.md already captures the seven reference areas, the gap analysis against the existing frontend instructions, the anti-pattern split, the recommendation to adapt rather than copy, and the follow-up tasks.
- docs/sources/overview.md already contains explicit attribution rows for Impeccable, the Impeccable website, the Anthropic frontend-design skill, and the VS Code Agent Skills docs.
- Follow-up tasks remain atomic at this level: #934 creates the new skill, #937 trims frontend.instructions.md and adds the skill handoff, and #938 adds the anti-pattern taxonomy. #937 and #938 correctly depend on #934.
- Command-surface reuse is already separated into #930, so this task stays on the design-guidance research domain instead of mixing skill architecture with command UX.
- Research-only task. No runtime code path, no new security surface, TDD N/A under the docs-only gate.

### Changes Made

- Claimed task #929 as architect-929.
- Rewrote the body to add explicit no-code scope and replace the ephemeral scratch-clone AC with durable outputs.
- Appended this architecture review.
- Approved the task for the next pipeline stage.

### Dependencies

- Verified: docs/research/impeccable-design-skills.md exists.
- Verified: docs/sources/overview.md contains attribution entries for the researched sources.
- Verified follow-up tasks: #934, #937, #938.
- Verified dependency wiring: #937 -> #934, #938 -> #934.
- Verified TDD predecessor not required because this task produces research and docs only.

[[2026-03-22]] Sun 17:29

## Test-Writer Notes

- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-03-22]] Sun 17:48

## Builder Notes

- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-03-22]] Sun 18:05

## Review Evidence

## Review: #929 - Research: Impeccable design skills - evaluate adoption for OwlBear frontend skill

### Test Results

- pytest command: `uv run pytest tests/test_skills.py tests/test_project_definition_skill.py -q --tb=short`
- Result: 40 passed, 4 failed, 2 warnings (exit 1).
- Failures:
  - `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_discovers_18_real_skills` (expects 19 skills, found 20)
  - `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_real_skills_have_nonempty_names` (asserts 19 skills precondition)
  - `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_list_skills_includes_all_19` (asserts 19 skills precondition)
  - `tests/test_project_definition_skill.py::TestProjectDefinitionSkillFrontmatter::test_user_invokable_false_in_frontmatter` (`user-invocable` missing in frontmatter)
- Scope note: these failures are outside #929 deliverables (research doc, source ledger, and follow-up tasks only).

### Lint Results

- ruff command: `uv run ruff check src/ tests/`
- Result: exit 1 with many pre-existing repo-wide findings (terminal output truncated).
- Scoped ruff command: `uv run ruff check tests/test_skills.py tests/test_project_definition_skill.py`
- Result: 3 findings (all `RUF100`) at `tests/test_skills.py:298`, `tests/test_skills.py:352`, `tests/test_skills.py:368`.
- Scope note: findings are outside #929 deliverables.

### Coverage

- N/A for #929 (docs-only research task; no runtime module changed).

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- N/A. #929 is docs-only and has no `TestFromAC_*` classes or test file output from this task.

#### Security Review

- No security issues in scope. #929 artifacts are documentation and kanban metadata only.

#### Test Integrity (TestFromAC comparison)

- N/A. No task-scoped `TestFromAC_*` edits exist for #929.

#### Test Quality

| Dimension | Rating | Evidence |
|---------|--------|---------|
| Assertion specificity | ADEQUATE | No task-scoped tests in #929; no runtime behavior introduced. |
| Negative/error paths | ADEQUATE | N/A for docs-only scope. |
| Mutation reasoning | ADEQUATE | No implementation under review for #929. |
| Test independence | ADEQUATE | No task-scoped tests added or edited. |
| Descriptive names | ADEQUATE | No task-scoped tests added or edited. |

#### Data Safety

- No data safety issues in scope. No persistence, concurrency, or input-processing code changed.

#### Implementation-Aware Test Gaps

- None in scope. #929 did not introduce implementation branches.

### Pass 2 - INFORMATIONAL

- Independent pytest and ruff runs are currently red in unrelated files (`tests/test_skills.py`, `tests/test_project_definition_skill.py`). This should be tracked separately from #929 because #929 changed research/docs artifacts only.
- `git --no-pager log --all --oneline --grep #929 -n 20` returned no commits tagged with `#929`; evidence collection relied on direct artifact verification.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Create research doc with required sections | `docs/research/impeccable-design-skills.md:6`, `:17`, `:28`, `:40`, `:56`, `:73`, `:103` show context, sources, comparison, 7-area catalog, anti-patterns, recommendation, and follow-up tasks sections. | N/A (docs-only) | PASS |
| Per-reference decision with rationale for all seven areas | `docs/research/impeccable-design-skills.md:44-50` lists typography, color-and-contrast, spatial-design, motion-design, interaction-design, responsive-design, and ux-writing with verdict and rationale. | N/A | PASS |
| Recommend instructions vs skill split and explicit verbatim-copy decision | `docs/research/impeccable-design-skills.md:75`, `:78` define skill vs instructions split; `:52` states verbatim adoption is rejected for all seven files. | N/A | PASS |
| Classify anti-patterns into universal blockers vs taste-specific heuristics with examples | `docs/research/impeccable-design-skills.md:58` (universal blockers examples), `:64-65` (taste-specific heuristics examples). | N/A | PASS |
| Create ideation follow-up tasks and link back to research doc | Follow-ups listed in `docs/research/impeccable-design-skills.md:103-127` with create commands using `--status ideation`; linked tasks exist with parent 929 in `kanban/tasks/934-create-owlbear-frontend-design-skill-from-curated.md:14`, `kanban/tasks/937-refactor-frontend-instructions-md-into-lean.md:14`, and `kanban/tasks/938-add-owlbear-frontend-anti-pattern-taxonomy.md:14`; explicit doc backlinks in `kanban/tasks/937-refactor-frontend-instructions-md-into-lean.md:29` and `kanban/tasks/938-add-owlbear-frontend-anti-pattern-taxonomy.md:30`. | N/A | PASS |
| Update source attribution ledger | `docs/sources/overview.md:5` introduces the Task #929 section with source rows at `:9-12` (Impeccable repo/site, Anthropic skill, VS Code docs). | N/A | PASS |

### Verdict: PASS

### Action Taken

- Claimed #929 as `reviewer-929`.
- Appended Review Evidence.
- Advanced task to docs gate.

[[2026-03-22]] Sun 19:10

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Create docs/research/impeccable-design-skills.md with required sections | File exists with 7 sections: context, sources, comparison, catalog, anti-patterns, recommendation, follow-ups | PASS |
| Per-reference decision with rationale for all 7 areas | Section 4 lists all 7 with Verdict=Adapt and rationale | PASS |
| Recommend instructions vs skill split + verbatim-copy decision | Section 6 recommends skill split; Section 4 rejects verbatim for all seven | PASS |
| Classify anti-patterns into universal blockers vs taste heuristics with examples | Section 5 lists 9 blockers and 9 taste heuristics with concrete examples | PASS |
| Create ideation follow-up tasks linked to research doc | #934 (todo), #937 (ideation), #938 (ideation) exist with parent=929 | PASS |
| Update docs/sources/overview.md with attribution | 4 attribution rows present for Impeccable, website, Anthropic skill, VS Code docs | PASS |

### Test Results

- pytest: 3751 passed, 109 failed, 20 skipped (all failures pre-existing: numpy compat, bearclaw CLI refactoring, RED tests for unimplemented tasks)
- ruff: N/A for docs-only task (no source code changed)

### AC Quality Score: 4/5

AC was adequate. Architect rewrote ephemeral scratch-clone AC into durable outputs, improving verifiability. Minor gap: original AC included a scratch-clone step that was not a durable deliverable.

### Quality Notes

- Upstream quality gap: research doc and overview.md were not committed by researcher/writer. Research doc committed by auditor (a5890ac). overview.md left uncommitted because it contains mixed changes from #929, #930, #934, #941, #924.

### Confidence: .97

### Action: archive

[[2026-03-22]] Sun 19:11

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Create docs/research/impeccable-design-skills.md with required sections | File exists with 7 sections: context, sources, comparison, catalog, anti-patterns, recommendation, follow-ups | PASS |
| Per-reference decision with rationale for all 7 areas | Section 4 lists all 7 with Verdict=Adapt and rationale | PASS |
| Recommend instructions vs skill split + verbatim-copy decision | Section 6 recommends skill split; Section 4 rejects verbatim for all seven | PASS |
| Classify anti-patterns into universal blockers vs taste heuristics with examples | Section 5 lists 9 blockers and 9 taste heuristics with concrete examples | PASS |
| Create ideation follow-up tasks linked to research doc | #934 (todo), #937 (ideation), #938 (ideation) exist with parent=929 | PASS |
| Update docs/sources/overview.md with attribution | 4 attribution rows present for Impeccable, website, Anthropic skill, VS Code docs | PASS |

### Test Results

- pytest: 3751 passed, 109 failed, 20 skipped (all failures pre-existing: numpy compat, bearclaw CLI refactoring, RED tests for unimplemented tasks)
- ruff: N/A for docs-only task (no source code changed)

### AC Quality Score: 4/5

AC was adequate. Architect rewrote ephemeral scratch-clone AC into durable outputs, improving verifiability. Minor gap: original AC included a scratch-clone step that was not a durable deliverable.

### Quality Notes

- Upstream quality gap: research doc and overview.md were not committed by researcher/writer. Research doc committed by auditor (a5890ac). overview.md left uncommitted because it contains mixed changes from #929, #930, #934, #941, #924.

### Confidence: .97

### Action: archive

[[2026-03-22]] Sun 19:11

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a5890ac | docs | docs/research/impeccable-design-skills.md | #929 |
