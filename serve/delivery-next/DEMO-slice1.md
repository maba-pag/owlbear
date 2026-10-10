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

## Slice 2 demonstration

Date 2026-10-10, macOS. Copilot CLI 1.0.95, `github-copilot-sdk` 1.0.19, gh 2.102.0, git 2.56.0, Node 24.21.0,
FastAPI 0.142.2, uvicorn 0.54.0; model `auto`, billed `gpt-6-luna` on every agent step. Sandbox `main` at
`0d0dff4`; phase C state moved to `.git/owlbear-delivery/archive-phase-c/`. Code: `fc3880d5b`, `add0d16ae`,
then `81f53d258` (fix below) from 06:05 UTC on.

```text
owlbear-next --repo ~/Projects/owlbear-sandbox profile                       # detect
owlbear-next --repo ~/Projects/owlbear-sandbox profile --confirm github:rules=none
owlbear-next --repo ~/Projects/owlbear-sandbox seed greeter|clamp|clock ...   # pre-approved one-task Changes
owlbear-next --repo ~/Projects/owlbear-sandbox host
```

Detected profile (v2; v3 after the confirmation): repository `boecht/owlbear-sandbox`, default branch `main`, methods squash/merge/rebase (chosen
`squash`), workflow `ci.yml` declaring check `test`, no pre-push hook, delete remote branch `no`. Rules, required
checks and merge queue: **unknown** (`HTTP 403: Upgrade to GitHub Pro …`). Unknown rules make merging
human-assisted (unit-checked); the owner confirmation `github:rules=none` records the 403 it saw and holds while
GitHub keeps answering the same, so direct merging was allowed. Re-reads before every publish and merge matched.

### Main journey: `greeter` (PR #3), times UTC

| Stage | Evidence |
| --- | --- |
| Build → review → final review | 05:56:32 → 05:57:59; commit `01c1d88` (`greet.ts`, `preview.ts`, test, script) |
| Publish | 05:58:06, 6.8 s: branch pushed with hooks, draft PR #3 created and marked ready |
| Follow | 05:58:09 pending "1 of 1 checks running"; run 38029299361 `test` passed; 05:58:31 "CI passed: test" |
| Check (preview) | Recipe accepted 05:59:04; host served `<p>Hallo, Ada!</p>` at 05:59:05; result `pass` via API 05:59:51; environment disposed |
| Merge consent | 05:59:54 "Merge · waiting for you: approve merging 01c1d88" (offer: PR, diff link, head, `test: passed`) |
| Failure (b) | Paused, consent for `01c1d88` via API 06:00:07, owner commit `0b5e2d9` pushed from a temporary clone, local commit `af24cd9` and untracked `scratch.txt` added in the worktree; resumed 06:00:28 → "approve merging 0b5e2d9, changed since 01c1d88 (1 commit(s): docs: describe the greeting (owner edit after consent) · files: packages/app/GREETING.md)". Consent for `01c1d88` then refused with 409; re-consent for `0b5e2d9` 06:00:39 |
| Merge | Run 38029432961 on `0b5e2d9` completed 06:00:41; squash merge with `sha=0b5e2d9…` → `7417fba` (GitHub merged 06:00:43); readback merged |
| Cleanup | Kept refs `origin/main`, `0b5e2d9`: 1 unmerged commit → `greeter-1.bundle` (verified), `scratch.txt` → `greeter-1.tar` (read back); worktree removed; history line |
| Done | "Done · merged PR #3 · unmerged work saved in …/greeter-1.bundle, …/greeter-1.tar" |

Credits 1.23. Touchpoints: check result, merge consent (twice: once voided by the injected head change).

### Failure (a): `clock` (PR #4), CI fails, Builder fixes

The brief stated, wrongly, that CI runs in Europe/Berlin; the test asserted `'14:00'` for `12:00Z`.

| Stage | Evidence |
| --- | --- |
| Publish, follow | `bec55c1`, run 38029444971 failed: `'12:00' !== '14:00'`; 06:01:22 follow `back` → task t2 "Fix the failing CI check test" carrying the log tail (cause `checks:follow:test`, 1 of 3) |
| Fix | t2 made the test zone-independent (`fb8f27c`, `3bd51bb`); reviews passed |
| Integrate before publish | 06:03:33 publish `back`: `origin/main` had moved (`7417fba`) → t3 merged it (`21b3ba5`) |
| Defect found | The final review diffed against the stale local `main`, saw `greeter`'s files as part of the Change and t4 removed them (`53d60ba`, local only). Paused at 06:05:07; fixed in `81f53d258` (base on `origin/<target>`); resumed 06:06:06. The corrected final review flagged the deletions, t5 restored them (`182e149`); net diff `time.ts` and its test only |
| Publish, follow, merge | 06:09:15 PR head `182e149`; "Publish · waiting for CI: 1 of 1 checks running (checked 8 s ago)"; run 38029946489 passed; consent through the Changes page merge dialog 06:10:27; squash merge → `d125e59`; cleanup with nothing to preserve |

