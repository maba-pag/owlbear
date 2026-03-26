## Research

Doc: docs/research/bearclaw-board-command-failure-tests-red-gate.md

Summary: #924 should keep the failure-path RED seam at the public CLI boundary.
Use CliRunner against the root app, patch only
bearclaw.commands.board.subprocess.run, assert exit code 1 plus stage-specific
messages that mention kanban-md, and keep the existing happy-path board
assertions in the same tests/test_cli_board.py file once implementation lands.
Reject helper-only seams and live kanban-md subprocesses for this task.

Follow-up:

- Existing #920 remains the GREEN implementation task.
- Existing #923 remains optional JSON-fixture cleanup.
- Created #926 Create reusable subprocess result helpers for BearClaw CLI tests.

Command executed:

- kanban\kanban-md.exe create "Create reusable subprocess result helpers for BearClaw CLI tests" --priority nice-to-have --status ideation --tags "cli,test,tooling,phase-14,type:test,scope:cli" --body "Research follow-up from docs/research/bearclaw-board-command-failure-tests-red-gate.md. Optional cleanup after #924 and #920. AC: (1) add a test-only helper that builds CompletedProcess-like subprocess results for success, non-zero exit, and malformed-JSON stdout or stderr cases without spawning the real binary; (2) expose an explicit spawn-failure seam for missing-binary coverage, such as an OSError fixture or equivalent helper; (3) adopt the helper in board failure-path tests and at least one existing BearClaw CLI subprocess test so duplication drops without changing behavior; (4) scope stays under tests/ only and adds no production abstraction." -> #926

Attribution updated: docs/sources/overview.md
