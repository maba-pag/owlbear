---
id: 692
title: Update builder.agent.md and tdd-workflow skill for GREEN-only phase
status: archived
priority: needed
created: 2026-03-08T16:39:47.2363665+01:00
updated: 2026-03-09T11:22:18.7937099+01:00
started: 2026-03-08T18:03:54.2812305+01:00
completed: 2026-03-09T11:22:18.7937099+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
depends_on:
    - 690
class: standard
---

## Context

Split from #683. Depends on #690 (test-writer agent, done). See docs/test-writer-agent-research.md.

With the test-writer handling RED phase, the builder's primary job shifts to GREEN: make existing tests pass. The builder retains the ability to add tests for implementation edge cases, but in a clearly marked separate class.

## Acceptance Criteria

### builder.agent.md changes

- [ ] `<persona>`: rewrite to reflect GREEN-only role -- the builder receives pre-written failing tests from the test-writer and takes pride in making them pass with minimal, surgical code. Remove references to writing tests first or seeing own tests fail. Keep existing personality (disciplined, surgical diffs, convention-strict).
- [ ] `<critical_rules>`: update first rule from "Write tests BEFORE implementation. See them FAIL first." to reflect receiving tests from test-writer and verifying they fail before implementing. All other existing critical_rules unchanged. Add two new rules: (1) TestBuilderDiscovered convention -- builder-added tests go in `TestBuilderDiscovered` class, never modify `TestFromAC_*` classes; (2) BLOCK protocol -- if test-writer's interface assumptions are infeasible, return `BLOCK: {explanation}` instead of silently modifying TestFromAC tests.
- [ ] `<multi_agent_context>`: dispatched AFTER test-writer. Pipeline position: `planner -> architect -> test-writer (RED) -> **builder (GREEN)** -> reviewer -> writer -> auditor`. Primary job is make test-writer's failing tests pass.
- [ ] `<workflow>` summary updated: "Read task + existing tests -> Verify tests fail -> Implement minimal code (GREEN) -> Refactor if needed -> May add TestBuilderDiscovered tests -> Verify (pytest + ruff) -> Advance to review"
- [ ] `<output_format>`: add BLOCK variant -- `BLOCK: #{id} -- {title}\nReason: {explanation of interface mismatch between TestFromAC assumptions and feasible implementation}\nSuggested AC revision: {what needs to change}`
- [ ] `<boundaries>`: new red flag: "You are modifying a TestFromAC class (only test-writer writes those -- add your tests to TestBuilderDiscovered instead)"
- [ ] `<boundaries>`: new red flag: "You are implementing code without first verifying the test-writer's tests fail"
- [ ] `<self_critique>` checklist: update "Tests written BEFORE implementation (saw them fail)" to "Test-writer's tests verified as failing before implementation" and add "Any builder-added tests are in TestBuilderDiscovered class, not TestFromAC"
- [ ] `<examples>`: update good_example to show GREEN-only flow (read existing tests -> verify fail -> implement -> pass). Remove RED step references.

### tdd-workflow SKILL.md changes

- [ ] Step 3 rewritten from "Write failing tests (RED)" to "Read existing tests" -- builder reads test-writer's `TestFromAC_*` tests, identifies expected interfaces (function signatures, class names, error types), plans implementation approach
- [ ] Step 3 includes: verify all `TestFromAC_*` tests currently FAIL (`uv run pytest tests/test_{module}.py -q --tb=short`). If any pass, something already exists -- investigate before implementing.
- [ ] New Step 5 (after GREEN, before Refactor): "Add builder-discovered tests (optional)" -- builder may add `TestBuilderDiscovered` class for edge cases found during implementation. These must also follow RED-GREEN: write test, see fail, implement fix.
- [ ] Step numbering adjusted for new step (original steps 5-7 become 6-8)
- [ ] Verification checklist updated: add "All TestFromAC tests pass", "Any builder-added tests are in TestBuilderDiscovered class", "No TestFromAC classes modified"

### Unchanged

- [ ] No changes to builder's tool access list (frontmatter `tools` array stays identical)
- [ ] tdd-workflow skill name stays `tdd-workflow` (renaming cascades to copilot-instructions.md, builder references -- YAGNI)