Credits 4.14 (2.0 of them after the defect). Touchpoints: merge consent; pause and resume were my containment.

### Other runs

- `clamp`: the final reviewer refused the brief's deliberate CI-only failing test three times (the Builder kept it
  because the brief demanded it) → "waiting for you: Findings remain after 2 rounds". Abandoned through the intent
  API: 3 unmerged commits bundled (`clamp-1.bundle`, verified), worktree removed, no PR. Credits 2.49.
- Sandbox `main` CI after both merges: run 38030022257 success. PRs #3 and #4 merged; #1 and #2 untouched.

Total credits 7.86. After `SIGINT` to the host, `status` printed "Delivery is not running" and `pgrep` found no
host, runner, Copilot CLI runtime or preview.

### Limits and deviations

- The person-only check ran after follow, as D3 orders it, not before publish.
- Failure (a) used a wrong-premise brief, not an injected commit; `clamp`, the injected version, was correctly
  stopped by review.
- Event timestamps before `81f53d258` are the step's start time, not the event's.
- Not shown live: the merge queue (`enqueued` → pending, unit-checked), unknown rules → "merge in GitHub", review
  comments → Builder task, a check that never starts, a pre-push hook rejection, an unknown push or merge result.
- Publication does not yet verify that HEAD equals the last final-reviewed commit.

## Slice 3 demonstration

Date 2026-10-10, macOS. Copilot CLI 1.0.95, `github-copilot-sdk` 1.0.19, `mcp` 2.3.0, `truststore` 0.10.4,
gh 2.102.0, git 2.56.0; model `auto`, billed `gpt-6-luna` on every agent step, no mismatch. Sandbox `main` pulled
to `d125e59`; slice 2 state moved to `.git/owlbear-delivery/archive-slice-2/`. Code: `0667e3c53` plus the
trust-store and `.mcp.json` fixes committed in `2cf7005c5`. Every command ran from the OwlBear worktree; the
chat agent was simulated by a stdio MCP client (`ClientSession` over `stdio_client`, scratch script).

| Stage | Evidence |
| --- | --- |
| Setup, first try | Readiness: `FIX network: … CERTIFICATE_VERIFY_FAILED … self-signed certificate in certificate chain`, all else ok, one fix ("set SSL_CERT_FILE …"). Defect: Python's default CA store does not hold the corporate proxy's root while `gh` and Node use the system store; readiness now uses `truststore` |
| Setup without consent (stdin not a terminal) | Readiness all ok (network, gh 2.102.0, signed in, `boecht/owlbear-sandbox: ADMIN`, Copilot CLI 1.0.95, git identity, signing not required). Profile v1: known `install:packages/app = npm ci` (`package-lock.json`), `check:packages/app = npm test` (`scripts.test`), CI `ci.yml`/`test`, `squash`, no pre-push hook; unknown `github:rules`, `required-checks`, `merge-queue` (HTTP 403). "Profile not confirmed; nothing was saved"; no file written |
| `setup --yes --confirm github:rules=none` | `github:rules` recorded "owner confirmed 2026-10-10; observed: HTTP 403 …"; `--yes` left `required-checks` and `merge-queue` unknown and said so; profile v3 saved with `setup:confirmed-by = --yes`. Written: `.vscode/tasks.json` (task "OwlBear Delivery host", `runOptions.runOn: folderOpen`, `${workspaceFolder}`) and `.mcp.json` (new `owlbear-delivery` stdio entry merged beside the existing `cwdprobe`). `task.allowAutomaticTasks`: not set, reported with the disclosed manual action |
| Host | Started 06:54:24 with the task's command line (host 99919) |
| `save_brief`, invalid | `saved: false`, `outcome: String should have at least 20 characters - e.g. "farewell(name) exists"`, `criteria: List should have at least 1 item …` |
| `save_brief`, valid | "Add shout(text)", one criterion `shout("hi") returns "HI!"`, scope `packages/app`, no person check → `c1`, v1, next "Approve brief v1 of c1 in the Changes page"; `show_status`: "Shape · waiting for you: approve brief v1", action Approve brief. No runner started |
| Brief approval (API) | `POST …/approve-brief {"version": 1}` 06:54:49.00 → `approved_version 1`, `approved_at` recorded; runner 1396 started 06:54:49.36 (step `plan`) |
| Plan | First `submit_result` rejected: `tasks[0].checks: "cd packages/app && npm test" is not a check of the project profile - use one of "npm test"`; second accepted 06:55:12: t1 "Add shout(text) with a unit test", scope `packages/app/src`, `packages/app/test`, check `npm test`. Read-only challenge `pass` 06:55:35 |
| Build, review | Commit `4681ed7` 06:56:09; task review `pass` 06:56:23, final review `pass` 06:56:41 |
| Publish, follow | PR #5 ready at `4681ed7` 06:56:49 (title from the brief); "Publish · waiting for CI: 1 of 1 checks running"; run 38032693683 `test` passed; follow done 06:57:26 |
| Merge consent | 06:57:30 "Merge · waiting for you: approve merging 4681ed7". `answer_question c1.q1` through chat: `answered: false`, "This is a recovery decision; make it in the Changes page", with the page URL (T6). Consent for `4681ed7…e029` via API 06:57:46 |
| Merge, cleanup | Squash merge with the consented `sha` → `a6eb298` (GitHub merged 06:57:52); push CI on `main` success; worktree removed, nothing to preserve; history line written |
| Done | `show_status`: "Done · merged PR #5". After `SIGINT` to the host the chat fallback read the state: `running: false`, "Delivery is not running - start it with the VS Code task 'OwlBear Delivery host', or run …", same Done line |

