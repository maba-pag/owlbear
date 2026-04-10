---
id: 6
title: 'P1-06: Create pyproject.toml'
status: archived
priority: critical
created: 2026-02-24T15:04:11.7404125+01:00
updated: 2026-02-27T09:59:55.0791109+01:00
started: 2026-02-24T15:16:56.4856862+01:00
completed: 2026-02-27T09:59:55.0791109+01:00
tags:
    - phase-1
    - tooling
    - config
class: standard
---

## Acceptance Criteria
- Create pyproject.toml at project root with:
  - [build-system]: requires hatchling, build-backend = hatchling.build
  - [project]: name = owlbear, version = 0.1.0, requires-python >= 3.12
  - [project.scripts]: bearclaw = bearclaw.cli:app
  - [project.dependencies]: typer>=0.15.0, httpx>=0.28.0, openai>=1.60.0, pydantic>=2.10.0, pydantic-ai>=0.1.0, pydantic-settings>=2.7.0, tenacity>=9.0.0, truststore>=0.10.0
  - [project.optional-dependencies] dev: pytest>=8.0, pytest-asyncio>=0.25.0, pytest-cov>=6.0, ruff>=0.9.0, bandit>=1.9.0, pre-commit>=4.0
  - [tool.ruff]: target-version = py312, line-length = 100, src = [src]
  - [tool.ruff.lint]: select = [ALL], ignore = [D, ANN101, ANN102, COM812, ISC001] (adjust as needed for practical linting)
  - [tool.ruff.format]: quote-style = double
  - [tool.pytest.ini_options]: testpaths = [tests], markers including 'api: marks tests requiring live API' and 'slow: marks slow tests'
  - [tool.bandit]: targets = [src/]
  - [tool.hatch.build.targets.wheel]: packages = [src/owlbear, src/bearclaw]
- Use src layout: packages under src/owlbear/ and src/bearclaw/

## Files to Create
- pyproject.toml

## Verification
- uv pip compile pyproject.toml succeeds (valid dependency spec)
- toml parses without errors
- ruff, pytest, bandit sections are present and valid
