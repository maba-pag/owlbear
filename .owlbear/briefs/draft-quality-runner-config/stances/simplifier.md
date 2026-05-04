# Simplifier Stance — Quality-Runner Routing

## Verdict: Scope is 2–3× larger than the problem

The quality-runner already has 2-toolchain routing. It already names `copilot-instructions.md` as routing authority. The only real gap is:
1. The consumer template doesn't declare the frontend root in a way agents can find
2. The skill doesn't describe a general cwd-resolution rule (just a path-prefix example)

## Recommended Cut

**4 artifacts → 2 artifacts.**

| Keep | Drop |
|------|------|
| h-quality-runner prose fix (cwd-resolution rule) | N-context generalization |
| copilot-instructions.md template section | Multi-root "design" |
| | h-vitest-and-linting changes |
| | setup/init.py scaffold logic |

## Why

- The multi-root design is premature: zero consumers need N contexts today. The 2-context case (Python + frontend) has a trivial heuristic.
- h-vitest-and-linting doesn't need changing if h-quality-runner just says "cd to the nearest package.json before running vitest."
- setup/init.py already scaffolds copilot-instructions.md — adding a section to the template is enough.

## Minimum Deliverable

1. ~3 lines of prose in h-quality-runner stating the general cwd rule
2. A `## Quality Runner` section in the copilot-instructions.md seed template declaring the project's test contexts

That's it. Ship in a day, not a week. Confidence: 0.85.
