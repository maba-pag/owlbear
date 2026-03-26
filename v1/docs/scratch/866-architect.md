## Architecture Review

**Verdict:** APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Append a one-line closure note to #866 stating that #822 already records the duplicate finding, #812 is the source of truth for the shipped core cleanup, and any further lifecycle change to #822 must occur while working directly on #822 | Verifiable self-contained board action that preserves the duplicate trail without instructing a cross-task edit | Keep |
| The closure note cites docs/research/core-init-reexport-stale-task.md | Verifiable provenance for why #866 is redundant | Keep |
| Archive #866 after appending the note | Clear terminal state for the redundant meta-task | Keep |
| No other task files, src/, or tests/ are modified | Required to keep the task single-domain and compliant with the cross-task edit rule in agent-common.instructions.md | Keep |

### Architecture Notes

Current repo and board evidence confirm the duplicate conclusion: archived #812 already implemented and audited the core __init__.py cleanup, the live code and targeted tests still match that state, and #822 already contains the duplicate finding plus a block reason. The original #866 text was not executable because it told the assignee on #866 to edit and archive #822, which violates the shared-task boundary rule that agents may not modify tasks outside the dispatched assignment.

Existing closure-task precedent in #837 and #865 uses atomic self-closure AC instead of cross-task edits. Reframing #866 the same way keeps the cleanup precise, auditable, and mechanically verifiable. No TDD predecessor is required because this is a closure/verification task with no application-code or test changes.

### Changes Made

- Rewrote the task body as an atomic self-closure task with explicit AC
- kanban\kanban-md.exe edit 866 --title "Archive redundant core re-export duplicate-cleanup meta-task" --body ... --claim dusk-wren
- Wrote full architecture review to docs/scratch/866-architect.md because kanban-md CLI argument parsing rejects markdown tables in --body/--append-body
- kanban\kanban-md.exe edit 866 --status todo --release

### Dependencies

- Added/Removed/Verified: verified #812 archived as source of truth, #822 already carries duplicate evidence and a block reason, docs/research/core-init-reexport-stale-task.md documents the stale-task finding; no code dependencies and no TDD task required
