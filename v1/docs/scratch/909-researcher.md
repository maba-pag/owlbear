## Research

Research doc: docs/research/bearclaw-board-command-red-gate.md

Key findings:

- Use CliRunner on the root BearClaw app and patch only the board command's subprocess.run seam.
- Model age in status from the latest move into the current status, with created fallback when no move exists.
- Assert Rich output via stable substrings, not full snapshots.

Follow-up:

- Existing #910 remains the GREEN implementation task.
- Created #923 for optional reusable paired kanban list/log JSON fixtures.
- Command: kanban\kanban-md.exe create "Create reusable kanban JSON fixture helpers for BearClaw CLI board tests" --priority nice-to-have --status ideation --tags cli,test,tooling,phase-14,type:test,scope:cli --depends-on 909

Attribution:

- Updated docs/sources/overview.md for kanban-md, Rich Tables, Typer Testing, and Typer Add Typer.
