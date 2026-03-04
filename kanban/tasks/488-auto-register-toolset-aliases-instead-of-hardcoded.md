---
id: 488
title: Auto-register toolset aliases instead of hardcoded map
status: ideation
priority: important
created: 2026-03-04T07:38:04.6142498+01:00
updated: 2026-03-04T07:38:04.6142498+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-15/INT-12: build_agent_registry() maintains hardcoded _aliases dict. Adding toolsets requires manual update. Missing: bookmark, visual_feedback, knowledge_source, project. Use class attribute or decorator for self-registration. AC: alias map derived automatically, all toolsets discoverable. See docs/architecture-audit.md, docs/integration-audit.md.
