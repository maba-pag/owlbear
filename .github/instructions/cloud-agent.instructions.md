---
description: "Scoped work, verification and complete handoffs for GitHub Copilot cloud sessions"
applyTo: "**"
excludeAgent: "code-review"
---

# GitHub Copilot Cloud Work

Scope: GitHub-hosted Copilot cloud-agent sessions, including Fix with Copilot and PR-comment tasks.
In other environments, follow that environment's review or implementation instructions.

## Scope and Verification

- Use the supplied task and PR context. Discover current revisions, source owners and test commands
  yourself. Use referenced plans to establish the requested scope; ask for the PR link only if the
  intended PR is genuinely ambiguous.
- Use normal platform-managed commits and publication to the assigned branch. Do not merge,
  broaden permissions, change protections or dispatch successors without user authorization.
- For review feedback, read the actual findings and current code first. Repair supported defects
  within the requested scope; explain rejected suggestions with evidence. A suggestion or Fix with
  Copilot invocation does not authorize unrelated redesign or weakened acceptance criteria.
- For a review-only request, inspect and report findings without editing. Implementation requires
  a separate user request.
- Use disposable state and synthetic inputs. No live OwlBear MCP startup, production-state changes,
  company authentication or real provider mutations for testing.
- Run the smallest affected test/check after substantive edits. Widen only for concrete consumer
  risks. Never run the whole OwlBear suite, MegaLinter, `uv run megalint`, `uv run quality` or heavy
  aggregate wrappers. Use locked toolchains and existing in-process tests; avoid repeated installs,
  builds and tests on unchanged inputs. Missing capabilities must not halt other supported work.
- Record unrun checks and their limits; fix real failures instead of adding skips or relaxing tests.
  Preserve existing work and publish coherent checkpoints before the session limit. A timeout does
  not require starting over, escalating models or repeating completed effects.

## Result and Next Request

End with the outcome, observed revision, actual proof and unresolved findings/capability gaps.
Distinguish your checks from prior reported evidence. Keep PR summaries current, not a session diary.

When another agent action is needed, include exactly one complete copy-ready request in a `text`
code block, starting with the selected model's GitHub-qualified mention. Default to
`@copilot+gpt-5.6-luna:max` for well-defined planning, implementation, review and repair. Recommend
Opus/Astra only for a concrete unresolved decision that merits their cost; put that model's known
selector in the command, never a guessed suffix or placeholder.

Choose the next action from evidence: unfinished task -> Resume; valid unresolved findings -> Repair;
implemented candidate -> Review. Write a self-contained request for the actual task on the current PR:

```text
@copilot+gpt-5.6-luna:max Review the fixes on this PR against its requested behavior and latest findings; do not edit code.
```

Include an accessible review/report link if the next worker cannot find it on this PR. Never leave
the user to add the model mention or assemble technical fields. A next request is advice, not approval
or dispatch. When a user decision or human merge is next, state that next step instead of a prompt.

## Delivery Redesign Tasks

When the task explicitly names a Delivery redesign package or phase, use its package plan and the
selected common, action and package sections of the
[cloud guide](../../.owlbear/research/delivery-cloud-flight-handoff.md). Include that phase and guide
path in the next request. The guide supplies this programme's execution and acceptance requirements.