## Architecture Notes

- The tdd-workflow skill name stays as-is (renaming would cascade to copilot-instructions.md, builder references, etc. -- YAGNI)
- The skill content shifts focus from RED+GREEN to GREEN-only, but the name `tdd-workflow` remains the builder's primary skill
- The BLOCK protocol routes through the orchestrator to the architect, NOT back to test-writer directly (prevents oscillation)
- Backward compatibility: when no `TestFromAC_*` classes exist (old-style single-agent TDD), builder falls back to full RED+GREEN workflow. Mention this in Step 3 as a note.

[[2026-03-08]] Sun 17:50
## Review Evidence

### AC Compliance  builder.agent.md

| AC Line | Evidence | Status |
|---------|----------|--------|
| persona rewritten for GREEN-only | Lines 27-31: receives pre-written failing tests, making them pass, red to green | PASS |
| critical_rules: GREEN phase, TestBuilderDiscovered, BLOCK protocol | Lines 40-42: all three new rules present with correct wording | PASS |
| multi_agent_context: dispatched AFTER test-writer | Lines 56-62: pipeline shown, primary job stated | PASS |
| workflow summary updated | Lines 67-69: GREEN-only summary with TestBuilderDiscovered mention | PASS |
| output_format: BLOCK variant | Lines 94-98: BLOCK format with reason + suggested AC revision | PASS |
| boundaries: TestFromAC red flag | Line 127: present | PASS |
| boundaries: implement without verify fail | Line 128: present | PASS |
| self_critique updated | Lines 194,202: both items updated/added | PASS |
| examples: GREEN-only flow | Lines 169-177: good_example shows read tests -> verify fail -> implement -> pass with TestBuilderDiscovered | PASS |
| tool access list unchanged | Frontmatter tools array identical to committed version | PASS |

### AC Compliance  tdd-workflow SKILL.md

| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 3 rewritten to Read existing tests | STILL says Write failing tests (RED) at line 25 | FAIL |
| Step 3 includes TestFromAC verify-fail | No TestFromAC mention anywhere in SKILL.md | FAIL |
| New Step 5 builder-discovered tests | No such step exists  Step 5 still Refactor | FAIL |
| Step numbering adjusted (8 steps) | Still 7 steps, numbering unchanged | FAIL |
| Verification checklist updated | Line 108 still says Tests written BEFORE implementation  no TestFromAC/TestBuilderDiscovered items | FAIL |
| Skill name unchanged | name: tdd-workflow confirmed | PASS |

### Test Quality
N/A  no Python code or tests involved (agent/skill markdown files only)

### Security
No issues  markdown instruction files, no code execution surface

### Rejection Details

| Failed Item | Gap | Required Fix |
|-------------|-----|--------------|
| tdd-workflow Step 3 | Still Write failing tests (RED)  must be Read existing tests with TestFromAC interface analysis | Rewrite Step 3 per AC |
| tdd-workflow Step 3 verify | No TestFromAC_* fail-verification instruction | Add verify-fail substep to Step 3 |
| tdd-workflow Step 5 | Missing Add builder-discovered tests step | Insert new Step 5 between GREEN and Refactor |
| tdd-workflow numbering | 7 steps, should be 8 | Renumber Steps 5-7 to 6-8 |
| tdd-workflow checklist | Missing 3 new checklist items | Add TestFromAC pass, TestBuilderDiscovered class, no TestFromAC modified |

### Verdict: FAIL confidence .95
builder.agent.md is complete (10/10 AC lines pass). tdd-workflow SKILL.md has 5/6 AC lines failing  the GREEN-only restructuring was not applied. Only the coverage section (from a prior task) was changed.

[[2026-03-08]] Sun 17:53
## Builder Notes (RETRY)
- Files changed: .github/skills/tdd-workflow/SKILL.md
- Step 3 rewritten: Read existing tests with TestFromAC interface analysis + verify-fail + backward compat note
- New Step 5: Add builder-discovered tests (optional) with RED-GREEN substeps
- Steps renumbered: 5->6 (Refactor), 6->7 (Verify), 7->8 (Advance)
- Checklist: 3 new items (TestFromAC pass, TestBuilderDiscovered class, no TestFromAC modified)
- No Python code involved  markdown-only change, no pytest/ruff needed

