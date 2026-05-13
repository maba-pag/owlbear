# Simplifier Stance — Body Newline Normalization

## Verdict: The false-positive tension is manufactured. Kill it.

The original brief already states "for markdown task bodies, there is no legitimate use case for literal backslash-n." That's correct. The context.md then introduces the opposite claim — that task bodies "discussing escape sequences" contain "legitimate literal `\n`" — and frames this as an "active tension."

It isn't. A task body that *talks about* `\n` is still a markdown body. When an agent writes `text.replace("\\n", "\n")` into a task body, the intent is the literal characters `\`, `n` rendered visually. Those characters survive normalization just fine — the file already contains actual newlines and the visual representation of code snippets depends on markdown fencing, not on the raw bytes being literal escape sequences. The "indistinguishable at the string level" framing is technically true but practically irrelevant: the bodies are markdown, not executable code. Grep for `\\n` in a code fence works identically whether the surrounding prose uses real newlines or literal `\n`.

**Cut the false-positive outcome entirely.** "Zero false positives on legitimate content" is a requirement that sounds rigorous but drags the solution toward heuristics, multi-pass detection, or context-aware parsing — all of which are absurd for a 5-line helper function. The naive `.replace("\\n", "\n")` *is* the correct solution. The original brief already proposed it.

## Scope cuts

1. **Drop the "zero false positives" outcome.** Replace with: "Naive replace is acceptable; edge cases in code-discussing bodies do not constitute corruption." This eliminates the need for any clever detection logic.

2. **Drop the named helper function.** The original brief proposes `_normalize_body()`. For a single `.replace()` call used in 5 spots, an inline expression or a one-liner is sufficient. A named function is fine too, but it should not be presented as a design decision requiring deliberation.

3. **Question whether this needs a full brief at all.** The actual change is: add `body = body.replace("\\n", "\n")` to 5 parameter sites in one file. That's a 10-line diff. The investment tier says "Tool" but the brief machinery (context, decisions, panel, synthesis) costs more attention than the implementation. This could be a single task with inline AC: "add backslash-n normalization to MCP body params; test with round-trip that double-escaped input produces real newlines."

## Decomposition pressure

None needed. This is already atomic. If anything, the brief is *over-decomposed* by framing prevention vs. remediation as a decision when the user already said prevention-only.

## What's right

- MCP server boundary is the correct layer. Agree.
- Prevention-only scope is correct. Agree.
- The 5 parameter sites are correctly identified. Agree.

## Confidence

**0.90** — High confidence that the false-positive framing is the primary source of unnecessary complexity and should be removed before any design work begins.
