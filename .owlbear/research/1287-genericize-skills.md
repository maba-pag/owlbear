# Research: #1287 — Genericize h-pytest-and-linting, h-vitest-and-linting, h-quality-runner

## Findings

### Current State

Commit `8e442bdc` (part of #1285 builder) already performed a mechanical `serve/` → `workspace/` find-and-replace across all three files:

| File | Changes | `\bserve/` remaining |
|------|---------|---------------------|
| h-pytest-and-linting/SKILL.md | 8 substitutions | 0 |
| h-vitest-and-linting/SKILL.md | 7 substitutions | 0 |
| h-quality-runner/SKILL.md | 7 substitutions + routing prose added | 0 |

**All 9 tests in `test_path_neutrality_1285.py` pass.** The test gate (AC5) is satisfied.

### Quality Gap: Brief Notation Convention (AC4)

The Brief (`draft-neutral-shared/brief.md`) specifies three notation rules the current implementation violates:

| Brief Rule | Expected | Actual |
|------------|----------|--------|
| Conceptual nouns inline | "your source packages", "your frontend package root" | Bare `workspace/` |
| Framed examples for concreteness | `> Example (OwlBear-dev): serve/cockpit/web/` | None present |
| Shell command prose notes | `# adjust paths for your project layout` | No prose notes |

Additionally, `workspace/` is problematic: it doesn't exist as a directory in OwlBear-dev (real path: `serve/`) NOR in any consumer project. It's neither a valid illustrative path nor a conceptual noun — it's a halfway state.

### What the Tests Verify vs. What ACs Specify

| AC | Test covers | AC text requires |
|----|-------------|------------------|
| AC1 | `\bserve/` absent | "concrete illustrative paths + prose note pattern" |
| AC2 | `\bserve/` absent | "'your frontend package root' + framed example" |
| AC3 | Routing phrase + `copilot-instructions.md` present | ✅ fully verified by test |
| AC4 | Not tested | Brief's notation convention compliance |
| AC5 | Tests pass | ✅ |

**Gap:** AC1, AC2, and AC4 have requirements beyond what the tests verify. The tests were designed as a floor (no `serve/` paths), not a ceiling (full notation compliance).

## Trade-off Matrix

| Option | Effort | Correctness | Risk | Confidence |
|--------|--------|-------------|------|------------|
| A: Accept test-passing state, close task | None | .60 — `workspace/` is semantically wrong | LLMs copy `workspace/` literally; agents execute broken commands | .40 |
| B: Refine to Brief convention (conceptual nouns + framed examples + prose notes) | ~30 min builder | .90 — matches Brief exactly | Minimal — file edits only | .80 |
| C: Refine to use `src/ tests/` as illustrative paths (simpler than full Brief) | ~15 min builder | .75 — correct but no framed examples | Slightly less clear for complex paths | .65 |

## Recommendation

**Option B** (confidence .80). The Brief's notation convention exists for a reason: bare `workspace/` will be copied literally by LLMs on consumer projects where no such path exists. The framed-example pattern (`> Example (OwlBear-dev): serve/cockpit/web/`) explicitly labels project-specific paths as non-normative. The prose note pattern (`# adjust paths for your project layout`) signals agents to explore rather than copy.

The builder task is small (~30 lines across 3 files) and requires no test changes — existing tests already pass.

## Sources

1. Brief: `.owlbear/briefs/draft-neutral-shared/brief.md` — Notation Convention section
2. Commit `8e442bdc` — the mechanical replacement diff
3. Test file: `tests/test_path_neutrality_1285.py` — test scope analysis
