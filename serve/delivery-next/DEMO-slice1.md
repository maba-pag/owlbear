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

## Re-demonstration after review

Same setup and commands, after the repairs F1-F7 (bounded steps, Builder-owned install, stricter permissions,
durable PID and answer evidence, derived HEAD, missing-session replacement). Billed model `gpt-6-luna` on every run.

| # | Change, run | Exit | Evidence | Credits |
| --- | --- | --- | --- | --- |
| 1 | `greet3`, runner process 1 | `ask` (15 s) | The Builder ran `cd 'packages/app' && npm ci` itself (transcript), read the package, then asked q1 (English, French, Spanish). Session `greet3-build-t1-4d5dd6a6`; runtime PID 42930 and child 42933 written to the activity log as `pids` events when seen; termination confirmed; scan empty | 0.257 |
| 2 | `greet3`, runner process 2 after the inbox answer "German: greet('Ada') returns 'Hallo, Ada!'" | `done` → `review` (12 s) | Same session resumed; `delivered_at` 04:35:26 recorded on send, `effect_observed_at` 04:35:37 only after the accepted result. Transcript: patch, `npm test` (3 pass, 0 fail), commit, `submit_result` accepted first time. Runner-derived HEAD `719f44c` on `owlbear/greet3` (`greet.ts`, `greet.test.ts`). PIDs 43543, 43544 gone; termination confirmed | 0.352 |
| 3 | `noverify`, brief demands `git commit --no-verify` | `done` (34 s) | The Builder declined on its own (prose: never skip hooks) and committed normally; no request reached the policy | 0.255 |
| 4 | `noverify2`, brief asks to attempt `--no-verify` once as a policy probe | `done` (38 s) | Activity `denied`: "`git commit --no-verify -am 'chore: describe math module'` uses --no-verify, which skips hooks or signing or forces history"; the same text is the outcome's `denial`. The Builder then committed with hooks (`1ccffb5`); termination confirmed | 0.373 |

Total 1.24 credits. `main` stayed at `0d0dff4`; new local branches `owlbear/greet3`, `owlbear/noverify`,
`owlbear/noverify2`; nothing pushed. After the runs `pgrep` found no Copilot runtime, `npm` or test process of
these steps. Not exercised live: an early submit (field error on `changes`), a step deadline or hung call, a
killed runner with answer readback, and a missing session; these are covered by fake-driven tests only.

## Phase C demonstration

Date 2026-10-10, macOS. Copilot CLI 1.0.95, `github-copilot-sdk` 1.0.19, FastAPI 0.142.2, uvicorn 0.54.0,
Node 24.21.0, model `auto` (billed `gpt-6-luna` on every step, no mismatch). Phase B Changes were moved to
`.git/owlbear-delivery/archive-phase-b/` first. Seed (one task, one person-only check, launch command
`npm run preview`), then the host; every later step was started by the host:

```text
owlbear-next --repo ~/Projects/owlbear-sandbox seed welcome --title "Add greet(name) and a local preview page" \
  --outcome "... 'npm run preview' serves http://127.0.0.1:4173/ ... the greeting language is a product decision ..." \
  --scope packages/app --check "npm test" --install "packages/app=npm ci" --launch "npm run preview" \
  --person-check "preview=Open the preview and confirm the greeting shows"
owlbear-next --repo ~/Projects/owlbear-sandbox host
```

Run `welcome` (times UTC):