[[2026-03-08]] Sun 17:55
[[2026-03-08]] Sun RETRY Review Evidence

### AC Compliance tdd-workflow SKILL.md (RETRY)
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 3 rewritten to Read existing tests | L24: heading + L25-30 TestFromAC interface analysis | PASS |
| Step 3 verify-fail instruction | L32-38: verify fail + investigate-if-pass | PASS |
| Backward compat note | L40-42: blockquote fallback to RED+GREEN | PASS |
| New Step 5 builder-discovered tests | L57-69: TestBuilderDiscovered + RED-GREEN substeps | PASS |
| Step renumbering (5->6, 6->7, 7->8) | 8 total steps, Refactor=6, Verify=7, Advance=8 | PASS |
| Checklist: TestFromAC pass | L105 | PASS |
| Checklist: TestBuilderDiscovered class | L107 | PASS |
| Checklist: No TestFromAC modified | L106 | PASS |
| Skill name unchanged | L2: name: tdd-workflow | PASS |

### builder.agent.md spot-check
All 10 AC lines confirmed passing in prior review. Spot-checked: critical_rules (L40-42), pipeline (L56-58), tools array (15 entries unchanged). No regressions.

### Test Quality
N/A -- markdown instruction files only, no Python code

### Security
No issues -- no code execution surface

### Verdict: PASS confidence .95

[[2026-03-08]] Sun 18:03
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Agent inventory: builder desc changed to GREEN phase. Skill inventory: tdd-workflow desc changed to GREEN phase workflow |
| 2 | Docstrings complete | No | N/A | No Python code changed -- only .agent.md and SKILL.md |
| 3 | sources.md | No | N/A | No new external patterns -- rewrite based on already-attributed research (#683) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | Task body references docs/test-writer-agent-research.md |
| 6 | SKILL.md frontmatter | Yes | Updated | tdd-workflow description updated to match GREEN-only content |

### Files Updated
- .github/copilot-instructions.md (agent + skill inventory tables)
- .github/skills/tdd-workflow/SKILL.md (frontmatter description)

### Scratch Files Cleaned
- None (no scratch files for #692)

[[2026-03-09]] Mon 04:57
Wave 3, agent: auditor

[[2026-03-09]] Mon 11:22
## Audit
### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| persona GREEN-only | L27-31: receives tests from test-writer, no RED refs | PASS |
| critical_rules: 3 new rules | L40-42: GREEN phase, TestBuilderDiscovered, BLOCK | PASS |
| multi_agent_context: after test-writer | L56-62: correct pipeline | PASS |
| workflow summary | L67-69: GREEN-only with TestBuilderDiscovered | PASS |
| output_format: BLOCK variant | L94-98: format present | PASS |
| boundaries: TestFromAC red flag | L127: present | PASS |
| boundaries: verify fail red flag | L128: present | PASS |
| self_critique updated | L196,L204: both items | PASS |
| examples: GREEN-only flow | L169-177: read->fail->implement | PASS |
| tool access unchanged | 15 entries identical | PASS |
| SKILL Step 3: Read existing tests | L24-38: TestFromAC analysis+verify fail | PASS |
| SKILL Step 5: builder-discovered | L57-69: TestBuilderDiscovered+RED-GREEN | PASS |
| SKILL 8 steps | Renumbered correctly | PASS |
| SKILL checklist 3 new items | L113-117: all present | PASS |
| SKILL name unchanged | L2: tdd-workflow | PASS |
| Tool access list unchanged | frontmatter identical | PASS |
| Skill name unchanged | name: tdd-workflow | PASS |
| Backward compat note | L40-42: fallback to RED+GREEN | PASS |

### Test Results
- pytest: 1271 passed, 20 skipped, 0 failures (pre-existing slack_sdk issue excluded)
- ruff: N/A (markdown-only changes)

### Confidence: .97
### Action: archive
