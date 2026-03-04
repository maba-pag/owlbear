---
id: 559
title: Add programmatic agent registration API
status: ideation
priority: someday
created: 2026-03-04T07:39:02.2025079+01:00
updated: 2026-03-04T07:39:02.2025079+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-16: AgentRegistry.scan() only supports file-based agent definitions (globs .md files). No register(defn) method for dynamic agents. Add register() alongside scan(). AC: both file and programmatic registration supported. See docs/architecture-audit.md.
