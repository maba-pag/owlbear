---
id: 944
title: Add frontend-audit prompt built on frontend-design skill
status: archived
priority: nice-to-have
created: 2026-03-22T19:01:47.1427788+01:00
updated: 2026-03-25T13:24:20.9469418+01:00
started: 2026-03-25T13:24:15.5035874+01:00
completed: 2026-03-25T13:24:15.5035874+01:00
tags:
    - ui
    - agent
    - scope:copilot
    - docs
    - type:docs
parent: 930
depends_on:
    - 934
    - 938
    - 943
class: standard
---

## Context

Pilot the first user-facing command in the Impeccable-style workflow for OwlBear: a scoped frontend audit that uses OwlBear's own frontend-design guidance rather than importing Impeccable verbatim.
See docs/research/impeccable-command-patterns.md.

## Acceptance Criteria

- [ ] Add `.github/prompts/frontend-audit.prompt.md` with description-only frontmatter (no `mode:`, `agent:`, or `applyTo:` keys) and an optional `${input:scope}` variable.
- [ ] Prompt reads `docs/design-context.md` when present for project-specific context and references the `frontend-design` skill by relative path (`../skills/frontend-design/SKILL.md`).
- [ ] Prompt produces a structured, severity-ranked audit using the two-tier classification from `references/anti-patterns.md` (blocker vs heuristic) across four categories: accessibility, responsive behavior, design-system consistency, and anti-patterns.
- [ ] Prompt explicitly does not edit code; it reports findings and recommends next commands (`/frontend-normalize`, `/frontend-polish`) or follow-up tasks.
- [ ] Prompt follows the same four-step structure as sibling prompts (Load context, Plan/scope, Execute audit, Verify/Guardrails).

[[2026-03-25]] Wed 07:10

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: description-only frontmatter + scope input | Clear, verifiable. Matches sibling prompt pattern (frontend-normalize, frontend-polish, design-context). | Tightened: explicit forbidden keys listed |
| AC2: references skill by relative path + design-context.md | Clear, verifiable. Consistent with all three sibling prompts. | Tightened: explicit relative path specified |
| AC3: severity-ranked audit with four categories | Original severity-ranked was underspecified. | Tightened: references anti-patterns.md two-tier taxonomy (blocker/heuristic) |
| AC4: no code edits, recommends next commands | Clear, verifiable. | Tightened: explicit command names added |
| AC5: four-step structure | New AC line. | Added: ensures structural consistency with siblings |

### Architecture Notes

