---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Accept frontmatter-inference test as sufficient for AC 3"
notes: ""
# >> Agent metadata (do not edit)
task_id: 42
agent: builder
created: 2026-03-27
urgency: blocking
decision_type: acceptance-criteria
---

# Decision: Is the frontmatter-inference test sufficient evidence for AC 3 of task #42?

## Context

Task #42 ("Add user-invocable: false to pipeline-only skills") requires adding
`user-invocable: false` to 11 pipeline-only SKILL.md files. AC 1 and AC 2 are
fully implemented and passing (11 files updated, 13/13 tests green, ruff clean).

AC 3 reads: _"Test slash-command menu shows only user-invocable skills."_

The test-writer wrote `TestFromAC_SlashCommandMenu::test_slash_command_menu_shows_only_user_invocable_skills`,
which dynamically scans every SKILL.md and asserts that the set of skills
_without_ `user-invocable: false` exactly equals the 10 user-invocable skills.
This is the maximum level of automated verification achievable — the VS Code
slash-command menu cannot be exercised from pytest.

The task has gone through two full review cycles and been returned to todo both
times specifically on AC 3: the reviewer requires either literal VS Code UI
verification or a change to the AC. The architect's original review notes say
"Manual UI verification — appropriate for YAML-only config change", indicating
the intent was always metadata verification rather than browser/IDE automation.

## Options

### A: Accept frontmatter-inference test as sufficient for AC 3 ← (rec:) recommended

The `TestFromAC_SlashCommandMenu` test is the best automated proxy achievable
without a VS Code extension testing harness. It verifies the data contract that
controls what the menu shows.

- Effort: 0 (already done)
- Trade-off: accepts that the test cannot drive VS Code's actual rendering
- Risk: VS Code ignores `user-invocable` somehow, but research at .95 confidence
  confirmed the property is supported

### B: Replace AC 3 with explicit manual verification note — (bp:) best practice

Update the task AC 3 to read "Verify manually: open VS Code chat, type `/`,
confirm only the 10 user-invocable skills appear." Record that note in the
task body as evidence, then advance to review.

- Effort: user opens VS Code and checks the menu once (~5 min)
- Trade-off: no automated regression guard, but the frontmatter test already
  serves as a proxy; manual step is unambiguous evidence
- Risk: environment where user is running doesn't have the skills loaded yet

### C: Defer / skip AC 3 verification entirely

Drop AC 3 from the acceptance criteria as untestable in this environment and
pass the task on AC 1+2 alone.

- Effort: 0
- Trade-off: no evidence the menu actually works, but the frontmatter change
  is low-risk; property is documented to work
- Risk: silent failure if the property has a bug in this VS Code version
