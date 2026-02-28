---
id: 231
title: Test Co-authored-by trailer in git_commit
status: archived
priority: nice-to-have
created: 2026-02-28T01:19:03.3365835+01:00
updated: 2026-02-28T23:54:12.3078825+01:00
started: 2026-02-28T01:19:16.596525+01:00
completed: 2026-02-28T23:54:12.3078825+01:00
tags:
    - github
    - tooling
    - test
class: standard
---

TDD test task for #219. File: tests/test_git_local.py (extend existing).

AC:
- [ ] Test git_commit('msg') appends Co-authored-by: OwlBear <owlbear@noreply> trailer
- [ ] Test the -m argument passed to git subprocess is: 'msg\n\nCo-authored-by: OwlBear <owlbear@noreply>'
- [ ] Test existing message with trailing newlines handled correctly
- [ ] Mock subprocess — verify exact args passed to git commit

File: tests/test_git_local.py
