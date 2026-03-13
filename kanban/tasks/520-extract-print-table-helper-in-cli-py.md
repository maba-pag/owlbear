---
id: 520
title: Extract _print_table helper in cli.py
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:29.4319581+01:00
updated: 2026-03-12T10:32:59.1578714+01:00
started: 2026-03-06T23:58:23.9523377+01:00
completed: 2026-03-12T10:32:59.1578714+01:00
tags:
    - audit
    - dry
    - refactor
    - scope:cli
depends_on:
    - 481
class: standard
---

DRY-04/F-03: Table formatting (col_widths, fmt, header, separator, rows) duplicated 3 times in cli.py.

## Research (trivial)

Checklist 1-3: N/A - trivial DRY extraction of table formatting, 3 copies in cli.py.

### Call sites

| # | Function | Line | Pattern |
|---|----------|------|---------|
| 1 | project_list | ~161 | header + sep + rows |
| 2 | ks_list | ~464 | header + sep + rows |
| 3 | _print_usage_table | ~605 | header + sep + rows + sep + footer |

Sites 1-2 are identical. Site 3 adds a separator before a totals row.

### Approach

Extract _print_table(headers, rows, footer=None). When footer is None: header + sep + rows. When footer is provided: header + sep + rows + sep + footer. ~15 LOC helper replaces ~30 LOC duplication.

Rich table considered but rejected (KISS/YAGNI): Rich is only a transitive dep, not imported in cli.py, and would change output formatting for no functional benefit.

### AC

- [ ] _print_table helper exists with (headers, rows, footer=None) signature
- [ ] project_list uses _print_table
- [ ] ks_list uses _print_table
- [ ] _print_usage_table uses _print_table with footer=totals
- [ ] Output unchanged for all 3 commands
- [ ] Tests pass, ruff clean

[[2026-03-12]] Thu 10:29
## Architecture Review
**Verdict:** BLOCK (Superseded)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| _print_table helper exists | Superseded by #630 (rich.table.Table) | N/A |
| project_list uses _print_table | #630 replaced with rich.table.Table | N/A |
| ks_list uses _print_table | #630 replaced with rich.table.Table | N/A |
| _print_usage_table uses _print_table | #630 replaced with rich.table.Table | N/A |
| Output unchanged | N/A - #630 changed output format | N/A |
| Tests pass, ruff clean | N/A | N/A |

### Architecture Notes
Task #630 (archived) superseded this entire task. It replaced all hand-rolled table
formatting with rich.table.Table - a superior approach. Confirmed: no col_widths,
_print_table, or hand-rolled header+sep+rows patterns remain in CLI code.

### Changes Made
- Unblocked task
- Deleting as superseded (all AC fulfilled by #630)

### Dependencies
- #481 (CLI split): archived
- #630 (rich.table.Table): archived - fully supersedes this task
