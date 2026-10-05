---
name: w-delivery-repair
description: "Workflow: Diagnose Delivery offline and apply fenced repair proposals under their confirmation policy"
user-invocable: false
---

# Delivery Repair

Repair Delivery state while its controllers are stopped. `delivery-repair` owns classification,
proposals, the fence, the journal, the backup and verification; the agent only runs its commands,
presents what they return, collects the user's decisions and reports. Unknown corruption is
preserved and diagnosed, never repaired by hand.

## Step 0 - Bootstrap

Run `delivery-diagnose inspect` first (the prompt names the exact command and its source fallback).
Then run `delivery-repair classify --format json` for the project, adding `--change-id` when the
user named a Change. Prefer the installed entry; when it is unavailable use
`uv run --no-sync delivery-repair` from the OwlBear checkout. Never run `uv sync`, setup or lifecycle
commands from this workflow.

If `classify` returns the `C09` maintenance finding (Delivery cannot be imported), report it with
the inspector's diagnostic codes and stop: platform defects follow the maintenance route, not this
workflow.

## Step 1 - Present Every Finding

Every finding names exactly one route, its owner and a resume condition. Present them grouped by
route and keep each one's owner and resume condition verbatim:

| Route | What the agent does |
| --- | --- |
| `offline` (C01, C02, C03) | Propose it in Step 2 |
| `offline` / `migrate` journal routes (C04) | Run the named `delivery-repair` command, or the delegated `delivery-migrate resume` or `verify`, with the named ID in Step 3; ask the user before `delivery-migrate abort` |
| `migrate` (`state-migration-required`) | Not delegated: name `/upgrade-delivery`, or ask the user through `vscode_askQuestions` and run `delivery-migrate propose`, `apply`, `verify` only after an explicit yes |
| `upgrade` (C05) | Name `/upgrade-delivery`; never downgrade or rewrite newer state |
| `online` (C06) | Name the MCP tool; it runs after Delivery starts, with that tool's own confirmation |
| `environment` (C08) | Give the exact `setup/init.py` instruction for the named locator |
| `contained` (C07) | Report the owner; the state stays preserved and refused |

`classify` also lists `online_checks`: C06 conditions only a remote read detects (snapshot
quarantine, local frontier mismatch, remote Change head mismatch, target-sync publication). They are
not findings: name each check's tool and say Delivery reports the condition after startup.

Never write request provenance, rehash a stored identity, or edit receipts, revisions, snapshots
or package identities. Never treat a finding as resolved because a command was run; only a
successful `verify` resolves it.

## Step 2 - Propose and Confirm (U1)

For one offline finding at a time run `delivery-repair propose <finding-id>` and show the returned
proposal: operation, policy, every path it changes, the consequence and the backup location.

- `engine-replay` (C03 `transaction-replay`) and the delegated `delivery-migrate resume` and
  `verify` commands are applied by the agent after it has shown the proposal; no further question.
  An initial migration (`delivery-migrate propose`, `apply`) is never delegated by this policy: it
  belongs to `/upgrade-delivery`, or runs only after the user explicitly approves it.
- `user-confirmed` (C01 `host-local-reset`, C02 `tracked-record-restore`) replaces user-owned or
  tracked bytes. Ask through `vscode_askQuestions` once per proposal, naming the paths, the
  consequence and the backup location, with the options *Apply this repair* and *Do not apply*.
  Only an explicit *Apply this repair* answer authorizes `--confirm <proposal-id>`; never infer it
  from an earlier answer, another proposal, or the prompt invocation.

## Step 3 - Stop, Apply, Verify

Ask the user to stop Delivery MCP (*MCP: List Servers* -> `owlbear-delivery` -> *Stop*) and every
Cockpit process for this project. Stopping controllers is always the user's step; never terminate
processes yourself. **Maintenance precondition:** no running process is exempt, not even a
degraded Cockpit, so the user must not restart Delivery MCP or Cockpit until `verify` (or `abort`)
has finished; say so before `apply`. `delivery-repair` repeats this precondition in its output and
checks again for controllers before every write. Then run, for one proposal:

1. `delivery-repair apply --proposal <id>` (adding `--confirm <id>` only after the Step 2 answer).
2. `delivery-repair verify <id>`.

`repair-controller-running` or `repair-controller-unknown` means a controller or an uninspectable
Python or uv process runs (or was started) in the workspace: ask the user to stop it, keep it
stopped, and retry the same command (`resume` after an interrupted `apply`).
`repair-proposal-stale` means the state changed: classify and propose again.
`repair-journal-open` names the journal that must finish first. After a crash or interruption run
`delivery-repair resume <id>`, then `verify`; `delivery-repair abort <id>` restores the complete
before-state from the backup when the user chooses to stop. `repair-corruption-stop` and
`repair-verify-mismatch` preserve every copy: report them and stop. A finding marked
`evidence: incomplete` (its located bytes exceed the evidence bounds or cannot be read) always makes
`verify` refuse `repair-verify-mismatch`; offer `abort` and report that finding's route.

Proposals are release-local staging. Before the user upgrades OwlBear, finish (`verify`) or `abort`
every applied repair with the current release, and propose any unapplied repair again afterwards.

After each verified repair, classify again. Repeat Steps 1 to 3 for the next offline finding.

## Step 4 - Restart and Report

Ask the user to restart Delivery MCP and Cockpit. Report the verified repairs, every remaining
finding with its route, owner and resume condition, and the backup locations. When `classify` finds
nothing for a Change that Cockpit shows blocked (a dirty or moved managed worktree, an unreadable
workspace, retry containment), say no offline repair applies and the card's reason is the blocker;
for a dirty worktree the user cleans it or abandons the Change. Use only finding IDs,
codes, Delivery-root-relative locators and proposal IDs; never raw record values, absolute paths,
exception text or log lines.
