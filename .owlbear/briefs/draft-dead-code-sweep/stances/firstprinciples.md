# First-Principles Stance — Dead Code Sweep

## Irreducible Claims

For this work to be worth doing, exactly two things must be true:

1. **No live runtime path executes `serve/orchestrator/` code.** (Verified: no external package imports it; internal imports are self-referential only.)
2. **Removing the code reduces real maintenance drag** — stale references mislead agents/contributors who read docs and skills as authoritative.

That's it. The "dead code is bad" framing reduces to: does it actively confuse or obstruct? If the answer is yes for orchestrator, removal is justified.

## Challenged Assumptions

### `owlbear-project.json` is NOT dead.

The context document lists it as "unclear consumers." It has **at least three live consumers**:

- `setup/init.py` — generates it during project setup (lines 58, 171, 337, 380)
- `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` — resolves global KB path from it at runtime
- `setup/sharing-guide.md` and `setup-guide.md` — document it as per-project metadata

Removing it would break consumer project setup and knowledge-base resolution. **This item should be dropped from scope entirely.**

### "Opportunistic cleanup" is unbounded.

The framing says "plus opportunistic cleanup of other obviously dead code." This smuggles in undefined scope. Without a hard boundary, the task expands into archaeology. The irreducible version is: remove orchestrator, fix its references, stop.

### Pydantic AI references may not be dead weight.

Context mentions Pydantic AI as abandoned direction #2, but the locked outcomes don't include removing it. Research docs are kept. If this is just stale mentions in docs — that's a 5-minute grep-and-edit, not a Brief-worthy item. Don't elevate it.

## Latent Value Check

- **Orchestrator patterns:** `ErrorJournal`, `RetryPolicy`, wave-assembly logic — these are design patterns that could inform future MCP server error handling. However, they live in git history. Removal doesn't destroy them.
- **Research docs:** Already scoped out. Correct call.

## Recommendation

Narrow scope to: (1) delete `serve/orchestrator/` and its test fixtures, (2) scrub live docs/skills/instructions of Copilot CLI / ACP references, (3) update pyproject.toml workspace list. **Drop `owlbear-project.json` — it's alive.** Drop "opportunistic cleanup" as a scope item; if something surfaces during the grep, note it in a follow-up task, don't expand this one.

**Confidence: 0.88** — high certainty on the owlbear-project.json challenge; moderate certainty that unbounded "opportunistic" scope is the main execution risk.
