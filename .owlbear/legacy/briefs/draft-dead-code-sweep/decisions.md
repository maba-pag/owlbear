# Decisions — Dead Code Sweep

## Project Type

- **Chosen:** `existing-feature/refactor` (cleanup/removal)
- **Rationale:** No new features. The work is identifying and removing code that served abandoned directions.

## Investment Tier

- **Chosen:** Tool
- **Rationale:** Internal cleanup, single decision-maker, bounded scope, medium risk (reversible via git). Standard M2, selective panel, full Brief.

## owlbear-project.json

- **Chosen:** Remove from root, seed, setup/init.py generation, and setup docs. Leave `scope_transfer.py` code untouched (it has `OWLBEAR_GLOBAL_KB_PATH` env var fallback; KB isn't fully implemented yet).
- **Rejected:** Drop entirely from scope (challengers recommended this — overruled by user). The file's only real runtime consumer is KB scope_transfer, which isn't complete. Removing generation + seed is safe.
- **Rejected:** Remove from KB too — would break the in-progress knowledge scope transfer feature.

## Scope

- **Chosen:** Surgical scope. Remove orchestrator + owlbear-project.json (per above) + all live references to Copilot CLI/ACP. If other dead code surfaces during grep, file as follow-up task.
- **Rejected:** "Opportunistic cleanup" clause (both challengers flagged as scope trap).
- **Rejected:** Tasks-only delivery (user chose thin Brief via Phase 2).

## Delivery Format

- **Chosen:** Thin Brief via Phase 2 (ideation-mediator)
- **Rejected:** Atomic kanban tasks without Brief (simplifier recommended this — user prefers the Brief for completeness).

## Excalidraw Diagrams

- **Chosen:** Edit now (option A) — remove orchestrator/ACP elements from all 3 diagram JSON files in this task.
- **Rejected:** Defer to follow-up (option B) — user wants a complete pass.
- **Rejected:** Delete and regenerate (option C) — loses layout work.

## Dev Environment KB Path

- **Chosen:** Ignore for now — KB isn't fully implemented yet; latent break is acceptable.
- **Rejected:** Set `OWLBEAR_GLOBAL_KB_PATH` in dev environment.
