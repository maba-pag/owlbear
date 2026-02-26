---
id: 20
title: 'P3-05: Create Stop test verification hook'
status: ideation
priority: medium
created: 2026-02-24T15:12:24.8904478+01:00
updated: 2026-02-26T18:53:00.5602742+01:00
tags:
    - phase-3
    - hooks
    - test
depends_on:
    - 16
    - 11
class: standard
---

AC: Create .github/hooks/stop-verify.json. Hook fires on Stop event. Runs 'uv run pytest tests/ -m not api --tb=short -q'. If tests fail (exit code != 0), exit 2 to block session end and return test failure output as reason. If tests pass, exit 0 to allow. Backing script runs pytest and checks return code. If VS Code hooks not stable, comment out with explanation. Files: .github/hooks/stop-verify.json + backing script.
