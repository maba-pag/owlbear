---
id: 146
title: Self-improvement pipeline — analytics to evaluation to human-gated proposals
status: ideation
priority: someday
created: 2026-02-27T14:59:42.7922645+01:00
updated: 2026-02-27T14:59:42.7922645+01:00
tags:
    - phase-12
    - agent
    - analytics
depends_on:
    - 142
class: standard
---

The 'agent improver' — but human-gated, never autonomous. Pipeline:
1. Collect: agent analytics (tool usage, errors, latency, task success/failure)
2. Evaluate: compare agent performance against quality criteria
3. Propose: generate improvement suggestions (prompt tweaks, tool changes, skill additions)
4. Review: present proposals to user via ask_user, never auto-apply
5. Apply: user-approved changes applied to agent definitions

This is the most dangerous feature — AI modifying its own instructions can degrade rapidly. The human gate is non-negotiable.
