---
id: 979
title: Wire two-tier NotificationHook instances in build_hooks
status: archived
priority: important
created: 2026-03-24T03:05:32.5411145+01:00
updated: 2026-03-26T03:06:01.6174276+01:00
tags:
    - hooks
    - bootstrap
    - scope:core
    - type:build
parent: 952
depends_on:
    - 977
    - 963
class: standard
---

See docs/research/priority-routed-notifications.md. AC: build_hooks() creates two NotificationHook instances (urgent tier with slack+sound+bell, info tier with bell only) using the new OwlBearSettings fields; events configured under hook_reactions with notify action are excluded from both tiers to avoid double-delivery (#963); tested with both tiers firing independently.
