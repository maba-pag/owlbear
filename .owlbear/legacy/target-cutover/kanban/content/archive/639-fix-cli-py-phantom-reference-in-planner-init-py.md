---
id: 639
title: Fix cli.py phantom reference in planner/__init__.py docstring
status: archived
priority: medium
created: 2026-04-06T02:35:22.7621528+02:00
updated: 2026-04-06T05:50:26.8317838+02:00
started: 2026-04-06T05:50:26.8317838+02:00
completed: 2026-04-06T05:50:26.8317838+02:00
tags:
    - scope:orchestrator
    - phase-2
    - type:fix
    - docs
parent: 619
class: standard
---

## Acceptance Criteria

- Remove "and cli.py" from the docstring in serve/orchestrator/src/owlbear/planner/__init__.py L5
- Docstring should reference only loop.py (the actual caller with planner imports)
- waves.py also imports from planner (models only) — include if warranted by docstring scope
- No other changes needed

## Context
Discovered during audit of #624. The docstring references cli.py as an in-process path caller, but cli.py has never existed in the repository. Fabricated evidence of "cli.py L15-16" propagated unverified through researcher, architect, builder, and reviewer stages.

[[2026-04-06]] Mon 02:50
REJECT: Premise challenge FAIL. cli.py exists at serve/orchestrator/src/owlbear/cli.py and imports from planner at L15-16 (read_board, select_tasks). The docstring reference is accurate. The audit finding that produced this task was itself incorrect — removing the cli.py reference would make the docstring less accurate, not more. Evidence: file_search confirmed cli.py exists; grep confirmed L15: from owlbear.planner.board import read_board, L16: from owlbear.planner.selector import select_tasks.

[[2026-04-06]] Mon 03:28
## Research\n- Research doc: none (premise validation only)\n- Sources: 3 files read (cli.py, loop.py, planner/__init__.py), 0 external\n- Finding: **Premise invalid** — cli.py exists at serve/orchestrator/src/owlbear/cli.py and imports read_board (L15) + select_tasks (L16) from planner. The docstring is accurate as-is.\n- Recommendation: Archive this task. No code change needed. (confidence: 0.97)\n- Follow-up tasks created: none\n- Decision requests: none\n- Challenge: SKIPPED — no recommendation to challenge (task invalidated by evidence)\n\n**Verified callers of planner package:**\n| File | Imports |\n|---|---|\n| cli.py L15-16 | read_board, select_tasks |\n| loop.py L17-18 | read_board, select_tasks |\n| waves.py L12 | DispatchEntry (models only) |\n\nThe audit finding from #624 that produced this task was itself incorrect. No implementation needed — recommend immediate archival.

[[2026-04-06]] Mon 04:02
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | **FAIL** | cli.py exists at serve/orchestrator/src/owlbear/cli.py. L15-16 import read_board and select_tasks from planner. Docstring at planner/__init__.py L5 is accurate. |

### Verdict: REJECT
Premise invalid — independently verified cli.py exists and imports from planner. The audit finding from #624 that created this task was incorrect. Removing the cli.py reference would degrade docstring accuracy.

### Action Taken: Reject to ideation. Recommend immediate archival — no code change is warranted.

[[2026-04-06]] Mon 05:50
## Research (validation pass)
- Prior research (Mon 03:28) and architecture review (Mon 04:02) both found premise invalid
- Independent re-verification confirms: cli.py exists at serve/orchestrator/src/owlbear/cli.py (L15: read_board, L16: select_tasks)
- planner/__init__.py L5 docstring correctly references cli.py
- No code change needed. Recommend immediate archival.
- Sources: 2 files verified (cli.py, planner/__init__.py), 0 external
- Follow-up tasks: none
- Decision requests: none
- Challenge: SKIPPED (premise invalidated, no recommendation to challenge)
