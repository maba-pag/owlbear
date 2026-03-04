---
id: 577
title: 'Recurring: Source inspiration audit (every 3 days)'
status: backlog
priority: important
created: 2026-03-04T08:03:33.1356117+01:00
updated: 2026-03-04T08:03:33.1356117+01:00
tags:
    - recurring
    - sop
class: standard
---

## Purpose

Track upstream changes in all sources used as inspiration (listed in `docs/sources.md`). When a source has been updated since our last check, analyze the changes and determine if they offer improvements worth adopting.

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

1. Read `docs/sources.md` in full
2. For each source entry, note: name, URL, what was taken, where used, date adopted
3. Group sources by section/research topic for systematic checking

### Phase 2: Check for Updates

For each source:

1. If it's a **GitHub repo**: check commits, releases, and tags since the date in sources.md
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
3. Update the `Date` column in `docs/sources.md` for all checked sources (even those with no relevant changes — the date records when we last verified)

### Phase 5: Report

Append a summary to the subtask body:

- Sources checked: N (grouped by section)
- Sources with updates: N
- Sources with relevant updates: N
- Tasks created: N (list task IDs and titles)
- Sources at latest / no relevant updates: list names
- Sources unreachable: list names (flag for manual review)

## Quality Gates

- Every source in `docs/sources.md` must be checked — no skipping, no sampling
- Changes must be analyzed against our **actual usage** (the "Where Used" column), not just summarized generically
- Tasks must include specific references (commit hash, release version, documentation section)
- Do not create tasks for upstream changes that don't affect our adopted patterns
- If a source URL is dead or unreachable, note it in the report and create a task to update or remove the source entry
- Newly discovered sources (found while checking existing ones) should be evaluated and added to `docs/sources.md` if adopted
