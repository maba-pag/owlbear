---
id: 760
title: Add cookie-persistence profiles to BrowserManager
status: archived
priority: someday
created: 2026-03-12T12:45:27.2480844+01:00
updated: 2026-03-22T19:17:49.4588531+01:00
started: 2026-03-22T19:17:49.4588531+01:00
completed: 2026-03-22T19:17:49.4588531+01:00
tags:
    - browser
    - phase-4
blocked: true
block_reason: 'Superseded by archived #835; feature already implemented and audited'
class: standard
---

Pattern: save/restore cookies per named profile (~1KB each vs 100MB Chrome profiles). Inspired by botasaurus tiny_profile (see docs/research/botasaurus.md S4.6). AC:
- [ ] BrowserConfig gains optional profile_name field
- [ ] On context close, cookies saved to profiles/{name}.json
- [ ] On context open, cookies restored if profile exists
- [ ] Profile storage path configurable

[[2026-03-21]] Sat 06:40
## Architecture Review
**Verdict:** Refine

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| BrowserConfig gains optional profile_name field | Already implemented in src/owlbear/config.py and surfaced via src/owlbear/tools/browser/config.py; archived coverage exists in #835 | Treat #760 as a stale duplicate and do not route it to builder flow |
| On context close, cookies saved to profiles/{name}.json | Already implemented in src/owlbear/tools/browser/manager.py and verified by tests/test_browser_cookie_profiles.py under archived #835 | Treat #760 as a stale duplicate and do not route it to builder flow |
| On context open, cookies restored if profile exists | Already implemented in src/owlbear/tools/browser/manager.py and verified by tests/test_browser_cookie_profiles.py under archived #835 | Treat #760 as a stale duplicate and do not route it to builder flow |
| Profile storage path configurable | BrowserConfig.profile_dir already exists; bootstrap also pre-creates browser_profiles via sandbox_path in src/owlbear/bootstrap/toolsets.py. Archived #835 notes the default bootstrap path is pre-created but not additionally wired into settings.browser by default | Keep any bootstrap-default cleanup as a separate follow-up, not part of #760 |

### Architecture Notes
- Research source docs/research/botasaurus.md section 4.6 marked cookie profiles as nice-to-have; the current repo already contains the intended browser-domain contract.
- Current codebase evidence:
  - src/owlbear/config.py defines BrowserConfig.profile_name and BrowserConfig.profile_dir with a both-or-neither validator.
  - src/owlbear/tools/browser/config.py re-exports BrowserConfig for the browser package surface.
  - src/owlbear/tools/browser/manager.py already restores cookies on __aenter__ and saves them on __aexit__.
  - tests/test_browser_cookie_profiles.py covers config validation, save/restore, graceful degradation, atomic writes, no-profile defaults, no-cookie logging, and bootstrap path handling.
- TDD compliance already exists through archived task #835, which carries the RED notes, review evidence, audit trail, and builder/writer commits for this feature.
- Routing #760 to todo would duplicate already-audited browser work. If more work is desired later, open a new task scoped only to bootstrap default wiring cleanup rather than reusing #760.

### Changes Made
- Claimed #760 for architecture review.
- Compared the task AC against the live codebase, research doc, and archived sibling task #835.
- Appended this architecture review note.
- Blocked #760 as superseded by archived #835 and released the claim.

### Dependencies
- Verified: archived task #835 is the executable source of truth for the cookie-profile implementation, tests, review, and audit.
- Added/Removed/Verified: no new dependencies added.
