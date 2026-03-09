---
id: 577
title: 'Recurring: Source inspiration audit (every 3 days)'
status: docs
priority: important
created: 2026-03-04T08:03:33.1356117+01:00
updated: 2026-03-09T18:10:01.7889179+01:00
tags:
    - recurring
    - sop
class: standard
---

## Purpose

Track upstream changes in all sources used as inspiration (listed in `docs/sources/overview.md`). When a source has been updated since our last check, analyze the changes and determine if they offer improvements worth adopting.

## Schedule

- **Type:** recurring
- **Frequency:** every 3 days
- **Last run:** never
- **Next due:** immediately

## Execution Protocol

1. The orchestrator creates a subtask: `Source inspiration audit — YYYY-MM-DD` with `--parent 577 --status ideation --tags "sop-run,source-check"`
2. The subtask moves through the full pipeline (ideation → … → done)
3. After the subtask reaches `done`, update `Last run` date in this task's body

## SOP: Source Inspiration Audit

### Phase 1: Inventory

1. Read `docs/sources/overview.md` in full
2. For each source entry, note: name, URL, what was taken, where used, date adopted
3. Group sources by section/research topic for systematic checking

### Phase 2: Check for Updates

For each source:

1. If it's a **GitHub repo**: check commits, releases, and tags since the date in `docs/sources/overview.md`
2. If it's a **PyPI package**: check changelog and releases since adoption date
3. If it's an **article/doc page**: check if the page has been modified (Last-Modified header, archive.org, or content diff)
4. If it's a **paper (arxiv)**: check for revised versions

Record per source:

- Source name and URL
- `has_updates` (bool)
- Summary of changes (commits, releases, content changes)
- Relevance to what we originally adopted

### Phase 3: Analyze Changes

For each source with updates:

1. **Read the changes** — commits, changelog entries, new documentation sections
2. **Evaluate relevance** — does this change affect the pattern, code, or idea we adopted? Reference the "What we studied" and "Where Used" columns
3. **Assess benefit** — would adopting this change improve our implementation? Be specific about *which* files/modules would benefit
4. **Assess risk** — would adopting this change break anything? Check for API changes, deprecations, or behavioral differences
5. **Rate the change:**
   - `skip` — no relevant changes, or change doesn't affect our usage
   - `nice-to-have` — minor improvement, no urgency
   - `important` — useful feature or pattern improvement
   - `needed` — addresses a known gap or deprecation in our code

### Phase 4: Create Tasks

For each change rated `nice-to-have` or above:

1. **Check existing board** — `kanban-md list --tag source-update` to avoid duplicates
2. Create a kanban task in `ideation` with:
   - Title describing the change to adopt (e.g., "Adopt moonshine v0.0.52 streaming improvements")
   - Body referencing: the source name/URL, the specific change (commit hash or release version), why it's beneficial, and which OwlBear files to modify
   - Tags: `source-update`, plus relevant module tags (e.g., `voice`, `knowledge`, `auth`)
   - Priority matching the rating
3. Update the `Date` column in `docs/sources/overview.md` for all checked sources (even those with no relevant changes — the date records when we last verified)

### Phase 5: Report

Append a summary to the subtask body:

- Sources checked: N (grouped by section)
- Sources with updates: N
- Sources with relevant updates: N
- Tasks created: N (list task IDs and titles)
- Sources at latest / no relevant updates: list names
- Sources unreachable: list names (flag for manual review)

## Quality Gates

- Every source in `docs/sources/overview.md` must be checked — no skipping, no sampling
- Changes must be analyzed against our **actual usage** (the "Where Used" column), not just summarized generically
- Tasks must include specific references (commit hash, release version, documentation section)
- Do not create tasks for upstream changes that don't affect our adopted patterns
- If a source URL is dead or unreachable, note it in the report and create a task to update or remove the source entry
- Newly discovered sources (found while checking existing ones) should be evaluated and added to `docs/sources/overview.md` if adopted

