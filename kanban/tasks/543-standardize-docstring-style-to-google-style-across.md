---
id: 543
title: Standardize docstring style to Google-style across codebase
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:47.2416438+01:00
updated: 2026-03-07T00:49:27.5411404+01:00
started: 2026-03-07T00:45:02.850864+01:00
tags:
    - audit
    - docs
    - code-quality
class: standard
---

Research complete. See docs/docstring-style-research.md.

Findings:
- Google-style is 70%% of existing sections (113 Args: vs 46 Parameters)
- 20 files have numpy-style docstrings
- Recommendation (.90): Enable D2-D4 rules with convention=google, ignore D1xx
- With convention=google, only 103 violations (vs 283 without); 23 auto-fixable
- 3 follow-up tasks: enable ruff D rules, convert numpy files, enable D1xx later

AC: consistent style, ruff D rules enabled for chosen style.
