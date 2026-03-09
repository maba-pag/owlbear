---
id: 658
title: 'Improve test coverage: bookmark_pipeline.py (85%)'
status: archived
priority: needed
created: 2026-03-08T01:59:02.9744822+01:00
updated: 2026-03-09T00:21:53.5331365+01:00
started: 2026-03-08T03:09:33.793629+01:00
completed: 2026-03-09T00:21:53.5331365+01:00
tags:
    - coverage-sprint
    - knowledge
    - test
class: standard
---

## Coverage Gap
Current: 85% (9 of 62 statements uncovered)
Missing lines: 190-200 (_default_web_read function - trafilatura import, retry-wrapped fetch, extract)

## Acceptance Criteria
- [ ] Coverage >= 95% for src/owlbear/memory/knowledge/bookmark_pipeline.py
- [ ] Tests cover: _default_web_read happy path (successful fetch + extract)
- [ ] Tests cover: _default_web_read with missing trafilatura (ImportError)
- [ ] Tests cover: _default_web_read with HTTP errors (retry behavior)
- [ ] All new tests pass, ruff clean

[[2026-03-08]] Sun 23:51
Wave 2, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 3, agent: auditor

[[2026-03-09]] Mon 00:21
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| Coverage >= 95% | 100% (62 stmts, 0 miss) via --cov | .98 |
| _default_web_read happy path | TestDefaultWebReadFetch.test_happy_path_returns_extracted_text, passing | .98 |
| _default_web_read ImportError | TestDefaultWebReadImportGuard (2 tests), passing | .98 |
| _default_web_read HTTP errors | TestDefaultWebReadFetch.test_http_error_propagates (500), passing | .95 |
| All tests pass, ruff clean | 21 passed; ruff All checks passed | .98 |

Overall: .97
