---
name: h-hook-authoring
description: "Handbook: Design and validate deterministic VS Code agent hooks without confusing guidance with enforcement"
user-invocable: false
---

# Hook Authoring

Use this handbook when adding or changing a VS Code agent hook, an agent frontmatter hook
 declaration, hook validation, or hook tests in the OwlBear development workspace. It is a
 developer-only reference under `.github/skills`; it is not part of the portable `share/` skill
 surface unless a separate decision promotes it.

## Authority And Boundary

- Hooks are hard runtime controls. This handbook is soft guidance for designing and reviewing them.
- Keep enforcement in the hook script, agent declaration, validator, or regression test. Do not claim
  that a skill, instruction, or prompt mechanically prevents a violation.
- Keep Delivery claims, Design intent, user decisions, publication, and lifecycle transitions in
  their native owners. A hook may guard or observe a tool boundary; it must not become a second
  lifecycle controller.
- Prefer the nearest existing hook contract over a new event, output shape, or policy vocabulary.
  Read the current script and its tests before changing the contract.

## Choose The Lifecycle Event

| Event | Appropriate responsibility | Keep out |
| --- | --- | --- |
| `SessionStart` | Inject small, current context that helps the selected agent orient itself | Selecting work, mutating authority, or making a startup failure look like successful work |
| `PreToolUse` | Allow, deny, or narrowly transform a tool request before execution | Broad policy inference, product decisions, or checks that require post-execution state |
| `PostToolUse` | Run a bounded check or return feedback about a completed tool call | Treating a warning as a blocked result unless the owning contract explicitly requires blocking |

Choose the event from the claimed boundary. A hook that only explains a rule belongs in a skill or
instruction; a rule that must mechanically block an operation belongs in a hook, tool restriction,
schema, validator, or test.

## Define The Contract First

Before writing the script, record the smallest contract that can be tested:

1. **Input:** name the hook event, relevant `tool_name`, and the exact `tool_input` fields used.
2. **Output:** define the no-op or allow response and every deny, context, replacement, or block
   response the consumer understands.
3. **Failure policy:** decide what empty, malformed, unknown, or dependency-failure input does. Use
   fail-open or fail-closed deliberately for the named safety boundary; do not inherit it by accident.
4. **Scope:** normalize paths against the repository root, reject traversal, and enumerate supported
   tools instead of guessing from arbitrary input.
5. **Execution:** keep subprocesses bounded, non-interactive, and free of secret or user-data leakage.
6. **Repeatability:** make the same input produce the same decision and keep the hook safe to run
   more than once.

For a write guard, distinguish an allowed path from an unknown tool and from malformed input. For a
context hook, distinguish valid context from an unavailable command. For a post-tool check, distinguish
an actual affected file from an edit request that contains no supported path.

## Place And Wire The Change

- Development hook scripts belong under `.owlbear/hooks/`.
- Agent hook declarations belong in the owning `.agent.md` frontmatter.
- Agent hook contracts are checked by `.owlbear/scripts/validate_agents.py`.
- Behavioral guarantees belong in focused tests beside the existing hook tests, such as
  `tests/test_write_guard_hooks.py` and `tests/test_lint_changed_hook.py`.
- A portable consumer hook also needs its corresponding `seed/.owlbear/hooks/` copy and setup
  coverage. A developer-only hook does not gain consumer wiring implicitly.
- Keep hook authoring guidance here; do not copy the same contract into every agent or into
  `.github/copilot-instructions.md`.

## Implementation And Review Sequence

1. Identify the safety or observation boundary and the agent or tool that owns it.
2. Read the nearest hook, its frontmatter declaration, validator rule, and focused tests.
3. Implement the smallest deterministic script using structured JSON parsing rather than shell text
   guessing for structured input.
4. Cover malformed and empty input, unknown tools, the permitted case, the blocked case, traversal
   or scope escapes, and dependency failures relevant to the chosen failure policy.
5. Validate the output shape and exit behavior independently of the model's interpretation.
6. Update declarations, validators, seed copies, or documentation only when the ownership boundary
   requires it. Do not broaden the hook because a nearby rule is merely convenient to enforce.
7. Run the focused hook tests and the agent/customization validator from the repository root.

## Review Checklist

| Question | Passing signal |
| --- | --- |
| Is the hook attached to the correct lifecycle event? | The event crosses the claimed boundary before or after the relevant tool action |
| Is the hard owner explicit? | Script, declaration, validator, or test owns the behavior; prose only explains it |
| Is the contract observable? | Tests assert parsed output, decision, context, or exit behavior rather than invocation alone |
| Are negative paths covered? | Malformed input, unknown tools, traversal, and dependency failure follow the named policy |
| Is the scope bounded? | Supported tools and paths are enumerated; unrelated lifecycle or Delivery state is untouched |
| Is it portable by intent? | Consumer wiring and seed parity are explicit, or the skill/script is clearly developer-only |

## Known Pitfalls

- **Prose enforcement:** a rule in this handbook cannot block a tool; move safety-critical behavior to
  the runtime owner.
- **Event mismatch:** a `PostToolUse` warning cannot prevent the operation that already happened; use
  `PreToolUse` for prevention and preserve post-execution checks for observation.
- **Silent contract drift:** changing a hook response without updating its declaration, validator, and
  focused tests leaves agents with an unverified boundary.
- **Overbroad guards:** denying unknown tools or unrelated paths can break future VS Code tools and
  obscure the actual safety boundary; make the supported set and fallback explicit.
- **Consumer leakage:** a `.github/skills` development aid is not automatically a portable `share/`
  artifact. Promote it only through a separate scope and loading decision.
