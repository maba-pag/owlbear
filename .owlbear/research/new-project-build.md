# New Project From Zero Build Design

> **Owning task:** item 15 of [the plan](owlbear-plan.md); owner decisions TD-421, TD-431..TD-433, TD-420; TD-420,
> TD-421 and TD-431/TD-432 since replaced by `D-01M5TYMBBBHQRN172N977ND3VS`, `D-01M5TYMBBAFTPN27RQKFVCEN6A`
> and `D-01M5TYR46VTW65B5JH1KM1M089`: no agent workspace
> **Date:** 2026-10-20
> **Question:** How does the owner create a new project, from an idea without a repository to one Delivery can use?
> **Status:** design answered by the owner on 2026-10-20; not built, not placed in the order. Made from the
> assistant's draft, Sol's proposal and the owner's intent, then challenged by Sol (REVISE 90%); every correction is
> folded in below.

## 1. Entry

Add project offers "An existing clone" (today) and "Create a new project". `owlbear install` ends by offering to open
the page on that choice; chat and commands only link there. Projects are still added only in the UI (TD-281).

## 2. The dialog

One dialog in steps, each with a default, ending in an exact preview of files and commands:

| Step | Default |
| --- | --- |
| Visibility, asked first (TD-431) | Private. If the chosen account's actual plan (read through `gh`) cannot protect branches of a private repository, the choice says so at once; paid accounts see no warning |
| Name and folder | `~/Projects/<slug>`; only a new or empty, owner-owned folder outside another repository |
| Git author | The effective Git configuration for that folder; asked when missing; written repository-local; signing requirements checked |
| GitHub repository | On; account and owner from `gh auth status`, by default the owner's account (TD-402) |
| Delivery's write account | The repository owner's account when `gh` has it, else `maba-pag`; shown and verified (TD-402) |
| CI and branch protection (TD-431) | Ticked and recommended: a minimal workflow with `push` and `pull_request` triggers and one job named `CI`; protection requires it, pull requests only, merge commits, no force push or deletion, no required approvals. Unavailable protection shows unticked with the reason |
| Labels | Inherit the Global list (C-16); creating missing labels is a separate tick |
| Delivery's chat tools | Ticked, with consent (TD-321), kept out of Git |

## 3. The run

A machine-host job with a receipt under `~/.owlbear`: approved inputs, intent recorded before each effect, file
fingerprints, commit, remote id and states. One job per destination; it counts as busy for stop and update; after a
restart an unfinished job shows with Retry.

1. **Preflight:** tools, the chosen account's `gh` login and permissions, name availability, signing. Nothing is
   created on failure; a missing login shows the `gh auth login` command (no tokens on the page).
2. **Local:** create the folder, `git init -b main`, local identity, render the approved files, commit exactly them
   (never `git add .`).
3. **GitHub:** create an empty repository with the chosen account, visibility sent explicitly and read back; record
   its id. A lost creation answer is reconciled; an occupied name is never adopted.
4. **Publish and protect:** check the approved files and commit tree again, push the first commit (the one consented
   direct push), wait a bounded time for `CI` on that exact commit, apply and read back the branch rules, save the
   merge method `merge` explicitly (profile detection prefers squash). A refused option asks again; never a silent
   weakening or a public repository.
5. **Configure and register:** labels if ticked, project settings, chat tools with consent, then
   register the project.

Local only (GitHub unticked) still completes the chosen local setup and is marked not ready for Delivery, with a later
publish path. Setup reuses the parts of `owlbear setup --repo` (consent, server entry, project files) behind the
dialog's answers.

**Account routing:** the project's GitHub account (TD-402's setting, pulled forward from item 10) routes setup and
every later GitHub write through a per-command `GH_TOKEN` from `gh auth token --user <login>`, never by switching `gh`
globally; Git pushes use that account's credential; tokens never reach receipts, logs or the page.

**Undo** removes only: files the job wrote and nobody changed, the folder if the job created it and it is otherwise
untouched, the registration. Never a repository with later work; a GitHub repository is deleted only by the owner.

## 4. Confirmation (C-29)

One dialog before running: what happens now (folder, files, commit, repository, push, rules), what Delivery does by
itself afterwards, what cannot be undone (a published repository), and the way forward if declined.

## 5. After creation (TD-433)

A project created this way is a real project: Delivery's work on it waits for the watcher (TD-338).

## 6. First version and later

First: personal repositories on github.com, one neutral starter, the resumable job, account routing, consent.
Later: organisations, framework templates, importing an existing folder without Git.

## 7. Tests

Temporary home and Git repositories, a fake `gh`, a crash injected at every step boundary (including after an effect
and before its receipt) and resumed, double clicks, an occupied name, a missing login, a plan without private
protection, undo of only owned artifacts; a browser test of the dialog.
