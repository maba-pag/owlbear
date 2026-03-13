---
id: 219
title: Add OwlBear Co-authored-by trailer to git_commit
status: archived
priority: nice-to-have
created: 2026-02-28T01:11:27.7375717+01:00
updated: 2026-02-28T23:54:03.380899+01:00
started: 2026-02-28T01:11:48.2980231+01:00
completed: 2026-02-28T23:54:03.380899+01:00
tags:
    - github
    - tooling
class: standard
---

Append Co-authored-by: OwlBear <owlbear@noreply> trailer to all commits made via git_commit tool.

File: src/owlbear/tools/git_local.py

AC:
- [ ] git_commit(message) appends trailer: message + '\n\nCo-authored-by: OwlBear <owlbear@noreply>'
- [ ] Trailer appended before passing to git commit -m
- [ ] Existing trailing whitespace/newlines in message stripped before appending
- [ ] ~5 LOC change in GitLocalToolset.git_commit
- [ ] No new dependencies

Depends on: #231 (test task)
See docs/research/github-bot-account.md
