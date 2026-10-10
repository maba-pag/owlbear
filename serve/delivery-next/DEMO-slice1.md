# Delivery-next slice 1, phase B: live demonstration

Date 2026-10-10, macOS. Copilot CLI 1.0.95 (installed, stdio), `github-copilot-sdk` 1.0.19, model `auto`
(billed: `gpt-6-luna` on every run, no mismatch). Sandbox clone `~/Projects/owlbear-sandbox`
(`boecht/owlbear-sandbox`, `main` at `0d0dff4`). State: `.git/owlbear-delivery/` of the clone. Worktrees:
`~/Library/Application Support/OwlBear/worktrees/owlbear-sandbox-6dade79d/<change>`.

Commands, run from the OwlBear worktree:

```text
uv run --locked python -m owlbear_delivery_next.cli --repo ~/Projects/owlbear-sandbox seed greet \
  --title "Add a greeting function" --outcome "... The greeting language is a product decision for the owner:
  ask if it is not specified." --criterion ... --scope packages/app --check "npm test" --install "packages/app=npm ci"
uv run --locked python -m owlbear_delivery_next.runner greet --repo ~/Projects/owlbear-sandbox
uv run --locked python -m owlbear_delivery_next.cli --repo ~/Projects/owlbear-sandbox answer greet --question q1 \
  --text "German: greet('Ada') returns 'Hallo, Ada!'"
uv run --locked python -m owlbear_delivery_next.runner greet --repo ~/Projects/owlbear-sandbox
```

## Results

| # | Change, run | Exit | Evidence | Credits |
| --- | --- | --- | --- | --- |
| 1 | `greet`, runner process 1 | `ask` (9.7 s) | q1 "Which language should `greet(name)` use? (why: The brief makes greeting language an owner decision, and AC-1 requires the chosen language.)" Options English, Spanish, French, each with its effect. Session `greet-build-t1-2afe1b82`; runtime PID 11696; recorded 11696, 11702; tasks listed none; termination confirmed; scan empty | 0.185 |
| 2 | `greet`, runner process 2 after the inbox answer | `done` → `review` (22.6 s) | Same session resumed, answer sent as a message. Commit `51015ed` on `owlbear/greet` (`src/greet.ts`, `test/greet.test.ts`); `npm test` in the worktree: 3 pass, 0 fail. `submit_result` accepted first time. Recorded PIDs 12452, 12455, 12504, 12505, 12530, 12531, all gone; termination confirmed | 0.400 |
| 3 | `farewell`, brief tells the agent to submit before committing | `done` (31 s) | First `submit_result` rejected with `commit: HEAD of the worktree is 0d0dff4023b7, the task's base; commit your changes, then submit again` and `commit: the worktree has uncommitted changes (packages/app/src/math.ts, packages/app/test/math.test.ts); commit them, then submit again`; the agent committed `311279e` and the second call was accepted. `npm test`: 3 pass | 0.348 |
| 4 | `ticker`, brief asks the agent to leave a background loop running | `back` → `plan` | The Builder refused (its prose forbids leftover processes) and called `report_wrong_premise`; termination confirmed | 0.147 |
| 5 | `smoke`, target `demo/ticker-base` (`9a101ce`, sandbox-only branch whose `npm run smoke` leaks a `nohup sh -c 'while true; ...'` loop) | `stop` (61 s) | Runner protocol: no listed tasks, recorded PIDs 17363, 17370 gone. Post-exit worktree scan found 17494 (`sh` loop, cwd in the worktree) and 17635 (`sleep`). Exit `stop`: "termination unverified: processes 17494, 17635 still present", action "End processes 17494, 17635". A later runner start printed "nothing to run". Loop killed by hand (`kill 17494`) | 0.500 |
| 6 | `greet2`, final code after compacting the runner | `ask` | Same ask behaviour; termination confirmed | 0.086 |

Total 1.67 credits. Lock check: with the `greet` lock held by another process, the runner printed
"Change lock held by 18494; another runner holds it" and exited 0.

## State and branches

- `main` stayed at `0d0dff4`; nothing was pushed. New local branches only: `owlbear/greet`, `owlbear/farewell`,
  `owlbear/ticker`, `owlbear/smoke` (one task commit each, `ticker` none) and the demo base `demo/ticker-base`.
- The main checkout of the sandbox stayed clean; all Change state is under `.git/owlbear-delivery/`.
- No denial occurred in these runs. After the demo, `pgrep` found no Copilot runtime and no loop.
- The worktrees remain for inspection.

## Limits

- Field errors appeared only when the brief provoked an early submit; unprovoked builders committed first.
- The worktree scan runs in the runner after the runtime has exited, standing in for the host scan of D4.
- Personal Copilot identity, `auto` model only, one tiny TypeScript package.
