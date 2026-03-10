---
id: 705
title: Audit global vs scoped instruction file ratio
status: backlog
priority: nice-to-have
created: 2026-03-09T05:12:29.139761+01:00
updated: 2026-03-10T00:59:01.2085772+01:00
started: 2026-03-10T00:53:14.5059268+01:00
tags:
    - phase-research
    - scope:core
    - docs
claimed_by: researcher
claimed_at: 2026-03-10T00:59:01.2085772+01:00
class: standard
---

Stripe avoids global agent rules to save context window space. Audit OwlBear's .instructions.md files to check if any global rules (applyTo: '**') could be scoped more narrowly.\n\nAC:\n- [ ] List all .instructions.md files and their applyTo patterns\n- [ ] Identify any with applyTo: '**' that could be narrowed\n- [ ] Propose scoping changes if any found\n\nSee docs/stripe-minions-research.md S3c for rationale.

## Research
