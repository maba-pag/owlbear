---
id: 1
title: 'P1-01: Rename Graphicator to OwlBear in copilot-instructions.md'
status: done
priority: high
created: 2026-02-24T15:02:41.7257529+01:00
updated: 2026-02-26T16:34:41.797539+01:00
started: 2026-02-24T15:16:56.3253936+01:00
completed: 2026-02-26T16:34:41.797539+01:00
tags:
    - phase-1
    - config
    - rename
class: standard
---

## Acceptance Criteria
- Replace title 'Tool: Graphicator' with 'Tool: OwlBear' in .github/copilot-instructions.md
- Replace ALL occurrences of 'graphicator' (case-insensitive) with 'owlbear' in the same file
- Do NOT fill in the TODO placeholders (separate tasks handle that)
- Do NOT change any other files

## Files to Edit
- .github/copilot-instructions.md

## Verification
- grep -i 'graphicator' .github/copilot-instructions.md returns zero results
- The file still parses correctly as valid Markdown
- No unrelated content was changed
