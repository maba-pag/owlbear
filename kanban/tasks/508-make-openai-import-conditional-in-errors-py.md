---
id: 508
title: Make openai import conditional in errors.py
status: ideation
priority: important
created: 2026-03-04T07:38:19.9842385+01:00
updated: 2026-03-04T07:38:19.9842385+01:00
tags:
    - audit
    - config
    - scope:core
class: standard
---

F-15: errors.py imports openai at module level. Any code importing classify_error requires openai installed, even CLI-only or knowledge-only usage. Move to TYPE_CHECKING block or try/except ImportError. AC: errors.py importable without openai. See docs/code-quality-audit.md.
