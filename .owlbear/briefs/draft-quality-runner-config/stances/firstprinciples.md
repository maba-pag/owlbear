# First-Principles Stance — Quality-Runner Structural Config

## Irreducible Problem (reduced)

The actual failure mode is narrow: **an agent holding a test path cannot determine the working directory to execute that test command from.** Toolchain selection (pytest vs vitest) is already solvable by file extension. The real gap is: given `frontend/src/__tests__/Foo.test.tsx`, where do I `cd` to run `npm test`?

That's it. Not "routing." Not "N contexts." Not "portability." The irreducible claim is: **cwd resolution for test execution requires knowing the nearest package root, and agents need either a way to find it or a way to be told.**

## Assumptions Challenged

### 1. "Portability promise of share/"

**Status: unearned.** The evidence section explicitly states: "No post-implementation routing failures." Zero external consumers have hit this problem. The framing treats a future portability property as a current broken contract. It is not broken — it is unbuilt. This distinction matters: "fix a broken thing" has urgency; "pre-build a feature for hypothetical future users" does not.

**Question to hold:** How many external consumers of `share/` exist today? If the answer is zero or one (OwlBear-dev itself), this is speculative infrastructure.

### 2. "Agents have no reliable way to determine toolchain"

**Status: mostly false.** Agents can:
- Read file extensions (`.tsx` → frontend, `.py` → Python) — the skill already describes this
- Walk up from a test file looking for `package.json` or `pyproject.toml` — standard filesystem traversal any LLM agent can perform
- Read the consumer's `copilot-instructions.md` which already has a Directory Structure table

The *actual* gap is that h-quality-runner doesn't say "walk up to the nearest package.json" as an explicit instruction. The skill hardcodes an example path instead of stating the general rule. This is a prose deficiency in one file, not a structural architecture problem.

### 3. "Need to support N test contexts"

**Status: premature generalization.** The minimum viable win says "at least 2 contexts." The current system has exactly 2 (Python + frontend). Designing for arbitrary N introduces accidental complexity for a requirement nobody has articulated. The two-context case has a trivial heuristic: if the file is under a directory with `package.json`, use npm/vitest; otherwise use uv/pytest. No routing table needed.

### 4. "Inference vs declaration" is a meaningful tension

**Status: false dichotomy.** The seed template *already declares the frontend root* in its Directory Structure table. `copilot-instructions.md` is already the place consumers state their layout. The "tension" assumes these are competing approaches, but they compose trivially: try inference first (walk to nearest package manifest), fall back to declared root in `copilot-instructions.md`. No architecture needed.

### 5. Scope includes setup/init.py scaffold changes

**Status: inherited scope creep.** If the fix is "add one sentence to h-quality-runner explaining the cwd-resolution heuristic," then init.py changes are unwarranted. The seed template already has the right structure. Only add scope that the irreducible problem demands.

## The Smallest Fix

Change one paragraph in h-quality-runner from:

> "Quality-runner selects the toolchain based on test_paths: paths under your frontend package root use vitest"

To something like:

> "Quality-runner resolves toolchain and cwd by walking up from each test_path to the nearest package manifest (package.json → vitest+npm, pyproject.toml → pytest+uv). The cwd is the directory containing that manifest. If your copilot-instructions.md declares a frontend root in its Directory Structure table, that serves as the authoritative override."

That's ~40 words of prose. No config schema, no N-context routing table, no init.py scaffold changes.

## Reframe

The problem is not "routing." The problem is that h-quality-runner's prose **describes what it does** (routes by path prefix) instead of **stating the general rule** (resolve cwd from nearest package manifest). The fix is editorial, not architectural.

## Confidence

**0.82** — High confidence the problem reduces to a prose fix. Slight uncertainty about whether consumers with non-standard layouts (monorepo with multiple package.json at different levels) would need the declared-root fallback to actually be formalized, but that's a refinement, not a counter-argument.

## Summary of Irreducible Core

| Claim | Necessary? |
|-------|-----------|
| Agents need to know cwd for test execution | **Yes** — irreducible |
| Agents can't determine toolchain from file content | No — extensions solve this |
| A config schema/declaration is needed | No — manifest-walk heuristic suffices |
| N-context generalization is needed now | No — 2 contexts with known heuristics |
| share/ portability is currently broken | No — untested; zero external consumers have failed |
| copilot-instructions.md needs a routing section | Maybe — but the existing Directory Structure table already serves this role |
| setup/init.py needs changes | No — seed template already has the relevant structure |
