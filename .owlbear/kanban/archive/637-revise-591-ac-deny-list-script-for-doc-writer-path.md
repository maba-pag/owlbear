---
id: 637
title: 'Revise #591 AC: deny-list script for doc-writer path guard'
status: archived
priority: medium
created: 2026-04-06T01:22:50.5411623+02:00
updated: 2026-04-06T02:19:28.8775587+02:00
started: 2026-04-06T02:19:28.8775587+02:00
completed: 2026-04-06T02:19:28.8775587+02:00
tags:
    - scope:agents
    - hooks
    - type:build
depends_on:
    - 589
class: standard
---

## Context
Research for #591 found that reusing deny-src-writes.ps1 (allow-list for tests/ only) is infeasible for doc-writer. Doc-writer writes to README.md, .owlbear/research/, .owlbear/sources/, .github/, share/skills/, share/instructions/, and *.py docstrings — all of which would be blocked by the tests/-only allow-list.

See .owlbear/research/pretooluse-doc-writer-path-guard-591.md for full analysis.

## Revised Acceptance Criteria (replaces #591 AC)
1. Create `.owlbear/hooks/deny-code-writes.ps1` — PreToolUse hook using **deny-list** approach: normalizes `\` to `/`, extracts paths from `tool_input.filePath`, `tool_input.dirPath`, and `tool_input.replacements[*].filePath`; denies when ANY extracted path starts with `serve/`, `v1/`, `tests/`, `setup/`, `.owlbear/hooks/`, `.owlbear/scripts/`, or equals `conftest.py`
2. Write-tool gate: script checks paths only for `tool_name` in `{create_file, replace_string_in_file, multi_replace_string_in_file, create_directory, apply_patch}`; all other `tool_name` values return `{}`
3. Add PreToolUse hook to `share/agents/doc-writer.agent.md` frontmatter: `powershell -NoProfile -NonInteractive -File .owlbear/hooks/deny-code-writes.ps1`
4. Script returns `{}` for: non-write tools (per AC2), missing/empty paths, empty/missing `tool_name`, malformed stdin JSON
5. Agent file parses as valid YAML frontmatter
6. Script has maintenance comment header listing denied dirs and rationale
7. Depends on: #589 (deny-src-writes.ps1 as pattern reference)

## Known Limitations
- `run_in_terminal` bypasses PreToolUse hooks (terminal writes are opaque)
- `.py` docstring-vs-logic enforcement is instruction-based only — hooks cannot distinguish content changes
- Deny-list is not self-maintaining: new source dirs require manual update to script
- `apply_patch` tool_input schema for path extraction may differ — verify during implementation

[[2026-04-06]] Mon 01:40
## AC Amendments (from research validation)
Apply these 5 amendments to the AC above:

R1 - Expand deny-list (AC1): Add seed/, store/, share/agents/, .git/ to denied paths.
R2 - Add editFiles to write-tools (AC2): VS Code docs confirm editFiles is a real tool_name.
R3 - Add files[] extraction (AC1): Path extraction must also iterate tool_input.files[*].
R4 - Remove apply_patch schema unverified Known Limitation: Confirmed by #546 tests.
R5 - Add Known Limitation: editFiles files[] schema from VS Code docs - verify empirically.

## Research
- Research doc: .owlbear/research/deny-code-writes-ac-validation-637.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: AC sound with 5 amendments (confidence: .80)
- Follow-up tasks created: none needed
- Decision requests: none (T1)

## Challenge Results
- Challenger: proceed (confidence: .80)
- Key challenges: B1 share/agents/ self-modification, B3 editFiles gap, A1 .git/ escalation
- Researcher response: revised - incorporated all 3 into amendments R1-R3

[[2026-04-06]] Mon 01:41
AC validated with 5 amendments: R1 expand deny-list (+seed/ +store/ +share/agents/ +.git/), R2-R3 add editFiles to write-tools + files[] extraction, R4 resolve apply_patch schema, R5 new Known Limitation for editFiles. Confidence .80.
