---
id: 611
title: Create dev branch and push to remote
status: backlog
priority: needed
created: 2026-04-04T21:54:56.0860979+02:00
updated: 2026-04-04T21:54:56.0860979+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
parent: 610
class: standard
---

## Summary

Create dev branch from current main. Push to remote. Set up local clone workflow: owlbear/ (main for projects) and owlbear-dev/ (dev for work).

## Acceptance Criteria

- [ ] AC1: dev branch created from current HEAD of main
- [ ] AC2: dev branch pushed to origin
- [ ] AC3: GitHub default branch remains main (consumer-facing, for git clone)
- [ ] AC4: All future development happens on dev or feature branches off dev
- [ ] AC5: Branch protection on main: only sync workflow can push (optional, can be done later)

## Notes

After this task, main and dev are identical. They diverge after the five-tier restructure (#598) lands on dev and the first sync runs.
