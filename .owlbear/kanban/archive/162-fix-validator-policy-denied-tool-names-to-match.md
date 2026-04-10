---
id: 162
title: Fix VALIDATOR_POLICY denied tool names to match actual toolset registrations
status: archived
priority: needed
created: 2026-02-27T20:46:21.1106006+01:00
updated: 2026-02-28T23:53:16.4578052+01:00
started: 2026-02-27T21:28:14.5605699+01:00
completed: 2026-02-28T23:53:16.4578052+01:00
tags:
    - phase-8
    - agent
    - bug
class: standard
---

VALIDATOR_POLICY in roles.py uses denied names that don't match any real tool. No tool is actually blocked.

## AC
- [ ] In src/owlbear/core/roles.py VALIDATOR_POLICY.denied_tools:
      - file_write -> write_file (matches FileToolset registered name)
      - file_edit -> create_file (matches FileToolset registered name)
      - file_delete -> remove entirely (no such tool exists)
      - execute_command -> remove (reviewer needs terminal for tests/lint; safety via CommandGuard)
- [ ] New denied_tools: frozenset({'write_file', 'create_file'})
- [ ] Update VALIDATOR_POLICY docstring: 'Validator: read-only — cannot write or create files'
- [ ] Update tests/test_roles.py:
      - Fix _make_toolset() fixture tool names to match real names (write_file, create_file, run_command)
      - Fix assertions to match corrected policy (write_file, create_file denied; run_command allowed)
      - Add test: run_command NOT in validator denied_tools (intentional — reviewer needs terminal)
- [ ] All existing tests pass after corrections
- [ ] ruff clean

## Architecture
- Actual registered tool names: read_file, write_file, create_file, list_directory, search_files (FileToolset), run_command (TerminalToolset), ask_user (AskUserToolset)
- Validator safety for command execution comes from CommandGuard (blocks dangerous cmds), not role policy
- Validator safety for file writes comes from role policy (blocks write_file, create_file)
