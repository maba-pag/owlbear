# Sharing OwlBear with Teammates

> How to give a teammate access to OwlBear for an existing project.

## Sharing Model

OwlBear installs once per Mac. Each teammate installs it on their own Mac and adds their own clone
of the project on its pages; there is no packaging step, cloning OwlBear is the installation.

Teammates and machines share one thing: a **shared settings repository**, a Git repository that
holds project settings, agent memory and the backlog. Each machine keeps its own clone of it in
`~/.owlbear/data`, made by `owlbear data URL`; OwlBear commits and pushes every save there.

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
owlbear data https://github.com/OWNER/SETTINGS.git
owlbear restart
```

**Expected result:** `owlbear data` clones the repository into `~/.owlbear/data`, names it and asks
for the restart. To keep the clone elsewhere, clone it yourself and run `owlbear data PATH` instead;
that folder then wins over `~/.owlbear/data`. See
[The shared settings repository](operating-owlbear.md#the-shared-settings-repository).

### 4. Add the project and connect its chats

Follow the setup guide's [Quick Start](setup-guide.md#quick-start) steps 4 and 5 with
`~/Dev/my-project`.

**Expected result:** the project is listed as `loaded` by `owlbear status`, and its Changes page
shows no **Setup required** note. Setup finds the project's folder in the shared settings
repository by the repository's identity, so every teammate's clone uses the same settings.

---

## Platform Notes

OwlBear supports macOS only. Linux and Windows are not supported yet.

No further platform-specific configuration is required:

- **MCP servers** — OwlBear's memory, knowledge and browser servers start from the installed
  runtime (`python -m owlbear_delivery_next serve <name>`) and stay on the version they started
  with

## What's Shared vs. Project-Local

| Resource | Location | Shared? |
| --- | --- | --- |
| OwlBear runtime | `~/.owlbear/runtime` | No — one per Mac; each machine updates itself |
| Delivery state | `~/.owlbear/projects/<id>/`, one folder per project | No — per machine |
| Project settings, agent memory, backlog | Shared settings repository, cloned in `~/.owlbear/data` or the folder `owlbear data PATH` set | Yes — when one is set |
| Shaping agent and its skill | `~/.copilot/`, linked into `~/.owlbear/runtime` | Yes — every teammate's runtime ships the same ones |
| MCP server code | `~/.owlbear/versions/<tag>/serve/` | Yes — each server runs from the version it started with, through `~/.owlbear/runtime` |
| `.github/copilot-instructions.md` | project root | No — per-project |
| `.owlbear/knowledge/` | project root | No — per-project |

Project-local agents, instructions and MCP servers add to these. See
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
Create it in your project root and keep it in source control.

---

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| A teammate's Changes page shows **Setup required** | Run the `owlbear setup --repo PATH` command it names on that teammate's Mac, then reload the project's VS Code window |
| Setup cannot claim the project's folder in the shared settings | Run `owlbear setup --repo PATH --folder NAME` with a folder name no other repository uses |
| `uv` not found | Install uv using the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Different OwlBear versions between teammates | Compare `owlbear versions` on each Mac; `owlbear update` takes the newest ([Upgrading OwlBear](operating-owlbear.md#upgrading-owlbear)) |