Credits: plan 0.272, plan challenge 0.338, build 0.383, task review 0.259, final review 0.176; total 1.43.
Approval to merge took 3 min 3 s. Touchpoints: brief approval and merge consent only. No permission denial. After
the host stopped, `pgrep` found no host, runner or Copilot runtime. The sandbox keeps the consented
`.vscode/tasks.json` and `.mcp.json` uncommitted; local branch `owlbear/add-shout-text` remains.

Limits: VS Code did not open the sandbox, so the folder-open task, workspace trust and loading `.mcp.json` in a
real chat session were not exercised; setup reads `task.allowAutomaticTasks` from user settings but cannot verify
workspace trust. Signing readiness ran only its "not required" branch live. The plan challenge passed in one
round; a challenge with findings, re-planning, the planner's `report_wrong_premise` (back to shape) and brief
revision were not exercised live (revision before and refusal after approval are unit-tested). Deviations from D4
line targets: `setup.py` + `cli.py` 436 (260), `api.py` 313 (300), `tools.py` 368 (300), `sdk_adapter.py` 629 (600).

## Slice 3 repairs

Date 2026-10-10, macOS, sandbox `boecht/owlbear-sandbox`; every command ran from the OwlBear worktree.

| Repair | Change and evidence |
| --- | --- |
| Token-bearing links | `save_brief`'s `next`, `show_status`'s `changes_page` and the T6 refusal give the host's `URL#token=…` (`api.link`). Live: the stdio client's `show_status` returned `http://127.0.0.1:61868/#token=…`, identical to the host's start line |
| Brief review gate | Approval keeps the Change in shape until the reviewer judges that exact version (`Brief.reviewed`); pass plans, findings ask the owner to revise, split or plan as it is; a new version is reviewed again. Unit-tested; not run live |
| SSH signing readiness | A missing, unreadable or malformed key is a failed check with one fix. Unit-tested |
| Overlap check | The planner and plan challenger see other open Changes' scopes; an accepted plan that overlaps asks "proceed" or "order" (pause), keeping the plan. Unit-tested |
| Skill install | Setup wrote `~/.copilot/skills/delivery/SKILL.md` ("chat skill installed for you only (not tracked)") and offers no tracked copy; `copilot skill list` showed it under Personal skills. VS Code loading from that location is not yet verified |
| Readiness gates | Host start ran readiness ("07:21:27 readiness: ok"; `show_status` `readiness: ok`). Before publish, a failed fact becomes pending on the network or an ask carrying its fix (e.g. `gh auth login`). Unit-tested |

Setup rerun: readiness all ok, profile v4 saved with `--yes`. After `SIGINT` to host 33150, `pgrep` found no
Delivery-next process and `host.json` was gone.
