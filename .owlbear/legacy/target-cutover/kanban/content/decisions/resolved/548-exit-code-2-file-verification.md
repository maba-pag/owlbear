---
# >> Your action: set response to completed when done
response: completed
notes: "Output: 2026-04-02 19:03:54.272 [info] [#6] [PostToolUse] Completed (NonBlockingError) in 1736ms\n2026-04-02 19:03:54.272 [info] [#6] [PostToolUse] Output: PROBE_EXIT2_FILE_548: tool=create_file. ; 'PROBE_EXIT2_FILE_548' does NOT appear in debug chat log, only in GH CP Chat Hooks Output."
# >> Agent metadata (do not edit)
request_type: action
task_id: 548
agent: researcher
created: 2026-04-02
urgency: blocking
---

# Action Request: Verify exit code 2 routing via `-File` invocation

## Context

Task #548 investigates whether PS 5.1 `-File` invocation mode correctly propagates
exit code 2 to the VS Code hooks engine as BlockingError (model-facing). The #532
empirical spike found NonBlockingError using `-Command` one-liners, but Microsoft
docs confirm `-File` handles exit codes differently. Theoretical analysis at .60
confidence predicts `-File` will produce BlockingError. See
`docs/research/exit-code-2-file-mode-routing.md` for full analysis.

## Steps

- [ ] Create `scripts/hooks/probe-exit2.ps1` with this content:
  ```powershell
  $input_json = [Console]::In.ReadToEnd() | ConvertFrom-Json
  [Console]::Error.WriteLine("PROBE_EXIT2_FILE_548: tool=$($input_json.tool_name)")
  exit 2
  ```
- [ ] Add a temporary PostToolUse hook to `agents/builder.agent.md` frontmatter:
  ```yaml
  hooks:
    PostToolUse:
      - type: command
        command: "powershell -NoProfile -File scripts/hooks/probe-exit2.ps1"
  ```
- [ ] Run the builder agent on a throwaway file-edit task (e.g., edit empty.txt)
- [ ] Check the **GitHub Copilot Chat Hooks** output channel:
  - Record the classification: `BlockingError` or `NonBlockingError`?
  - Record the exact log line (copy/paste the relevant line)
- [ ] Check the **Chat Debug View** (Tool Call Debug Log):
  - Does stderr content ("PROBE_EXIT2_FILE_548...") appear?
  - If yes, what XML/format wrapping is used?
- [ ] Remove the probe hook from `agents/builder.agent.md`
- [ ] Delete `scripts/hooks/probe-exit2.ps1`
- [ ] Fill in `notes:` above with the classification result and any observations

## Completion instructions

When all steps above are checked off, set `response: completed` in the YAML header and save.
The planner will unblock the task automatically on its next cycle.
