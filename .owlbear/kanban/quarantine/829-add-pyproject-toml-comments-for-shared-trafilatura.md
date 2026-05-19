---
id: 829
title: Add pyproject.toml comments for shared trafilatura dep
status: archived
priority: nice-to-have
created: 2026-03-15T12:52:28.8754961+01:00
updated: 2026-03-16T21:39:21.0180206+01:00
started: 2026-03-16T21:39:21.0180206+01:00
completed: 2026-03-16T21:39:21.0180206+01:00
tags:
    - config
    - deps
class: standard
---

Add inline comments to pyproject.toml explaining trafilatura duplication across crawl and search extras (intentional, per docs/research/consolidate-trafilatura-extras.md). Update content_extractor.py import guard to mention both --extra crawl and --extra search.

## AC

- [ ] pyproject.toml crawl and search lines have clarifying comments
- [ ] content_extractor.py ImportError message mentions both extras
- [ ] uv lock succeeds after changes

[[2026-03-15]] Sun 13:04

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| pyproject.toml crawl/search lines have clarifying comments | Clear, verifiable by reading file | Keep |
| content_extractor.py ImportError mentions both extras | Clear, verifiable  L73 currently says only crawl | Keep |
| uv lock succeeds after changes | Mechanical check, verifiable | Keep |

### Architecture Notes

- Comment/docs-only task, no behavior change. TDD not required (ImportError path is pragma: no cover, requires trafilatura uninstalled).
- Research doc (consolidate-trafilatura-extras.md) is thorough, prior art from httpx/pydantic supports keeping flat extras.
- content_extractor.py L73 currently: 'owlbear[crawl]'. Should become e.g. 'owlbear[crawl] or owlbear[search]'.
- #537 (backlog) will eventually centralize all trafilatura imports to content_extractor.py  this task is correctly independent of that.

### Changes Made

- Approved with no AC changes

### Dependencies

- None required. Independent of #537.

[[2026-03-15]] Sun 13:25

## Test-Writer Notes

- Non-implementation task (tagged config)  no tests applicable.
- AC covers pyproject.toml comments, ImportError message wording, and uv lock. All are config/docs changes, not testable behavior.
- Architecture review confirms: TDD not required (ImportError path is pragma: no cover).
- Passing through to builder.

[[2026-03-15]] Sun 13:56

## Builder Notes

- Files changed: pyproject.toml, src/owlbear/tools/browser/content_extractor.py
- Added inline comments to crawl/search extras explaining intentional trafilatura duplication
- Updated ImportError message to mention both --extra crawl and --extra search
- uv lock: resolved 427 packages, no errors
- ruff: All checks passed
- Commit: ab7ad69

[[2026-03-15]] Sun 13:56

## Builder Notes

[[2026-03-15]] Sun 13:56

- Files changed: pyproject.toml, src/owlbear/tools/browser/content_extractor.py
- Added inline comments to crawl/search extras explaining intentional trafilatura duplication
- Updated ImportError message to mention both --extra crawl and --extra search
- uv lock: resolved 427 packages, no errors
- ruff: All checks passed
- Commit: ab7ad69

[[2026-03-15]] Sun 14:09

## Review Evidence

### Test Results

- N/A: config/docs-only task, no behavioral changes, no test files.

### Lint Results

- ruff: All checks passed! (exit 0)

### Coverage

- N/A: no code behavior changed.

### Pass 1 - CRITICAL

#### Security Review

- No security issues. Comment-only TOML change, string message change in Python. No user input, no I/O, no serialization, no credentials.

#### Test Integrity

- No TestFromAC classes (config/docs task, TDD not required per architect).

#### Test Quality

- N/A: no tests for this task (correctly so per architect review).

#### Data Safety

- No data safety issues. No data handling changes.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| pyproject.toml crawl/search have comments | read_file L29-36: both extras have inline comments referencing docs/research/consolidate-trafilatura-extras.md | PASS |
| content_extractor.py ImportError mentions both extras | read_file L68-71: msg says 'uv sync --extra crawl or uv sync --extra search' | PASS |
| uv lock succeeds | uv lock resolved 427 packages, exit 0 | PASS |

### Verdict: PASS (confidence .95)

### Action: move to docs

-t

[[2026-03-16]] Mon 21:37

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| pyproject.toml crawl/search lines have clarifying comments | L32: shared with search comment; L37: shared with crawl comment  both reference docs/research/consolidate-trafilatura-extras.md | PASS |
| content_extractor.py ImportError mentions both extras | L70: uv sync --extra crawl  or  uv sync --extra search | PASS |
| uv lock succeeds | builder notes 427 packages resolved exit 0; uv.lock in commit ab7ad69 | PASS |

### Test Results

- pytest: N/A (config/docs-only task, no behavioral changes; architect confirmed TDD not required)
- ruff: clean (reviewer confirmed, exit 0)

### Commit

- ab7ad69: docs: add trafilatura duplication comments and update import guard (#829, builder)

### Confidence: 1.0

### Action: archive
