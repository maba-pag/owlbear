---
id: 564
title: Consider Hook protocol for automated event registration
status: ideation
priority: someday
created: 2026-03-04T07:39:07.0113635+01:00
updated: 2026-03-04T07:39:07.0113635+01:00
tags:
    - audit
    - dry
    - hooks
class: standard
---

DRY-12: Hook register() manually calls hooks.register(event, self.handle) in 9 classes. No shared protocol. Define Hook ABC with events: ClassVar and automated registration. Low priority -- current approach is explicit. AC: decision documented. See docs/software-design-audit.md.
