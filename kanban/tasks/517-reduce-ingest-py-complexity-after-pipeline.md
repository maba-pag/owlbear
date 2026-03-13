---
id: 517
title: Reduce ingest.py complexity after pipeline refactor
status: todo
priority: important
created: 2026-03-04T07:38:27.4728203+01:00
updated: 2026-03-10T19:04:33.4444497+01:00
started: 2026-03-06T23:58:22.1903475+01:00
tags:
    - audit
    - modularity
    - knowledge
blocked: true
block_reason: 'Review FAIL: code never committed to git + test API mismatch (inter_doc_builder vs enricher)'
class: standard
---

SUPERSEDED: Split into #671 (DocumentStore extraction), #672 (GraphEnricher extraction), #673 (re-exports), #674 (tests). Original task was an umbrella covering 3 extraction operations plus re-exports -- not atomic. See docs/ingest-complexity-reduction-research.md for full research.

[[2026-03-10]] Tue 04:29
## Audit
### Task Type
Superseded umbrella task -- split into #671 (DocumentStore), #672 (GraphEnricher), #673 (re-exports), #674 (tests). All 4 subtasks show status: archived.

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Properly decomposed into atomic tasks | 4 subtasks created with clear AC, dependency graph, correct priority | PASS |
| Research doc exists | docs/ingest-complexity-reduction-research.md present, complete | PASS |
| Subtasks completed (all archived) | Board shows #671-674 all archived | PASS |
| Code committed | document_store.py + enrichment.py NEVER committed (git log --all shows zero commits). ingest.py modified but unstaged. | **FAIL** |
| Tests passing | 9 tests in test_inter_doc_pipeline_integration.py FAIL: old API `inter_doc_builder` kwarg not updated to `enricher` | **FAIL** |

### Test Results
- Full suite (--ignore=test_daemon.py): 3825 passed, 29 failed, 48 errors
- Failures directly related to #517 refactor: 9 in test_inter_doc_pipeline_integration.py
  - TypeError: IngestPipeline.__init__() got unexpected keyword argument 'inter_doc_builder'
  - AttributeError: 'IngestPipeline' object has no attribute '_inter_doc_builder'
  - AssertionError: 'inter_doc_builder' not in call kwargs (now 'enricher')
- Other failures: pre-existing (Copilot token, bootstrap module attrs, httpx timeouts)

### Ruff
All checks passed on refactored files.

### Git Status (critical)
- `src/owlbear/memory/knowledge/document_store.py` -- UNTRACKED (never committed on any branch)
- `src/owlbear/memory/knowledge/enrichment.py` -- UNTRACKED (never committed on any branch)
- `src/owlbear/memory/knowledge/ingest.py` -- modified, unstaged
- `src/owlbear/memory/knowledge/__init__.py` -- modified, unstaged
- `tests/test_inter_doc_pipeline_integration.py` -- modified, unstaged

### Root Cause
Subtasks #671-674 were archived without committing code. Previous auditors verified code on disk but did not check git status. The inter_doc_pipeline_integration tests reference the pre-refactor API (`inter_doc_builder` kwarg) instead of the new `enricher` parameter.

### Confidence: .65
### Action: REJECT to review

[[2026-03-10]] Tue 19:04
## Review Evidence (reviewer, 2026-03-10)

### Test Results
- pytest tests/test_inter_doc_pipeline_integration.py: 1 tested, 1 FAILED (stopped at first)
- TypeError: IngestPipeline.__init__() got unexpected keyword argument 'inter_doc_builder'
- Tests reference old API (inter_doc_builder) but implementation uses new param (enricher)

### Lint Results
- ruff: All checks passed on ingest.py, document_store.py, enrichment.py, __init__.py, test file

### Git Status (CRITICAL)
- document_store.py: UNTRACKED (never committed on any branch)
- enrichment.py: UNTRACKED (never committed on any branch)
- ingest.py, __init__.py, test file: modified but UNSTAGED
- Subtasks #671-674 all marked archived, but code never reached version control

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| DocumentStore extracted | document_store.py exists on disk but untracked in git | FAIL |
| GraphEnricher extracted | enrichment.py exists on disk but untracked in git | FAIL |
| Re-exports updated | __init__.py modified but unstaged | FAIL |
| Tests pass | test fails: old API kwarg inter_doc_builder vs new enricher | FAIL |
| Code committed | Zero commits on any branch for new files | FAIL |

### Root Cause
4 subtasks were marked archived without committing any code. Tests still reference pre-refactor API. Prior audit identified same issues -- nothing remediated.

### Verdict: FAIL
Confidence: .30

### Rejection Table
| Gap | Required Fix |
|-----|-------------|
| Code never committed | git add + commit all new/modified files |
| Test API mismatch | Update test: inter_doc_builder -> enricher |
| Subtasks archived prematurely | Re-open subtasks or create new fix task |
