# First-Principles Stance — Body Newline Normalization

## Core Challenges

### 1. Contradictory outcomes

"Zero false positives + full normalization" is internally inconsistent. The two cases (LLM double-escape vs. legitimate literal `\n`) are byte-identical at the string level. The brief acknowledges this then lists both as outcomes anyway.

### 2. Wrong layer?

The MCP server receives already-parsed strings with zero context about LLM intent. It's the least-information point for this decision. An upstream fix — LLM prompt guidance ("JSON `\n` is already a newline; never use `\\n`") — would address root cause with zero false positives and zero code changes.

### 3. Broader than `\n`

If the LLM confuses JSON escape semantics for newlines, it likely does the same for `\t`, `\\`, and other sequences. Fixing one escape character is whack-a-mole unless the problem is proven to be newline-specific.

### 4. High false-positive risk in this system

OwlBear's task bodies routinely discuss escape sequences and code behavior — the exact content a naive replace would corrupt.

### 5. "Prevention only" is a confidence tell

If the fix isn't trusted enough to run on existing data, that's a signal it shouldn't be trusted for new data either. The scoping reveals latent doubt about correctness.

## Confidence

**0.85** — Strong challenge. The upstream prompt fix deserves investigation before committing to a server-side normalize.
