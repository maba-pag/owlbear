---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "more research needed"
notes: "User has created a screenshot of the current state in the most up to date version of vs code (1.113.0 from March 25th 2026) showing the tool name as `todo` (see docs\decisions\pending\193-todos-vs-todo-tool-name.png). Also, the Tool configuration als o shows the tool is named todo, not todos. No changelog after August 2025 (1.104) even mentions the todo tool, let alone a renaming. The research done so far is not sufficient to conclude that the tool name is `todos` and not `todo`. More research is needed to confirm the current tool name in VS Code."
# >> Agent metadata (do not edit)
task_id: 193
agent: researcher
created: 2026-03-29
urgency: blocking
decision_type: scope-decision
---

# Decision: Is the VS Code tool name `todos` or `todo`?

## Context

Task #193 was created with the premise that `todos` is the OLD tool name and `todo`
is the CURRENT name. Research contradicts this — three independent sources confirm
`todos` IS the current correct name.

The `validate_agents.py` script correctly checks for bare `todo` and flags it as
error ("should be `todos`"). All 11 agent files already use `todos`. Prior research
(task #4, `docs/research/agent-md-format.md`) documented the v1→v2 rename as
`todo` → `todos`. Existing tests (`tests/test_agent_port_v2.py`) assert `todos`.

See `docs/research/stale-tool-names.md` for full analysis.

## Options

### A: No rename needed — todos is correct ← (rec:) recommended

- Effort: 0 (close task #193 as invalid)
- Trade-off: none — codebase is already correct
- Risk: if a very recent VS Code update renamed `todos` back to `todo` (not
  reflected in docs updated March 25, 2026), agent files would break
- Evidence: VS Code cheat sheet (2026-03-25), prior research doc, existing tests

### B: Rename todos to todo — user's original intent

- Effort: ~1 day, 3 tasks (rename all agent files, update validator, update tests)
- Trade-off: contradicts official docs and prior research findings
- Risk: if `todos` is correct (as docs say), this breaks all tool references

### C: Defer / do nothing

- Effort: 0
- Trade-off: task #193 stays blocked until resolved
- Risk: none immediate

## Recommendation

.95 confidence — Option A. The official VS Code documentation (March 25, 2026),
prior project research (task #4), and existing tests all independently confirm
`todos` is the current name. If you have evidence of a more recent rename not yet
reflected in the docs, choose Option B.

## Impact of Deferral

Task #193 is blocked. Follow-up tasks for expanding the validator (separate from
the rename question) will be created at `ideation` regardless of this decision.
