# Sharing OwlBear with Teammates

> How to give a teammate access to OwlBear for an existing project.

## Sharing Model

OwlBear uses a **shared installation** model: a single owlbear repository lives on a
developer's machine alongside their project directories. Each project references owlbear
using relative paths (e.g., `../owlbear/share/agents`). There is no packaging step — clone is
install.

This means sharing owlbear with a teammate means they clone **both**:

1. The **owlbear** repository (shared tooling)
2. The **project** repository (their actual project)

Both repos must sit in a sibling layout for the relative paths to work. On Windows,
they must also be on the same drive.

> **Windows limitation:** owlbear and the project must be on the **same drive**.
> Cross-drive relative paths raise a `ValueError` in `init.py` before any files are
> written. macOS and Linux are not affected.

---

## Set Up for a Teammate

Walk the teammate through these steps:

```shell
# 1. Clone the project repository to a convenient parent directory
git clone https://github.com/OWNER/PROJECT.git ~/Dev/my-project

# 2. Clone owlbear as a sibling
git clone https://github.com/maba-pag/owlbear.git ~/Dev/owlbear

# 3. Bootstrap owlbear into the project workspace
cd ~/Dev/my-project
uv run --project ../owlbear python ../owlbear/setup/init.py

# 4. Open the project in VS Code
code .
```

> **Windows:** use `C:\Dev\...` paths and backslashes:
> `uv run --project ..\owlbear python ..\owlbear\setup\init.py`.
> owlbear and the project must be on the same drive.

Setup infers the GitHub `owner/name` identity from the default `origin` remote. If the project uses a
different remote or has no inferable GitHub URL, pass `--remote NAME --github-repository OWNER/NAME`.

If an existing project reports that retired Delivery state needs migration, preserve the reported
files and follow the [Delivery state migration procedure](../serve/tools/README.md) before
restarting setup or Cockpit.

After VS Code opens, have the teammate follow the canonical
[installation verification](setup-guide.md#verify-the-installation). It checks both the shared
customization roots and all five seeded MCP servers. Before the first workflow, also run
`gh auth status` and confirm an active account.

To launch Cockpit for the shared project, run it from the project directory and point uv
at the sibling owlbear clone:

```shell
cd ~/Dev/my-project
uv run --project ../owlbear cockpit
```

This serves the prebuilt Cockpit bundle from owlbear while keeping target change, delivery,
Memory, and Ideas state scoped to the project.

---

## Platform Notes

### macOS and Linux

No platform-specific configuration is required:

- **Hooks** — all 5 hooks are Python scripts (`allow-stances-only.py`, `deny-src-writes.py`, `deny-writes.py`, `lint-changed.py`, `session-context.py`) executed by VS Code's extension host — no shell dependency
- **MCP servers** — started via `uv run`, which works identically on macOS, Linux, and Windows

### Windows

- owlbear and the project must be on the **same drive** (e.g., both on `C:\`)
- Use backslashes in the bootstrap command: `uv run --project ..\owlbear python ..\owlbear\setup\init.py`

---

## What's Shared vs. Project-Local

| Resource | Location | Shared? |
| --- | --- | --- |
| Agents (`.agent.md`) | `../owlbear/share/agents/` | Yes — all teammates get the same agents |
| Skills (`SKILL.md`) | `../owlbear/share/skills/` | Yes — all teammates get the same skills |
| Instructions (`*.instructions.md`) | `../owlbear/share/instructions/` | Yes — shared baseline |
| Prompts (`*.prompt.md`) | `../owlbear/share/prompts/` | Yes — shared baseline |
| MCP server code | `../owlbear/serve/` | Yes — started from owlbear via `uv run --project` |
| Hook runtime files | `.owlbear/hooks/` in project | No — copied from `seed/` into each project |
| Delivery package authority | `.owlbear/delivery/packages/` in project | No — tracked per-project |
| Delivery runtime and worktrees | `.owlbear/delivery/runtime/` and `.owlbear/delivery/worktrees/` in project | No — ignored and host-local |
| Immutable legacy inventory | `.owlbear/legacy/` in project, when present | No — read-only history |
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
eliminates the need for the sibling-dir setup but requires all developers to have the
same directory structure. Use this sparingly — the sibling layout is simpler.

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
| `ValueError` during `init.py` | Ensure owlbear and project are on the same Windows drive |
| Agents missing after setup | Run `init.py` again; check that `.vscode/settings.json` was created and contains `chat.agentFilesLocations` pointing to the owlbear installation |
| Cockpit command not found in project | Run `uv run --project ../owlbear cockpit` from the project root instead of plain `uv run cockpit` |
| Delivery MCP or Cockpit reports that a legacy root requires migration | Preserve the reported state unchanged and complete the dedicated Delivery migration before restarting |
| Cockpit opens the wrong workspace | Launch from the project root or pass the intended project directory to `uv --directory` |
| Hook updates not taking effect after `git pull` | Re-run `init.py`; use `--replace-hooks` if local hook files differ and you want the seeded versions restored |
| `uv` not found | Install uv using the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Different owlbear checkout states between teammates | Use the same branch (`main` for consumer use or `dev` for OwlBear development), then `git pull` and rerun `init.py` to refresh copied runtime files |
