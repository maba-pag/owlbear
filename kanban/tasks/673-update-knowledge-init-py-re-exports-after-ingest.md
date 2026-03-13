---
id: 673
title: Update knowledge __init__.py re-exports after ingest split
status: archived
priority: important
created: 2026-03-08T03:00:21.137072+01:00
updated: 2026-03-09T16:17:18.9172278+01:00
started: 2026-03-08T05:52:54.9530723+01:00
completed: 2026-03-09T16:17:18.9172278+01:00
tags:
    - modularity
    - knowledge
depends_on:
    - 672
class: standard
---

After #671 and #672 complete, update src/owlbear/memory/knowledge/__init__.py to re-export DocumentStore, GraphEnricher, DocumentStatus, compute_content_hash from their new modules. AC: (1) __init__.py exports DocumentStore from document_store. (2) __init__.py exports GraphEnricher from enrichment. (3) __init__.py exports DocumentStatus and compute_content_hash from document_store. (4) All external import paths (bootstrap.py, tests, etc.) work without changes to their import statements. (5) Ruff clean. See docs/research/ingest-complexity-reduction.md.

[[2026-03-09]] Mon 16:17
## Audit
### AC Verification
| AC | Evidence | Status |
|---|----------|--------|
| (1) exports DocumentStore from document_store | __init__.py L9-13 import + __all__ | PASS |
| (2) exports GraphEnricher from enrichment | __init__.py L16 import + __all__ | PASS |
| (3) exports DocumentStatus & compute_content_hash from document_store | __init__.py L9-13 import + __all__ | PASS |
| (4) External import paths work | bootstrap/knowledge.py L62 uses package-level imports; 62 knowledge tests pass; 1271/1271 suite pass (1 pre-existing slack_sdk failure unrelated) | PASS |
| (5) Ruff clean | ruff check on all 3 files: All checks passed | PASS |

### Test Results
- pytest: 1271 passed, 1 failed (pre-existing slack_sdk env issue), 20 skipped
- ruff: All checks passed

### Confidence: .97
### Action: archive
