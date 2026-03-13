---
id: 777
title: Implement bearclaw decisions list/show/resolve commands
status: todo
priority: nice-to-have
created: 2026-03-13T11:31:47.973694+01:00
updated: 2026-03-13T20:28:05.9002206+01:00
started: 2026-03-13T12:32:49.8278279+01:00
tags:
    - cli
    - process
depends_on:
    - 778
class: standard
---

## Context
CLI commands for the file-based decision-request workflow.
See docs/research/bearclaw-decision-commands.md for research.

## Acceptance Criteria
- [ ] New file: src/bearclaw/commands/decisions.py
- [ ] Module constants: DECISIONS_DIR = Path(docs/decisions), PENDING = DECISIONS_DIR / pending, RESOLVED = DECISIONS_DIR / resolved (relative to cwd)
- [ ] _parse_decision_file(path) helper using yaml.safe_load on --- delimiters (matching agent_def.py pattern). Returns (frontmatter_dict, body_str) or raises ValueError on malformed frontmatter
- [ ] 'bearclaw decisions list' scans pending/ for *.md, parses frontmatter, outputs Rich Table with columns: Task ID (task_id field), Title (first H1 heading text), Age (days since created), Urgency (urgency field), Type (decision_type field)
- [ ] 'bearclaw decisions show {task_id}' finds file by matching task_id frontmatter field across pending/*.md, displays full file content via rich.markdown.Markdown. Argument type: str
- [ ] 'bearclaw decisions resolve {task_id}' interactive flow: find file by task_id, extract options from ## Options subsection headings (### A: ..., ### B: ...), prompt choice via typer.prompt() (NOT Rich Prompt.ask  for CliRunner testability per #778 research), prompt notes via typer.prompt(), typer.confirm() before executing, write ## Resolution section, update frontmatter status to resolved, shutil.move to resolved/
- [ ] Registered in cli.py via app.add_typer(decisions_app)
- [ ] No new dependencies (use yaml.safe_load pattern from agent_def.py)
- [ ] Graceful error messages (typer.echo + typer.Exit(code=1)) for: no pending decisions, task_id not found, malformed frontmatter, ## Options section not found (fall back to free-text input)

[[2026-03-13]] Fri 20:27
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| New file: decisions.py | Clear, correct location | None |
| Module constants DECISIONS_DIR/PENDING/RESOLVED | Precise, matches research recommendation | Added |
| _parse_decision_file() helper | Follows agent_def.py pattern, return type specified | Added |
| decisions list Rich Table | Columns mapped to frontmatter fields + H1 heading | Clarified Title source |
| decisions show {task_id} | Search by frontmatter field (safe, no path traversal) | Clarified arg type |
| decisions resolve interactive | Specified typer.prompt() over Prompt.ask() per #778 testability research, added typer.confirm() | Refined |
| Registered via app.add_typer | Clear, matches existing CLI pattern (9 existing sub-apps) | None |
| No new dependencies | Clear, yaml.safe_load pattern established in 2 modules | None |
| Graceful error messages | Error cases enumerated, fallback for missing Options section | Added fallback |

### Architecture Notes
- Domain: CLI only (bearclaw/commands/) -- single domain
- Pattern: follows established add_typer pattern in cli.py (L45-55)
- Frontmatter parsing: reuse yaml.safe_load --- delimiter pattern from agent_def.py L75-88 and registry.py L136-166
- Security: glob-based file search (pending/*.md) constrains file access; no user-controlled path construction
- TDD: test task #778 exists, added depends_on relationship
- Testability: AC now specifies typer.prompt() over Rich Prompt.ask() per #778 research finding on CliRunner input= compatibility

### Changes Made
- Refined all 9 AC lines with precise implementation details
- Added depends_on: [778] for TDD sequencing
- Changed Prompt.ask to typer.prompt for testability
- Added typer.confirm() before irreversible resolve action
- Added _parse_decision_file helper spec
- Added module constants spec
- Added fallback behavior when Options section missing

### Dependencies
- Added: depends_on #778 (tests must be written first)
- Verified: #767 (research) completed, doc exists at docs/research/bearclaw-decision-commands.md

[[2026-03-13]] Fri 20:27
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| New file: decisions.py | Clear, correct location | None |
| Module constants DECISIONS_DIR/PENDING/RESOLVED | Precise, matches research recommendation | Added |
| _parse_decision_file() helper | Follows agent_def.py pattern, return type specified | Added |
| decisions list Rich Table | Columns mapped to frontmatter fields + H1 heading | Clarified Title source |
| decisions show {task_id} | Search by frontmatter field (safe, no path traversal) | Clarified arg type |
| decisions resolve interactive | Specified typer.prompt() over Prompt.ask() per #778 testability research, added typer.confirm() | Refined |
| Registered via app.add_typer | Clear, matches existing CLI pattern (9 existing sub-apps) | None |
| No new dependencies | Clear, yaml.safe_load pattern established in 2 modules | None |
| Graceful error messages | Error cases enumerated, fallback for missing Options section | Added fallback |

### Architecture Notes
- Domain: CLI only (bearclaw/commands/) -- single domain
- Pattern: follows established add_typer pattern in cli.py (L45-55)
- Frontmatter parsing: reuse yaml.safe_load --- delimiter pattern from agent_def.py L75-88 and registry.py L136-166
- Security: glob-based file search (pending/*.md) constrains file access; no user-controlled path construction
- TDD: test task #778 exists, added depends_on relationship
- Testability: AC now specifies typer.prompt() over Rich Prompt.ask() per #778 research finding on CliRunner input= compatibility

### Changes Made
- Refined all 9 AC lines with precise implementation details
- Added depends_on: [778] for TDD sequencing
- Changed Prompt.ask to typer.prompt for testability
- Added typer.confirm() before irreversible resolve action
- Added _parse_decision_file helper spec
- Added module constants spec
- Added fallback behavior when Options section missing

### Dependencies
- Added: depends_on #778 (tests must be written first)
- Verified: #767 (research) completed, doc exists at docs/research/bearclaw-decision-commands.md
