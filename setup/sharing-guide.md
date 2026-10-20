# Sharing OwlBear with Teammates

> How to give a teammate access to OwlBear for an existing project.

## Sharing Model

OwlBear installs once per Mac. Each teammate installs it on their own Mac and adds their own clone
of the project on its pages; there is no packaging step, cloning OwlBear is the installation.

Two things can be shared between teammates and machines:

1. A **shared settings repository**: a Git repository that holds project settings, agent memory
   and the backlog. Each machine points at its own clone of it with `owlbear data PATH`; OwlBear
   commits and pushes every save there.
2. The optional **agent workspace**: OwlBear's agents, skills and tool servers loaded into the
   project's VS Code workspace from the OwlBear runtime alias `~/.owlbear/runtime`. Setup writes
   relative paths to that alias (e.g., `../../.owlbear/runtime/share/agents` for a project at
   `~/Dev/my-project`), so self-updates keep them valid; teammates who share these settings keep
   the project at the same path relative to their home folder.

## Prerequisites

The teammate needs a Mac with everything in the setup guide's
[Prerequisites](setup-guide.md#prerequisites), push access to the project on GitHub, and read and
write access to the shared settings repository if you use one.

---

## Set Up for a Teammate

Walk the teammate through these steps:

### 1. Clone the project repository

```shell
git clone https://github.com/OWNER/PROJECT.git ~/Dev/my-project
```

**Expected result:** the project is checked out at `~/Dev/my-project`.

### 2. Install and start OwlBear

Follow the setup guide's [Quick Start](setup-guide.md#quick-start) steps 1 to 3.

**Expected result:** `owlbear start` prints the address of OwlBear's pages.

### 3. Point OwlBear at the shared settings repository

Skip this step if your team does not use one.

```shell
git clone https://github.com/OWNER/SETTINGS.git ~/Dev/owlbear-settings
owlbear data ~/Dev/owlbear-settings
owlbear restart
```

**Expected result:** `owlbear data` names the repository and asks for the restart.

### 4. Add the project and connect its chats

Follow the setup guide's [Quick Start](setup-guide.md#quick-start) steps 4 and 5 with
`~/Dev/my-project`.

**Expected result:** the project is listed as `loaded` by `owlbear status`, and its Changes page
shows no **Setup required** note. Setup finds the project's folder in the shared settings
repository by the repository's identity, so every teammate's clone uses the same settings.

### 5. Optional: set up the agent workspace

```shell
cd ~/Dev/my-project
uv run --project ~/.owlbear/runtime python ~/.owlbear/runtime/setup/init.py
code .
```

**Expected result:** setup lists what it would write and asks first; after `y`, VS Code opens
`~/Dev/my-project` with the shared OwlBear customization roots
and the four seeded MCP servers; check them as
[the setup guide](setup-guide.md#4-confirm-it-loaded) describes.

---

## Platform Notes

OwlBear supports macOS only. Linux and Windows are not supported yet.

No further platform-specific configuration is required:

- **Hooks** — the seeded hook `deny-src-writes.py` is a Python script executed by VS Code's
  extension host — no shell dependency
- **MCP servers** — started via `uv run`

## What's Shared vs. Project-Local

| Resource | Location | Shared? |
| --- | --- | --- |
| OwlBear runtime | `~/.owlbear/runtime` | No — one per Mac; each machine updates itself |
| Delivery state | `~/.owlbear/projects/<id>/`, one folder per project | No — per machine |
| Project settings, agent memory, backlog | Shared settings repository | Yes — when one is set |
| Agents (`.agent.md`) | `~/.owlbear/runtime/share/agents/` | Yes — all teammates get the same agents |
| Skills (`SKILL.md`) | `~/.owlbear/runtime/share/skills/` | Yes — all teammates get the same skills |
| Instructions (`*.instructions.md`) | `~/.owlbear/runtime/share/instructions/` | Yes — shared baseline |
| Prompts (`*.prompt.md`) | `~/.owlbear/runtime/share/prompts/` | Yes — shared baseline |
| MCP server code | `~/.owlbear/runtime/serve/` | Yes — started from owlbear via `uv run --project` |
| Hook runtime files | `.owlbear/hooks/` in project | No — copied from `seed/` into each project |
| `.github/copilot-instructions.md` | project root | No — per-project (override layer) |
| `.owlbear/knowledge/` | project root | No — per-project |

Project-local resources can override or extend shared owlbear resources. Hook files are
the exception: they are project-local runtime copies, not a live-shared customization
surface. See
[Project-Specific Customization](operating-owlbear.md#project-specific-customization) in the
operating guide.

---

## Team Conventions

### Agent naming

Each teammate's project can add local agents, but agent names must be unique. VS Code
loads agents from all configured locations simultaneously and does **not** deduplicate
same-name agents. Two agents named `reviewer.agent.md` from different locations will
both appear in the picker.

**Convention:** Prefix project-specific agents with the project name:
`my-project-reviewer.agent.md`, not `reviewer.agent.md`.

### Project-specific instructions

The `.github/copilot-instructions.md` file in the project directory is the right place
for project-specific rules (coding style, domain conventions, restricted tools).
This file takes priority over the owlbear shared instructions — create it in your project
root and keep it in source control.

### Monorepo alternative

If the project is a monorepo, VS Code's `chat.useCustomizationsInParentRepositories`
setting allows owlbear customizations to be discovered from a parent directory. This
eliminates the need for the runtime-alias paths but requires all developers to have the
same directory structure. Use this sparingly — the runtime alias is simpler.

---

## Organization-Level Sharing (GitHub Teams)

For organizations with GitHub Copilot Business or Enterprise, VS Code supports
**organization-level agents** that are discovered automatically for all members without
any local setup step. This is an alternative to the filesystem sharing model above,
but it covers agents only (not MCP servers, skills, or instructions).

If your team has org-level Copilot access, consider publishing owlbear agents to the
organization agent registry as a complement to the local installation.

---

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| A teammate's Changes page shows **Setup required** | Run the `owlbear setup --repo PATH` command it names on that teammate's Mac, then reload the project's VS Code window |
| Setup cannot claim the project's folder in the shared settings | Run `owlbear setup --repo PATH --folder NAME` with a folder name no other repository uses |
| Agents missing after setup | Run `init.py` again; check that `.vscode/settings.json` was created and contains `chat.agentFilesLocations` pointing to the owlbear installation |
| Hook updates not taking effect after an OwlBear update | Re-run `init.py`; use `--replace-hooks` if local hook files differ and you want the seeded versions restored |
| `uv` not found | Install uv using the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Different OwlBear versions between teammates | Compare `owlbear versions` on each Mac; `owlbear update` takes the newest ([Upgrading OwlBear](operating-owlbear.md#upgrading-owlbear)). For the agent workspace, rerun `init.py` after an update to refresh copied runtime files |
