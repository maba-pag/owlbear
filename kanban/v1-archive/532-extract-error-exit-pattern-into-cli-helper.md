---
id: 532
title: Extract error-exit pattern into CLI helper
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:37.5818336+01:00
updated: 2026-03-21T05:01:33.2295508+01:00
started: 2026-03-07T00:26:12.332562+01:00
completed: 2026-03-21T05:01:33.2295508+01:00
tags:
    - audit
    - dry
    - scope:cli
depends_on:
    - 481
class: standard
---

F-19: except SomeException: typer.echo(f'Error: {exc}'); raise typer.Exit(1) pattern repeated 21 times. Extract _cli_error(msg: str) -> NoReturn helper. See docs/research/cli-error-exit.md.

Research checklist: N/A - trivial DRY extraction of 2-line error-exit pattern.

Recommendation (.90): Single _cli_error(msg) helper function. Covers both try/except and validation patterns. KISS-aligned.

AC:
- _cli_error() defined with NoReturn annotation
- Zero raw typer.Exit(code=1) in cli.py except _version_callback
- All existing CLI tests pass
- ruff clean

[[2026-03-21]] Sat 05:01
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| _cli_error() defined with NoReturn annotation | Already satisfied in src/bearclaw/commands/__init__.py | Verified |
| Zero raw typer.Exit(code=1) in cli.py except _version_callback | Original AC is stale after #481 split; stronger condition now holds: only src/bearclaw/commands/__init__.py contains typer.Exit(code=1) and it is the helper itself | Refined and verified |
| All existing CLI tests pass | Dedicated helper tests exist in tests/test_cli_error_helper.py and archived task #805 audited the contract | Verified |
| ruff clean | Archived task #805 recorded ruff clean for helper + tests | Verified |

### Architecture Notes
- The linked research doc docs/research/cli-error-exit.md is marked Status: Complete and describes this extraction as the chosen DRY pattern.
- Dependency #481 is archived; the CLI split moved the implementation location from src/bearclaw/cli.py to src/bearclaw/commands/__init__.py.
- Current repo state already contains _cli_error(msg: str) -> NoReturn and 7 command modules import and call it.
- Commit 8dc0f5d ("chore: commit _cli_error helper + tests (#532, auditor)") contains src/bearclaw/commands/__init__.py and tests/test_cli_error_helper.py, which satisfies this task's contract.
- Routing #532 to todo would duplicate completed work. The correct action is to archive it as stale board metadata.

### Changes Made
- Claimed #532 for architect review
- Appended architecture evidence pointing to current code, archived task #805, and commit 8dc0f5d
- Chose archive over backlog -> todo because the implementation and paired tests already exist

### Dependencies
- Verified: #481 archived
- Verified: #805 archived test task for the helper contract
- Verified: repo state and commit 8dc0f5d satisfy #532
