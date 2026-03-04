---
id: 489
title: Fix NotificationHook signature mismatch
status: ideation
priority: important
created: 2026-03-04T07:38:05.373334+01:00
updated: 2026-03-04T07:38:05.373334+01:00
tags:
    - audit
    - bugfix
    - hooks
class: standard
---

ARC-09: NotificationHook.__call__ takes (self, event, data) but HookRegistry.emit invokes handlers with single data arg. Mismatch papered over by _make_handler() closure. Other hooks follow single-arg convention. AC: NotificationHook.__call__ takes (self, data) like all other hooks. See docs/architecture-audit.md.
