---
description: "Scoped work, verification and complete handoffs for GitHub Copilot cloud sessions"
applyTo: "**"
excludeAgent: "code-review"
---

# GitHub Copilot Cloud Work

Applies only inside GitHub-hosted Copilot cloud-agent sessions, including Fix with Copilot and
PR-comment tasks. Do not change local IDE or built-in PR review behavior when this file is loaded there.

## Scope and Verification

- Use the supplied task and PR context. Discover current revisions, source owners and test commands
  yourself; ask for the PR link only if the intended PR is genuinely ambiguous.
- Use normal platform-managed commits and publication to the assigned branch. Do not merge,
  broaden permissions, change protections or dispatch successors without user authorization.
- For an explicitly identified Delivery redesign package/phase, read only the required common,
  action and package sections of the [cloud guide](../../.owlbear/research/delivery-cloud-flight-handoff.md)
  and its package plan. For other work, follow the actual task; do not invent D-phase IDs or require
  Delivery records, claims, custom agents, memory or a package plan.
- For review feedback, read the actual findings and current code first. Repair supported defects
  within the requested scope; explain rejected suggestions with evidence. A suggestion or Fix with
  Copilot invocation does not authorize unrelated redesign or weakened acceptance criteria.
- An explicit review-only request stays read-only. Report findings and propose a repair request;
  do not apply your own suggestions or imply that review approval authorizes implementation.
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
implemented candidate -> Review. Include the actual Delivery phase and guide path only for an identified
Delivery task. Otherwise write a plain-language PR-scoped request, for example:

```text
@copilot+gpt-5.6-luna:max Review the fixes on this PR against its requested behavior and latest findings; do not edit code.
```

Include an accessible review/report link if the next worker cannot find it on this PR. Never leave
the user to add the model mention or assemble technical fields. A next request is advice, not approval
or dispatch. If a genuine user decision or human merge is next, say so instead of inventing an agent job.
