---
id: 468
title: Restrict token file permissions
status: archived
priority: needed
created: 2026-03-04T07:37:47.9515569+01:00
updated: 2026-03-06T19:28:16.0914237+01:00
started: 2026-03-06T10:20:47.0771327+01:00
completed: 2026-03-06T19:28:16.0914237+01:00
tags:
    - audit
    - security
    - auth
class: standard
---

SEC-03: save_token() writes copilot_token.json as plaintext with default permissions (0o644 on Unix). On multi-user systems, other users can read the OAuth token. Fix by using atomic os.open() with restricted mode.

## Acceptance Criteria

- [ ] save_token() creates/overwrites the token file using os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600) + os.fdopen() + f.write() instead of Path.write_text()
- [ ] Parent directory (~/.owlbear/) is created with mode 0o700 on Unix (os.makedirs with mode param or os.chmod after mkdir)
- [ ] On Windows, skip the os.open() approach  use Path.write_text() as before (os.open mode bits are ignored on Windows; parent dir ACL inheritance is sufficient)
- [ ] Platform branch: use sys.platform or os.name to decide Unix vs Windows path
- [ ] No new dependencies  stdlib only (os, stat, sys)
- [ ] Existing save_token() signature unchanged: (token_data: dict[str, Any], path: Path | None = None) -> None
- [ ] Existing load_token() and load_or_refresh_token() unchanged
- [ ] Test (Unix only, skip on Windows): after save_token(), stat.S_IMODE(os.stat(path).st_mode) == 0o600
- [ ] Test (Unix only): parent dir mode is 0o700 after save_token() creates it
- [ ] Test: round-trip saveload still works (existing test preserved)
- [ ] Test: parent directory creation still works (existing test preserved)
- [ ] ruff clean, all existing tests still pass

## Architecture Notes

- **Pattern:** Use os.open() for atomic file creation with permissions  no race window between create and chmod. This is the Ansible vault pattern.
- **File:** src/owlbear/auth/copilot.py  save_token() function (line ~185)
- **Tests:** tests/test_auth/test_copilot.py  TestTokenCaching class (line ~219)
- **No existing permission patterns** in codebase  this is the first. Future tasks can follow this precedent.
- **Scope:** ~10-15 LOC change in save_token() + ~20 LOC new tests. Do NOT refactor load_token or other functions.
