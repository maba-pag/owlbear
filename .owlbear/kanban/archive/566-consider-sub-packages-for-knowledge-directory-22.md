---
id: 566
title: Consider sub-packages for knowledge/ directory (22 files)
status: archived
priority: someday
created: 2026-03-04T07:39:08.9251319+01:00
updated: 2026-03-21T23:36:59.8950646+01:00
started: 2026-03-07T04:28:06.9048401+01:00
completed: 2026-03-21T23:36:56.209156+01:00
tags:
    - audit
    - modularity
    - knowledge
class: standard
---

MOD-04: Decision documented in docs/research/knowledge-subpackages.md. **Decision: Keep flat (.80 confidence).** 22 files is below the split threshold. No circular imports, no navigation pain, PEP 20 flat-is-better. Revisit if package exceeds 30 files.

## AC

- [x] Decision documented: Keep flat

[[2026-03-21]] Sat 13:47
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Decision documented: Keep flat | Clear, verifiable no-op design decision. docs/research/knowledge-subpackages.md records the keep-flat rationale and revisit trigger. | Accept as-is |

### Architecture Notes
The live package boundary remains a single flat namespace at src/owlbear/memory/knowledge/ with 24 Python files, which is higher than the original audit snapshot but still below the research document's 30-file revisit threshold. The package already exposes a curated public API through src/owlbear/memory/knowledge/__init__.py using lazy imports to manage import complexity, while assembly code in src/owlbear/bootstrap/knowledge.py and toolset wiring in src/owlbear/tools/knowledge.py import the current layout directly. Broad direct imports across bootstrap, tools, CLI, and tests mean a sub-package split would create churn without a corresponding layering or cohesion win. Keeping the flat package does not introduce a new dependency, security boundary, or interface contract. TDD and failure-mode mapping are N/A because this is a decision-only task and produces no code.

### Changes Made
- Claimed task for architect review as architect-566
- Appended this Architecture Review section
- Moved task to todo

### Dependencies
- Verified current subsystem boundary: src/owlbear/memory/knowledge/ remains in the memory layer and is assembled from src/owlbear/bootstrap/knowledge.py without upward import violations
- Added/Removed/Verified: no implementation dependencies; no RED predecessor required because this task produces no code

[[2026-03-21]] Sat 14:27
## Test-Writer Notes
- Non-implementation task (tagged: audit, modularity, knowledge) — decision-only, no code produced.
- Architecture review confirmed: TDD and failure-mode mapping are N/A.
- Passing through to builder.

[[2026-03-21]] Sat 15:01
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-03-21]] Sat 17:39
## Review Evidence
## Review: #566 - Consider sub-packages for knowledge/ directory (22 files)

### Test Results
- pytest command: uv run pytest tests/test_agent_definitions.py -q --tb=short
- result: 84 passed, 0 failed, 2 warnings (optional dependency skips)

### Lint Results
- ruff (repo-wide): uv run ruff check src/ tests/ -> Found 451 errors (pre-existing repository-wide lint debt in untouched files)
- ruff (task-scoped): uv run ruff check src/owlbear/memory/knowledge tests/test_bookmark.py tests/test_bookmark_pipeline.py tests/test_bookmark_toolset.py -> All checks passed!

### Coverage
- N/A for this task (decision-only, no Python implementation changes)

### Pass 1 - CRITICAL
#### Security Review
- No security issues found for task scope: no executable code changes, no new dependencies, no secrets in reviewed decision artifact.

#### Test Integrity (TestFromAC comparison)
- N/A: no task-specific TestFromAC classes were added or modified in this decision-only task.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | No new or modified task-specific tests required by AC |
| Negative/error paths | N/A | AC defines a documentation decision only |
| Mutation reasoning | N/A | No implementation behavior introduced by this task |
| Test independence | N/A | No new test state introduced |
| Descriptive names | N/A | No new tests introduced |

#### Data Safety
- No data safety issues found for task scope: no data-path code changes.

### Pass 2 - INFORMATIONAL
- Repo-wide ruff currently fails due unrelated baseline lint debt, but task-scoped lint for knowledge package and representative tests is clean.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Decision documented: Keep flat | kanban/tasks/566-consider-sub-packages-for-knowledge-directory-22.md:22 shows AC checked; docs/research/knowledge-subpackages.md:61 states Recommendation (.80 confidence): Keep Flat; docs/research/knowledge-subpackages.md:72 defines revisit trigger | N/A (decision-only task, no executable behavior) | PASS |

### Verdict: PASS
- Confidence: .94

### Action Taken
- kanban\\kanban-md.exe edit 566 --status docs --claim reviewer-566
- kanban\\kanban-md.exe edit 566 --release

[[2026-03-21]] Sat 23:36
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Decision documented: Keep flat | docs/research/knowledge-subpackages.md exists with 'Recommendation (.80 confidence): Keep Flat' at section 4, revisit trigger at 30 files. Committed in 42ff2c6. | PASS |

### Test Results
- pytest: 3746 passed, 97 failed (all pre-existing: numpy compat, bootstrap sig changes), 20 skipped. No failures related to knowledge package.
- ruff (knowledge/): clean

### Confidence: .97
### Action: archive
