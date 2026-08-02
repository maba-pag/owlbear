---
# >> Your action: set response to completed when done
response: completed
notes: "All AC (2,3,4,6,8,9) tested successfully."
# >> Agent metadata (do not edit)
request_type: action
task_id: 167
agent: builder
created: 2026-03-31
urgency: blocking
---

# Action Request: Manual VS Code validation for multi-project setup (#167)

## Context

Task #167 ("Validate multi-project setup in VS Code") is blocked on 5 AC items that
require direct VS Code GUI interaction — specifically opening the test-project/ in a
separate VS Code window and verifying that OwlBear customisation files load correctly.

Builder agents have already completed AC1, AC5, AC7:

- **AC1 PASS** — `test-project/` created at `C:\Users\p362329\Coding\Projects\test-project`
  with `.vscode/settings.json` (agents/skills/instructions all mapped to `../owlbear`),
  `.vscode/mcp.json` (4 servers), `.github/copilot-instructions.md`, kanban/, and
  `owlbear-project.json` all in place.
- **AC5 PASS** — `owlbear-kanban` MCP `list_tasks` tool confirmed operational.
- **AC7 PASS** — `test-project/.github/agents/test-agent.agent.md` created with correct
  YAML frontmatter (name: Test Agent).

The 5 remaining steps below require you to open `test-project/` in VS Code and verify
the UI. See the full builder session notes in task #167 body for detailed context.

## Steps

- [ ] **AC2** — Open `C:\Users\p362329\Coding\Projects\test-project` in VS Code. Open
  the Chat panel, click the agent picker (the `@` selector), and choose
  "Configure Custom Agents." Verify that OwlBear agents (e.g., `orchestrator`,
  `builder`, `reviewer`) appear in the list.

- [ ] **AC3** — In the test-project VS Code window, type `/` in the Chat input to open
  the slash-command menu, or ask a relevant question (e.g., "how do I run tests?").
  Verify that OwlBear skills appear in the `/` menu or auto-load as context.

- [ ] **AC4** — In the test-project VS Code window, right-click on the Chat panel and
  select **Diagnostics**. Verify that the OwlBear instructions file
  (`instructions/python.instructions.md` or similar) appears loaded with no errors.

- [ ] **AC6** — In the test-project VS Code window, send a chat message (any question).
  Expand the **References** section in the chat response. Verify that
  `.github/copilot-instructions.md` content is listed as a reference.

- [ ] **AC8** — In the agent picker, verify that both the test agent
  (`test-project/.github/agents/test-agent.agent.md`) and OwlBear agents appear
  **side by side** with distinct names — project agents do NOT shadow or replace
  OwlBear agents.

- [ ] **AC9** — After completing all checks above, delete the test-project/ directory:
  `Remove-Item -Recurse -Force C:\Users\p362329\Coding\Projects\test-project`
  and document your findings as a Builder Notes section in task #167.

## Completion instructions

When all steps above are checked off, set `response: completed` in the YAML header and save.
The planner will unblock task #167 automatically on its next cycle.
