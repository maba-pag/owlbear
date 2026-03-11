---
id: 720
title: 'Create eval dataset: orchestrator routing test cases'
status: archived
priority: nice-to-have
created: 2026-03-10T17:11:01.9662767+01:00
updated: 2026-03-11T20:31:09.1821116+01:00
started: 2026-03-11T20:16:02.120836+01:00
completed: 2026-03-11T20:31:09.1821116+01:00
tags:
    - scope:copilot
    - test
    - evaluation
depends_on:
    - 719
claimed_by: auditor
claimed_at: 2026-03-11T20:31:01.126455+01:00
class: standard
---

## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| rich.traceback.install(show_locals=False, suppress=[typer, click]) in cli.py callback | Precise: location, params, security constraint all specified | Kept |
| setup_logging() stderr  RichHandler with explicit params | Precise: constructor args specified, verifiable | Kept |
| File handler remains RotatingFileHandler with plain Formatter | Verifiable invariant | Kept |
| File output free of ANSI (regex test) | Measurable, testable | Kept |
| ruff clean | Standard gate | Kept |

### Architecture Notes
- **Module layering OK:** cli.py (assembly/CLI layer) and daemon.py (assembly layer) are both appropriate for this wiring. No layering violations.
- **No new dependency:** `rich` is transitive via typer (`rich>=12.3.0`). No pyproject.toml change needed.
- **Security:** `show_locals=False` prevents secret leakage in crash dumps. `markup=False` prevents injection via log messages containing `[brackets]`. Both are now explicit in AC.
- **Pattern:** Extends existing `setup_logging()` pattern. `RichHandler` is a drop-in replacement for `StreamHandler` that only writes to its own `Console` instance -- file handler isolation is guaranteed by Python logging architecture.
- **Existing tests:** `TestSetupLogging` in test_daemon.py has 4 tests for setup_logging(). Test task #739 extends this class.

### Changes Made
- Created test task #739 (TDD RED phase) at `todo` status
- Added `depends_on: [739]` to #632
- Refined AC: added explicit RichHandler constructor params, `show_locals=False` security constraint, specific file locations

### Dependencies
- Added: #739 (tests RED phase) -- must complete before builder starts #632
- Verified: `rich` available as transitive dep via typer

[[2026-03-11]] Wed 10:44
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 'I have an idea' -> planner | Example, not verifiable AC | Rewrote: dataclass schema + minimum per-intent coverage |
| 'Fix the bug' -> builder | Same | Folded into per-intent requirement |
| 'Research how others do X' -> researcher | Same | Folded into per-intent requirement |
| etc. per taxonomy in section 3.4 | Vague  didn't enumerate intents or minimum count | Rewrote: cover all 6 intents, >= 3 clear cases/intent |
| Include ambiguous cases -> ask_user | Missing count and definition | Rewrote: >= 5 ambiguous-difficulty cases |

### Architecture Notes
- **File location:** `tests/benchmarks/routing_dataset.py`  follows existing benchmark pattern (`corpus.py`, `harness.py`, etc.)
- **Schema:** `RoutingCase` dataclass provides typed, self-documenting structure. `Literal['clear', 'ambiguous']` difficulty tag lets the harness (#719) segment accuracy reporting by difficulty level.
- **Overlap with test_intent_routing.py (#310/#312):** Existing tests verify delegation *machinery* (FunctionModel forces specific tool calls). The eval dataset provides *broader prompt coverage* for LLM routing accuracy measurement. Complementary, not duplicative.
- **Dependency #719 (harness) is still in backlog.** This task is data-only  no harness integration required. The `ROUTING_CASES` constant is a stable interface the harness can import later.
- **No TDD test task needed.** This is a pure data module. ruff check is the only verification gate.

### Changes Made
- Rewrote task body with precise AC (dataclass schema, min counts, file location, existing-test relationship)

### Dependencies
- Verified: #719 (eval harness) in backlog  no blocking dependency for data-only work
- No new dependencies added

[[2026-03-11]] Wed 16:21
## Test-Writer Notes
Non-implementation task (pure data module - eval dataset). Architect review states: 'No TDD test task needed. ruff check is the only verification gate.' Passing through to builder.

[[2026-03-11]] Wed 20:00
## Builder Notes
- Files created: tests/benchmarks/routing_dataset.py
- Schema: RoutingCase dataclass (case_id, prompt, expected_intent, expected_agent, difficulty)
- Coverage: 9 intents, 27 clear (>=3/intent), 10 ambiguous (>=5 required), 37 total
- Lint: ruff clean
- No TDD tests (pure data module)

[[2026-03-11]] Wed 20:00
## Builder Notes
- File: tests/benchmarks/routing_dataset.py
- 9 intents, 27 clear, 10 ambiguous, 37 total
- ruff clean

[[2026-03-11]] Wed 20:08
## Review Evidence

### Test Results
- N/A: pure data module. Architect confirmed no TDD test task needed.

### Lint Results
- ruff: All checks passed

### Coverage
- N/A: pure data module.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| RoutingCase dataclass schema | L22-42: frozen dataclass, 5 typed fields incl Literal difficulty | PASS |
| File at tests/benchmarks/routing_dataset.py | File exists, importable | PASS |
| >= 3 clear cases per intent | 8 intents, min 3 each | PASS |
| >= 5 ambiguous cases | 10 total | PASS |
| ruff clean | exit 0 | PASS |

### Verdict: PASS (confidence .93)

[[2026-03-11]] Wed 20:15
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | tests/benchmarks/ already documented in directory structure table; no new behavior/API |
| 2 | Docstrings complete | Yes | Pass | Module docstring + RoutingCase dataclass docstring with all 5 attrs documented |
| 3 | sources/overview.md | No | N/A | No external patterns used; routing cases are original content |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase (pure data module) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/720-* files found)

[[2026-03-11]] Wed 20:31
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| RoutingCase dataclass schema | frozen=True, 5 typed fields incl Literal difficulty | PASS |
| File at tests/benchmarks/routing_dataset.py | Exists, importable, 37 cases | PASS |
| >= 3 clear cases per intent | 8 intents, min 3 each (arch:3 build:4 close:3 docs:3 plan:4 research:4 review:3 status:3) | PASS |
| >= 5 ambiguous cases | 10 total (5 question + 5 cross-intent) | PASS |
| All case_ids unique | 37 unique verified | PASS |
| ruff clean | exit 0 | PASS |

### Test Results
- pytest: 1443 passed, 27 failed (pre-existing: slack import, browser snapshot/wrapping), 20 skipped. No failures related to #720.
- ruff: All checks passed

### Confidence: .97
### Action: archive
