---
# >> Your action: set response to completed when done
response: completed
notes: ""
# >> Agent metadata (do not edit)
request_type: action
task_id: 532
agent: researcher
created: 2026-04-01
urgency: blocking
---

# Action Request: Empirical PostToolUse Hook Output Routing Verification

## Context

Task #532 requires verifying which PostToolUse output mechanisms reach the builder
agent model when running as a subagent. The theoretical analysis is complete
(see docs/research/posttooluse-subagent-output-routing.md) but empirical verification
requires interactive GUI observation that only a human can perform.

This directly informs whether task #210 (PostToolUse lint guard) can rely on
`additionalContext` or must use only exit code 2.

## Steps

- [ ] **Add test hook to builder.agent.md** — Insert the following `hooks:` block into
  the YAML frontmatter of `agents/builder.agent.md` (after the `agents: []` line):
  ```yaml
  hooks:
    PostToolUse:
      - type: command
        command: "powershell -NoProfile -Command \"$input = [Console]::In.ReadToEnd(); $json = $input | ConvertFrom-Json; if ($json.tool_name -match 'create_file|replace_string_in_file|multi_replace_string_in_file') { @{ hookSpecificOutput = @{ hookEventName = 'PostToolUse'; additionalContext = 'PROBE_ADDITIONAL_CONTEXT_532' }; systemMessage = 'PROBE_SYSTEM_MESSAGE_532' } | ConvertTo-Json -Compress } else { '{}' }\""
  ```

- [ ] **Open Hooks output channel** — View > Output > select "GitHub Copilot Chat Hooks"

- [ ] **Run builder on a throw-away edit** — In a new chat session, ask the builder
  agent (`@builder`) to create `docs/scratch/532-probe.txt` with any content

- [ ] **Record `additionalContext` routing** — After the hook fires, expand the builder
  subagent call and check: does `PROBE_ADDITIONAL_CONTEXT_532` appear in the builder's
  conversation context? Record: yes/no

- [ ] **Record `systemMessage` routing** — Check the main chat panel (not the expanded
  subagent): does `PROBE_SYSTEM_MESSAGE_532` appear? Record: yes/no

- [ ] **Record hook execution** — Check the Hooks output channel: did the hook fire?
  What JSON output was logged? Record the output

- [ ] **Test exit code 2 variant** — Replace the hook command with one that exits with
  code 2 and writes to stderr:
  ```yaml
  hooks:
    PostToolUse:
      - type: command
        command: "powershell -NoProfile -Command \"$input = [Console]::In.ReadToEnd(); $json = $input | ConvertFrom-Json; if ($json.tool_name -match 'create_file|replace_string_in_file|multi_replace_string_in_file') { [Console]::Error.WriteLine('PROBE_EXIT2_532: Lint errors detected'); exit 2 } else { '{}' }\""
  ```

- [ ] **Record exit code 2 routing** — Does `PROBE_EXIT2_532` appear in the builder's
  context? Does it appear in the chat panel? Record both

- [ ] **Remove test hook** — Remove the `hooks:` section from builder.agent.md, delete
  `docs/scratch/532-probe.txt`

- [ ] **Update research doc** — Add empirical findings to
  `docs/research/posttooluse-subagent-output-routing.md` section 4 with observed
  routing for each mechanism, then update #210's AC if needed

## Completion instructions

When all steps above are checked off, set `response: completed` in the YAML header and save.
The planner will unblock task #532 automatically on its next cycle.
