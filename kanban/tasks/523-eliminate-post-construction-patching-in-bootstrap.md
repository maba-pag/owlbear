---
id: 523
title: Eliminate post-construction patching in bootstrap
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:31.3955566+01:00
updated: 2026-03-04T07:38:31.3955566+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-14: bootstrap creates placeholder for ProjectToolset, patches real agent after construction. agent._deps.agent_registry set after agent construction. Two-phase init creates temporal coupling. Use lazy property or reorder construction. AC: no post-construction patching. See docs/architecture-audit.md.