[[2026-03-09]] Mon 17:04
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| Phase/Gate | Assessment | Status |
|------------|------------|--------|
| Phase 1: Inventory | Clear  reads `docs/sources/overview.md`, groups by section | PASS |
| Phase 2: Check for Updates | Clear protocol per source type (GitHub/PyPI/article/paper), recording template provided | PASS |
| Phase 3: Analyze Changes | 5-step analysis with 4-level rating scale (skip/nice-to-have/important/needed) | PASS |
| Phase 4: Create Tasks | Dupe check, ideation status, specific tag/priority format, date updates | PASS |
| Phase 5: Report | Summary template with 6 metrics | PASS |
| Quality Gates | 6 verifiable rules  no sampling, actual-usage analysis, specific references, dead URL handling | PASS |
| Execution Protocol | Orchestrator spawns subtask, subtask flows through pipeline, parent updated on completion | PASS |

### Architecture Notes
- Recurring SOP template task  no code implementation, no TDD needed
- Follows same pattern as sibling SOPs #578 (dependency audit) and #579 (project audit)
- File path `docs/sources/overview.md` verified correct (`docs/sources/` directory contains `overview.md`)
- Fixed one abbreviated reference (line 43: `sources.md` -> `docs/sources/overview.md`)
- Source file has ~35 entries across 10 sections  manageable per-run scope

### Changes Made
- Fixed abbreviated path reference on line 43
- Moved to todo

### Dependencies
- None required  standalone recurring SOP

[[2026-03-09]] Mon 17:04
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| Phase/Gate | Assessment | Status |
|------------|------------|--------|
| Phase 1: Inventory | Clear  reads `docs/sources/overview.md`, groups by section | PASS |
| Phase 2: Check for Updates | Clear protocol per source type (GitHub/PyPI/article/paper), recording template provided | PASS |
| Phase 3: Analyze Changes | 5-step analysis with 4-level rating scale (skip/nice-to-have/important/needed) | PASS |
| Phase 4: Create Tasks | Dupe check, ideation status, specific tag/priority format, date updates | PASS |
| Phase 5: Report | Summary template with 6 metrics | PASS |
| Quality Gates | 6 verifiable rules  no sampling, actual-usage analysis, specific references, dead URL handling | PASS |
| Execution Protocol | Orchestrator spawns subtask, subtask flows through pipeline, parent updated on completion | PASS |

### Architecture Notes
- Recurring SOP template task  no code implementation, no TDD needed
- Follows same pattern as sibling SOPs #578 (dependency audit) and #579 (project audit)
- File path `docs/sources/overview.md` verified correct (`docs/sources/` directory contains `overview.md`)
- Fixed one abbreviated reference (line 43: `sources.md` -> `docs/sources/overview.md`)
- Source file has ~35 entries across 10 sections  manageable per-run scope

### Changes Made
- Fixed abbreviated path reference on line 43
- Moved to todo

### Dependencies
- None required  standalone recurring SOP

[[2026-03-09]] Mon 17:27
## Test-Writer Notes
- Non-implementation task (tagged recurring, sop)  no tests applicable.
- Architecture review confirms: 'no code implementation, no TDD needed'
- Passing through to builder.

[[2026-03-09]] Mon 17:44
## Builder Notes
- Non-implementation task: recurring SOP template (tagged recurring, sop)
- Files changed: none
- Tests: N/A (test-writer confirmed no tests applicable)
- Lint: N/A (no code changes)
- Verification: docs/sources/overview.md exists with ~35 entries across 10+ sections. Execution protocol, 5 SOP phases, and 6 quality gates are fully specified in task body.
- The SOP defines a recurring audit process. Actual first-run execution happens when the orchestrator spawns a subtask per the Execution Protocol.
- Architecture review: APPROVED (no code, matches sibling SOPs #578, #579)

[[2026-03-09]] Mon 18:09
## Review Evidence (Reviewer)
Verdict: PASS confidence .93
See docs/scratch/577-reviewer.md for full evidence.
