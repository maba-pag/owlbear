---
id: 646
title: Fix pytest-cov + pydantic v2.12 RootModel MRO crash
status: archived
priority: important
created: 2026-03-07T16:49:17.770134+01:00
updated: 2026-03-07T18:08:33.2348396+01:00
started: 2026-03-07T17:37:35.9464602+01:00
completed: 2026-03-07T18:08:33.2348396+01:00
tags:
    - bugfix
    - test
    - config
    - deps
class: standard
---

## Problem
pytest-cov's import instrumentation triggers a ValueError in pydantic v2.12.5 when running --cov with dotted module names:

ValueError: tuple.index(x): x not in tuple

Root cause: coverage.py's SysModuleSaver probes dotted module names via importlib.find_spec(), importing pydantic modules. After probing, it restores sys.modules, but pydantic's @functools.cache retains stale BaseModel references. Re-import creates new BaseModel with different id() -> mro.index() crash.

## Fix
Use directory paths instead of dotted module names with --cov:
- BAD:  --cov=owlbear.tools.diagram.toolset
- GOOD: --cov=src/owlbear/tools/diagram

See docs/pytest-cov-pydantic-mro-crash-research.md

## Acceptance Criteria
- [ ] code-review SKILL.md uses --cov=src/owlbear/{path} not --cov=owlbear.{module}
- [ ] tdd-workflow SKILL.md uses --cov=src/owlbear/{path} not --cov=owlbear.{module}
- [ ] uv run pytest tests/test_diagram_toolset.py --cov=src/owlbear/tools/diagram --cov-report=term-missing -q passes
- [ ] No regression in plain pytest runs