| Done criterion | Evidence |
| --- | --- |
| Host launches the Builder by itself → `ask` | Host 71227 started 05:02:09 and launched runner 71229 at once; `ask` q1 at 05:02:19 (Other language, English, Spanish); termination confirmed, no tasks listed |
| Second host prints the URL and exits 0 | `Delivery is already running: http://127.0.0.1:59161/`, exit 0. API without token → 401; foreign `Host` header → 403 |
| Answer through the API launches exactly one successor | `curl POST /api/next/changes/welcome/answers` (o3, "German: greet('Ada') returns 'Hallo, Ada!'") at 05:02:37.03; runner 73170 started 05:02:37.09; `delivered_at` 05:02:37.97, `effect_observed_at` 05:03:31.95 |
| Host killed while a runner is active; restart waits, observes, continues | `kill -9` host at 05:02:41; runner 73170 lived on in its own session; `status`: "welcome: Build 1/1 · Delivery is not running / next: Start Delivery (run `owlbear-next host`)". New host 73542 at 05:02:47 showed "implementing … builder active 12 s ago", waited; the runner ended 05:03:31 (`done`, commit `ea6d120`); after the termination check the host launched one runner, 73949, at 05:03:33 |
| Review runs | Task review `pass` 05:04:05 and final review `pass` 05:04:37 on `ea6d120`, each with covered-path fingerprints; read-only policy; `submit_result` accepted first time |
| Check preparation returns a launch recipe | Publish and follow are slice stubs ("not published: publication is a later slice"). Check runner 74256: one URL request denied, then recipe `npm run preview`, `packages/app`, `http://127.0.0.1:4173/` accepted 05:05:03; termination confirmed |
| Host launches the preview, verifies readiness, status shows the waiting check | 05:05:04 "check environment ready … PIDs [74689, 74715]" (npm, pgid 74689, parent host; node `src/preview.ts`). `curl` → `<p>Hallo, Ada!</p>`. Status `Check · waiting for you: Open the preview and confirm the greeting shows · http://127.0.0.1:4173/`, next: Report result. Killing node 74715 → host relaunched at 05:05:35 (PIDs 75895, 75918) |
| Orphan blocks the next writer; removal resumes | `sh -c 'while true; do sleep 5; done'` (77042) started outside Delivery in `packages/app` of the worktree |
| Check result disposes the environment; Change reaches a defined end | `POST …/check-results` (pass) 05:05:48 → "check environment disposed" (preview refused) → "no writer starts: processes still present: 77042 (bash), 77045 (sleep)"; status "Merge · stopped: … / next: End processes 77042, 77045". `kill 77042` at 05:05:54; next tick 05:06:18 launched runner 77694 → "Merge · waiting for you: Publishing and merging are a later slice; the checked work is on branch owlbear/welcome" |

Credits: build ask 0.114, build 0.557, task review 0.218, final review 0.261, check preparation 0.344; total
1.49. Touchpoints: the answer and the check result only (the environment kill and the orphan were injected
faults). `owlbear/welcome` holds `ea6d120` (`greet.ts`, `preview.ts`, two tests, `package.json`); `npm test`
in the worktree: 4 pass, 0 fail. `main` stayed at `0d0dff4`, nothing was pushed and the sandbox checkout is
clean. After `SIGINT` to the host, `pgrep` found no host, runner, preview, orphan or Copilot runtime;
`host.json` was removed and `status` showed "Delivery is not running".

Two earlier runs found defects, fixed before `welcome`:

- `hello` (0.09 credits): the host's scan without a start time counted unreadable system daemons (`lsd`,
  `UserEventAgent`, …) as leftovers and blocked. The scan now passes the runner's or step's start time.
- `greeting` (0.90 credits): my answer chose "English" with the text "German instead"; the Builder built
  German, and the reviewer, whose prompt lacked the owner's answers, asked again. Every agent prompt now carries
  the owner's answers. This run also showed host kill and restart with no duplicate runner.

Limits: sleep detection, recorded-PID survivors after a killed runner and the PR terminal-state hook ran only in
tests; environment relaunch after a host restart was not shown live (relaunch after interruption was). The
Changes page was fetched but not used in a browser; answers and results went through the API with `curl`.

## Repairs after review of `25c2dd89b`

- Environment ownership: the host persists `launched_at` before spawning and the group id and leader PID right
  after, before readiness. A launch without a recorded group is uncertain; the next pass scans the worktree from
  `launched_at`, disposes of what it finds and launches only when nothing remains, else no writer starts and the
  PIDs are named. A started but never ready environment is disposed of and relaunched.
- Disposal signals the recorded group (`killpg`, TERM, 5 s, KILL) even without its leader, and the recorded
  PIDs; it succeeds only when no group member or recorded PID remains. A failure keeps the environment record,
  names the PIDs and blocks relaunch and the next writer.
- A check result is recorded by the inbox fold and settled by the host only when its recorded inputs (criteria,
  path fingerprints, procedure, environment) equal the current ones; the pending wait is cleared only by that
  settlement. A settled failure settles no later round.
- The Changes page replaces its forms after a successful submission and keeps only a focused text field or input.
- A second `host` prints the token-bearing URL.

Disposable scenarios (macOS, temporary directory, removed afterwards; no process left per `pgrep`):

| Scenario | Outcome |
| --- | --- |
| Leader serves readiness, spawns a child ignoring SIGTERM after 2 s and exits | Recorded `[96200]`; after 3 s the leader was gone, the group held 96234. Verification over recorded PIDs alone reported confirmed. The new disposal ended 96234 with KILL after 5.3 s; group empty, `pgrep -g 96200` none |
| Host killed (`SIGKILL`) between spawn and recording the group | Persisted `launched_at`, no group; orphan 96463 still served. The restarted host found it by the worktree scan, disposed of it, then launched one group 96470 and entered pending; only 96470 ran |

## Known deviations

Modules over the draft limits of the architecture, kept as they are: `sdk_adapter.py` 611 (600), `store.py` 260
(250), `models.py` 388 (350), `loop.py` 507 (500).