- **Pattern consistency:** Three sibling prompts already exist: design-context.prompt.md (#943), frontend-normalize.prompt.md (#945), frontend-polish.prompt.md (#946). All follow a four-step structure (Load context, Plan, Execute, Verify/Guardrails). The audit prompt must follow the same pattern.
- **Severity taxonomy:** The frontend-design skill's references/anti-patterns.md defines Universal Blockers (hard gates) vs Taste Heuristics (warnings). The audit output must use this existing classification rather than inventing a new one.
- **Read-only constraint:** Unlike normalize and polish, the audit prompt must NOT edit any files. It produces a report only.
- **TDD:** Test-writer will create contract tests (following test_945_frontend_normalize_prompt.py pattern) at the todo stage.
- **No application code involved:** This is a markdown prompt file only, scope:copilot domain.

### Changes Made

- Refined AC: tightened 4 original lines, added AC5 (structural consistency)
- No new tasks created (TDD handled by pipeline test-writer at todo stage)

### Dependencies

- Verified: #934 (archived), #938 (archived), #943 (archived) - all satisfied

[[2026-03-25]] Wed 07:37

## Test-Writer Notes

- Test file: tests/test_944_frontend_audit_prompt.py
- Classes: TestFromAC_FrontendAuditPrompt
- Tests per category: happy 4, edge 4, error 4, boundary 16
- Total: 28 tests, all FAIL
- ruff: clean
- AC1 (frontmatter + scope): 6 tests
- AC2 (skill path + design-context): 4 tests
- AC3 (severity taxonomy + 4 cats): 9 tests
- AC4 (no edits + next commands): 4 tests
- AC5 (four-step structure): 5 tests

[[2026-03-25]] Wed 11:19

## Builder Notes

- Files changed: .github/prompts/frontend-audit.prompt.md
- Tests: 28 passed in tests/test_944_frontend_audit_prompt.py; scoped coverage run reported TOTAL 2 percent (bare cov project-level metric).
- Lint: ruff check tests/test_944_frontend_audit_prompt.py passed.
- Evidence: RED verification before implementation showed 28 failing tests from missing prompt file; GREEN verification after implementation showed 28 passed.
- Fixes applied: Added .github/prompts/frontend-audit.prompt.md with description-only frontmatter, optional scope input, four-step flow (Load context, Plan and scope, Execute audit, Verify and guardrails), relative frontend-design references, blocker and heuristic severity tiers, and report-only guardrails with next command recommendations.

[[2026-03-25]] Wed 12:15

## Review Evidence

### Review: #944 - Add frontend-audit prompt built on frontend-design skill

### Test Results

- pytest: 28 passed, 0 failed in 0.18s.
- Scope: tests/test_944_frontend_audit_prompt.py.
- Preservation evidence: git diff 385e6de..20198bb on tests/test_944_frontend_audit_prompt.py was empty. Current HEAD diff is formatting-only and not builder-authored.

### Lint Results

- ruff: All checks passed for tests/test_944_frontend_audit_prompt.py.

### Coverage

- Not applicable. The reviewed implementation is .github/prompts/frontend-audit.prompt.md, not Python source.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC1 COVERED: test_prompt_file_exists, test_frontmatter_has_description, test_frontmatter_no_mode_key, test_frontmatter_no_agent_key, test_frontmatter_no_applyto_key, and test_scope_input_variable_present would fail on missing file, missing description key, forbidden frontmatter keys, or missing scope input.
- AC2 COVERED: test_references_design_context_md, test_references_frontend_design_skill_by_relative_path, test_skill_reference_is_not_absolute_path, and test_skill_reference_resolves_to_existing_file would fail if the prompt dropped docs/design-context.md or used a bad skill path.
- AC3 COVERED: test_blocker_tier_mentioned, test_heuristic_tier_mentioned, test_references_anti_patterns_file, test_audit_output_is_severity_ranked, and test_all_four_categories_present would fail if the blocker or heuristic taxonomy, anti-pattern reference, severity ranking, or required categories were removed.
- AC4 COVERED: test_does_not_edit_code, test_recommends_frontend_normalize_command, test_recommends_frontend_polish_command, and test_mentions_follow_up_tasks_or_next_commands require explicit read-only behavior and concrete next steps.
- AC5 COVERED: test_step_load_context_present, test_step_plan_or_scope_present, test_step_execute_audit_present, test_step_verify_or_guardrails_present, and test_four_steps_in_order require the sibling four-step structure and ordering.

#### Security Review

- No security issues found. The deliverable is a static markdown prompt with no code execution, secrets, or unsafe input handling.

#### Test Integrity

- All TestFromAC_FrontendAuditPrompt methods were preserved. No diff exists between RED commit 385e6de and builder commit 20198bb for tests/test_944_frontend_audit_prompt.py.

#### Test Quality

- Assertion specificity: ADEQUATE. The suite checks concrete keys, commands, step labels, relative-path resolution, and required category names.
- Negative or error paths: ADEQUATE. The suite forbids mode, agent, and applyTo frontmatter keys and rejects absolute skill paths.
- Mutation reasoning: ADEQUATE. Removing a required category, dropping blocker or heuristic tags, or reordering steps would fail named tests.
- Test independence: STRONG. Each test only reads the prompt file through a shared helper and shares no mutable state.
- Descriptive names: STRONG. Test names map directly to AC clauses.

#### Data Safety

- No data safety issues found. The prompt does not persist data, mutate state, or introduce concurrency.

#### Implementation-Aware Test Gaps

- No significant untested paths. The only extra instruction beyond the AC is default scope selection when input is absent, which is simple guidance rather than behavioral code complexity.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

- AC1 PASS: .github/prompts/frontend-audit.prompt.md line 2 has description-only frontmatter and line 9 has the optional scope variable.
- AC2 PASS: .github/prompts/frontend-audit.prompt.md lines 13 through 15 read docs/design-context.md, ../skills/frontend-design/SKILL.md, and ../skills/frontend-design/references/anti-patterns.md.
- AC3 PASS: .github/prompts/frontend-audit.prompt.md line 7 sets severity-ranked output, line 16 names blocker and heuristic, lines 33 through 36 list the four categories, lines 40 through 41 define the tiers, and lines 51 through 55 require tagged findings and next-step recommendations. The referenced taxonomy headings are at .github/skills/frontend-design/references/anti-patterns.md lines 6 and 37.
- AC4 PASS: .github/prompts/frontend-audit.prompt.md lines 46 through 55 keep the output report-only and recommend /frontend-normalize and /frontend-polish; lines 59 through 61 repeat the no-edit and follow-up-task guardrails.
- AC5 PASS: .github/prompts/frontend-audit.prompt.md lines 11, 21, 29, and 46 implement Load context, Plan and scope, Execute audit, and Verify and guardrails in order.

### Verdict: PASS

- Confidence: .95.

### Action Taken

- Review evidence appended.
- Pending status move to docs and reviewer claim release.

[[2026-03-25]] Wed 12:26

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Pure markdown prompt, no behavior/API/protocol change. Command Surface Selection table describes surf types, not individual files. |
| 2 | Docstrings | No | N/A | No Python source files created or modified. |
| 3 | docs/sources/overview.md | Yes | Pass | Impeccable attribution already present in Task #930 section (line 41). frontend-audit derives from that same research; no new external pattern. |
| 4 | README.md | No | N/A | No CLI commands added or changed. |
| 5 | Research doc linked | Yes | Pass | docs/research/impeccable-command-patterns.md exists (Test-Path True). Linked from task body Context section. |

### Files Updated

- None

### Scratch Files Cleaned

- None (no docs/scratch/944-* files existed)

-t

[[2026-03-25]] Wed 13:24

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: description-only frontmatter + scope input | Frontmatter has only description key; no mode/agent/applyTo. scope input on line 9. 6 tests pass. | PASS |
| AC2: skill by relative path + design-context | Lines 13-15 reference design-context.md, SKILL.md, anti-patterns.md. 4 tests pass. | PASS |
| AC3: severity-ranked two-tier taxonomy, 4 categories | blocker + heuristic tiers, 4 categories listed. 9 tests pass. | PASS |
| AC4: no code edits, recommends next commands | Guardrail present. /frontend-normalize and /frontend-polish recommended. 4 tests pass. | PASS |
| AC5: four-step structure | Steps 1-4 in correct order matching siblings. 5 tests pass. | PASS |

### Test Results

- pytest (scoped): 28 passed, 0 failed (0.19s)
- pytest (full suite): 4279 passed, 160 failed (pre-existing), 2 skipped
- ruff: All checks passed

### Architect Quality

- AC specificity: Excellent. All 5 lines concrete and testable.
- Edge case coverage: No gaps found.
- Design direction: Sibling pattern, read-only constraint, severity taxonomy reuse all correct.
- AC quality score: 5/5

### Confidence: .97

### Action: archive
