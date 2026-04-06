---
# >> Your action: set response to completed when done
response: completed
notes: "Duplicate of docs\decisions\resolved\167-manual-vs-code-validation.md that was in pending/ at the same time. skipped because already resolved."
# >> Agent metadata (do not edit)
request_type: action
task_id: 167
agent: builder
created: 2026-04-02
urgency: blocking
---

# Action Request: Re-validate multi-project setup in VS Code (post-boolean-fix)

## Context

Task #167 validates the OwlBear clone=install model in VS Code. The previous manual
validations (2026-03-31) all failed because setup.py emitted string values for
`chat.agentFilesLocations` / `chat.agentSkillsLocations` / `chat.instructionsFilesLocations`
instead of boolean `true`. VS Code ignores string-valued entries, so no owlbear agents, skills,
or instructions were visible.

The boolean fix was committed 2026-04-01. A fresh `test-project/` has been recreated at
`C:\Users\p362329\Coding\Projects\test-project` with the correct settings. The `settings.json`
now reads `true` instead of `"OwlBear Agents"` etc. All programmatic AC items (AC1, AC5, AC7, AC9
setup) are confirmed. The remaining 5 items require VS Code UI interaction.

## Steps

- [ ] Open `C:\Users\p362329\Coding\Projects\test-project` as a folder in VS Code
      (File → Open Folder or `code C:\Users\p362329\Coding\Projects\test-project`)
- [ ] **AC2** — Open the agent picker (@ in chat or Configure Custom Agents). Verify owlbear agents
      (orchestrator, researcher, builder, etc.) appear in the list. Write outcome in notes below.
- [ ] **AC3** — Type `/` in VS Code chat and verify owlbear skills/prompts appear. Or ask a relevant
      question and confirm a relevant skill auto-loads. Write outcome in notes below.
- [ ] **AC4** — Open Chat Customizations (Chat menu → Chat Customizations or gear icon in chat).
      Verify owlbear instructions (`agent-common.instructions.md`, `python.instructions.md`, etc.)
      appear as loaded. Write outcome in notes below.
- [ ] **AC6** — In VS Code chat, verify `.github/copilot-instructions.md` appears in the chat
      References section (the link icon near the chat input). Write outcome in notes below.
- [ ] **AC7** — In the agent picker, confirm `Test Agent` (from `test-project/.github/agents/`)
      appears alongside the owlbear agents. Write outcome in notes below.
- [ ] **AC8** — Confirm owlbear agents are still visible even with `Test Agent` in the picker.
      Project-level agents should coexist, not shadow or replace owlbear agents.
      Write outcome in notes below.
- [ ] **AC9** — Close VS Code (or switch back to owlbear workspace), then delete test-project:
      `Remove-Item 'C:\Users\p362329\Coding\Projects\test-project' -Recurse -Force`

## Completion instructions

Document each AC outcome briefly in the `notes` field above (e.g., "AC2 PASS: saw orchestrator,
researcher, builder agents. AC3 PASS: /skills showed prompts. AC4 PASS: instructions listed.
AC6 PASS: copilot-instructions.md linked. AC7 PASS: Test Agent visible. AC8 PASS: no shadowing.
AC9 PASS: deleted.").

When all steps above are checked off, set `response: completed` in the YAML header and save.
The planner will unblock task #167 automatically on its next cycle.
