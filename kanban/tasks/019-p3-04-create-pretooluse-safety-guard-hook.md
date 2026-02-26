---
id: 19
title: 'P3-04: Create PreToolUse safety guard hook'
status: ideation
priority: medium
created: 2026-02-24T15:11:32.1221629+01:00
updated: 2026-02-26T18:53:00.1425368+01:00
tags:
    - phase-3
    - hooks
depends_on:
    - 16
class: standard
---

AC: Create .github/hooks/pre-tool-use-safety.json. Hook fires on PreToolUse event. Blocks dangerous commands: rm -rf /, git push --force, pip install (without uv), format C:, del /s /q, any command with sudo rm. Exit code 2 to block, 0 to allow. Backing script parses tool input JSON from stdin, checks command against blocklist regex patterns. If VS Code hooks not stable, comment out with explanation. Files: .github/hooks/pre-tool-use-safety.json + backing script.
