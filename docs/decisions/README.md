# Decision Requests

This directory contains structured decision requests from agents that need user input before proceeding.

- `pending/` — Unresolved decisions awaiting user response
- `resolved/` — Decisions the user has acted on (moved here after resolution)

## For users

Check `pending/` periodically (or when notified). To resolve a decision:

1. Open the file in `pending/`
2. Fill in the `## Resolution` section at the bottom (Decision, Notes, Resolved date)
3. Change `status: pending` to `status: resolved` in the frontmatter
4. Move the file to `resolved/`

The planner detects resolved decisions each cycle and unblocks the corresponding task.

## For agents

See `.github/instructions/decision-requests.instructions.md` for the full format and workflow.
