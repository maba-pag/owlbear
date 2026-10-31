---
name: owlbear-release-analysis
description: "Workflow: Analyse a Copilot SDK, Copilot CLI, AHP spec or VS Code release before OwlBear relies on it"
argument-hint: "Component and versions, e.g. 'SDK 1.0.27 → 1.0.28', 'CLI 1.0.105 → 1.0.107', 'VS Code 1.145', or a Renovate PR"
user-invocable: true
disable-model-invocation: true
---

# Release Analysis

Analyse one update of the Copilot platform OwlBear runs on, before OwlBear relies on it: what changed, what OwlBear
must change, what it could use, and the proof each changed part needs. The owner invokes it by name in a normal chat;
the text after the name says which component and versions. Renovate opens the SDK and AHP updates as their own pull
requests; Homebrew moves the CLI and VS Code updates itself, so those two start here by hand.

Release notes understate changes: the SDK's say "CLI snapshot" for releases that added session options, sign-in modes
and tool namespaces. Read what actually changed, never one component's notes alone.

## 1. When

| Update | Run it |
| --- | --- |
| SDK (`github-copilot-sdk`) | On its Renovate pull request, before it merges |
| AHP spec (`microsoft/agent-host-protocol`) | On its Renovate pull request, before it merges |
| Copilot CLI | Before `brew upgrade` installs it |
| VS Code | Before installing the release |

If the CLI or VS Code already moved: stop OwlBear when idle on the machine page (New Change is refused while it
drains). That stops the host, which the decision lookup in step 4 needs, so restart it with `owlbear start --paused`
and start no Change step or New Change yourself (paused does not refuse New Change) until the analysis is done and any
repair is released and installed (`owlbear update`); then press Resume. Paused still runs a curation or Retro trigger
set to "On, even while paused" (curate after merge, curate when idle, Retro after a Change, Retro when idle): before
the restart, set each such trigger on the machine page to "On, not while paused", start neither by hand, and put them
back after the Resume.

## 2. Pin the versions and read what changed

Name the from and to versions, and each source with its exact version or ref. Work in a folder of this run's own,
`.owlbear/scratch/release-<component>-<to>/`, and delete only that folder at the end: `.owlbear/scratch/` holds other
tools' data.

- **SDK:** for each version, `https://pypi.org/pypi/github-copilot-sdk/<version>/json` gives the
  `py3-none-any` wheel's URL and SHA-256. Fetch both with `curl`, check each hash, unpack with
  `uv run python -m zipfile -e <wheel> <folder>` (no pip), then `diff -ru` the two `copilot/` folders. Read every
  changed file, not only the notes. Note the CLI each pins (`copilot/_cli_version.py` `CLI_VERSION`) and its protocol
  (`copilot/_sdk_protocol_version.py`) against the installed CLI (`copilot --version`): Delivery runs the installed
  CLI (`runtimes/copilot_cli.py`), never the SDK's own.
- **CLI:** `gh release list -R github/copilot-cli` and `gh release view <tag> -R github/copilot-cli` for every
  release between the installed version and the new one, pre-releases skipped.
- **AHP:** `gh api repos/microsoft/agent-host-protocol/compare/spec/v<from>...spec/v<to>`, its `CHANGELOG.md`, and
  `types/test-cases/version-negotiation.json` at the new tag.
- **VS Code:** the release notes, `https://code.visualstudio.com/updates/v1_<minor>`, for each version since the
  last one analysed; read the agent host, chat, Copilot and settings sections.

For an SDK or AHP update, also read the CLI and VS Code notes for the versions installed now: the SDK's changes often
arrive from the CLI.

## 3. Classify each change

For every change, one line: what changed (with the source's file:line or note), then one of

- **must change:** OwlBear breaks or behaves differently without a change. Give the OwlBear file:line it hits.
- **use:** OwlBear could use it. Give the OwlBear file:line it would change, and what it would gain.
- **ignore:** it touches nothing OwlBear uses. Say why in a few words.

Find OwlBear's call sites with `rg`, starting from `runtimes/` in `serve/delivery-next/src/owlbear_delivery_next/`:
`sdk_adapter.py` and the `sdk_*.py` modules (session options, events, usage), `copilot_cli.py` (which CLI runs),
`ahp.py` (the protocol it offers), `vscode_*.py` (the shaping chat). Group items only when every member is named.

## 4. Check against the decisions

Ask `lookup_decisions` one question that names the update and the changes it touches; one lookup at a time, retrying
on "another lookup is running". Check each must-change and use item against the answer and name the decisions it
touches or breaks. If the lookup fails, say the decisions are unavailable and why, never that none apply. The
decisions stay in the chat: none of their text goes into a commit, pull request or comment; cite their ids only.

## 5. Name the proof

For each must-change item, the proof its fix needs, chosen by the part it changes:

| Part | Proof |
| --- | --- |
| Session options or events (`sdk_adapter.py`, `sdk_*.py`) | A unit test that fails before the fix, and one live step |
| AHP (`ahp.py`, `vscode_*.py`) | The spec's `version-negotiation.json` fixture test, and a live New Change |
| The CLI | `uv run pytest -m model serve/delivery-next/tests/test_step_loading_live.py`, run locally |

## 6. Report and act

Write the report to owlbear-data, `owlbear/research/platform-releases/<component>-<from>-<to>.md`, in a clone of
maba-pag/owlbear-data, committed and pushed to its main. It holds the pinned versions and sources, the classified
list, the decision check's outcome, and the proof per must-change item. On the pull request (SDK, AHP) or the
tracking issue (CLI, VS Code), comment a summary that links the report and cites decision ids only.

- **must change:** for an SDK or AHP update, fix it in its Renovate pull request, with its proof, before it merges.
  For a CLI or VS Code update, which has no pull request, fix it in a repair pull request of its own; OwlBear uses
  the new version only once the repair is released and installed.
- **use:** ask the owner, one item per question; file an issue for each he approves.
- **ignore:** nothing further.

The Renovate pull request merges only once this analysis is done; Renovate sets no release label, so the owner labels
it to release it.
